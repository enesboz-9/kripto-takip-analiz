import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Sayfa Ayarları
st.set_page_config(page_title="Crypto Strategy Pro", layout="wide")

st.title("🛡️ Stratejik Kripto Analiz Terminali")

# --- SIDEBAR AYARLARI ---
symbol = st.sidebar.selectbox("Kripto Birimi", ["BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD", "ARB-USD"])
interval = st.sidebar.selectbox("Strateji Zaman Dilimi", ["5m", "1h", "1d"], index=1)

# Zaman dilimine göre periyot ayarı (5m için periyodu 5 güne çıkardık daha stabil veri için)
period_map = {"5m": "5d", "1h": "1mo", "1d": "max"}

@st.cache_data(ttl=60)
def fetch_and_calculate(ticker, timeframe):
    df = yf.download(ticker, interval=timeframe, period=period_map[timeframe])
    if df.empty or len(df) < 50: return pd.DataFrame()
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # --- ZAMANA ÖZEL İNDİKATÖRLER ---
    if timeframe == "5m":
        df['EMA_9'] = ta.ema(df['Close'], length=9)
        df['EMA_21'] = ta.ema(df['Close'], length=21)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        
        # Bollinger Bantları - Dinamik Sütun Yakalama
        bbands = ta.bbands(df['Close'], length=20, std=2)
        df = pd.concat([df, bbands], axis=1)
        # Sütunları standartlaştırıyoruz (Versiyon farkını önlemek için)
        df.rename(columns={bbands.columns[0]: 'BBL', bbands.columns[2]: 'BBU'}, inplace=True)
        
        macd = ta.macd(df['Close'])
        df = pd.concat([df, macd], axis=1)
        df.rename(columns={macd.columns[0]: 'MACD_VAL'}, inplace=True)
        
        # VWAP için
        df['VWAP'] = ta.vwap(df['High'], df['Low'], df['Close'], df['Volume'])

    elif timeframe == "1h":
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        df['EMA_50'] = ta.ema(df['Close'], length=50)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        macd = ta.macd(df['Close'])
        df = pd.concat([df, macd], axis=1)
        df.rename(columns={macd.columns[0]: 'MACD_VAL', macd.columns[2]: 'MACD_SIG'}, inplace=True)
        
        ichi = ta.ichimoku(df['High'], df['Low'], df['Close'])[0]
        df = pd.concat([df, ichi], axis=1)
        df.rename(columns={ichi.columns[0]: 'ITS', ichi.columns[1]: 'IKS'}, inplace=True)

    elif timeframe == "1d":
        df['SMA_50'] = ta.sma(df['Close'], length=50)
        df['SMA_200'] = ta.sma(df['Close'], length=200)
        df['RSI'] = ta.rsi(df['Close'], length=14)

    return df

df = fetch_and_calculate(symbol, interval)

if df.empty:
    st.error("Veri çekilemedi veya yetersiz veri!")
    st.stop()

# --- SİNYAL ANALİZ MOTORU ---
last = df.iloc[-1]
signals = []

if interval == "5m":
    signals.append(("EMA 9/21 Kesişimi", "AL" if last['EMA_9'] > last['EMA_21'] else "SAT", last['EMA_9'] > last['EMA_21']))
    signals.append(("VWAP Durumu", "Fiyat Üstte" if last['Close'] > last['VWAP'] else "Fiyat Altta", last['Close'] > last['VWAP']))
    signals.append(("RSI (14)", f"{last['RSI']:.2f}", 30 < last['RSI'] < 70))
    signals.append(("MACD", "Pozitif" if last['MACD_VAL'] > 0 else "Negatif", last['MACD_VAL'] > 0))

elif interval == "1h":
    signals.append(("Trend (EMA 20/50)", "Yükseliş" if last['EMA_20'] > last['EMA_50'] else "Düşüş", last['EMA_20'] > last['EMA_50']))
    signals.append(("MACD Sinyali", "Olumlu" if last['MACD_VAL'] > last['MACD_SIG'] else "Olumsuz", last['MACD_VAL'] > last['MACD_SIG']))
    signals.append(("Ichimoku", "Pozitif" if last['ITS'] > last['IKS'] else "Negatif", last['ITS'] > last['IKS']))

elif interval == "1d":
    signals.append(("Ana Trend (SMA 50/200)", "Boğa" if last['SMA_50'] > last['SMA_200'] else "Ayı", last['SMA_50'] > last['SMA_200']))
    signals.append(("RSI", f"{last['RSI']:.2f}", 30 < last['RSI'] < 70))

# --- GÖRSELLEŞTİRME ---
col1, col2 = st.columns([1, 3])

with col1:
    st.subheader("📋 Sinyaller")
    for name, status, is_pos in signals:
        c = "green" if is_pos else "red"
        st.markdown(f"**{name}:** <span style='color:{c}'>{status}</span>", unsafe_allow_html=True)

with col2:
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Fiyat"), row=1, col=1)
    
    if interval == "5m":
        fig.add_trace(go.Scatter(x=df.index, y=df['VWAP'], name="VWAP", line=dict(color='white', dash='dot')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['BBU'], name="BB Üst", line=dict(color='rgba(173, 216, 230, 0.4)')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['BBL'], name="BB Alt", fill='tonexty', line=dict(color='rgba(173, 216, 230, 0.4)')), row=1, col=1)
    
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name="RSI", line=dict(color='purple')), row=2, col=1)
    fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
