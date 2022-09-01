from functions import *


class RyanairClass:
    ac_name = 'Ryanair'
    temp_rate_eur_gbp = 0.85
    api_endpoint_known_place = 'https://www.ryanair.com/api/farfnd/3/oneWayFares?departureAirportIataCode=#FROM' \
                               '#&arrivalAirportIataCode=#TO#&language=en&market=en-gb&offset=0' \
                               '&outboundDepartureDateFrom=#DATE_FROM#&outboundDepartureDateTo=#DATE_TO' \
                               '#&priceValueTo=100'

    def __init__(self, routes, month_cnt=1, log=False):
        self.routes = routes
        self.month_cnt = month_cnt
        self.log = log

    def get_name(self):
        return self.ac_name

    def get_routes(self):
        return self.routes

    def count_ac_routes(self):
        cnt_ac_routes = 0
        for from_code in self.routes:
            for to_code in self.routes[from_code]:
                cnt_ac_routes += 1
        return cnt_ac_routes

    def get_all_flights_from_to_city(self):
        ar_flights = defaultdict(lambda: defaultdict(list))
        url_list = []
        from_codes = list(self.routes.keys())

        for from_code in self.routes:
            for to_code in self.routes[from_code]:
                for days in range(0, self.month_cnt * 30):
                    if days == 0:
                        date_from = datetime.now()
                        date_from_text = date_from.strftime("%Y-%m-%d")
                    else:
                        date_from = datetime.now() + timedelta(days=days)
                        date_from_text = date_from.strftime("%Y-%m-%d")

                    link_from = str_replace(self.api_endpoint_known_place,
                                            ["#FROM#", "#TO#", "#DATE_FROM#", "#DATE_TO#"],
                                            [from_code, to_code, date_from_text, date_from_text])
                    url_list.append(link_from)
                    link_to = str_replace(self.api_endpoint_known_place, ["#FROM#", "#TO#", "#DATE_FROM#", "#DATE_TO#"],
                                          [to_code, from_code, date_from_text, date_from_text])
                    url_list.append(link_to)

        # Get data
        loop = get_or_create_eventloop()
        ar_data = loop.run_until_complete(get_multy_url(loop, url_list))

        for flight_data_ar in ar_data:
            if flight_data_ar["fares"]:
                for flight_data in flight_data_ar["fares"]:
                    if flight_data["outbound"]["price"]["currencyCode"] == "EUR":
                        price = flight_data["outbound"]["price"]["value"] * self.temp_rate_eur_gbp
                    else:
                        price = flight_data["outbound"]["price"]["value"]

                    departure_date_time = flight_data["outbound"]["departureDate"]
                    departure_time_stamp = get_timestamp_from_date(departure_date_time)

                    if flight_data["outbound"]["departureAirport"]["iataCode"] in from_codes:
                        # Outbound
                        ar_flights["FROM"][departure_time_stamp].append({
                            'FROM': flight_data["outbound"]["departureAirport"]["iataCode"],
                            'TO': flight_data["outbound"]["arrivalAirport"]["iataCode"],
                            'PRICE': round(price, 2),
                            'DATE_TIME': flight_data["outbound"]["departureDate"],
                            'AIR_COMPANY': self.get_name()
                        })
                    else:
                        # Inbound
                        ar_flights["TO"][departure_time_stamp].append({
                            'FROM': flight_data["outbound"]["departureAirport"]["iataCode"],
                            'TO': flight_data["outbound"]["arrivalAirport"]["iataCode"],
                            'PRICE': round(price, 2),
                            'DATE_TIME': flight_data["outbound"]["departureDate"],
                            'AIR_COMPANY': self.get_name()
                        })

        if self.log:
            print_to_file("Fetch complete", f'{self.get_name()} fetch complete')

        return ar_flights
