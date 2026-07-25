import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go

# ==========================================
# ตั้งค่าหน้าเว็บ
# ==========================================
st.set_page_config(page_title="Gold Pro Analyzer", page_icon="🥇", layout="centered")

# ==========================================
# ฟังก์ชันคำนวณต่างๆ
# ==========================================
def add_indicators(df):
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # MACD
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    # EMA (Dynamic Support/Resistance)
    df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
    
    return df

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
        return {'R2': 0, 'R1': 0, 'PP': 0, 'S1': 0, 'S2': 0}

@st.cache_data(ttl=60)
def fetch_data():
    gold = yf.Ticker("GC=F")
    # ดึงข้อมูลมา 3 เดือนเพื่อวาดกราฟ
    df_d = gold.history(period="3mo", interval="1d")
    df_w = gold.history(period="6mo", interval="1wk")
    df_m = gold.history(period="1y", interval="1mo")
    
    # ป้องกัน Error หากดึงข่าวไม่ได้
    try:
        news_raw = gold.news
        news_list = []
        for n in news_raw:
            # บางที Yahoo เปลี่ยน Key เป็น 'title' หรืออยู่ใน 'content'
            title = n.get('title', '')
            if not title and 'content' in n:
                title = n['content'].get('title', '')
            if title:
                news_list.append(title)
    except:
        news_list = []
        
    return df_d, df_w, df_m, news_list

# ==========================================
# ส่วนแสดงผล UI
# ==========================================
st.title("🥇 XAU/USD Pro Analyzer")
st.caption(f"อัปเดตล่าสุด: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

if st.button("🔄 ดึงข้อมูลล่าสุด"):
    st.cache_data.clear()

try:
    df_daily, df_weekly, df_monthly, recent_news = fetch_data()
    
    if df_daily.empty:
        st.error("ไม่สามารถเชื่อมต่อข้อมูลตลาดได้")
        st.stop()
        
    df_daily = add_indicators(df_daily)
    current_price = df_daily.iloc[-1]['Close']
    change = current_price - df_daily.iloc[-2]['Close']
    
    # 1. แสดงราคาปัจจุบัน
    st.metric(label="ราคาทองฟิวเจอร์สปัจจุบัน (USD/oz)", value=f"{current_price:.2f}", delta=f"{change:.2f}")
    
    # 2. กราฟแท่งเทียน (Candlestick)
    st.subheader("📈 กราฟแนวโน้ม (Daily)")
    fig = go.Figure(data=[go.Candlestick(
        x=df_daily.index,
        open=df_daily['Open'], high=df_daily['High'],
        low=df_daily['Low'], close=df_daily['Close'],
        name='Price'
    )])
    fig.add_trace(go.Scatter(x=df_daily.index, y=df_daily['EMA20'], mode='lines', name='EMA 20', line=dict(color='blue', width=1)))
    fig.add_trace(go.Scatter(x=df_daily.index, y=df_daily['EMA50'], mode='lines', name='EMA 50', line=dict(color='orange', width=1)))
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=350, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    # 3. สรุปจุดเข้า-ออกสำคัญ (Trading Zones)
    st.subheader("🎯 จุดเข้า/จุดออกสำคัญ (Key Levels)")
    
    ema20 = df_daily.iloc[-1]['EMA20']
    ema50 = df_daily.iloc[-1]['EMA50']
    p_day = calculate_pivots(df_daily, -2)
    p_week = calculate_pivots(df_weekly, -2)
    p_month = calculate_pivots(df_monthly, -2)

    t1, t2 = st.tabs(["🔥 Day Trade (สั้น)", "🏛️ Swing Trade (กลาง-ยาว)"])
    
    with t1:
        st.write("**โซนแนวต้าน (พิจารณาขาย/Take Profit)**")
        st.error(f"🔴 R2 (รายวัน): {p_day['R2']:,.1f}")
        st.error(f"🟠 R1 (รายวัน): {p_day['R1']:,.1f}")
        st.write("---")
        st.write("**โซนแนวรับ (พิจารณาซื้อ/Cut Loss)**")
        st.success(f"🟢 S1 (รายวัน): {p_day['S1']:,.1f}")
        st.success(f"🔵 S2 (รายวัน): {p_day['S2']:,.1f}")
        st.info(f"เส้น EMA 20 (แนวรับ/ต้านเคลื่อนที่): {ema20:,.1f}")

    with t2:
        st.write("**แนวต้านสำคัญภาพใหญ่**")
        st.error(f"🔴 แนวต้านรายเดือน (Monthly R1): {p_month['R1']:,.1f}")
        st.warning(f"🟠 แนวต้านรายสัปดาห์ (Weekly R1): {p_week['R1']:,.1f}")
        st.write("---")
        st.write("**แนวรับสำคัญภาพใหญ่**")
        st.success(f"🟢 แนวรับรายสัปดาห์ (Weekly S1): {p_week['S1']:,.1f}")
        st.info(f"🔵 แนวรับรายเดือน (Monthly S1): {p_month['S1']:,.1f}")
        st.info(f"เส้น EMA 50 (แยกเทรนด์หลัก): {ema50:,.1f}")

    # 4. โมเมนตัม
    st.subheader("📊 อินดิเคเตอร์ (Momentum)")
    current_rsi = df_daily.iloc[-1]['RSI']
    macd = df_daily.iloc[-1]['MACD']
    signal = df_daily.iloc[-1]['Signal']
    
    c1, c2 = st.columns(2)
    with c1:
        rsi_stat = "🔥 ซื้อมากไป" if current_rsi >= 70 else "🥶 ขายมากไป" if current_rsi <= 30 else "ปกติ"
        st.metric("RSI (14)", f"{current_rsi:.1f}", rsi_stat, delta_color="off")
    with c2:
        macd_stat = "กระทิง (Bullish)" if macd > signal else "หมี (Bearish)"
        st.metric("MACD", macd_stat, delta_color="off")

    # 5. ข่าวสาร
    st.subheader("📰 ข่าวเศรษฐกิจล่าสุด (ส่งผลต่อราคาทอง)")
    if recent_news:
        for i, title in enumerate(recent_news[:5], 1):
            st.write(f"- {title}")
    else:
        st.info("ไม่มีข่าวใหม่ที่ดึงข้อมูลได้ในขณะนี้")

except Exception as e:
    st.error(f"ระบบขัดข้องชั่วคราว: {e}")
