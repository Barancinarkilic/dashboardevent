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
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Genel İstatistikler", "🧑‍🤝‍🧑 Yaş ve Cinsiyet", "✅ Katılım Analizi", "🟣 Darka Üyeliği", "📥 Ham Veri"])

with tab1:
    st.subheader("📌 Genel Katılım Bilgileri")

    total = len(df)
    attended = df['is_attended'].sum()
    misafir_count = df['is_misafir'].sum()
    registered_count = total - misafir_count

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Toplam Kayıt", total)
    col2.metric("Katılan Kişi Sayısı", attended)
    col3.metric("Kayıt Sahibi", registered_count)
    col4.metric("Misafir (Eş/Çocuk)", misafir_count)

    # Person type and attendance analysis
    st.subheader("👥 Kişi Tipi ve Katılım Analizi")
    
    # Safe plotting with error handling
    try:
        fig1 = px.histogram(df, x='kisi_tipi', color='is_attended',
                           barmode='group', title="Kişi Tipi ve Katılım")
        st.plotly_chart(fig1, use_container_width=True)
        
        # Data table for person type and attendance
        person_type_data = df.groupby(['kisi_tipi', 'is_attended']).size().reset_index(name='count')
        st.subheader("📋 Kişi Tipi ve Katılım Verileri")
        st.dataframe(person_type_data)
        
        # CSV download for this graph
        csv = person_type_data.to_csv(index=False).encode('utf-8')
        st.download_button("📄 Kişi Tipi ve Katılım CSV'si", csv, "kisi_tipi_katilim.csv", "text/csv")
    except Exception as e:
        st.error(f"Error creating chart: {str(e)}")

    # General statistics table
    st.subheader("📊 Genel İstatistikler Tablosu")
    general_stats = pd.DataFrame({
        'Metrik': ['Toplam Kayıt', 'Katılan', 'Katılmayan', 'Kayıt Sahibi', 'Misafir'],
        'Sayı': [total, attended, total - attended, registered_count, misafir_count],
        'Oran (%)': [
            f"{(total/total)*100:.1f}" if total > 0 else "0.0",
            f"{(attended/total)*100:.1f}" if total > 0 else "0.0",
            f"{((total-attended)/total)*100:.1f}" if total > 0 else "0.0",
            f"{(registered_count/total)*100:.1f}" if total > 0 else "0.0",
            f"{(misafir_count/total)*100:.1f}" if total > 0 else "0.0"
        ]
    })
    st.dataframe(general_stats)
    
    # CSV download for general statistics
    try:
        csv = general_stats.to_csv(index=False).encode('utf-8')
        st.download_button("📄 Genel İstatistikler CSV'si", csv, "genel_istatistikler.csv", "text/csv")
    except Exception as e:
        st.error(f"Error creating general stats CSV: {str(e)}")

