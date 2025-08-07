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

def calculate_returns(df, date_col, close_col):
    """상승률을 계산하는 함수"""
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col)
    
    # 3일, 20일, 60일 상승률 계산
    df['return_3d'] = df[close_col].pct_change(3) * 100
    df['return_20d'] = df[close_col].pct_change(20) * 100
    df['return_60d'] = df[close_col].pct_change(60) * 100
    
    return df

def calculate_returns_until_date(df, date_col, close_col, target_date):
    """특정 날짜까지의 데이터만 사용하여 상승률을 계산하는 함수"""
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col)
    
    # target_date까지의 데이터만 사용
    df_filtered = df[df[date_col] <= pd.to_datetime(target_date)].copy()
    
    if len(df_filtered) == 0:
        return df
    
    # 3일, 20일, 60일 상승률 계산
    df_filtered['return_3d'] = df_filtered[close_col].pct_change(3) * 100
    df_filtered['return_20d'] = df_filtered[close_col].pct_change(20) * 100
    df_filtered['return_60d'] = df_filtered[close_col].pct_change(60) * 100
    
    # 원본 데이터프레임에 결과 추가
    result_df = df.copy()
    for col in ['return_3d', 'return_20d', 'return_60d']:
        if col in df_filtered.columns:
            result_df[col] = df_filtered[col]
    
    return result_df

def calculate_relative_momentum(df_stock, df_benchmark, date_col, close_col, periods=[20, 60, 120]):
    """KODEX 200에 대한 상대 모멘텀을 계산하는 함수"""
    df = df_stock.copy()
    df_bm = df_benchmark.copy()
    
    # 날짜 컬럼 찾기
    bm_date_col = find_column(df_bm, ['date', 'Date', '날짜'])
    bm_close_col = find_column(df_bm, ['close', 'Close', '종가'])
    
    df[date_col] = pd.to_datetime(df[date_col])
    df_bm[bm_date_col] = pd.to_datetime(df_bm[bm_date_col])
    
    # 날짜 기준으로 병합
    merged = pd.merge(
        df[[date_col, close_col]], 
        df_bm[[bm_date_col, bm_close_col]].rename(columns={bm_date_col: date_col, bm_close_col: "bm_close"}), 
        on=date_col, 
        how="inner"
    )
    
    # 각 기간별 상대 모멘텀 계산
    for period in periods:
        merged[f"rel_mom_{period}"] = (
            (merged[close_col] / merged[close_col].shift(period)) /
            (merged["bm_close"] / merged["bm_close"].shift(period)) - 1
        ) * 100  # 백분율로 변환
    
    # 원본 데이터프레임에 상대 모멘텀 컬럼 추가 (날짜 기준으로 매핑)
    result_df = df.copy()
    for period in periods:
        # 날짜를 키로 사용하여 매핑
        merged_subset = merged[[date_col, f"rel_mom_{period}"]].set_index(date_col)
        result_df[f"rel_mom_{period}"] = result_df[date_col].map(merged_subset[f"rel_mom_{period}"])
    
    return result_df

def calculate_relative_momentum_until_date(df_stock, df_benchmark, date_col, close_col, target_date, periods=[20, 60, 120]):
    """특정 날짜까지의 데이터만 사용하여 KODEX 200에 대한 상대 모멘텀을 계산하는 함수"""
    df = df_stock.copy()
    df_bm = df_benchmark.copy()
    
    # 날짜 컬럼 찾기
    bm_date_col = find_column(df_bm, ['date', 'Date', '날짜'])
    bm_close_col = find_column(df_bm, ['close', 'Close', '종가'])
    
    df[date_col] = pd.to_datetime(df[date_col])
    df_bm[bm_date_col] = pd.to_datetime(df_bm[bm_date_col])
    
    # target_date까지의 데이터만 사용
    df_filtered = df[df[date_col] <= pd.to_datetime(target_date)].copy()
    df_bm_filtered = df_bm[df_bm[bm_date_col] <= pd.to_datetime(target_date)].copy()
    
    if len(df_filtered) == 0 or len(df_bm_filtered) == 0:
        return df
    
    # 날짜 기준으로 병합
    merged = pd.merge(
        df_filtered[[date_col, close_col]], 
        df_bm_filtered[[bm_date_col, bm_close_col]].rename(columns={bm_date_col: date_col, bm_close_col: "bm_close"}), 
        on=date_col, 
        how="inner"
    )
    
    # 각 기간별 상대 모멘텀 계산
    for period in periods:
        merged[f"rel_mom_{period}"] = (
            (merged[close_col] / merged[close_col].shift(period)) /
            (merged["bm_close"] / merged["bm_close"].shift(period)) - 1
        ) * 100  # 백분율로 변환
    
    # 원본 데이터프레임에 상대 모멘텀 컬럼 추가 (날짜 기준으로 매핑)
    result_df = df.copy()
    for period in periods:
        # 날짜를 키로 사용하여 매핑
        merged_subset = merged[[date_col, f"rel_mom_{period}"]].set_index(date_col)
        result_df[f"rel_mom_{period}"] = result_df[date_col].map(merged_subset[f"rel_mom_{period}"])
    
    return result_df

