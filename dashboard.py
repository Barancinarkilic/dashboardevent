import json
import pandas as pd
import streamlit as st
import plotly.express as px
from airtable import Airtable
import numpy as np

# Airtable credentials
API_KEY = "patdZWDEHqY2ZV0a4.81026ce468cfc36bbf9f400b282664e7869655d36ded3fec82a58bce4746c6d5"
BASE_ID = "appjsVC6vEzetd4Ao"
TABLE_NAME = "exploded"

# Get Airtable data with error handling
try:
    airtable = Airtable(BASE_ID, TABLE_NAME, API_KEY)
    records = airtable.get_all()
    
    # Convert to DataFrame
    df = pd.DataFrame(records)
    
    if 'fields' in df.columns:
        fields_df = pd.json_normalize(df['fields'])
        df = pd.concat([df.drop('fields', axis=1), fields_df], axis=1)
    
    # Handle duplicate columns properly
    df = df.loc[:, ~df.columns.duplicated()]
    
    # Drop the first 'id' column (not the Airtable row ID) if it exists
    if 'id' in df.columns:
        df = df.drop(columns=['id'], errors='ignore')
    
    # Clean and prepare data
    # Convert is_attended to boolean, handling NaN values
    if 'is_attended' in df.columns:
        df['is_attended'] = df['is_attended'].fillna(False).astype(bool)
    else:
        df['is_attended'] = False
    
    # Define if row is a misafir (telefon_numarasi is NaN)
    if 'telefon_numarasi' in df.columns:
        df['is_misafir'] = df['telefon_numarasi'].isna()
    else:
        df['is_misafir'] = False
    
    df['kisi_tipi'] = df['is_misafir'].apply(lambda x: 'Eş/Çocuk' if x else 'Kayıt Sahibi')
    
    # Handle age column - convert to numeric, handle errors
    if 'yas' in df.columns:
        df['yas'] = pd.to_numeric(df['yas'], errors='coerce')
    else:
        df['yas'] = np.nan
    
    # Handle gender column - ensure it exists
    if 'gender' not in df.columns:
        df['gender'] = 'Bilinmiyor'
    
    # Handle darka_uyesi column - ensure it exists
    if 'darka_uyesi' not in df.columns:
        df['darka_uyesi'] = 'Bilinmiyor'
    
    # Clean gender data
    df['gender'] = df['gender'].fillna('Bilinmiyor')
    df['darka_uyesi'] = df['darka_uyesi'].fillna('Bilinmiyor')
    
    print(f"Data loaded successfully. Shape: {df.shape}")
    print(f"Columns: {df.columns.tolist()}")
    
except Exception as e:
    st.error(f"Error loading data: {str(e)}")
    st.stop()

# Title
st.set_page_config(page_title="Etkinlik Dashboard", layout="wide")
st.title("🎉 Etkinlik Katılımcı Dashboard'u")

# Tabs for breakdown
tab1, tab2, tab3, tab4 = st.tabs(["📊 Genel İstatistikler", "🧑‍🤝‍🧑 Yaş ve Cinsiyet", "🟣 Darka Üyeliği", "📥 Ham Veri"])

with tab1:
    st.subheader("📌 Genel Katılım Bilgileri")

    total = len(df)
    attended = df['is_attended'].sum()
    misafir_count = df['is_misafir'].sum()

    col1, col2, col3 = st.columns(3)
    col1.metric("Toplam Kayıt", total)
    col2.metric("Katılan Kişi Sayısı", attended)
    col3.metric("Misafir (Eş/Çocuk) Sayısı", misafir_count)

    # Safe plotting with error handling
    try:
        fig1 = px.histogram(df, x='kisi_tipi', color='is_attended',
                           barmode='group', title="Kişi Tipi ve Katılım")
        st.plotly_chart(fig1, use_container_width=True)
    except Exception as e:
        st.error(f"Error creating chart: {str(e)}")

with tab2:
    st.subheader("👤 Yaş Dağılımı ve Cinsiyet Kırılımı")

    # Only show age histogram if we have age data
    if 'yas' in df.columns and not df['yas'].isna().all():
        try:
            fig2 = px.histogram(df.dropna(subset=['yas']), x='yas', nbins=20, title="Yaş Dağılımı")
            st.plotly_chart(fig2, use_container_width=True)
        except Exception as e:
            st.error(f"Error creating age chart: {str(e)}")

    # Gender-age box plot
    if 'gender' in df.columns and 'yas' in df.columns:
        try:
            fig3 = px.box(df.dropna(subset=['yas', 'gender']), x='gender', y='yas', 
                         points='all', title="Cinsiyete Göre Yaş Dağılımı")
            st.plotly_chart(fig3, use_container_width=True)
        except Exception as e:
            st.error(f"Error creating gender-age chart: {str(e)}")

    # Gender-attendance histogram
    if 'gender' in df.columns:
        try:
            fig4 = px.histogram(df, x='gender', color='is_attended', 
                               barmode='group', title="Cinsiyet ve Katılım")
            st.plotly_chart(fig4, use_container_width=True)
        except Exception as e:
            st.error(f"Error creating gender-attendance chart: {str(e)}")

with tab3:
    st.subheader("🟣 Darka Üyeliği Analizi")

    if 'darka_uyesi' in df.columns:
        try:
            fig5 = px.histogram(df, x='darka_uyesi', title="Darka Üyesi Dağılımı")
            st.plotly_chart(fig5, use_container_width=True)
        except Exception as e:
            st.error(f"Error creating Darka membership chart: {str(e)}")

        # Darka membership and gender
        if 'gender' in df.columns:
            try:
                fig6 = px.histogram(df, x='darka_uyesi', color='gender', 
                                   barmode='group', title="Darka Üyeliği ve Cinsiyet")
                st.plotly_chart(fig6, use_container_width=True)
            except Exception as e:
                st.error(f"Error creating Darka-gender chart: {str(e)}")

        # Darka membership and age
        if 'yas' in df.columns:
            try:
                fig7 = px.box(df.dropna(subset=['yas']), x='darka_uyesi', y='yas', 
                             title="Darka Üyeliğine Göre Yaş Dağılımı")
                st.plotly_chart(fig7, use_container_width=True)
            except Exception as e:
                st.error(f"Error creating Darka-age chart: {str(e)}")

        # Darka membership and attendance
        try:
            fig8 = px.histogram(df, x='darka_uyesi', color='is_attended', 
                               barmode='group', title="Katılım ve Darka Üyeliği")
            st.plotly_chart(fig8, use_container_width=True)
        except Exception as e:
            st.error(f"Error creating Darka-attendance chart: {str(e)}")

with tab4:
    st.subheader("📥 Ham Veri ve İndirme")

    st.dataframe(df)
    
    try:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📄 CSV olarak indir", csv, "katilimcilar.csv", "text/csv")
    except Exception as e:
        st.error(f"Error creating CSV download: {str(e)}")
