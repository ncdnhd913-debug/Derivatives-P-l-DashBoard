import streamlit as st
from datetime import date, timedelta
import calendar

# 전체 페이지 설정
st.set_page_config(
    page_title="파생상품 손익효과 분석",
    layout="wide"
)

# 사이드바 구성
st.sidebar.header("파생상품 거래 정보")

# 1. 거래금액($) 입력 필드
st.sidebar.number_input(
    label="거래금액($)",
    min_value=0.0,
    format="%.2f",
    help="거래에 사용된 금액을 달러($) 단위로 입력하세요."
)

# 2. 기일물 선택 메뉴
tenor_options = {
    "1주일물": 7,
    "1개월물": 30,
    "2개월물": 60,
    "3개월물": 90,
    "6개월물": 180,
    "9개월물": 270,
    "1년물": 365,
    "2년물": 365 * 2,
    "3년물": 365 * 3,
}
selected_tenor = st.sidebar.selectbox(
    label="기일물",
    options=list(tenor_options.keys()),
    index=2, # 기본값: 2개월물
    help="계약 기간(기일물)을 선택하세요."
)
tenor_days = tenor_options[selected_tenor]

# 3. 계약일자 입력 필드
start_date = st.sidebar.date_input(
    label="계약 시작일자",
    value=date.today(),
    help="계약 시작일을 선택하세요."
)
end_date = start_date + timedelta(days=tenor_days)
st.sidebar.text_input(
    label="계약 종료일자",
    value=end_date.isoformat(),
    disabled=True,
    help="기일물에 따라 자동으로 계산된 계약 종료일자입니다."
)

# 4. 결산연월(자동으로 말일로 설정)
# 선택된 달의 마지막 날을 계산하는 함수
def get_last_day_of_month(year, month):
    return calendar.monthrange(year, month)[1]

# 연도와 월을 별도로 선택할 수 있도록 변경
st.sidebar.subheader("결산연월")
settlement_year = st.sidebar.selectbox(
    label="연도",
    options=list(range(start_date.year, start_date.year + 10)),
    index=0
)
settlement_month = st.sidebar.selectbox(
    label="월",
    options=list(range(1, 13)),
    index=date.today().month - 1
)

# 선택된 연도와 월로 결산일 자동 설정 (해당 월의 마지막 날)
settlement_date_corrected = date(settlement_year, settlement_month, get_last_day_of_month(settlement_year, settlement_month))
st.sidebar.write(f"최종 결산일: **{settlement_date_corrected.isoformat()}**")

# 5. 통화선도환율(소수점 두 자리) 입력 필드
st.sidebar.number_input(
    label="통화선도환율",
    min_value=0.0,
    format="%.2f",
    help="통화선도환율을 소수점 둘째 자리까지 입력하세요."
)

# 6. 현물환율(소수점 두 자리) 입력 필드
st.sidebar.number_input(
    label="현물환율",
    min_value=0.0,
    format="%.2f",
    help="현재 시장 환율(현물환율)을 소수점 둘째 자리까지 입력하세요."
)

# 메인 화면 구성
st.title("📈 파생상품 손익효과 분석 대시보드")
st.write("왼쪽 사이드바에서 거래 정보를 입력하면, 이 곳에 손익효과 분석 결과가 도표로 나타납니다.")

# 예시로 빈 도표를 표시할 수 있는 자리
# st.line_chart(...)
# st.bar_chart(...)