with tab2:
    st.subheader("👤 Yaş ve Cinsiyet Analizi")
    
    # Overview metrics
    if 'yas' in df.columns and not df['yas'].isna().all():
        df_with_age = df.dropna(subset=['yas'])
        df_filtered_age = df_with_age[~df_with_age['yas'].isin([0, 1])]
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Toplam Yaş Verisi", len(df_with_age))
        col2.metric("Filtrelenmiş Veri (0,1 Hariç)", len(df_filtered_age))
        col3.metric("Ortalama Yaş", f"{df_filtered_age['yas'].mean():.1f}" if len(df_filtered_age) > 0 else "N/A")
        col4.metric("Medyan Yaş", f"{df_filtered_age['yas'].median():.1f}" if len(df_filtered_age) > 0 else "N/A")

    # Age distribution analysis
    st.subheader("📈 Yaş Dağılımı Analizi")
    
    # Only show age histogram if we have age data (filtered for age 0 and 1)
    if 'yas' in df.columns and not df['yas'].isna().all():
        try:
            # Filter out age 0 and 1 for age distribution
            df_age_filtered = df.dropna(subset=['yas'])
            df_age_filtered = df_age_filtered[~df_age_filtered['yas'].isin([0, 1])]
            
            if len(df_age_filtered) > 0:
                fig2 = px.histogram(df_age_filtered, x='yas', nbins=20, title="Yaş Dağılımı (0 ve 1 Hariç)")
                st.plotly_chart(fig2, use_container_width=True)
                
                # Age distribution data table
                age_stats = df_age_filtered['yas'].describe()
                age_data = pd.DataFrame({
                    'İstatistik': ['Sayı', 'Ortalama', 'Std', 'Min', '25%', '50%', '75%', 'Max'],
                    'Değer': [age_stats['count'], age_stats['mean'], age_stats['std'], 
                             age_stats['min'], age_stats['25%'], age_stats['50%'], 
                             age_stats['75%'], age_stats['max']]
                })
                st.subheader("📋 Yaş Dağılımı İstatistikleri")
                st.dataframe(age_data)
                
                # CSV download for age distribution
                csv = df_age_filtered[['yas']].to_csv(index=False).encode('utf-8')
                st.download_button("📄 Yaş Dağılımı CSV'si", csv, "yas_dagilimi.csv", "text/csv")
            else:
                st.info("Yaş 0 ve 1 dışında veri bulunamadı")
        except Exception as e:
            st.error(f"Error creating age chart: {str(e)}")

    # Gender-age analysis
    st.subheader("👥 Cinsiyet ve Yaş Analizi")
    
    # Gender-age box plot (filtered for age 0 and 1)
    if 'gender' in df.columns and 'yas' in df.columns:
        try:
            df_gender_age = df.dropna(subset=['yas', 'gender'])
            df_gender_age = df_gender_age[~df_gender_age['yas'].isin([0, 1])]
            
            if len(df_gender_age) > 0:
                fig3 = px.box(df_gender_age, x='gender', y='yas', 
                             points='all', title="Cinsiyete Göre Yaş Dağılımı (0 ve 1 Hariç)")
                st.plotly_chart(fig3, use_container_width=True)
                
                # Gender-age statistics table
                gender_age_stats = df_gender_age.groupby('gender')['yas'].agg(['count', 'mean', 'median', 'std']).reset_index()
                gender_age_stats.columns = ['Cinsiyet', 'Sayı', 'Ortalama', 'Medyan', 'Standart Sapma']
                st.subheader("📋 Cinsiyet-Yaş İstatistikleri")
                st.dataframe(gender_age_stats)
                
                # CSV download for gender-age
                csv = df_gender_age[['gender', 'yas']].to_csv(index=False).encode('utf-8')
                st.download_button("📄 Cinsiyet-Yaş CSV'si", csv, "cinsiyet_yas.csv", "text/csv")
            else:
                st.info("Cinsiyet ve yaş verisi bulunamadı")
        except Exception as e:
            st.error(f"Error creating gender-age chart: {str(e)}")

    # Gender-attendance analysis
    st.subheader("👥 Cinsiyet ve Katılım Analizi")
    
    # Gender-attendance histogram (no age filtering)
    if 'gender' in df.columns:
        try:
            fig4 = px.histogram(df, x='gender', color='is_attended', 
                               barmode='group', title="Cinsiyet ve Katılım")
            st.plotly_chart(fig4, use_container_width=True)
            
            # Gender-attendance data table
            gender_attendance_data = df.groupby(['gender', 'is_attended']).size().reset_index(name='count')
            st.subheader("📋 Cinsiyet-Katılım Verileri")
            st.dataframe(gender_attendance_data)
            
            # CSV download for gender-attendance
            csv = gender_attendance_data.to_csv(index=False).encode('utf-8')
            st.download_button("📄 Cinsiyet-Katılım CSV'si", csv, "cinsiyet_katilim.csv", "text/csv")
        except Exception as e:
            st.error(f"Error creating gender-attendance chart: {str(e)}")

