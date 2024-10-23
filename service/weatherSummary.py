from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime
from models import WeatherData, DailySummary
from sqlalchemy import func
import json
from service.weatherFetch import CITIES, redis_client
from database import get_db  # Import async session factory

async def calculate_daily_summaries(db: AsyncSession):
    try:
        today = datetime.utcnow().date()
        for city in CITIES:
            cache_key = f"daily_summary_{city}_{today}"
            cached_summary = redis_client.get(cache_key)

            if cached_summary:
                continue  # Skip if cached daily summary is available

            result = await db.execute(
                select(
                    func.avg(WeatherData.temp_celsius).label('avg_temp'),
                    func.max(WeatherData.temp_celsius).label('max_temp'),
                    func.min(WeatherData.temp_celsius).label('min_temp'),
                    WeatherData.main
                ).filter(
                    WeatherData.city == city,
                    func.date(WeatherData.timestamp) == today
                ).group_by(WeatherData.main)  # Add GROUP BY clause
            )
            results = result.all()

            if not results:
                continue  # Skip if no results

            # Extract average, max, min temperatures
            avg_temp, max_temp, min_temp, _ = results[0]

            # Find dominant condition based on most frequent weather condition during the day
            weather_conditions_result = await db.execute(
                select(WeatherData.main).filter(
                    WeatherData.city == city,
                    func.date(WeatherData.timestamp) == today
                )
            )
            weather_conditions = weather_conditions_result.scalars().all()
            
            if weather_conditions:
                dominant_condition = max(set(weather_conditions), key=weather_conditions.count)
            else:
                dominant_condition = None  # Handle case with no weather data

            summary = DailySummary(
                city=city,
                date=today,
                avg_temp=avg_temp,
                max_temp=max_temp,
                min_temp=min_temp,
                dominant_condition=dominant_condition
            )
            db.add(summary)

        await db.commit()  # Commit outside of the loop
    except Exception as e:
        print(f"Error in calculate_daily_summaries: {e}")
        await db.rollback()  # Rollback if there is an error




async def schedule_daily_summaries():
    async with get_db() as db:  # Use the async context manager to get the session
        await calculate_daily_summaries(db)