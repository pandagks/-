## https://github.com/Songdoyang/Simulator_DRT/blob/main/%EC%A1%B8%EC%97%85%EC%9E%91%ED%92%88_simulator/route.py
from route import get_distance_between

class Bus:
    def __init__(self, current_stop, bus_id, max_capacity=15):
        self.bus_id = bus_id
        self.current_stop = current_stop
        self.onboard_customers = []
        self.route = []
        self.finished_customers = []
        self.total_distance = 0
        self.passed_stops = set()
        self.max_capacity = max_capacity
        self.total_boarded_customers = 0
        self.start_time = None
        self.end_time = None
        self.next_stop = None
        self.departure_time = None
        self.is_moving = False

    def is_idle(self):
        return not self.is_moving and self.next_stop is None and len(self.onboard_customers) == 0

    def can_board_customer(self):
        return len(self.onboard_customers) < self.max_capacity

    def start_move(self):
        self.is_moving = True

    def finish_move(self):
        self.is_moving = False
        self.next_stop = None

    def board_customer(self, customer, boarding_time):
        if self.can_board_customer():
            self.onboard_customers.append(customer)
            self.total_boarded_customers += 1
            if self.start_time is None:
                self.start_time = boarding_time
            print(f"Customer {customer.customer_id} boarded on Bus {self.bus_id}")

    def drop_customer(self, stop_id, current_time):
        dropping = [c for c in self.onboard_customers if c.getoff_stop == stop_id]
        self.onboard_customers = [c for c in self.onboard_customers if c.getoff_stop != stop_id]
        self.finished_customers.extend([(c, current_time) for c in dropping])
        return dropping

    def move_to_next_stop(self, stop, distance, arrival_time):
        self.total_distance += distance
        self.current_stop = stop
        self.end_time = arrival_time
