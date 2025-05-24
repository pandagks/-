import random
from statistics import mean, stdev
from utils import get_distance_between

# ---------------------------
# Helper Functions
# ---------------------------
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

def evaluate_sequence(seq):
    seen = set()
    unique_seq = []
    for stop in seq:
        if stop not in seen:
            unique_seq.append(stop)
            seen.add(stop)
    seq = unique_seq
    total = 0
    for i in range(len(seq) - 1):
        dist = get_distance_between(seq[i], seq[i+1])
        total += dist if dist else 0
    return total

def initialize_population(pairs, size=50):
    return [generate_valid_sequence(pairs) for _ in range(size)]

def crossover(parent1, parent2):
    if len(parent1) < 3:
        return parent1[:]  # 너무 짧으면 복사만
    cut = random.randint(1, len(parent1) - 2)
    head = parent1[:cut]
    tail = [x for x in parent2 if x not in head]
    return head + tail


def mutate(seq, pickup_set):
    idx1, idx2 = random.sample(range(len(seq)), 2)
    if seq[idx1] not in pickup_set and seq[idx2] not in pickup_set:
        seq[idx1], seq[idx2] = seq[idx2], seq[idx1]
    return seq

# ---------------------------
# Main GA Function
# ---------------------------
total_distance_across_runs = 0
total_time_across_runs = 0

def run_ga(pairs, generations=100, pop_size=50, verbose=True, plot=False):
    global total_distance_across_runs, total_time_across_runs

    population = initialize_population(pairs, pop_size)
    pickup_set = set([p for p, _ in pairs])
    fitness_history = []
    fitness_with_return = []

    for gen in range(generations):
        scored = [(evaluate_sequence(ind), ind) for ind in population]
        scored.sort(key=lambda x: x[0])
        best_score, best_seq = scored[0]

        # 복귀 거리 포함한 총 거리
        return_dist = get_distance_between(best_seq[-1], "00_오이도차고지") or 0
        fitness_with_return = [evaluate_sequence(path) + get_distance_between(path[-1], "00_오이도차고지") for path in population]

        fitness_history.append(best_score)

        next_gen = [best_seq]  # elitism
        while len(next_gen) < pop_size:
            p1, p2 = random.sample(scored[:20], 2)
            child = crossover(p1[1], p2[1])
            child = mutate(child, pickup_set)
            next_gen.append(child)

        population = next_gen

    best = min(population, key=evaluate_sequence)
    best = [s for i, s in enumerate(best) if s not in best[:i]]

    total_distance = 0
    total_minutes = 0
    for i in range(len(best) - 1):
        dist = get_distance_between(best[i], best[i+1])
        if dist and dist > 0:
            minutes = int(dist * 3)
            total_distance += dist
            total_minutes += minutes
            if verbose:
                print(f"  {best[i]} -> {best[i+1]} : {dist:.2f} km / {minutes}분")

    last_stop = best[-1]
    return_to_depot = get_distance_between(last_stop, "00_오이도차고지")
    if return_to_depot:
        minutes_back = int(return_to_depot * 3)
        if verbose:
            print(f"  {last_stop} -> 00_오이도차고지 : {return_to_depot:.2f} km / {minutes_back}분 (복귀)")
        total_distance += return_to_depot
        total_minutes += minutes_back

    total_distance_across_runs += total_distance
    total_time_across_runs += total_minutes

    if verbose:
        print(f"[GA] 총 이동 거리: {total_distance:.2f} km")
        print(f"[GA] 총 예상 소요 시간: {total_minutes}분")
        print(f"[GA 누적] 전체 시간대 총 이동 거리 합: {total_distance_across_runs:.2f} km")
        print(f"[GA 누적] 전체 시간대 총 소요 시간 합: {total_time_across_runs}분")
        print("[GA] 세대별 최적 거리 통계 (복귀 포함):")
        print(f"  평균: {mean(fitness_with_return):.2f} km")
        print(f"  표준편차: {stdev(fitness_with_return) if len(fitness_with_return) > 1 else 0:.2f} km")
        print(f"  초기: {fitness_with_return[0]:.2f} km → 최종: {fitness_with_return[-1]:.2f} km")
        print("[GA 최종 요약]")
        print(f"총 누적 거리: {total_distance_across_runs:.2f} km")
        print(f"총 누적 시간: {total_time_across_runs}분")

    return best, fitness_with_return, total_distance, total_minutes
