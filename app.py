import json
import urllib

from flask import Flask, render_template, request, redirect, url_for
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, State
import requests

api_key = 'knkCECdY7peqeS8qu8VtYSqTvPMAchAM'


class WeatherForecast:
    def __init__(self, temperature, humidity, wind_speed, wind_probability):
        self.temperature = temperature
        self.humidity = humidity
        self.wind_speed = wind_speed
        self.wind_probability = wind_probability


def get_location_data(lat, lon):
    url = 'http://dataservice.accuweather.com/locations/v1/cities/geoposition/search'
    params = {
        'q': f'{lat},{lon}',
        'apikey': api_key,
        'details': 'true'
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


def get_current_forecast(city_key):
    url = f'http://dataservice.accuweather.com/currentconditions/v1/{city_key}'
    params = {
        'apikey': api_key,
        'details': 'true'
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    if data and len(data) > 0:
        data = data[0]
    else:
        raise ValueError("Ошибка: данные о погоде не получены или неверный формат")

    return WeatherForecast(
        temperature=data.get('Temperature', {}).get('Metric', {}).get('Value'),
        humidity=data.get('RelativeHumidity'),
        wind_speed=data.get('Wind', {}).get('Speed', {}).get('Metric', {}).get('Value'),
        wind_probability=data.get('PrecipitationSummary', {}).get('Precipitation', {}).get('Value', 0.0)
    )


def check_bad_weather(weather_forecast):
    if weather_forecast.temperature < 0 or weather_forecast.temperature > 35:
        return "Ой-ой, погода плохая!"
    elif weather_forecast.humidity > 50:
        return "Ой-ой, погода плохая!"
    elif weather_forecast.wind_probability > 0.7:
        return "Ой-ой, погода плохая!"
    return "Погода — супер!"


app = Flask(__name__)

dash_app = Dash(__name__, server=app, url_base_pathname='/dash/')

dash_app.layout = html.Div([
    dcc.Dropdown(id='city-dropdown', placeholder='Выберите город'),
    dcc.Dropdown(
        id='parameter-dropdown',
        options=[
            {"label": "Temperature", "value": 'temperature'},
            {"label": "Humidity", "value": 'humidity'},
            {"label": "Wind Speed", "value": 'wind_speed'},
            {"label": "Precipitation Probability", "value": 'wind_probability'}
        ],
        value='temperature',
        placeholder="Выберите параметр"
    ),
    dcc.Graph(id='weather-graph'),
    html.Div(id='stored-weather-data', style={'display': 'none'})  # Элемент для хранения данных
])


@app.route("/", methods=["GET", "POST"])
def index():
    weather_data = None
    error = None
    city_options = []

    if request.method == "POST":
        try:
            start_point = request.form["start_point"]
            end_point = request.form["end_point"]

            start_lat, start_lon = start_point.split(',')
            end_lat, end_lon = end_point.split(',')

            start_point_params = get_location_data(start_lat, start_lon)
            start_point_key = start_point_params['Key']
            start_city = start_point_params['LocalizedName']

            end_point_params = get_location_data(end_lat, end_lon)
            end_point_key = end_point_params['Key']
            end_city = end_point_params['LocalizedName']

            start_weather = get_current_forecast(start_point_key)
            end_weather = get_current_forecast(end_point_key)

            weather_data = {
                "start_city": start_city,
                "end_city": end_city,
                "start_weather_evaluation": check_bad_weather(start_weather),
                "end_weather_evaluation": check_bad_weather(end_weather),
                "start_forecast": start_weather.__dict__,
                "end_forecast": end_weather.__dict__,
                "cities_options": [
                    {"label": start_city, "value": "start_forecast"},
                    {"label": end_city, "value": "end_forecast"}
                ]
            }
        except Exception as e:
            error = str(e)
        dash_options = json.dumps(weather_data['cities_options']) if weather_data else json.dumps({})
    return render_template("index.html", weather_data=weather_data, error=error, dash_options=dash_options)

@dash_app.server.before_request
def dash_with_params():
    if request.path == '/dash/':
        weather_data_json = request.args.get('weather_data', '[]')  # Получаем данные из строки запроса
        weather_data_json = urllib.parse.unquote(weather_data_json) # Декодируем URL, если необходимо
        print("Decoded weather data:", weather_data_json)
        try:
            print(type(weather_data_json))
            weather_data = json.loads(weather_data_json)
            print("Parsed weather data:", weather_data)
            dash_app.layout.children[0].options = weather_data  # Устанавливаем опции для city-dropdown
        except json.JSONDecodeError as e:
            print("JSON parsing error:", e)

@dash_app.callback(
    [Output('city-dropdown', 'options')],
    [Input('stored-weather-data', 'children')])  # Ожидаем изменения данных
def load_and_store_data(stored_data):
    print("Callback for loading city options triggered")
    if stored_data:
        try:
            cities = json.loads(stored_data)
            print("Loaded data: ", cities)
            return [cities]
        except json.JSONDecodeError as e:
            print("Error loading data:", e)
            return [[]]
    print(f"stored_data: {stored_data}")
    return [[]]  # Возвращаем пустое значение, если данных нет

@dash_app.callback(
    Output('weather-graph', 'figure'),
    [Input('city-dropdown', 'value'), Input('parameter-dropdown', 'value')],
    [State('stored-weather-data', 'children')]
)
def update_graph(selected_city, weather_type, city_options_json):
    print("Update graph callback triggered")
    if not selected_city or not city_options_json:
        print("No data for plotting")
        return go.Figure()

    city_options = json.loads(city_options_json)
    forecast = next((city['forecast'] for city in city_options if city['value'] == selected_city), None)

    if not forecast:
        print("No forecast data found for selected city")
        return go.Figure()

    data_map = {
        'temperature': forecast['temperature'],
        'humidity': forecast['humidity'],
        'wind_speed': forecast['wind_speed'],
        'wind_probability': forecast['wind_probability']
    }
    print("Data map:", data_map)

    fig = go.Figure(data=[
        go.Bar(x=[selected_city], y=[data_map[weather_type]], name=weather_type)
    ])
    fig.update_layout(title=f"Current {weather_type.title()} in {selected_city}")
    return fig


if __name__ == "__main__":
    app.run(debug=True)