from functions import *


class EasyjetClass:
    ac_name = 'EasyJet'
    apiEndpoint = 'https://www.easyjet.com/api/routepricing/v2/searchfares/GetLowestDailyFares?departureAirport=#FROM' \
                  '#&arrivalAirport=#TO#&currency=GBP'

    def __init__(self, routes, month_cnt=1, log=False, start_date=None, finish_date=None):
        self.routes = routes
        self.month_cnt = month_cnt
        self.log = log
        self.start_date = start_date
        self.finish_date = finish_date

    def get_name(self):
        return self.ac_name

    def get_routes(self):
        return self.routes

    def get_cheapest_flight(self):
        start_timestamp = int(datetime.timestamp(self.start_date))
        finish_times_tamp = int(datetime.timestamp(self.finish_date))
        cnt_ac_routes = self.count_ac_routes()
        ar_flights = defaultdict(list)
        cnt = 0

        for from_code in self.routes:
            for to_code in self.routes[from_code]:
                link = str_replace(self.apiEndpoint, ["#FROM#", "#TO#"], [from_code, to_code])
                src = make_request_get(link)
                ar_data = json.loads(src)

                # Outbound
                for flight_data in ar_data:
                    price = flight_data['outboundPrice']
                    departure_date_time = flight_data['departureDateTime']
                    departure_time_stamp = get_timestamp_from_date(departure_date_time)

                    if departure_time_stamp in range(start_timestamp, finish_times_tamp):
                        ar_flights[round(price, 2)].append({
                            'FROM': from_code,
                            'TO': to_code,
                            'COUNTRY': flight_data['arrivalCountry'],
                            'PRICE': round(price, 2),
                            'DATE_TIME': departure_date_time,
                            'AIR_COMPANY': self.get_name()
                        })

                cnt += 1
                print(f'{self.get_name()} {cnt} of {cnt_ac_routes} routes complete')

        ar_flights_diff_cheapest = get_different_cheapest(ar_flights, False)
        return slice_dict(ar_flights_diff_cheapest, 1)

    def count_ac_routes(self):
        cnt_ac_routes = 0
        for from_code in self.routes:
            for _ in self.routes[from_code]:
                cnt_ac_routes += 1
        return cnt_ac_routes

    def get_all_flights_from_to_city(self):
        ar_flights = defaultdict(lambda: defaultdict(list))
        time_stamp_to = int(time.time()) + 24 * 3600 * self.month_cnt * 30
        url_list = []

        from_codes = list(self.routes.keys())

        for from_code in self.routes:
            for to_code in self.routes[from_code]:
                # Outbound
                link_from = str_replace(self.apiEndpoint, ["#FROM#", "#TO#"], [from_code, to_code])
                url_list.append(link_from)
                # Inbound
                link_to = str_replace(self.apiEndpoint, ["#FROM#", "#TO#"], [to_code, from_code])
                url_list.append(link_to)

        # Get data
        loop = get_or_create_eventloop()
        ar_data = loop.run_until_complete(get_multy_url(loop, url_list))

        for ar_data_direction in ar_data:
            for flight_data in ar_data_direction:

                price = flight_data['outboundPrice']
                departure_date_time = flight_data['departureDateTime']
                departure_time_stamp = get_timestamp_from_date(departure_date_time)

                if departure_time_stamp < time_stamp_to:
                    # Outbound
                    if flight_data["departureAirport"] in from_codes:
                        ar_flights["FROM"][departure_time_stamp].append({
                            'FROM': flight_data['departureAirport'],
                            'TO': flight_data['arrivalAirport'],
                            'PRICE': round(price, 2),
                            'DATE_TIME': departure_date_time,
                            'AIR_COMPANY': self.get_name()
                        })
                    else:
                        ar_flights["TO"][departure_time_stamp].append({
                            'FROM': flight_data['departureAirport'],
                            'TO': flight_data['arrivalAirport'],
                            'PRICE': round(price, 2),
                            'DATE_TIME': departure_date_time,
                            'AIR_COMPANY': self.get_name()
                        })

        if self.log:
            print_to_file("Fetch complete", f'{self.get_name()} fetch complete')

        return ar_flights
