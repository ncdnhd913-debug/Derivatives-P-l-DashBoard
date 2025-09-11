import streamlit as st
from datetime import date, timedelta
import calendar
import pandas as pd
import altair as alt
import math

# Full page configuration
st.set_page_config(
    page_title="파생상품 손익효과 분석",
    layout="wide"
)

# Initialize session state for hypothetical rates
if 'hypothetical_rates' not in st.session_state:
    st.session_state.hypothetical_rates = {}

# Function to accurately calculate the contract period in months/years
def add_months_to_date(d, months):
    """
    Adds months to a given date and returns an accurate date.
    Example: Adding 1 month to January 31st results in February 28th or 29th (leap year).
    """
    year = d.year + (d.month + months - 1) // 12
    month = (d.month + months - 1) % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)

# Sidebar configuration
st.sidebar.header("파생상품 계약 정보")

# 0. Forward exchange transaction type selection menu
transaction_type = st.sidebar.selectbox(
    label="선도환거래종류",
    options=["선매도", "선매수"],
    help="거래 종류에 따라 손익 계산 방식이 달라집니다."
)

# 1. Transaction amount ($) input field (initial value set to 0.0 for meaningful analysis)
amount_usd = st.sidebar.number_input(
    label="거래금액($)",
    min_value=0.0,
    format="%.2f",
    value=0.0,
    help="거래에 사용된 금액을 달러($) 단위로 입력하세요."
)

# 5. Contract rate (two decimal places) input field (initial value set to 0.0 for meaningful analysis)
contract_rate = st.sidebar.number_input(
    label="계약환율",
    min_value=0.0,
    format="%.2f",
    value=0.0,
    help="계약 시점의 통화선도환율을 입력하세요."
)

# 2. Tenor selection menu
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
    index=2, # Default: 2 months
    help="계약 기간(기일물)을 선택하세요."
)
tenor_days = tenor_options[selected_tenor]

# 3. Contract date and rate input fields
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
        value=0.0,
        help="계약 시작일의 현물환율을 입력하세요."
    )

col_end_date, col_end_rate = st.sidebar.columns(2)
# Calculate contract maturity date based on tenor
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
        value=0.0,
        help="계약 만료일의 현물환율을 입력하세요."
    )

# 4. Settlement month/year and rate input fields
st.sidebar.subheader("결산일자")

# Function to get the last day of a month
def get_last_day_of_month(year, month):
    return calendar.monthrange(year, month)[1]

# Modify settlement month/year to be selectable only within the contract period
all_settlement_dates = []
current_year = start_date.year
current_month = start_date.month

# Get the last day of the maturity month
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

# --- Change monthly hypothetical forward rate input fields to a Data Editor ---
st.sidebar.markdown(
    "시나리오 분석을 위해 각 월말의 예상 통화선도환율을 입력하세요.",
    help="더블클릭하거나 탭하여 값을 수정할 수 있습니다."
)

current_year_scenario = start_date.year
current_month_scenario = start_date.month

# Create a list of all settlement months (excluding maturity month)
all_settlement_months = []
# Set initial value to 0.0
initial_rate_for_hypo = 0.0

while date(current_year_scenario, current_month_scenario, 1) <= end_of_contract_month.replace(day=1):
    is_expiry_month_scenario = (current_year_scenario == end_date.year and current_month_scenario == end_date.month)
    if not is_expiry_month_scenario:
        month_key = f"{current_year_scenario}-{current_month_scenario}"
        
        if month_key not in st.session_state.hypothetical_rates:
            st.session_state.hypothetical_rates[month_key] = initial_rate_for_hypo
        
        all_settlement_months.append({
            "결산일자": f"{current_year_scenario}년 {current_month_scenario}월말",
            "예상 통화선도환율": st.session_state.hypothetical_rates.get(month_key),
            "month_key": month_key # Key for internal use
        })
    current_month_scenario += 1
    if current_month_scenario > 12:
        current_month_scenario = 1
        current_year_scenario += 1

df_rates = pd.DataFrame(all_settlement_months)

