import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(page_title="Dziennik Sklepu Cloud", page_icon="☁️", layout="wide")
st.title("☁️ Dziennik Sklepu (Google Sheets)")

# --- 2. POŁĄCZENIE Z GOOGLE ---
# Twoje ID arkusza (wpisane na sztywno, bo już wiemy że jest dobre)
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
    st.error(f"❌ BŁĄD: Nie mogę połączyć się z arkuszem.")
    st.warning(f"Upewnij się, że udostępniłeś arkusz dla: robot-sklepowy@copper-frame-484915-g5.iam.gserviceaccount.com")
    st.stop()
else:
    st.toast("Połączono z chmurą!", icon="✅")

# --- 3. FUNKCJE DANYCH ---
def pobierz_dane():
    try:
        dane = arkusz.get_all_records()
        if not dane:
            return pd.DataFrame(columns=['Data', 'Godzina', 'Klienci', 'Utarg', 'Srednia'])
        
        df = pd.DataFrame(dane)
        
        # Konwersja liczb
        df['Klienci'] = pd.to_numeric(df['Klienci'], errors='coerce').fillna(0).astype(int)
        df['Utarg'] = pd.to_numeric(df['Utarg'], errors='coerce').fillna(0.0)
        df['Srednia'] = pd.to_numeric(df['Srednia'], errors='coerce').fillna(0.0)
        
        if 'Data' in df.columns:
            df['Data'] = pd.to_datetime(df['Data']).dt.date
            df = df.sort_values(by=['Data', 'Godzina'], ascending=[False,
