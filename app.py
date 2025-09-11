import streamlit as st
from datetime import date, timedelta
import calendar
import pandas as pd
import locale

# 로케일 설정 (숫자 포맷을 위해)
try:
    locale.setlocale(locale.LC_ALL, 'ko_KR.UTF-8')
except locale.Error:
    st.warning("한국어 로케일 설정을 지원하지 않는 환경입니다. 숫자 포맷이 다르게 보일 수 있습니다.")
    
# 전체 페이지 설정
st.set_page_config(
    page_title="파생상품 손익효과 분석",
    layout="wide"
)

# 세션 상태 초기화
if 'hypothetical_rates' not in st.session_state:
    st.session_state.hypothetical_rates = {}

# 월/년 단위 계약 기간을 정확하게 계산하는 함수
def add_months_to_date(d, months):
    """
    주어진 날짜에 월을 더하여 정확한 날짜를 반환합니다.
    예: 1월 31일에 1개월을 더하면 2월 28일 또는 29일(윤년)이 됩니다.
    """
    year = d.year + (d.month + months - 1) // 12
    month = (d.month + months - 1) % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)

# 사이드바 구성
st.sidebar.header("파생상품 계약 정보")

# 0. 선도환거래종류 선택 메뉴
transaction_type = st.sidebar.selectbox(
    label="선도환거래종류",
    options=["선매도", "선매수"],
    help="거래 종류에 따라 손익 계산 방식이 달라집니다."
)

# 1. 거래금액($) 입력 필드
amount_usd = st.sidebar.number_input(
    label="거래금액($)",
    min_value=0.0,
    format="%.2f",
    help="거래에 사용된 금액을 달러($) 단위로 입력하세요."
)

