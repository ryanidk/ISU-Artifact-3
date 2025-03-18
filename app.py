from flask import Flask, request, render_template, redirect, url_for, session
import math
from groq import Groq
import os
import json
import random
import re
from urllib.parse import quote
from collections import Counter
import requests
import time
import jwt

# Flask app setup
app = Flask(__name__)
groq_api_key = os.getenv('GROQ_API_KEY')
app.secret_key = os.getenv('SECRET_KEY')
groq_client = Groq(api_key=groq_api_key)

# Apple WeatherKit
SERVICE_ID = os.getenv('WEATHERKIT_SERVICE_ID')
TEAM_ID = os.getenv('WEATHERKIT_TEAM_ID')
KEY_ID = os.getenv('WEATHERKIT_KEY_ID')
PRIVATE_KEY = os.getenv('WEATHERKIT_PRIVATE_KEY')

# Mapbox (for geocoding)
MAPBOX_API_KEY = os.getenv('MAPBOX_API_KEY')


# Round 4 functions
def round_4(value):
    if value.is_integer():
        return f"{int(value)}"
    elif len(f"{value}".split('.')[1]) <= 4:
        return f"{value}"
    else:
        return f"~{value:.4f}"

# Util functions (Find mean, median, mode, range, interquartile range, quartiles, outliers)
def find_mean(data):
    if not data:
        return None
    return sum(data) / len(data)

def find_median(data):
    if not data:
        return None
    sorted_data = sorted(data)
    n = len(sorted_data)
    if n % 2 == 0:
        return (sorted_data[n // 2] + sorted_data[n // 2 - 1]) / 2
    else:
        return sorted_data[n // 2]


def find_modes(data):
    counts = Counter(data)
    max_count = max(counts.values())

    modes = [key for key, value in counts.items() if value == max_count]

    if len(modes) == len(data):
        return None
    else:
        modes_str = [round_4(mode) for mode in modes]
        return modes_str

def find_range(data):
    if not data:
        return None
    return max(data) - min(data)


def find_quartiles(data):
    if not data:
        return None
    sorted_data = sorted(data)
    n = len(sorted_data)

    lower_half = sorted_data[:n // 2]
    upper_half = sorted_data[(n + 1) // 2:]
    q1 = find_median(lower_half)
    q2 = find_median(sorted_data)
    q3 = find_median(upper_half)

    return q1, q2, q3


def find_iqr(data):
    if not data:
        return None
    q1, _, q3 = find_quartiles(data)
    return q3 - q1


def find_outliers(data):
    if not data:
        return None
    q1, _, q3 = find_quartiles(data)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr

    outliers = [x for x in data if x < lower_bound or x > upper_bound]
    outliers_str = [round_4(outlier) for outlier in outliers]
    return outliers_str

def generate_jwt():
    headers = {
        'kid': KEY_ID,
        'id': f'{TEAM_ID}.{SERVICE_ID}'
    }
    payload = {
        'iss': TEAM_ID,
        'iat': int(time.time()),
        'exp': int(time.time()) + 3600,
        'sub': SERVICE_ID
    }
    token = jwt.encode(payload, PRIVATE_KEY, algorithm='ES256', headers=headers)
    return token


@app.route("/", methods=['GET', 'POST'])
def index():
    if request.method == "POST":
        result = None
        ai_explain = None
        try:
            data = request.form.get('data').strip()
            data = [float(x) for x in data.split() if bool(re.match(r'^[0-9.]+$', x))]
            if len(data) <= 1:
                result = f"Error in calculation: Invalid data"
                ai_explain = "<b>AI Explanation:</b>\nNot available"
                return json.dumps({'result': result, 'explain': ai_explain})

            # stats
            mean = find_mean(data)
            median = find_median(data)
            modes = find_modes(data)
            range_ = find_range(data)
            q1, q2, q3 = find_quartiles(data)
            iqr = find_iqr(data)
            outliers = find_outliers(data)

            # resutl
            result = f"Mean: {round_4(mean)}\n"
            result += f"Median: {round_4(median)}\n"
            if modes is not None:
                result += f"Mode: {', '.join(modes)}\n"
            else:
                result += f"Mode: None\n"
            result += f"Range: {round_4(range_)}\n"
            result += f"Quartiles: Q1 = {round_4(q1)}, Q2 = {round_4(q2)}, Q3 = {round_4(q3)}\n"
            result += f"Interquartile Range: {round_4(iqr)}\n"
            if len(outliers) > 0:
                result += f"Outliers: {', '.join(outliers)}"
            else:
                result += f"Outliers: None"

            # explain
            completion = groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {
                        "role": "system",
                        "content": f"You are a helpful assistant aimed to help a user analyze data by calculating the mean, median, and mode, range, outliers, interquartile range, quartiles the data provided: {data}. The results are as follows: {result}. You shall not output markdown, like **, __, ||, etc. NEVER OUTPUT ANYTHING IN **BOLD**. Never ask the user for any additional input to make your explanation complete. You shall only use the results provided, even if you disagree. The exception is numbers with a decimal of zero, which you can omit. Only provide examples if they are step by step and directly related to the calculation. Avoid using too many decimals."
                    },
                    {
                        "role": "user",
                        "content": f"Analyze the data: {data}."
                    }
                ],
                temperature=0.7,
                max_tokens=1024,
                top_p=1,
                stream=False,
                stop=None,
            )
            ai_explain = f"<b>AI Explanation:</b>\n{completion.choices[0].message.content}"
        except Exception as e:
            result = f"Error in calculation: {e}"
            ai_explain = "<b>AI Explanation:</b>\nNot available"
        return json.dumps({'result': result, 'explain': ai_explain})
    return render_template('calculator.html')

@app.route("/grapher", methods=['GET', 'POST'])
def grapher():
    return render_template('grapher.html')

@app.route("/stock-grapher", methods=['GET', 'POST'])
def stock_grapher():
    return render_template('stock-grapher.html')


@app.route("/weather-grapher", methods=['GET', 'POST'])
def weather_grapher():
    if request.method == "GET":
        return render_template('weather-grapher.html')
    elif request.method == "POST":
        try:
            city = request.get_json()['city'].strip()

            # Geocoding
            geocode_url = f'https://api.mapbox.com/search/geocode/v6/forward?q={quote(city)}&access_token={MAPBOX_API_KEY}'
            geocode_response = requests.get(geocode_url).json()
            long = geocode_response['features'][0]['properties']['coordinates']['longitude']
            lat = geocode_response['features'][0]['properties']['coordinates']['latitude']

            # Weather data
            weatherkit_url = f'https://weatherkit.apple.com/api/v1/weather/en_US/{lat}/{long}?dataSets=currentWeather,forecastDaily,forecastHourly,forecastNextHour&timezone=America/Toronto'
            headers = {
                'Authorization': f'Bearer {generate_jwt()}'
            }
            weather_response = requests.get(weatherkit_url, headers=headers)

            return weather_response.text

        except Exception as e:
            return f"Error: {e}"


if __name__ == "__main__":
    app.run(host="0.0.0.0")

