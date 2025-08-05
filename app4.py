import streamlit as st
import pandas as pd
import os
from glob import glob
import datetime as dt
import traceback

def find_column(df, target_names):
    for col in df.columns:
        if col.strip().lower() in [name.lower() for name in target_names]:
            return col
    return None

# 재평가일 계산 함수
def calculate_evaluation_dates(trading_dates, start_date, end_date, eval_type):
    """
    거래일 목록에서 재평가일을 계산하는 함수
    
    Args:
        trading_dates: 전체 거래일 목록
        start_date: 시작일
        end_date: 종료일
        eval_type: 평가 유형 ("weekly_first", "monthly_1_3_weeks", "monthly_first")
    
    Returns:
        evaluation_dates: 재평가일 목록
    """
    # 선택된 기간의 거래일만 필터링
    period_dates = [d for d in trading_dates if start_date <= d <= end_date]
    
    if not period_dates:
        return []
    
    evaluation_dates = []
    
    if eval_type == "weekly_first":
        # 매주의 첫 거래일
        current_week_start = None
        for date in period_dates:
            # 해당 주의 시작일 (월요일) 계산
            week_start = date - dt.timedelta(days=date.weekday())
            
            if current_week_start != week_start:
                current_week_start = week_start
                evaluation_dates.append(date)
    
    elif eval_type == "monthly_1_3_weeks":
        # 매달 1-3주의 첫 거래일
        current_month = None
        current_week_in_month = None
        
        for date in period_dates:
            month_key = (date.year, date.month)
            
            if current_month != month_key:
                current_month = month_key
                current_week_in_month = 0
            
            # 해당 월의 몇 번째 주인지 계산
            week_start = date - dt.timedelta(days=date.weekday())
            month_start = date.replace(day=1)
            week_in_month = ((week_start - month_start).days // 7) + 1
            
            if week_in_month <= 3 and week_in_month != current_week_in_month:
                current_week_in_month = week_in_month
                evaluation_dates.append(date)
    
    elif eval_type == "monthly_first":
        # 매달의 첫 거래일
        current_month = None
        
        for date in period_dates:
            month_key = (date.year, date.month)
            
            if current_month != month_key:
                current_month = month_key
                evaluation_dates.append(date)
    
    return evaluation_dates

# 새로운 feature 계산 함수
def calculate_recent_high_feature(df, evaluation_date, pct=8):
    """
    재평가일 전날 종가가 최근 5일 중 최저값보다 지정된 % 이상 큰지 확인하는 feature
    
    Args:
        df: 주식 데이터프레임
        evaluation_date: 재평가일
        pct: 퍼센트 (기본값: 8)
    
    Returns:
        recent_high_Xpct: True/False (조건 만족 여부)
    """
    try:
        date_col = find_column(df, ['date', 'Date', '날짜'])
        close_col = find_column(df, ['close', 'Close', '종가'])
        
        if not date_col or not close_col:
            return False
        
        df[date_col] = pd.to_datetime(df[date_col])
        
        # 재평가일 전날
        yesterday = evaluation_date - dt.timedelta(days=1)
        
        # 최근 5일 데이터 (재평가일 기준 -1, -2, -3, -4, -5일)
        recent_5_days = []
        for i in range(1, 6):
            check_date = evaluation_date - dt.timedelta(days=i)
            day_data = df[df[date_col] == pd.to_datetime(check_date)]
            if len(day_data) > 0:
                recent_5_days.append({
                    'date': check_date,
                    'close': day_data.iloc[0][close_col]
                })
        
        if len(recent_5_days) < 2:  # 최소 2일 이상의 데이터 필요
            return False
        
        # 전날 종가
        yesterday_data = df[df[date_col] == pd.to_datetime(yesterday)]
        if len(yesterday_data) == 0:
            return False
        
        yesterday_close = yesterday_data.iloc[0][close_col]
        
        # 최근 5일 중 최저값
        min_close = min([day['close'] for day in recent_5_days])
        
        # 전날 종가가 최저값보다 지정된 % 이상 큰지 확인
        threshold = min_close * (1 + pct/100)
        recent_high_pct = yesterday_close >= threshold
        
        return recent_high_pct
        
    except Exception as e:
        st.warning(f"Error calculating recent_high_{pct}pct feature: {e}")
        return False

def calculate_recent_high_8pct(df, evaluation_date):
    """8% 버전"""
    return calculate_recent_high_feature(df, evaluation_date, 8)

def calculate_recent_high_5pct(df, evaluation_date):
    """5% 버전"""
    return calculate_recent_high_feature(df, evaluation_date, 5)

def calculate_recent_high_3pct(df, evaluation_date):
    """3% 버전"""
    return calculate_recent_high_feature(df, evaluation_date, 3)

# 사용 가능한 feature 목록과 설명
AVAILABLE_FEATURES = {
    # 기본 가격 데이터
    "open": "시가",
    "high": "고가", 
    "low": "저가",
    "close": "종가",
    "volume": "거래량",
    
    # 이동평균선
    "sma5": "5일 이동평균선",
    "sma10": "10일 이동평균선", 
    "sma20": "20일 이동평균선",
    "sma60": "60일 이동평균선",
    "sma120": "120일 이동평균선",
    
    # 지수이동평균선
    "ema12": "12일 지수이동평균선",
    "ema26": "26일 지수이동평균선",
    
    # 기술적 지표
    "rsi": "RSI (상대강도지수)",
    "macd": "MACD",
    "macd_signal": "MACD 시그널",
    "macd_histogram": "MACD 히스토그램",
    "bb_upper": "볼린저 밴드 상단",
    "bb_middle": "볼린저 밴드 중간",
    "bb_lower": "볼린저 밴드 하단",
    "bb_width": "볼린저 밴드 폭",
    "bb_position": "볼린저 밴드 위치",
    
    # 거래량 지표
    "volume_sma5": "5일 거래량 이동평균",
    "volume_sma20": "20일 거래량 이동평균",
    "volume_ratio": "거래량 비율",
    
    # 변동성 지표
    "atr": "ATR (평균진폭)",
    "volatility": "변동성",
    
    # 새로운 feature
    "recent_high_8pct": "재평가일 전날 종가가 최근 5일 중 최저값보다 8% 이상 큰 상황",
    "recent_high_5pct": "재평가일 전날 종가가 최근 5일 중 최저값보다 5% 이상 큰 상황",
    "recent_high_3pct": "재평가일 전날 종가가 최근 5일 중 최저값보다 3% 이상 큰 상황"
}



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


DATA_FOLDER = "/home/hanmil/backtest_app" # os.path.dirname(__file__) 
st.set_page_config(page_title="Stock Screening App", layout="wide")
st.title("Stock Screening App")

# KODEX 200 데이터에서 거래일 추출
def get_trading_dates():
    try:
        df_kodex = pd.read_csv(os.path.join(DATA_FOLDER, "069500_features.csv"))
        date_col = find_column(df_kodex, ['date', 'Date', '날짜'])
        if date_col:
            df_kodex[date_col] = pd.to_datetime(df_kodex[date_col])
            trading_dates = df_kodex[date_col].dt.date.unique()
            trading_dates = sorted(trading_dates)
            return trading_dates
        else:
            st.error("날짜 컬럼을 찾을 수 없습니다.")
            return []
    except Exception as e:
        st.error(f"KODEX 200 데이터 로드 중 오류: {e}")
        return []

# 거래일 목록 가져오기
trading_dates = get_trading_dates()

if trading_dates:
    # 거래일 범위 계산
    min_date = min(trading_dates)
    max_date = max(trading_dates)
    
    # 2019년 1월 1일부터 2025년 6월 30일까지의 거래일 필터링
    start_limit = dt.date(2019, 1, 1)
    end_limit = dt.date(2025, 6, 30)
    filtered_trading_dates = [d for d in trading_dates if start_limit <= d <= end_limit]
    
    if filtered_trading_dates:
        # 연도별, 월별, 일별로 거래일 그룹화
        years = sorted(list(set(d.year for d in filtered_trading_dates)))
        years_str = [str(year) for year in years]
        
        # 시작일과 종료일 선택
        st.subheader("📅 기간 선택")
        st.write("**거래일만 선택 가능합니다** (2019년 1월 1일 ~ 2025년 6월 30일)")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**시작일**")
            # 시작일 연도 선택
            start_year = st.selectbox("연도", years_str, index=0, key="start_year")
            
            # 시작일 월 선택
            start_year_dates = [d for d in filtered_trading_dates if d.year == int(start_year)]
            start_months = sorted(list(set(d.month for d in start_year_dates)))
            start_months_str = [f"{month:02d}월" for month in start_months]
            start_month = st.selectbox("월", start_months_str, key="start_month")
            start_month_num = int(start_month.replace("월", ""))
            
            # 시작일 일 선택
            start_month_dates = [d for d in start_year_dates if d.month == start_month_num]
            start_days = sorted(list(set(d.day for d in start_month_dates)))
            start_days_str = [f"{day:02d}일" for day in start_days]
            start_day = st.selectbox("일", start_days_str, key="start_day")
            start_day_num = int(start_day.replace("일", ""))
            
            # 시작일 생성
            start_date = dt.date(int(start_year), start_month_num, start_day_num)
            
        with col2:
            st.write("**종료일**")
            # 종료일 연도 선택
            end_year = st.selectbox("연도", years_str, index=len(years_str)-1, key="end_year")
            
            # 종료일 월 선택
            end_year_dates = [d for d in filtered_trading_dates if d.year == int(end_year)]
            end_months = sorted(list(set(d.month for d in end_year_dates)))
            end_months_str = [f"{month:02d}월" for month in end_months]
            end_month = st.selectbox("월", end_months_str, index=len(end_months_str)-1, key="end_month")
            end_month_num = int(end_month.replace("월", ""))
            
            # 종료일 일 선택
            end_month_dates = [d for d in end_year_dates if d.month == end_month_num]
            end_days = sorted(list(set(d.day for d in end_month_dates)))
            end_days_str = [f"{day:02d}일" for day in end_days]
            end_day = st.selectbox("일", end_days_str, index=len(end_days_str)-1, key="end_day")
            end_day_num = int(end_day.replace("일", ""))
            
            # 종료일 생성
            end_date = dt.date(int(end_year), end_month_num, end_day_num)
        
        # 날짜 유효성 검사
        if start_date > end_date:
            st.error("⚠️ 시작일이 종료일보다 늦습니다. 올바른 기간을 선택해주세요.")
        else:
            st.success(f"✅ 선택된 기간: {start_date} ~ {end_date}")

            # 거래일 정보 표시
            with st.expander("📅 거래일 정보"):
                    st.write(f"**전체 데이터 범위**: {min_date} ~ {max_date}")
                    st.write(f"**선택 가능 범위**: {start_limit} ~ {end_limit}")
                    st.write(f"**선택 가능한 거래일 수**: {len(filtered_trading_dates)}일")
                    st.write(f"**선택된 기간**: {start_date} ~ {end_date}")
                    
                    # 선택된 기간의 거래일 수 계산
                    selected_trading_dates = [d for d in filtered_trading_dates if start_date <= d <= end_date]
                    st.write(f"**선택된 기간 거래일 수**: {len(selected_trading_dates)}일")
                    
                    # 선택된 기간의 거래일 목록 표시 (처음 10개와 마지막 10개)
                    if len(selected_trading_dates) > 20:
                        display_dates = selected_trading_dates[:10] + ["..."] + selected_trading_dates[-10:]
                        st.write(f"**거래일 목록**: {', '.join([d.strftime('%Y-%m-%d') for d in display_dates if isinstance(d, dt.date)])}")
                    else:
                        st.write(f"**거래일 목록**: {', '.join([d.strftime('%Y-%m-%d') for d in selected_trading_dates])}")

    interval_days_map = {
    "매주의 첫 거래일": "weekly_first",
    "매달 1-3주의 첫 거래일": "monthly_1_3_weeks",
    "매달의 첫 거래일": "monthly_first"
}
eval_cycle = st.selectbox("Evaluation Interval", list(interval_days_map.keys()), key="eval_cycle_main")
eval_type = interval_days_map[eval_cycle]

# 재평가일 계산
if trading_dates and 'start_date' in locals() and 'end_date' in locals():
    evaluation_dates = calculate_evaluation_dates(trading_dates, start_date, end_date, eval_type)
    
    # 재평가일 정보 표시
    with st.expander("📊 재평가일 정보"):
        st.write(f"**재평가 유형**: {eval_cycle}")
        st.write(f"**총 재평가일 수**: {len(evaluation_dates)}일")
        
        if evaluation_dates:
            st.write(f"**첫 재평가일**: {evaluation_dates[0]}")
            st.write(f"**마지막 재평가일**: {evaluation_dates[-1]}")
            
            # 재평가일 목록 표시 (처음 10개와 마지막 10개)
            if len(evaluation_dates) > 20:
                display_dates = evaluation_dates[:10] + ["..."] + evaluation_dates[-10:]
                date_strings = []
                for d in display_dates:
                    if isinstance(d, dt.date):
                        date_strings.append(d.strftime('%Y-%m-%d'))
                    else:
                        date_strings.append(str(d))
                st.write(f"**재평가일 목록**: {', '.join(date_strings)}")
            else:
                st.write(f"**재평가일 목록**: {', '.join([d.strftime('%Y-%m-%d') for d in evaluation_dates])}")
        else:
            st.warning("선택된 기간에 재평가일이 없습니다.")

# ==============================
# 주식 종목 선택
# ==============================
st.subheader("📈 주식 종목 선택")

file_paths = sorted(glob(os.path.join(DATA_FOLDER, "*_features.csv")))
stock_codes = [os.path.basename(p).split("_")[0] for p in file_paths]
stock_names = [f"{CODE_TO_NAME.get(code, code)} ({code})" for code in stock_codes]
selected_stocks = st.multiselect("Select Stocks", options=stock_names)
selected_codes = [name.split("(")[-1][:-1] for name in selected_stocks]

# ==============================
# UI 확장: 필수조건, 최대 보유 종목 수
# ==============================

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
        max_value=num_conditions, 
        value=1, 
        step=1,
        help=f"최소 몇 개의 조건을 만족해야 보유할지 설정 (전체 조건 개수: {num_conditions})"
    )
