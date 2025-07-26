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


DATA_FOLDER = os.path.dirname(__file__)  # 현재 디렉터리 기준
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

st.subheader("Market Holding Condition")
market_hold_condition = st.text_input("Market Hold Condition (ex: market_trend == 'bad')", value="")

st.subheader("Strategy Conditions")
conditions = []
required_flags = []
num_conditions = st.number_input("Number of Conditions", min_value=1, max_value=5, value=1, step=1)

for i in range(num_conditions):
    cols = st.columns([3, 1])
    cond = cols[0].text_input(f"Condition {i+1}", key=f"cond_{i}", placeholder="Example: sma20 > sma60")
    required = cols[1].checkbox("Required", key=f"req_{i}")
    if cond.strip():
        conditions.append(cond.strip())
        required_flags.append(required)

max_stock_count = st.number_input("Max Number of Stocks to Hold", min_value=1, max_value=10, value=3, step=1)

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

        all_results = []
        equity_curve = []
        cycle_returns = []
        portfolio_value = 100000000
        initial_value = portfolio_value

        for i, (d_start, d_end) in enumerate(date_ranges):
            st.markdown(f"### Cycle {i+1}: {d_start} ~ {d_end}")
            results = []
            prices = {}

            # 시장 보유 조건 평가
            market_hold = False
            if market_hold_condition.strip():
                try:
                    sample_code = selected_codes[0]
                    df_sample = pd.read_csv(os.path.join(DATA_FOLDER, f"{sample_code}_features.csv"))
                    date_col = find_column(df_sample, ['date', 'Date', '날짜'])
                    df_sample[date_col] = pd.to_datetime(df_sample[date_col])
                    df_cycle_sample = df_sample[(df_sample[date_col] >= pd.to_datetime(d_start)) & (df_sample[date_col] <= pd.to_datetime(d_end))].copy()
                    if len(df_cycle_sample) > 0:
                        local_dict = {col: df_cycle_sample.iloc[0][col] for col in df_cycle_sample.columns}
                        market_hold = eval(market_hold_condition, {}, local_dict)
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
                    
                    df_cycle = df[(df[date_col] >= pd.to_datetime(d_start)) & (df[date_col] <= pd.to_datetime(d_end))].copy()

                    required_satisfied = True
                    for cond, req in zip(conditions, required_flags):
                        if req:
                            try:
                                if len(df_cycle.query(cond)) == 0:
                                    required_satisfied = False
                                    break
                            except Exception:
                                required_satisfied = False
                                break
                    if not required_satisfied:
                        continue

                    satisfied_count = 0
                    non_required_conditions = [(cond, req) for cond, req in zip(conditions, required_flags) if not req]
                    if len(non_required_conditions) == 0:
                        satisfied_count = 100
                    else:
                        for cond, req in non_required_conditions:
                            try:
                                if len(df_cycle.query(cond)) > 0:
                                    satisfied_count += 1
                            except Exception:
                                pass

                    df_sorted = df_cycle.sort_values(by=date_col)
                    if len(df_sorted) >= 1:
                        start_price = df_sorted.iloc[0]["close"]
                        if len(df_sorted) >= 2:
                            end_price = df_sorted.iloc[-1]["close"]
                        else:
                            df_before_cycle = df[df[date_col] < pd.to_datetime(d_start)].copy()
                            if len(df_before_cycle) > 0:
                                df_before_sorted = df_before_cycle.sort_values(by=date_col)
                                end_price = df_before_sorted.iloc[-1]["close"]
                            else:
                                end_price = start_price
                        prices[code] = {
                            "start": start_price,
                            "end": end_price
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

            if results:
                df_result = pd.DataFrame(results)
                df_result = df_result.sort_values(by=["Satisfied Conditions"], ascending=[False])
                st.dataframe(df_result[["Cycle", "Code", "Name", "Satisfied Conditions"]])
                all_results.extend(df_result.to_dict("records"))

                top_codes = df_result[df_result["Satisfied Conditions"] > 0].head(max_stock_count)["Code"].tolist()
                if top_codes:
                    invested_each = portfolio_value / len(top_codes)
                    total_value = 0
                    summary = []
                    for code in top_codes:
                        p = prices.get(code)
                        if p and p["start"] > 0:
                            ret = (p["end"] - p["start"]) / p["start"]
                            value = invested_each * (1 + ret)
                            total_value += value
                            summary.append({"Code": code, "Name": CODE_TO_NAME.get(code, code), "Return %": round(ret * 100, 2)})
                    portfolio_value = total_value
                    st.write("Held Stocks")
                    st.dataframe(pd.DataFrame(summary))
                    cycle_ret = round((portfolio_value - equity_curve[-1]["Value"])/equity_curve[-1]["Value"]*100 if equity_curve else (portfolio_value - initial_value)/initial_value*100, 2)
                    cycle_returns.append(cycle_ret)
                else:
                    cycle_returns.append(0.0)
                equity_curve.append({"Cycle": f"Cycle {i+1}", "Value": portfolio_value})
            else:
                st.warning("No matching results found for this interval.")
                equity_curve.append({"Cycle": f"Cycle {i+1}", "Value": portfolio_value})
                cycle_returns.append(0.0)

        if all_results:
            final_df = pd.DataFrame(all_results)
            csv = final_df.to_csv(index=False).encode("utf-8-sig")
            st.download_button("Download Full Results (CSV)", data=csv, file_name="full_results.csv", mime="text/csv")

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

            # 비교전략: 전체 기간 동안 KODEX 200 보유 (매 사이클 재투자 방식)
            if "069500" in stock_codes:
                df_kodex = pd.read_csv(os.path.join(DATA_FOLDER, "069500_features.csv"))
                date_col = find_column(df_kodex, ['date', 'Date'])
                df_kodex[date_col] = pd.to_datetime(df_kodex[date_col])
                df_kodex = df_kodex[(df_kodex[date_col] >= pd.to_datetime(start_date)) & (df_kodex[date_col] <= pd.to_datetime(end_date))]
                df_kodex = df_kodex.sort_values(by=date_col)
                kodex_value = initial_value
                kodex_curve = []
                for d_start, d_end in date_ranges:
                    df_cycle = df_kodex[(df_kodex[date_col] >= pd.to_datetime(d_start)) & (df_kodex[date_col] <= pd.to_datetime(d_end))]
                    if len(df_cycle) >= 2:
                        start_price = df_cycle.iloc[0]["close"]
                        end_price = df_cycle.iloc[-1]["close"]
                        ret = (end_price - start_price) / start_price
                        kodex_value *= (1 + ret)
                    kodex_curve.append(kodex_value)
                buyhold_return = round((kodex_value - initial_value) / initial_value * 100, 2)
                # MDD 계산
                mdd = 0
                for i in range(len(kodex_curve)):
                    peak = kodex_curve[i]
                    trough = kodex_curve[i:]
                    if len(trough) > 0:
                        drawdown = (peak - min(trough)) / peak
                        mdd = max(mdd, drawdown)
                buyhold_mdd = round(mdd * 100, 2)
                st.metric("Buy and Hold (KODEX 200, Rolling)", f"{buyhold_return}%")
                st.metric("Buy and Hold (KODEX 200, Rolling) MDD", f"{buyhold_mdd}%")
