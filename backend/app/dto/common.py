"""Shared DTOs."""
from pydantic import BaseModel


class HealthDTO(BaseModel):
    status: str
    database: str
    mysql_version: str
    alarm_events: int


class MessageDTO(BaseModel):
    message: str