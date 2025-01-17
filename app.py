import json
import urllib

from flask import Flask, render_template, request, redirect, url_for
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, State
import requests

api_key = 'og9R34qcnRjo5h19ldGzqZG6RaICmAjG'

import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
import requests

# Константы
ACCUWEATHER_API_KEY = "og9R34qcnRjo5h19ldGzqZG6RaICmAjG"
ACCUWEATHER_BASE_URL = "http://dataservice.accuweather.com"
ACCUWEATHER_LOCATION_URL = f"{ACCUWEATHER_BASE_URL}/locations/v1/cities/search"
ACCUWEATHER_FORECAST_URL = f"{ACCUWEATHER_BASE_URL}/forecasts/v1/daily/5day"

# Инициализация приложения
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Прогноз погоды для нескольких городов"

app.layout = html.Div([
    html.H2("Прогноз погоды для нескольких городов", style={'text-align': 'center', 'margin-top': '40px'}),

    dbc.Row([
        dbc.Col([
            html.Label("Город отправления:"),
            dbc.Input(id='origin-input', type='text', placeholder='Название города', className="mb-3"),
            html.Div(id='intermediate-points'),
            html.Label("Город назначения:"),
            dbc.Input(id='destination-input', type='text', placeholder='Название города', className="mb-3"),
            dbc.Button("Добавить промежуточный город", id='add-point-btn', color="primary", className="mb-3"),
            dcc.Dropdown(
                id="plot-interval-dropdown",
                options=[{"label": "3 Дня", "value": "3"}, {"label": "5 Дней", "value": "5"}],
                value="5",
                clearable=False,
                className="mb-3"
            ),
            dbc.Button("Получить прогноз", id='get-weather-btn', color="success"),
            dcc.Dropdown(
                id="plot-type-dropdown",
                options=[
                    {"label": "Температура", "value": "temperature"},
                    {"label": "Влажность", "value": "humidity"},
                ],
                value="temperature",
                clearable=False,
                className="mb-3"
            )
        ], width=4),

        dbc.Col(dcc.Graph(id='map'), width=8)
    ]),

    dcc.Store(id="session-data"),
    dcc.Graph(id='selected-graph', style={'display': 'none'}),
])


def get_city_coordinates(city_name):
    """Получить ключ локации AccuWeather по названию города."""
    params = {"apikey": ACCUWEATHER_API_KEY, "q": city_name}
    response = requests.get(ACCUWEATHER_LOCATION_URL, params=params)

    if response.status_code == 200:
        data = response.json()
        if data:
            return data[0]["Key"]
    return None


def get_weather_forecast(location_key, days=5):
    """Получить прогноз погоды по ключу локации."""
    params = {"apikey": ACCUWEATHER_API_KEY, "metric": True}
    response = requests.get(f"{ACCUWEATHER_FORECAST_URL}/{location_key}", params=params)

    if response.status_code == 200:
        return response.json()
    return None


@app.callback(
    Output('intermediate-points', 'children'),
    Input('add-point-btn', 'n_clicks'),
    State('intermediate-points', 'children'),
)
def add_intermediate_point(n_clicks, children):
    if n_clicks:
        children = children or []
        point_number = len(children) + 1
        new_point = dbc.Input(
            id={'type': 'intermediate-input', 'index': point_number},
            placeholder=f'Промежуточный город {point_number}',
            className="mb-2"
        )
        children.append(new_point)
    return children


@app.callback(
    Output('session-data', 'data'),
    Input('get-weather-btn', 'n_clicks'),
    State('origin-input', 'value'),
    State('destination-input', 'value'),
    State({'type': 'intermediate-input', 'index': dash.ALL}, 'value'),
)
def fetch_weather_data(n_clicks, origin, destination, intermediate_points):
    if not n_clicks:
        return dash.no_update

    all_locations = {"Город отправления": origin, "Город прибытия": destination, "Промежуточный город (пересадка)": intermediate_points or []}
    weather_data = {}

    for loc_type, city in all_locations.items():
        if isinstance(city, list):
            for i, intermediate_city in enumerate(city, start=1):
                loc_key = get_city_coordinates(intermediate_city)
                if loc_key:
                    weather_data[f"intermediate_{i}"] = get_weather_forecast(loc_key)
        else:
            loc_key = get_city_coordinates(city)
            if loc_key:
                weather_data[loc_type] = get_weather_forecast(loc_key)

    return weather_data


@app.callback(
    Output('selected-graph', 'figure'),
    Output('selected-graph', 'style'),
    Input('session-data', 'data'),
    State('plot-type-dropdown', 'value'),
)
def update_graphs(weather_data, plot_type):
    if not weather_data:
        return go.Figure(), {'display': 'none'}  # Если нет данных, скрываем график

    traces = []
    for loc, forecast in weather_data.items():
        days = forecast['DailyForecasts']
        dates = [day['Date'] for day in days]

        if plot_type == "temperature":
            values = [day['Temperature']['Maximum']['Value'] for day in days]
            y_label = "Температура (°C)"
        elif plot_type == "humidity":
            values = [day['Day']['RainProbability'] for day in days]
            y_label = "Влажность (%)"
        elif plot_type == "wind_speed":
            values = [day['Day']['Wind']['Speed']['Value'] for day in days]
            y_label = "Скорость ветра (км/ч)"
        else:
            continue

        traces.append(go.Scatter(x=dates, y=values, mode='lines', name=loc))

    fig = go.Figure(data=traces)
    fig.update_layout(
        title="Прогноз погоды",
        xaxis_title="Дата",
        yaxis_title=y_label,
        template="plotly_white",
    )

    return fig, {'display': 'block'}  # График отображается, если данные есть


# Обновление параметров выпадающего меню
app.layout = html.Div([
    html.H2("Прогноз погоды для нескольких городов", style={'text-align': 'center', 'margin-top': '40px'}),

    dbc.Row([
        dbc.Col([
            html.Label("Город отправления:"),
            dbc.Input(id='origin-input', type='text', placeholder='Название города', className="mb-3"),
            html.Div(id='intermediate-points'),
            html.Label("Город назначения:"),
            dbc.Input(id='destination-input', type='text', placeholder='Название города', className="mb-3"),
            dcc.Dropdown(
                id="plot-interval-dropdown",
                options=[{"label": "На 3 дня", "value": "3"}, {"label": "На 5 дней", "value": "5"}],
                value="5",
                clearable=False,
                className="mb-3"
            ),
            dcc.Dropdown(
                id="plot-type-dropdown",
                options=[
                    {"label": "Температура", "value": "temperature"},
                    {"label": "Влажность", "value": "humidity"},
                    {"label": "Скорость ветра", "value": "wind_speed"},
                ],
                value="temperature",
                clearable=False,
                className="mb-3"
            ),
            # Размещение кнопок в горизонтальном ряду
            dbc.Row([
                dbc.Col(dbc.Button("Добавить промежуточный город", id='add-point-btn', color="primary", className="mb-3"), width=6),
                dbc.Col(dbc.Button("Получить прогноз погоды", id='get-weather-btn', color="success", className="mb-3"), width=6),
            ]),  # Разделить кнопки равномерно по ширине
        ], width=4),

        dbc.Col(dcc.Graph(id='map'), width=8)
    ]),

    dcc.Store(id="session-data"),
    dcc.Graph(id='selected-graph', style={'display': 'none'}),
], style={'padding': '140px'})

if __name__ == '__main__':
    app.run_server(debug=True)
