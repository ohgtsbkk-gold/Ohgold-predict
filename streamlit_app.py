import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go

# ==========================================
# ตั้งค่าหน้าเว็บ
# ==========================================
st.set_page_config(page_title="Gold Pro Analyzer V9", page_icon="🥇", layout="wide")

# ==========================================
# ฟังก์ชันคำนวณ Indicator
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
    
    df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
    return df

@st.cache_data(ttl=300)
def fetch_market_data():
    tickers = {
        "Gold": "GC=F",
        "DXY": "DX-Y.NYB",
        "Oil": "CL=F",
        "S&P500": "^GSPC",
        "Dow": "^DJI",
        "Nasdaq": "^IXIC"
    }
    data = {}
    for name, symbol in tickers.items():
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="3mo", interval="1d")
            if not df.empty and 'Close' in df.columns:
                df = df.dropna(subset=['Close'])
                if not df.empty:
                    data[name] = df
        except Exception:
            pass
            
    news_list = []
    try:
        gold_ticker = yf.Ticker("GC=F")
        if hasattr(gold_ticker, 'news') and gold_ticker.news:
            for n in gold_ticker.news:
                title = n.get('title', '')
                if not title and 'content' in n:
                    title = n['content'].get('title', '')
                if title:
                    news_list.append(title)
    except Exception:
        pass
        
    return data, news_list

# ==========================================
# UI: Sidebar - เครื่องมือคำนวณความเสี่ยง
# ==========================================
with st.sidebar:
    st.header("🧮 เครื่องมือคำนวณความเสี่ยง")
    capital = st.number_input("เงินทุน (USD):", min_value=10.0, value=1000.0, step=100.0)
    risk_pct = st.slider("ความเสี่ยงที่รับได้ (%):", min_value=0.5, max_value=10.0, value=2.0, step=0.5)
    
    entry_price = st.number_input("จุดเข้า (Entry):", min_value=0.0, value=2000.0)
    sl_price = st.number_input("จุดตัดขาดทุน (Stop Loss):", min_value=0.0, value=1990.0)
    
    if entry_price > 0 and sl_price > 0 and entry_price != sl_price:
        risk_amount = capital * (risk_pct / 100)
        stop_loss_points = abs(entry_price - sl_price)
        lot_size = risk_amount / (stop_loss_points * 100)
        
        st.write("---")
        st.error(f"💸 ขาดทุนสูงสุด: ${risk_amount:.2f}")
        st.warning(f"📏 ระยะ SL: {stop_loss_points:.2f} จุด")
        st.success(f"🎯 ขนาด Lot: {lot_size:.3f}")

# ==========================================
# UI: Main Page
# ==========================================
st.title("🥇 XAU/USD Pro Analyzer V9")
st.caption("ระบบวิเคราะห์ราคาทองคำ ตลาดสากล แนวรับ-แนวต้าน และคำแนะนำการซื้อขายแบบเรียลไทม์")

