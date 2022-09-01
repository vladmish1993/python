import pymysql.cursors
from classes.easyjet import EasyjetClass
from classes.ryanair import RyanairClass
from classes.wizzair import WizzairClass
from functions import *


class FlightClass:
    def __init__(self, cities_from=List[str], max_return_price=100, skipped_countries=List[str], adding_price=Dict,
                 month_cnt=1, log=True):

        # Connect to the database
        self.connection = pymysql.connect(host='localhost',
                                          user='root',
                                          password='',
                                          database='skyscanner',
                                          cursorclass=pymysql.cursors.DictCursor)
        self.cities_from = cities_from
        self.max_return_price = max_return_price
        self.skipped_countries = skipped_countries
        self.adding_price = adding_price
        self.month_cnt = month_cnt
        self.log = log

        self.cities_from_ids = []
        self.ar_allowed_ac = {}
        self.all_cities_by_code = {}
        self.all_cities_by_iata = {}
        self.cheapest_flights = defaultdict(list)
        self.ar_routes = defaultdict(lambda: defaultdict(list))
        self.available_flight = defaultdict(lambda: defaultdict(list))

    def get_cheapest_flights(self):
        with self.connection:
            with self.connection.cursor() as cursor:

                # get lowcost air companies
                sql = "SELECT * FROM `air_companies` WHERE `lowcost`=1"
                cursor.execute(sql)
                result = cursor.fetchall()
                for row in result:
                    ac_class_name = row["name"].replace(" ", "")
                    ac_class_name = ac_class_name.strip().lower().title()
                    self.ar_allowed_ac[row["code"]] = ac_class_name

                # get all airports
                sql = "SELECT * FROM `cities`"
                cursor.execute(sql)
                result = cursor.fetchall()
                for row in result:
                    self.all_cities_by_code[row["code"]] = row
                    self.all_cities_by_iata[row["iata"]] = row

                if self.log:
                    print_to_file("cities_from", self.cities_from)

                # get airports ids
                for city_from in self.cities_from:
                    # if airport code exists
                    if city_from in self.all_cities_by_iata:
                        self.cities_from_ids.append(self.all_cities_by_iata[city_from]["code"])

                if self.cities_from_ids:
                    string_ac = [str(ar_allowed_ac_key) for ar_allowed_ac_key in list(self.ar_allowed_ac.keys())]
                    string_cities = [str(cities_from_id) for cities_from_id in self.cities_from_ids]

                    # get all routes for lowcost companies and cities_from
                    sql = 'SELECT * FROM `routes` WHERE `ac_code` IN (' + ', '.join(
                        string_ac) + ') AND `des_code` IN (' + ', '.join(string_cities) + ')'
                    cursor.execute(sql)
                    result = cursor.fetchall()
                    cnt_routes = 0
                    for row in result:
                        country = self.all_cities_by_code[row["dep_code"]]["country_code"]
                        if country not in self.skipped_countries:
                            cnt_routes += 1
                            self.ar_routes[row["ac_code"]][row["des_code"]].append(row["dep_code"])

        if self.ar_routes:
            if self.log:
                print_to_file("", f"Total routes: {cnt_routes}")

            # get all routes for air company with codes
            for ac_code in self.ar_routes:
                ar_ac_routes_with_codes = {}
                for ac_from_code in self.ar_routes[ac_code]:
                    from_iata = self.all_cities_by_code[ac_from_code]["iata"]
                    ar_ac_routes_with_codes[from_iata] = []
                    for ac_to_code in self.ar_routes[ac_code][ac_from_code]:
                        to_iata = self.all_cities_by_code[ac_to_code]["iata"]
                        ar_ac_routes_with_codes[from_iata].append(to_iata)

                ac_class_name = self.ar_allowed_ac[ac_code]
                class_name = ac_class_name + 'Class'

                if self.log:
                    print_to_file("Routes with codes", ar_ac_routes_with_codes)

                # if routes exists
                if ar_ac_routes_with_codes:
                    ob_ac = eval(class_name)(ar_ac_routes_with_codes, self.month_cnt, self.log)
                    flights_from_to_city = ob_ac.get_all_flights_from_to_city()

                    for direction in flights_from_to_city:
                        for flight_date_time in flights_from_to_city[direction]:
                            for flight_data in flights_from_to_city[direction][flight_date_time]:
                                self.available_flight[direction][flight_date_time].append(flight_data)

            # if self.log:
            # print_to_file("Available .env", self.available_flight)

            # Find return flights
            # sort outbounds flights by timestamp
            self.available_flight["FROM"] = collections.OrderedDict(sorted(self.available_flight["FROM"].items()))

            for flight_date_time in self.available_flight["FROM"]:
                for flight_data in self.available_flight["FROM"][flight_date_time]:
                    ar_cheapest_return = find_return_flight(flight_date_time, flight_data["TO"],
                                                            self.available_flight["TO"], [2, 4])

                    if ar_cheapest_return:
                        sum_price = flight_data["PRICE"] + ar_cheapest_return["PRICE"]

                        # Adding prices
                        if flight_data["FROM"] in self.adding_price:
                            sum_price += self.adding_price[flight_data["FROM"]]
                            flight_data["BUS"] = self.adding_price[flight_data["FROM"]]

                        if ar_cheapest_return["TO"] in self.adding_price:
                            sum_price += self.adding_price[ar_cheapest_return["TO"]]
                            ar_cheapest_return["BUS"] = self.adding_price[ar_cheapest_return["TO"]]

                        sum_price = round(sum_price)

                        if sum_price <= self.max_return_price:
                            flight_data["FROM_TEXT"] = self.all_cities_by_iata[flight_data["FROM"]]["name"]
                            flight_data["TO_TEXT"] = self.all_cities_by_iata[flight_data["TO"]]["name"]
                            ar_cheapest_return["FROM_TEXT"] = self.all_cities_by_iata[ar_cheapest_return["FROM"]][
                                "name"]
                            ar_cheapest_return["TO_TEXT"] = self.all_cities_by_iata[ar_cheapest_return["TO"]]["name"]

                            self.cheapest_flights[sum_price].append({
                                'FROM': flight_data,
                                'TO': ar_cheapest_return
                            })

            if self.log:
                print_to_file("Cheapest flights before sort", self.cheapest_flights)

            self.cheapest_flights = collections.OrderedDict(sorted(self.cheapest_flights.items()))
            self.cheapest_flights = get_different_cheapest(self.cheapest_flights, True)
            self.cheapest_flights = slice_dict(self.cheapest_flights, 10)

            if self.log:
                print_to_file("Cheapest flights after sort", self.cheapest_flights)

        return self.cheapest_flights