else:
    min_satisfied_conditions = 0
    st.info("💡 **Note**: 조건이 없으므로 모든 종목이 보유 대상입니다.")

# ==============================
# 매도 조건 설정
# ==============================
st.subheader("📉 매도 조건 설정")

# 익절, 트레일링 손절, 최대 손절 설정
col1, col2, col3 = st.columns(3)

with col1:
    take_profit_pct = st.number_input(
        "익절 (%)", 
        min_value=0.0, 
        max_value=100.0, 
        value=0.0, 
        step=0.1,
        help="수익률이 이 값에 도달하면 매도 (0 = 비활성화)"
    )

with col2:
    trailing_stop_pct = st.number_input(
        "트레일링 손절 (%)", 
        min_value=0.0, 
        max_value=100.0, 
        value=0.0, 
        step=0.1,
        help="최고점 대비 하락률이 이 값에 도달하면 매도 (0 = 비활성화)"
    )

with col3:
    max_loss_pct = st.number_input(
        "최대 손절 (%)", 
        min_value=0.0, 
        max_value=100.0, 
        value=0.0, 
        step=0.1,
        help="매수 대비 손실률이 이 값에 도달하면 매도 (0 = 비활성화)"
    )

# 보유 기간 중 매도 조건 설정
st.write("**보유 기간 중 매도 조건** (재평가일을 기다리지 않고 조건 만족 시 즉시 매도)")

