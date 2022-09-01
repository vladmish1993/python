from functions import *


class WizzairClass:
    ac_name = 'WizzAir'
    temp_rate_eur_gbp = '0.85'
    api_endpoint_src = 'https://wizzair.com/static_fe/metadata.json'

    def __init__(self, routes, month_cnt=1, log=False):
        self.routes = routes
        self.month_cnt = month_cnt
        self.log = log

    def get_name(self):
        return self.ac_name

    def get_routes(self):
        return self.routes

    def get_all_flights_from_to_city(self):
        ar_flights = defaultdict(lambda: defaultdict(list))

        # get endpoint
        api_endpoint_src = make_request_get(self.api_endpoint_src)
        ar_data = json.loads(api_endpoint_src)
        api_endpoint = ar_data["apiUrl"]

        payloads_list = []
        for from_code in self.routes:
            for to_code in self.routes[from_code]:
                for month in range(1, self.month_cnt + 1):
                    if month == 1:
                        date_from_text = datetime.now().strftime("%Y-%m-%d")
                    else:
                        date_from = datetime.now() + timedelta(days=(month - 1) * 30)
                        date_from_text = date_from.strftime("%Y-%m-%d")

                    date_to = datetime.now() + timedelta(days=month * 30)
                    date_to_text = date_to.strftime("%Y-%m-%d")

                    payload = {
                        "flightList": [
                            {
                                "departureStation": from_code,
                                "arrivalStation": to_code,
                                "from": date_from_text,
                                "to": date_to_text
                            },
                            {
                                "departureStation": to_code,
                                "arrivalStation": from_code,
                                "from": date_from_text,
                                "to": date_to_text
                            }
                        ],
                        "priceType": "regular",
                        "adultCount": 2,
                        "childCount": 0,
                        "infantCount": 0
                    }
                    payloads_list.append(payload)

        url = api_endpoint + '/search/timetable'

        # Get data
        loop = get_or_create_eventloop()
        ar_data = loop.run_until_complete(post_multy_url(loop, url, payloads_list))

        for ar_data_month in ar_data:
            # Outbound
            for flight_data in ar_data_month["outboundFlights"]:
                departure_date_time = flight_data["departureDate"]
                departure_time_stamp = get_timestamp_from_date(departure_date_time)
                price = flight_data["price"]["amount"]

                if price:
                    ar_flights["FROM"][departure_time_stamp].append({
                        'FROM': flight_data["departureStation"],
                        'TO': flight_data["arrivalStation"],
                        'PRICE': round(price, 2),
                        'DATE_TIME': departure_date_time,
                        'AIR_COMPANY': self.get_name()
                    })

            # Inbound
            for flight_data in ar_data_month["returnFlights"]:
                departure_date_time = flight_data["departureDate"]
                departure_time_stamp = get_timestamp_from_date(departure_date_time)
                price = flight_data["price"]["amount"]

                if price:
                    ar_flights["TO"][departure_time_stamp].append({
                        'FROM': flight_data["departureStation"],
                        'TO': flight_data["arrivalStation"],
                        'PRICE': round(price, 2),
                        'DATE_TIME': departure_date_time,
                        'AIR_COMPANY': self.get_name()
                    })

        if self.log:
            print_to_file("Fetch complete", f'{self.get_name()} fetch complete')

        return ar_flights
