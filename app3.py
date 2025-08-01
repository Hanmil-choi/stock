import streamlit as st
import pandas as pd
import os
from glob import glob
import datetime as dt
import traceback

# ==============================
# 유틸: 컬럼 자동 탐지 함수
# ==============================
def find_column(df, target_names):
    for col in df.columns:
        if col.strip().lower() in [name.lower() for name in target_names]:
            return col
    return None

# ==============================
# 종목 코드 → 회사명 매핑
# ==============================
CODE_TO_NAME = {
    "000270": "Kia",
    "000660": "SK Hynix",
    "005380": "Hyundai Motor",
    "005490": "POSCO",
    "005930": "Samsung Electronics",
    "010140": "Korean Air",
    "014620": "Taekyung",
    "028300": "HLB",
    "034020": "Doosan Enerbility",
    "035420": "NAVER",
    "035900": "JYP Entertainment",
    "041510": "SM Entertainment",
    "051910": "LG Chem",
    "068270": "Celltrion",
    "069500": "KODEX 200",
    "079550": "LIG Nex1",
    "086520": "ECOPRO",
    "089030": "Techwing",
    "105560": "KB Financial",
    "112040": "Daewoo Shipbuilding & Marine Engineering (Hanwha Ocean)",
    "196170": "Alteogen",
    "207940": "Samsung Biologics",
    "247540": "EcoProBM",
    "263750": "펄어비스 (Pearl Abyss)",
    "293490": "Kakao Games",
    "329180": "HD Hyundai Construction Equipment",
    "373220": "LG Energy Solution"
}


DATA_FOLDER = os.path.dirname(__file__) 
st.set_page_config(page_title="Stock Screening App", layout="wide")
st.title("Stock Screening App")

base_date = dt.date(2025, 6, 30)
quick_range = st.selectbox("Quick Range Selection", ["Manual", "Past 1 Week", "Past 1 Month", "Past 3 Months", "Year to Date"])

if quick_range == "Manual":
    start_date = st.date_input("Start Date", value=dt.date(2019, 1, 2), min_value=dt.date(2019, 1, 2), max_value=base_date)
    end_date = st.date_input("End Date", value=base_date, min_value=dt.date(2019, 1, 2), max_value=base_date)
else:
    if quick_range == "Past 1 Week":
        start_date = base_date - dt.timedelta(days=7)
    elif quick_range == "Past 1 Month":
        start_date = base_date - dt.timedelta(days=30)
    elif quick_range == "Past 3 Months":
        start_date = base_date - dt.timedelta(days=90)
    elif quick_range == "Year to Date":
        start_date = dt.date(base_date.year, 1, 1)
    end_date = base_date
    st.info(f"Selected period: {start_date} ~ {end_date}")

interval_days_map = {
    "Every 3 Days": 3,
    "Every Week": 7,
    "Every 2 Weeks": 14,
    "Every Month (30d)": 30
}
eval_cycle = st.selectbox("Evaluation Interval", list(interval_days_map.keys()))
eval_days = interval_days_map[eval_cycle]

file_paths = sorted(glob(os.path.join(DATA_FOLDER, "*_features.csv")))
stock_codes = [os.path.basename(p).split("_")[0] for p in file_paths]
stock_names = [f"{CODE_TO_NAME.get(code, code)} ({code})" for code in stock_codes]
selected_stocks = st.multiselect("Select Stocks", options=stock_names)
selected_codes = [name.split("(")[-1][:-1] for name in selected_stocks]

# ==============================
# UI 확장: 시장 보유 조건, 필수조건, 최대 보유 종목 수
# ==============================

st.subheader("Market Holding Condition (KODEX 200 기준)")
market_hold_option = st.selectbox(
    "Market Hold Condition Option",
    ["Manual Input", "KODEX 200 하락장 (close < sma20)", "KODEX 200 급락장 (close < sma5)", "KODEX 200 보합장 (abs(close - sma20) < sma20 * 0.02)"]
)

if market_hold_option == "Manual Input":
    market_hold_condition = st.text_input("Market Hold Condition (ex: kodex_close < kodex_sma20)", value="")
elif market_hold_option == "KODEX 200 하락장 (close < sma20)":
    market_hold_condition = "kodex_close < kodex_sma20"
elif market_hold_option == "KODEX 200 급락장 (close < sma5)":
    market_hold_condition = "kodex_close < kodex_sma5"
elif market_hold_option == "KODEX 200 보합장 (abs(close - sma20) < sma20 * 0.02)":
    market_hold_condition = "abs(kodex_close - kodex_sma20) < kodex_sma20 * 0.02"
else:
    market_hold_condition = ""

# KODEX 200 사용 가능한 변수들 표시
try:
    df_kodex_sample = pd.read_csv(os.path.join(DATA_FOLDER, "069500_features.csv"))
    with st.expander("Available KODEX 200 Features (use with 'kodex_' prefix)"):
        kodex_features = [f"kodex_{col}" for col in df_kodex_sample.columns]
        st.write(", ".join(kodex_features))
        st.info("💡 **Note**: Use 'kodex_' prefix for KODEX 200 variables in Market Hold Condition")
except Exception as e:
    st.warning(f"Error loading KODEX 200 file: {e}")

st.subheader("Strategy Conditions")
conditions = []
required_flags = []
num_conditions = st.number_input("Number of Conditions", min_value=1, max_value=10, value=1, step=1)

for i in range(num_conditions):
    cols = st.columns([3, 1])
    cond = cols[0].text_input(f"Condition {i+1}", key=f"cond_{i}", placeholder="Example: sma20 > sma60")
    required = cols[1].checkbox("Required", key=f"req_{i}")
    if cond.strip():
        conditions.append(cond.strip())
        required_flags.append(required)

max_stock_count = st.number_input("Max Number of Stocks to Hold", min_value=1, max_value=10, value=3, step=1)

