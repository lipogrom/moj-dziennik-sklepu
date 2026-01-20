import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(page_title="Dziennik Sklepu", page_icon="🛒", layout="wide")

# Mniejszy tytuł (według życzenia)
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
        
        # Konwersja i czyszczenie
        df['Klienci'] = pd.to_numeric(df['Klienci'], errors='coerce').fillna(0).astype(int)
        df['Utarg'] = pd.to_numeric(df['Utarg'], errors='coerce').fillna(0.0)
        df['Srednia'] = pd.to_numeric(df['Srednia'], errors='coerce').fillna(0.0)
        
        if 'Data' in df.columns:
            df['Data'] = pd.to_datetime(df['Data']).dt.date
            df = df.sort_values(by=['Data', 'Godzina'], ascending=[False, True])
        return df
    except Exception as e:
        return pd.DataFrame(columns=['Data', 'Godzina', 'Klienci', 'Utarg', 'Srednia'])

def zapisz_wszystko(df):
    df_save = df.copy()
    
    # Przeliczanie średniej
    df_save['Srednia'] = df_save.apply(
        lambda row: round(row['Utarg'] / row['Klienci'], 2) if row['Klienci'] > 0 else 0.0, 
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

# --- 4. INTERFEJS I NAWIGACJA ---

# MENU BOCZNE (Sidebar)
with st.sidebar:
    st.header("🗂️ Menu")
    # Przełącznik widoku
    wybrany_widok = st.radio(
        "Wybierz zakładkę:",
        ["🏠 Wpis i Edycja", "📅 Historia i Kalendarz"]
    )
    st.divider()
    st.info("Dane są zapisywane automatycznie w Google Sheets.")

# --- WIDOK 1: WPIS I EDYCJA (GŁÓWNY) ---
if wybrany_widok == "🏠 Wpis i Edycja":
    
    # A. FORMULARZ DODAWANIA (TERAZ NA GŁÓWNYM EKRANIE)
    st.container() # Ramka dla porządku
    st.subheader("➕ Dodaj nowy wpis")
    
    with st.form("dodaj_wpis_main"):
        # Układamy pola w dwóch kolumnach dla lepszego wyglądu
        col1, col2 = st.columns(2)
        
        with col1:
            wybrana_data = st.date_input("Data", date.today())
            klienci = st.number_input("Liczba klientów", min_value=0, step=1)
            
        with col2:
            godziny_lista = [f"{h}:00" for h in range(7, 22)]
            wybor_godziny = st.selectbox("Godzina", godziny_lista)
            utarg = st.number_input("Utarg (zł)", min_value=0.0, step=0.1)
        
        # Przycisk na całą szerokość
        submit = st.form_submit_button("ZAPISZ WPIS", type="primary", use_container_width=True)

    if submit:
        srednia = round(utarg / klienci, 2) if klienci > 0 else 0
        nowy_wiersz = [str(wybrana_data), wybor_godziny, klienci, utarg, srednia]
        try:
            arkusz.append_row(nowy_wiersz)
            st.success(f"✅ Dodano! {wybrana_data} | Godz: {wybor_godziny}")
            st.rerun()
        except Exception as e:
            st.error(f"Błąd zapisu: {e}")

    st.divider()

    # B. TABELA EDYCJI I USUWANIA
    df = pobierz_dane()
    
    if not df.empty:
        # Narzędzie usuwania (zwijane)
        with st.expander("🗑️ Narzędzie usuwania wpisów"):
            st.warning("Tutaj możesz trwale usunąć błędny wpis.")
            lista_wpisow = [
                f"{row['Data']} | {row['Godzina']} | {row['Utarg']:.2f} zł" 
                for index, row in df.iterrows()
            ]
            wybrany_do_usuniecia = st.selectbox("Wybierz wpis:", lista_wpisow)
            
            if st.button("❌ USUŃ WYBRANY", type="primary"):
                indeks = lista_wpisow.index(wybrany_do_usuniecia)
                df_po_usunieciu = df.drop(df.index[indeks])
                with st.spinner("Usuwam..."):
                    zapisz_wszystko(df_po_usunieciu)
                st.success("Usunięto!")
                st.rerun()

        # Tabela edycji
        st.subheader("🖊️ Edytuj dzisiejsze (i starsze) wpisy")
        
        konfiguracja_kolumn = {
            "Godzina": st.column_config.SelectboxColumn(
                "Godzina", options=[f"{h}:00" for h in range(7, 22)], required=True
            ),
            "Utarg": st.column_config.NumberColumn("Utarg", min_value=0, format="%.2f zł"),
            "Srednia": st.column_config.NumberColumn("Średnia", format="%.2f zł", disabled=True),
            "Klienci": st.column_config.NumberColumn("Klienci", format="%d"),
            "Data": st.column_config.DateColumn("Data", format="YYYY-MM-DD")
        }

        edytowane = st.data_editor(
            df, 
            column_config=konfiguracja_kolumn,
            num_rows="dynamic", 
            use_container_width=True, 
            key="editor"
        )
        
        if st.button("💾 ZATWIERDŹ ZMIANY W TABELI"):
            with st.spinner("Zapisuję zmiany..."):
                zapisz_wszystko(edytowane)
            st.success("Zapisano!")
            st.rerun()

# --- WIDOK 2: HISTORIA I KALENDARZ ---
elif wybrany_widok == "📅 Historia i Kalendarz":
    st.subheader("📅 Podsumowanie Miesiąca")
    
    df = pobierz_dane()
    
    if not df.empty:
        # Kafelki z podsumowaniem ogólnym
        c1, c2, c3 = st.columns(3)
        c1.metric("Suma Utargu", f"{df['Utarg'].sum():.2f} zł")
        c2.metric("Liczba Klientów", f"{df['Klienci'].sum()}")
        srednia_ogolna = df['Utarg'].sum() / df['Klienci'].sum() if df['Klienci'].sum() > 0 else 0
        c3.metric("Średni paragon", f"{srednia_ogolna:.2f} zł")

        st.divider()

        # Tabela dzienna
        st.write("Dziennik sprzedaży (dniami):")
        kalendarz = df.groupby('Data')[['Utarg', 'Klienci']].sum().sort_index(ascending=False).reset_index()
        
        st.dataframe(
            kalendarz, 
            column_config={
                "Utarg": st.column_config.NumberColumn(format="%.2f zł"),
                "Data": st.column_config.DateColumn("Dzień")
            },
            use_container_width=True
        )
        
        # Wykres
        st.write("Trend sprzedaży:")
        st.bar_chart(kalendarz, x="Data", y="Utarg")
    else:
        st.info("Brak danych do wyświetlenia.")
