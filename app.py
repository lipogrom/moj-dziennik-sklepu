import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(page_title="Dziennik Sklepu Cloud", page_icon="☁️", layout="wide")
st.title("☁️ Dziennik Sklepu (Google Sheets)")

# --- 2. POŁĄCZENIE Z GOOGLE ---
# 👇👇👇 TUTAJ WKLEJ SWOJE ID ARKUSZA 👇👇👇
ARKUSZ_ID = "13M376ahDkq_8ZdwxDZ5Njn4cTKfO4v78ycMRsowmPMs"

@st.cache_resource
def polacz_z_google():
    """Łączy się z Google Sheets używając ID arkusza"""
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
    st.error(f"❌ BŁĄD: Nie mogę otworzyć arkusza. Sprawdź ID w kodzie.")
    st.stop()
else:
    st.toast("Połączono z Google Sheets!", icon="✅")

# --- 3. FUNKCJE DANYCH ---
def pobierz_dane():
    try:
        dane = arkusz.get_all_records()
        if not dane:
            return pd.DataFrame(columns=['Data', 'Godzina', 'Klienci', 'Utarg', 'Srednia'])
        
        df = pd.DataFrame(dane)
        
        # Konwersja typów
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
    """Nadpisuje cały arkusz"""
    df_save = df.copy()
    
    # Przeliczamy średnią na nowo (na wypadek gdybyś zmienił utarg w tabeli)
    # Zabezpieczenie przed dzieleniem przez zero
    df_save['Srednia'] = df_save.apply(
        lambda row: round(row['Utarg'] / row['Klienci'], 2) if row['Klienci'] > 0 else 0.0, 
        axis=1
    )

    # Sanityzacja (puste pola na zera)
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
tab1, tab2 = st.tabs(["✍️ Wpis i Edycja", "📅 Kalendarz i Historia"])

# === ZAKŁADKA 1: WPISY ===
with tab1:
    st.header("Zarządzanie wpisami")
    
    # --- FORMULARZ BOCZNY ---
    with st.sidebar:
        st.header("➕ Dodaj nowy wpis")
        with st.form("dodaj_wpis"):
            wybrana_data = st.date_input("Data", date.today())
            godziny_lista = [f"{h}:00" for h in range(7, 22)]
            wybor_godziny = st.selectbox("Godzina", godziny_lista)
            klienci = st.number_input("Liczba klientów", min_value=0, step=1)
            utarg = st.number_input("Utarg (zł)", min_value=0.0, step=0.1)
            
            submit = st.form_submit_button("ZAPISZ W CHMURZE")

    if submit:
        srednia = round(utarg / klienci, 2) if klienci > 0 else 0
        nowy_wiersz = [str(wybrana_data), wybor_godziny, klienci, utarg, srednia]
        try:
            arkusz.append_row(nowy_wiersz)
            st.success(f"✅ Zapisano! {wybrana_data} - {wybor_godziny}")
            st.rerun()
        except Exception as e:
            st.error(f"Błąd zapisu: {e}")

    # --- TABELA EDYCJI (Nowa Konfiguracja!) ---
    df = pobierz_dane()
    
    if not df.empty:
        # Konfiguracja kolumn - Tu dzieje się magia wyglądu
        konfiguracja_kolumn = {
            "Godzina": st.column_config.SelectboxColumn(
                "Godzina",
                help="Kliknij dwukrotnie, aby zmienić godzinę",
                width="medium",
                options=[f"{h}:00" for h in range(7, 22)], # Lista 7-21
                required=True
            ),
            "Utarg": st.column_config.NumberColumn(
                "Utarg",
                help="Utarg w złotówkach",
                min_value=0,
                step=0.1,
                format="%.2f zł" # Formatowanie waluty
            ),
            "Srednia": st.column_config.NumberColumn(
                "Średnia",
                format="%.2f zł", # Formatowanie waluty
                disabled=True # Średniej nie edytujemy, ona się sama liczy
            ),
            "Klienci": st.column_config.NumberColumn(
                "Klienci",
                min_value=0,
                step=1,
                format="%d"
            ),
            "Data": st.column_config.DateColumn(
                "Data",
                format="YYYY-MM-DD"
            )
        }

        st.subheader("🖊️ Tabela (Edycja)")
        st.info("Kliknij dwukrotnie w komórkę, aby edytować.")
        
        # Wyświetlamy tabelę z nową konfiguracją
        edytowane = st.data_editor(
            df, 
            column_config=konfiguracja_kolumn, # Podpinamy konfigurację
            num_rows="dynamic", 
            use_container_width=True, 
            key="editor"
        )
        
        # Przycisk zapisu
        if st.button("💾 ZATWIERDŹ ZMIANY W TABELI", type="primary"):
            with st.spinner("Przeliczam średnią i aktualizuję chmurę..."):
                zapisz_wszystko(edytowane)
            st.success("Arkusz zaktualizowany.")
            st.rerun()

# === ZAKŁADKA 2: KALENDARZ ===
with tab2:
    st.header("📅 Podsumowanie")
    df = pobierz_dane()
    
    if not df.empty:
        kalendarz = df.groupby('Data')[['Utarg', 'Klienci']].sum().sort_index(ascending=False).reset_index()
        
        col1, col2 = st.columns(2)
        col1.metric("Łączny Utarg", f"{df['Utarg'].sum():.2f} zł")
        col2.metric("Łącznie Klientów", f"{df['Klienci'].sum()}")
        
        st.dataframe(
            kalendarz, 
            column_config={"Utarg": st.column_config.NumberColumn(format="%.2f zł")},
            use_container_width=True
        )
        st.bar_chart(kalendarz, x="Data", y="Utarg")