# 최소 Satisfied Conditions 설정
optional_conditions_count = sum(1 for req in required_flags if not req)  # 선택 조건 개수 계산
if optional_conditions_count > 0:
    min_satisfied_conditions = st.number_input(
        "Minimum Satisfied Conditions to Hold", 
        min_value=0, 
        max_value=optional_conditions_count, 
        value=min(1, optional_conditions_count), 
        step=1,
        help=f"최소 몇 개의 선택 조건을 만족해야 보유할지 설정 (현재 선택 조건 개수: {optional_conditions_count})"
    )
else:
    min_satisfied_conditions = 0
    st.info("💡 **Note**: 선택 조건이 없으므로 모든 종목이 보유 대상입니다.")

if selected_codes:
    try:
        df_sample = pd.read_csv(os.path.join(DATA_FOLDER, f"{selected_codes[0]}_features.csv"))
        with st.expander("Available Features"):
            st.write(", ".join(df_sample.columns))
    except Exception as e:
        st.warning(f"Error loading file: {e}")

if st.button("Run Analysis"):
    if not selected_codes or not conditions:
        st.warning("Please select stocks and enter at least one condition.")
    else:
        date_ranges = []
        current_start = start_date
        while current_start < end_date:
            current_end = min(current_start + dt.timedelta(days=eval_days - 1), end_date)
            date_ranges.append((current_start, current_end))
            current_start = current_end + dt.timedelta(days=1)

        equity_curve = []
        cycle_returns = []
        portfolio_value = 100000000
        initial_value = portfolio_value

        for i, (d_start, d_end) in enumerate(date_ranges):
            st.markdown(f"### Cycle {i+1}: {d_start} ~ {d_end}")
            results = []
            prices = {}

            # 시장 보유 조건 평가 (KODEX 200 데이터 사용)
            market_hold = False
            if market_hold_condition.strip():
                try:
                    df_kodex = pd.read_csv(os.path.join(DATA_FOLDER, "069500_features.csv"))
                    date_col = find_column(df_kodex, ['date', 'Date', '날짜'])
                    df_kodex[date_col] = pd.to_datetime(df_kodex[date_col])
                    
                    # 이전 사이클의 KODEX 200 데이터 사용
                    if i > 0:  # 첫 번째 사이클이 아닌 경우
                        prev_end = date_ranges[i-1][1]  # 이전 사이클 종료일
                        df_prev_kodex = df_kodex[df_kodex[date_col] == pd.to_datetime(prev_end)].copy()
                        if len(df_prev_kodex) == 0:
                            # 이전 사이클 종료일 데이터가 없으면 이전 사이클 기간의 마지막 데이터 사용
                            prev_start = date_ranges[i-1][0]
                            df_prev_cycle_kodex = df_kodex[(df_kodex[date_col] >= pd.to_datetime(prev_start)) & (df_kodex[date_col] <= pd.to_datetime(prev_end))].copy()
                            if len(df_prev_cycle_kodex) > 0:
                                df_prev_sorted_kodex = df_prev_cycle_kodex.sort_values(by=date_col)
                                df_prev_kodex = df_prev_sorted_kodex.iloc[-1:].copy()
                    else:  # 첫 번째 사이클인 경우
                        # 현재 사이클 시작일 이전의 마지막 데이터 사용
                        df_prev_kodex = df_kodex[df_kodex[date_col] < pd.to_datetime(d_start)].copy()
                        if len(df_prev_kodex) > 0:
                            df_prev_sorted_kodex = df_prev_kodex.sort_values(by=date_col)
                            df_prev_kodex = df_prev_sorted_kodex.iloc[-1:].copy()
                    
                    if len(df_prev_kodex) > 0:
                        # KODEX 200 관련 변수들을 계산하여 추가
                        local_dict = {col: df_prev_kodex.iloc[0][col] for col in df_prev_kodex.columns}
                        
                        # 컬럼명에 kodex_ 접두사 추가
                        kodex_local_dict = {}
                        for key, value in local_dict.items():
                            kodex_local_dict[f'kodex_{key}'] = value
                        
                        # 안전한 eval 실행
                        try:
                            market_hold = eval(market_hold_condition, {}, kodex_local_dict)
                        except NameError as e:
                            st.warning(f"Variable not found in KODEX 200 data: {e}")
                            st.warning(f"Available variables: {list(kodex_local_dict.keys())}")
                            market_hold = False
                        except Exception as e:
                            st.warning(f"Error evaluating market hold condition: {e}")
                            market_hold = False
                except Exception as e:
                    st.warning(f"Market hold condition error: {e}")
                    market_hold = False

            if market_hold:
                st.info("[Market Hold] No stocks are bought in this cycle.")
                equity_curve.append({"Cycle": f"Cycle {i+1}", "Value": portfolio_value})
                cycle_returns.append(0.0)
                continue

            for code in selected_codes:
                try:
                    df = pd.read_csv(os.path.join(DATA_FOLDER, f"{code}_features.csv"))
                    date_col = find_column(df, ['date', 'Date', '날짜'])
                    df[date_col] = pd.to_datetime(df[date_col])
                    
                    # 이전 사이클의 데이터로 조건 평가
                    if i > 0:  # 첫 번째 사이클이 아닌 경우
                        prev_end = date_ranges[i-1][1]  # 이전 사이클 종료일
                        df_prev = df[df[date_col] == pd.to_datetime(prev_end)].copy()
                        if len(df_prev) == 0:
                            # 이전 사이클 종료일 데이터가 없으면 이전 사이클 기간의 마지막 데이터 사용
                            prev_start = date_ranges[i-1][0]
                            df_prev_cycle = df[(df[date_col] >= pd.to_datetime(prev_start)) & (df[date_col] <= pd.to_datetime(prev_end))].copy()
                            if len(df_prev_cycle) > 0:
                                df_prev_sorted = df_prev_cycle.sort_values(by=date_col)
                                df_prev = df_prev_sorted.iloc[-1:].copy()
                    else:  # 첫 번째 사이클인 경우
                        # 현재 사이클 시작일 이전의 마지막 데이터 사용
                        df_prev = df[df[date_col] < pd.to_datetime(d_start)].copy()
                        if len(df_prev) > 0:
                            df_prev_sorted = df_prev.sort_values(by=date_col)
                            df_prev = df_prev_sorted.iloc[-1:].copy()
                    
                    if len(df_prev) == 0:
                        continue  # 데이터가 없으면 스킵

                    required_satisfied = True
                    for cond, req in zip(conditions, required_flags):
                        if req:
                            try:
                                if len(df_prev.query(cond)) == 0:
                                    required_satisfied = False
                                    break
                            except Exception:
                                required_satisfied = False
                                break
                    if not required_satisfied:
                        continue

                    satisfied_count = 0
                    # 선택 조건만 카운트 (필수 조건은 이미 확인됨)
                    for cond, req in zip(conditions, required_flags):
                        if not req:  # 선택 조건만
                            try:
                                if len(df_prev.query(cond)) > 0:
                                    satisfied_count += 1
                            except Exception:
                                # 조건 평가 중 오류가 발생하면 해당 조건은 만족하지 않은 것으로 처리
                                pass

                    # 가격 계산: 현재 사이클 시작 시점의 가격 사용 (매수 가격)
                    df_current_start = df[df[date_col] == pd.to_datetime(d_start)].copy()
                    if len(df_current_start) == 0:
                        df_before_cycle = df[df[date_col] < pd.to_datetime(d_start)].copy()
                        if len(df_before_cycle) > 0:
                            df_before_sorted = df_before_cycle.sort_values(by=date_col)
                            df_current_start = df_before_sorted.iloc[-1:].copy()
                        else:
                            continue
                    
                    start_price = df_current_start.iloc[0]["close"]
                    
                    # 사이클 종료 시점의 가격은 다음 사이클에서 계산
                    # 여기서는 시작 가격만 저장
                    prices[code] = {
                        "start": start_price,
                        "end": None  # 나중에 설정
                    }

                    results.append({
                        "Code": code,
                        "Name": CODE_TO_NAME.get(code, code),
                        "Satisfied Conditions": satisfied_count,
                        "Cycle": f"Cycle {i+1}",
                        "From": d_start,
                        "To": d_end
                    })

                except Exception as e:
                    st.error(f"Error processing {code}: {type(e).__name__} - {e}")
                    st.exception(e)

            # 현재 사이클의 종료 가격 설정
            for code in selected_codes:
                try:
                    df = pd.read_csv(os.path.join(DATA_FOLDER, f"{code}_features.csv"))
                    date_col = find_column(df, ['date', 'Date', '날짜'])
                    df[date_col] = pd.to_datetime(df[date_col])
                    
                    if i < len(date_ranges) - 1:  # 마지막 사이클이 아닌 경우
                        # 다음 사이클 시작 시점의 가격을 현재 사이클의 종료 가격으로 설정
                        next_start = date_ranges[i + 1][0]
                        df_next_start = df[df[date_col] == pd.to_datetime(next_start)].copy()
                        if len(df_next_start) == 0:
                            # 다음 사이클 시작일 데이터가 없으면 현재 사이클 종료일 데이터 사용
                            df_cycle_end = df[df[date_col] == pd.to_datetime(d_end)].copy()
                            if len(df_cycle_end) == 0:
                                # 종료일 데이터가 없으면 마지막 사용 가능한 데이터 사용
                                df_before_end = df[df[date_col] <= pd.to_datetime(d_end)].copy()
                                if len(df_before_end) > 0:
                                    df_before_end_sorted = df_before_end.sort_values(by=date_col)
                                    df_cycle_end = df_before_end_sorted.iloc[-1:].copy()
                            if len(df_cycle_end) > 0 and code in prices:
                                prices[code]["end"] = df_cycle_end.iloc[0]["close"]
                        elif len(df_next_start) > 0 and code in prices:
                            prices[code]["end"] = df_next_start.iloc[0]["close"]
                    else:  # 마지막 사이클인 경우
                        # 마지막 사이클 종료 시점의 가격 설정
                        df_cycle_end = df[df[date_col] == pd.to_datetime(d_end)].copy()
                        if len(df_cycle_end) == 0:
                            # 종료일 데이터가 없으면 마지막 사용 가능한 데이터 사용
                            df_before_end = df[df[date_col] <= pd.to_datetime(d_end)].copy()
                            if len(df_before_end) > 0:
                                df_before_end_sorted = df_before_end.sort_values(by=date_col)
                                df_cycle_end = df_before_end_sorted.iloc[-1:].copy()
                        
                        if len(df_cycle_end) > 0 and code in prices:
                            prices[code]["end"] = df_cycle_end.iloc[0]["close"]
                except Exception as e:
                    st.warning(f"Error setting end price for {code}: {e}")

            if results:
                df_result = pd.DataFrame(results)
                # Satisfied Conditions 수에 따라 내림차순 정렬 (확실하게)
                df_result = df_result.sort_values(by=["Satisfied Conditions"], ascending=[False])
                
                # 최소 Satisfied Conditions를 만족하는 종목들 선택
                qualified_stocks = df_result[df_result["Satisfied Conditions"] >= min_satisfied_conditions]
                
                # 보유할 종목 결정
                if len(qualified_stocks) > 0:
                    # 최소 조건을 만족하는 종목이 max_stock_count보다 많으면 상위 max_stock_count개만 보유
                    if len(qualified_stocks) <= max_stock_count:
                        top_codes = qualified_stocks["Code"].tolist()
                    else:
                        # max_stock_count보다 많으면 상위 max_stock_count개만 보유
                        top_codes = qualified_stocks.head(max_stock_count)["Code"].tolist()
                else:
                    top_codes = []
                
                # 보유 종목 수익률 계산 및 표시
                if top_codes:
                    invested_each = portfolio_value / len(top_codes)
                    total_value = 0
                    summary = []
                    for code in top_codes:
                        p = prices.get(code)
                        if p and p["start"] > 0 and p["end"] is not None:
                            # 거래세 0.35%만 적용 (매도 시점)
                            ret = (p["end"] - p["start"]) / p["start"]
                            sell_amount = invested_each * (1 + ret)
                            sell_tax = sell_amount * 0.0035  # 거래세 (0.35%)
                            value = sell_amount - sell_tax
                            total_value += value
                            summary.append({"Code": code, "Name": CODE_TO_NAME.get(code, code), "Return %": round(ret * 100, 2), "Net Return %": round((value - invested_each) / invested_each * 100, 2)})

                    portfolio_value = total_value
                    st.write("Held Stocks")
                    st.dataframe(pd.DataFrame(summary))
                    cycle_ret = round((portfolio_value - equity_curve[-1]["Value"])/equity_curve[-1]["Value"]*100 if equity_curve else (portfolio_value - initial_value)/initial_value*100, 2)
                    cycle_returns.append(cycle_ret)
                else:
                    # 보유할 종목이 없어도 포트폴리오 가치는 유지
                    cycle_returns.append(0.0)
                    st.info("💡 **No stocks meet the minimum conditions for this cycle**")
                
                equity_curve.append({"Cycle": f"Cycle {i+1}", "Value": portfolio_value})
                
                # 각 사이클에서 전체 종목 수익률 비교 (보유할 종목이 없어도 계산)
                st.write("### 📊 All Stocks Performance in This Cycle")
                st.info("💡 **Held stocks are highlighted in blue**")
                
                cycle_all_stocks_performance = []
                
                # 모든 후보 종목의 이번 사이클 수익률 계산 (보유 여부와 관계없이)
                for code in selected_codes:
                    try:
                        df = pd.read_csv(os.path.join(DATA_FOLDER, f"{code}_features.csv"))
                        date_col = find_column(df, ['date', 'Date', '날짜'])
                        df[date_col] = pd.to_datetime(df[date_col])
                        
                        # 사이클 시작 가격
                        df_cycle_start = df[df[date_col] == pd.to_datetime(d_start)].copy()
                        if len(df_cycle_start) == 0:
                            df_before_cycle = df[df[date_col] < pd.to_datetime(d_start)].copy()
                            if len(df_before_cycle) > 0:
                                df_before_sorted = df_before_cycle.sort_values(by=date_col)
                                df_cycle_start = df_before_sorted.iloc[-1:].copy()
                        
                        # 사이클 종료 가격
                        if i < len(date_ranges) - 1:  # 마지막 사이클이 아닌 경우
                            next_start = date_ranges[i + 1][0]
                            df_cycle_end = df[df[date_col] == pd.to_datetime(next_start)].copy()
                            if len(df_cycle_end) == 0:
                                df_cycle_end_alt = df[df[date_col] == pd.to_datetime(d_end)].copy()
                                if len(df_cycle_end_alt) == 0:
                                    df_before_end = df[df[date_col] <= pd.to_datetime(d_end)].copy()
                                    if len(df_before_end) > 0:
                                        df_before_end_sorted = df_before_end.sort_values(by=date_col)
                                        df_cycle_end = df_before_end_sorted.iloc[-1:].copy()
                                else:
                                    df_cycle_end = df_cycle_end_alt
                        else:  # 마지막 사이클인 경우
                            df_cycle_end = df[df[date_col] == pd.to_datetime(d_end)].copy()
                            if len(df_cycle_end) == 0:
                                df_before_end = df[df[date_col] <= pd.to_datetime(d_end)].copy()
                                if len(df_before_end) > 0:
                                    df_before_end_sorted = df_before_end.sort_values(by=date_col)
                                    df_cycle_end = df_before_end_sorted.iloc[-1:].copy()
                        
                        if len(df_cycle_start) > 0 and len(df_cycle_end) > 0:
                            start_price = df_cycle_start.iloc[0]["close"]
                            end_price = df_cycle_end.iloc[0]["close"]
                            cycle_return = (end_price - start_price) / start_price
                            
                            # 거래세 0.35% 적용
                            sell_amount = 100000000 * (1 + cycle_return)
                            sell_tax = sell_amount * 0.0035
                            net_return = cycle_return - sell_tax / 100000000
                            
                            # 해당 사이클에서 실제로 보유한 종목인지 확인
                            is_held = code in top_codes if 'top_codes' in locals() else False
                            
                            # 해당 종목의 Satisfied Conditions 수 계산 (실제 투자 결정과 동일한 방식)
                            satisfied_conditions = 0
                            try:
                                # 실제 투자 결정과 동일한 방식으로 조건 평가
                                if i > 0:  # 첫 번째 사이클이 아닌 경우
                                    prev_end = date_ranges[i-1][1]  # 이전 사이클 종료일
                                    df_prev = df[df[date_col] == pd.to_datetime(prev_end)].copy()
                                    if len(df_prev) == 0:
                                        # 이전 사이클 종료일 데이터가 없으면 이전 사이클 기간의 마지막 데이터 사용
                                        prev_start = date_ranges[i-1][0]
                                        df_prev_cycle = df[(df[date_col] >= pd.to_datetime(prev_start)) & (df[date_col] <= pd.to_datetime(prev_end))].copy()
                                        if len(df_prev_cycle) > 0:
                                            df_prev_sorted = df_prev_cycle.sort_values(by=date_col)
                                            df_prev = df_prev_sorted.iloc[-1:].copy()
                                else:  # 첫 번째 사이클인 경우
                                    # 현재 사이클 시작일 이전의 마지막 데이터 사용
                                    df_prev = df[df[date_col] < pd.to_datetime(d_start)].copy()
                                    if len(df_prev) > 0:
                                        df_prev_sorted = df_prev.sort_values(by=date_col)
                                        df_prev = df_prev_sorted.iloc[-1:].copy()
                                
                                if len(df_prev) > 0:
                                    # 필수 조건 확인
                                    required_satisfied = True
                                    for cond, req in zip(conditions, required_flags):
                                        if req:  # 필수 조건
                                            try:
                                                if len(df_prev.query(cond)) == 0:
                                                    required_satisfied = False
                                                    break
                                            except Exception:
                                                required_satisfied = False
                                                break
                                    
                                    if required_satisfied:
                                        # 선택 조건만 카운트
                                        for cond, req in zip(conditions, required_flags):
                                            if not req:  # 선택 조건만
                                                try:
                                                    if len(df_prev.query(cond)) > 0:
                                                        satisfied_conditions += 1
                                                except Exception:
                                                    pass
                            except Exception as e:
                                satisfied_conditions = 0
                            
                            cycle_all_stocks_performance.append({
                                "Code": code,
                                "Name": CODE_TO_NAME.get(code, code),
                                "Cycle Return %": round(cycle_return * 100, 2),
                                "Net Return %": round(net_return * 100, 2),
                                "Satisfied Conditions": satisfied_conditions,
                                "Held": is_held
                            })
                            
                    except Exception as e:
                        st.warning(f"Error calculating cycle performance for {code}: {e}")
                
                if cycle_all_stocks_performance:
                    # Satisfied Conditions 수에 따라 정렬
                    cycle_all_stocks_df = pd.DataFrame(cycle_all_stocks_performance)
                    cycle_all_stocks_df = cycle_all_stocks_df.sort_values(by="Satisfied Conditions", ascending=False)
                    
                    # 표시용 데이터프레임 생성
                    display_cycle_df = cycle_all_stocks_df.copy()
                    display_cycle_df['Cycle Return %'] = display_cycle_df['Cycle Return %'].apply(lambda x: f"{x:+.2f}%")
                    display_cycle_df['Net Return %'] = display_cycle_df['Net Return %'].apply(lambda x: f"{x:+.2f}%")
                    display_cycle_df['Held'] = display_cycle_df['Held'].apply(lambda x: "✅" if x else "")
                    
                    # 컬럼 순서 변경
                    display_cycle_df = display_cycle_df[['Code', 'Name', 'Satisfied Conditions', 'Cycle Return %', 'Net Return %', 'Held']]
                    
                    # 보유한 종목 강조 표시
                    def highlight_held_cycle(val):
                        if val == "✅":
                            return 'background-color: lightblue'
                        return ''
                    
                    st.dataframe(
                        display_cycle_df.style.map(
                            highlight_held_cycle, 
                            subset=['Held']
                        ),
                        use_container_width=True
                    )
                    

                
                # KODEX 200과의 비교
                try:
                    df_kodex = pd.read_csv(os.path.join(DATA_FOLDER, "069500_features.csv"))
                    date_col = find_column(df_kodex, ['date', 'Date', '날짜'])
                    df_kodex[date_col] = pd.to_datetime(df_kodex[date_col])
                    
                    # KODEX 200 시작 가격
                    df_kodex_start = df_kodex[df_kodex[date_col] == pd.to_datetime(d_start)].copy()
                    if len(df_kodex_start) == 0:
                        df_kodex_before = df_kodex[df_kodex[date_col] < pd.to_datetime(d_start)].copy()
                        if len(df_kodex_before) > 0:
                            df_kodex_before_sorted = df_kodex_before.sort_values(by=date_col)
                            df_kodex_start = df_kodex_before_sorted.iloc[-1:].copy()
                    
                    # KODEX 200 종료 가격
                    if i < len(date_ranges) - 1:  # 마지막 사이클이 아닌 경우
                        next_start = date_ranges[i + 1][0]
                        df_kodex_end = df_kodex[df_kodex[date_col] == pd.to_datetime(next_start)].copy()
                        if len(df_kodex_end) == 0:
                            df_kodex_cycle_end = df_kodex[df_kodex[date_col] == pd.to_datetime(d_end)].copy()
                            if len(df_kodex_cycle_end) == 0:
                                df_kodex_before_end = df_kodex[df_kodex[date_col] <= pd.to_datetime(d_end)].copy()
                                if len(df_kodex_before_end) > 0:
                                    df_kodex_before_end_sorted = df_kodex_before_end.sort_values(by=date_col)
                                    df_kodex_cycle_end = df_kodex_before_end_sorted.iloc[-1:].copy()
                            if len(df_kodex_cycle_end) > 0:
                                kodex_end_price = df_kodex_cycle_end.iloc[0]["close"]
                            else:
                                kodex_end_price = df_kodex_start.iloc[0]["close"]
                        else:
                            kodex_end_price = df_kodex_end.iloc[0]["close"]
                    else:  # 마지막 사이클인 경우
                        df_kodex_cycle_end = df_kodex[df_kodex[date_col] == pd.to_datetime(d_end)].copy()
                        if len(df_kodex_cycle_end) == 0:
                            df_kodex_before_end = df_kodex[df_kodex[date_col] <= pd.to_datetime(d_end)].copy()
                            if len(df_kodex_before_end) > 0:
                                df_kodex_before_end_sorted = df_kodex_before_end.sort_values(by=date_col)
                                df_kodex_cycle_end = df_kodex_before_end_sorted.iloc[-1:].copy()
                        if len(df_kodex_cycle_end) > 0:
                            kodex_end_price = df_kodex_cycle_end.iloc[0]["close"]
                        else:
                            kodex_end_price = df_kodex_start.iloc[0]["close"]
                    
                    if len(df_kodex_start) > 0:
                        kodex_start_price = df_kodex_start.iloc[0]["close"]
                        kodex_return = (kodex_end_price - kodex_start_price) / kodex_start_price
                        kodex_cycle_return = round(kodex_return * 100, 2)
                        
                        # KODEX 200 거래세 적용 (거래세 0.35%만 적용)
                        kodex_sell_amount = 100000000 * (1 + kodex_return)
                        kodex_sell_tax = kodex_sell_amount * 0.0035  # 거래세 (0.35%)
                        kodex_net_return = kodex_return - kodex_sell_tax / 100000000
                        kodex_net_cycle_return = round(kodex_net_return * 100, 2)
                        
                        st.write(f"**KODEX 200 Comparison**: {kodex_cycle_return:+.2f}% (Net: {kodex_net_cycle_return:+.2f}%)")
                        
                        # 전략 vs KODEX 200 비교
                        if cycle_returns[-1] > kodex_net_cycle_return:
                            st.success(f"✅ **Strategy outperformed KODEX 200 by {cycle_returns[-1] - kodex_net_cycle_return:+.2f}%**")
                        elif cycle_returns[-1] < kodex_net_cycle_return:
                            st.error(f"❌ **Strategy underperformed KODEX 200 by {kodex_net_cycle_return - cycle_returns[-1]:+.2f}%**")
                        else:
                            st.info("➖ **Strategy matched KODEX 200 performance**")
                except Exception as e:
                    st.warning(f"Error calculating KODEX 200 comparison: {e}")
            else:
                st.warning("No matching results found for this interval.")
                equity_curve.append({"Cycle": f"Cycle {i+1}", "Value": portfolio_value})
                cycle_returns.append(0.0)



        if equity_curve:
            st.subheader("📊 Portfolio Performance Analysis")
            
            # 포트폴리오 성과 데이터프레임 생성
            equity_df = pd.DataFrame(equity_curve)
            equity_df['Initial_Value'] = initial_value
            equity_df['Absolute_Return'] = equity_df['Value'] - initial_value
            equity_df['Return_Rate_%'] = round((equity_df['Value'] - initial_value) / initial_value * 100, 2)
            equity_df['Cycle_Return_%'] = cycle_returns
            
            # 표시용 데이터프레임 생성
            display_df = equity_df.copy()
            display_df['Value'] = display_df['Value'].apply(lambda x: f"{x:,.0f}")
            display_df['Initial_Value'] = display_df['Initial_Value'].apply(lambda x: f"{x:,.0f}")
            display_df['Absolute_Return'] = display_df['Absolute_Return'].apply(lambda x: f"{x:+,.0f}")
            display_df['Return_Rate_%'] = display_df['Return_Rate_%'].apply(lambda x: f"{x:+.2f}%")
            display_df['Cycle_Return_%'] = display_df['Cycle_Return_%'].apply(lambda x: f"{x:+.2f}%")
            
            # 사이클별 성과 표
            st.write("### 📈 Cycle Performance Summary")
            st.dataframe(display_df, use_container_width=True)
            

            
            # 성과 지표
            st.write("### 🎯 Performance Summary")
            st.info("💰 **Transaction Tax**: 0.35% tax applied on sell transactions")
            
            col1, col2, col3, col4 = st.columns(4)
            
            total_return = round((portfolio_value - initial_value) / initial_value * 100, 2)
            mdd = round(max([(equity_df["Value"].iloc[i] - min(equity_df["Value"].iloc[i:])) / equity_df["Value"].iloc[i] for i in range(len(equity_df))]) * 100, 2)
            avg_cycle_return = round(sum(cycle_returns)/len(cycle_returns), 2)
            final_value = equity_df['Value'].iloc[-1]
            
            with col1:
                st.metric("Total Return", f"{total_return:+.2f}%", f"{total_return:+.2f}%")
            with col2:
                st.metric("Max Drawdown (MDD)", f"{mdd:.2f}%")
            with col3:
                st.metric("Avg Cycle Return", f"{avg_cycle_return:+.2f}%")
            with col4:
                st.metric("Final Portfolio Value", f"{final_value:,.0f}")

            # 비교전략: 선택한 종목 모두에 균등투자 (매 사이클 재투자 방식)
            st.write("### 📊 Comparison Strategy: Equal Weight Portfolio")
            st.info("💡 **Comparison Strategy**: Equal weight investment in all selected stocks with 0.35% transaction tax")
            
            equal_weight_value = initial_value
            equal_weight_curve = []
            
            for i, (d_start, d_end) in enumerate(date_ranges):
                cycle_prices = {}
                
                # 각 종목의 가격 정보 수집 (시작 시점만)
                for code in selected_codes:
                    try:
                        df = pd.read_csv(os.path.join(DATA_FOLDER, f"{code}_features.csv"))
                        date_col = find_column(df, ['date', 'Date', '날짜'])
                        df[date_col] = pd.to_datetime(df[date_col])
                        
                        # 사이클 시작 시점의 가격만 사용
                        df_cycle_start = df[df[date_col] == pd.to_datetime(d_start)].copy()
                        if len(df_cycle_start) == 0:
                            df_before_cycle = df[df[date_col] < pd.to_datetime(d_start)].copy()
                            if len(df_before_cycle) > 0:
                                df_before_sorted = df_before_cycle.sort_values(by=date_col)
                                df_cycle_start = df_before_sorted.iloc[-1:].copy()
                            else:
                                continue
                        
                        start_price = df_cycle_start.iloc[0]["close"]
                        cycle_prices[code] = {"start": start_price, "end": None}
                    except Exception as e:
                        st.warning(f"Error processing {code} for comparison: {e}")
                
                # 현재 사이클의 종료 가격 설정
                for code in selected_codes:
                    try:
                        df = pd.read_csv(os.path.join(DATA_FOLDER, f"{code}_features.csv"))
                        date_col = find_column(df, ['date', 'Date', '날짜'])
                        df[date_col] = pd.to_datetime(df[date_col])
                        
                        if i < len(date_ranges) - 1:  # 마지막 사이클이 아닌 경우
                            # 다음 사이클 시작 시점의 가격을 현재 사이클의 종료 가격으로 설정
                            next_start = date_ranges[i + 1][0]
                            df_next_start = df[df[date_col] == pd.to_datetime(next_start)].copy()
                            if len(df_next_start) == 0:
                                # 다음 사이클 시작일 데이터가 없으면 현재 사이클 종료일 데이터 사용
                                df_cycle_end = df[df[date_col] == pd.to_datetime(d_end)].copy()
                                if len(df_cycle_end) == 0:
                                    # 종료일 데이터가 없으면 마지막 사용 가능한 데이터 사용
                                    df_before_end = df[df[date_col] <= pd.to_datetime(d_end)].copy()
                                    if len(df_before_end) > 0:
                                        df_before_end_sorted = df_before_end.sort_values(by=date_col)
                                        df_cycle_end = df_before_end_sorted.iloc[-1:].copy()
                                if len(df_cycle_end) > 0 and code in cycle_prices:
                                    cycle_prices[code]["end"] = df_cycle_end.iloc[0]["close"]
                            elif len(df_next_start) > 0 and code in cycle_prices:
                                cycle_prices[code]["end"] = df_next_start.iloc[0]["close"]
                        else:  # 마지막 사이클인 경우
                            # 마지막 사이클 종료 시점의 가격 설정
                            df_cycle_end = df[df[date_col] == pd.to_datetime(d_end)].copy()
                            if len(df_cycle_end) == 0:
                                # 종료일 데이터가 없으면 마지막 사용 가능한 데이터 사용
                                df_before_end = df[df[date_col] <= pd.to_datetime(d_end)].copy()
                                if len(df_before_end) > 0:
                                    df_before_end_sorted = df_before_end.sort_values(by=date_col)
                                    df_cycle_end = df_before_end_sorted.iloc[-1:].copy()
                            
                            if len(df_cycle_end) > 0 and code in cycle_prices:
                                cycle_prices[code]["end"] = df_cycle_end.iloc[0]["close"]
                    except Exception as e:
                        st.warning(f"Error setting end price for {code} in comparison: {e}")
                
                # 균등투자 계산 (매매 수수료 0.35% 적용)
                if cycle_prices:
                    invested_per_stock = equal_weight_value / len(cycle_prices)
                    total_cycle_value = 0
                    
                    for code, prices in cycle_prices.items():
                        if prices["start"] > 0 and prices["end"] is not None:
                            # 거래세 0.35%만 적용 (매도 시점)
                            ret = (prices["end"] - prices["start"]) / prices["start"]
                            sell_amount = invested_per_stock * (1 + ret)
                            sell_tax = sell_amount * 0.0035  # 거래세 (0.35%)
                            value = sell_amount - sell_tax
                            total_cycle_value += value

                    
                    equal_weight_value = total_cycle_value
                
                equal_weight_curve.append(equal_weight_value)
            
            # 균등투자 전략 성과 계산
            equal_weight_return = round((equal_weight_value - initial_value) / initial_value * 100, 2)
            
            # MDD 계산
            equal_weight_mdd = 0
            for i in range(len(equal_weight_curve)):
                peak = equal_weight_curve[i]
                trough = equal_weight_curve[i:]
                if len(trough) > 0:
                    drawdown = (peak - min(trough)) / peak
                    equal_weight_mdd = max(equal_weight_mdd, drawdown)
            equal_weight_mdd = round(equal_weight_mdd * 100, 2)
            
            st.write("#### 📈 Equal Weight Portfolio Performance")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Equal Weight Portfolio Return", f"{equal_weight_return:+.2f}%", f"{equal_weight_return:+.2f}%")
            with col2:
                st.metric("Equal Weight Portfolio MDD", f"{equal_weight_mdd:.2f}%")
            
            st.write("**Note**: Equal weight strategy applies 0.35% transaction tax")

            # 전체 기간 KODEX 200 비교
            st.write("### 📊 Overall KODEX 200 Comparison")
            st.info("💡 **KODEX 200 Benchmark**: 1억원 투자, 0.35% transaction tax")
            
            try:
                df_kodex_total = pd.read_csv(os.path.join(DATA_FOLDER, "069500_features.csv"))
                date_col = find_column(df_kodex_total, ['date', 'Date', '날짜'])
                df_kodex_total[date_col] = pd.to_datetime(df_kodex_total[date_col])
                
                # 전체 기간 시작 가격
                df_kodex_total_start = df_kodex_total[df_kodex_total[date_col] == pd.to_datetime(start_date)].copy()
                if len(df_kodex_total_start) == 0:
                    df_kodex_total_before = df_kodex_total[df_kodex_total[date_col] < pd.to_datetime(start_date)].copy()
                    if len(df_kodex_total_before) > 0:
                        df_kodex_total_before_sorted = df_kodex_total_before.sort_values(by=date_col)
                        df_kodex_total_start = df_kodex_total_before_sorted.iloc[-1:].copy()
                
                # 전체 기간 종료 가격
                df_kodex_total_end = df_kodex_total[df_kodex_total[date_col] == pd.to_datetime(end_date)].copy()
                if len(df_kodex_total_end) == 0:
                    df_kodex_total_before_end = df_kodex_total[df_kodex_total[date_col] <= pd.to_datetime(end_date)].copy()
                    if len(df_kodex_total_before_end) > 0:
                        df_kodex_total_before_end_sorted = df_kodex_total_before_end.sort_values(by=date_col)
                        df_kodex_total_end = df_kodex_total_before_end_sorted.iloc[-1:].copy()
                
                if len(df_kodex_total_start) > 0 and len(df_kodex_total_end) > 0:
                    kodex_total_start_price = df_kodex_total_start.iloc[0]["close"]
                    kodex_total_end_price = df_kodex_total_end.iloc[0]["close"]
                    kodex_total_return = (kodex_total_end_price - kodex_total_start_price) / kodex_total_start_price
                    kodex_total_return_pct = round(kodex_total_return * 100, 2)
                    
                    # KODEX 200 거래세 적용 (거래세 0.35%만 적용)
                    kodex_total_sell_amount = initial_value * (1 + kodex_total_return)
                    kodex_total_sell_tax = kodex_total_sell_amount * 0.0035  # 거래세 (0.35%)
                    kodex_total_net_return = kodex_total_return - kodex_total_sell_tax / initial_value
                    kodex_total_net_return_pct = round(kodex_total_net_return * 100, 2)
                    
                    kodex_final_value = initial_value * (1 + kodex_total_net_return)
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("KODEX 200 Total Return", f"{kodex_total_return_pct:+.2f}%", f"{kodex_total_return_pct:+.2f}%")
                    with col2:
                        st.metric("KODEX 200 Net Return", f"{kodex_total_net_return_pct:+.2f}%", f"{kodex_total_net_return_pct:+.2f}%")
                    with col3:
                        st.metric("KODEX 200 Final Value", f"{kodex_final_value:,.0f}")
                    with col4:
                        strategy_vs_kodex = total_return - kodex_total_net_return_pct
                        st.metric("Strategy vs KODEX 200", f"{strategy_vs_kodex:+.2f}%", f"{strategy_vs_kodex:+.2f}%")
                    
                    # 성과 비교 요약
                    st.write("### 🎯 Performance Summary vs KODEX 200")
                    if total_return > kodex_total_net_return_pct:
                        st.success(f"🏆 **Strategy outperformed KODEX 200 by {total_return - kodex_total_net_return_pct:+.2f}%**")
                        st.write(f"💰 **Strategy Final Value**: {final_value:,.0f} vs **KODEX 200 Final Value**: {kodex_final_value:,.0f}")
                    elif total_return < kodex_total_net_return_pct:
                        st.error(f"📉 **Strategy underperformed KODEX 200 by {kodex_total_net_return_pct - total_return:+.2f}%**")
                        st.write(f"💰 **Strategy Final Value**: {final_value:,.0f} vs **KODEX 200 Final Value**: {kodex_final_value:,.0f}")
                    else:
                        st.info("➖ **Strategy matched KODEX 200 performance**")
                        st.write(f"💰 **Both Final Values**: {final_value:,.0f}")
                    
                    # 승률 계산
                    strategy_wins = sum(1 for ret in cycle_returns if ret > 0)
                    total_cycles = len(cycle_returns)
                    win_rate = round(strategy_wins / total_cycles * 100, 1) if total_cycles > 0 else 0
                    
                    st.write(f"📊 **Strategy Win Rate**: {win_rate}% ({strategy_wins}/{total_cycles} cycles)")
                    
            except Exception as e:
                st.warning(f"Error calculating overall KODEX 200 comparison: {e}")