with tab3:
    st.subheader("✅ Katılım Analizi")
    
    # Attendance overview
    total = len(df)
    attended = df['is_attended'].sum()
    not_attended = total - attended
    attendance_rate = (attended / total * 100) if total > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Toplam Kayıt", total)
    col2.metric("Katılan", attended)
    col3.metric("Katılmayan", not_attended)
    col4.metric("Katılım Oranı", f"{attendance_rate:.1f}%")
    
    # Attendance by person type
    st.subheader("👥 Kişi Tipine Göre Katılım")
    try:
        fig_attendance_type = px.histogram(df, x='kisi_tipi', color='is_attended',
                                          barmode='group', title="Kişi Tipine Göre Katılım")
        st.plotly_chart(fig_attendance_type, use_container_width=True)
        
        # Data table
        attendance_type_data = df.groupby(['kisi_tipi', 'is_attended']).size().reset_index(name='count')
        st.subheader("📋 Kişi Tipi-Katılım Verileri")
        st.dataframe(attendance_type_data)
        
        # CSV download
        csv = attendance_type_data.to_csv(index=False).encode('utf-8')
        st.download_button("📄 Kişi Tipi-Katılım CSV'si", csv, "kisi_tipi_katilim_detay.csv", "text/csv")
    except Exception as e:
        st.error(f"Error creating attendance type chart: {str(e)}")
    
    # Attendance by gender
    st.subheader("👥 Cinsiyete Göre Katılım")
    if 'gender' in df.columns:
        try:
            fig_attendance_gender = px.histogram(df, x='gender', color='is_attended',
                                                barmode='group', title="Cinsiyete Göre Katılım")
            st.plotly_chart(fig_attendance_gender, use_container_width=True)
            
            # Data table
            attendance_gender_data = df.groupby(['gender', 'is_attended']).size().reset_index(name='count')
            st.subheader("📋 Cinsiyet-Katılım Verileri")
            st.dataframe(attendance_gender_data)
            
            # CSV download
            csv = attendance_gender_data.to_csv(index=False).encode('utf-8')
            st.download_button("📄 Cinsiyet-Katılım CSV'si", csv, "cinsiyet_katilim_detay.csv", "text/csv")
        except Exception as e:
            st.error(f"Error creating attendance gender chart: {str(e)}")
    
    # Attendance by age (filtered for age 0 and 1)
    st.subheader("📈 Yaşa Göre Katılım")
    if 'yas' in df.columns and not df['yas'].isna().all():
        try:
            df_age_attendance = df.dropna(subset=['yas'])
            df_age_attendance = df_age_attendance[~df_age_attendance['yas'].isin([0, 1])]
            
            if len(df_age_attendance) > 0:
                fig_attendance_age = px.box(df_age_attendance, x='is_attended', y='yas',
                                           title="Katılım Durumuna Göre Yaş Dağılımı (0 ve 1 Hariç)")
                st.plotly_chart(fig_attendance_age, use_container_width=True)
                
                # Age-attendance statistics table
                age_attendance_stats = df_age_attendance.groupby('is_attended')['yas'].agg(['count', 'mean', 'median', 'std']).reset_index()
                age_attendance_stats.columns = ['Katılım', 'Sayı', 'Ortalama', 'Medyan', 'Standart Sapma']
                st.subheader("📋 Yaş-Katılım İstatistikleri")
                st.dataframe(age_attendance_stats)
                
                # CSV download
                csv = df_age_attendance[['yas', 'is_attended']].to_csv(index=False).encode('utf-8')
                st.download_button("📄 Yaş-Katılım CSV'si", csv, "yas_katilim.csv", "text/csv")
            else:
                st.info("Yaş 0 ve 1 dışında veri bulunamadı")
        except Exception as e:
            st.error(f"Error creating attendance age chart: {str(e)}")
    
    # Attendance by Darka membership
    st.subheader("🟣 Darka Üyeliğine Göre Katılım")
    if 'darka_uyesi' in df.columns:
        try:
            fig_attendance_darka = px.histogram(df, x='darka_uyesi', color='is_attended',
                                               barmode='group', title="Darka Üyeliğine Göre Katılım")
            st.plotly_chart(fig_attendance_darka, use_container_width=True)
            
            # Data table
            attendance_darka_data = df.groupby(['darka_uyesi', 'is_attended']).size().reset_index(name='count')
            st.subheader("📋 Darka-Katılım Verileri")
            st.dataframe(attendance_darka_data)
            
            # CSV download
            csv = attendance_darka_data.to_csv(index=False).encode('utf-8')
            st.download_button("📄 Darka-Katılım CSV'si", csv, "darka_katilim.csv", "text/csv")
        except Exception as e:
            st.error(f"Error creating attendance Darka chart: {str(e)}")
    
    # Detailed attendance data
    st.subheader("📋 Katılım Detayları")
    attendance_df = df[['is_attended', 'kisi_tipi'] + ([col for col in ['gender', 'yas', 'darka_uyesi'] if col in df.columns])]
    st.dataframe(attendance_df)
    
    # CSV download for detailed attendance data
    try:
        csv = attendance_df.to_csv(index=False).encode('utf-8')
        st.download_button("📄 Katılım Detay CSV'si", csv, "katilim_detay.csv", "text/csv")
    except Exception as e:
        st.error(f"Error creating detailed attendance CSV: {str(e)}")

