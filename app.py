import streamlit as st
import google.generativeai as genai
import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from geopy.geocoders import Nominatim
import datetime
import time

# ================= AYARLAR =================
# ================= AYARLAR =================
try:
    
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    
    st.error("⚠️ API Anahtarı bulunamadı! Lütfen Streamlit Cloud 'Secrets' ayarlarını yapın.")
    st.stop()

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

# ================= SAYFA AYARLARI =================
st.set_page_config(page_title="İklim Analiz Sistemi", layout="wide", page_icon="🌍")

# ================= FONKSİYONLAR =================

@st.cache_data
def koordinat_bul(sehir_adi):
    geolocator = Nominatim(user_agent="muhendislik_istasyonu_v27_final_fix")
    try:
        time.sleep(1)
        location = geolocator.geocode(sehir_adi)
        if location:
            return location.latitude, location.longitude, location.address
        else:
            return None, None, None
    except:
        return None, None, None

def anlik_durum_cek(lat, lon):
    openmeteo = openmeteo_requests.Client()
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": ["temperature_2m", "relative_humidity_2m", "apparent_temperature", "is_day", "weather_code", "wind_speed_10m"],
        "timezone": "auto"
    }
    responses = openmeteo.weather_api(url, params=params)
    response = responses[0]
    current = response.Current()
    
    sicaklik = current.Variables(0).Value()
    nem = current.Variables(1).Value()
    hissedilen = current.Variables(2).Value()
    gunduz_mu = current.Variables(3).Value()
    kod = current.Variables(4).Value()
    ruzgar_hiz = current.Variables(5).Value()
    
    utc_simdi = datetime.datetime.now(datetime.timezone.utc)
    offset_saniye = response.UtcOffsetSeconds()
    yerel_saat = utc_simdi + datetime.timedelta(seconds=offset_saniye)
    
    return sicaklik, nem, hissedilen, gunduz_mu, ruzgar_hiz, yerel_saat, int(kod)

@st.cache_data
def gecmis_veri_cek_v2(lat, lon, baslangic, bitis):
    cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)
    
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": baslangic,
        "end_date": bitis,
        "daily": ["temperature_2m_max", "temperature_2m_min", "temperature_2m_mean", "precipitation_sum", "wind_speed_10m_max"],
        "timezone": "auto"
    }
    responses = openmeteo.weather_api(url, params=params)
    daily = responses[0].Daily()
    
    data = {"date": pd.date_range(
        start=pd.to_datetime(daily.Time(), unit="s", utc=True),
        end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
        freq=pd.Timedelta(seconds=daily.Interval()),
        inclusive="left"
    )}
    data["max"] = daily.Variables(0).ValuesAsNumpy()
    data["min"] = daily.Variables(1).ValuesAsNumpy()
    data["mean"] = daily.Variables(2).ValuesAsNumpy()
    data["yagis"] = daily.Variables(3).ValuesAsNumpy()
    data["ruzgar"] = daily.Variables(4).ValuesAsNumpy()
    
    return pd.DataFrame(data)

@st.cache_data
def tahmin_veri_cek(lat, lon):
    openmeteo = openmeteo_requests.Client()
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": ["temperature_2m_max", "temperature_2m_min", "precipitation_probability_max", "wind_speed_10m_max", "weather_code"],
        "forecast_days": 7,
        "timezone": "auto"
    }
    responses = openmeteo.weather_api(url, params=params)
    daily = responses[0].Daily()
    
    data = {"date": pd.date_range(
        start=pd.to_datetime(daily.Time(), unit="s", utc=True),
        end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
        freq=pd.Timedelta(seconds=daily.Interval()),
        inclusive="left"
    )}
    data["max"] = daily.Variables(0).ValuesAsNumpy()
    data["min"] = daily.Variables(1).ValuesAsNumpy()
    data["yagis_ihtimal"] = daily.Variables(2).ValuesAsNumpy()
    data["ruzgar"] = daily.Variables(3).ValuesAsNumpy()
    data["kod"] = daily.Variables(4).ValuesAsNumpy()
    
    return pd.DataFrame(data)