st.write("---")
st.write("## 📖 앱 사용법 가이드")

with st.expander("🔍 **기본 설정 방법**", expanded=False):
    st.write("""
    ### 1. 백테스트 기간 설정
    - **Start Date**: 백테스트 시작일 선택
    - **End Date**: 백테스트 종료일 선택
    - **Evaluation Cycle**: 재평가 주기 선택 (1주, 2주, 1개월, 3개월)
    
    ### 2. 종목 선택
    - **Select Stocks**: 분석할 종목들을 선택
    - **Available Features**: 선택한 종목의 사용 가능한 변수들 확인
    """)

with st.expander("📊 **Market Hold Condition 설정**", expanded=False):
    st.write("""
    ### Market Hold Condition (KODEX 200 기준)
    - **Manual Input**: 직접 조건 입력 (예: kodex_close < kodex_sma20)
    - **KODEX 200 하락장**: close < sma20
    - **KODEX 200 급락장**: close < sma5
    - **KODEX 200 보합장**: abs(close - sma20) < sma20 * 0.02
    
    ### 사용 가능한 KODEX 200 변수들
    - kodex_close, kodex_open, kodex_high, kodex_low
    - kodex_sma5, kodex_sma20, kodex_sma60
    - kodex_rsi, kodex_macd, kodex_volume 등
    """)

