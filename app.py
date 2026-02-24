import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta  # Teknik analiz için kolaylık sağlar
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Crypto Pro Analyzer", layout="wide")

# --- PARAMETRELER ---
st.sidebar.header("🔍 Analiz Ayarları")
symbol = st.sidebar.selectbox("Kripto Birimi", ["BTC-USD", "ETH-USD", "SOL-USD", "ARB-USD"])
interval = st.sidebar.selectbox("Zaman Dilimi", ["5m", "15m", "1h", "1d"], index=2)
period_map = {"5m": "1d", "15m": "5d", "1h": "1mo", "1d": "max"}

# --- VERİ ÇEKME VE HESAPLAMA ---
@st.cache_data
def get_data(ticker, interval, period):
    df = yf.download(ticker, interval=interval, period=period)
    # İndikatör Hesaplamaları
    df['RSI'] = ta.rsi(df['Close'], length=14)
    df['SMA_20'] = ta.sma(df['Close'], length=20)
    macd = ta.macd(df['Close'])
    df = pd.concat([df, macd], axis=1)
    return df

df = get_data(symbol, interval, period_map[interval])

# --- SİNYAL ÜRETME MANTIĞI ---
def generate_signal(row):
    rsi = row['RSI']
    close = row['Close']
    sma = row['SMA_20']
    
    if rsi < 35 and close > sma:
        return "GÜÇLÜ AL", "green"
    elif rsi < 45:
        return "AL", "lightgreen"
    elif rsi > 65 and close < sma:
        return "GÜÇLÜ SAT", "red"
    elif rsi > 55:
        return "SAT", "orange"
    else:
        return "BEKLE / NÖTR", "gray"

current_row = df.iloc[-1]
signal_text, color = generate_signal(current_row)

# --- ARAYÜZ ---
col1, col2, col3 = st.columns(3)
col1.metric("Anlık Fiyat", f"${current_row['Close']:.2f}")
col2.metric("RSI (14)", f"{current_row['RSI']:.2f}")
col3.markdown(f"### Sinyal: <span style='color:{color}'>{signal_text}</span>", unsafe_allow_html=True)

# --- GRAFİK ---
fig = go.Figure()
# Mum Grafiği
fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], 
                             low=df['Low'], close=df['Close'], name='Fiyat'))
# SMA Çizgisi
fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], line=dict(color='yellow', width=1), name='SMA 20'))

fig.update_layout(title=f"{symbol} {interval} Grafik", xaxis_rangeslider_visible=False)
st.plotly_chart(fig, use_container_width=True)

# --- TEKNİK DETAY TABLOSU ---
with st.expander("Teknik Detayları Gör"):
    st.write(df.tail(10))
