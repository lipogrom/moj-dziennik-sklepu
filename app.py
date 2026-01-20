import streamlit as st
import pandas as pd
import gspread
import altair as alt  # <--- NOWA BIBLIOTEKA DO ŁADNYCH WYKRESÓW
from google.oauth2.service_account import Credentials
from datetime import date, timedelta

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(page_title="Dziennik Sklepu", page_icon="🛒", layout="wide")
st.markdown("### ☁️ Dziennik Sklepu (Google Sheets)")

# --- 2. POŁĄCZENIE Z GOOGLE ---
ARKUSZ_ID = "13M376ahDkq_8ZdwxDZ5Njn4cTKfO4v78ycMRsowmPMs"

@st.cache_resource
def polacz_z_google():
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets']
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(ARKUSZ_ID).sheet1
        return sheet
    except Exception as e:
        return None

arkusz = polacz_z_google()

if arkusz is None:
    st.error("❌ Błąd połączenia z chmurą Google.")
    st.stop()

# --- 3. FUNKCJE DANYCH ---
def pobierz_dane():
    try:
        dane = arkusz.get_all_records()
        if not dane:
            return pd.DataFrame(columns=['Data', 'Godzina', 'Klienci', 'Utarg', 'Srednia'])
        df = pd.DataFrame(dane)
        
        # Konwersja
        df['Klienci'] = pd.to_numeric(df['Klienci'], errors='coerce').fillna(0).astype(int)
        df['Utarg'] = pd.to_numeric(df['Utarg'], errors='coerce').fillna(0.0)
        df['Srednia'] = pd.to_numeric(df['Srednia'], errors='coerce').fillna(0.0)
        
        if 'Data' in df.columns:
            df['Data'] = pd.to_datetime(df['Data']).dt.date
            # Sortowanie: Data malejąco, potem Godzina malejąco
            df = df.sort_values(by=['Data', 'Godzina'], ascending=[False, False])
            
        # Reset indeksu
        df = df.reset_index(drop=True)
        return df
    except Exception as e:
        return pd.DataFrame(columns=['Data', 'Godzina', 'Klienci', 'Utarg', 'Srednia'])

def zapisz_wszystko(df):
    """Naprawa matematyki i zapis"""
    df_save = df.copy()

    # --- BEZPIECZNIK ---
    if 'Lp.' in df_save.columns:
        df_save = df_save.drop(columns=['Lp.'])
    
    # Przeliczanie średniej
    df_save['Srednia'] = df_save.apply(
        lambda row: round(float(row['Utarg']) / float(row['Klienci']), 2) if row['Klienci'] > 0 else 0.0, 
        axis=1
    )

    # Sanityzacja
    df_save['Klienci'] = pd.to_numeric(df_save['Klienci'], errors='coerce').fillna(0).astype(int)
    df_save['Utarg'] = pd.to_numeric(df_save['Utarg'], errors='coerce').fillna(0.0)
    df_save['Srednia'] = pd.to_numeric(df_save['Srednia'], errors='coerce').fillna(0.0)
    df_save = df_save.fillna("")
    df_save['Data'] = df_save['Data'].astype(str)
    
    try:
        arkusz.clear()
        arkusz.append_row(df_save.columns.tolist())
        arkusz.append_rows(df_save.values.tolist())
    except Exception as e:
        st.error(f"Błąd zapisu: {e}")

# --- 4. INTERFEJS ---

tab1, tab2 = st.tabs(["🏠 Panel Główny", "📅 Historia i Wykresy"])

# === ZAKŁADKA 1: PANEL GŁÓWNY ===
with tab1:
    col_left, col_right = st.columns([0.35, 0.65], gap="large")

    # --- LEWA: FORMULARZ ---
    with col_left:
        st.markdown("##### ➕ Nowy wpis")
        with st.container(border=True):
            with st.form("dodaj_wpis_main"):
                wybrana_data = st.date_input("Data", date.today())
                
                godziny_lista = [f"{h}:00" for h in range(7, 22)]
                wybor_godziny = st.selectbox("Godzina", godziny_lista)
                
                klienci = st.number_input("Liczba klientów", min_value=0, step=1)
                utarg = st.number_input("Utarg (zł)", min_value=0.0, step=0.1)
                
                st.markdown("---")
                submit = st.form_submit_button("ZAPISZ WPIS", type="primary", use_container_width=True)

        if submit:
            srednia = round(utarg / klienci, 2) if klienci > 0 else 0
            nowy_wiersz = [str(wybrana_data), wybor_godziny, klienci, utarg, srednia]
            try:
                arkusz.append_row(nowy_wiersz)
                st.toast(f"✅ Dodano! {utarg} zł", icon="💰")
                st.rerun()
            except Exception as e:
                st.error(f"Błąd zapisu: {e}")

    # --- PRAWA: TABELA Z Lp. ---
    with col_right:
        df = pobierz_dane()
        
        if not df.empty:
            df.insert(0, 'Lp.', range(1, len(df) + 1))

            with st.expander("🗑️ Narzędzie usuwania"):
                mapa_wpisow = {}
                for idx, row in df.iterrows():
                    etykieta = f"Lp. {row['Lp.']} | {row['Data']} | {row['Godzina']} | {row['Utarg']:.2f} zł"
                    mapa_wpisow[etykieta] = idx
                
                wybrana_etykieta = st.selectbox("Wybierz wpis do usunięcia:", list(mapa_wpisow.keys()))
                
                if st.button("❌ USUŃ TRWALE", type="primary"):
                    indeks_do_usuniecia = mapa_wpisow[wybrana_etykieta]
                    df_po_usunieciu = df.drop(indeks_do_usuniecia)
                    with st.spinner("Usuwam..."):
                        zapisz_wszystko(df_po_usunieciu)
                    st.success("Usunięto!")
                    st.rerun()

            st.markdown("##### 🖊️ Ostatnie wpisy")
            
            konfiguracja = {
                "Lp.": st.column_config.NumberColumn("Lp.", disabled=True, width="small"),
                "Godzina": st.column_config.SelectboxColumn("Godzina", options=[f"{h}:00" for h in range(7, 22)], required=True),
                "Utarg": st.column_config.NumberColumn("Utarg", min_value=0, format="%.2f zł"),
                "Srednia": st.column_config.NumberColumn("Średnia", format="%.2f zł", disabled=True),
                "Klienci": st.column_config.NumberColumn("Klienci", format="%d"),
                "Data": st.column_config.DateColumn("Data", format="YYYY-MM-DD")
            }

            edytowane = st.data_editor(
                df, 
                column_config=konfiguracja, 
                num_rows="dynamic", 
                use_container_width=True, 
                key="editor",
                height=500,
                hide_index=True
            )
            
            if st.button("💾 ZATWIERDŹ ZMIANY W TABELI", use_container_width=True):
                with st.spinner("Aktualizuję..."):
                    zapisz_wszystko(edytowane)
                st.success("Zapisano!")
                st.rerun()
        else:
            st.info("Brak wpisów.")