def calculate_52week_high_low(df, date_col, close_col, high_col, low_col):
    """52주 고점/저점을 계산하는 함수"""
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col)
    
    # 52주(약 252거래일) 고점/저점 계산
    df['high_52w'] = df[high_col].rolling(window=252, min_periods=1).max()
    df['low_52w'] = df[low_col].rolling(window=252, min_periods=1).min()
    
    # 현재가 대비 52주 고점/저점 비율
    df['high_52w_ratio'] = (df[close_col] / df['high_52w']) * 100
    df['low_52w_ratio'] = (df[close_col] / df['low_52w']) * 100
    
    return df

def calculate_52week_high_low_until_date(df, date_col, close_col, high_col, low_col, target_date):
    """특정 날짜까지의 데이터만 사용하여 52주 고점/저점을 계산하는 함수"""
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col)
    
    # target_date까지의 데이터만 사용
    df_filtered = df[df[date_col] <= pd.to_datetime(target_date)].copy()
    
    if len(df_filtered) == 0:
        return df
    
    # 52주(약 252거래일) 고점/저점 계산
    df_filtered['high_52w'] = df_filtered[high_col].rolling(window=252, min_periods=1).max()
    df_filtered['low_52w'] = df_filtered[low_col].rolling(window=252, min_periods=1).min()
    
    # 현재가 대비 52주 고점/저점 비율
    df_filtered['high_52w_ratio'] = (df_filtered[close_col] / df_filtered['high_52w']) * 100
    df_filtered['low_52w_ratio'] = (df_filtered[close_col] / df_filtered['low_52w']) * 100
    
    # 원본 데이터프레임에 결과 추가
    result_df = df.copy()
    for col in ['high_52w', 'low_52w', 'high_52w_ratio', 'low_52w_ratio']:
        if col in df_filtered.columns:
            result_df[col] = df_filtered[col]
    
    return result_df

# 주식 종목 코드와 이름 매핑
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
st.set_page_config(page_title="Daily Trading Log App", layout="wide")
st.title("Daily Trading Log App")

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
    
    # 2023년 7월 3일부터 2025년 6월 30일까지의 거래일 필터링
    start_limit = dt.date(2023, 7, 3)
    end_limit = dt.date(2025, 6, 30)
    filtered_trading_dates = [d for d in trading_dates if start_limit <= d <= end_limit]
    
    if filtered_trading_dates:
        # 연도별, 월별, 일별로 거래일 그룹화
        years = sorted(list(set(d.year for d in filtered_trading_dates)))
        years_str = [str(year) for year in years]
        
        # 시작일과 종료일 선택
        st.subheader("기간 선택")
        st.write("거래일만 선택 가능합니다 (2023년 7월 3일 ~ 2025년 6월 30일)")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**시작일**")
            start_year = st.selectbox("연도", years_str, index=0, key="start_year")
            start_year_dates = [d for d in filtered_trading_dates if d.year == int(start_year)]
            start_months = sorted(list(set(d.month for d in start_year_dates)))
            start_months_str = [f"{month:02d}월" for month in start_months]
            start_month = st.selectbox("월", start_months_str, key="start_month")
            start_month_num = int(start_month.replace("월", ""))
            start_month_dates = [d for d in start_year_dates if d.month == start_month_num]
            start_days = sorted(list(set(d.day for d in start_month_dates)))
            start_days_str = [f"{day:02d}일" for day in start_days]
            start_day = st.selectbox("일", start_days_str, key="start_day")
            start_day_num = int(start_day.replace("일", ""))
            start_date = dt.date(int(start_year), start_month_num, start_day_num)
            
        with col2:
            st.write("**종료일**")
            end_year = st.selectbox("연도", years_str, index=len(years_str)-1, key="end_year")
            end_year_dates = [d for d in filtered_trading_dates if d.year == int(end_year)]
            end_months = sorted(list(set(d.month for d in end_year_dates)))
            end_months_str = [f"{month:02d}월" for month in end_months]
            end_month = st.selectbox("월", end_months_str, index=len(end_months_str)-1, key="end_month")
            end_month_num = int(end_month.replace("월", ""))
            end_month_dates = [d for d in end_year_dates if d.month == end_month_num]
            end_days = sorted(list(set(d.day for d in end_month_dates)))
            end_days_str = [f"{day:02d}일" for day in end_days]
            end_day = st.selectbox("일", end_days_str, index=len(end_days_str)-1, key="end_day")
            end_day_num = int(end_day.replace("일", ""))
            end_date = dt.date(int(end_year), end_month_num, end_day_num)
        
        # 날짜 유효성 검사
        if start_date > end_date:
            st.error("시작일이 종료일보다 늦습니다. 올바른 기간을 선택해주세요.")
        else:
            st.success(f"선택된 기간: {start_date} ~ {end_date}")

            # 거래일 정보 표시
            with st.expander("거래일 정보"):
                st.write(f"**전체 데이터 범위**: {min_date} ~ {max_date}")
                st.write(f"**선택 가능 범위**: {start_limit} ~ {end_limit}")
                st.write(f"**선택 가능한 거래일 수**: {len(filtered_trading_dates)}일")
                st.write(f"**선택된 기간**: {start_date} ~ {end_date}")
                
                # 선택된 기간의 거래일 수 계산
                selected_trading_dates = [d for d in filtered_trading_dates if start_date <= d <= end_date]
                st.write(f"**선택된 기간 거래일 수**: {len(selected_trading_dates)}일")

