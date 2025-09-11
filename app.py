import altair as alt
import pandas as pd
import streamlit as st

# Streamlit 앱 제목
st.title("수익 및 손실 (P&L) 대시보드")

# 예시 데이터 생성
# 실제 사용자의 P&L 데이터로 대체해야 합니다.
data = {
    'Category': ['Revenue', 'Cost of Goods Sold', 'Operating Expenses', 'Net Income'],
    'Value': [50000, -25000, -15000, 10000]
}
df = pd.DataFrame(data)

# 'Net Income'을 강조하기 위해 색상 구분
color_domain = ['Revenue', 'Cost of Goods Sold', 'Operating Expenses', 'Net Income']
color_range = ['#4c78a8', '#f58518', '#e45756', '#54a24b']

# 막대 차트 생성
chart = alt.Chart(df).mark_bar().encode(
    x=alt.X(
        'Category:N',
        axis=alt.Axis(title="카테고리"),
        # 'band' 인수는 잘못된 사용이며,
        # 막대 사이의 간격은 'paddingInner'로 조절합니다.
        scale=alt.Scale(
            domain=color_domain,
            paddingInner=0.5  # 막대 사이의 간격 (0.5는 막대 너비의 50%를 의미)
        )
    ),
    y=alt.Y('Value:Q', axis=alt.Axis(title="값")),
    # 값에 따라 색상 인코딩
    color=alt.Color('Category:N', scale=alt.Scale(domain=color_domain, range=color_range)),
    tooltip=[
        alt.Tooltip('Category', title='카테고리'),
        alt.Tooltip('Value', title='값', format=',d')
    ]
).properties(
    title="P&L 차트"
).interactive() # 상호작용 기능 추가

# Streamlit에 차트 표시
st.altair_chart(chart, use_container_width=True)

# 추가 정보 표시
st.markdown("""
### 대시보드 정보
이 대시보드는 P&L 데이터를 시각화합니다.
- **Revenue**: 총 수입
- **Cost of Goods Sold**: 상품 원가
- **Operating Expenses**: 운영 비용
- **Net Income**: 순이익
""")
