"""Pydantic models of the request bodies (they also feed the generated OpenAPI documentation).

The models guarantee the *shape* of a request: a JSON object with known fields of the right basic type.
Business rules (length limits, value ranges, privacy) stay in the domain layer (validation.py, services.py),
so every error message stays in one place and in Ukrainian.
"""
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Body(BaseModel):
    model_config = ConfigDict(extra="ignore")


class RegisterIn(Body):
    username: str | None = Field(None, description="Логін: 3-20 символів, латиниця, цифри, «_»")
    password: str | None = Field(None, description="Пароль, щонайменше 8 символів")
    display_name: str | None = Field(None, description="Ім'я в профілі (за замовчуванням - логін)")


class LoginIn(Body):
    username: str | None = None
    password: str | None = None


class ProfileIn(Body):
    display_name: str | None = None
    sport: str | None = None
    level: str | None = Field(None, description="початківець | середній | просунутий | професіонал")
    goals: str | None = None
    bio: str | None = None


class ImageIn(Body):
    image: str | None = Field(None, description="Зображення JPEG/PNG/WebP як data URL у base64")


class WorkoutIn(Body):
    title: str | None = None
    date: str | None = Field(None, description="РРРР-ММ-ДД, за замовчуванням сьогодні")
    visibility: str | None = Field(None, description="private (за замовчуванням) або public")
    notes: str | None = None
    exercises: Any = Field(None, description="[{name, sets: [{reps, weight_kg}]}]")


class WorkoutPatch(Body):
    title: str | None = None
    date: str | None = None
    visibility: str | None = None
    notes: str | None = None


class PostIn(Body):
    body: str | None = None
    visibility: str | None = Field(None, description="public (за замовчуванням) або private")
    image: str | None = Field(None, description="Необов'язкове фото як data URL у base64")


class PostPatch(Body):
    body: str | None = None
    visibility: str | None = None


class CommentIn(Body):
    body: str | None = None


class AiIn(Body):
    prompt: str | None = Field(None, description="Опис бажаного тренування, до 500 символів")