sell_conditions = []
sell_required_flags = []
num_sell_conditions = st.number_input("Number of Sell Conditions", min_value=0, max_value=5, value=0, step=1)

for i in range(num_sell_conditions):
    cols = st.columns([3, 1])
    sell_cond = cols[0].text_input(f"Sell Condition {i+1}", key=f"sell_cond_{i}", placeholder="Example: rsi > 80")
    sell_required = cols[1].checkbox("Required", key=f"sell_req_{i}")
    if sell_cond.strip():
        sell_conditions.append(sell_cond.strip())
        sell_required_flags.append(sell_required)

# 매도 조건 만족 시 최소 조건 수 설정
optional_sell_conditions_count = sum(1 for req in sell_required_flags if not req)  # 선택 매도 조건 개수 계산
if optional_sell_conditions_count > 0:
    min_satisfied_sell_conditions = st.number_input(
        "Minimum Satisfied Sell Conditions to Sell", 
        min_value=0, 
        max_value=optional_sell_conditions_count, 
        value=min(1, optional_sell_conditions_count), 
        step=1,
        help=f"최소 몇 개의 선택 매도 조건을 만족해야 매도할지 설정 (현재 선택 매도 조건 개수: {optional_sell_conditions_count})"
    )
else:
    min_satisfied_sell_conditions = 0
    if num_sell_conditions > 0:
        st.info("💡 **Note**: 선택 매도 조건이 없으므로 필수 조건만 만족하면 매도됩니다.")
    else:
        st.info("💡 **Note**: 매도 조건이 설정되지 않았습니다.")

# 매도 조건 설정 요약
with st.expander("📋 매도 조건 설정 요약"):
    st.write("**익절 설정**:")
    if take_profit_pct > 0:
        st.write(f"- 익절: {take_profit_pct}%")
    else:
        st.write("- 익절: 비활성화")
    
    st.write("**손절 설정**:")
    if trailing_stop_pct > 0:
        st.write(f"- 트레일링 손절: {trailing_stop_pct}%")
    else:
        st.write("- 트레일링 손절: 비활성화")
    
    if max_loss_pct > 0:
        st.write(f"- 최대 손절: {max_loss_pct}%")
    else:
        st.write("- 최대 손절: 비활성화")
    
    st.write("**보유 기간 중 매도 조건**:")
    if sell_conditions:
        for i, (cond, req) in enumerate(zip(sell_conditions, sell_required_flags)):
            status = "필수" if req else "선택"
            st.write(f"- 조건 {i+1}: {cond} ({status})")
        st.write(f"- 최소 만족 조건 수: {min_satisfied_sell_conditions}")
    else:
        st.write("- 설정된 매도 조건 없음")

if selected_codes:
    try:
        df_sample = pd.read_csv(os.path.join(DATA_FOLDER, f"{selected_codes[0]}_features.csv"))
        with st.expander("Available Features"):
            st.write(", ".join(df_sample.columns))
    except Exception as e:
        st.warning(f"Error loading file: {e}")

# ==============================
# 사용 가능한 Feature 목록
# ==============================
st.subheader("📋 사용 가능한 Feature 목록")

# Feature 카테고리별로 표시
feature_categories = {
    "기본 가격 데이터": ["open", "high", "low", "close", "volume"],
    "이동평균선": ["sma5", "sma10", "sma20", "sma60", "sma120"],
    "지수이동평균선": ["ema12", "ema26"],
    "기술적 지표": ["rsi", "macd", "macd_signal", "macd_histogram", "bb_upper", "bb_middle", "bb_lower", "bb_width", "bb_position"],
    "거래량 지표": ["volume_sma5", "volume_sma20", "volume_ratio"],
    "변동성 지표": ["atr", "volatility"],
    "새로운 Feature": ["recent_high_8pct"]
}

for category, features in feature_categories.items():
    with st.expander(f"🔍 {category}"):
        for feature in features:
            if feature in AVAILABLE_FEATURES:
                st.write(f"**{feature}**: {AVAILABLE_FEATURES[feature]}")
            else:
                st.write(f"**{feature}**: 설명 없음")

# 새로운 feature 상세 설명
with st.expander("🆕 새로운 Feature 상세 설명"):
    st.write("### recent_high_8pct")
    st.write("**설명**: 재평가일 전날 종가가 최근 5일 중 최저값보다 8% 이상 큰 상황")
    st.write("**계산 방법**:")
    st.write("1. 재평가일 기준 -1, -2, -3, -4, -5일의 종가 수집")
    st.write("2. 이 5일 중 최저값 계산")
    st.write("3. 재평가일 전날 종가가 최저값의 1.08배(8% 증가) 이상인지 확인")
    st.write("**사용 예시**: `recent_high_8pct == True`")
    st.write("**의미**: 최근 5일 중 저점이 있었고, 현재 가격이 그 저점보다 8% 이상 회복된 상황")

# ==============================
# 분석 실행 버튼
# ==============================
st.subheader("🚀 분석 실행")

