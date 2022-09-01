import operator
import requests
from datetime import timedelta
from datetime import *
from collections import defaultdict
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List
from aiohttp import ClientSession
import asyncio
import pprint
import collections
import itertools
import json
import time
import os


def print_pre(data):
    pprint.pprint(data)


def print_to_file(info=None, data=None):
    with open("app.log", "w", encoding="utf-8") as log_file:
        if info:
            pprint.pprint(info, log_file)
        if data:
            pprint.pprint(data, log_file)
            pprint.pprint("=======================================", log_file)


def str_replace(string, replace_from, replace_to):
    for r in replace_from:
        index = replace_from.index(r)
        string = string.replace(r, replace_to[index])
    return string


def slice_dict(dictionary, count):
    sliced_dictionary = dict(itertools.islice(dictionary.items(), count))
    return sliced_dictionary


def get_timestamp_from_date(date_string):
    date_string = str_replace(date_string, [".000"], [""])
    date_object = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S")
    timestamp = int(date_object.timestamp())
    return timestamp


def get_formatted_date(date_string):
    date_object = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S")
    formated_date = date_object.strftime("%d-%m-%Y %H:%M")
    return formated_date


def array_orderby(unsorted_list, key1, key2):
    sorted_list = sorted(unsorted_list, key=operator.itemgetter(key1, key2))
    return sorted_list


def get_different_cheapest(ar_flights, round=False):
    ar_flights = collections.OrderedDict(sorted(ar_flights.items()))

    result = defaultdict(list)
    cities = []
    for price in ar_flights:
        for flight in ar_flights[price]:
            if round:
                if flight["FROM"]["TO"] not in cities:
                    cities.append(flight["FROM"]["TO"])
                    result[price].append(flight)
            else:
                if flight["TO"] not in cities:
                    cities.append(flight["TO"])
                    result[price].append(flight)
    return result


def get_or_create_eventloop():
    try:
        return asyncio.get_event_loop()
    except RuntimeError as ex:
        if "There is no current event loop in thread" in str(ex):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return asyncio.get_event_loop()


def make_request_get(link):
    try:
        result = requests.get(link)
        if result.status_code == 200:
            json_res = result.text
            return json_res
    except requests.exceptions.RequestException:  # This is the correct syntax
        print('requests_error')


async def aiohttp_get(session: ClientSession, url: str, timeout: int = 1000):
    async with session.get(url=url, timeout=timeout) as response:
        response_json = []
        if response.status == 200:
            try:
                response_json = await response.json(content_type=None)
            except json.decoder.JSONDecodeError:
                pass

        return response_json


async def aiohttp_post(session: ClientSession, url: str, payload: Dict, timeout: int = 1000):
    async with session.post(url=url, json=payload, timeout=timeout) as response:
        if response.status == 200:
            response_json = None
            try:
                response_json = await response.json(content_type=None)
            except json.decoder.JSONDecodeError:
                pass
        return response_json


async def aiohttp_get_parallel(session: ClientSession, list_of_urls: List[str], timeout: int = 1000):
    results = await asyncio.gather(*[aiohttp_get(session, url, timeout) for url in list_of_urls])
    return results


async def aiohttp_post_parallel(session: ClientSession, url, payloads_list, timeout: int = 1000):
    results = await asyncio.gather(*[aiohttp_post(session, url, payload, timeout) for payload in payloads_list])
    return results


async def get_multy_url(loop, url_list):
    async with ClientSession(loop=loop) as session:
        results = await aiohttp_get_parallel(session, url_list)
        return results


async def post_multy_url(loop, url, payloads_list):
    async with ClientSession(loop=loop) as session:
        results = await aiohttp_post_parallel(session, url, payloads_list)
        return results


def find_return_flight(timestamp, from_airport, return_list, days=None):
    if days is None:
        days = [2, 3]
    ar_return_flights = {}

    time_stamp_plus_days_from = timestamp + 86400 * days[0]
    time_stamp_plus_days_to = timestamp + 86400 * days[1]

    for flight_date_time in return_list:
        if flight_date_time in range(time_stamp_plus_days_from, time_stamp_plus_days_to):
            for flight_data in return_list[flight_date_time]:
                if flight_data["FROM"] == from_airport:
                    ar_return_flights[flight_data["PRICE"]] = flight_data

    if ar_return_flights:
        # sort by price and slice first one
        ar_return_flights = collections.OrderedDict(sorted(ar_return_flights.items()))
        ar_return_flights = dict(list(ar_return_flights.items())[:1])
        ar_return_flights = list(ar_return_flights.values())[0]

    return ar_return_flights


def find_return_flight_weekends(timestamp, flight_data_from, from_airport, return_list):
    ar_return_flights = {}

    ob_date = datetime.fromtimestamp(timestamp)
    weekday = ob_date.strftime('%A')
    hour = int(ob_date.strftime('%H'))

    # print(f'{timestamp}=={weekday} == {hour}')
    if (flight_data_from["FROM"] == "DUB" and weekday == "Saturday" and 8 <= hour <= 12) or (flight_data_from[
                                                                                                 "FROM"] != "DUB" and weekday == "Friday" and 20 <= hour or weekday == "Saturday" and 8 <= hour <= 11):

        time_stamp_plus_days_from = timestamp + 86400 * 1
        if weekday == "Friday":
            time_stamp_plus_days_to = timestamp + 86400 * 2 + 3600 * 4
        else:
            time_stamp_plus_days_to = timestamp + 86400 * 2 - 3600 * 8

        for flight_date_time in return_list:
            ob_date = datetime.fromtimestamp(flight_date_time)
            weekday = ob_date.strftime('%A')
            hour = int(ob_date.strftime('%H'))

            # if flight_date_time < timestamp + 86400 * 3 and weekday == "Sunday" and 19 <= hour:
            if flight_date_time in range(time_stamp_plus_days_from, time_stamp_plus_days_to):
                for flight_data in return_list[flight_date_time]:
                    if flight_data["FROM"] == from_airport:
                        ar_return_flights[flight_data["PRICE"]] = flight_data

        if ar_return_flights:
            # sort by price and slice first one
            ar_return_flights = collections.OrderedDict(sorted(ar_return_flights.items()))
            ar_return_flights = dict(list(ar_return_flights.items())[:1])
            ar_return_flights = list(ar_return_flights.values())[0]

    return ar_return_flights
