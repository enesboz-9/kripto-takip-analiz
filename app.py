import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests

# Sayfa Ayarları
st.set_page_config(page_title="Crypto Intelligence - Enes Boz", layout="wide")

# --- GELİŞTİRİCİ İMZASI (CSS) ---
st.markdown(
    """
    <style>
    .developer-badge {
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: linear-gradient(45deg, #ff4b4b, #ff8a8a);
        color: white;
        padding: 12px 24px;
        border-radius: 50px;
        font-weight: bold;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.5);
        z-index: 9999;
        border: 2px solid rgba(255,255,255,0.2);
    }
    </style>
    <div class="developer-badge">
        🚀 Developer: Enes Boz
    </div>
    """,
    unsafe_allow_html=True
)

st.title("🛡️ Kripto İstihbarat ve Strateji Terminali")

# --- DATA FETCH FUNCTIONS ---
@st.cache_data(ttl=600)
def get_fear_greed():
    try:
        r = requests.get("https://api.alternative.me/fng/")
        return r.json()['data'][0]
    except:
        return None

@st.cache_data(ttl=60)
def fetch_and_calculate(ticker, timeframe, period):
    df = yf.download(ticker, interval=timeframe, period=period)
    if df.empty or len(df) < 50: return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # Teknik Hesaplamalar
    df['RSI'] = ta.rsi(df['Close'], length=14)
    df['EMA_20'] = ta.ema(df['Close'], length=20)
    
    # Bollinger Bantları
    bb = ta.bbands(df['Close'], length=20, std=2)
    df = pd.concat([df, bb], axis=1)
    df.rename(columns={bb.columns[0]: 'BBL', bb.columns[2]: 'BBU'}, inplace=True)
    
    # MACD
    macd = ta.macd(df['Close'])
    df = pd.concat([df, macd], axis=1)
    df.rename(columns={macd.columns[0]: 'MACD_VAL', macd.columns[2]: 'MACD_SIG'}, inplace=True)
    
    return df

# --- SIDEBAR ---
st.sidebar.header("⚙️ Kontrol Paneli")
symbol = st.sidebar.selectbox("Kripto Birimi", ["BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD", "ARB-USD"])
interval = st.sidebar.selectbox("Zaman Dilimi", ["5m", "1h", "1d"], index=1)
period_map = {"5m": "5d", "1h": "1mo", "1d": "max"}

st.sidebar.markdown("---")
st.sidebar.write("👤 **Geliştirici Bilgisi**")
st.sidebar.info("Bu terminal **Enes Boz** tarafından kripto yatırımcıları için özel olarak tasarlanmıştır.")

# --- VERİ ÇEKİMİ ---
df = fetch_and_calculate(symbol, interval, period_map[interval])
fng_data = get_fear_greed()

if df.empty:
    st.error("Veri yüklenemedi!")
    st.stop()

# --- ÜST METRİKLER ---
col_f1, col_f2, col_f3, col_f4 = st.columns(4)
with col_f1:
    if fng_data:
        st.metric("Piyasa Duyarlılığı", f"{fng_data['value']}/100", fng_data['value_classification'])
with col_f2:
    st.metric("Anlık Fiyat", f"${df['Close'].iloc[-1]:,.2f}")
with col_f3:
    change = ((df['Close'].iloc[-1] - df['Open'].iloc[0]) / df['Open'].iloc[0]) * 100
    st.metric("Periyot Değişimi", f"%{change:.2f}")
with col_f4:
    st.metric("RSI Değeri", f"{df['RSI'].iloc[-1]:.2f}")

# --- ANA GRAFİK (TEKNİK ANALİZ) ---
st.subheader("🔍 Profesyonel Teknik Analiz")
fig_main = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])

# Mumlar ve Bollinger
fig_main.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Candle"), row=1, col=1)
fig_main.add_trace(go.Scatter(x=df.index, y=df['BBU'], line=dict(color='rgba(255,255,255,0.2)'), name="Bollinger Üst"), row=1, col=1)
fig_main.add_trace(go.Scatter(x=df.index, y=df['BBL'], fill='tonexty', line=dict(color='rgba(255,255,255,0.1)'), name="Bollinger Alt"), row=1, col=1)

# RSI Alt Grafik
fig_main.add_trace(go.Scatter(x=df.index, y=df['RSI'], name="RSI", line=dict(color='#8A2BE2')), row=2, col=1)
fig_main.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
fig_main.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

fig_main.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False)
st.plotly_chart(fig_main, use_container_width=True)

# --- ALT GRAFİK (SAF FİYAT TRENDİ) ---
st.subheader(f"📈 {symbol} Sade Fiyat Trendi")
fig_price = go.Figure()
fig_price.add_trace(go.Scatter(x=df.index, y=df['Close'], fill='tozeroy', line=dict(color='cyan', width=2), name="Fiyat"))
fig_price.update_layout(height=300, template="plotly_dark", margin=dict(l=0, r=0, t=20, b=0))
st.plotly_chart(fig_price, use_container_width=True)

# --- SİNYAL PANELİ ---
st.divider()
st.subheader("📝 Yapay Zeka Destekli Sinyal Kararı")
last = df.iloc[-1]
if last['RSI'] < 30: s, sc = "GÜÇLÜ AL", "#00FF00"
elif last['RSI'] < 45: s, sc = "AL", "#90EE90"
elif last['RSI'] > 70: s, sc = "GÜÇLÜ SAT", "#FF0000"
elif last['RSI'] > 55: s, sc = "SAT", "#FFA500"
else: s, sc = "NÖTR / BEKLE", "#808080"

st.markdown(f"""
    <div style="background-color: #1e1e1e; padding: 20px; border-radius: 10px; border-left: 10px solid {sc};">
        <h2 style="color: white; margin: 0;">Mevcut Strateji Kararı: <span style="color: {sc};">{s}</span></h2>
        <p style="color: gray; margin-top: 10px;">Analiz Zamanı: {last.name} | Periyot: {interval}</p>
    </div>
""", unsafe_allow_html=True)
