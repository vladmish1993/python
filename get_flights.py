from classes.flights import FlightClass
from functions import *

cities_from = ['DUB']
max_return_price = 100
skipped_countries = ["GB", "IE"]
# skipped_countries = []
adding_price = {'DUB': 10}
month_cnt = 1

ob_ac = FlightClass(cities_from, max_return_price, skipped_countries, adding_price, month_cnt, True)
cheapest_flights = ob_ac.get_cheapest_flights()
print_pre(cheapest_flights)
