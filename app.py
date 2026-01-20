import streamlit as st
import pandas as pd
from datetime import date
import os

# 1. KONFIGURACJA STRONY
st.set_page_config(page_title="Dziennik Sklepu", page_icon="🛒")

st.title("🛒 Dziennik Sklepu")
st.write("Witaj w swoim cyfrowym zeszycie!")

# 2. MECHANIZM DANYCH (Lokalny plik CSV)
plik_danych = 'dane.csv'

# Funkcja do ładowania danych
def laduj_dane():
    if os.path.exists(plik_danych):
        return pd.read_csv(plik_danych)
    else:
        return pd.DataFrame(columns=['Data', 'Godzina', 'Klienci', 'Utarg', 'Srednia'])

# 3. INTERFEJS (Panel boczny do wprowadzania)
st.sidebar.header("📝 Dodaj nowy wpis")

godziny = [f"{h}:00" for h in range(7, 22)]
wybor_godziny = st.sidebar.selectbox("Wybierz godzinę", godziny)
klienci = st.sidebar.number_input("Liczba klientów", min_value=0, step=1)
utarg = st.sidebar.number_input("Łączny utarg (zł)", min_value=0.0, step=0.1)

if st.sidebar.button("ZAPISZ WPIS"):
    # Obliczenia
    srednia = round(utarg / klienci, 2) if klienci > 0 else 0
    dzis = date.today().strftime("%Y-%m-%d")
    
    # Tworzenie nowego wiersza
    nowy_wpis = pd.DataFrame([{
        'Data': dzis,
        'Godzina': wybor_godziny,
        'Klienci': klienci,
        'Utarg': utarg,
        'Srednia': srednia
    }])
    
    # Zapis do pliku
    df = laduj_dane()
    df = pd.concat([df, nowy_wpis], ignore_index=True)
    df.to_csv(plik_danych, index=False)
    st.sidebar.success("Zapisano pomyślnie!")

# 4. GŁÓWNY EKRAN (Tabela i Wykresy)
df = laduj_dane()

if not df.empty:
    st.subheader("📊 Twoje dzisiejsze wyniki")
    st.dataframe(df)

    # Proste podsumowanie
    st.metric("Całkowity utarg", f"{df['Utarg'].sum()} zł")
    
    # Wykres
    st.subheader("📈 Analiza godzinowa")
    wykres_dane = df.groupby('Godzina')['Utarg'].sum()
    st.bar_chart(wykres_dane)
    
    # Przycisk pobierania (Ważne w chmurze!)
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="💾 Pobierz dane jako CSV",
        data=csv,
        file_name='moj_utarg.csv',
        mime='text/csv',
    )
else:
    st.info("Baza jest pusta. Użyj panelu po lewej, aby dodać pierwszy wpis.")
