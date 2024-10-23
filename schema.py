from pydantic import BaseModel
from datetime import datetime

class AlertSchema(BaseModel):
    city: str
    alert_type: str
    alert_message: str
    timestamp: datetime

    class Config:
        orm_mode = True  # This allows the model to read data from ORM models
        from_attributes = True