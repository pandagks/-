from parameters import load_fixed_customers
from customer import Customer
from utils import get_distance_between, calculate_cost
from bus import Bus
from ga_optimizer import run_ga
from statistics import mean, stdev
import heapq

class Simulation:
    def __init__(self):
        self.customers = []                      # 전체 고객 리스트
        self.buses = []                          # 버스 객체 리스트
        self.waiting_customers = {}              # 정류장별 대기 중인 고객 딕셔너리
        self.current_time = 600                  # 시뮬레이션 시간 (분 단위, 10:00시작)
        self.bus_counter = 1                     # 버스 번호 부여용 카운터
        self.total_distance_across_runs = 0      # 누적 이동 거리
        self.total_time_across_runs = 0          # 누적 이동 시간
        self.fitness_all = []                    # GA 성능 기록 리스트
        self.abandoned_customers = 0             # 대기시간 초과로 포기한 고객 수

    def generate_customers(self):
        fixed_customers = load_fixed_customers()  # 파라미터에서 고정 고객 생성
        for customer in fixed_customers:
            if customer.boarding_stop != customer.getoff_stop:  # 승하차 정류장이 같지 않은 경우만
                self.customers.append(customer)
                self.waiting_customers.setdefault(customer.boarding_stop, []).append(customer)

    def run(self):
        self.generate_customers()  # 고객 생성
        self.buses.append(Bus(bus_id="Bus1", current_stop="00_오이도차고지", max_capacity=15))  # 버스 초기화

        for hour in range(10, 17):  # 10시 ~ 16시까지 반복
            hour_min = hour * 60
            hourly_customers = [c for c in self.customers if hour_min <= c.time < hour_min + 60]
            hourly_ids = {c.customer_id for c in hourly_customers}
            remaining_customers = hourly_customers.copy()
            #GA 최적화 준비 및 실행
            pairs = [(c.boarding_stop, c.getoff_stop) for c in hourly_customers]
            if not pairs:
                continue
            stops_to_visit, fitness_with_return, distance, minutes = run_ga(pairs, verbose=True)
            # 탑승/하차 인원 계산
            boarding_count = {}
            getoff_count = {}

            for c in hourly_customers:
                boarding_count[c.boarding_stop] = boarding_count.get(c.boarding_stop, 0) + 1
                getoff_count[c.getoff_stop] = getoff_count.get(c.getoff_stop, 0) + 1
            
            #각 정류장에 승하차 인원이 있다면 "정류장ID(3승차, 2하차)" 형식으로 표기
            route_summary = []
            for stop in stops_to_visit:
                board = boarding_count.get(stop, 0)
                drop = getoff_count.get(stop, 0)
                label = stop
                info = []
                if board > 0:
                    info.append(f"{board}승차")
                if drop > 0:
                    info.append(f"{drop}하차")
                if info:
                    label += f"({', '.join(info)})"
                route_summary.append(label)
            #경로 출력 및 누적 기록 "15시 사이클] 방문 경로: A(2승차) → B(1하차)"
            print(f"[{hour}시 사이클] 방문 경로: {' → '.join(route_summary)}")
            self.total_distance_across_runs += distance
            self.total_time_across_runs += minutes
            self.fitness_all.extend(fitness_with_return)
            #고객이 남아있는데 버스가 부족하면 새 버스 추가
            bus_index = 0
            while remaining_customers:
                if bus_index >= len(self.buses):
                    self.bus_counter += 1
                    new_bus = Bus(bus_id=f"Bus{self.bus_counter}", current_stop="00_오이도차고지", max_capacity=15)
                    self.buses.append(new_bus)

                #버스 한 대씩 루트 수행, 이동거리만큼 current_time도 증가
                bus = self.buses[bus_index]
                bus_index += 1

                unfinished = {c.customer_id for c in remaining_customers}
                while unfinished:
                    for i, stop in enumerate(stops_to_visit):
                        if i > 0:
                            prev = stops_to_visit[i - 1]
                            dist = get_distance_between(prev, stop)
                            if dist is not None:
                                bus.total_distance += dist
                                self.current_time += int(dist * 3)

                        #정류장에서 하차 처리
                        bus.current_stop = stop

                        dropped = bus.drop_customer(stop, self.current_time)
                        for c in dropped:
                            c.dropoff_time = self.current_time
                            hour, minute = divmod(self.current_time, 60)
                            print(f"[{hour:02d}:{minute:02d}] {c.customer_id}번 고객이 {bus.bus_id} 버스에서 하차 (정류장: {stop})")
                        #정류장에서 대기 중인 고객 확인 및 탑승
                        waiting_list = list(self.waiting_customers.get(stop, []))
                        for c in waiting_list:
                            wait_time = self.current_time - c.time
                            #고객 탑승 조건 확인 
                            #해당 시간대 고객인지
                            #45분 이하로 기다렸는지
                            #버스 자리가 남았는지
                            if (
                                c.customer_id in hourly_ids and 
                                c.time <= self.current_time and 
                                wait_time <= 45 and 
                                bus.can_board_customer()
                            ):
                                #탑승 or 포기 처리
                                bus.board_customer(c, self.current_time)
                                self.waiting_customers[stop].remove(c)
                                c.pickup_time = self.current_time
                                hour, minute = divmod(self.current_time, 60)
                                print(f"[{hour:02d}:{minute:02d}] {c.customer_id}번 고객이 {bus.bus_id} 버스에 탑승 (정류장: {stop}, 하차: {c.getoff_stop})")
                            elif wait_time > 45:
                                self.waiting_customers[stop].remove(c)
                                self.abandoned_customers += 1
                                remaining_customers = [x for x in remaining_customers if x.customer_id != c.customer_id]  # ⬅️ 이 줄 추가
                                hour, minute = divmod(self.current_time, 60)
                                print(f"[{hour:02d}:{minute:02d}] {c.customer_id}번 고객이 {stop}에서 대기 {wait_time}분 후 탑승 포기")

                    #아직 남아있는 고객 ID 다시 설정
                    unfinished = {c.customer_id for c in remaining_customers if c.customer_id not in {cust.customer_id for cust, _ in bus.finished_customers}}

                bus.end_time = self.current_time
                remaining_customers = [c for c in remaining_customers if all(c.customer_id != cust.customer_id for cust, _ in bus.finished_customers)]
            
            # 다음 시간대까지 시간 여유 계산, 다음 시간대까지 시간이 15분 이상 남으면 버스를 차고지로 복귀
            next_hour = (hour + 1) * 60 if hour < 16 else None
            if next_hour:
                time_gap = next_hour - self.current_time
                if time_gap >= 15:
                    for bus in self.buses:
                        if bus.current_stop != "00_오이도차고지":
                            dist = get_distance_between(bus.current_stop, "00_오이도차고지")
                            if dist:
                                bus.total_distance += dist
                                self.current_time += int(dist * 3)
                                bus.current_stop = "00_오이도차고지"
                                hour, minute = divmod(self.current_time, 60)
                                print(f"[{hour:02d}:{minute:02d}] {bus.bus_id} 버스가 오이도차고지로 복귀하여 대기")
                else:
                    hour, minute = divmod(self.current_time, 60)
                    print(f"[{hour:02d}:{minute:02d}] 버스들이 대기 없이 다음 정류장 이동 예정")

        print("\n=== 시뮬레이션 종료 ===")

        print("[GA 최종 요약]")
        print("\n[고객별 대기 시간 요약]")
        total_waiting = 0
        count = 0
        # 고객별 대기시간 계산 준비
        for customer in self.customers:
            if hasattr(customer, 'pickup_time'):
                wait = customer.pickup_time - customer.time
                total_waiting += wait
                count += 1
                h, m = divmod(wait, 60)
                print(f"Customer {customer.customer_id}: 대기 {wait}분 ({h:02d}:{m:02d})")
        if count:
            avg = total_waiting / count
            h, m = divmod(int(avg), 60)
            print(f"\n[평균 대기 시간] {avg:.2f}분 ({h:02d}:{m:02d}) - 총 {count}명")
        print(f"\n[탑승 포기 고객 수] {self.abandoned_customers}명")
        print(f"총 누적 거리: {self.total_distance_across_runs:.2f} km")
        print(f"총 누적 시간: {self.total_time_across_runs}분")
        print(f"총 예상 비용: {calculate_cost(self.total_distance_across_runs):,}원")

if __name__ == "__main__":
    sim = Simulation()
    sim.run()
