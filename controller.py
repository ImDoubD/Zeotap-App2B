from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from datetime import datetime
from database import get_db
from service.alerts import check_alerts, fetch_latest_alert, send_email_alert
from service.weatherFetch import fetch_weather_data, CITIES, get_weather_data_from_db
from service.weatherSummary import calculate_daily_summaries
from service.forecast import fetch_forecast_data
from service.historicalData import fetch_historical_weather_data
from models import DailySummary
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

router = APIRouter()

# Get current weather for a single city
@router.get("/weather/{city}")
async def get_weather(city: str):
    try:
        weather_data = await fetch_weather_data(city)
        return weather_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# API endpoint to fetch and store weather data
@router.get("/weather")
async def get_weather_data(user_pref_celsius: bool = True, db: AsyncSession = Depends(get_db)):
    all_weather_data = []
    
    # Fetch weather data from the database
    weather_data_records = await get_weather_data_from_db(db, CITIES)
    
    for weather_data in weather_data_records:
        # Assuming you have a method to convert data into the desired format
        processed_data = {
            "city": weather_data.city,
            "main": weather_data.main,
            "description": weather_data.description,
            "temp_celsius": weather_data.temp_celsius,
            "feels_like": weather_data.feels_like,
            "humidity": weather_data.humidity,
            "wind_speed": weather_data.wind_speed,
            "pressure": weather_data.pressure,
            "visibility": weather_data.visibility,
            "timestamp": weather_data.timestamp.isoformat()  # Convert to string format if needed
        }
        all_weather_data.append(processed_data)

    return {"weather": all_weather_data}

@router.get("/weather/daily-summary/{city}")
async def get_daily_summary(city: str, db: AsyncSession = Depends(get_db)):
    today = datetime.utcnow().date()
    result = await db.execute(
        select(DailySummary).filter(DailySummary.city == city, DailySummary.date == today)
    )
    summary = result.scalars().first()  # Get the first result

    if not summary:
        # No need to wrap in a new transaction; use the existing one.
        await calculate_daily_summaries(db)  # Pass the existing session
        result = await db.execute(
            select(DailySummary).filter(DailySummary.city == city, DailySummary.date == today)
        )
        summary = result.scalars().first()

    return summary


# Get historical weather data for a city
@router.get("/weather/historical/{city}")
async def get_historical_weather(city: str):
    try:
        historical_data = await fetch_historical_weather_data(city)
        return historical_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get weather forecast for a city
@router.get("/weather/forecast/{city}")
async def get_weather_forecast(city: str):
    try:
        forecast_data = await fetch_forecast_data(city)
        return forecast_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Trigger alert check with user-configurable thresholds
@router.post("/weather/check-alerts")
async def check_weather_alerts(background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db), 
                               temp_threshold: float = Query(35.0), humidity_threshold: float = Query(80), pressure_threshold_min: int = Query(1000), pressure_threshold_max: int = Query(1030), wind_threshold: float = Query(15), visibility_threshold: int = Query(1000)):
    try:
        await check_alerts(db, background_tasks, temp_threshold=temp_threshold, humidity_threshold=humidity_threshold, pressure_threshold_min=pressure_threshold_min, pressure_threshold_max=pressure_threshold_max, wind_threshold=wind_threshold, visibility_threshold=visibility_threshold)
        return {"message": "Alert check initiated with user-configurable thresholds."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Fetch the latest alert signal of specified city
@router.get("/weather/latest-alert/{city}")
async def get_latest_alert(city: str, db: AsyncSession = Depends(get_db)):
    try:
        # Fetch the latest alert for the specified city
        latest_alert = await fetch_latest_alert(db, city)
        if "error" in latest_alert:
            raise HTTPException(status_code=500, detail=latest_alert["error"])
        return latest_alert
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mail sending query
@router.post("/weather/send-alert-email")
async def send_alert_email(city: str = Query(...), email: str = Query(...), db: AsyncSession = Depends(get_db)):
    try:
        result = await send_email_alert(city, email, db)
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return {"message": result["message"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))