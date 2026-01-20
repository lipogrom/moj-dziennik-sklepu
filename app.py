import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(page_title="Dziennik Sklepu Cloud", page_icon="☁️", layout="wide")
st.title("☁️ Dziennik Sklepu (Google Sheets)")

# --- 2. POŁĄCZENIE Z GOOGLE ---
# 👇👇👇 ID ARKUSZA (Poprawione - bez spacji na końcu) 👇👇👇
ARKUSZ_ID = "13M376ahDkq_8ZdwxDZ5Njn4cTKfO4v78ycMRsowmPMs"

@st.cache_resource
def polacz_z_google():
    """Łączy się z Google Sheets używając ID arkusza"""
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets']
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        # Otwieramy po ID
        sheet = client.open_by_key(ARKUSZ_ID).sheet1
        return sheet
    except Exception as e:
        # Wypisujemy błąd w logach (dla Ciebie), żebyś widział co jest nie tak
        print(f"Błąd połączenia: {e}")
        return None

arkusz = polacz_z_google()

if arkusz is None:
    st.error(f"❌ BŁĄD: Nie mogę otworzyć arkusza o ID: {ARKUSZ_ID}")
    st.info("💡 Rozwiązanie:")
    st.markdown("""
    1. Sprawdź, czy na pewno kliknąłeś **Udostępnij** w tym nowym arkuszu.
    2. Sprawdź, czy wkleiłeś tam e-mail robota:
       (Znajdziesz go w Streamlit -> Settings -> Secrets -> client_email).
    """)
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
        
        # Konwersja liczb (zabezpieczenie przed błędami)
        df['Klienci'] = pd.to_numeric(df['Klienci'], errors='coerce').fillna(0).astype(int)
        df['Utarg'] = pd.to_numeric(df['Utarg'], errors='coerce').fillna(0.0)
        df['Srednia'] = pd.to_numeric(df['Srednia'], errors='coerce').fillna(0.0)
        
        # Sortowanie dat
        if 'Data' in df.columns:
            df['Data'] = pd.to_datetime(df['Data']).dt.date
            df = df.sort_values(by=['Data', 'Godzina'], ascending=[False, True])
        return df
    except Exception as e:
        return pd.DataFrame(columns=['Data', 'Godzina', 'Klienci', 'Utarg', 'Srednia'])

def zapisz_wszystko(df):
    """Nadpisuje cały arkusz (Bezpieczna wersja)"""
    df_save = df.copy()
    
    # --- NAPRAWA PUSTYCH PÓL (Sanityzacja) ---
    df_save['Klienci'] = pd.to_numeric(df_save['Klienci'], errors='coerce').fillna(0).astype(int)
    df_save['Utarg'] = pd.to_numeric(df_save['Utarg'], errors='coerce').fillna(0.0)
    df_save['Srednia'] = pd.to_numeric(df_save['Srednia'], errors='coerce').fillna(0.0)
    df_save = df_save.fillna("") # Reszta pustych na pusty tekst
    # -----------------------------------------

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
    
    # --- A. FORMULARZ DODAWANIA (LEWY PASEK) ---
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
            st.success(f"✅ Zapisano! {wybrana_data} - {wybor_godziny}")
            st.rerun()
        except Exception as e:
            st.error(f"Błąd zapisu: {e}")

    # --- B. EDYCJA I USUWANIE (ŚRODEK) ---
    df = pobierz_dane()
    
    if not df.empty:
        # SEKCJA USUWANIA
        with st.expander("🗑️ NARZĘDZIE USUWANIA (Kliknij, aby rozwinąć)", expanded=False):
            st.warning("Wybierz wpis z listy, aby go trwale usunąć.")
            
            # Lista do wyboru
            lista_wpisow = [
                f"{row['Data']} | Godz: {row['Godzina']} | Utarg: {row['Utarg']} zł | Klientów: {row['Klienci']}" 
                for index, row in df.iterrows()
            ]
            
            wybrany_do_usuniecia = st.selectbox("Wybierz wpis do skasowania:", lista_wpisow)
            
            if st.button("❌ USUŃ WYBRANY WPIS", type="primary"):
                indeks = lista_wpisow.index(wybrany_do_usuniecia)
                df_po_usunieciu = df.drop(df.index[indeks])
                
                with st.spinner("Usuwam wpis z chmury..."):
                    zapisz_wszystko(df_po_usunieciu)
                
                st.success("Wpis usunięty!")
                st.rerun()

        st.divider()

        # SEKCJA TABELI EDYCJI
        st.subheader("🖊️ Tabela (Edycja)")
        edytowane = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="editor")
        
        if st.button("💾 ZATWIERDŹ ZMIANY W TABELI"):
            with st.spinner("Aktualizuję chmurę..."):
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
        
        st.dataframe(kalendarz, use_container_width=True)
        st.bar_chart(kalendarz, x="Data", y="Utarg")
