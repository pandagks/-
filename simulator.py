from parameters import load_fixed_customers
from customer import Customer
from utils import get_distance_between, calculate_cost
import heapq

class Event:
    def __init__(self, time, customer=None, bus=None, event_type="boarding"):
        self.time = time
        self.customer = customer
        self.bus = bus
        self.event_type = event_type

    def __lt__(self, other):
        return self.time < other.time

class Simulation:
    MAX_WAIT_TIME = 30

    def __init__(self):
        self.events = []
        self.customers = []
        self.buses = []
        self.waiting_customers = {}
        self.current_time = 0

    def generate_customers(self):
        fixed_customers = load_fixed_customers()
        for customer in fixed_customers:
            self.customers.append(customer)
            self.waiting_customers.setdefault(customer.boarding_stop, []).append(customer)
            self.schedule_event(customer)

    def schedule_event(self, customer):
        heapq.heappush(self.events, Event(customer.time, customer=customer, event_type="boarding"))

    def schedule_bus_move(self, bus, from_stop, to_stop, start_time):
        distance = get_distance_between(from_stop, to_stop)
        if distance is None:
            return

        travel_time = int(distance * 3)
        arrival_time = start_time + travel_time
        heapq.heappush(self.events, Event(time=arrival_time, bus=bus, event_type="bus_move"))

        print(f"[{start_time}분 → {arrival_time}분] {bus.bus_id} 이동 예약: {from_stop} → {to_stop} ({distance}km)")
        bus.next_stop = to_stop
        bus.departure_time = start_time
        bus.start_move()

    def handle_event(self, event):
        self.current_time = event.time

        if event.event_type == "boarding":
            stop = event.customer.boarding_stop
            waiting_list = self.waiting_customers.get(stop, [])
            ready_customers = [c for c in waiting_list if c.time <= self.current_time]

            available_buses = [
                bus for bus in self.buses
                if bus.current_stop == stop and not bus.is_moving and bus.can_board_customer()
            ]

            if not ready_customers or not available_buses:
                if event.customer in self.waiting_customers.get(stop, []):
                    if self.current_time - event.customer.time < self.MAX_WAIT_TIME:
                        heapq.heappush(self.events, Event(self.current_time + 1, customer=event.customer, event_type="boarding"))
                    else:
                        print(f"[{self.current_time}분] {event.customer.customer_id}번 고객은 버스를 오래 기다려 탑승 포기")
                        self.waiting_customers[stop].remove(event.customer)

                        for bus in self.buses:
                            if bus.is_idle():
                                print(f"[{self.current_time}분] 여유 버스 {bus.bus_id}가 정류장 {stop}으로 배차됨")
                                self.schedule_bus_move(bus, bus.current_stop, stop, self.current_time)
                                break
                return

            for bus in available_buses:
                to_board = []
                for c in ready_customers:
                    if len(to_board) + len(bus.onboard_customers) < bus.max_capacity:
                        to_board.append(c)

                if to_board:
                    for c in to_board:
                        bus.board_customer(c, self.current_time)
                        self.waiting_customers[stop].remove(c)
                        print(f"[{self.current_time}분] {c.customer_id}번 고객이 {bus.bus_id} 버스에 탑승 (정류장: {stop})")

                    destination = to_board[0].getoff_stop
                    self.schedule_bus_move(bus, bus.current_stop, destination, self.current_time)
                    break

        elif event.event_type == "bus_move":
            bus = event.bus
            distance = get_distance_between(bus.current_stop, bus.next_stop)
            if distance is not None:
                bus.move_to_next_stop(bus.next_stop, distance, self.current_time)
                bus.finish_move()
                print(f"[{self.current_time}분] {bus.bus_id} 버스가 {bus.current_stop}에 도착")

                dropped = bus.drop_customer(bus.current_stop, self.current_time)
                for c in dropped:
                    print(f"[{self.current_time}분] {c.customer_id}번 고객이 {bus.bus_id} 버스에서 하차")

                remaining = bus.onboard_customers
                if remaining:
                    next_stop = remaining[0].getoff_stop
                    self.schedule_bus_move(bus, bus.current_stop, next_stop, self.current_time)

                if bus.current_stop in self.waiting_customers:
                    for c in list(self.waiting_customers[bus.current_stop]):
                        if c.time <= self.current_time:
                            heapq.heappush(self.events, Event(self.current_time, customer=c, event_type="boarding"))

    def run(self):
        self.generate_customers()
        while self.events:
            event = heapq.heappop(self.events)
            self.handle_event(event)
        self.end_simulation()

    def end_simulation(self):
        print("\n=== 시뮬레이션 종료 ===")
        self.print_summary()

    def print_summary(self):
        print("\n시뮬레이션 결과 요약")
        total_distance = 0.0
        total_customers = 0
        total_cost = 0.0

        if not self.buses:
            print("버스 정보가 없습니다.")
            return

        for bus in self.buses:
            if bus.total_boarded_customers == 0:
                print(f"{bus.bus_id}은(는) 운행하지 않았습니다.")
            else:
                duration = (bus.end_time - bus.start_time) if bus.start_time is not None and bus.end_time is not None else 0
                cost = calculate_cost(bus.total_distance)
                print(f"{bus.bus_id} 이동거리: {bus.total_distance:.2f} km | 고객 수: {bus.total_boarded_customers}명 | 운영비: {cost:.0f}원 | 운행 시간: {duration}분")
                total_distance += bus.total_distance
                total_customers += bus.total_boarded_customers
                total_cost += cost

        print(f"\n총 이동거리: {total_distance:.2f} km")
        print(f"총 고객 수: {total_customers}명")
        print(f"총 운영비: {total_cost:.0f}원")

if __name__ == "__main__":
    from bus import Bus
    sim = Simulation()
    sim.buses.append(Bus(bus_id="Bus1", current_stop="00_오이도차고지", max_capacity=5))
    sim.buses.append(Bus(bus_id="Bus2", current_stop="00_오이도차고지", max_capacity=5))
    sim.buses.append(Bus(bus_id="Bus3", current_stop="00_오이도차고지", max_capacity=5))
    sim.run()