# ==============================
# 주식 종목 선택 (Opt-out 방식)
# ==============================
st.subheader("주식 종목 선택")

file_paths = sorted(glob(os.path.join(DATA_FOLDER, "*_features.csv")))
stock_codes = [os.path.basename(p).split("_")[0] for p in file_paths]
stock_names = [f"{CODE_TO_NAME.get(code, code)} ({code})" for code in stock_codes]

# 기본값으로 모든 종목 선택
default_selected = stock_names.copy()

# 제외할 종목 선택 (Opt-out)
excluded_stocks = st.multiselect(
    "제외할 종목 선택 (기본값: 모든 종목 선택)", 
    options=stock_names,
    help="선택한 종목들은 거래에서 제외됩니다. 아무것도 선택하지 않으면 모든 종목이 거래 대상입니다."
)

# 최종 선택된 종목 계산
selected_stocks = [name for name in default_selected if name not in excluded_stocks]
selected_codes = [name.split("(")[-1][:-1] for name in selected_stocks]

st.write(f"**거래 대상 종목 수**: {len(selected_codes)}개")
if selected_codes:
    st.write(f"**거래 대상**: {', '.join([CODE_TO_NAME.get(code, code) for code in selected_codes[:5]])}{'...' if len(selected_codes) > 5 else ''}")

# ==============================
# 초기 자금 설정
# ==============================
st.subheader("초기 자금 설정")

initial_capital = st.number_input(
    "초기 투자 자금 (원)", 
    min_value=1000000, 
    max_value=1000000000, 
    value=100000000, 
    step=10000000,
    help="거래를 시작할 초기 자금을 설정합니다."
)

st.write(f"**초기 자금**: {initial_capital:,}원")

# ==============================
# 포트폴리오 관리 설정
# ==============================
st.subheader("포트폴리오 관리 설정")

# 최대 보유 종목 수 설정
max_holdings = st.number_input(
    "최대 보유 종목 수", 
    min_value=1, 
    max_value=10, 
    value=3, 
    step=1,
    help="동시에 보유할 수 있는 최대 종목 수를 설정합니다."
)

# 종목별 최대 투자 비율 설정
max_investment_ratio = st.number_input(
    "종목별 최대 투자 비율 (%)", 
    min_value=10, 
    max_value=100, 
    value=50, 
    step=5,
    help="한 종목에 투자할 수 있는 최대 자금 비율을 설정합니다."
)

st.write(f"**최대 보유 종목 수**: {max_holdings}개")
st.write(f"**종목별 최대 투자 비율**: {max_investment_ratio}%")

# ==============================
# 사용 가능한 Feature 목록
# ==============================
st.subheader("사용 가능한 Feature 목록")

# Feature 카테고리별로 표시
feature_categories = {
    "기본 가격 데이터": ["open", "high", "low", "close", "volume"],
    "이동평균선": ["sma5", "sma10", "sma20", "sma60", "sma120"],
    "지수이동평균선": ["ema12", "ema26"],
    "기술적 지표": ["rsi", "macd", "macd_signal", "macd_histogram", "bb_upper", "bb_middle", "bb_lower", "bb_width", "bb_position"],
    "거래량 지표": ["volume_sma5", "volume_sma20", "volume_ratio"],
    "변동성 지표": ["atr", "volatility"],
    "상승률 지표": ["return_3d", "return_20d", "return_60d"],
    "상대 모멘텀 지표": ["rel_mom_20", "rel_mom_60", "rel_mom_120"],
    "52주 고점/저점 지표": ["high_52w", "low_52w", "high_52w_ratio", "low_52w_ratio"]
}

for category, features in feature_categories.items():
    with st.expander(f"{category}"):
        for feature in features:
            st.write(f"**{feature}**: {feature}")

# ==============================
# Buy 조건 설정
# ==============================
st.subheader("Buy 조건 설정")

st.write("**모든 Buy 조건을 만족하는 종목이 있으면 다음날 시가에 매수합니다.**")

# 52주 고점 모멘텀 전략 예시
with st.expander("52주 고점 모멘텀 전략 예시"):
    st.write("**52주 고점 모멘텀 전략**: 현재가가 52주 고점의 98% 이상일 때 매수하는 전략")
    st.write("**Buy 조건 예시**: `high_52w_ratio >= 98`")
    st.write("**설명**: 52주 고점에 가까운 종목은 강한 상승 모멘텀을 보일 가능성이 높습니다.")
    st.write("**주의**: 이 전략은 고점 근처에서 매수하므로 리스크가 높을 수 있습니다.")

