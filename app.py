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

# 2. 계약일자 입력 필드
today = date.today()
last_week = today - timedelta(days=7)
contract_dates = st.sidebar.date_input(
    label="계약일자",
    value=(last_week, today),
    help="계약 시작일과 종료일을 선택하세요."
)
contract_start_date = contract_dates[0] if isinstance(contract_dates, tuple) else today

# 3. 결산연월(자동으로 말일로 설정)
# 선택된 달의 마지막 날을 계산하는 함수
def get_last_day_of_month(year, month):
    return calendar.monthrange(year, month)[1]

settlement_date = st.sidebar.date_input(
    label="결산연월",
    min_value=contract_start_date, # 계약 시작일 이전으로 선택 불가능하게 설정
    help="결산일을 선택하세요. 선택된 월의 마지막 날로 자동 설정됩니다."
)

# 선택된 날짜의 연도와 월을 가져와 마지막 날로 변경
settlement_date_corrected = settlement_date.replace(day=get_last_day_of_month(settlement_date.year, settlement_date.month))
st.sidebar.write(f"최종 결산일: **{settlement_date_corrected.isoformat()}**")

# 4. 통화선도환율(소수점 두 자리) 입력 필드
st.sidebar.number_input(
    label="통화선도환율",
    min_value=0.0,
    format="%.2f",
    help="통화선도환율을 소수점 둘째 자리까지 입력하세요."
)

# 5. 현물환율(소수점 두 자리) 입력 필드
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
