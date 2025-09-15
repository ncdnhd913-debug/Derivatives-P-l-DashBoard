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

# Initialize session state for hypothetical rates and FX rates
if 'hypothetical_rates' not in st.session_state:
    st.session_state.hypothetical_rates = {}
if 'fx_valuation_rates' not in st.session_state:
    st.session_state.fx_valuation_rates = pd.DataFrame()

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
    index=1, # Default: 2 months
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
    start_spot_rate = st.sidebar.number_input(
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
    end_spot_rate = st.sidebar.number_input(
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
        month_key = f"{current_year_scenario}-{current_month_scenario:02d}"
        
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

# --- 외화환산데이터 입력 부분을 사이드바 맨 아래로 이동 ---
st.sidebar.markdown("---")
st.sidebar.subheader("외화환산손익 데이터")
uploaded_file = st.sidebar.file_uploader(
    "계정별원장(.xlsx, .xls) 업로드",
    type=["xlsx", "xls"],
    help="외화환산이익/손실을 포함하는 계정별원장 엑셀 파일을 업로드하세요."
)

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
        # 월별 키를 생성할 때 `f"{...}-{...:02d}"` 형식으로 패딩을 추가하여 항상 두 자릿수로 만듭니다.
        settlement_rate_key = f"{settlement_year}-{settlement_month:02d}"
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

    # --- Process uploaded file for FX P&L and new FX rate chart
    st.markdown("---")
    st.subheader("외화환산손익 데이터 분석")

    monthly_fx_pl = {}
    df_ledger = pd.DataFrame() # Initialize an empty DataFrame
    
    # 생성될 모든 월 문자열의 순서 리스트를 미리 생성 (정확한 차트 정렬을 위함)
    ordered_month_strings = []
    temp_year, temp_month = start_date.year, start_date.month
    while date(temp_year, temp_month, 1) <= end_of_contract_month.replace(day=1):
        ordered_month_strings.append(f"{temp_year}년 {temp_month}월")
        temp_month += 1
        if temp_month > 12:
            temp_month = 1
            temp_year += 1

    if uploaded_file is not None:
        try:
            # Step 1: Find the correct header row
            required_columns_strict = ['회계일', '계정명', '차변', '대변', '환율', '거래환종']
            header_row = None
            
            # Read the file with no header to inspect the data
            df_temp = pd.read_excel(uploaded_file, header=None, nrows=50)
            
            # Find the row that contains all required columns (case-insensitive and with stripping)
            for i in range(len(df_temp)):
                row_values = [str(x).strip() for x in df_temp.iloc[i]]
                found_all = all(col.lower() in [val.lower() for val in row_values] for col in required_columns_strict)
                if found_all:
                    header_row = i
                    break
        
            if header_row is None:
                st.error("업로드한 파일에서 '회계일', '계정명', '차변', '대변', '환율', '거래환종' 열을 찾을 수 없습니다. 열 이름의 철자를 확인하거나, 첫 번째 행이 아닌 경우에도 올바르게 인식되도록 수정했습니다.")
                st.stop()
        
            # Step 2: Read the full file using the identified header row
            df_ledger = pd.read_excel(uploaded_file, header=header_row)
            df_ledger.columns = [col.strip() for col in df_ledger.columns]

            # Re-map columns to the expected names
            df_ledger.rename(columns={
                '회계일': '회계일',
                '계정명': '계정명',
                '차변': '차변',
                '대변': '대변',
                '환율': '환율',
                '거래환종': '거래환종'
            }, inplace=True)

            # Convert columns to numeric, coercing errors to NaN
            df_ledger['차변'] = pd.to_numeric(df_ledger['차변'], errors='coerce').fillna(0)
            df_ledger['대변'] = pd.to_numeric(df_ledger['대변'], errors='coerce').fillna(0)
            df_ledger['환율'] = pd.to_numeric(df_ledger['환율'], errors='coerce').fillna(0)
            
            # Convert '회계일' to datetime
            df_ledger['회계일'] = pd.to_datetime(df_ledger['회계일'])
            
            # NEW: Filter out rows that contain "월계" or "누계" in the '계정명' column
            df_ledger = df_ledger[~df_ledger['계정명'].str.contains('월계|누계', case=False, na=False)]
            
            # Calculate FX P&L by checking if the account name CONTAINS the keywords
            df_ledger['fx_pl'] = 0
            df_ledger.loc[df_ledger['계정명'].str.contains('외화환산이익', case=False, na=False), 'fx_pl'] = df_ledger['대변']
            df_ledger.loc[df_ledger['계정명'].str.contains('외화환산손실', case=False, na=False), 'fx_pl'] = -df_ledger['차변']
            
            df_ledger['month_key'] = df_ledger['회계일'].dt.strftime('%Y-%m')
            monthly_fx_pl = df_ledger.groupby('month_key')['fx_pl'].sum().to_dict()
            
            # Display FX P&L metric here
            if f"{settlement_year}-{settlement_month:02d}" in monthly_fx_pl:
                selected_month_fx_pl = monthly_fx_pl[f"{settlement_year}-{settlement_month:02d}"]
                if selected_month_fx_pl >= 0:
                    st.metric(label="외화환산손익 (원)", value=f"{selected_month_fx_pl:,.0f}원", delta="이익")
                else:
                    st.metric(label="외화환산손익 (원)", value=f"{selected_month_fx_pl:,.0f}원", delta="손실", delta_color="inverse")
            else:
                st.info("선택된 결산일에 해당하는 외화환산손익 데이터가 업로드된 파일에 없습니다.")

    except Exception as e:
        st.error(f"파일을 처리하는 중 오류가 발생했습니다. 파일 형식이 올바른지 확인해주세요. 오류 메시지: {e}")
        st.stop()
else:
    st.info("왼쪽 사이드바에서 계정별원장 파일을 업로드해 주세요.")
    
# --- Display P&L scenario with a chart
st.markdown("---")
st.subheader("📊 파생상품 및 외화평가 기간별 총 손익 시나리오")
    
# Create DataFrame for scenario analysis
scenario_data = []
current_year_chart = start_date.year
current_month_chart = start_date.month
    
while date(current_year_chart, current_month_chart, 1) <= end_of_contract_month.replace(day=1):
    month_key_chart = f"{current_year_chart}-{current_month_chart:02d}"
        
    # Calculate Derivative P&L
    is_expiry_month_chart = (current_year_chart == end_date.year and current_month_chart == end_date.month)
    derivative_pl = 0
    if is_expiry_month_chart:
        derivative_pl = expiry_profit_loss
    else:
        # 수정된 부분: 이제 예상 통화선도환율을 Data Editor에서 가져옵니다.
        hypothetical_forward_rate = st.session_state.hypothetical_rates.get(month_key_chart)
        if hypothetical_forward_rate is None:
            hypothetical_forward_rate = initial_rate_for_hypo
        
        if transaction_type == "선매도":
            derivative_pl = (contract_rate - hypothetical_forward_rate) * amount_usd
        else: # Buy forward
            derivative_pl = (hypothetical_forward_rate - contract_rate) * amount_usd
        
    # Get FX P&L from uploaded file data
    fx_pl = monthly_fx_pl.get(f"{current_year_chart}-{current_month_chart:02d}", 0)
    
    scenario_data.append({
        "결산연월": f"{current_year_chart}년 {current_month_chart}월",
        "파생상품 손익 (백만원)": derivative_pl / 1_000_000,
        "외화환산손익 (백만원)": fx_pl / 1_000_000
    })

    current_month_chart += 1
    if current_month_chart > 12:
        current_month_chart = 1
        current_year_chart += 1
    
# Create DataFrame and melt for grouped bar chart
df_scenario = pd.DataFrame(scenario_data)
df_melted = pd.melt(df_scenario, id_vars=['결산연월'], 
                         value_vars=['파생상품 손익 (백만원)', '외화환산손익 (백만원)'],
                         var_name='손익 종류', value_name='손익 (백만원)')

# Generate and display Altair chart
st.write("각 월에 대한 파생상품 손익과 업로드된 파일의 외화환산손익을 비교합니다.")
    
# Dynamically set Y-axis domain to ensure bars are always visible
min_pl = df_melted['손익 (백만원)'].min()
max_pl = df_melted['손익 (백만원)'].max()
    
buffer = 1.2
min_domain = -10.0
max_domain = 10.0

if not math.isclose(min_pl, 0.0) or not math.isclose(max_pl, 0.0):
    abs_max = max(abs(min_pl), abs(max_pl))
    min_domain = -abs_max * buffer
    max_domain = abs_max * buffer
    
chart_domain = [min_domain, max_domain]

# Calculate dynamic chart width for horizontal scrolling if tenor is > 1 year
num_months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month) + 1
chart_width = max(600, num_months * 80) # Use a minimum width, then scale up
    
# --- 그룹 막대 차트로 변경하여 모든 월이 표시되도록 수정
bar_chart = alt.Chart(df_melted).mark_bar(size=20).encode(
    # Y축
    y=alt.Y('손익 (백만원)', axis=alt.Axis(title='손익 (백만원)', format=',.2f'), scale=alt.Scale(domain=chart_domain)),
    # 그룹을 위한 X축: 결산연월 (순서 강제 적용)
    x=alt.X('결산연월:O', axis=alt.Axis(title='결산 연월', labelAngle=0), sort=ordered_month_strings),
    # 그룹 내 막대 위치를 위한 X축 오프셋
    xOffset=alt.XOffset('손익 종류:N'),
    # 색상
    color=alt.Color('손익 종류', legend=alt.Legend(title="손익 종류")),
    # 툴팁
    tooltip=[
        alt.Tooltip('결산연월', title='결산연월'),
        alt.Tooltip('손익 종류', title='손익 종류'),
        alt.Tooltip('손익 (백만원)', title='손익 (백만원)', format=',.2f')
    ]
).properties(
    title='월별 파생상품 및 외화평가 손익 시나리오',
    width=chart_width,
    height=400
).interactive()

st.altair_chart(bar_chart)

# --- NEW: 환율 꺾은선 그래프 추가 (Add FX Rate Line Chart) ---
st.markdown("---")
st.subheader("📈 외화평가 시점별 환율 변동 추이")

# --- 수정된 부분: 외화평가 환율을 직접 입력/수정할 수 있는 Data Editor 추가 ---
st.markdown(
    "아래 표의 **'외화평가 환율'**을 직접 수정하여 원하는 값을 차트에 반영할 수 있습니다.",
    help="업로드된 파일의 월말 환율이 기본값으로 채워집니다. 더블클릭하거나 탭하여 수정하세요."
)

# Initialize a DataFrame for FX valuation rates
df_fx_rates = pd.DataFrame({
    '회계연월': ordered_month_strings,
    '환율': [0.0] * len(ordered_month_strings),
    'month_key': [f"{d.split('년')[0]}-{d.split('년')[1].strip()[:-1].zfill(2)}" for d in ordered_month_strings]
})

# If a file is uploaded, use its rates as the default values
if uploaded_file is not None and not df_ledger.empty:
    df_usd_rates = df_ledger[df_ledger['거래환종'].str.upper() == 'USD'].copy()
    df_monthly_rates_from_ledger = df_usd_rates.groupby(df_usd_rates['회계일'].dt.to_period('M'))['환율'].last().reset_index()
    df_monthly_rates_from_ledger['month_key'] = df_monthly_rates_from_ledger['회계일'].dt.strftime('%Y-%m')

    # Update the main DataFrame with values from the uploaded file
    df_fx_rates = df_fx_rates.set_index('month_key')
    df_fx_rates.update(df_monthly_rates_from_ledger.set_index('month_key'))
    df_fx_rates = df_fx_rates.reset_index()

# Use a data editor to let the user edit the rates
edited_fx_rates = st.data_editor(
    df_fx_rates,
    column_config={
        "회계연월": st.column_config.TextColumn(
            "회계연월",
            disabled=True,
        ),
        "환율": st.column_config.NumberColumn(
            "외화평가 환율",
            min_value=0.0,
            format="%.2f",
            help="이 달의 외화평가 환율을 입력하세요."
        ),
        "month_key": None
    },
    hide_index=True,
    num_rows="fixed",
    key='fx_rates_editor'
)

# Store the edited DataFrame in session state
st.session_state.fx_valuation_rates = edited_fx_rates

# 계약환율 데이터를 추가하기 위한 데이터프레임 생성
df_contract_rate_data = pd.DataFrame({
    '회계연월': ordered_month_strings,
    '환율': [contract_rate] * len(ordered_month_strings),
    '환율 종류': ['계약환율'] * len(ordered_month_strings)
})

# 외화평가 환율 데이터를 그래프용으로 변환
df_monthly_rates_for_chart = edited_fx_rates.rename(columns={'환율': '환율'}).copy()
df_monthly_rates_for_chart['환율 종류'] = '외화평가 환율'
df_monthly_rates_for_chart = df_monthly_rates_for_chart[['회계연월', '환율', '환율 종류']]

# 두 데이터프레임 합치기
df_rates_for_chart = pd.concat([df_contract_rate_data, df_monthly_rates_for_chart])

if not df_rates_for_chart.empty:
    # Calculate a dynamic domain for the line chart's Y-axis to improve visibility
    min_rate = df_rates_for_chart['환율'].min()
    max_rate = df_rates_for_chart['환율'].max()

    if math.isclose(min_rate, max_rate):
        buffer = min_rate * 0.05
    else:
        buffer = (max_rate - min_rate) * 0.1
        
    rate_domain = [min_rate - buffer, max_rate + buffer]

    # Altair 꺾은선 그래프 생성
    line_chart = alt.Chart(df_rates_for_chart).mark_line(point=True).encode(
        x=alt.X('회계연월:O', axis=alt.Axis(title='결산 연월', labelAngle=0), sort=ordered_month_strings),
        y=alt.Y('환율', axis=alt.Axis(title='환율', format=',.2f'), scale=alt.Scale(domain=rate_domain)),
        color=alt.Color('환율 종류', legend=alt.Legend(title="환율 종류")),
        tooltip=[
            alt.Tooltip('회계연월', title='결산연월'),
            alt.Tooltip('환율 종류', title='환율 종류'),
            alt.Tooltip('환율', title='환율', format=',.2f')
        ]
    ).properties(
        title='계약환율 대비 외화평가 시점별 환율 변동',
        width=800, # 차트 폭을 고정값으로 설정
        height=400
    ).interactive()
    st.altair_chart(line_chart)
