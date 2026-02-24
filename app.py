import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests

# Sayfa Ayarları
st.set_page_config(page_title="Crypto Intelligence Hub", layout="wide")

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

    # Teknik Hesaplamalar (Standartlaştırma)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    df['EMA_20'] = ta.ema(df['Close'], length=20)
    df['EMA_50'] = ta.ema(df['Close'], length=50)
    
    # Bollinger & MACD Dinamik İsimlendirme
    bb = ta.bbands(df['Close'], length=20, std=2)
    df = pd.concat([df, bb], axis=1)
    df.rename(columns={bb.columns[0]: 'BBL', bb.columns[2]: 'BBU'}, inplace=True)
    
    macd = ta.macd(df['Close'])
    df = pd.concat([df, macd], axis=1)
    df.rename(columns={macd.columns[0]: 'MACD_VAL', macd.columns[2]: 'MACD_SIG'}, inplace=True)
    
    return df

# --- SIDEBAR ---
symbol = st.sidebar.selectbox("Kripto Birimi", ["BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD", "ARB-USD"])
interval = st.sidebar.selectbox("Zaman Dilimi", ["5m", "1h", "1d"], index=1)
period_map = {"5m": "5d", "1h": "1mo", "1d": "max"}

df = fetch_and_calculate(symbol, interval, period_map[interval])
fng_data = get_fear_greed()

# --- ÜST METRİKLER VE PSYCHOLOGY ---
col_f1, col_f2, col_f3, col_f4 = st.columns(4)
with col_f1:
    if fng_data:
        st.metric("Piyasa Korku/Açgözlülük", f"{fng_data['value']}/100", fng_data['value_classification'])
with col_f2:
    st.metric("Anlık Fiyat", f"${df['Close'].iloc[-1]:,.2f}")
with col_f3:
    change = ((df['Close'].iloc[-1] - df['Open'].iloc[0]) / df['Open'].iloc[0]) * 100
    st.metric("Periyot Değişimi", f"%{change:.2f}")
with col_f4:
    rsi_now = df['RSI'].iloc[-1]
    st.metric("RSI Gücü", f"{rsi_now:.2f}")

# --- ANA GRAFİK (TEKNİK ANALİZ) ---
st.subheader("🔍 Teknik Analiz Görünümü")
fig_main = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])

# Mum Grafiği ve Bollinger
fig_main.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Candle"), row=1, col=1)
fig_main.add_trace(go.Scatter(x=df.index, y=df['BBU'], line=dict(color='rgba(173, 216, 230, 0.2)'), name="BB Üst"), row=1, col=1)
fig_main.add_trace(go.Scatter(x=df.index, y=df['BBL'], fill='tonexty', line=dict(color='rgba(173, 216, 230, 0.2)'), name="BB Alt"), row=1, col=1)
fig_main.add_trace(go.Scatter(x=df.index, y=df['EMA_20'], line=dict(color='yellow', width=1), name="EMA 20"), row=1, col=1)

# RSI
fig_main.add_trace(go.Scatter(x=df.index, y=df['RSI'], name="RSI", line=dict(color='purple')), row=2, col=1)
fig_main.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
fig_main.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

fig_main.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False)
st.plotly_chart(fig_main, use_container_width=True)

# --- ALT GRAFİK (SADE FİYAT) ---
st.subheader(f"📈 {symbol} Saf Fiyat Trendi")
fig_price = go.Figure()
fig_price.add_trace(go.Scatter(x=df.index, y=df['Close'], fill='tozeroy', line=dict(color='cyan', width=2), name="Fiyat"))
fig_price.update_layout(height=300, template="plotly_dark", margin=dict(l=0, r=0, t=0, b=0))
st.plotly_chart(fig_price, use_container_width=True)

# --- SİNYAL VE BACKTEST ÖZETİ ---
st.divider()
col_s1, col_s2 = st.columns(2)

with col_s1:
    st.subheader("📝 Aktif Sinyal Durumu")
    last = df.iloc[-1]
    # Basit Sinyal Mantığı
    if last['RSI'] < 35: s, sc = "ALIM BÖLGESİ", "green"
    elif last['RSI'] > 65: s, sc = "SATIŞ BÖLGESİ", "red"
    else: s, sc = "NÖTR / İZLE", "gray"
    
    st.markdown(f"**Genel Strateji Kararı:** <h2 style='color:{sc}'>{s}</h2>", unsafe_allow_html=True)

with col_s2:
    st.subheader("📊 Strateji Verimliliği")
    # Basit bir Backtest simülasyonu: RSI 30 altı al, 70 üstü sat
    buy_signals = df[df['RSI'] < 30]
    sell_signals = df[df['RSI'] > 70]
    st.write(f"Bu periyotta toplam **{len(buy_signals)}** Al, **{len(sell_signals)}** Sat fırsatı oluştu.")
    st.caption("Not: Bu veriler yatırım tavsiyesi değildir, teknik indikatörlerin matematiksel sonucudur.")
