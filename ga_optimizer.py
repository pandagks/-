import random
from utils import get_distance_between

# 각 고객의 (pickup, dropoff) 정류장 정보를 받아 유효한 순열 생성
def generate_valid_sequence(pairs):
    seen = set()
    pickups = []
    for p, _ in pairs:
        if p not in seen:
            pickups.append(p)
            seen.add(p)
    dropoffs = []
    for _, d in pairs:
        if d not in seen:
            dropoffs.append(d)
            seen.add(d)
    sequence = pickups.copy()
    remaining = dropoffs.copy()
    random.shuffle(remaining)
    for drop in remaining:
        idx = random.randint(0, len(sequence))
        while sequence.index([p for p, d in pairs if d == drop][0]) >= idx:
            idx += 1
        sequence.insert(idx, drop)
    return sequence

# 거리 총합 계산
def evaluate_sequence(seq):
    from collections import Counter
    seen = set()
    unique_seq = []
    for stop in seq:
        if stop not in seen:
            unique_seq.append(stop)
            seen.add(stop)
    seq = unique_seq
    from collections import Counter
    counts = Counter(seq)
    dupes = {k: v for k, v in counts.items() if v > 1}
    if dupes:
        print("[경고] 중복 정류장 있음:", dupes)
    total = 0
    for i in range(len(seq) - 1):
        dist = get_distance_between(seq[i], seq[i+1])
        total += dist if dist else 0
    return total

# 초기 population 생성
def initialize_population(pairs, size=50):
    return [generate_valid_sequence(pairs) for _ in range(size)]

# 유전자 교차 (간단한 순서 기반 교차)
def crossover(parent1, parent2):
    cut = random.randint(1, len(parent1) - 2)
    head = parent1[:cut]
    tail = [x for x in parent2 if x not in head]
    return head + tail

# 돌연변이 (드롭 위치 교체)
def mutate(seq, pickup_set):
    idx1, idx2 = random.sample(range(len(seq)), 2)
    if seq[idx1] not in pickup_set and seq[idx2] not in pickup_set:
        seq[idx1], seq[idx2] = seq[idx2], seq[idx1]
    return seq

# 메인 GA 실행
total_distance_across_runs = 0
total_time_across_runs = 0

def run_ga(pairs, generations=100, pop_size=50):
    global total_distance_across_runs, total_time_across_runs
    print("[GA] 입력된 정류장 쌍 (승차 → 하차):")
    print("  순서대로 정류장 조합:")
    print("  " + " | ".join(f"({p}→{d})" for p, d in pairs))
    for i, (p, d) in enumerate(pairs):
        print(f"  고객 {i+1}: 승차={p}, 하차={d}")
    population = initialize_population(pairs, pop_size)
    pickup_set = set([p for p, _ in pairs])

    for gen in range(generations):
        scored = [(evaluate_sequence(ind), ind) for ind in population]
        scored.sort(key=lambda x: x[0])
        next_gen = [scored[0][1]]  # elitism

        while len(next_gen) < pop_size:
            p1, p2 = random.sample(scored[:20], 2)
            child = crossover(p1[1], p2[1])
            child = mutate(child, pickup_set)
            next_gen.append(child)

        population = next_gen

    best = min(population, key=evaluate_sequence)
    # 중복 제거 후 순서 유지
    best = [s for i, s in enumerate(best) if s not in best[:i]]
    print("[GA] 최적 경로 순서 및 구간별 거리/시간:")
    total_distance = 0
    total_minutes = 0
    for i in range(len(best) - 1):
        dist = get_distance_between(best[i], best[i+1])
        if dist and dist > 0:
            minutes = int(dist * 3)
            total_distance += dist
            total_minutes += minutes
            print(f"  {best[i]} -> {best[i+1]} : {dist:.2f} km / {minutes}분")

    # 차고지 복귀 거리 추가 (마지막 정류장에서 오이도차고지까지)
    last_stop = best[-1]
    return_to_depot = get_distance_between(last_stop, "00_오이도차고지")
    if return_to_depot:
        minutes_back = int(return_to_depot * 3)
        print(f"  {last_stop} -> 00_오이도차고지 : {return_to_depot:.2f} km / {minutes_back}분 (복귀)")
        total_distance += return_to_depot
        total_minutes += minutes_back
    print(f"[GA] 총 이동 거리: {total_distance:.2f} km")
    print(f"[GA] 총 예상 소요 시간: {total_minutes}분")
    print(f"[GA] 해당 시간대 수요를 만족하기 위한 경로의 총 이동 거리: {total_distance:.2f} km")
    total_distance_across_runs += total_distance
    total_time_across_runs += total_minutes
    # 최종 반환 전 중복 제거 및 정류장 연결 유효성 확인
    final_path = []
    seen = set()
    for stop in best:
        if stop not in seen:
            final_path.append(stop)
            seen.add(stop)
    print(f"[GA] 최종 반환 경로 (중복 제거됨): {final_path}")
    print(f"[GA 누적] 전체 시간대 총 이동 거리 합: {total_distance_across_runs:.2f} km")
    print(f"[GA 누적] 전체 시간대 총 소요 시간 합: {total_time_across_runs}분")
    return final_path