with tab4:
    st.subheader("🟣 Darka Üyeliği Analizi")
    
    # Overview metrics
    if 'darka_uyesi' in df.columns:
        darka_counts = df['darka_uyesi'].value_counts()
        total_darka = len(df)
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Toplam Kayıt", total_darka)
        col2.metric("Darka Üyesi", darka_counts.get('Evet', 0))
        col3.metric("Darka Üyesi Değil", darka_counts.get('Hayır', 0))
        col4.metric("Bilinmiyor", darka_counts.get('Bilinmiyor', 0))

    # Darka membership distribution
    st.subheader("📊 Darka Üyeliği Dağılımı")
    if 'darka_uyesi' in df.columns:
        try:
            fig5 = px.histogram(df, x='darka_uyesi', title="Darka Üyesi Dağılımı")
            st.plotly_chart(fig5, use_container_width=True)
            
            # Darka membership data table
            darka_data = df['darka_uyesi'].value_counts().reset_index()
            darka_data.columns = ['Darka Üyeliği', 'Sayı']
            darka_data['Oran (%)'] = (darka_data['Sayı'] / len(df) * 100).round(1)
            st.subheader("📋 Darka Üyeliği Verileri")
            st.dataframe(darka_data)
            
            # CSV download
            csv = darka_data.to_csv(index=False).encode('utf-8')
            st.download_button("📄 Darka Üyeliği CSV'si", csv, "darka_uyesi.csv", "text/csv")
        except Exception as e:
            st.error(f"Error creating Darka membership chart: {str(e)}")

        # Darka membership and gender
        st.subheader("👥 Darka Üyeliği ve Cinsiyet")
        if 'gender' in df.columns:
            try:
                fig6 = px.histogram(df, x='darka_uyesi', color='gender', 
                                   barmode='group', title="Darka Üyeliği ve Cinsiyet")
                st.plotly_chart(fig6, use_container_width=True)
                
                # Data table
                darka_gender_data = df.groupby(['darka_uyesi', 'gender']).size().reset_index(name='count')
                st.subheader("📋 Darka-Cinsiyet Verileri")
                st.dataframe(darka_gender_data)
                
                # CSV download
                csv = darka_gender_data.to_csv(index=False).encode('utf-8')
                st.download_button("📄 Darka-Cinsiyet CSV'si", csv, "darka_cinsiyet.csv", "text/csv")
            except Exception as e:
                st.error(f"Error creating Darka-gender chart: {str(e)}")

        # Darka membership and age (filtered for age 0 and 1)
        st.subheader("📈 Darka Üyeliği ve Yaş")
        if 'yas' in df.columns:
            try:
                df_darka_age = df.dropna(subset=['yas'])
                df_darka_age = df_darka_age[~df_darka_age['yas'].isin([0, 1])]
                
                if len(df_darka_age) > 0:
                    fig7 = px.box(df_darka_age, x='darka_uyesi', y='yas', 
                                 title="Darka Üyeliğine Göre Yaş Dağılımı (0 ve 1 Hariç)")
                    st.plotly_chart(fig7, use_container_width=True)
                    
                    # Darka-age statistics table
                    darka_age_stats = df_darka_age.groupby('darka_uyesi')['yas'].agg(['count', 'mean', 'median', 'std']).reset_index()
                    darka_age_stats.columns = ['Darka Üyeliği', 'Sayı', 'Ortalama', 'Medyan', 'Standart Sapma']
                    st.subheader("📋 Darka-Yaş İstatistikleri")
                    st.dataframe(darka_age_stats)
                    
                    # CSV download
                    csv = df_darka_age[['darka_uyesi', 'yas']].to_csv(index=False).encode('utf-8')
                    st.download_button("📄 Darka-Yaş CSV'si", csv, "darka_yas.csv", "text/csv")
                else:
                    st.info("Yaş 0 ve 1 dışında veri bulunamadı")
            except Exception as e:
                st.error(f"Error creating Darka-age chart: {str(e)}")

        # Darka membership and attendance
        st.subheader("✅ Darka Üyeliği ve Katılım")
        try:
            fig8 = px.histogram(df, x='darka_uyesi', color='is_attended', 
                               barmode='group', title="Katılım ve Darka Üyeliği")
            st.plotly_chart(fig8, use_container_width=True)
            
            # Data table
            darka_attendance_data = df.groupby(['darka_uyesi', 'is_attended']).size().reset_index(name='count')
            st.subheader("📋 Darka-Katılım Verileri")
            st.dataframe(darka_attendance_data)
            
            # CSV download
            csv = darka_attendance_data.to_csv(index=False).encode('utf-8')
            st.download_button("📄 Darka-Katılım CSV'si", csv, "darka_katilim_detay.csv", "text/csv")
        except Exception as e:
            st.error(f"Error creating Darka-attendance chart: {str(e)}")