with st.expander("⚙️ **Strategy Conditions 설정**", expanded=False):
    st.write("""
    ### 조건 설정 방법
    1. **Number of Conditions**: 설정할 조건 개수 (1~10개)
    2. **Condition 입력**: 각 조건을 텍스트로 입력
    3. **Required 체크박스**: 필수 조건 여부 설정
    
    ### 조건 예시
    - **기술적 지표**: sma20 > sma60, rsi < 30, volume > 1000000
    - **가격 조건**: close > open, high > close * 1.02
    - **복합 조건**: (sma20 > sma60) & (rsi < 70) & (volume > 500000)
    
    ### 조건 우선순위
    - **필수 조건**: 모든 필수 조건을 만족해야 함
    - **선택 조건**: 만족하는 선택 조건 개수로 우선순위 결정
    """)

with st.expander("🎯 **투자 설정**", expanded=False):
    st.write("""
    ### 투자 설정
    1. **Max Number of Stocks to Hold**: 최대 보유 종목 수 (1~10개)
    2. **Minimum Satisfied Conditions**: 보유하기 위한 최소 선택 조건 개수
    
    ### 투자 결정 로직
    1. **필수 조건 확인**: 모든 필수 조건을 만족하는 종목만 후보
    2. **선택 조건 카운트**: 만족하는 선택 조건 개수 계산
    3. **우선순위 정렬**: 선택 조건 개수가 많은 순서대로 정렬
    4. **최종 선택**: 최소 조건을 만족하는 종목들 중 상위 순서로 선택
    """)

