from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from service.weatherFetch import scheduled_fetch_weather
from service.weatherSummary import schedule_daily_summaries
from controller import router as weather_router


app = FastAPI(
    title="Weather Monitoring System",
    description="Real-time weather monitoring API using FastAPI and PostgreSQL",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (for development, limit in production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

scheduler = BackgroundScheduler()

# Background job to fetch weather data every 5 minutes
def setup_weather_scheduled_jobs():
    scheduler.add_job(scheduled_fetch_weather, 'interval', minutes=5)
    scheduler.add_job(schedule_daily_summaries, 'interval', hours=24)
    scheduler.start()

app.include_router(weather_router, prefix="/api")

# Application startup event to initiate background tasks
@app.on_event("startup")
def startup_event():
    setup_weather_scheduled_jobs()

@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()

@app.get("/")
def root():
    return {"message": "Weather Monitoring API is running!"}
