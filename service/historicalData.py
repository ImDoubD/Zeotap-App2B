import httpx
from sqlalchemy import func
import json
from config import settings
from service.weatherFetch import REDIS_EXPIRY_TIME, redis_client

# Fetch historical weather data from OpenWeatherMap
async def fetch_historical_weather_data(city: str):
    cache_key = f"historical_data_{city}"
    cached_data = redis_client.get(cache_key)
    
    if cached_data:
        return json.loads(cached_data)
    
    url = f'http://history.openweathermap.org/data/2.5/history/city?q={city}&appid={settings.OPENWEATHER_API_KEY}'
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        historical_data = response.json()

        # Cache the historical weather data
        redis_client.setex(cache_key, REDIS_EXPIRY_TIME, json.dumps(historical_data))
        return historical_data