if st.button("Run Analysis"):
    if not selected_codes or not conditions:
        st.warning("Please select stocks and enter at least one condition.")
    else:
        st.write("**선택된 종목**:", selected_codes)
        st.write("**설정된 조건**:", conditions)
        st.write("**재평가일 수**:", len(evaluation_dates) if 'evaluation_dates' in locals() else 0)
        
        # 통합된 분석 로직 (app3 스타일 주식 선택 + 기존 매도 조건)
        if 'evaluation_dates' in locals() and evaluation_dates:
            st.subheader("📊 리밸런싱 백테스트 결과")
            
            # 초기 설정
            portfolio_value = 100000000  # 1억원
            initial_value = portfolio_value
            equity_curve = [{"Cycle": "Initial", "Value": initial_value}]  # 초기값 추가
            cycle_returns = []
            held_stocks = []  # 현재 보유 중인 종목들
            stock_positions = {}  # 각 종목의 매수 정보 저장
            
            # 현금 보유 변수 추가
            cash_holding = False
            
            # 각 사이클별 상세 결과 저장
            cycle_details = []
            
            for i, rebalancing_date in enumerate(evaluation_dates):
                # 사이클 시작/종료일 계산
                cycle_start = rebalancing_date
                if i < len(evaluation_dates) - 1:
                    cycle_end = evaluation_dates[i+1]
                else:
                    # 마지막 사이클: 선택된 종료일까지만
                    cycle_end = end_date

                st.markdown(f"### 리밸런싱 {i+1}: {cycle_start} ~ {cycle_end}")

                # 매수 실행 (매일 조건 재평가)
                buy_summary = []
                cash_holding = True
                buy_executed = False
                
                # 사이클 내 모든 거래일에서 매수 조건 체크
                cycle_trading_dates = [d for d in trading_dates if cycle_start <= d < cycle_end]
                
                for check_date in cycle_trading_dates:
                    if buy_executed:  # 이미 매수했으면 더 이상 체크하지 않음
                        break
                        
                    # 해당 날짜까지의 데이터로 조건 평가
                    yesterday = check_date - dt.timedelta(days=1)
                    
                    # 각 종목별 조건 만족 개수 계산
                    stock_condition_counts = []
                    
                    for code in selected_codes:
                        try:
                            df = pd.read_csv(os.path.join(DATA_FOLDER, f"{code}_features.csv"))
                            date_col = find_column(df, ['date', 'Date', '날짜'])
                            df[date_col] = pd.to_datetime(df[date_col])
                            
                            # D-1까지의 데이터로 조건 평가
                            df_until_yesterday = df[df[date_col] <= pd.to_datetime(yesterday)].copy()
                            if len(df_until_yesterday) > 0:
                                # 조건 평가
                                conditions_satisfied = 0
                                required_satisfied = True
                                
                                for cond, req in zip(conditions, required_flags):
                                    try:
                                        # recent_high_Xpct feature들은 실시간 계산
                                        if 'recent_high_8pct' in cond:
                                            # 실시간으로 recent_high_8pct 계산
                                            recent_high_8pct_value = calculate_recent_high_8pct(df, check_date)
                                            
                                            # 조건 평가 (recent_high_8pct == True 또는 recent_high_8pct == recent_high_8pct)
                                            if 'recent_high_8pct == True' in cond or 'recent_high_8pct == recent_high_8pct' in cond:
                                                condition_satisfied = recent_high_8pct_value
                                            else:
                                                condition_satisfied = not recent_high_8pct_value
                                        elif 'recent_high_5pct' in cond:
                                            # 실시간으로 recent_high_5pct 계산
                                            recent_high_5pct_value = calculate_recent_high_5pct(df, check_date)
                                            
                                            # 조건 평가
                                            if 'recent_high_5pct == True' in cond or 'recent_high_5pct == recent_high_5pct' in cond:
                                                condition_satisfied = recent_high_5pct_value
                                            else:
                                                condition_satisfied = not recent_high_5pct_value
                                        elif 'recent_high_3pct' in cond:
                                            # 실시간으로 recent_high_3pct 계산
                                            recent_high_3pct_value = calculate_recent_high_3pct(df, check_date)
                                            
                                            # 조건 평가
                                            if 'recent_high_3pct == True' in cond or 'recent_high_3pct == recent_high_3pct' in cond:
                                                condition_satisfied = recent_high_3pct_value
                                            else:
                                                condition_satisfied = not recent_high_3pct_value
                                            
                                            if req:  # 필수 조건
                                                if not condition_satisfied:
                                                    required_satisfied = False
                                                    break
                                            else:  # 선택 조건
                                                if condition_satisfied:
                                                    conditions_satisfied += 1
                                        else:
                                            # 기존 방식으로 조건 평가
                                            if req:  # 필수 조건
                                                if len(df_until_yesterday.query(cond)) == 0:
                                                    required_satisfied = False
                                                    break
                                            else:  # 선택 조건
                                                if len(df_until_yesterday.query(cond)) > 0:
                                                    conditions_satisfied += 1
                                    except Exception as e:
                                        st.warning(f"Error evaluating condition '{cond}' for {code}: {e}")
                                        if req:
                                            required_satisfied = False
                                            break
                                
                                # 조건을 만족하면 후보에 추가
                                if required_satisfied and conditions_satisfied >= min_satisfied_conditions:
                                    stock_condition_counts.append({
                                        'code': code,
                                        'name': CODE_TO_NAME.get(code, code),
                                        'conditions_satisfied': conditions_satisfied,
                                        'required_satisfied': required_satisfied
                                    })
                        except Exception as e:
                            st.warning(f"Error evaluating {code}: {e}")
                    
                    # 조건 만족 개수 순으로 정렬
                    stock_condition_counts.sort(key=lambda x: x['conditions_satisfied'], reverse=True)
                    
                    # 보유 종목 선정
                    buy_codes = []
                    if stock_condition_counts:
                        max_conditions = stock_condition_counts[0]['conditions_satisfied']
                        # 가장 많이 만족한 종목들만 선택
                        top_stocks = [stock for stock in stock_condition_counts 
                                     if stock['conditions_satisfied'] == max_conditions]
                        
                        if len(top_stocks) <= max_stock_count:
                            buy_codes = [stock['code'] for stock in top_stocks]
                        else:
                            # max_stock_count보다 많으면 랜덤 선택
                            import random
                            buy_codes = [stock['code'] for stock in random.sample(top_stocks, max_stock_count)]
                    
                    # 매수 실행 (다음날 시가로 매수)
                    if buy_codes:
                         cash_holding = False
                         buy_executed = True
                         st.write(f"📈 {check_date} : 조건을 만족하는 종목 발견")
                         st.write(f"📈 선택된 종목: {', '.join([CODE_TO_NAME.get(code, code) for code in buy_codes])}")
                         st.write(f"📊 조건 만족 개수: {max_conditions}개")
                         
                         # 다음 거래일 찾기 (다음 리밸런싱일과 겹치지 않도록)
                         next_trading_day = None
                         for trading_date in trading_dates:
                             if trading_date > check_date and trading_date < cycle_end:
                                 next_trading_day = trading_date
                                 break
                         
                         if next_trading_day:
                             # 다음날 시가로 매수
                             invest_per_stock = portfolio_value / len(buy_codes)
                             
                             # 디버깅 로그 추가
                             st.write(f"🔍 매수 디버깅: portfolio_value={portfolio_value:,.0f}, 종목수={len(buy_codes)}, 투자금액={invest_per_stock:,.0f}")
                             
                             for code in buy_codes:
                                 try:
                                     df = pd.read_csv(os.path.join(DATA_FOLDER, f"{code}_features.csv"))
                                     date_col = find_column(df, ['date', 'Date', '날짜'])
                                     open_col = find_column(df, ['open', 'Open', '시가'])
                                     df[date_col] = pd.to_datetime(df[date_col])
                                     df_buy = df[df[date_col] == pd.to_datetime(next_trading_day)]
                                     if len(df_buy) > 0:
                                         open_price = df_buy.iloc[0][open_col]
                                         shares = invest_per_stock / open_price if open_price > 0 else 0
                                         
                                         # 디버깅 로그 추가
                                         st.write(f"🔍 {code} 매수: 시가={open_price:,.0f}, 수량={shares:.2f}, 투자금액={invest_per_stock:,.0f}")
                                         
                                         buy_summary.append({
                                             "Code": code,
                                             "Name": CODE_TO_NAME.get(code, code),
                                             "Buy Date": next_trading_day,
                                             "Buy Price": f"{open_price:,.0f}",
                                             "Shares": f"{shares:.2f}",
                                             "Investment": f"{invest_per_stock:,.0f}"
                                         })
                                         # 포트폴리오에 추가
                                         held_stocks.append(code)
                                         stock_positions[code] = {
                                             'buy_price': open_price,
                                             'buy_date': next_trading_day,
                                             'shares': shares
                                         }
                                     else:
                                         st.warning(f"⚠️ {code}: {next_trading_day} 거래일 데이터 없음")
                                 except Exception as e:
                                     st.warning(f"Error buying {code}: {e}")
                             
                             if not held_stocks:
                                 st.error(f"❌ 매수 실패: 모든 종목에서 매수 수량이 0이거나 데이터 오류")
                             else:
                                 # 매수 후 포트폴리오 가치 계산
                                 total_investment = sum(stock_positions[code]['shares'] * stock_positions[code]['buy_price'] for code in held_stocks)
                                 st.write(f"✅ 매수 완료: 총 투자금액 {total_investment:,.0f}원")
                         else:
                             st.warning(f"⚠️ 다음 거래일을 찾을 수 없음: {check_date} 이후 {cycle_end} 이전")
                         break  # 매수 완료 후 루프 종료
                    else:
                        # 조건을 만족하는 종목이 없으면 다음날로
                        continue
                
                # 현금보유 여부 결정
                if not buy_executed:
                    st.info(f"💰 {cycle_start} ~ {cycle_end} : 조건을 만족하는 종목이 없어 현금 보유 (수익률 0%)")
                    held_stocks = []
                    stock_positions = {}

                # 현금보유 시 처리
                if not buy_executed:
                    cycle_return = 0.0
                    equity_curve.append({"Cycle": f"리밸런싱 {i+1}", "Value": portfolio_value})
                    cycle_returns.append(cycle_return)
                    cycle_details.append({
                        'cycle': i+1,
                        'start_date': cycle_start,
                        'end_date': cycle_end,
                        'cash_holding': cash_holding,
                        'held_stocks': held_stocks.copy(),
                        'buy_summary': [],
                        'sell_summary': [],
                        'cycle_return': cycle_return,
                        'portfolio_value': portfolio_value
                    })
                    continue

                # 매도 조건 체크 및 매도 실행
                sell_summary = []
                total_buy = 0
                total_sell = 0
                
                # 사이클 내 모든 거래일에서 매도 조건 체크
                cycle_trading_dates = [d for d in trading_dates if cycle_start <= d < cycle_end]
                sold_codes = set()  # 이미 매도된 종목들
                
                for check_date in cycle_trading_dates:
                    for code in held_stocks[:]:  # 복사본으로 순회
                        if code in sold_codes:  # 이미 매도된 종목이면 건너뛰기
                            continue
                            
                        try:
                            df = pd.read_csv(os.path.join(DATA_FOLDER, f"{code}_features.csv"))
                            date_col = find_column(df, ['date', 'Date', '날짜'])
                            close_col = find_column(df, ['close', 'Close', '종가'])
                            df[date_col] = pd.to_datetime(df[date_col])
                            
                            # 해당 날짜의 데이터
                            df_check = df[df[date_col] == pd.to_datetime(check_date)]
                            if len(df_check) == 0:
                                continue
                            
                            current_close = df_check.iloc[0][close_col]
                            position = stock_positions.get(code, {})
                            buy_price = position.get('buy_price', 0)
                            shares = position.get('shares', 0)
                            highest_price = position.get('highest_price', buy_price)
                            
                            # 익절 체크
                            if take_profit_pct > 0 and buy_price > 0:
                                profit_pct = ((current_close - buy_price) / buy_price) * 100
                                if profit_pct >= take_profit_pct:
                                    sold_codes.add(code)
                                    sell_price = current_close * (1 - 0.0035)  # 수수료 적용
                                    profit_amount = (sell_price - buy_price) * shares
                                    sell_summary.append({
                                        "Code": code,
                                        "Name": CODE_TO_NAME.get(code, code),
                                        "Buy Date": position.get('buy_date', 'N/A'),
                                        "Buy Price": f"{buy_price:,.0f}",
                                        "Shares": f"{shares:.2f}",
                                        "Sell Date": check_date,
                                        "Sell Price": f"{sell_price:,.0f}",
                                        "Profit %": f"{profit_pct:+.2f}",
                                        "Profit Amount": f"{profit_amount:,.0f}",
                                        "Reason": "익절"
                                    })
                                    total_buy += buy_price * shares
                                    total_sell += sell_price * shares
                                    # 포트폴리오에서 제거
                                    held_stocks.remove(code)
                                    if code in stock_positions:
                                        del stock_positions[code]
                                    continue
                            
                            # 최대 손절 체크
                            if max_loss_pct > 0 and buy_price > 0:
                                loss_pct = ((buy_price - current_close) / buy_price) * 100
                                if loss_pct >= max_loss_pct:
                                    sold_codes.add(code)
                                    sell_price = current_close * (1 - 0.0035)  # 수수료 적용
                                    loss_amount = (sell_price - buy_price) * shares
                                    sell_summary.append({
                                        "Code": code,
                                        "Name": CODE_TO_NAME.get(code, code),
                                        "Buy Date": position.get('buy_date', 'N/A'),
                                        "Buy Price": f"{buy_price:,.0f}",
                                        "Shares": f"{shares:.2f}",
                                        "Sell Date": check_date,
                                        "Sell Price": f"{sell_price:,.0f}",
                                        "Profit %": f"{-loss_pct:+.2f}",
                                        "Profit Amount": f"{loss_amount:,.0f}",
                                        "Reason": "최대 손절"
                                    })
                                    total_buy += buy_price * shares
                                    total_sell += sell_price * shares
                                    # 포트폴리오에서 제거
                                    held_stocks.remove(code)
                                    if code in stock_positions:
                                        del stock_positions[code]
                                    continue
                            
                            # 트레일링 손절 체크
                            if trailing_stop_pct > 0 and buy_price > 0:
                                # 최고점 업데이트
                                if current_close > highest_price:
                                    highest_price = current_close
                                    stock_positions[code]['highest_price'] = highest_price
                                
                                # 트레일링 손절 체크
                                drop_from_high = ((highest_price - current_close) / highest_price) * 100
                                if drop_from_high >= trailing_stop_pct:
                                    sold_codes.add(code)
                                    sell_price = current_close * (1 - 0.0035)  # 수수료 적용
                                    profit_pct = ((sell_price - buy_price) / buy_price) * 100
                                    profit_amount = (sell_price - buy_price) * shares
                                    sell_summary.append({
                                        "Code": code,
                                        "Name": CODE_TO_NAME.get(code, code),
                                        "Buy Date": position.get('buy_date', 'N/A'),
                                        "Buy Price": f"{buy_price:,.0f}",
                                        "Shares": f"{shares:.2f}",
                                        "Sell Date": check_date,
                                        "Sell Price": f"{sell_price:,.0f}",
                                        "Profit %": f"{profit_pct:+.2f}",
                                        "Profit Amount": f"{profit_amount:,.0f}",
                                        "Reason": "트레일링 손절"
                                    })
                                    total_buy += buy_price * shares
                                    total_sell += sell_price * shares
                                    # 포트폴리오에서 제거
                                    held_stocks.remove(code)
                                    if code in stock_positions:
                                        del stock_positions[code]
                                    continue
                            
                            # 보유 기간 중 매도 조건 체크
                            if sell_conditions:
                                df_until_check = df[df[date_col] <= pd.to_datetime(check_date)].copy()
                                if len(df_until_check) > 0:
                                    sell_conditions_satisfied = 0
                                    sell_required_satisfied = True
                                    
                                    for sell_cond, sell_req in zip(sell_conditions, sell_required_flags):
                                        try:
                                            if sell_req:  # 필수 매도 조건
                                                if len(df_until_check.query(sell_cond)) == 0:
                                                    sell_required_satisfied = False
                                                    break
                                            else:  # 선택 매도 조건
                                                if len(df_until_check.query(sell_cond)) > 0:
                                                    sell_conditions_satisfied += 1
                                        except Exception:
                                            if sell_req:
                                                sell_required_satisfied = False
                                                break
                                    
                                    # 매도 조건 만족 시 매도 (다음날 시가로 매도)
                                    if sell_required_satisfied and sell_conditions_satisfied >= min_satisfied_sell_conditions:
                                        # 다음 거래일 찾기
                                        next_trading_day = None
                                        for trading_date in trading_dates:
                                            if trading_date > check_date:
                                                next_trading_day = trading_date
                                                break
                                        
                                        if next_trading_day:
                                            # 다음날 시가로 매도
                                            df_next = df[df[date_col] == pd.to_datetime(next_trading_day)]
                                            if len(df_next) > 0:
                                                open_col = find_column(df, ['open', 'Open', '시가'])
                                                next_open = df_next.iloc[0][open_col]
                                                sell_price = next_open * (1 - 0.0035)  # 수수료 적용
                                                profit_pct = ((sell_price - buy_price) / buy_price) * 100
                                                profit_amount = (sell_price - buy_price) * shares
                                                sell_summary.append({
                                                    "Code": code,
                                                    "Name": CODE_TO_NAME.get(code, code),
                                                    "Buy Date": position.get('buy_date', 'N/A'),
                                                    "Buy Price": f"{buy_price:,.0f}",
                                                    "Shares": f"{shares:.2f}",
                                                    "Sell Date": next_trading_day,
                                                    "Sell Price": f"{sell_price:,.0f}",
                                                    "Profit %": f"{profit_pct:+.2f}",
                                                    "Profit Amount": f"{profit_amount:,.0f}",
                                                    "Reason": "매도 조건 만족"
                                                })
                                                total_buy += buy_price * shares
                                                total_sell += sell_price * shares
                                                # 포트폴리오에서 제거
                                                held_stocks.remove(code)
                                                if code in stock_positions:
                                                    del stock_positions[code]
                                                sold_codes.add(code)
                                                continue
                                        
                        except Exception as e:
                            st.warning(f"Error checking sell conditions for {code}: {e}")
                
                # 리밸런싱일 시가로 남은 종목들 매도
                for code in held_stocks[:]:
                    try:
                        df = pd.read_csv(os.path.join(DATA_FOLDER, f"{code}_features.csv"))
                        date_col = find_column(df, ['date', 'Date', '날짜'])
                        open_col = find_column(df, ['open', 'Open', '시가'])
                        df[date_col] = pd.to_datetime(df[date_col])
                        df_sell = df[df[date_col] == pd.to_datetime(cycle_end)]
                        if len(df_sell) > 0:
                            open_price = df_sell.iloc[0][open_col]
                            sell_price = open_price * (1 - 0.0035)
                            position = stock_positions.get(code, {})
                            buy_price = position.get('buy_price', 0)
                            shares = position.get('shares', 0)
                            profit_pct = ((sell_price - buy_price) / buy_price) * 100 if buy_price > 0 else 0
                            profit_amount = (sell_price - buy_price) * shares
                            sell_summary.append({
                                "Code": code,
                                "Name": CODE_TO_NAME.get(code, code),
                                "Buy Date": position.get('buy_date', 'N/A'),
                                "Buy Price": f"{buy_price:,.0f}",
                                "Shares": f"{shares:.2f}",
                                "Sell Date": cycle_end,
                                "Sell Price": f"{sell_price:,.0f}",
                                "Profit %": f"{profit_pct:+.2f}",
                                "Profit Amount": f"{profit_amount:,.0f}",
                                "Reason": "리밸런싱 매도"
                            })
                            total_buy += buy_price * shares
                            total_sell += sell_price * shares
                            # 포트폴리오에서 제거
                            held_stocks.remove(code)
                            if code in stock_positions:
                                del stock_positions[code]
                    except Exception as e:
                        st.warning(f"Error selling {code}: {e}")

                # 수익률 계산 및 포트폴리오 가치 업데이트
                if total_buy > 0:
                    cycle_return = ((total_sell - total_buy) / total_buy) * 100
                    portfolio_value = total_sell
                else:
                    # 매수만 하고 매도가 없는 경우, 현재 보유 종목들의 가치 계산
                    current_portfolio_value = 0
                    for code in held_stocks:
                        try:
                            df = pd.read_csv(os.path.join(DATA_FOLDER, f"{code}_features.csv"))
                            date_col = find_column(df, ['date', 'Date', '날짜'])
                            close_col = find_column(df, ['close', 'Close', '종가'])
                            df[date_col] = pd.to_datetime(df[date_col])
                            
                            # 사이클 마지막 거래일의 종가로 계산
                            last_trading_date = max([d for d in trading_dates if cycle_start <= d < cycle_end])
                            df_last = df[df[date_col] == pd.to_datetime(last_trading_date)]
                            
                            if len(df_last) > 0:
                                current_close = df_last.iloc[0][close_col]
                                position = stock_positions.get(code, {})
                                shares = position.get('shares', 0)
                                current_portfolio_value += current_close * shares
                        except Exception as e:
                            st.warning(f"Error calculating current value for {code}: {e}")
                    
                    portfolio_value = current_portfolio_value
                    cycle_return = 0  # 매도가 없었으므로 수익률 0
                
                equity_curve.append({"Cycle": f"리밸런싱 {i+1}", "Value": portfolio_value})
                cycle_returns.append(cycle_return)

                # 결과 표시 및 저장
                if buy_summary or sell_summary:
                    st.write("**📊 거래 내역**")
                    
                    # 매수/매도 내역을 하나의 표로 통합
                    combined_summary = []
                    
                    # 매수 내역 추가
                    for buy_item in buy_summary:
                        combined_summary.append({
                            "Code": buy_item["Code"],
                            "Name": buy_item["Name"],
                            "Action": "매수",
                            "Date": buy_item["Buy Date"],
                            "Price": buy_item["Buy Price"],
                            "Shares": buy_item["Shares"],
                            "Investment": buy_item["Investment"],
                            "Profit %": "-",
                            "Profit Amount": "-",
                            "Reason": "매수"
                        })
                    
                    # 매도 내역 추가
                    for sell_item in sell_summary:
                        combined_summary.append({
                            "Code": sell_item["Code"],
                            "Name": sell_item["Name"],
                            "Action": "매도",
                            "Date": sell_item["Sell Date"],
                            "Price": sell_item["Sell Price"],
                            "Shares": sell_item["Shares"],
                            "Investment": sell_item["Buy Price"],
                            "Profit %": sell_item["Profit %"],
                            "Profit Amount": sell_item["Profit Amount"],
                            "Reason": sell_item["Reason"]
                        })
                    
                    if combined_summary:
                        combined_df = pd.DataFrame(combined_summary)
                        st.dataframe(combined_df, use_container_width=True)
                st.write(f"**포트폴리오 가치**: {int(portfolio_value):,}원")
                st.write(f"**사이클 수익률**: {cycle_return:+.2f}%")
                cycle_details.append({
                    'cycle': i+1,
                    'start_date': cycle_start,
                    'end_date': cycle_end,
                    'cash_holding': cash_holding,
                    'held_stocks': held_stocks.copy(),
                    'buy_summary': buy_summary,
                    'sell_summary': sell_summary,
                    'cycle_return': cycle_return,
                    'portfolio_value': portfolio_value
                })
            
            # 최종 결과
            st.subheader("📈 최종 성과")
            total_return = ((portfolio_value - initial_value) / initial_value) * 100
            st.write(f"**초기 투자금**: {int(initial_value):,}원")
            st.write(f"**최종 포트폴리오 가치**: {int(portfolio_value):,}원")
            st.write(f"**총 수익률**: {total_return:+.2f}%")
            
            if cycle_returns:
                avg_return = sum(cycle_returns) / len(cycle_returns)
                st.write(f"**평균 사이클 수익률**: {avg_return:+.2f}%")
                st.write(f"**총 리밸런싱 횟수**: {len(evaluation_dates)}회")
            
            # 사이클별 상세 결과
            with st.expander("📋 사이클별 상세 결과"):
                for detail in cycle_details:
                    st.write(f"**사이클 {detail['cycle']} ({detail['start_date']} ~ {detail['end_date']})**:")
                    if detail['cash_holding']:
                        st.write("- 현금보유 (수익률 0%)")
                    else:
                        st.write(f"- 보유 종목: {', '.join([CODE_TO_NAME.get(code, code) for code in detail['held_stocks']])}")
                        st.write(f"- 수익률: {detail['cycle_return']:+.2f}%")
                    st.write(f"- 포트폴리오 가치: {int(detail['portfolio_value']):,}원")
                    
                    # 매수/매도 내역 표시 (통합 표)
                    if detail['buy_summary'] or detail['sell_summary']:
                        st.write("  📊 거래 내역:")
                        
                        # 매수/매도 내역을 하나의 표로 통합
                        combined_summary = []
                        
                        # 매수 내역 추가
                        for buy_item in detail['buy_summary']:
                            combined_summary.append({
                                "Code": buy_item["Code"],
                                "Name": buy_item["Name"],
                                "Action": "매수",
                                "Date": buy_item["Buy Date"],
                                "Price": buy_item["Buy Price"],
                                "Shares": buy_item["Shares"],
                                "Investment": buy_item["Investment"],
                                "Profit %": "-",
                                "Profit Amount": "-",
                                "Reason": "매수"
                            })
                        
                        # 매도 내역 추가
                        for sell_item in detail['sell_summary']:
                            combined_summary.append({
                                "Code": sell_item["Code"],
                                "Name": sell_item["Name"],
                                "Action": "매도",
                                "Date": sell_item["Sell Date"],
                                "Price": sell_item["Sell Price"],
                                "Shares": sell_item["Shares"],
                                "Investment": sell_item["Buy Price"],
                                "Profit %": sell_item["Profit %"],
                                "Profit Amount": sell_item["Profit Amount"],
                                "Reason": sell_item["Reason"]
                            })
                        
                        if combined_summary:
                            combined_df = pd.DataFrame(combined_summary)
                            st.dataframe(combined_df, use_container_width=True)
                    
                    st.write("---")
            
            # ==============================
            # 비교 분석: KODEX 200, 동등비율 투자
            # ==============================

            st.subheader("📊 비교 분석")

            # 1. KODEX 200 단일 투자
            kodex_equity = [initial_value]
            kodex_cycle_returns = []
            kodex_code = "069500"
            for i, rebalancing_date in enumerate(evaluation_dates):
                try:
                    df_kodex = pd.read_csv(os.path.join(DATA_FOLDER, f"{kodex_code}_features.csv"))
                    date_col = find_column(df_kodex, ['date', 'Date', '날짜'])
                    open_col = find_column(df_kodex, ['open', 'Open', '시가'])
                    df_kodex[date_col] = pd.to_datetime(df_kodex[date_col])
                    df_rebal = df_kodex[df_kodex[date_col] == pd.to_datetime(rebalancing_date)]
                    if len(df_rebal) > 0:
                        open_price = df_rebal.iloc[0][open_col]
                        # 매도 시 수수료 적용 (이전 cycle에서 매도)
                        if i > 0:
                            prev_rebal = evaluation_dates[i-1]
                            df_prev = df_kodex[df_kodex[date_col] == pd.to_datetime(prev_rebal)]
                            if len(df_prev) > 0:
                                prev_open = df_prev.iloc[0][open_col]
                                # 매도 시 수수료 적용
                                ret = (open_price * (1-0.0035) - prev_open) / prev_open
                                kodex_equity.append(kodex_equity[-1] * (1 + ret))
                                kodex_cycle_returns.append(ret*100)
                        else:
                            kodex_cycle_returns.append(0.0)
                except Exception as e:
                    st.warning(f"KODEX 200 비교 분석 오류: {e}")
                    kodex_equity.append(kodex_equity[-1])
                    kodex_cycle_returns.append(0.0)
            if len(kodex_equity) < len(equity_curve):
                kodex_equity += [kodex_equity[-1]] * (len(equity_curve)-len(kodex_equity))

            # 2. 동등비율 투자 (매번 선택된 모든 종목)
            equal_equity = [initial_value]
            equal_cycle_returns = []
            for i, rebalancing_date in enumerate(evaluation_dates):
                try:
                    # 매 리밸런싱마다 선택된 종목 전체 (조건 재계산)
                    yesterday = rebalancing_date - dt.timedelta(days=1)
                    equal_stock_condition_counts = []
                    
                    for code in selected_codes:
                        try:
                            df = pd.read_csv(os.path.join(DATA_FOLDER, f"{code}_features.csv"))
                            date_col = find_column(df, ['date', 'Date', '날짜'])
                            df[date_col] = pd.to_datetime(df[date_col])
                            
                            # D-1까지의 데이터로 조건 평가
                            df_until_yesterday = df[df[date_col] <= pd.to_datetime(yesterday)].copy()
                            if len(df_until_yesterday) > 0:
                                # 조건 평가
                                conditions_satisfied = 0
                                required_satisfied = True
                                
                                for cond, req in zip(conditions, required_flags):
                                    try:
                                        # recent_high_Xpct feature들은 실시간 계산
                                        if 'recent_high_8pct' in cond:
                                            # 실시간으로 recent_high_8pct 계산
                                            recent_high_8pct_value = calculate_recent_high_8pct(df, rebalancing_date)
                                            
                                            # 조건 평가 (recent_high_8pct == True 또는 recent_high_8pct == recent_high_8pct)
                                            if 'recent_high_8pct == True' in cond or 'recent_high_8pct == recent_high_8pct' in cond:
                                                condition_satisfied = recent_high_8pct_value
                                            else:
                                                condition_satisfied = not recent_high_8pct_value
                                        elif 'recent_high_5pct' in cond:
                                            # 실시간으로 recent_high_5pct 계산
                                            recent_high_5pct_value = calculate_recent_high_5pct(df, rebalancing_date)
                                            
                                            # 조건 평가
                                            if 'recent_high_5pct == True' in cond or 'recent_high_5pct == recent_high_5pct' in cond:
                                                condition_satisfied = recent_high_5pct_value
                                            else:
                                                condition_satisfied = not recent_high_5pct_value
                                        elif 'recent_high_3pct' in cond:
                                            # 실시간으로 recent_high_3pct 계산
                                            recent_high_3pct_value = calculate_recent_high_3pct(df, rebalancing_date)
                                            
                                            # 조건 평가
                                            if 'recent_high_3pct == True' in cond or 'recent_high_3pct == recent_high_3pct' in cond:
                                                condition_satisfied = recent_high_3pct_value
                                            else:
                                                condition_satisfied = not recent_high_3pct_value
                                            
                                            if req:  # 필수 조건
                                                if not condition_satisfied:
                                                    required_satisfied = False
                                                    break
                                            else:  # 선택 조건
                                                if condition_satisfied:
                                                    conditions_satisfied += 1
                                        else:
                                            # 기존 방식으로 조건 평가
                                            if req:  # 필수 조건
                                                if len(df_until_yesterday.query(cond)) == 0:
                                                    required_satisfied = False
                                                    break
                                            else:  # 선택 조건
                                                if len(df_until_yesterday.query(cond)) > 0:
                                                    conditions_satisfied += 1
                                    except Exception as e:
                                        st.warning(f"Error evaluating condition '{cond}' for {code}: {e}")
                                        if req:
                                            required_satisfied = False
                                            break
                                
                                # 조건을 만족하면 후보에 추가
                                if required_satisfied and conditions_satisfied >= min_satisfied_conditions:
                                    equal_stock_condition_counts.append({
                                        'code': code,
                                        'conditions_satisfied': conditions_satisfied,
                                        'required_satisfied': required_satisfied
                                    })
                        except Exception as e:
                            st.warning(f"Error evaluating {code} for equal weight: {e}")
                    
                    codes_this_cycle = [x['code'] for x in equal_stock_condition_counts]
                    if not codes_this_cycle:
                        equal_cycle_returns.append(0.0)
                        equal_equity.append(equal_equity[-1])
                        continue
                    invest_per_stock = equal_equity[-1] / len(codes_this_cycle)
                    total_value = 0
                    for code in codes_this_cycle:
                        df = pd.read_csv(os.path.join(DATA_FOLDER, f"{code}_features.csv"))
                        date_col = find_column(df, ['date', 'Date', '날짜'])
                        open_col = find_column(df, ['open', 'Open', '시가'])
                        df[date_col] = pd.to_datetime(df[date_col])
                        df_rebal = df[df[date_col] == pd.to_datetime(rebalancing_date)]
                        if len(df_rebal) > 0:
                            open_price = df_rebal.iloc[0][open_col]
                            # 매도 시 수수료 적용 (이전 cycle에서 매도)
                            if i > 0:
                                prev_rebal = evaluation_dates[i-1]
                                df_prev = df[df[date_col] == pd.to_datetime(prev_rebal)]
                                if len(df_prev) > 0:
                                    prev_open = df_prev.iloc[0][open_col]
                                    ret = (open_price * (1-0.0035) - prev_open) / prev_open
                                    total_value += invest_per_stock * (1 + ret)
                            else:
                                total_value += invest_per_stock
                    if i > 0:
                        ret = (total_value - equal_equity[-1]) / equal_equity[-1]
                        equal_cycle_returns.append(ret*100)
                        equal_equity.append(total_value)
                    else:
                        equal_cycle_returns.append(0.0)
                        equal_equity.append(equal_equity[-1])
                except Exception as e:
                    st.warning(f"동등비율 비교 분석 오류: {e}")
                    equal_cycle_returns.append(0.0)
                    equal_equity.append(equal_equity[-1])
            if len(equal_equity) < len(equity_curve):
                equal_equity += [equal_equity[-1]] * (len(equity_curve)-len(equal_equity))

            # 3. 비교 통계 테이블
            import numpy as np

            # 각 전략의 최종 값과 수익률 계산
            my_strategy_final = equity_curve[-1]["Value"] if equity_curve else initial_value
            kodex_final = kodex_equity[-1] if kodex_equity else initial_value
            equal_final = equal_equity[-1] if equal_equity else initial_value

            # Max Drawdown 계산 함수
            def calculate_max_drawdown(equity_values):
                if not equity_values or len(equity_values) < 2:
                    return 0.0
                
                peak = equity_values[0]
                max_drawdown = 0.0
                
                for value in equity_values:
                    if value > peak:
                        peak = value
                    drawdown = (peak - value) / peak * 100
                    if drawdown > max_drawdown:
                        max_drawdown = drawdown
                
                return max_drawdown

            # 각 전략의 Max Drawdown 계산
            my_strategy_values = [item["Value"] for item in equity_curve]
            kodex_max_dd = calculate_max_drawdown(kodex_equity)
            equal_max_dd = calculate_max_drawdown(equal_equity)
            my_strategy_max_dd = calculate_max_drawdown(my_strategy_values)

            # Summary Statistics
            summary = pd.DataFrame({
                'Final Value': [int(my_strategy_final), int(kodex_final), int(equal_final)],
                'Total Return (%)': [((my_strategy_final/initial_value)-1)*100, ((kodex_final/initial_value)-1)*100, ((equal_final/initial_value)-1)*100],
                'Average Cycle Return (%)': [np.mean(cycle_returns) if cycle_returns else 0, np.mean(kodex_cycle_returns) if kodex_cycle_returns else 0, np.mean(equal_cycle_returns) if equal_cycle_returns else 0],
                'Max Drawdown (%)': [my_strategy_max_dd, kodex_max_dd, equal_max_dd]
            }, index=['My Strategy','KODEX 200','Equal Weight'])

            # 수치 포맷팅 적용
            summary['Final Value'] = summary['Final Value'].apply(lambda x: f"{x:,}")
            summary['Total Return (%)'] = summary['Total Return (%)'].round(2)
            summary['Average Cycle Return (%)'] = summary['Average Cycle Return (%)'].round(2)
            summary['Max Drawdown (%)'] = summary['Max Drawdown (%)'].round(2)

            st.write("#### Strategy Summary Statistics")
            st.dataframe(summary)

            # ==============================
            # 내부 디버깅용 분석 로그 (사용자에게는 표시하지 않음)
            # ==============================
            
            # 내부 분석 로그 생성
            debug_log = []
            debug_log.append(f"=== 백테스트 디버깅 로그 ===")
            debug_log.append(f"전략 최종 가치: {int(my_strategy_final):,}원")
            debug_log.append(f"KODEX 200 최종 가치: {int(kodex_final):,}원")
            debug_log.append(f"내 전략 총 수익률: {((my_strategy_final/initial_value)-1)*100:.2f}%")
            debug_log.append(f"KODEX 200 총 수익률: {((kodex_final/initial_value)-1)*100:.2f}%")
            debug_log.append(f"내 전략 최대 손실폭: {my_strategy_max_dd:.2f}%")
            debug_log.append(f"사용된 조건: {', '.join(conditions)}")
            debug_log.append(f"조건 만족 최소 개수: {min_satisfied_conditions}개")
            debug_log.append(f"최대 보유 종목 수: {max_stock_count}개")
            
            # 사이클별 상세 로그
            debug_log.append(f"\n=== 사이클별 상세 결과 ===")
            for i, detail in enumerate(cycle_details):
                debug_log.append(f"사이클 {i+1}: {detail['start_date']} ~ {detail['end_date']}")
                debug_log.append(f"  - 현금보유: {detail['cash_holding']}")
                debug_log.append(f"  - 보유 종목: {detail['held_stocks']}")
                debug_log.append(f"  - 수익률: {detail['cycle_return']:+.2f}%")
                debug_log.append(f"  - 포트폴리오 가치: {int(detail['portfolio_value']):,}원")
                if detail['buy_summary']:
                    debug_log.append(f"  - 매수 내역: {len(detail['buy_summary'])}건")
                if detail['sell_summary']:
                    debug_log.append(f"  - 매도 내역: {len(detail['sell_summary'])}건")
                debug_log.append("")
            
            # 문제점 분석
            debug_log.append(f"=== 문제점 분석 ===")
            if my_strategy_final == 0:
                debug_log.append("⚠️ 포트폴리오 가치가 0원 - 매수 로직 또는 조건 문제")
            if my_strategy_final < kodex_final:
                debug_log.append("📉 내 전략이 KODEX 200을 하회")
            if 'recent_high_8pct' in str(conditions):
                debug_log.append("💡 recent_high_8pct 조건이 너무 엄격할 수 있음")
            
            # 내부 로그 저장 (사용자에게는 표시하지 않음)
            debug_summary = "\n".join(debug_log)
            
            # 디버깅용 expander (접혀있음)
            with st.expander("🔧 내부 디버깅 로그 (개발자용)", expanded=False):
                st.text_area(
                    "디버깅 로그",
                    value=debug_summary,
                    height=300,
                    help="내부 디버깅용 로그입니다"
                )
