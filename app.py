import streamlit as st
import pandas as pd
from datetime import date
import os

# 1. KONFIGURACJA STRONY
st.set_page_config(page_title="Dziennik Sklepu", page_icon="🛒", layout="wide")
st.title("🛒 Dziennik Sklepu v3")

plik_danych = 'dane.csv'

# --- FUNKCJE POMOCNICZE ---
def laduj_dane():
    if os.path.exists(plik_danych):
        df = pd.read_csv(plik_danych)
        # Upewniamy się, że kolumna Data jest traktowana jako data, a nie tekst
        df['Data'] = pd.to_datetime(df['Data']).dt.date
        return df.sort_values(by=['Data', 'Godzina'], ascending=[False, True])
    else:
        return pd.DataFrame(columns=['Data', 'Godzina', 'Klienci', 'Utarg', 'Srednia'])

def zapisz_dane(df):
    df.to_csv(plik_danych, index=False)

# --- MENU GŁÓWNE (ZAKŁADKI) ---
tab1, tab2 = st.tabs(["✍️ Wpis i Edycja", "📅 Kalendarz i Historia"])

# ==========================================
# ZAKŁADKA 1: WPROWADZANIE I EDYCJA
# ==========================================
with tab1:
    st.header("Bieżąca praca")
    
    # PANEL BOCZNY (Sidebar) wewnątrz tej zakładki
    with st.sidebar:
        st.header("📝 Nowy wpis")
        with st.form("formularz_dodawania"):
            # TERAZ MOŻESZ WYBRAĆ DATĘ!
            wybrana_data = st.date_input("Data wpisu", date.today())
            
            godziny = [f"{h}:00" for h in range(7, 22)]
            wybor_godziny = st.selectbox("Wybierz godzinę", godziny)
            
            klienci = st.number_input("Liczba klientów", min_value=0, step=1)
            utarg = st.number_input("Łączny utarg (zł)", min_value=0.0, step=0.1)
            
            przycisk_dodaj = st.form_submit_button("ZAPISZ WPIS")

    # LOGIKA DODAWANIA
    if przycisk_dodaj:
        srednia = round(utarg / klienci, 2) if klienci > 0 else 0
        
        nowy_wpis = pd.DataFrame([{
            'Data': wybrana_data, # Tu wchodzi wybrana data
            'Godzina': wybor_godziny,
            'Klienci': klienci,
            'Utarg': utarg,
            'Srednia': srednia
        }])
        
        df = laduj_dane()
        df = pd.concat([df, nowy_wpis], ignore_index=True)
        zapisz_dane(df)
        st.success(f"Dodano wpis dla dnia {wybrana_data}!")
        st.rerun()

    # TABELA EDYCJI (Dla wybranego dnia)
    df = laduj_dane()
    if not df.empty:
        st.subheader("🖊️ Ostatnie wpisy (Edytowalne)")
        st.info("Tutaj możesz poprawiać błędy. Zmiany zapisz przyciskiem pod tabelą.")
        
        edytowane_dane = st.data_editor(
            df,
            num_rows="dynamic",
            key="edytor_glowny",
            use_container_width=True
        )

        if st.button("💾 Zapisz zmiany w tabeli", type="primary"):
            zapisz_dane(edytowane_dane)
            st.success("Zaktualizowano bazę danych!")
            st.rerun()
            
        # Przycisk pobierania (Backup)
        csv = edytowane_dane.
