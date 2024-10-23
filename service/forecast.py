import httpx
import json
from config import settings
from service.weatherFetch import REDIS_EXPIRY_TIME, redis_client

# Fetch weather forecast data
async def fetch_forecast_data(city: str):
    cache_key = f"forecast_data_{city}"
    cached_data = redis_client.get(cache_key)
    
    if cached_data:
        return json.loads(cached_data)
    
    url = f'http://pro.openweathermap.org/data/2.5/forecast?q={city}&appid={settings.OPENWEATHER_API_KEY}'
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        forecast_data = response.json()

        # Cache the forecast data
        redis_client.setex(cache_key, REDIS_EXPIRY_TIME, json.dumps(forecast_data))
        return forecast_data
