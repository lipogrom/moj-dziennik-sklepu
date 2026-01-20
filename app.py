import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(page_title="Dziennik Sklepu Cloud", page_icon="☁️", layout="wide")
st.title("☁️ Dziennik Sklepu (Google Sheets)")

# --- 2. POŁĄCZENIE Z GOOGLE ---
# Upewnij się, że Twój plik na dysku ma taką nazwę!
NAZWA_ARKUSZA = "Dziennik Sklepu Baza"

@st.cache_resource
def polacz_z_google():
    """Łączy się z Google Sheets używając klucza z Secrets"""
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets']
        # Pobieramy klucz z sejfu Streamlit
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        # Otwieramy arkusz
        sheet = client.open(NAZWA_ARKUSZA).sheet1
        return sheet
    except Exception as e:
        return None

# Próba połączenia
arkusz = polacz_z_google()

if arkusz is None:
    st.error(f"❌ BŁĄD: Nie mogę znaleźć arkusza o nazwie '{NAZWA_ARKUSZA}' lub robot nie ma do niego dostępu.")
    st.info("Sprawdź czy udostępniłeś arkusz dla maila robota (client_email)!")
    st.stop()
else:
    st.toast("Połączono z Google Sheets!", icon="✅")

# --- 3. FUNKCJE DANYCH ---
def pobierz_dane():
    """Pobiera wszystkie dane z arkusza do DataFrame"""
    try:
        dane = arkusz.get_all_records()
        if not dane:
            return pd.DataFrame(columns=['Data', 'Godzina', 'Klienci', 'Utarg', 'Srednia'])
        
        df = pd.DataFrame(dane)
        # Konwersja liczb (gdyby Google zapisał je jako tekst)
        df['Klienci'] = pd.to_numeric(df['Klienci'], errors='coerce').fillna(0).astype(int)
        df['Utarg'] = pd.to_numeric(df['Utarg'], errors='coerce').fillna(0.0)
        df['Srednia'] = pd.to_numeric(df['Srednia'], errors='coerce').fillna(0.0)
        
        # Sortowanie dat
        if 'Data' in df.columns:
            df['Data'] = pd.to_datetime(df['Data']).dt.date
            df = df.sort_values(by=['Data', 'Godzina'], ascending=[False, True])
        return df
    except Exception as e:
        st.error(f"Błąd pobierania: {e}")
        return pd.DataFrame()

def zapisz_wszystko(df):
    """Nadpisuje cały arkusz (dla edycji)"""
    df_save = df.copy()
    df_save['Data'] = df_save['Data'].astype(str) # Data na tekst dla JSONa
    
    arkusz.clear()
    arkusz.append_row(df_save.columns.tolist()) # Nagłówki
    arkusz.append_rows(df_save.values.tolist()) # Dane

# --- 4. INTERFEJS ---
tab1, tab2 = st.tabs(["✍️ Wpis i Edycja", "📅 Kalendarz i Historia"])

# === ZAKŁADKA 1: WPISY ===
with tab1:
    st.header("Zarządzanie wpisami")
    
    # FORMULARZ (SIDEBAR)
    with st.sidebar:
        st.header("➕ Dodaj nowy wpis")
        with st.form("dodaj_wpis"):
            wybrana_data = st.date_input("Data", date.today())
            godziny = [f"{h}:00" for h in range(7, 22)]
            wybor_godziny = st.selectbox("Godzina", godziny)
            klienci = st.number_input("Liczba klientów", min_value=0, step=1)
            utarg = st.number_input("Utarg (zł)", min_value=0.0, step=0.1)
            
            submit = st.form_submit_button("ZAPISZ W CHMURZE")

    if submit:
        srednia = round(utarg / klienci, 2) if klienci > 0 else 0
        nowy_wiersz = [str(wybrana_data), wybor_godziny, klienci, utarg, srednia]
        
        try:
            arkusz.append_row(nowy_wiersz)
            st.success(f"✅ Zapisano w Google Sheets! {wybrana_data} - {wybor_godziny}")
            st.rerun()
        except Exception as e:
            st.error(f"Błąd zapisu: {e}")

    # EDYCJA TABELI
    df = pobierz_dane()
    
    if not df.empty:
        st.info("💡 Kliknij w tabelę, aby edytować. Potem kliknij przycisk poniżej.")
        edytowane = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="editor")
        
        if st.button("💾 ZATWIERDŹ ZMIANY W GOOGLE SHEETS", type="primary"):
            with st.spinner("Aktualizuję chmurę Google..."):
                zapisz_wszystko(edytowane)
            st.success("Gotowe! Arkusz zaktualizowany.")
            st.rerun()

# === ZAKŁADKA 2: KALENDARZ ===
with tab2:
    st.header("📅 Podsumowanie")
    df = pobierz_dane()
    
    if not df.empty:
        # Sumowanie dzienne
        kalendarz = df.groupby('Data')[['Utarg', 'Klienci']].sum().sort_index(ascending=False).reset_index()
        
        col1, col2 = st.columns(2)
        col1.metric("Łączny Utarg", f"{df['Utarg'].sum():.2f} zł")
        col2.metric("Łącznie Klientów", f"{df['Klienci'].sum()}")
        
        st.subheader("Historia dni")
        st.dataframe(
            kalendarz, 
            column_config={"Utarg": st.column_config.NumberColumn(format="%.2f zł")},
            use_container_width=True
        )
        
        st.bar_chart(kalendarz, x="Data", y="Utarg")