# Buy 조건 입력
buy_conditions = []
num_buy_conditions = st.number_input("Buy 조건 개수", min_value=1, max_value=10, value=1, step=1)

for i in range(num_buy_conditions):
    buy_cond = st.text_input(f"Buy 조건 {i+1}", key=f"buy_cond_{i}", placeholder="Example: rsi < 30")
    if buy_cond.strip():
        buy_conditions.append(buy_cond.strip())

# ==============================
# Sell 조건 설정
# ==============================
st.subheader("Sell 조건 설정")

st.write("**하나라도 Sell 조건을 만족하면 다음날 시가에 매도합니다.**")

# Sell 조건 입력
sell_conditions = []
num_sell_conditions = st.number_input("Sell 조건 개수", min_value=1, max_value=10, value=1, step=1)

for i in range(num_sell_conditions):
    sell_cond = st.text_input(f"Sell 조건 {i+1}", key=f"sell_cond_{i}", placeholder="Example: rsi > 80")
    if sell_cond.strip():
        sell_conditions.append(sell_cond.strip())

# 추가 Sell 조건들
st.write("**추가 Sell 조건**")

# 익절 설정
take_profit_pct = st.number_input(
    "익절 수익률 (%)", 
    min_value=0.0, 
    max_value=100.0, 
    value=10.0, 
    step=0.5,
    help="이 수익률에 도달하면 매도합니다."
)

# 손절 설정
stop_loss_pct = st.number_input(
    "손절 수익률 (%)", 
    min_value=-100.0, 
    max_value=0.0, 
    value=-5.0, 
    step=0.5,
    help="이 손실률에 도달하면 매도합니다."
)

# 최대 보유거래일 설정
max_holding_days = st.number_input(
    "최대 보유거래일", 
    min_value=1, 
    max_value=365, 
    value=30, 
    step=1,
    help="이 일수만큼 보유한 후 매도합니다."
)

# 트레일링 손절 설정
trailing_stop_loss_pct = st.number_input(
    "트레일링 손절 수익률 (%)", 
    min_value=-100.0, 
    max_value=0.0, 
    value=-2.0, 
    step=0.5,
    help="매수 후 최고점 대비 이 손실률에 도달하면 매도합니다."
)

# ==============================
# 분석 실행
# ==============================
st.subheader("분석 실행")