try:
    data, recent_news = fetch_market_data()
    
    if "Gold" not in data or data["Gold"].empty:
        st.error("ไม่สามารถโหลดข้อมูลราคาทองคำได้ในขณะนี้ กรุณากดรีเฟรชอีกครั้ง")
        st.stop()
        
    df_gold = add_indicators(data["Gold"])
    
    # 1. Macro Dashboard (6 คอลัมน์)
    cols = st.columns(6)
    assets = [
        ("Gold", "ทองคำ", "🥇"), 
        ("DXY", "ดอลลาร์ (DXY)", "💵"), 
        ("Oil", "น้ำมัน WTI", "🛢️"), 
        ("S&P500", "S&P 500", "📈"), 
        ("Dow", "Dow Jones", "📉"),
        ("Nasdaq", "Nasdaq", "💻")
    ]
    
    for i, (key, name, icon) in enumerate(assets):
        if key in data and len(data[key]) >= 2:
            try:
                curr = float(data[key]['Close'].iloc[-1])
                prev = float(data[key]['Close'].iloc[-2])
                diff = curr - prev
                cols[i].metric(f"{icon} {name}", f"{curr:,.2f}", f"{diff:,.2f}")
            except Exception:
                cols[i].metric(f"{icon} {name}", "N/A", "N/A")
        else:
            cols[i].metric(f"{icon} {name}", "N/A", "N/A")
            
    st.write("---")

    # 2. กราฟทอง & Fibonacci
    st.subheader("📊 กราฟแนวโน้ม พร้อม Fibonacci Retracement")
    
    recent_30 = df_gold.tail(30)
    max_price = recent_30['High'].max()
    min_price = recent_30['Low'].min()
    diff_val = max_price - min_price
    
    fib_levels = {
        "0.0% (High)": max_price,
        "23.6%": max_price - 0.236 * diff_val,
        "38.2%": max_price - 0.382 * diff_val,
        "50.0%": max_price - 0.5 * diff_val,
        "61.8%": max_price - 0.618 * diff_val,
        "78.6%": max_price - 0.786 * diff_val,
        "100.0% (Low)": min_price
    }

    fig = go.Figure(data=[go.Candlestick(
        x=df_gold.index, open=df_gold['Open'], high=df_gold['High'],
        low=df_gold['Low'], close=df_gold['Close'], name='Price'
    )])
    fig.add_trace(go.Scatter(x=df_gold.index, y=df_gold['EMA20'], mode='lines', name='EMA 20', line=dict(color='blue', width=1)))
    fig.add_trace(go.Scatter(x=df_gold.index, y=df_gold['EMA50'], mode='lines', name='EMA 50', line=dict(color='orange', width=1)))
    
    colors = ['red', 'orange', 'yellow', 'green', 'blue', 'purple', 'black']
    for (level_name, price), color in zip(fib_levels.items(), colors):
        fig.add_hline(y=price, line_dash="dot", line_color=color, annotation_text=level_name, annotation_position="top left")

    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=500, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    # ==========================================
    # 3. คำนวณแนวรับ - แนวต้าน (Pivot Points)
    # ==========================================
    st.subheader("🛡️ แนวรับ - แนวต้าน สำคัญ (Pivot Points)")
    last_row = df_gold.iloc[-2]  # ใช้แท่งเทียนวันก่อนหน้าคำนวณ
    p_high = last_row['High']
    p_low = last_row['Low']
    p_close = last_row['Close']
    
    pivot = (p_high + p_low + p_close) / 3
    r1 = (2 * pivot) - p_low
    s1 = (2 * pivot) - p_high
    r2 = pivot + (p_high - p_low)
    s2 = pivot - (p_high - p_low)

    r_col1, r_col2, r_col3, r_col4, r_col5 = st.columns(5)
    r_col1.metric("แนวต้าน 2 (R2)", f"{r2:,.2f}")
    r_col2.metric("แนวต้าน 1 (R1)", f"{r1:,.2f}")
    r_col3.metric("จุดหมุน (Pivot)", f"{pivot:,.2f}")
    r_col4.metric("แนวรับ 1 (S1)", f"{s1:,.2f}")
    r_col5.metric("แนวรับ 2 (S2)", f"{s2:,.2f}")

    st.write("---")

    # ==========================================
    # 4. หน้าปัด Gauge และคำแนะนำการซื้อขาย
    # ==========================================
    st.subheader("🧭 หน้าปัดสรุปสัญญาณเทรดและคำแนะนำ")
    trade_style = st.radio("เลือกสไตล์การเทรดของคุณ:", ["Day Trade (สั้น)", "Swing Trade (กลาง-ยาว)"], horizontal=True)
    
    curr_close = df_gold['Close'].iloc[-1]
    ema20 = df_gold['EMA20'].iloc[-1]
    ema50 = df_gold['EMA50'].iloc[-1]
    rsi = df_gold['RSI'].iloc[-1]
    macd = df_gold['MACD'].iloc[-1]
    sig = df_gold['Signal'].iloc[-1]
    
    col_gauge, col_advice = st.columns([1, 1])
    
    if trade_style == "Day Trade (สั้น)":
        score = 0
        if rsi > 65: score -= 30
        elif rsi < 35: score += 30
        if macd > sig: score += 50
        else: score -= 50
        gauge_val = 50 + (score / 2)
        title_text = "Day Trade Momentum (RSI + MACD)"
        
        # คำแนะนำ Day Trade
        with col_advice:
            st.markdown("### 💬 คำแนะนำสำหรับ Day Trade")
            st.write(f"- **RSI (14):** `{rsi:.2f}`")
            st.write(f"- **MACD Status:** `{'MACD ตัด Signal ขึ้น (Bullish)' if macd > sig else 'MACD ตัด Signal ลง (Bearish)'}`")
            if rsi > 70:
                st.error("🚨 **สถานะ: Overbought (ซื้อมากเกินไป)** ระวังแรงขายทำกำไรระยะสั้น หลีกเลี่ยงการไล่ราคาซื้อ")
            elif rsi < 30:
                st.success("🟢 **สถานะ: Oversold (ขายมากเกินไป)** เป็นจุดเฝ้าระวังเพื่อหาจังหวะ Buy เมื่อราคาเริ่มกลับตัว")
            elif macd > sig:
                st.success("📈 **คำแนะนำ:** โมเมนตัมขาขึ้นระยะสั้นได้เปรียบ หาจังหวะ Buy เมื่อราคาย่อตัวเข้าใกล้แนวรับ S1")
            else:
                st.error("📉 **คำแนะนำ:** โมเมนตัมขาลงระยะสั้นกดดัน หาจังหวะ Sell ตามแนวต้าน R1 หรือรอสัญญาณนิ่ง")
    else:
        score = 0
        if curr_close > ema20 and ema20 > ema50:
            score = 80 
        elif curr_close < ema20 and ema20 < ema50:
            score = 20 
        else:
            score = 50 
        gauge_val = score
        title_text = "Swing Trade Trend (EMA 20 & 50 Alignment)"
        
        # คำแนะนำ Swing Trade
        with col_advice:
            st.markdown("### 💬 คำแนะนำสำหรับ Swing Trade")
            st.write(f"- **ราคาปัจจุบัน:** `${curr_close:,.2f}`")
            st.write(f"- **EMA 20 / EMA 50:** `{ema20:,.2f}` / `{ema50:,.2f}`")
            if curr_close > ema20 and ema20 > ema50:
                st.success("🚀 **คำแนะนำ:** แนวโน้มหลักเป็น **Uptrend ขาขึ้นชัดเจน** ถือสถานะซื้อ (Hold Buy) หรือย่อซื้อสะสม (Buy on Dip) ใช้ EMA 20 เป็นจุด Stop Loss")
            elif curr_close < ema20 and ema20 < ema50:
                st.error("⚠️ **คำแนะนำ:** แนวโน้มหลักเป็น **Downtrend ขาลง** ควรงดการถือ Long ยาว หรือเน้นหาจังหวะ Sell เมื่อราคาเด้งชนแนวต้าน")
            else:
                st.warning("⚖️ **คำแนะนำ:** ตลาดอยู่ในช่วง **ไซด์เวย์ / เลือกทาง** รอดูความชัดเจนของการเบรกกรอบแนวรับ-แนวต้านสำคัญก่อนออกไม้ใหญ่")

    with col_gauge:
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = gauge_val,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': title_text},
            gauge = {
                'axis': {'range': [0, 100]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 35], 'color': "red"},
                    {'range': [35, 65], 'color': "lightgray"},
                    {'range': [65, 100], 'color': "green"}],
                'threshold': {
                    'line': {'color': "black", 'width': 4},
                    'thickness': 0.75,
                    'value': gauge_val}}))
        fig_gauge.update_layout(height=260, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_gauge, use_container_width=True)

    # ==========================================
    # 5. ข่าวตลาดล่าสุด
    # ==========================================
    st.write("---")
    st.subheader("📰 ข่าวตลาดล่าสุด")
    if recent_news:
        for title in recent_news[:5]:
            st.write(f"- {title}")
    else:
        st.info("ขณะนี้ระบบยังไม่พบลิงก์ข่าวใหม่ หรือ Yahoo Finance ปิดกั้นการดึงข้อมูลชั่วคราว")

except Exception as e:
    st.error(f"เกิดข้อผิดพลาดในการประมวลผลข้อมูล: {e}")
