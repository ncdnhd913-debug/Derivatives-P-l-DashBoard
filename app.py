# --- FIXED: 환율 꺾은선 그래프 (외화평가 환율 인식 & 표시) ---
st.markdown("---")
st.subheader("📈 외화평가 시점별 환율 변동 추이")

# 0) 계약환율(고정선) 베이스 데이터
df_contract_rate_data = pd.DataFrame({
    '회계연월': ordered_month_strings,            # ← 상단에서 만든 "YYYY년 M월" (0패딩 없음)
    '환율': [contract_rate] * len(ordered_month_strings),
    '환율 종류': ['계약환율'] * len(ordered_month_strings)
})

df_rates_for_chart = df_contract_rate_data.copy()

if uploaded_file is None or df_ledger.empty:
    st.info("왼쪽 사이드바에서 계정별원장 파일을 업로드하면 환율 변동 추이를 볼 수 있습니다.")
else:
    # 1) 유효 환율만 사용(>0), 일자 오름차순 정렬 후 '월말 기준' 마지막 환율을 취함
    #    (누적/월계 등 불필요 행은 앞에서 이미 제거됨)
    rates = (
        df_ledger.loc[df_ledger['환율'] > 0, ['회계일', '환율']]
                .sort_values('회계일')
                .groupby(pd.Grouper(key='회계일', freq='M'), as_index=False)
                .last()
    )

    # 2) 라벨을 ordered_month_strings와 완전히 동일하게 생성 (0패딩 없음)  ← FIXED
    rates['회계연월'] = (
        rates['회계일'].dt.year.astype(str) + '년 ' +
        rates['회계일'].dt.month.astype(int).astype(str) + '월'
    )
    rates['환율 종류'] = '외화평가 환율'

    # 3) 계약기간 내 월만 남기고 필요한 컬럼만 유지
    rates = rates[rates['회계연월'].isin(ordered_month_strings)][['회계연월', '환율', '환율 종류']]

    # 4) 계약환율 시리즈와 외화평가 환율 시리즈를 세로 결합(concat)  ← FIXED
    df_rates_for_chart = (
        pd.concat([df_contract_rate_data, rates], ignore_index=True)
          .dropna(subset=['환율'])
    )

    if rates.empty:
        st.warning("업로드된 파일에서 계약기간 내 유효한 '외화평가 환율'을 찾지 못했습니다. 파일의 '환율' 컬럼과 날짜를 확인해 주세요.")

# 5) 축 범위 자동 계산 및 라인 차트 렌더링
if not df_rates_for_chart.empty:
    min_rate = float(df_rates_for_chart['환율'].min())
    max_rate = float(df_rates_for_chart['환율'].max())
    if math.isclose(min_rate, max_rate):
        buffer = max(1.0, min_rate * 0.05)
    else:
        buffer = (max_rate - min_rate) * 0.10
    rate_domain = [min_rate - buffer, max_rate + buffer]

    line_chart = alt.Chart(df_rates_for_chart).mark_line(point=True).encode(
        x=alt.X('회계연월:O', axis=alt.Axis(title='결산 연월', labelAngle=0), sort=ordered_month_strings),
        y=alt.Y('환율:Q', axis=alt.Axis(title='환율', format=',.2f'), scale=alt.Scale(domain=rate_domain)),
        color=alt.Color('환율 종류:N', legend=alt.Legend(title="환율 종류")),
        tooltip=[
            alt.Tooltip('회계연월', title='결산연월'),
            alt.Tooltip('환율 종류', title='환율 종류'),
            alt.Tooltip('환율:Q', title='환율', format=',.2f')
        ]
    ).properties(
        title='계약환율 대비 외화평가 시점별 환율 변동',
        width=chart_width,   # ← 위에서 계산한 가변 폭 사용 (긴 기간 스크롤 대응)
        height=400
    ).interactive()

    st.altair_chart(line_chart)
