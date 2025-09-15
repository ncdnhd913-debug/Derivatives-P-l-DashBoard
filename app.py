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
    
# 계약환율 데이터를 추가하기 위한 데이터프레임 생성
# 모든 계약 기간 월에 대해 계약환율 데이터를 만듭니다.
df_contract_rate_data = pd.DataFrame({
    '회계연월': ordered_month_strings,
    '환율': [contract_rate] * len(ordered_month_strings),
    '환율 종류': ['계약환율'] * len(ordered_month_strings)
})

if uploaded_file is None:
    st.info("왼쪽 사이드바에서 계정별원장 파일을 업로드하면 환율 변동 추이를 볼 수 있습니다.")
    df_rates_for_chart = df_contract_rate_data
else:
    # 외화평가 환율 데이터가 있는지 확인하고 데이터프레임 생성
    if not df_ledger.empty and '환율' in df_ledger.columns and (df_ledger['환율'] > 0).any():
        
        # 새로운 요구사항 반영: '거래환종'이 'USD'인 데이터만 필터링
        df_usd_rates = df_ledger[df_ledger['거래환종'].str.upper() == 'USD'].copy()
        
        # 각 월의 마지막 날짜 데이터가 없더라도, 해당 월의 마지막 기록된 환율을 가져오도록 수정
        df_monthly_rates_from_ledger = df_usd_rates.groupby(df_usd_rates['회계일'].dt.to_period('M'))['환율'].last().reset_index()
        
        # PeriodDtype을 Timestamp로 변환
        df_monthly_rates_from_ledger['회계일'] = df_monthly_rates_from_ledger['회계일'].dt.to_timestamp()
        
        # 계약 기간 내의 월에 해당하는 데이터만 필터링
        df_monthly_rates_from_ledger['회계연월'] = df_monthly_rates_from_ledger['회계일'].dt.strftime('%Y년 %m월')
        df_monthly_rates_from_ledger = df_monthly_rates_from_ledger[df_monthly_rates_from_ledger['회계연월'].isin(ordered_month_strings)].copy()
        
        # '환율 종류' 컬럼 추가
        df_monthly_rates_from_ledger['환율 종류'] = '외화평가 환율'
        
        # --- 수정된 부분: pd.concat을 사용하여 데이터프레임 합치기 ---
        # 두 데이터프레임의 열 순서를 맞춥니다.
        df_monthly_rates_from_ledger = df_monthly_rates_from_ledger[['회계연월', '환율', '환율 종류']]
        
        # '계약환율' 데이터프레임과 '외화평가 환율' 데이터프레임을 아래로 합칩니다.
        df_rates_for_chart = pd.concat([df_contract_rate_data, df_monthly_rates_from_ledger])
        
    else:
        st.info("업로드된 파일에 유효한 '환율' 데이터가 없어 계약환율만 표시됩니다.")
        df_rates_for_chart = df_contract_rate_data

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
