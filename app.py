import streamlit as st
import pandas as pd
import datetime
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
import koreanize_matplotlib

st.title("🚍 DRT 수요 예측 및 하차 히트맵 시각화")

route_options = {
    '25번': {
        'demand_file': "C:\\Users\\panda\\Documents\\졸작\\result\\bus_25(10-16).xlsx",
        'dropoff_file': "C:\\Users\\panda\\Documents\\졸작\\result\\25번_정류장_승하차\\승하차정류장_ID.csv"
    },
    '23번': {
        'demand_file': "C:\\Users\\panda\\Documents\\졸작\\result\\bus_23(10-16).xlsx",
        'dropoff_file': "C:\\Users\\panda\\Documents\\졸작\\result\\23번_정류장_승하차\\승하차정류장_ID.csv"
    }
}

selected_route = st.selectbox("버스 노선을 선택하세요", list(route_options.keys()))
file_paths = route_options[selected_route]

target_date = st.date_input("예측할 날짜를 선택하세요", value=datetime.date(2024, 3, 4))
target_date_str = target_date.strftime("%Y-%m-%d")

시간대들 = ['10', '11', '12', '13', '14', '15', '16']
승차컬럼 = [f"{h}(승차)" for h in 시간대들]
하차컬럼 = [f"{h}(하차)" for h in 시간대들]


@st.cache_data
def load_demand_data(path: str) -> pd.DataFrame:
    return pd.read_excel(path)[['정류장_ID', '일'] + 시간대들]

@st.cache_data
def load_dropoff_data(path: str) -> pd.DataFrame:
    return pd.read_csv(path)

df_demand = load_demand_data(file_paths['demand_file'])
df_dropoff = load_dropoff_data(file_paths['dropoff_file'])


def generate_prediction_local(df, target_date):
    df['월'] = pd.to_datetime(df['일']).dt.month
    train_df = df[df['월'].between(3, 10)]

    stats = (
        train_df
        .groupby('정류장_ID')[시간대들]
        .agg(['mean', 'std'])
    )
    stats.columns = [f'{col}_{stat}' for col, stat in stats.columns]
    stats = stats.reset_index()

    date_str = pd.to_datetime(target_date).strftime('%Y-%m-%d')
    test_df = df[df['일'] == date_str].copy()
    if test_df.empty:
        st.warning(f"[경고] 일자 '{date_str}'에 해당하는 데이터가 없습니다.")
        return pd.DataFrame()

    np.random.seed(hash(target_date) % (2**32))  

    결과 = []
    for _, row in test_df.iterrows():
        정류장 = row['정류장_ID']
        통계행 = stats[stats['정류장_ID'] == 정류장]
        if 통계행.empty:
            continue
        예측 = {'정류장_ID': 정류장, '일': date_str}
        for 시간 in 시간대들:
            λ = 통계행[f'{시간}_mean'].values[0]
            λ = max(λ, 1e-6)
            예측[f'{시간}(승차)'] = int(np.random.poisson(λ))
        결과.append(예측)

    return pd.DataFrame(결과)

predicted = generate_prediction_local(df_demand, target_date)

st.subheader("📈 수요 분포 추정값값")
if not predicted.empty:
    st.dataframe(predicted)
    sum_by_hour = predicted[승차컬럼].sum()
    st.bar_chart(sum_by_hour)
else:
    st.warning("선택한 날짜에 데이터가 없습니다.")


st.subheader("📍 하차 히트맵")

raw_df = df_dropoff[['정류장_ID'] + 하차컬럼].set_index('정류장_ID')
norm = df_dropoff.set_index('정류장_ID')['통과노선수']
heatmap_df = raw_df.div(norm, axis=0).fillna(0)

fig, ax = plt.subplots(figsize=(12, len(heatmap_df) * 0.4))
sns.heatmap(heatmap_df, annot=True, fmt=".2f", cmap="YlOrRd", ax=ax)
st.pyplot(fig)

import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

def plot_tradeoff_curve():
    # X축 비율: 거리 0 ↔ 대기시간 1
    x = np.linspace(0, 1, 100)

    # 지수적으로 증가하는 비용 함수
    cost_from_distance = 10000 + 8000 * np.exp(4 * (x - 1))  # 거리 기반
    cost_from_wait = 10000 + 8000 * np.exp(-4 * x)           # 대기시간 기반

    # 교차점 계산
    mid_index = np.argmin(np.abs(cost_from_distance - cost_from_wait))
    opt_x = x[mid_index]
    opt_cost = cost_from_distance[mid_index]

    # 그래프 그리기
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(x, cost_from_distance, label="거리 vs 비용", color='blue')
    ax.plot(x, cost_from_wait, label="대기시간 vs 비용", color='orange')
    ax.plot(opt_x, opt_cost, 'ro', label="최적 Trade-off 점")

    ax.set_xlabel("비중 (거리: 0 → 대기시간: 1)", fontsize=12)
    ax.set_ylabel("예상 비용 (원)", fontsize=12)
    ax.set_title("거리 기반과 대기시간 기반 비용 곡선의 교차", fontsize=14)
    ax.grid(True)
    ax.legend()
    st.pyplot(fig)

# Streamlit 실행
st.header("🚍 거리 vs 대기시간 Trade-off 시각화")
st.write("두 목적이 교차하는 지점을 통해 최적 균형점을 시각적으로 이해할 수 있습니다.")
plot_tradeoff_curve()
