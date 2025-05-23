from parameters import load_fixed_customers
from customer import Customer
from utils import get_distance_between, calculate_cost
from bus import Bus
import heapq
from ga_optimizer import run_ga
class Simulation:
    def __init__(self):
        self.customers = []
        self.buses = []
        self.waiting_customers = {}
        self.current_time = 600  # 10:00부터 시작
        self.bus_counter = 1

    def generate_customers(self):
        fixed_customers = load_fixed_customers()
        for customer in fixed_customers:
            if customer.boarding_stop != customer.getoff_stop:
                self.customers.append(customer)
                self.waiting_customers.setdefault(customer.boarding_stop, []).append(customer)

    def run(self):
        self.generate_customers()
        self.buses.append(Bus(bus_id="Bus1", current_stop="00_오이도차고지", max_capacity=30))

        for hour in range(10, 17):
            hour_min = hour * 60
            hourly_customers = [c for c in self.customers if hour_min <= c.time < hour_min + 60]
            hourly_ids = {c.customer_id for c in hourly_customers}
            remaining_customers = hourly_customers.copy()
            stops_to_visit = self.get_stops_in_order(hourly_customers)

            bus_index = 0
            while remaining_customers:
                if bus_index >= len(self.buses):
                    self.bus_counter += 1
                    new_bus = Bus(bus_id=f"Bus{self.bus_counter}", current_stop="00_오이도차고지", max_capacity=30)
                    self.buses.append(new_bus)

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
                        else:
                            hour, minute = divmod(self.current_time, 60)
                            
                        bus.current_stop = stop

                        dropped = bus.drop_customer(stop, self.current_time)
                        for c in dropped:
                            c.dropoff_time = self.current_time
                            hour, minute = divmod(self.current_time, 60)
                            print(f"[{hour:02d}:{minute:02d}] {c.customer_id}번 고객이 {bus.bus_id} 버스에서 하차 (정류장: {stop})")

                        waiting_list = list(self.waiting_customers.get(stop, []))
                        for c in waiting_list:
                            if c.customer_id in hourly_ids and c.time <= self.current_time and bus.can_board_customer():
                                bus.board_customer(c, self.current_time)
                                self.waiting_customers[stop].remove(c)
                                c.pickup_time = self.current_time
                                hour, minute = divmod(self.current_time, 60)
                                print(f"[{hour:02d}:{minute:02d}] {c.customer_id}번 고객이 {bus.bus_id} 버스에 탑승 (정류장: {stop}, 하차: {c.getoff_stop})")

                    unfinished = {c.customer_id for c in remaining_customers if c.customer_id not in {cust.customer_id for cust, _ in bus.finished_customers}}
                bus.end_time = self.current_time
                remaining_customers = [c for c in remaining_customers if c.customer_id not in {cust.customer_id for cust, _ in bus.finished_customers}]

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

        self.end_simulation()

    def get_stops_in_order(self, customers):
        pairs = [(c.boarding_stop, c.getoff_stop) for c in customers]
        if not pairs:
            return []
        return run_ga(pairs)


    def all_hourly_customers_finished(self, hourly_ids, bus):
        finished_ids = {c.customer_id for c, _ in bus.finished_customers}
        return hourly_ids.issubset(finished_ids)

    def end_simulation(self):
        print("\n=== 시뮬레이션 종료 ===")
        self.print_summary()

    def print_summary(self):
        print("\n시뮬레이션 결과 요약")
        total_distance = 0.0
        total_customers = 0
        total_cost = 0.0

        for bus in self.buses:
            if bus.total_boarded_customers == 0:
                print(f"{bus.bus_id}은(는) 운행하지 않았습니다.")
            else:
                duration = (bus.end_time - bus.start_time) if bus.end_time and bus.start_time else 0
                cost = calculate_cost(bus.total_distance)
                print(f"{bus.bus_id} 이동거리: {bus.total_distance:.2f} km | 고객 수: {bus.total_boarded_customers}명 | 운영비: {cost:.0f}원 | 운행 시간: {duration}분")
                total_distance += bus.total_distance
                total_customers += bus.total_boarded_customers
                total_cost += cost

        print(f"\n총 이동거리: {total_distance:.2f} km")
        print(f"총 고객 수: {total_customers}명")
        print(f"총 운영비: {total_cost:.0f}원")

if __name__ == "__main__":
    sim = Simulation()
    sim.run()


