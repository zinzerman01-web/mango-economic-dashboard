import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime

# --- 보안 설정: Secrets에서 API 키 가져오기 ---
# 실제 키는 배포 후 Streamlit Cloud 설정창(Secrets)에서 입력할 예정입니다.
FRED_KEY = st.secrets["FRED_API_KEY"]
ECOS_KEY = st.secrets["ECOS_API_KEY"]

# --- 페이지 및 스타일 설정 ---
st.set_page_config(page_title="망고 통합 경제 터미널", layout="wide")

st.markdown("""
    <style>
    .section-card {
        background-color: white; padding: 18px; border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.07); border-top: 5px solid #2c3e50;
        margin-bottom: 20px;
    }
    .metric-container { display: flex; justify-content: space-between; align-items: center; }
    .price { font-size: 1.1rem; font-weight: 800; cursor: help; }
    .up { color: #e74c3c; font-weight: bold; }
    .down { color: #3498db; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 데이터 수집 및 차트 함수 (캐싱 적용: 수천 명 접속 대비) ---
@st.cache_data(ttl=600) # 10분 동안 데이터 보관 (API 호출 횟수 절약)
def fetch_yf(ticker, name):
    try:
        df = yf.download(ticker, period="1mo", progress=False)
        curr, prev = df['Close'].iloc[-1], df['Close'].iloc[-2]
        chg = ((curr - prev) / prev) * 100
        return {"name": name, "val": curr, "pct": f"{chg:+.2f}%", "up": chg > 0, "history": df['Close'].tolist(), "date": df.index[-1].strftime('%Y-%m-%d')}
    except: return None

@st.cache_data(ttl=3600) # 금리 등은 1시간 단위 보관
def fetch_fred(series_id, name):
    url = f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&api_key={FRED_KEY}&file_type=json&sort_order=desc&limit=30"
    try:
        res = requests.get(url).json()['observations']
        history = [float(x['value']) for x in res if x['value'] != '.'][::-1]
        curr, prev = history[-1], history[-2]
        return {"name": name, "val": curr, "pct": f"{curr-prev:+.2f}", "up": curr > prev, "history": history, "date": res[0]['date']}
    except: return None

# --- 화면 구성 (섹션별 루프) ---
st.title("📊 실시간 경제 지표 통합 터미널")

# 예시 섹션: 시장 금리
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown('<div class="section-card"><h4>🏛️ 주요 시장 금리</h4>', unsafe_allow_html=True)
    d = fetch_fred("DGS10", "미 국채 10Y")
    if d:
        color_cls = "up" if d['up'] else "down"
        st.markdown(f'<div class="metric-container"><span>{d["name"]}</span><span class="price" title="{d["date"]}">{d["val"]:.2f}%</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div style="text-align:right" class="{color_cls}">{"▲" if d["up"] else "▼"} {d["pct"]}</div>', unsafe_allow_html=True)
        # 차트 생략 (공간상)
    st.markdown('</div>', unsafe_allow_html=True)

# (나머지 주식, 환율 항목들도 위와 같은 방식으로 추가...)
