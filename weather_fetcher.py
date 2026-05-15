import os
import requests
import logging

logger = logging.getLogger(__name__)

WEATHER_API_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_API_URL = "https://api.openweathermap.org/data/2.5/forecast"

def get_weather(api_key: str, city: str = "Amsterdam") -> str:
    """Fetch current weather for a city."""
    if not api_key or api_key == "your_openweathermap_api_key_here":
        return "Weather API key not configured."

    params = {
        "q": city,
        "appid": api_key,
        "units": "metric"
    }

    try:
        resp = requests.get(WEATHER_API_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        temp = data["main"]["temp"]
        desc = data["weather"][0]["description"]
        wind = data["wind"]["speed"]
        
        return f"Current weather in {city}: {temp}°C, {desc}. Wind speed: {wind} m/s."
    except Exception as e:
        logger.error(f"Error fetching weather: {e}")
        return "Could not fetch weather data."

def get_forecast(api_key: str, city: str = "Amsterdam") -> str:
    """Fetch a brief 24h forecast."""
    if not api_key or api_key == "your_openweathermap_api_key_here":
        return "Weather API key not configured."

    params = {
        "q": city,
        "appid": api_key,
        "units": "metric",
        "cnt": 8  # 8 * 3 hours = 24 hours
    }

    try:
        resp = requests.get(FORECAST_API_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        forecasts = []
        for item in data["list"]:
            dt = item["dt_txt"]
            temp = item["main"]["temp"]
            desc = item["weather"][0]["description"]
            forecasts.append(f"- {dt}: {temp}°C, {desc}")
        
        return "24h Forecast:\n" + "\n".join(forecasts)
    except Exception as e:
        logger.error(f"Error fetching forecast: {e}")
        return "Could not fetch forecast data."