@st.cache_data
def teknik_analiz_olustur(prompt):
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Rapor oluşturulamadı. (Hata: {e})"

# --- İKON VE DURUM METİNLERİ 
def kod_cozucu(kod, gunduz_mu=True):
    if kod == 0: 
        return "☀️" if gunduz_mu else "🌙", "Açık"
    if 1 <= kod <= 2: 
        return "🌤️" if gunduz_mu else "☁️", "Parçalı Bulutlu"
    if kod == 3: 
        return "☁️", "Bulutlu"
    if 45 <= kod <= 48: 
        return "☁️", "Çok Bulutlu" 
    if 51 <= kod <= 55: 
        return "🌦️", "Hafif Yağmur"
    if 56 <= kod <= 57: 
        return "🌨️", "Karla Karışık"
    if 61 <= kod <= 65: 
        return "🌧️", "Yağmurlu"
    if 66 <= kod <= 67: 
        return "🌨️", "Donan Yağmur"
    if 71 <= kod <= 77: 
        return "❄️", "Karlı"
    if 80 <= kod <= 82: 
        return "☔", "Sağanak"
    if 95 <= kod <= 99: 
        return "⛈️", "Gök Gürültülü"
    return "❓", "Bilinmiyor"

def get_theme_colors(tema):
    if "dark" in tema: return "rgba(0,0,0,0)", "white"
    else: return "#FFFFFF", "black"

def interaktif_grafik(df, sehir_adi, renk_max, renk_min, renk_yagis, grafik_temasi, font_color, bg_color):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=df['date'], y=df['max'], name="Max Sıcaklık", line=dict(color=renk_max, width=3)), secondary_y=False)
    fig.add_trace(go.Scatter(x=df['date'], y=df['min'], name="Min Sıcaklık", line=dict(color=renk_min, width=3, dash='dot')), secondary_y=False)
    fig.add_trace(go.Bar(x=df['date'], y=df['yagis'], name="Yağış (mm)", marker_color=renk_yagis, opacity=0.5), secondary_y=True)
    
    fig.update_layout(
        title=dict(text=f'<b>{sehir_adi}</b> Geçmiş Analizi', font=dict(color=font_color, size=20)),
        template=grafik_temasi, 
        hovermode="x unified", 
        height=400, 
        legend=dict(orientation="h", y=1.1, x=0.5, font=dict(color=font_color)),
        paper_bgcolor=bg_color, 
        plot_bgcolor=bg_color, 
        font=dict(color=font_color)
    )
    fig.update_xaxes(title_font=dict(color=font_color), tickfont=dict(color=font_color))
    fig.update_yaxes(title_font=dict(color=font_color), tickfont=dict(color=font_color))
    return fig

def ruzgar_grafigi(df, renk_ruzgar, plotly_tema, font_color, bg_color):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['date'], y=df['ruzgar'], name="Rüzgar Hızı", fill='tozeroy', line=dict(color=renk_ruzgar)))
    
    fig.update_layout(
        title=dict(text="Rüzgar Analizi (km/h)", font=dict(color=font_color, size=20)),
        template=plotly_tema, 
        height=350, 
        paper_bgcolor=bg_color, 
        plot_bgcolor=bg_color, 
        font=dict(color=font_color),
        xaxis=dict(title_font=dict(color=font_color), tickfont=dict(color=font_color)),
        yaxis=dict(title_font=dict(color=font_color), tickfont=dict(color=font_color))
    )
    return fig

def tahmin_grafigi(df, sehir_adi, tema, font, bg):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['date'], y=df['max'], name="Gündüz", line=dict(color='#FF4B4B', width=4)))
    fig.add_trace(go.Scatter(x=df['date'], y=df['min'], name="Gece", line=dict(color='#4B4BFF', width=4)))
    fig.add_trace(go.Scatter(x=df['date'].tolist() + df['date'].tolist()[::-1], y=df['max'].tolist() + df['min'].tolist()[::-1], fill='toself', fillcolor='rgba(100, 100, 100, 0.2)', line=dict(color='rgba(255,255,255,0)'), name='Aralık', showlegend=False))
    
    fig.update_layout(
        title=dict(text=f"7 Günlük Tahmin: {sehir_adi}", font=dict(color=font, size=20)),
        template=tema, 
        paper_bgcolor=bg, 
        plot_bgcolor=bg, 
        font=dict(color=font), 
        height=400, 
        hovermode="x unified",
        legend=dict(font=dict(color=font)),
        xaxis=dict(title_font=dict(color=font), tickfont=dict(color=font)),
        yaxis=dict(title_font=dict(color=font), tickfont=dict(color=font))
    )
    return fig

