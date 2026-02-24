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

# Zaman dilimine göre periyot ayarı
period_map = {"5m": "1d", "1h": "1mo", "1d": "max"}

@st.cache_data(ttl=60)
def fetch_and_calculate(ticker, timeframe):
    df = yf.download(ticker, interval=timeframe, period=period_map[timeframe])
    if df.empty or len(df) < 50: return pd.DataFrame()
    
    # Sütun temizliği
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # --- ZAMANA ÖZEL İNDİKATÖRLER ---
    if timeframe == "5m":
        # Scalping Seti
        df['EMA_9'] = ta.ema(df['Close'], length=9)
        df['EMA_21'] = ta.ema(df['Close'], length=21)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        bbands = ta.bbands(df['Close'], length=20, std=2)
        df = pd.concat([df, bbands], axis=1)
        macd = ta.macd(df['Close'])
        df = pd.concat([df, macd], axis=1)
        # VWAP (Basitleştirilmiş)
        df['VWAP'] = ta.vwap(df['High'], df['Low'], df['Close'], df['Volume'])

    elif timeframe == "1h":
        # Swing Seti
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        df['EMA_50'] = ta.ema(df['Close'], length=50)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        macd = ta.macd(df['Close'])
        df = pd.concat([df, macd], axis=1)
        df['OBV'] = ta.obv(df['Close'], df['Volume'])
        # Ichimoku (Temel bileşenler)
        ichi = ta.ichimoku(df['High'], df['Low'], df['Close'])[0]
        df = pd.concat([df, ichi], axis=1)

    elif timeframe == "1d":
        # Trend Seti
        df['SMA_50'] = ta.sma(df['Close'], length=50)
        df['SMA_200'] = ta.sma(df['Close'], length=200)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        macd = ta.macd(df['Close'])
        df = pd.concat([df, macd], axis=1)
        df['OBV'] = ta.obv(df['Close'], df['Volume'])

    return df

df = fetch_and_calculate(symbol, interval)

if df.empty:
    st.error("Veri çekilemedi veya yetersiz veri!")
    st.stop()

# --- SİNYAL ANALİZ MOTORU ---
last = df.iloc[-1]
prev = df.iloc[-2]
signals = []

if interval == "5m":
    signals.append(("EMA 9/21 Kesişimi", "AL" if last['EMA_9'] > last['EMA_21'] else "SAT", last['EMA_9'] > last['EMA_21']))
    signals.append(("VWAP Durumu", "Fiyat Üstte (Olumlu)" if last['Close'] > last['VWAP'] else "Fiyat Altta (Olumsuz)", last['Close'] > last['VWAP']))
    signals.append(("RSI (14)", f"{last['RSI']:.2f}", 30 < last['RSI'] < 70))
    signals.append(("MACD", "Momentum Pozitif" if last['MACD_12_26_9'] > 0 else "Momentum Negatif", last['MACD_12_26_9'] > 0))

elif interval == "1h":
    signals.append(("Trend (EMA 20/50)", "Yükseliş" if last['EMA_20'] > last['EMA_50'] else "Düşüş", last['EMA_20'] > last['EMA_50']))
    signals.append(("MACD Kesişimi", "Al Sinyali" if last['MACD_12_26_9'] > last['MACDs_12_26_9'] else "Sat Sinyali", last['MACD_12_26_9'] > last['MACDs_12_26_9']))
    signals.append(("Ichimoku (Tenkan/Kijun)", "Pozitif" if last['ITS_9'] > last['IKS_26'] else "Negatif", last['ITS_9'] > last['IKS_26']))

elif interval == "1d":
    signals.append(("Ana Trend (SMA 50/200)", "Boğa" if last['SMA_50'] > last['SMA_200'] else "Ayı", last['SMA_50'] > last['SMA_200']))
    signals.append(("Stratejik RSI", "Aşırı Satım (Al)" if last['RSI'] < 30 else "Aşırı Alım (Sat)" if last['RSI'] > 70 else "Nötr", 30 < last['RSI'] < 70))

# --- ARAYÜZ ÇIKTILARI ---
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📋 Sinyal Özetleri")
    for name, status, is_positive in signals:
        color = "green" if is_positive else "red"
        st.markdown(f"**{name}:** <span style='color:{color}'>{status}</span>", unsafe_allow_html=True)
    
    st.info(f"Seçilen Strateji: {interval} - {'Scalping' if interval=='5m' else 'Swing' if interval=='1h' else 'Trend Takibi'}")

with col2:
    # Grafik Oluşturma
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
    
    # Ana Grafik (Candlestick)
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Fiyat"), row=1, col=1)
    
    # Zamana özel çizgiler
    if interval == "5m":
        fig.add_trace(go.Scatter(x=df.index, y=df['VWAP'], name="VWAP", line=dict(color='white', dash='dot')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['BBU_20_2.0'], name="BB Üst", line=dict(color='gray', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['BBL_20_2.0'], name="BB Alt", fill='tonexty', line=dict(color='gray', width=1)), row=1, col=1)
    
    elif interval == "1h":
        fig.add_trace(go.Scatter(x=df.index, y=df['ISA_9'], name="Bulut A", line=dict(width=0)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['ISB_26'], name="Bulut B", fill='tonexty', line=dict(width=0)), row=1, col=1)

    # Alt Grafik (RSI)
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name="RSI", line=dict(color='purple')), row=2, col=1)
    fig.add_hline(y=70, line_color="red", line_dash="dash", row=2, col=1)
    fig.add_hline(y=30, line_color="green", line_dash="dash", row=2, col=1)

    fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
