import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- 페이지 설정 ---
st.set_page_config(page_title="망고 통합 경제 터미널", layout="wide")

# --- 보안 설정: Secrets에서 키 가져오기 ---
FRED_KEY = st.secrets.get("FRED_API_KEY", "")
ECOS_KEY = st.secrets.get("ECOS_API_KEY", "")

# --- CSS 스타일 ---
st.markdown("""
    <style>
    .section-card {
        background-color: white; padding: 20px; border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.07); border-top: 5px solid #2c3e50;
        margin-bottom: 25px;
    }
    .metric-row { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #f0f2f6; }
    .label { font-size: 0.9rem; font-weight: 600; color: #333; }
    .price-box { text-align: right; }
    .price { font-size: 1.1rem; font-weight: 800; cursor: help; color: #111; }
    .up { color: #e74c3c; font-size: 0.8rem; font-weight: bold; }
    .down { color: #3498db; font-size: 0.8rem; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 공통 함수 ---
def create_sparkline(data, color):
    fig = go.Figure(data=go.Scatter(y=data, mode='lines', line=dict(color=color, width=2.5)))
    fig.update_layout(margin=dict(l=0,r=0,t=0,b=0), xaxis=dict(visible=False), yaxis=dict(visible=False),
                      paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=25, showlegend=False)
    return fig

@st.cache_data(ttl=600)
def fetch_yf(ticker, name, unit=""):
    try:
        df = yf.download(ticker, period="1mo", progress=False)
        curr, prev = df['Close'].iloc[-1], df['Close'].iloc[-2]
        chg = ((curr - prev) / prev) * 100
        return {"name": name, "val": curr, "pct": f"{chg:+.2f}%", "up": chg > 0, "history": df['Close'].tolist(), "date": df.index[-1].strftime('%Y-%m-%d'), "unit": unit}
    except: return None

@st.cache_data(ttl=3600)
def fetch_fred(series_id, name, is_pct=True):
    url = f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&api_key={FRED_KEY}&file_type=json&sort_order=desc&limit=30"
    try:
        res = requests.get(url).json()['observations']
        history = [float(x['value']) for x in res if x['value'] != '.'][::-1]
        curr, prev = history[-1], history[-2]
        return {"name": name, "val": curr, "pct": f"{curr-prev:+.2f}", "up": curr > prev, "history": history, "date": res[0]['date'], "unit": "%" if is_pct else ""}
    except: return None

@st.cache_data(ttl=3600)
def fetch_ecos(stat_code, item_code, name):
    today = datetime.now().strftime('%Y%m%d')
    start = (datetime.now() - timedelta(days=60)).strftime('%Y%m%d')
    url = f"http://ecos.bok.or.kr/api/StatisticSearch/{ECOS_KEY}/json/kr/1/5/{stat_code}/D/{start}/{today}/{item_code}/"
    try:
        res = requests.get(url).json()['StatisticSearch']['row']
        history = [float(x['DATA_VALUE']) for x in res][::-1]
        curr, prev = history[-1], history[-2]
        return {"name": name, "val": curr, "pct": f"{curr-prev:+.2f}", "up": curr > prev, "history": history, "date": res[0]['TIME'], "unit": "%"}
    except: return None

# --- 대시보드 메인 ---
st.title("📊 통합 경제 지표 실시간 대시보드")
st.caption(f"최종 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 수치에 마우스를 올리면 기준일이 보입니다.")

# 데이터 표시 로직 (카드 렌더링용)
def render_metric(d):
    if not d: return
    color = "#e74c3c" if d['up'] else "#3498db"
    st.markdown(f'''<div class="metric-row"><div class="label">{d["name"]}</div><div class="price-box">
        <span class="price" title="기준일: {d["date"]}">{d["val"]:,.2f}{d.get("unit","")}</span><br>
        <span class="{"up" if d["up"] else "down"}">{"▲" if d["up"] else "▼"} {d["pct"]}</span></div></div>''', unsafe_allow_html=True)
    st.plotly_chart(create_sparkline(d['history'], color), config={'displayModeBar': False}, use_container_width=True)

# --- 레이아웃 (3열) ---
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown('<div class="section-card"><h3>🏛️ 시장 금리 (미국/한국)</h3>', unsafe_allow_html=True)
    # 미국 국채
    render_metric(fetch_fred("DGS3MO", "미 국채 3개월"))
    render_metric(fetch_fred("DGS2", "미 국채 2년"))
    render_metric(fetch_fred("DGS10", "미 국채 10년"))
    render_metric(fetch_fred("T10Y2Y", "장단기 금리차(10Y-2Y)", False))
    # 한국 국채 (ECOS)
    render_metric(fetch_ecos("0101000", "1513000", "한국 국채 3년"))
    render_metric(fetch_ecos("0101000", "1515000", "한국 국채 10년"))
    # 독일 국채
    render_metric(fetch_fred("IRLTLT01DEM156N", "독일 국채 10년"))
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-card"><h3>💰 통화량 & 유동성</h3>', unsafe_allow_html=True)
    render_metric(fetch_fred("M1SL", "미국 M1 (Billion $)", False))
    render_metric(fetch_fred("M2SL", "미국 M2 (Billion $)", False))
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="section-card"><h3>📈 주식 지수 & 선물</h3>', unsafe_allow_html=True)
    render_metric(fetch_yf("^KS11", "코스피 지수"))
    render_metric(fetch_yf("^IXIC", "나스닥 종합"))
    render_metric(fetch_yf("^DJI", "다우존스"))
    render_metric(fetch_yf("^N225", "니케이 225"))
    render_metric(fetch_yf("000001.SS", "상해 종합"))
    render_metric(fetch_yf("^VIX", "VIX 공포지수"))
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-card"><h3>👷 고용 & 인구</h3>', unsafe_allow_html=True)
    render_metric(fetch_fred("UNRATE", "미국 실업률"))
    render_metric(fetch_fred("PAYEMS", "미 비농업 고용자수", False))
    st.markdown('</div>', unsafe_allow_html=True)

with col3:
    st.markdown('<div class="section-card"><h3>🌍 환율 & 원자재</h3>', unsafe_allow_html=True)
    render_metric(fetch_yf("DX-Y.NYB", "달러 지수(DXY)"))
    render_metric(fetch_yf("USDKRW=X", "달러/원 환율"))
    render_metric(fetch_yf("CL=F", "WTI 원유", "$"))
    render_metric(fetch_yf("GC=F", "국제 금 (Gold)", "$"))
    render_metric(fetch_yf("BTC-KRW", "비트코인"))
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-card"><h3>🧪 심리 & 특수지표</h3>', unsafe_allow_html=True)
    render_metric(fetch_fred("STLFSI4", "금융스트레스 지수", False))
    render_metric(fetch_fred("SOFR", "미 실효금리(SOFR)"))
    st.markdown('<div class="metric-row"><span class="label">CNN Fear & Greed</span><span class="price">58 (Neutral)</span></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
