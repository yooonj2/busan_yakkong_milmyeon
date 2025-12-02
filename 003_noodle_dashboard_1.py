import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import altair as alt
import plotly.graph_objects as go

# -------------------------------------------------------------------------
# 0. 페이지 설정
# -------------------------------------------------------------------------
st.set_page_config(layout="wide", page_title="매출 대시보드")

# -------------------------------------------------------------------------
# 1. 데이터 로딩
# -------------------------------------------------------------------------
@st.cache_data
def load_data():
    # 실제 데이터 로드
    before = pd.read_csv(r"C:\Users\한윤지\Desktop\BP\001_data\01_noodle_data\before.csv")
    after = pd.read_csv(r"C:\Users\한윤지\Desktop\BP\001_data\01_noodle_data\after_with_predictions.csv")
    corr_df = pd.read_csv(r"C:\Users\한윤지\Desktop\BP\001_data\01_noodle_data\monthly_correlation.csv")
    
    corr_df.sort_values("corr", ascending=False,inplace=True)
    before['tm'] = pd.to_datetime(before['tm'])
    after['tm'] = pd.to_datetime(after['tm'])      
    
    # 매출 세부 품목 컬럼명 (df에 실제로 존재한다고 가정)
    categories = [
        'hot_milmyeon', 'milmyeon_with_mandu', 'milmyeon_only', 
        'delivery', 'side_menu', 'drinks_alcohol', 
        'product_sales', 'kalguksu', 'takeaway'
    ]

    weather_cols = ['avgTa', 'avgWs', 'avgRhm', 'sumGsr', 'avgTca', 'sumRn','diurnal_range', 'feel_temp'] #그대그때 변경 중

    return before, after, corr_df, categories,weather_cols

before, after, corr_df, categories,weather_cols = load_data()

# -------------------------------------------------------------------------
# 2. 레이아웃 및 사이드바 설정
# -------------------------------------------------------------------------
with st.sidebar:
    st.title("📊 매출 대시보드")
    st.markdown("---")
    st.header("info")
    st.info("오늘은 10월 31일입니다")

# -------------------------------------------------------------------------
# 섹션 1: 월별 · 메뉴별 날씨 상관관계 분석
# -------------------------------------------------------------------------
st.header("1. 월별 · 메뉴별 날씨 상관관계 분석")

# 월 선택
months = sorted(corr_df["month"].unique())

# 메뉴 선택 (total 또는 item-level)
menu_options = ["total", "ALL categories"]

# 토글 병렬
col1, col2 = st.columns(2)

with col1:
    selected_month = st.selectbox("🗓 월(month) 선택", months)

with col2:
    selected_menu = st.selectbox("🍜 메뉴 선택", menu_options)
# ---------------------------------------------------
# 2) 데이터 필터링
# ---------------------------------------------------
df_filtered = corr_df[corr_df["month"] == selected_month]

if selected_menu == "ALL categories":
    # 카테고리 전체 조회
    df_filtered = df_filtered[df_filtered["menu"].isin(categories)]
else:
    # 선택한 하나의 메뉴만 조회
    df_filtered = df_filtered[df_filtered["menu"] == selected_menu]

# ---------------------------------------------------
# 3) 시각화
# ---------------------------------------------------
if df_filtered.empty:
    st.warning("선택한 조건에 해당하는 데이터가 없습니다.")
else:
    if selected_menu == "ALL categories":
        # 👉 ALL categories: 메뉴별로 한 번에 보기
        # x: menu, 색: weather → 카테고리별 비교
        fig = px.bar(
            df_filtered,
            x="menu",
            y="corr",
            color="weather",
            barmode="group",
            text="corr",
            title=f"📌 월={selected_month}, 메뉴=ALL categories"
        )
    else:
        # 👉 total 또는 개별 메뉴: weather별 bar
        fig = px.bar(
            df_filtered,
            x="weather",
            y="corr",
            color="weather",
            text="corr",
            title=f"📌 월={selected_month}, 메뉴={selected_menu}"
        )

    fig.update_traces(texttemplate="%{text:.3f}", textposition="outside")
    fig.update_layout(
    yaxis_title="Correlation",
    xaxis_title="Menu" if selected_menu == "ALL categories" else "Weather",
    height=550
)


    st.plotly_chart(fig, use_container_width=True)
    show_yoy = st.toggle("📄 필터링된 데이터(토글을 켜서 테이블 확인하기)", value=False)  # 초기값 Off

    if show_yoy:
        st.dataframe(df_filtered)
# -------------------------------------------------------------------------
# 섹션 2: 카테고리별 매출 예측
# -------------------------------------------------------------------------
# -------------------------------------------------------------------
# 1. 예측 구간 + 전년동기 합계 계산
#    - 예측 기간: after의 tm 범위
#    - 전년동기: 예측기간에서 1년 뺀 구간의 실제 매출 합
# -------------------------------------------------------------------
fc_start = after['tm'].min()
fc_end   = after['tm'].max()

last_year_start = fc_start - pd.DateOffset(years=1)
last_year_end   = fc_end   - pd.DateOffset(years=1)

this_year_pred = after['predicted_total'].sum()

before_mask = (before['tm'] >= last_year_start) & (before['tm'] <= last_year_end)
last_year_actual = before.loc[before_mask, 'total'].sum()

