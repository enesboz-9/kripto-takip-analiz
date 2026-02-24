import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Sayfa Ayarları
st.set_page_config(page_title="Crypto Pro Analyzer", layout="wide")

st.title("📈 Kripto Para Teknik Analiz ve Sinyal")

# --- PARAMETRELER (SIDEBAR) ---
st.sidebar.header("🔍 Analiz Ayarları")
symbol = st.sidebar.selectbox("Kripto Birimi", ["BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD", "XRP-USD"])
interval = st.sidebar.selectbox("Zaman Dilimi", ["5m", "15m", "1h", "1d"], index=2)

# yfinance kısıtlamalarına göre periyot eşleşmesi
period_map = {
    "5m": "1d",   # 5 dakikalık veri için son 1 gün
    "15m": "5d",  # 15 dakikalık veri için son 5 gün
    "1h": "1mo",  # 1 saatlik veri için son 1 ay
    "1d": "max"   # Günlük veri için tüm geçmiş
}

# --- VERİ ÇEKME VE HESAPLAMA ---
@st.cache_data(ttl=60) # Veriyi 60 saniye önbellekte tutar
def get_data(ticker, interval, period):
    try:
        df = yf.download(ticker, interval=interval, period=period)
        if df.empty or len(df) < 20: # Teknik analiz için en az 20 satır lazım
            return pd.DataFrame()
        
        # Multi-index sütun sorununu temizleme (yfinance yeni versiyon için)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # İndikatör Hesaplamaları
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['SMA_20'] = ta.sma(df['Close'], length=20)
        
        # MACD hesaplama ve sütun isimlerini düzeltme
        macd_df = ta.macd(df['Close'])
        df = pd.concat([df, macd_df], axis=1)
        
        return df
    except Exception as e:
        st.error(f"Veri çekme hatası: {e}")
        return pd.DataFrame()

df = get_data(symbol, interval, period_map[interval])

# --- HATA KONTROLÜ ---
if df.empty:
    st.warning(f"⚠️ {symbol} için {interval} diliminde yeterli veri bulunamadı. Lütfen zaman dilimini veya coini değiştirin.")
    st.info("İpucu: 5m için son 1 günü, 1h için son 1 ayı seçmeyi deneyin.")
    st.stop()

# --- SİNYAL ÜRETME MANTIĞI ---
current_row = df.iloc[-1]
rsi_val = current_row['RSI']
price_val = current_row['Close']
sma_val = current_row['SMA_20']

def get_signal(rsi, price, sma):
    if rsi < 35 and price > sma: return "GÜÇLÜ AL", "green"
    if rsi < 40: return "AL", "lightgreen"
    if rsi > 65 and price < sma: return "GÜÇLÜ SAT", "red"
    if rsi > 60: return "SAT", "orange"
    return "NÖTR / BEKLE", "gray"

signal_text, signal_color = get_signal(rsi_val, price_val, sma_val)

# --- ARAYÜZ (METRİKLER) ---
col1, col2, col3 = st.columns(3)
col1.metric("Anlık Fiyat", f"${price_val:,.2f}")
col2.metric("RSI (14)", f"{rsi_val:.2f}")
col3.markdown(f"### Sinyal: <span style='color:{signal_color}'>{signal_text}</span>", unsafe_allow_html=True)

# --- GELİŞMİŞ GRAFİK (Subplots) ---
# Üstte Mum Grafiği, altta RSI
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                    vertical_spacing=0.1, row_heights=[0.7, 0.3])

# 1. Row: Candlestick & SMA
fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], 
                             low=df['Low'], close=df['Close'], name='Fiyat'), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], line=dict(color='yellow', width=1.5), name='SMA 20'), row=1, col=1)

# 2. Row: RSI
fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='purple'), name='RSI'), row=2, col=1)
fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

fig.update_layout(height=700, xaxis_rangeslider_visible=False, template="plotly_dark")
st.plotly_chart(fig, use_container_width=True)

# Veri Tablosu
with st.expander("Son Verileri İncele"):
    st.dataframe(df.tail(10))
