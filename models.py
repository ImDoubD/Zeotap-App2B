from sqlalchemy import Column, Integer, String, Float, Date, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class WeatherData(Base):
    __tablename__ = 'weather_data'

    id = Column(Integer, primary_key=True, index=True)
    city = Column(String, index=True)
    main = Column(String)  # Main weather condition (e.g., "Haze")
    description = Column(String)  # Detailed description (e.g., "haze")
    temp_celsius = Column(Float)  # Temperature in Celsius
    feels_like = Column(Float)  # Feels like temperature in Celsius
    humidity = Column(Integer)  # Humidity percentage
    wind_speed = Column(Float)  # Wind speed
    pressure = Column(Integer)  # Atmospheric pressure
    visibility = Column(Integer)  # Visibility in meters
    timestamp = Column(DateTime)

class DailySummary(Base):
    __tablename__ = 'daily_summary'

    id = Column(Integer, primary_key=True, index=True)
    city = Column(String, index=True)
    date = Column(Date, index=True)
    avg_temp = Column(Float)
    max_temp = Column(Float)
    min_temp = Column(Float)
    dominant_condition = Column(String)

class Alert(Base):
    __tablename__ = 'alert'

    id = Column(Integer, primary_key=True, index=True)
    city = Column(String)
    alert_type = Column(String)
    alert_message = Column(String)
    timestamp = Column(DateTime)
