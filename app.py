import streamlit as st
from datetime import date, timedelta
import calendar
import pandas as pd
import altair as alt
import math

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

# 1. 거래금액($) 입력 필드 (초기값을 1,000,000로 설정하여 의미 있는 분석값 제공)
amount_usd = st.sidebar.number_input(
    label="거래금액($)",
    min_value=0.0,
    format="%.2f",
    value=1_000_000.0, # 초기값을 1,000,000로 변경하여 그래프에 값이 표시되도록 함
    help="거래에 사용된 금액을 달러($) 단위로 입력하세요."
)

# 5. 계약환율(소수점 두 자리) 입력 필드 (초기값을 1300으로 설정하여 의미 있는 분석값 제공)
contract_rate = st.sidebar.number_input(
    label="계약환율",
    min_value=0.0,
    format="%.2f",
    value=1300.0, # 초기값을 1,300.0으로 변경하여 손익 계산 결과가 0이 되지 않도록 함
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
    # 초기값을 1290.0으로 변경하여 시작부터 손익 차이를 보여줌
    start_spot_rate = st.number_input(
        label="시작 시점 현물환율",
        min_value=0.0,
        format="%.2f",
        value=1290.0,
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
    # 초기값을 1320.0으로 변경하여 손익이 바로 보이도록 함
    end_spot_rate = st.number_input(
        label="만기 시점 현물환율",
        min_value=0.0,
        format="%.2f",
        value=1320.0, 
        help="계약 만료일의 현물환율을 입력하세요."
    )

# 4. 결산연월 및 환율 입력 필드
st.sidebar.subheader("결산일자")

# 선택된 달의 마지막 날을 계산하는 함수
def get_last_day_of_month(year, month):
    return calendar.monthrange(year, month)[1]

# 결산연월을 계약 기간 내에서만 선택 가능하도록 수정
all_settlement_dates = []
current_year = start_date.year
current_month = start_date.month

# 만기월의 마지막 날짜를 구함
end_of_contract_month = date(end_date.year, end_date.month, get_last_day_of_month(end_date.year, end_date.month))

while date(current_year, current_month, 1) <= end_of_contract_month.replace(day=1):
    last_day = get_last_day_of_month(current_year, current_month)
    all_settlement_dates.append(date(current_year, current_month, last_day))
    current_month += 1
    if current_month > 12:
        current_month = 1
        current_year += 1

date_options = [f"{d.year}년 {d.month}월" for d in all_settlement_dates]
date_index = date_options.index(f"{date.today().year}년 {date.today().month}월") if f"{date.today().year}년 {date.today().month}월" in date_options else 0

settlement_date = st.sidebar.selectbox(
    label="결산일자",
    options=date_options,
    index=date_index,
    format_func=lambda d: d.replace("년", "년 ").replace("월", "월")
)
settlement_date_corrected = all_settlement_dates[date_options.index(settlement_date)]

st.sidebar.markdown(f"**최종 결산일:** **`{settlement_date_corrected.isoformat()}`**")

# --- 월말별 예상 통화선도환율 입력란을 Data Editor로 변경 ---
st.sidebar.markdown(
    "시나리오 분석을 위해 각 월말의 예상 통화선도환율을 입력하세요.",
    help="더블클릭하거나 탭하여 값을 수정할 수 있습니다."
)

current_year_scenario = start_date.year
current_month_scenario = start_date.month

# 모든 결산월 리스트 생성 (만기월 제외)
all_settlement_months = []
# 초기값을 계약환율과 다르게 설정하여 평가손익이 바로 보이도록 수정
initial_rate_for_hypo = contract_rate + 20

while date(current_year_scenario, current_month_scenario, 1) <= end_of_contract_month.replace(day=1):
    is_expiry_month_scenario = (current_year_scenario == end_date.year and current_month_scenario == end_date.month)
    if not is_expiry_month_scenario:
        month_key = f"{current_year_scenario}-{current_month_scenario}"
        
        if month_key not in st.session_state.hypothetical_rates:
            st.session_state.hypothetical_rates[month_key] = initial_rate_for_hypo
        
        all_settlement_months.append({
            "결산일자": f"{current_year_scenario}년 {current_month_scenario}월말",
            "예상 통화선도환율": st.session_state.hypothetical_rates.get(month_key),
            "month_key": month_key # 내부 사용을 위한 키
        })
    current_month_scenario += 1
    if current_month_scenario > 12:
        current_month_scenario = 1
        current_year_scenario += 1

df_rates = pd.DataFrame(all_settlement_months)

# Data Editor를 사용하여 환율 입력
edited_df = st.sidebar.data_editor(
    df_rates,
    column_config={
        "결산일자": st.column_config.TextColumn(
            "결산일자",
            disabled=True,
        ),
        "예상 통화선도환율": st.column_config.NumberColumn(
            "예상 통화선도환율",
            min_value=0.01,
            format="%.2f",
            help="이 달의 예상 통화선도환율을 입력하세요."
        ),
        "month_key": None
    },
    hide_index=True,
    num_rows="fixed",
)

if not edited_df.empty:
    for _, row in edited_df.iterrows():
        # 사용자가 값을 비워두면 None이 될 수 있으므로, 기본값을 설정
        updated_rate = row['예상 통화선도환율']
        st.session_state.hypothetical_rates[row['month_key']] = updated_rate if updated_rate is not None else contract_rate + 20


# 메인 화면 구성
st.title("📈 파생상품 손익효과 분석 대시보드")
st.write("왼쪽 사이드바에서 계약 정보 및 결산일자를 입력하시면 실시간으로 분석 결과가 표시됩니다.")

# 모든 필수 입력값이 유효한지 확인
error_messages = []
if not amount_usd > 0:
    error_messages.append("거래금액($)")
if not contract_rate > 0:
    error_messages.append("계약환율")
if not start_spot_rate > 0:
    error_messages.append("시작 시점 현물환율")
if not end_spot_rate > 0:
    error_messages.append("만기 시점 현물환율")

if error_messages:
    # 에러 메시지 표시 후 함수 종료 (아래 코드는 실행되지 않음)
    st.warning(f"다음 항목의 값을 0보다 크게 입력해주세요: {', '.join(error_messages)}")
else:
    settlement_year = settlement_date_corrected.year
    settlement_month = settlement_date_corrected.month
    
    is_expiry_month = (settlement_year == end_date.year and settlement_month == end_date.month)
    
    # 거래손익은 항상 계산
    if transaction_type == "선매도":
        expiry_profit_loss = (contract_rate - end_spot_rate) * amount_usd
    else: # 선매수
        expiry_profit_loss = (end_spot_rate - contract_rate) * amount_usd

    # 평가손익은 만기월이 아닌 경우에만 계산
    if not is_expiry_month:
        settlement_rate_key = f"{settlement_year}-{settlement_month}"
        settlement_forward_rate_for_calc = st.session_state.hypothetical_rates.get(settlement_rate_key, 0)

        if settlement_forward_rate_for_calc <= 0:
            st.warning("선택된 결산일자에 대한 '예상 통화선도환율'을 0보다 크게 입력해주세요.")
        else:
            if transaction_type == "선매도":
                valuation_profit_loss = (contract_rate - settlement_forward_rate_for_calc) * amount_usd
                valuation_rate_diff_text = f"{contract_rate:,.2f} - {settlement_forward_rate_for_calc:,.2f}"
            else: # 선매수
                valuation_profit_loss = (settlement_forward_rate_for_calc - contract_rate) * amount_usd
                valuation_rate_diff_text = f"{settlement_forward_rate_for_calc:,.2f} - {contract_rate:,.2f}"

            # 평가손익 결과 표시
            st.header(f"{settlement_month}월 결산시점 파생상품 평가손익 분석 결과")
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
    
    # 만기월인 경우 거래손익 결과 표시
    else:
        st.header(f"{settlement_month}월 결산시점 파생상품 거래손익 분석결과")
        st.write("만기 시점의 현물환율을 기준으로 계산한 실제 손익입니다.")
        col_expiry_result, col_expiry_diff = st.columns(2)
        if transaction_type == "선매도":
            expiry_rate_diff_text = f"{contract_rate:,.2f} - {end_spot_rate:,.2f}"
        else: # 선매수
            expiry_rate_diff_text = f"{end_spot_rate:,.2f} - {contract_rate:,.2f}"
        with col_expiry_result:
            if expiry_profit_loss >= 0:
                st.metric(label="파생상품 거래손익 (원)", value=f"{expiry_profit_loss:,.0f}원", delta="이익")
            else:
                st.metric(label="파생상품 거래손익 (원)", value=f"{expiry_profit_loss:,.0f}원", delta="손실", delta_color="inverse")
        with col_expiry_diff:
            st.metric(label="환율 차이 (원)", value=f"{end_spot_rate - contract_rate:,.2f}")
        st.markdown(f"**총 파생상품 거래손익:** ${amount_usd:,.0f} * ({expiry_rate_diff_text}) = {expiry_profit_loss:,.0f}원")

    # --- 그래프로 손익 시나리오 표시
    st.markdown("---")
    st.subheader("📊 파생상품 가입에 따른 기간별 예상 총 손익 시나리오")
    
    # 시나리오 분석을 위한 데이터프레임 생성
    scenario_data = []
    current_year_chart = start_date.year
    current_month_chart = start_date.month

    while date(current_year_chart, current_month_chart, 1) <= end_of_contract_month.replace(day=1):
        month_key_chart = f"{current_year_chart}-{current_month_chart}"
        is_expiry_month_chart = (current_year_chart == end_date.year and current_month_chart == end_date.month)
        
        total_pl = 0
        
        if is_expiry_month_chart:
            # 만기월인 경우, 만기 시점 환율에 따른 거래손익 계산
            total_pl = expiry_profit_loss
        else:
            # 만기월이 아닌 경우, 월말 예상 통화선도환율에 따른 평가손익 계산
            # `hypothetical_rates`에 값이 없으면 `initial_rate_for_hypo`를 사용
            hypothetical_forward_rate = st.session_state.hypothetical_rates.get(month_key_chart)
            if hypothetical_forward_rate is None:
                hypothetical_forward_rate = initial_rate_for_hypo
            
            if transaction_type == "선매도":
                total_pl = (contract_rate - hypothetical_forward_rate) * amount_usd
            else: # 선매수
                total_pl = (hypothetical_forward_rate - contract_rate) * amount_usd
            
        scenario_data.append({
            "결산연월": f"{current_year_chart}년 {current_month_chart}월",
            "총 손익 (백만원)": total_pl / 1_000_000,
            "평가손익 (백만원)": (total_pl / 1_000_000) if not is_expiry_month_chart else 0,
            "거래손익 (백만원)": (total_pl / 1_000_000) if is_expiry_month_chart else 0
        })

        current_month_chart += 1
        if current_month_chart > 12:
            current_month_chart = 1
            current_year_chart += 1
    
    # 데이터프레임 생성
    df_scenario = pd.DataFrame(scenario_data)

    # Altair 차트 생성 및 표시
    st.write("각 월에 입력된 예상 통화선도환율을 기준으로 계산된 손익 시나리오입니다.")
    
    # Y축 도메인을 동적으로 설정하여 막대가 항상 보이도록 수정
    min_pl = df_scenario['총 손익 (백만원)'].min()
    max_pl = df_scenario['총 손익 (백만원)'].max()
    # 0을 기준으로 대칭적인 범위를 설정
    abs_max = max(abs(min_pl), abs(max_pl))
    chart_domain = [-abs_max * 1.2, abs_max * 1.2]
    # 손익 값이 0이어서 차트가 보이지 않는 경우를 대비해 최소 범위를 설정
    if math.isclose(min_pl, 0.0) and math.isclose(max_pl, 0.0):
        chart_domain = [-10.0, 10.0]

    # 막대 그래프 (색상 조건 포함)
    bar_chart = alt.Chart(df_scenario).mark_bar(
        size=35,
        cornerRadiusTopLeft=5,
        cornerRadiusTopRight=5
    ).encode(
        x=alt.X(
            '결산연월',
            sort=date_options,
            axis=alt.Axis(
                title='결산연월',
                labelAngle=0
            )
        ),
        y=alt.Y(
            '총 손익 (백만원)',
            axis=alt.Axis(
                title='총 손익 (백만원)',
                format=',.2f'
            ),
            scale=alt.Scale(domain=chart_domain)
        ),
        color=alt.condition(
            alt.datum['총 손익 (백만원)'] >= 0,
            alt.value('#3498db'), # 이익일 경우 파란색
            alt.value('#e74c3c') # 손실일 경우 빨간색
        ),
        tooltip=[
            alt.Tooltip('결산연월', title='결산연월'),
            alt.Tooltip('총 손익 (백만원)', title='총 손익 (백만원)', format=',.2f'),
            alt.Tooltip('평가손익 (백만원)', title='평가손익 (백만원)', format=',.2f'),
            alt.Tooltip('거래손익 (백만원)', title='거래손익 (백만원)', format=',.2f')
        ]
    )

    # 손익 기준선(0)에 수평선 추가
    zero_line = alt.Chart(pd.DataFrame({'y': [0]})).mark_rule(
        color='#7f8c8d',
        strokeWidth=2,
        strokeDash=[5, 5]
    ).encode(
        y='y:Q'
    )

    # 차트를 결합하고 속성 설정
    final_chart = (bar_chart + zero_line).properties(
        title='월별 총 손익 시나리오'
    ).interactive()

    st.altair_chart(final_chart, use_container_width=True)