# === ZAKŁADKA 2: HISTORIA ===
with tab2:
    st.subheader("📅 Podsumowanie Statystyk")
    df = pobierz_dane()
    
    if not df.empty:
        c1, c2, c3 = st.columns(3)
        suma_utarg = df['Utarg'].sum()
        suma_klientow = df['Klienci'].sum()
        srednia_ogolna = suma_utarg / suma_klientow if suma_klientow > 0 else 0
        
        c1.metric("Utarg Całkowity", f"{suma_utarg:.2f} zł")
        c2.metric("Liczba Klientów", f"{suma_klientow}")
        c3.metric("Średni Paragon", f"{srednia_ogolna:.2f} zł")

        st.divider()
        
        widok_wykresu = st.radio("Grupowanie wykresu:", ["📆 Dni", "📊 Tygodnie"], horizontal=True)

        if widok_wykresu == "📆 Dni":
            # --- WYKRES DZIENNY (ALTAIR - POZIOME NAPISY) ---
            kalendarz = df.groupby('Data')[['Utarg']].sum().reset_index()
            kalendarz['Data'] = pd.to_datetime(kalendarz['Data'])
            kalendarz = kalendarz.sort_values('Data')
            kalendarz['Data'] = kalendarz['Data'].dt.strftime('%Y-%m-%d')
            
            wykres_dni = alt.Chart(kalendarz).mark_bar().encode(
                x=alt.X('Data', title='Data', axis=alt.Axis(labelAngle=0)), # <-- KĄT 0 STOPNI (POZIOMO)
                y=alt.Y('Utarg', title='Utarg (zł)'),
                tooltip=['Data', 'Utarg']
            ).interactive()
            
            st.altair_chart(wykres_dni, use_container_width=True)
            
        else:
            # --- WYKRES TYGODNIOWY (ALTAIR - POZIOME NAPISY) ---
            df_tyg = df.copy()
            df_tyg['Data'] = pd.to_datetime(df_tyg['Data'])
            
            def oznacz_tydzien(data):
                start = data - timedelta(days=data.weekday())
                koniec = start + timedelta(days=6)
                nr = data.strftime('%W')
                rok = data.strftime('%Y')
                zakres = f"{start.strftime('%d.%m')} - {koniec.strftime('%d.%m')}"
                return f"{rok}-W{nr} ({zakres})"

            df_tyg['Etykieta'] = df_tyg['Data'].apply(oznacz_tydzien)
            wykres_tygodniowy = df_tyg.groupby('Etykieta')[['Utarg']].sum().reset_index().sort_values('Etykieta')
            
            wykres_tyg = alt.Chart(wykres_tygodniowy).mark_bar().encode(
                x=alt.X('Etykieta', title='Tydzień', axis=alt.Axis(labelAngle=0)), # <-- KĄT 0 STOPNI (POZIOMO)
                y=alt.Y('Utarg', title='Utarg (zł)'),
                tooltip=['Etykieta', 'Utarg']
            ).interactive()

            st.altair_chart(wykres_tyg, use_container_width=True)
        
        st.divider()
        st.markdown("**Tabela podsumowująca (Dni):**")
        
        tabela_dni = df.groupby('Data')[['Utarg', 'Klienci']].sum().sort_index(ascending=False).reset_index()
        tabela_dni['Srednia Dnia'] = tabela_dni.apply(lambda x: x['Utarg'] / x['Klienci'] if x['Klienci'] > 0 else 0, axis=1)

        st.dataframe(
            tabela_dni, 
            column_config={
                "Utarg": st.column_config.NumberColumn(format="%.2f zł"),
                "Srednia Dnia": st.column_config.NumberColumn(format="%.2f zł"),
                "Data": st.column_config.DateColumn("Dzień")
            },
            use_container_width=True
        )
    else:
        st.info("Brak danych.")