with st.expander("📈 **결과 해석**", expanded=False):
    st.write("""
    ### 사이클별 결과
    - **Held Stocks**: 실제 보유한 종목들의 수익률
    - **All Stocks Performance**: 모든 후보 종목의 수익률 비교
    - **KODEX 200 Comparison**: KODEX 200과의 사이클별 비교
    
    ### 전체 성과
    - **Strategy Performance**: 전략의 전체 수익률 및 MDD
    - **Equal Weight Performance**: 균등투자 전략과의 비교
    - **KODEX 200 Comparison**: KODEX 200과의 전체 기간 비교
    
    ### 성과 지표
    - **Total Return**: 전체 수익률
    - **MDD (Maximum Drawdown)**: 최대 낙폭
    - **Win Rate**: 승률 (수익 사이클 비율)
    """)

with st.expander("⚠️ **주의사항**", expanded=False):
    st.write("""
    ### 중요 사항
    1. **미래 데이터 누락 방지**: 모든 조건은 이전 사이클 데이터로 평가
    2. **거래세 적용**: 매도 시점에만 0.35% 거래세 적용
    3. **데이터 가용성**: 선택한 기간에 데이터가 있는 종목만 분석
    4. **조건 설정**: 올바른 변수명과 문법으로 조건 입력
    
    ### 팁
    - **조건 테스트**: 간단한 조건부터 시작하여 점진적으로 복잡하게
    - **성과 비교**: KODEX 200과의 비교로 전략 성과 평가
    - **위험 관리**: MDD를 고려한 리스크 관리
    """)

with st.expander("🔧 **고급 기능**", expanded=False):
    st.write("""
    ### 고급 설정
    1. **Market Hold Condition**: 시장 상황에 따른 투자 중단
    2. **필수/선택 조건**: 조건의 중요도에 따른 분류
    3. **최소 조건 설정**: 보유 기준의 엄격함 조절
    4. **최대 보유 개수**: 포트폴리오 분산도 조절
    
    ### 성과 분석
    - **사이클별 분석**: 각 재평가 시점의 성과 확인
    - **종목별 분석**: 보유/미보유 종목의 수익률 비교
    - **벤치마크 비교**: KODEX 200과의 성과 비교
    """)