with tab5:
    st.subheader("📥 Ham Veri ve İndirme")
    
    # Data overview
    col1, col2, col3 = st.columns(3)
    col1.metric("Toplam Satır", len(df))
    col2.metric("Toplam Sütun", len(df.columns))
    col3.metric("Eksik Veri Oranı", f"{(df.isnull().sum().sum() / (len(df) * len(df.columns)) * 100):.1f}%")
    
    # Column information
    st.subheader("📋 Sütun Bilgileri")
    column_info = pd.DataFrame({
        'Sütun': df.columns,
        'Veri Tipi': df.dtypes.astype(str),
        'Eksik Veri': df.isnull().sum(),
        'Benzersiz Değer': df.nunique()
    })
    st.dataframe(column_info)
    
    # Raw data
    st.subheader("📊 Ham Veri")
    st.dataframe(df)
    
    # CSV download for raw data
    try:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📄 Ham Veri CSV'si", csv, "ham_veri.csv", "text/csv")
    except Exception as e:
        st.error(f"Error creating raw data CSV: {str(e)}")
    
    # Missing data analysis
    st.subheader("🔍 Eksik Veri Analizi")
    missing_data = df.isnull().sum().reset_index()
    missing_data.columns = ['Sütun', 'Eksik Veri Sayısı']
    missing_data['Eksik Veri Oranı (%)'] = (missing_data['Eksik Veri Sayısı'] / len(df) * 100).round(1)
    st.dataframe(missing_data)
    
    # CSV download for missing data analysis
    try:
        csv = missing_data.to_csv(index=False).encode('utf-8')
        st.download_button("📄 Eksik Veri Analizi CSV'si", csv, "eksik_veri_analizi.csv", "text/csv")
    except Exception as e:
        st.error(f"Error creating missing data CSV: {str(e)}")
