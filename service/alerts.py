from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import WeatherData, Alert
from fastapi import BackgroundTasks
from datetime import datetime
from schema import AlertSchema
from service.weatherFetch import CITIES
from database import SessionLocal
from config import settings

# Checking the thresholds for alerts asynchronously
async def check_alerts(db: AsyncSession, background_tasks: BackgroundTasks, temp_threshold=35.0, humidity_threshold=80, pressure_threshold_min=1000, pressure_threshold_max=1030, wind_threshold=15, visibility_threshold=1000):
    low_temp = 0.0  # Example lower bound for very cold weather
    for city in CITIES:
        query = (
            select(WeatherData)
            .filter(WeatherData.city == city)
            .order_by(WeatherData.timestamp.desc())
            .limit(2)
        )
        result = await db.execute(query)  # Asynchronously execute the query
        recent_data = result.scalars().all()

        if len(recent_data) >= 2:
            if recent_data[0].temp_celsius > temp_threshold and recent_data[1].temp_celsius > temp_threshold:
                background_tasks.add_task(create_alert, city, "High Temperature", f"Temperature exceeded {temp_threshold}°C", db)
            if recent_data[0].temp_celsius < low_temp:
                background_tasks.add_task(create_alert, city, "Very Cold", "Temperature dropped below freezing", db)
            if recent_data[0].humidity > humidity_threshold:
                background_tasks.add_task(create_alert, city, "High Humidity", f"Humidity exceeded {humidity_threshold}%", db)
            if recent_data[0].wind_speed > wind_threshold:
                background_tasks.add_task(create_alert, city, "Very Strong Winds", f"Wind Speed exceeded {wind_threshold}%", db)
            if recent_data[0].pressure > pressure_threshold_max:
                background_tasks.add_task(create_alert, city, "Very High Pressure", f"Pressure exceeded {pressure_threshold_max}%", db)
            if recent_data[0].pressure < pressure_threshold_min:
                background_tasks.add_task(create_alert, city, "Very Low Pressure", f"Pressure below {pressure_threshold_min}%", db)
            if recent_data[0].visibility < visibility_threshold:
                background_tasks.add_task(create_alert, city, "Very Low Visibility", f"Visibility below {pressure_threshold_min}%", db)

# Helper function to create alerts
async def create_alert(city: str, alert_type: str, alert_message: str, db: AsyncSession):
    alert = Alert(
        city=city,
        alert_type=alert_type,
        alert_message=alert_message,
        timestamp=datetime.utcnow()
    )
    db.add(alert)
    await db.commit()


async def fetch_latest_alert(db: AsyncSession, city: str):
    try:
        stmt = (
            select(Alert)
            .filter(Alert.city == city)
            .order_by(Alert.timestamp.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        latest_alert = result.scalars().first()

        if latest_alert:
            return AlertSchema.from_orm(latest_alert)  # Serialize to Pydantic model
        else:
            return {"message": f"No alerts found for city: {city}"}
    except Exception as e:
        return {"error": str(e)}

    

async def send_email_alert(city: str, recipient_email: str, db: AsyncSession):
    # Fetch the latest alert for the given city
    latest_alert = await fetch_latest_alert(db, city)
    
    if "message" in latest_alert:
        return {"error": f"No alerts found for {city}"}

    #content
    subject = f"Weather Alert for {city}: {latest_alert.alert_type}"
    body = f"""
    Hello,

    There is a new weather alert for {city}:
    
    Alert Type: {latest_alert.alert_type}
    Alert Message: {latest_alert.alert_message}
    Timestamp: {latest_alert.timestamp}

    Please take necessary precautions.

    Best regards,
    Weather Monitoring System
    """

    # Create a multipart email
    message = MIMEMultipart()
    message["From"] = settings.SMTP_SENDER_EMAIL
    message["To"] = recipient_email
    message["Subject"] = subject

    
    message.attach(MIMEText(body, "plain"))

    # Connect to the SMTP server and send the email
    try:
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_SENDER_EMAIL, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_SENDER_EMAIL, recipient_email, message.as_string())

        return {"message": f"Alert email sent successfully to {recipient_email}."}
    except Exception as e:
        return {"error": str(e)}