# 5. 계약환율(소수점 두 자리) 입력 필드 (위치 변경)
contract_rate = st.sidebar.number_input(
    label="계약환율",
    min_value=0.0,
    format="%.2f",
    help="계약 시점의 통화선도환율을 입력하세요."
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

# 3. 계약일자 및 환율 입력 필드
st.sidebar.subheader("파생상품 계약일자")
col_start_date, col_start_rate = st.sidebar.columns(2)
with col_start_date:
    start_date = st.date_input(
        label="계약 시작일자",
        value=date.today(),
        help="계약 시작일을 선택하세요."
    )
with col_start_rate:
    start_spot_rate = st.number_input(
        label="시작 시점 현물환율",
        min_value=0.0,
        format="%.2f",
        help="계약 시작일의 현물환율을 입력하세요."
    )

col_end_date, col_end_rate = st.sidebar.columns(2)
# 기일물에 따라 계약 만기일자 계산
if selected_tenor.endswith("개월물") or selected_tenor.endswith("년물"):
    months_to_add = 0
    if selected_tenor.endswith("개월물"):
        months_to_add = int(selected_tenor.replace("개월물", ""))
    elif selected_tenor.endswith("년물"):
        months_to_add = int(selected_tenor.replace("년물", "")) * 12
    end_date = add_months_to_date(start_date, months_to_add)
else:
    end_date = start_date + timedelta(days=tenor_days)

with col_end_date:
    st.date_input(
        label="계약 만기일자",
        value=end_date,
        disabled=True,
        help="기일물에 따라 자동으로 계산된 계약 만기일자입니다."
    )
with col_end_rate:
    end_spot_rate = st.number_input(
        label="만기 시점 현물환율",
        min_value=0.0,
        format="%.2f",
        help="계약 만료일의 현물환율을 입력하세요."
    )

# 4. 결산연월 및 환율 입력 필드
# 선택된 달의 마지막 날을 계산하는 함수
def get_last_day_of_month(year, month):
    return calendar.monthrange(year, month)[1]

# 결산연월을 계약 기간 내에서만 선택 가능하도록 수정
st.sidebar.subheader("결산연월")
col_settlement_year, col_settlement_month = st.sidebar.columns(2)

# 계약 시작일과 만기일을 기준으로 선택 가능한 연도 목록 생성
last_day_of_end_month = get_last_day_of_month(end_date.year, end_date.month)
end_of_contract_month = date(end_date.year, end_date.month, last_day_of_end_month)

possible_years = list(range(start_date.year, end_of_contract_month.year + 1))
year_index = possible_years.index(date.today().year) if date.today().year in possible_years else 0

with col_settlement_year:
    settlement_year = st.selectbox(
        label="연도",
        options=possible_years,
        index=year_index
    )

# 선택된 연도에 따라 선택 가능한 월 목록 동적 생성
if settlement_year == start_date.year and settlement_year == end_of_contract_month.year:
    possible_months = list(range(start_date.month, end_of_contract_month.month + 1))
elif settlement_year == start_date.year:
    possible_months = list(range(start_date.month, 13))
elif settlement_year == end_of_contract_month.year:
    possible_months = list(range(1, end_of_contract_month.month + 1))
else:
    possible_months = list(range(1, 13))
    
month_index = possible_months.index(date.today().month) if date.today().month in possible_months else 0

with col_settlement_month:
    settlement_month = st.selectbox(
        label="월",
        options=possible_months,
        index=month_index
    )

settlement_date_corrected = date(settlement_year, settlement_month, get_last_day_of_month(settlement_year, settlement_month))
st.sidebar.markdown(f"**최종 결산일:** **`{settlement_date_corrected.isoformat()}`**")

# --- 새로운 기능 추가 ---
# 결산 가능 월별 예상 통화선도환율 입력
st.sidebar.subheader("결산 가능 월별 예상 환율")
st.sidebar.markdown("시나리오 분석을 위해 각 월의 예상 통화선도환율을 입력하세요.")

current_year_scenario = start_date.year
current_month_scenario = start_date.month

while date(current_year_scenario, current_month_scenario, 1) <= end_of_contract_month.replace(day=1):
    month_key = f"{current_year_scenario}-{current_month_scenario}"
    
    # 세션 상태에 값이 없으면 0으로 초기화
    if month_key not in st.session_state.hypothetical_rates:
        st.session_state.hypothetical_rates[month_key] = 0.0

    # 동적으로 환율 입력 필드 생성
    st.session_state.hypothetical_rates[month_key] = st.sidebar.number_input(
        label=f"{current_year_scenario}년 {current_month_scenario}월 통화선도환율",
        min_value=0.0,
        value=st.session_state.hypothetical_rates[month_key],
        format="%.2f",
        key=f"rate_{month_key}"
    )

    current_month_scenario += 1
    if current_month_scenario > 12:
        current_month_scenario = 1
        current_year_scenario += 1

# 메인 화면 구성
st.title("📈 파생상품 손익효과 분석 대시보드")
st.write("왼쪽 사이드바에서 계약 정보를 입력하고 **'손익 분석 실행'** 버튼을 누르세요.")

# 손익 분석 실행 버튼
if st.sidebar.button("손익 분석 실행"):
    # 결산일이 계약 기간 내에 있는지 확인
    if settlement_date_corrected < start_date or settlement_date_corrected > end_of_contract_month:
        st.error("결산일은 계약 시작일과 만기일이 속한 달의 마지막 날 사이여야 합니다. 결산연월을 다시 선택해주세요.")
    # 모든 필수 입력값이 유효한지 확인
    elif contract_rate > 0 and amount_usd > 0 and end_spot_rate > 0:
        # 현재 선택된 결산월의 예상 환율을 가져옴
        settlement_rate_key = f"{settlement_year}-{settlement_month}"
        settlement_forward_rate_for_calc = st.session_state.hypothetical_rates.get(settlement_rate_key, 0)

        if settlement_forward_rate_for_calc <= 0:
            st.warning("선택된 결산연월에 대한 예상 통화선도환율을 0보다 크게 입력해주세요.")
        else:
            # 손익 계산 로직 (평가손익과 거래손익 모두 계산)
            if transaction_type == "선매도":
                valuation_profit_loss = (contract_rate - settlement_forward_rate_for_calc) * amount_usd
                expiry_profit_loss = (contract_rate - end_spot_rate) * amount_usd
                valuation_rate_diff_text = f"{contract_rate:,.2f} - {settlement_forward_rate_for_calc:,.2f}"
                expiry_rate_diff_text = f"{contract_rate:,.2f} - {end_spot_rate:,.2f}"
            else: # 선매수
                valuation_profit_loss = (settlement_forward_rate_for_calc - contract_rate) * amount_usd
                expiry_profit_loss = (end_spot_rate - contract_rate) * amount_usd
                valuation_rate_diff_text = f"{settlement_forward_rate_for_calc:,.2f} - {contract_rate:,.2f}"
                expiry_rate_diff_text = f"{end_spot_rate:,.2f} - {contract_rate:,.2f}"

            # --- 수정된 기능: 결산시점 평가손익은 항상 표시 ---
            st.header("결산시점 파생상품 평가손익 분석 결과")
            st.write("선택된 결산일에 예상 환율을 기준으로 계산한 평가손익입니다.")

            col_valuation_result, col_valuation_diff = st.columns(2)
            with col_valuation_result:
                if valuation_profit_loss >= 0:
                    st.metric(label="파생상품 평가손익 (원)", value=f"{valuation_profit_loss:,.0f}원", delta="이익")
                else:
                    st.metric(label="파생상품 평가손익 (원)", value=f"{valuation_profit_loss:,.0f}원", delta="손실", delta_color="inverse")
            with col_valuation_diff:
                st.metric(label="환율 차이 (원)", value=f"{settlement_forward_rate_for_calc - contract_rate:,.2f}")

            st.markdown(f"**총 파생상품 평가손익:** ${amount_usd:,.0f} * ({valuation_rate_diff_text}) = {valuation_profit_loss:,.0f}원")

            # --- 수정된 기능: 결산일이 만기일과 동일한 달이면 거래손익도 같이 표시 ---
            if settlement_year == end_date.year and settlement_month == end_date.month:
                st.markdown("---")
                st.header("계약만료시점 파생상품 거래손익 분석 결과")
                st.write("만기 시점의 현물환율을 기준으로 계산한 실제 손익입니다.")

                col_expiry_result, col_expiry_diff = st.columns(2)
                with col_expiry_result:
                    if expiry_profit_loss >= 0:
                        st.metric(label="파생상품 거래손익 (원)", value=f"{expiry_profit_loss:,.0f}원", delta="이익")
                    else:
                        st.metric(label="파생상품 거래손익 (원)", value=f"{expiry_profit_loss:,.0f}원", delta="손실", delta_color="inverse")
                with col_expiry_diff:
                    st.metric(label="환율 차이 (원)", value=f"{end_spot_rate - contract_rate:,.2f}")

                st.markdown(f"**총 파생상품 거래손익:** ${amount_usd:,.0f} * ({expiry_rate_diff_text}) = {expiry_profit_loss:,.0f}원")

            # --- 수정된 기능: 결산 가능 연월을 X축으로 하는 손익 시나리오 그래프
            st.markdown("---")
            st.subheader("📊 기간별 예상 총 손익 시나리오")
            
            # 시나리오 분석을 위한 데이터프레임 생성
            scenario_data = []
            current_year_chart = start_date.year
            current_month_chart = start_date.month

            while date(current_year_chart, current_month_chart, 1) <= end_of_contract_month.replace(day=1):
                month_key_chart = f"{current_year_chart}-{current_month_chart}"
                hypothetical_forward_rate = st.session_state.hypothetical_rates.get(month_key_chart, 0)
                
                if transaction_type == "선매도":
                    hypothetical_pl = (contract_rate - hypothetical_forward_rate) * amount_usd
                else: # 선매수
                    hypothetical_pl = (hypothetical_forward_rate - contract_rate) * amount_usd
                
                # 차트 순서 정렬을 위해 YYYY-MM 형식의 날짜 문자열을 사용
                scenario_data.append({"결산연월": f"{current_year_chart}-{current_month_chart:02d}", "총 손익 (원)": hypothetical_pl})

                current_month_chart += 1
                if current_month_chart > 12:
                    current_month_chart = 1
                    current_year_chart += 1
            
            df_scenario = pd.DataFrame(scenario_data)

            # 그래프 표시
            st.write("각 월에 입력된 예상 통화선도환율을 기준으로 계산된 손익 시나리오입니다.")
            st.line_chart(df_scenario, x="결산연월", y="총 손익 (원)")

    else:
        st.warning("모든 필수 입력값(거래금액, 계약환율, 만기 시점 현물환율)을 모두 0보다 크게 입력해주세요.")
