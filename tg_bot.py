from classes.flights import FlightClass
from threading import Timer
from functions import *

load_dotenv()

# get .env data
BOT_ID = os.getenv('BOT_ID')
MAX_RETURN_PRICE = int(os.getenv('MAX_RETURN_PRICE'))
MONTH_CNT = int(os.getenv('MONTH_CNT'))
SKIP_GB_IE = (os.getenv('SKIP_GB_IE', 'False') == 'True')
IS_LOG = (os.getenv('IS_LOG', 'False') == 'True')

payload = {
    "parse_mode": "HTML",
    "disable_web_page_preview": False,
    "disable_notification": False,
    "reply_to_message_id": None
}
headers = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

url_send_mess = "https://api.telegram.org/bot" + BOT_ID + "/sendMessage"

run = True
offset = None
joke_command = "/say_joke"
rate_command = "/say_rate"
flight_command = "/find_tickets"
wait_answer = defaultdict(lambda: defaultdict(list))


def send_message(text, chat_id):
    payload["text"] = text
    payload["chat_id"] = chat_id
    response = requests.post(url_send_mess, json=payload, headers=headers)
    if IS_LOG:
        print_to_file("Send message", response.text)


def get_messages(url):
    try:
        result = requests.get(url)
        if result.status_code == 200:
            ar_data = json.loads(result.text)
            return ar_data
    except requests.exceptions.RequestException:
        print('requests_error')


def get_joke():
    try:
        result = requests.get("https://v2.jokeapi.dev/joke/Any?safe-mode")
        if result.status_code == 200:
            ar_data = json.loads(result.text)
            html = None
            if ar_data:
                if ar_data["type"] == "single":
                    joke = ar_data["joke"]
                    html = f"<b>{joke}</b>"
                else:
                    setup = ar_data["setup"]
                    delivery = ar_data["delivery"]
                    html = f"{setup}\n<tg-spoiler><b>{delivery}</b></tg-spoiler>"
            return html
    except requests.exceptions.RequestException:
        print('requests_error')


def get_rate():
    try:
        result = requests.get("https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?json")
        if result.status_code == 200:
            ar_data = json.loads(result.text)
            html = None
            if ar_data:
                for rate_data in ar_data:
                    if rate_data["cc"] == "GBP":
                        rate = rate_data["rate"]
                        html = f"<b>{rate}</b>"
            return html
    except requests.exceptions.RequestException:
        print('requests_error')


def get_flights(airports_str=None, trip_range_str=None):
    cities_from = []
    if airports_str:
        airports = airports_str.split(',')
        for airport in airports:
            cities_from.append(airport.upper().strip())

    if cities_from:
        # skip Great Britain and Ireland
        if SKIP_GB_IE:
            skipped_countries = ["GB", "IE"]
        else:
            skipped_countries = []

        # Bus from/to city
        # adding_price = {'DUB': 10}
        adding_price = {}

        max_return_price = MAX_RETURN_PRICE
        month_cnt = MONTH_CNT

        # trip length
        trip_length = []
        if trip_range_str:
            trip_range = trip_range_str.split('-')
            if type(trip_range) == list:
                for trip_range_day in trip_range:
                    trip_length.append(int(trip_range_day.strip()))

        # Get the cheapest flights
        ob_ac = FlightClass(cities_from, max_return_price, skipped_countries, adding_price, month_cnt, trip_length,
                            True)
        cheapest_flights = ob_ac.get_cheapest_flights()

        if cheapest_flights:
            ar_return_html = []
            for price in cheapest_flights:
                flight_data = cheapest_flights[price][0]
                ar_return_html.append(
                    f'From <b>{flight_data["FROM"]["FROM_TEXT"]}</b> to <b>{flight_data["FROM"]["TO_TEXT"]}</b> at {get_formatted_date(flight_data["FROM"]["DATE_TIME"])} via {flight_data["FROM"]["AIR_COMPANY"]} and return on {get_formatted_date(flight_data["TO"]["DATE_TIME"])} via {flight_data["TO"]["AIR_COMPANY"]} for <b>{price}£</b>')

            return_html = f"10 cheapest return flights in next {MONTH_CNT} month:\n==========================\n"
            return_html = return_html + '\n==========================\n'.join(ar_return_html)
            return return_html
        else:
            return "Unfortunately there are no flights 🥲 \n Maybe you are failed in airport code..."
    else:
        return "Something went wrong 😞"


def get_last_messages():
    global offset

    if not offset:
        url = f"https://api.telegram.org/bot" + BOT_ID + "/getUpdates"
    else:
        url = f"https://api.telegram.org/bot" + BOT_ID + f"/getUpdates?offset={offset}"

    ar_data = get_messages(url)

    if ar_data["ok"]:
        if "result" in ar_data.keys():
            for message in ar_data["result"]:
                if "message" in message.keys():
                    offset = message["update_id"] + 1

                    user_id = message["message"]["from"]["id"]
                    chat_id = message["message"]["chat"]["id"]

                    command = None
                    if "entities" in message["message"].keys():
                        if message["message"]["entities"][0]["type"] == "bot_command":
                            command = message["message"]["text"]

                    # if user select flight_command, next message should be with airport codes
                    if chat_id in wait_answer:
                        for wait_answer_chat_user in list(wait_answer[chat_id]):
                            if wait_answer_chat_user == user_id and wait_answer[chat_id][user_id]["command"] == flight_command:
                                if "airports" in wait_answer[chat_id][user_id]:
                                    airports = wait_answer[chat_id][user_id]["airports"]
                                    trip_range = message["message"]["text"]

                                    # send wait placeholder
                                    send_message("Wait for a wee minute ⏰", chat_id)

                                    # get flights
                                    send_html = get_flights(airports, trip_range)
                                    if send_html:
                                        send_message(send_html, chat_id)
                                        del wait_answer[chat_id][user_id]
                                else:
                                    wait_answer[chat_id][user_id]["airports"] = message["message"]["text"]
                                    send_html = f"Please set trip length in days, format: 2-3, 5-8, etc."
                                    send_message(send_html, chat_id)

                    if command:
                        send_html = None
                        if joke_command in command:
                            send_html = get_joke()
                        elif rate_command in command:
                            send_html = get_rate()
                        elif flight_command in command:
                            wait_answer[chat_id][user_id] = {"command": flight_command}
                            send_html = f"Hi, {message['message']['from']['first_name']}!\nPlease send nearby airport codes separated by comma \",\""

                        if send_html:
                            send_message(send_html, chat_id)


def test():
    global run
    get_last_messages()
    if run:
        Timer(1, test).start()


test()