# ================= ARAYÜZ =================

if 'analiz_yapildi' not in st.session_state: st.session_state.analiz_yapildi = False
if 'df_gecmis' not in st.session_state: st.session_state.df_gecmis = None
if 'df_tahmin' not in st.session_state: st.session_state.df_tahmin = None
if 'adres' not in st.session_state: st.session_state.adres = ""
if 'baslangic' not in st.session_state: st.session_state.baslangic = None
if 'bitis' not in st.session_state: st.session_state.bitis = None

with st.sidebar:
    st.title("Kontrol Paneli")
    mod_secimi = st.radio("İşlem Modu:", ["Geçmiş Veri Analizi", "Hava Tahmini"], index=0)
    st.markdown("---")
    
    secilen_mod = st.radio("Arayüz:", ["Karanlık", "Aydınlık"], index=0)
    if secilen_mod == "Karanlık":
        st.markdown("""
        <style>
        .stApp { background-color: #0E1117; color: white; }
        section[data-testid="stSidebar"] { background-color: #262730; }
        section[data-testid="stSidebar"] * { color: white !important; }
        section[data-testid="stSidebar"] input { color: black !important; }
        header[data-testid="stHeader"] { background-color: #0E1117; }
        </style>
        """, unsafe_allow_html=True)
        plotly_tema, font_color, bg_color = "plotly_dark", "white", "rgba(0,0,0,0)"
    else:
        st.markdown("""
        <style>
        .stApp { background-color: #FFFFFF; color: black; }
        section[data-testid="stSidebar"] { background-color: #F0F2F6; }
        section[data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label { color: black !important; }
        header[data-testid="stHeader"] { background-color: #FFFFFF; }
        </style>
        """, unsafe_allow_html=True)
        plotly_tema, font_color, bg_color = "plotly_white", "black", "rgba(255,255,255,1)"
    
    st.subheader("Konum Seçimi")
    girilen_sehir = st.text_input("Şehir:", value="Diyarbakır")
    
    
    if mod_secimi == "Geçmiş Veri Analizi":
        st.subheader("Tarih Aralığı")
        bugun = datetime.date.today()
        gecen_yil = bugun - datetime.timedelta(days=365)
        tarih_araligi = st.date_input("Dönem:", (gecen_yil, bugun), max_value=bugun)
        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            renk_max = st.color_picker("Max", "#FF4B4B")
            renk_ruzgar = st.color_picker("Rüzgar", "#FFA500")
        with c2:
            renk_min = st.color_picker("Min", "#4B4BFF")
            renk_yagis = st.color_picker("Yağış", "#00FF00")
        baslat = st.button("Analizi Başlat", type="primary")
        
    else:
        
        st.markdown("---")
        st.info("Önümüzdeki 7 günün tahmin verileri ve teknik değerlendirme.")
        baslat = st.button("Tahmini Getir", type="primary")
    
    st.markdown("---")
    st.caption("**Geliştirici:** Mücahid Kerem")
    st.caption("**Veri Altyapısı:** Open-Meteo API")