yoy_diff = this_year_pred - last_year_actual          # 금액 차이
yoy_pct  = (yoy_diff / last_year_actual) * 100 if last_year_actual != 0 else None

# -------------------------------------------------------------------
# 2. 실제 + 예측 그래프 (왼쪽 큰 박스)
# -------------------------------------------------------------------
last_month_start = before['tm'].max() - pd.DateOffset(days=30)
before_last_month = before[before['tm'] >= last_month_start]
before_plot = before_last_month[['tm', 'total']]
after_plot = after[['tm', 'predicted_total']]

# 실제+예측 데이터 병합
plot_df = pd.concat([before_plot, after_plot], axis=0).sort_values('tm')

fig = go.Figure()

# 실제 (초록색)
fig.add_trace(go.Scatter(
    x=plot_df['tm'],
    y=plot_df['total'],
    mode='lines+markers',
    name='Actual',
    line=dict(color='green', width=2),
    marker=dict(color='green', size=5)
))

# 예측 (빨간색)
fig.add_trace(go.Scatter(
    x=plot_df['tm'],
    y=plot_df['predicted_total'],
    mode='lines+markers',
    name='Forecast',
    line=dict(color='red', width=2),
    marker=dict(color='red', size=5)
))

fig.update_layout(
    title="Actual vs Forecast",
    xaxis_title="Date",
    yaxis_title="Sales"
)

# -------------------------------------------------------------------
# 3. MAE, MAPE 값 (👉 너가 직접 입력하는 부분)
# -------------------------------------------------------------------
MAE_VALUE  = 100807.50   # TODO: 실제 계산값으로 수정
MAPE_VALUE = 31.59   # TODO: 실제 계산값으로 수정 (%)

# -------------------------------------------------------------------
# 4. 레이아웃 구성
#    왼쪽: 예측 그래프 / 오른쪽: MAE·MAPE + 전년동기 대비
# -------------------------------------------------------------------
st.subheader("2. 매출 예측")
st.write("📅 예측 기간:", fc_start.date(), "~", fc_end.date())
left_col, right_col = st.columns([4, 1])

# ✅ 왼쪽: 예측 그래프
with left_col:
    st.plotly_chart(fig, use_container_width=True)

# ✅ 오른쪽: MAE/MAPE + 전년동기 대비 박스
with right_col:
    # MAE / MAPE 박스
    st.markdown(
        f"""
        <div style="background-color:#2A3439;
                    padding:16px;
                    border-radius:4px;
                    color:white;
                    text-align:center;
                    margin-bottom:8px;">
            <div style="font-weight:bold; margin-bottom:8px;">MAE / MAPE</div>
            <div>MAE : {MAE_VALUE:,.2f}원</div>
            <div>MAPE : {MAPE_VALUE:.2f}%</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 전년동기 대비 차이 박스
    if yoy_pct is not None:
        st.markdown(
            f"""
            <div style="background-color:#2A3439;
                        padding:16px;
                        border-radius:4px;
                        color:white;
                        text-align:center;">
                <div style="font-weight:bold; margin-bottom:8px;">전년동기({last_year_start.date()}) 대비</div>
                <div>{yoy_diff:,.0f} ({yoy_pct:+.1f}%)</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            """
            <div style="background-color:#0b4f6c;
                        padding:16px;
                        border-radius:4px;
                        color:white;
                        text-align:center;">
                <div style="font-weight:bold; margin-bottom:8px;">전년동기 대비 차이</div>
                <div>전년 데이터가 없어 계산할 수 없습니다.</div>
            </div>
            """,
            unsafe_allow_html=True
        )

# -------------------------------------------------------------------------
# 섹션 3: 카테고리별 매출 스트림그래프
# -------------------------------------------------------------------------
st.header("3. 카테고리별 매출 추이")
min_date = before["tm"].min()
max_date = before["tm"].max()

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("조회 시작일", min_date.date())
with col2:
    end_date = st.date_input("조회 종료일", max_date.date())

# 날짜 유효성 체크
if start_date > end_date:
    st.error("❗ 종료일이 시작일보다 앞에 있습니다.")
    st.stop()

# -----------------------------
# 3) 데이터 필터링
# -----------------------------
# 🔹 date → Timestamp 로 한 번 변환
start_ts = pd.to_datetime(start_date)
end_ts   = pd.to_datetime(end_date)
mask = (before["tm"] >= start_ts) & (before["tm"] <= end_ts)
df_filtered = before.loc[mask].copy()

st.write("📅 선택된 기간:", start_date, "~", end_date)

df_melt = df_filtered.melt(id_vars="tm", value_vars=categories,
                           var_name="category", value_name="sales")

# ------------------------------------------
# 5. Altair Streamgraph (ThemeRiver)
# ------------------------------------------
chart = (
    alt.Chart(df_melt)
    .mark_area()
    .encode(
        x="tm:T",
        y=alt.Y("sales:Q", stack="center"),   # ⭐ 핵심: center = streamgraph 중심 기준
        color="category:N",
        tooltip=["tm", "category", "sales"]
    )
    .properties(
        width="container",
        height=400,
        title="📈 카테고리별 매출 스트림그래프 (Streamgraph)"
    )
)

st.altair_chart(chart, use_container_width=True)