# Use Data Editor for rate input
edited_df = st.sidebar.data_editor(
    df_rates,
    column_config={
        "결산일자": st.column_config.TextColumn(
            "결산일자",
            disabled=True,
        ),
        "예상 통화선도환율": st.column_config.NumberColumn(
            "예상 통화선도환율",
            min_value=0.0,
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
        updated_rate = row['예상 통화선도환율']
        # Set the value to 0.0 if the user deletes it (it becomes None)
        st.session_state.hypothetical_rates[row['month_key']] = updated_rate if updated_rate is not None else 0.0

# Main screen
st.title("📈 파생상품 손익효과 분석 대시보드")
st.write("왼쪽 사이드바에서 계약 정보 및 결산일자를 입력하시면 실시간으로 분석 결과가 표시됩니다.")

# Check for zero/invalid values
zero_value_errors = []
if not amount_usd > 0:
    zero_value_errors.append("거래금액($)")
if not contract_rate > 0:
    zero_value_errors.append("계약환율")
if not start_spot_rate > 0:
    zero_value_errors.append("시작 시점 현물환율")
if not end_spot_rate > 0:
    zero_value_errors.append("만기 시점 현물환율")

if zero_value_errors:
    st.warning(f"다음 항목의 값을 0보다 크게 입력해주세요: {', '.join(zero_value_errors)}")
# Add the new validation logic for contract rate vs. start spot rate
elif contract_rate > start_spot_rate:
    st.error("한미 금리차에 따른 스왑포인트를 음수로 가정하여, 계약환율은 계약 시작시점의 현물환율보다 낮아야합니다.")
else:
    settlement_year = settlement_date_corrected.year
    settlement_month = settlement_date_corrected.month
    
    is_expiry_month = (settlement_year == end_date.year and settlement_month == end_date.month)
    
    # Transaction P&L is always calculated
    if transaction_type == "선매도":
        expiry_profit_loss = (contract_rate - end_spot_rate) * amount_usd
    else: # Buy forward
        expiry_profit_loss = (end_spot_rate - contract_rate) * amount_usd

    # Valuation P&L is calculated only if it's not the maturity month
    if not is_expiry_month:
        settlement_rate_key = f"{settlement_year}-{settlement_month}"
        settlement_forward_rate_for_calc = st.session_state.hypothetical_rates.get(settlement_rate_key, 0)

        if settlement_forward_rate_for_calc <= 0:
            st.warning("선택된 결산일자에 대한 '예상 통화선도환율'을 0보다 크게 입력해주세요.")
        else:
            if transaction_type == "선매도":
                valuation_profit_loss = (contract_rate - settlement_forward_rate_for_calc) * amount_usd
                valuation_rate_diff_text = f"{contract_rate:,.2f} - {settlement_forward_rate_for_calc:,.2f}"
            else: # Buy forward
                valuation_profit_loss = (settlement_forward_rate_for_calc - contract_rate) * amount_usd
                valuation_rate_diff_text = f"{settlement_forward_rate_for_calc:,.2f} - {contract_rate:,.2f}"

            # Display valuation P&L result
            st.header(f"{settlement_month}월 결산시점 파생상품 평가손익 분석 결과")
            st.write("선택된 결산일에 예상 환율을 기준으로 계산한 평가손익입니다.")
            col_valuation_result, col_valuation_diff = st.columns(2)
            with col_valuation_result:
                if valuation_profit_loss >= 0:
                    st.metric(label="파생상품 평가손익 (원)", value=f"{valuation_profit_loss:,.0f}원", delta="이익")
                else:
                    st.metric(label="파생상품 평가손익 (원)", value=f"{valuation_profit_loss:,.0f}원", delta="손실", delta_color="inverse")
            with col_valuation_diff:
                st.metric(label="환율 차이 (원)", value=f"{settlement_forward_rate_for_calc - contract_rate:,.2f}원")
            st.markdown(f"**총 파생상품 평가손익:** ${amount_usd:,.0f} * ({valuation_rate_diff_text}) = {valuation_profit_loss:,.0f}원")
    
    # Display transaction P&L result if it's the maturity month
    else:
        st.header(f"{settlement_month}월 결산시점 파생상품 거래손익 분석결과")
        st.write("만기 시점의 현물환율을 기준으로 계산한 실제 손익입니다.")
        col_expiry_result, col_expiry_diff = st.columns(2)
        if transaction_type == "선매도":
            expiry_rate_diff_text = f"{contract_rate:,.2f} - {end_spot_rate:,.2f}"
        else: # Buy forward
            expiry_rate_diff_text = f"{end_spot_rate:,.2f} - {contract_rate:,.2f}"
        with col_expiry_result:
            if expiry_profit_loss >= 0:
                st.metric(label="파생상품 거래손익 (원)", value=f"{expiry_profit_loss:,.0f}원", delta="이익")
            else:
                st.metric(label="파생상품 거래손익 (원)", value=f"{expiry_profit_loss:,.0f}원", delta="손실", delta_color="inverse")
        with col_expiry_diff:
            st.metric(label="환율 차이 (원)", value=f"{end_spot_rate - contract_rate:,.2f}원")
        st.markdown(f"**총 파생상품 거래손익:** ${amount_usd:,.0f} * ({expiry_rate_diff_text}) = {expiry_profit_loss:,.0f}원")

    # --- Display P&L scenario with a chart
    st.markdown("---")
    st.subheader("📊 파생상품 가입에 따른 기간별 예상 총 손익 시나리오")
    
    # Create DataFrame for scenario analysis
    scenario_data = []
    current_year_chart = start_date.year
    current_month_chart = start_date.month

    while date(current_year_chart, current_month_chart, 1) <= end_of_contract_month.replace(day=1):
        month_key_chart = f"{current_year_chart}-{current_month_chart}"
        is_expiry_month_chart = (current_year_chart == end_date.year and current_month_chart == end_date.month)
        
        total_pl = 0
        
        if is_expiry_month_chart:
            # If it's the maturity month, calculate transaction P&L based on the maturity rate
            total_pl = expiry_profit_loss
        else:
            # If it's not the maturity month, calculate valuation P&L based on the hypothetical forward rate
            hypothetical_forward_rate = st.session_state.hypothetical_rates.get(month_key_chart)
            if hypothetical_forward_rate is None:
                hypothetical_forward_rate = initial_rate_for_hypo
            
            if transaction_type == "선매도":
                total_pl = (contract_rate - hypothetical_forward_rate) * amount_usd
            else: # Buy forward
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
    
    # Create DataFrame
    df_scenario = pd.DataFrame(scenario_data)

    # Generate and display Altair chart
    st.write("각 월에 입력된 예상 통화선도환율을 기준으로 계산된 손익 시나리오입니다.")
    
    # Dynamically set Y-axis domain to ensure bars are always visible
    min_pl = df_scenario['총 손익 (백만원)'].min()
    max_pl = df_scenario['총 손익 (백만원)'].max()
    
    # Set a small buffer for the chart domain
    buffer = 1.2
    # Set a base domain for cases where P&L is 0
    min_domain = -10.0
    max_domain = 10.0

    if not math.isclose(min_pl, 0.0) or not math.isclose(max_pl, 0.0):
        abs_max = max(abs(min_pl), abs(max_pl))
        min_domain = -abs_max * buffer
        max_domain = abs_max * buffer
    
    chart_domain = [min_domain, max_domain]

    # Bar chart (including color condition)
    bar_chart = alt.Chart(df_scenario).mark_bar().encode(
        x=alt.X(
            '결산연월',
            sort=date_options,
            axis=alt.Axis(
                title='결산연월',
                labelAngle=0
            ),
            # Corrected: use paddingInner to control bar width/spacing
            scale=alt.Scale(paddingInner=0.5) 
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
            alt.value('#3498db'), # Blue for profit
            alt.value('#e74c3c') # Red for loss
        ),
        tooltip=[
            alt.Tooltip('결산연월', title='결산연월'),
            alt.Tooltip('총 손익 (백만원)', title='총 손익 (백만원)', format=',.2f'),
            alt.Tooltip('평가손익 (백만원)', title='평가손익 (백만원)', format=',.2f'),
            alt.Tooltip('거래손익 (백만원)', title='거래손익 (백만원)', format=',.2f')
        ]
    )

    # Add a horizontal line at the P&L baseline (0)
    zero_line = alt.Chart(pd.DataFrame({'y': [0]})).mark_rule(
        color='#7f8c8d',
        strokeWidth=2,
        strokeDash=[5, 5]
    ).encode(
        y='y:Q'
    )

    # Combine charts and set properties
    final_chart = (bar_chart + zero_line).properties(
        title='월별 총 손익 시나리오'
    ).interactive()

    st.altair_chart(final_chart, use_container_width=True)