if baslat:
    lat, lon, tam_adres = koordinat_bul(girilen_sehir)
    if lat:
        st.session_state.adres = tam_adres
        try:
            sicaklik, nem, his, gunduz, ruzgar, saat, kod = anlik_durum_cek(lat, lon)
            ikon, durum_metni = kod_cozucu(kod, gunduz)
            arkaplan = "linear-gradient(to right, #4facfe 0%, #00f2fe 100%)" if gunduz else "linear-gradient(to right, #434343 0%, black 100%)"
            
            st.markdown(f"""
            <div style="padding: 20px; border-radius: 15px; background: {arkaplan}; color: white; box-shadow: 0 4px 15px rgba(0,0,0,0.2); margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h2 style="margin:0; font-size: 2rem;">{tam_adres.split(",")[0]}</h2>
                        <p style="margin:0; opacity: 0.9;">{tam_adres}</p>
                        <h3 style="margin-top: 10px;">{saat.strftime('%H:%M')} <span style="font-size: 0.8em; opacity: 0.8;">(Yerel Saat)</span></h3>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 4rem;">{ikon}</div>
                        <div style="font-size: 1.2rem; font-weight: bold;">{durum_metni}</div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 3.5rem; font-weight: bold;">{sicaklik:.1f}°C</div>
                        <div style="font-size: 1rem;">Hissedilen: <b>{his:.1f}°C</b></div>
                        <div style="font-size: 1rem;">Nem: <b>%{nem:.0f}</b> | Rüzgar: <b>{ruzgar:.1f} km/h</b></div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander("Konumu Haritada Göster"):
                map_data = pd.DataFrame({'lat': [lat], 'lon': [lon]})
                st.map(map_data, zoom=10)
            
            if mod_secimi == "Geçmiş Veri Analizi" and len(tarih_araligi) == 2:
                st.session_state.analiz_yapildi = True
                st.session_state.baslangic = tarih_araligi[0]
                st.session_state.bitis = tarih_araligi[1]
                with st.spinner('Veriler taranıyor...'):
                    df = gecmis_veri_cek_v2(lat, lon, tarih_araligi[0].strftime("%Y-%m-%d"), tarih_araligi[1].strftime("%Y-%m-%d"))
                    st.session_state.df_gecmis = df

            elif mod_secimi == "Hava Tahmini":
                st.session_state.analiz_yapildi = True
                with st.spinner('Tahmin alınıyor...'):
                    df_tahmin = tahmin_veri_cek(lat, lon)
                    st.session_state.df_tahmin = df_tahmin

        except Exception as e:
            st.error(f"Veri Hatası: {e}")
    else:
        st.error("Şehir bulunamadı.")

if st.session_state.analiz_yapildi:
    
    # GEÇMİŞ MOD
    if mod_secimi == "Geçmiş Veri Analizi" and st.session_state.df_gecmis is not None:
        df = st.session_state.df_gecmis
        baslangic = st.session_state.baslangic
        bitis = st.session_state.bitis
        
        ort = df['max'].mean()
        maks = df['max'].max()
        minn = df['min'].min()
        top_yagis = df['yagis'].sum()
        max_ruzgar = df['ruzgar'].max()

        tab1, tab2, tab3 = st.tabs(["Sıcaklık & Yağış", "Rüzgar", "Teknik Değerlendirme"])
        
        with tab1:
            st.plotly_chart(interaktif_grafik(df, st.session_state.adres.split(",")[0], renk_max, renk_min, renk_yagis, plotly_tema, font_color, bg_color), use_container_width=True)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Ortalama", f"{ort:.1f} °C")
            c2.metric("En Yüksek", f"{maks:.1f} °C")
            c3.metric("En Düşük", f"{minn:.1f} °C")
            c4.metric("Top. Yağış", f"{top_yagis:.1f} mm")
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(label="Verileri İndir (CSV)", data=csv, file_name=f"{girilen_sehir}_gecmis_veri.csv", mime="text/csv")
            
        with tab2:
            st.plotly_chart(ruzgar_grafigi(df, renk_ruzgar, plotly_tema, font_color, bg_color), use_container_width=True)
            st.info(f"Maksimum rüzgar hamlesi: **{max_ruzgar} km/h**")
            
        with tab3:
            gun_sayisi = (bitis - baslangic).days
            prompt = f"""
            Sen uzman bir Meteoroloji Mühendisisin. Aşağıdaki verileri kullanarak resmi ve teknik bir analiz raporu yaz.
            Bölge: {st.session_state.adres}
            Dönem: {baslangic.strftime('%d.%m.%Y')} - {bitis.strftime('%d.%m.%Y')} ({gun_sayisi} Gün)
            İstatistikler: Max {maks}°C, Min {minn}°C, Ort {ort}°C, Toplam Yağış {top_yagis}mm.
            Rapor Formatı:
            1. **Giriş:** Dönemin genel meteorolojik karakteristiği.
            2. **Sıcaklık Rejimi:** Mevsim normallerine göre sapmalar.
            3. **Yağış Analizi:** Kuraklık durumu veya yağışın dağılımı.
            4. **Sonuç:** Tarım ve su kaynakları üzerindeki olası etkiler.
            Lütfen "Yapay zeka", "Model" gibi ifadeler KULLANMA. Doğrudan mühendis gibi yaz.
            """
            with st.spinner('Analiz hazırlanıyor...'):
                st.markdown(teknik_analiz_olustur(prompt))

    # TAHMİN MODU
    elif mod_secimi == "Hava Tahmini" and st.session_state.df_tahmin is not None:
        df = st.session_state.df_tahmin
        
        st.subheader("7 Günlük Tahmin")
        st.plotly_chart(tahmin_grafigi(df, st.session_state.adres.split(",")[0], plotly_tema, font_color, bg_color), use_container_width=True)
        csv_tahmin = df.to_csv(index=False).encode('utf-8')
        st.download_button(label="Tahmin Verisini İndir (CSV)", data=csv_tahmin, file_name=f"{girilen_sehir}_tahmin_veri.csv", mime="text/csv")
        
        cols = st.columns(7)
        for i, row in df.iterrows():
            with cols[i]:
                ikon, durum = kod_cozucu(row['kod'], True)
                st.caption(f"{row['date'].strftime('%d.%m')}")
                st.markdown(f"### {ikon}")
                st.markdown(f"**{row['max']:.0f}°** / {row['min']:.0f}°")
                
                # TAVSİYE MANTIĞI GÜNCELLENDİ
                tavsiye = ""
                if row['kod'] >= 95: tavsiye = "⚠️ Fırtına"
                elif row['yagis_ihtimal'] > 60: tavsiye = "☔ Yağışlı"
                elif row['max'] > 30: tavsiye = "🔥 Sıcak"
                elif row['max'] < 5: tavsiye = "❄️ Soğuk"
                elif row['max'] < 15: tavsiye = "🧥 Serin"
                elif durum == "Açık": tavsiye = "☀️ Güneşli"
                else: tavsiye = f"☁️ {durum}" # "Normal" yerine gerçek durumu yaz
                
                st.caption(tavsiye)
        
        st.markdown("---")
        st.subheader("📝 Haftalık Teknik Değerlendirme") # <-- Başlık değişti
        
        # PROMPT 
        prompt_tahmin = f"""
        GÖREV: Aşağıdaki 7 günlük hava tahmin verilerini analiz et ve teknik bir rapor yaz.
        
        VERİLER:
        Konum: {st.session_state.adres}
        Maksimum Sıcaklıklar: {df['max'].tolist()}
        Minimum Sıcaklıklar: {df['min'].tolist()}
        Yağış İhtimalleri: {df['yagis_ihtimal'].tolist()}
        Rüzgar Hızları: {df['ruzgar'].tolist()}
        
        FORMAT:
        1. **Sıcaklık Trendi:** (Isınma/Soğuma analizi)
        2. **Yağış Riski:** (Hangi günler riskli?)
        3. **Rüzgar Durumu:** (Fırtına riski analizi)
        4. **Mühendislik Notu:** (Kısa teknik tavsiye)
        
        KURALLAR:
        - "Merhaba", "Saygılar", "İmza" YOK.
        - Direkt maddelerle başla.
        """
        
        with st.spinner('Değerlendirme hazırlanıyor...'):
            sonuc = teknik_analiz_olustur(prompt_tahmin)
            if sonuc:
                st.markdown(sonuc)
            else:

                st.error("Rapor oluşturulamadı. Lütfen tekrar deneyin.")