if st.button("Run Daily Trading Log"):
    if not selected_codes or not buy_conditions:
        st.warning("주식 종목과 Buy 조건을 설정해주세요.")
    else:
        st.write("**선택된 종목**:", selected_codes)
        st.write("**Buy 조건**:", buy_conditions)
        if sell_conditions:
            st.write("**Sell 조건**:", sell_conditions)
        else:
            st.write("**Sell 조건**: 없음 (추가 Sell 조건만 사용)")
        
        # 선택된 기간의 거래일만 필터링
        selected_trading_dates = [d for d in filtered_trading_dates if start_date <= d <= end_date]
        st.write(f"**분석 기간**: {len(selected_trading_dates)}일")
        
        # 일일 거래 로그 생성
        st.subheader("일일 거래 로그")
        
        # 초기 설정
        current_capital = initial_capital
        current_portfolio_value = 0
        held_stocks = {}  # {code: {'buy_price': price, 'buy_date': date, 'shares': shares, 'buy_amount': amount, 'highest_price': price}}
        daily_logs = []
        trading_summary = []  # 거래 요약을 위한 리스트
        
        # 수수료 설정
        commission_rate = 0.0035  # 0.35%
        
        # KODEX 200 데이터 로드 (상대 모멘텀 계산용)
        try:
            df_kodex = pd.read_csv(os.path.join(DATA_FOLDER, "069500_features.csv"))
        except Exception as e:
            st.error(f"KODEX 200 데이터 로드 실패: {e}")
            st.stop()
        
        # 진행 상황 표시
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, trading_date in enumerate(selected_trading_dates):
            status_text.text(f"분석 중... {i+1}/{len(selected_trading_dates)}일차 ({trading_date})")
            progress_bar.progress((i + 1) / len(selected_trading_dates))
            
            # 1. 보유 종목들의 Sell 조건 체크 (매도 우선)
            sell_candidates = []
            if held_stocks:
                for code, position in list(held_stocks.items()):
                    try:
                        df = pd.read_csv(os.path.join(DATA_FOLDER, f"{code}_features.csv"))
                        date_col = find_column(df, ['date', 'Date', '날짜'])
                        close_col = find_column(df, ['close', 'Close', '종가'])
                        
                        df[date_col] = pd.to_datetime(df[date_col])
                        
                        # 해당 날짜까지의 데이터만 사용하여 상승률 계산
                        df = calculate_returns_until_date(df, date_col, close_col, trading_date)
                        
                        # 해당 날짜까지의 데이터만 사용하여 상대 모멘텀 계산 (KODEX 200 대비)
                        df = calculate_relative_momentum_until_date(df, df_kodex, date_col, close_col, trading_date)
                        
                        # 해당 날짜까지의 데이터만 사용하여 52주 고점/저점 계산
                        high_col = find_column(df, ['high', 'High', '고가'])
                        low_col = find_column(df, ['low', 'Low', '저가'])
                        if high_col and low_col:
                            df = calculate_52week_high_low_until_date(df, date_col, close_col, high_col, low_col, trading_date)
                        
                        # 해당 날짜의 종가
                        df_today = df[df[date_col] == pd.to_datetime(trading_date)]
                        if len(df_today) > 0:
                            current_close = df_today.iloc[0][close_col]
                            buy_price = position['buy_price']
                            shares = position['shares']
                            buy_amount = position['buy_amount']
                            
                            # 최고가 업데이트
                            if current_close > position['highest_price']:
                                position['highest_price'] = current_close
                            
                            # Sell 조건 체크
                            df_until_today = df[df[date_col] <= pd.to_datetime(trading_date)].copy()
                            if len(df_until_today) > 0:
                                sell_conditions_satisfied = 0
                                sell_required_satisfied = True
                                sell_reason = "Condition"
                                
                                # Sell 조건이 있을 때만 체크
                                if sell_conditions:
                                    for sell_cond in sell_conditions:
                                        try:
                                            if len(df_until_today.query(sell_cond)) > 0:
                                                sell_conditions_satisfied += 1
                                                sell_reason = "Condition"
                                        except Exception as e:
                                            sell_required_satisfied = False
                                            break
                                
                                # 익절 조건 체크
                                current_profit_pct = ((current_close - buy_price) / buy_price) * 100
                                if take_profit_pct > 0 and current_profit_pct >= take_profit_pct:
                                    sell_conditions_satisfied += 1
                                    sell_reason = "Take Profit"
                                
                                # 손절 조건 체크
                                if stop_loss_pct < 0 and current_profit_pct <= stop_loss_pct:
                                    sell_conditions_satisfied += 1
                                    sell_reason = "Stop Loss"
                                
                                # 최대 보유거래일 체크
                                holding_days = (trading_date - position['buy_date']).days
                                if max_holding_days > 0 and holding_days >= max_holding_days:
                                    sell_conditions_satisfied += 1
                                    sell_reason = "Max Holding Days"
                                
                                # 트레일링 손절 조건 체크
                                if trailing_stop_loss_pct < 0:
                                    trailing_loss_pct = ((current_close - position['highest_price']) / position['highest_price']) * 100
                                    if trailing_loss_pct <= trailing_stop_loss_pct:
                                        sell_conditions_satisfied += 1
                                        sell_reason = "Trailing Stop Loss"
                                
                                # Sell 조건 만족 시 매도 후보에 추가 (하나라도 만족하면 매도)
                                # Sell 조건이 없어도 추가 Sell 조건(익절, 손절 등)은 체크
                                if sell_required_satisfied and sell_conditions_satisfied >= 1:
                                    sell_candidates.append((code, sell_reason))
                                    
                    except Exception as e:
                        continue
            
            # 2. Sell 조건 만족 종목 매도
            if sell_candidates:
                # 다음 거래일 찾기
                next_trading_day = None
                for trading_day in selected_trading_dates:
                    if trading_day > trading_date:
                        next_trading_day = trading_day
                        break
                
                if next_trading_day:
                    # 매도 실행 (다음날 시가)
                    total_sell_amount = 0
                    for code, sell_reason in sell_candidates:
                        try:
                            df = pd.read_csv(os.path.join(DATA_FOLDER, f"{code}_features.csv"))
                            date_col = find_column(df, ['date', 'Date', '날짜'])
                            close_col = find_column(df, ['close', 'Close', '종가'])
                            open_col = find_column(df, ['open', 'Open', '시가'])
                            
                            df[date_col] = pd.to_datetime(df[date_col])
                            
                            # 해당 날짜까지의 데이터만 사용하여 상승률 계산
                            df = calculate_returns_until_date(df, date_col, close_col, trading_date)
                            
                            # 해당 날짜까지의 데이터만 사용하여 상대 모멘텀 계산 (KODEX 200 대비)
                            df = calculate_relative_momentum_until_date(df, df_kodex, date_col, close_col, trading_date)
                            
                            # 해당 날짜까지의 데이터만 사용하여 52주 고점/저점 계산
                            high_col = find_column(df, ['high', 'High', '고가'])
                            low_col = find_column(df, ['low', 'Low', '저가'])
                            if high_col and low_col:
                                df = calculate_52week_high_low_until_date(df, date_col, close_col, high_col, low_col, trading_date)
                            
                            # 다음날 시가로 매도
                            df_next = df[df[date_col] == pd.to_datetime(next_trading_day)]
                            if len(df_next) > 0:
                                open_price = df_next.iloc[0][open_col]
                                position = held_stocks[code]
                                shares = position['shares']
                                buy_price = position['buy_price']
                                buy_amount = position['buy_amount']
                                
                                sell_price = open_price * (1 - commission_rate)  # 수수료 적용
                                sell_amount = sell_price * shares
                                profit_amount = sell_amount - buy_amount
                                profit_pct = ((sell_price - buy_price) / buy_price) * 100
                                
                                # 거래 요약에 추가
                                trading_summary.append({
                                    'date': next_trading_day,
                                    'action': 'SELL',
                                    'code': code,
                                    'name': CODE_TO_NAME.get(code, code),
                                    'price': sell_price,
                                    'shares': shares,
                                    'amount': sell_amount,
                                    'profit_amount': profit_amount,
                                    'profit_pct': profit_pct,
                                    'sell_reason': sell_reason,
                                    'cash_before': current_capital,
                                    'cash_after': current_capital + sell_amount
                                })
                                
                                total_sell_amount += sell_amount
                                
                                # 보유 종목에서 제거
                                del held_stocks[code]
                                
                        except Exception as e:
                            continue
                    
                    # 매도 후 자금 추가
                    current_capital += total_sell_amount
            
            # 3. 보유 종목이 최대 보유 종목 수보다 적으면 Buy 조건 체크
            if len(held_stocks) < max_holdings:
                # Buy 조건을 만족하는 종목 찾기
                buy_candidates = []
                
                for code in selected_codes:
                    try:
                        df = pd.read_csv(os.path.join(DATA_FOLDER, f"{code}_features.csv"))
                        date_col = find_column(df, ['date', 'Date', '날짜'])
                        close_col = find_column(df, ['close', 'Close', '종가'])
                        
                        df[date_col] = pd.to_datetime(df[date_col])
                        
                        # 해당 날짜까지의 데이터만 사용하여 상승률 계산
                        df = calculate_returns_until_date(df, date_col, close_col, trading_date)
                        
                        # 해당 날짜까지의 데이터만 사용하여 상대 모멘텀 계산 (KODEX 200 대비)
                        df = calculate_relative_momentum_until_date(df, df_kodex, date_col, close_col, trading_date)
                        
                        # 해당 날짜까지의 데이터만 사용하여 52주 고점/저점 계산
                        high_col = find_column(df, ['high', 'High', '고가'])
                        low_col = find_column(df, ['low', 'Low', '저가'])
                        if high_col and low_col:
                            df = calculate_52week_high_low_until_date(df, date_col, close_col, high_col, low_col, trading_date)
                        
                        # 해당 날짜까지의 데이터로 조건 평가
                        df_until_today = df[df[date_col] <= pd.to_datetime(trading_date)].copy()
                        if len(df_until_today) > 0:
                            # 디버깅: 상대 모멘텀 값 확인 (처음 몇 개 종목만)
                            if len(buy_candidates) == 0 and code in ['005930', '000660']:
                                current_data = df_until_today[df_until_today[date_col] == pd.to_datetime(trading_date)]
                                if len(current_data) > 0 and 'rel_mom_20' in current_data.columns:
                                    rel_mom_value = current_data.iloc[0]['rel_mom_20']
                                    if not pd.isna(rel_mom_value):
                                        st.write(f"**디버깅**: {code} 종목의 rel_mom_20 = {rel_mom_value:.2f}")
                                    else:
                                        st.write(f"**디버깅**: {code} 종목의 rel_mom_20 = NaN")
                                else:
                                    st.write(f"**디버깅**: {code} 종목에 rel_mom_20 컬럼이 없습니다.")
                            
                            # Buy 조건 평가
                            buy_conditions_satisfied = 0
                            buy_required_satisfied = True
                            
                            for buy_cond in buy_conditions:
                                try:
                                    if len(df_until_today.query(buy_cond)) > 0:
                                        buy_conditions_satisfied += 1
                                except Exception as e:
                                    buy_required_satisfied = False
                                    break
                            
                            # Sell 조건 평가 (Sell 조건을 만족하면 매수하지 않음)
                            sell_conditions_satisfied = 0
                            sell_required_satisfied = True
                            
                            # Sell 조건이 있을 때만 체크
                            if sell_conditions:
                                for sell_cond in sell_conditions:
                                    try:
                                        if len(df_until_today.query(sell_cond)) > 0:
                                            sell_conditions_satisfied += 1
                                    except Exception as e:
                                        sell_required_satisfied = False
                                        break
                            
                            # 디버깅: Buy 조건은 만족하지만 Sell 조건 때문에 매수하지 않는 경우
                            if (buy_required_satisfied and buy_conditions_satisfied >= len(buy_conditions) and 
                                sell_required_satisfied and sell_conditions_satisfied > 0):
                                if code in ['005930', '000660']:  # 특정 종목만 디버깅
                                    st.write(f"**디버깅**: {code} 종목이 Buy 조건은 만족하지만 Sell 조건 때문에 매수하지 않습니다.")
                                    st.write(f"  - Buy 조건 만족 수: {buy_conditions_satisfied}/{len(buy_conditions)}")
                                    st.write(f"  - Sell 조건 만족 수: {sell_conditions_satisfied}")
                                    # 현재 날짜의 rel_mom_20 값 확인
                                    current_data = df_until_today[df_until_today[date_col] == pd.to_datetime(trading_date)]
                                    if len(current_data) > 0 and 'rel_mom_20' in current_data.columns:
                                        rel_mom_value = current_data.iloc[0]['rel_mom_20']
                                        st.write(f"  - rel_mom_20 값: {rel_mom_value}")
                            
                            # Buy 조건은 모두 만족하고, Sell 조건은 하나도 만족하지 않을 때만 매수
                            # Sell 조건이 없으면 sell_conditions_satisfied는 0이므로 매수 가능
                            if (buy_required_satisfied and buy_conditions_satisfied >= len(buy_conditions) and 
                                sell_required_satisfied and sell_conditions_satisfied == 0):
                                buy_candidates.append(code)
                                
                                # 디버깅: 조건 만족 시 로그 출력
                                if len(buy_candidates) <= 3:  # 처음 3개만 출력
                                    st.write(f"**디버깅**: {code} 종목이 Buy 조건을 만족했습니다.")
                                    st.write(f"  - Buy 조건 만족 수: {buy_conditions_satisfied}/{len(buy_conditions)}")
                                    st.write(f"  - Sell 조건 만족 수: {sell_conditions_satisfied}")
                                    # 현재 날짜의 rel_mom_20 값 확인
                                    current_data = df_until_today[df_until_today[date_col] == pd.to_datetime(trading_date)]
                                    if len(current_data) > 0 and 'rel_mom_20' in current_data.columns:
                                        rel_mom_value = current_data.iloc[0]['rel_mom_20']
                                        st.write(f"  - rel_mom_20 값: {rel_mom_value}")
                                
                    except Exception as e:
                        continue
                
                # Buy 조건 만족 종목이 있으면 다음날 매수
                if buy_candidates:
                    # 다음 거래일 찾기
                    next_trading_day = None
                    for trading_day in selected_trading_dates:
                        if trading_day > trading_date:
                            next_trading_day = trading_day
                            break
                    
                    if next_trading_day:
                        # 매수 실행 (다음날 시가)
                        for code in buy_candidates:
                            try:
                                df = pd.read_csv(os.path.join(DATA_FOLDER, f"{code}_features.csv"))
                                date_col = find_column(df, ['date', 'Date', '날짜'])
                                close_col = find_column(df, ['close', 'Close', '종가'])
                                open_col = find_column(df, ['open', 'Open', '시가'])
                                
                                df[date_col] = pd.to_datetime(df[date_col])
                                
                                # 해당 날짜까지의 데이터만 사용하여 상승률 계산
                                df = calculate_returns_until_date(df, date_col, close_col, trading_date)
                                
                                # 해당 날짜까지의 데이터만 사용하여 상대 모멘텀 계산 (KODEX 200 대비)
                                df = calculate_relative_momentum_until_date(df, df_kodex, date_col, close_col, trading_date)
                                
                                # 해당 날짜까지의 데이터만 사용하여 52주 고점/저점 계산
                                high_col = find_column(df, ['high', 'High', '고가'])
                                low_col = find_column(df, ['low', 'Low', '저가'])
                                if high_col and low_col:
                                    df = calculate_52week_high_low_until_date(df, date_col, close_col, high_col, low_col, trading_date)
                                
                                # 다음날 시가로 매수
                                df_next = df[df[date_col] == pd.to_datetime(next_trading_day)]
                                if len(df_next) > 0:
                                    open_price = df_next.iloc[0][open_col]
                                    # 종목별 최대 투자 비율 적용
                                    max_buy_amount = current_capital * (max_investment_ratio / 100)
                                    buy_amount = min(current_capital / len(buy_candidates), max_buy_amount)
                                    shares = buy_amount / open_price if open_price > 0 else 0
                                    
                                    if shares > 0:
                                        held_stocks[code] = {
                                            'buy_price': open_price,
                                            'buy_date': next_trading_day,
                                            'shares': shares,
                                            'buy_amount': buy_amount,
                                            'highest_price': open_price
                                        }
                                        
                                        # 거래 요약에 추가
                                        trading_summary.append({
                                            'date': next_trading_day,
                                            'action': 'BUY',
                                            'code': code,
                                            'name': CODE_TO_NAME.get(code, code),
                                            'price': open_price,
                                            'shares': shares,
                                            'amount': buy_amount,
                                            'cash_before': current_capital,
                                            'cash_after': current_capital - buy_amount
                                        })
                            except Exception as e:
                                continue
                        
                        # 매수 후 자금 차감
                        if buy_candidates:
                            # 실제 투자된 금액만 차감
                            total_invested = sum([
                                held_stocks[code]['buy_amount'] 
                                for code in buy_candidates 
                                if code in held_stocks
                            ])
                            current_capital -= total_invested
            
            # 4. 보유 종목들의 현재 가치 계산
            current_portfolio_value = 0
            if held_stocks:
                for code, position in held_stocks.items():
                    try:
                        df = pd.read_csv(os.path.join(DATA_FOLDER, f"{code}_features.csv"))
                        date_col = find_column(df, ['date', 'Date', '날짜'])
                        close_col = find_column(df, ['close', 'Close', '종가'])
                        
                        df[date_col] = pd.to_datetime(df[date_col])
                        
                        # 해당 날짜까지의 데이터만 사용하여 상승률 계산
                        df = calculate_returns_until_date(df, date_col, close_col, trading_date)
                        
                        # 해당 날짜까지의 데이터만 사용하여 상대 모멘텀 계산 (KODEX 200 대비)
                        df = calculate_relative_momentum_until_date(df, df_kodex, date_col, close_col, trading_date)
                        
                        # 해당 날짜까지의 데이터만 사용하여 52주 고점/저점 계산
                        high_col = find_column(df, ['high', 'High', '고가'])
                        low_col = find_column(df, ['low', 'Low', '저가'])
                        if high_col and low_col:
                            df = calculate_52week_high_low_until_date(df, date_col, close_col, high_col, low_col, trading_date)
                        
                        # 해당 날짜의 종가
                        df_today = df[df[date_col] == pd.to_datetime(trading_date)]
                        if len(df_today) > 0:
                            current_close = df_today.iloc[0][close_col]
                            buy_price = position['buy_price']
                            shares = position['shares']
                            buy_amount = position['buy_amount']
                            
                            current_value = current_close * shares
                            current_portfolio_value += current_value
                            
                            # 최고가 업데이트
                            if current_close > position['highest_price']:
                                position['highest_price'] = current_close
                                
                    except Exception as e:
                        continue
                    else:
                        # 다음 거래일이 없어 매도할 수 없음
                        pass
                else:
                    # Sell 조건 만족 종목 없음
                    pass
            
            total_portfolio_value = current_capital + current_portfolio_value
            
            # 4. 일일 로그 저장
            daily_log = {
                'date': trading_date,
                'day': i+1,
                'cash': current_capital,
                'portfolio_value': total_portfolio_value,
                'held_stocks_count': len(held_stocks),
                'held_stocks': list(held_stocks.keys())
            }
            daily_logs.append(daily_log)
        
        # 진행 상황 완료
        progress_bar.empty()
        status_text.empty()
        
        # 거래 로그 표시
        if trading_summary:
            st.subheader("거래 로그")
            
            # 거래 요약을 DataFrame으로 변환
            df_trading = pd.DataFrame(trading_summary)
            
            # 거래 로그 표시
            st.dataframe(
                df_trading[['date', 'action', 'name', 'price', 'shares', 'amount', 'profit_pct', 'sell_reason']].round(2),
                use_container_width=True
            )
            
            # 상세 거래 정보 (expander)
            with st.expander("상세 거래 정보"):
                for trade in trading_summary:
                    st.write(f"**{trade['date']} - {trade['action']}**: {trade['name']}")
                    st.write(f"  - 가격: {trade['price']:,.0f}원")
                    st.write(f"  - 수량: {trade['shares']:.2f}주")
                    st.write(f"  - 거래금액: {trade['amount']:,.0f}원")
                    if 'profit_pct' in trade:
                        st.write(f"  - 수익률: {trade['profit_pct']:+.2f}%")
                    if 'sell_reason' in trade:
                        st.write(f"  - 매도 사유: {trade['sell_reason']}")
                    st.write(f"  - 거래 전 현금: {trade['cash_before']:,.0f}원")
                    st.write(f"  - 거래 후 현금: {trade['cash_after']:,.0f}원")
                    st.write("")
        else:
            st.info("분석 기간 동안 거래가 발생하지 않았습니다.")
        
        # 최종 결과
        st.subheader("최종 성과")
        final_value = daily_logs[-1]['portfolio_value'] if daily_logs else initial_capital
        total_return = ((final_value - initial_capital) / initial_capital) * 100
        
        st.write(f"**초기 투자금**: {initial_capital:,}원")
        st.write(f"**최종 포트폴리오 가치**: {final_value:,.0f}원")
        st.write(f"**총 수익률**: {total_return:+.2f}%")
        st.write(f"**분석 기간**: {len(selected_trading_dates)}일")
        
        # 일일 로그 요약
        with st.expander("일일 포트폴리오 현황"):
            df_daily = pd.DataFrame(daily_logs)
            df_daily['date'] = pd.to_datetime(df_daily['date'])
            df_daily = df_daily.sort_values('date')
            
            # 보유 종목 정보 추가
            df_daily['held_stocks_names'] = df_daily['held_stocks'].apply(
                lambda x: ', '.join([CODE_TO_NAME.get(code, code) for code in x]) if x else '없음'
            )
            
            st.dataframe(
                df_daily[['date', 'cash', 'portfolio_value', 'held_stocks_count', 'held_stocks_names']].round(0),
                use_container_width=True

            )
