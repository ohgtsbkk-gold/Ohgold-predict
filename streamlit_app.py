import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# ตั้งค่าหน้าเว็บ (Page Config)
st.set_page_config(page_title="Gold Analyzer", page_icon="🥇", layout="centered")

# ==========================================
# ฟังก์ชันคำนวณต่างๆ (ซ่อนการทำงานไว้หลังบ้าน)
# ==========================================
def add_indicators(df):
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    return df

def analyze_sentiment(news_titles):
    bullish = ['cut', 'inflation', 'war', 'tension', 'drop', 'weak', 'stimulus', 'dovish', 'crisis']
    bearish = ['hike', 'strong', 'growth', 'peace', 'hawkish', 'recover', 'high']
    score = 0
    for title in news_titles:
        t = title.lower()
        if any(w in t for w in bullish): score += 1
        if any(w in t for w in bearish): score -= 1
    if score > 0: return "🟢 เชิงบวกต่อทอง (มีโอกาสขึ้น)"
    elif score < 0: return "🔴 เชิงลบต่อทอง (มีโอกาสลง)"
    else: return "⚪ ข้อมูลยังไม่ชัดเจน / ทรงตัว"

def calculate_pivots(df, index):
    try:
        row = df.iloc[index]
        pp = (row['High'] + row['Low'] + row['Close']) / 3
        r1 = (2 * pp) - row['Low']
        r2 = pp + (row['High'] - row['Low'])
        s1 = (2 * pp) - row['High']
        s2 = pp - (row['High'] - row['Low'])
        return {'R2': r2, 'R1': r1, 'PP': pp, 'S1': s1, 'S2': s2}
    except:
        return None

# ระบบ Cache ข้อมูล 1 นาที เพื่อไม่ให้โหลดช้า
@st.cache_data(ttl=60)
def fetch_data():
    gold = yf.Ticker("GC=F")
    df_d = gold.history(period="1mo", interval="1d")
    df_w = gold.history(period="3mo", interval="1wk")
    news = gold.news
    return df_d, df_w, news

# ==========================================
# ส่วนแสดงผลหน้าเว็บ (UI)
# ==========================================
st.title("🥇 XAU/USD Smart Analyzer")
st.caption(f"อัปเดตข้อมูลล่าสุด: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} (อิงจาก Gold Futures)")

if st.button("🔄 ดึงข้อมูลล่าสุดเดี๋ยวนี้"):
    st.cache_data.clear()

try:
    df_daily, df_weekly, news_data = fetch_data()
    
    if df_daily.empty or df_weekly.empty:
        st.error("ดึงข้อมูลไม่สำเร็จ ตลาดอาจปิดทำการ")
        st.stop()
        
    df_daily = add_indicators(df_daily)
    current_price = df_daily.iloc[-1]['Close']
    prev_price = df_daily.iloc[-2]['Close']
    change = current_price - prev_price
    
    # คำนวณต่างๆ
    pivots_d = calculate_pivots(df_daily, -2)
    pivots_w = calculate_pivots(df_weekly, -2)
    current_rsi = df_daily.iloc[-1]['RSI']
    macd = df_daily.iloc[-1]['MACD']
    signal = df_daily.iloc[-1]['Signal']
    
    # 1. แสดงราคา
    st.metric(label="ราคาปัจจุบัน (USD/oz)", value=f"{current_price:.2f}", delta=f"{change:.2f}")
    
    # 2. แสดงตัวชี้วัด (Indicators)
    st.subheader("📊 โมเมนตัมตลาด (Daily)")
    col1, col2 = st.columns(2)
    
    with col1:
        rsi_status = "ทรงตัว"
        if current_rsi >= 70: rsi_status = "🔥 Overbought"
        elif current_rsi <= 30: rsi_status = "🥶 Oversold"
        st.info(f"**RSI (14)**\n\n{current_rsi:.1f} ({rsi_status})")
        
    with col2:
        macd_status = "🟢 กระทิง (Bullish)" if macd > signal else "🔴 หมี (Bearish)"
        st.info(f"**MACD**\n\n{macd_status}")

    # 3. แนวรับแนวต้าน (Support & Resistance)
    st.subheader("🎯 โซนแนวรับ/แนวต้าน (Day & Swing)")
    
    # หา Confluence (ต้าน)
    if abs(pivots_d['R1'] - pivots_w['R1']) < 10:
        st.error(f"🚨 **ต้านแข็งแกร่ง (Confluence): {pivots_d['R1']:.1f}**")
    else:
        st.error(f"🔴 R2: {pivots_d['R2']:.1f} | 🟠 R1: {pivots_d['R1']:.1f}")
        
    st.write(f"⚪ **จุดหมุน (Pivot): {pivots_d['PP']:.1f}**")
    
    # หา Confluence (รับ)
    if abs(pivots_d['S1'] - pivots_w['S1']) < 10:
        st.success(f"🚨 **รับแข็งแกร่ง (Confluence): {pivots_d['S1']:.1f}**")
    else:
        st.success(f"🟢 S1: {pivots_d['S1']:.1f} | 🔵 S2: {pivots_d['S2']:.1f}")

    # 4. ข่าว
    recent_news = [n['title'] for n in news_data[:3]] if news_data else []
    sentiment = analyze_sentiment(recent_news)
    
    st.subheader("📰 อารมณ์ข่าวต่างประเทศ")
    st.markdown(f"**สรุปทิศทาง:** {sentiment}")
    
    if recent_news:
        with st.expander("ดูพาดหัวข่าวล่าสุด (ภาษาอังกฤษ)"):
            for i, title in enumerate(recent_news, 1):
                st.write(f"{i}. {title}")

except Exception as e:
    st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูล: {e}")
