import asyncio
import httpx
import redis
from datetime import datetime
from models import WeatherData
from config import settings
from database import SessionLocal
import json
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.future import select
from fastapi import APIRouter, HTTPException
from apscheduler.schedulers.asyncio import AsyncIOScheduler

router = APIRouter()

CITIES = ['Delhi', 'Mumbai', 'Chennai', 'Bengaluru', 'Kolkata', 'Hyderabad']
REDIS_EXPIRY_TIME = 299  # Cache expiry time in seconds (5 minutes)

scheduler = BackgroundScheduler()

# Initialize Redis client
redis_client = redis.StrictRedis.from_url(settings.REDIS_URL, decode_responses=True)

# Fetch current weather data from OpenWeatherMap API
async def fetch_weather_data(city: str):
    cache_key = f"weather_data_{city}"
    cached_data = redis_client.get(cache_key)

    if cached_data:
        return json.loads(cached_data)  # Return cached data if available

    url = f'http://pro.openweathermap.org/data/2.5/weather?q={city}&appid={settings.OPENWEATHER_API_KEY}'
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Error fetching data from OpenWeatherMap.")
        weather_data = response.json()

        # Cache the weather data
        redis_client.setex(cache_key, REDIS_EXPIRY_TIME, json.dumps(weather_data))
        return weather_data

lock = asyncio.Lock()

# Process and store weather data in DB with temperature conversion based on user preference
async def process_weather_data(data, db: AsyncSession, user_pref_celsius=True):
    try:
        
        temp_kelvin = data['main']['temp']
        feels_like_kelvin = data['main']['feels_like']
        humidity = data['main']['humidity']
        wind_speed = data['wind']['speed']
        main_condition = data['weather'][0]['main']
        description = data['weather'][0]['description']
        pressure = data['main']['pressure']
        visibility = data['visibility']
        
        
        temp_celsius = temp_kelvin - 273.15 if user_pref_celsius else (temp_kelvin - 273.15) * 9 / 5 + 32
        feels_like = feels_like_kelvin - 273.15 if user_pref_celsius else (feels_like_kelvin - 273.15) * 9 / 5 + 32

        
        weather_data = WeatherData(
            city=data['name'],
            main=main_condition,
            description=description,
            temp_celsius=temp_celsius,
            feels_like=feels_like,
            humidity=humidity,
            wind_speed=wind_speed,
            pressure=pressure,
            visibility=visibility,
            timestamp=datetime.utcnow() 
        )
        db.add(weather_data)  # Add the new weather data entry to the session
        await db.commit() 
        return weather_data  

    except Exception as e:
        print(f"Error processing weather data: {e}")
        await db.rollback()



async def get_weather_data_from_db(db: AsyncSession, cities: list):
    subquery = (
        select(
            WeatherData.city,
            func.max(WeatherData.timestamp).label('latest_timestamp')
        )
        .filter(WeatherData.city.in_(cities))
        .group_by(WeatherData.city)
        .subquery()
    )

    query = (
        select(WeatherData)
        .join(subquery, (WeatherData.city == subquery.c.city) & (WeatherData.timestamp == subquery.c.latest_timestamp))
    )

    result = await db.execute(query)  
    return result.scalars().all() 

scheduler = AsyncIOScheduler()


async def fetch_and_process_city_weather(city: str):
    async with SessionLocal() as db:  
        try:
            weather_data = await fetch_weather_data(city)
            await process_weather_data(weather_data, db) 
        except Exception as e:
            print(f"Error processing weather data for {city}: {e}")
        finally:
            await db.close() 

# Main scheduled task to fetch weather data for all cities
async def scheduled_fetch_weather():
    tasks = [fetch_and_process_city_weather(city) for city in CITIES]
    await asyncio.gather(*tasks)  # Running all the fetch and process tasks concurrently

# Start the scheduler
scheduler.add_job(scheduled_fetch_weather, 'interval', minutes=5)
scheduler.start()

# To keep the event loop running
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass

