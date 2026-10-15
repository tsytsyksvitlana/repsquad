"""Input validation."""
import base64
import binascii
import re
from datetime import date, timedelta

from .errors import ValidationError
from .privacy import PRIVATE, PUBLIC, VISIBILITIES

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,20}$")
MIN_PASSWORD = 8

MAX_EXERCISES = 30
MAX_SETS = 20
MAX_REPS = 100
MAX_WEIGHT = 1000
MAX_COMMENT = 500
MAX_AVATAR_BYTES = 200_000
MAX_POST_IMAGE_BYTES = 600_000
MAX_POST = 1000

LEVELS = ("", "початківець", "середній", "просунутий", "професіонал")


def clean_text(value, label, *, max_len, required=False):
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise ValidationError(f"Поле «{label}» має бути текстом")
    value = re.sub(r"[ \t]+", " ", value).strip()
    if required and not value:
        raise ValidationError(f"Поле «{label}» обов'язкове")
    if len(value) > max_len:
        raise ValidationError(f"Поле «{label}» задовге (максимум {max_len} символів)")
    return value


def validate_username(username):
    if not isinstance(username, str) or not USERNAME_RE.match(username):
        raise ValidationError("Логін: 3–20 символів, лише латинські літери, цифри та «_»")
    return username


def validate_password(password):
    if not isinstance(password, str) or len(password) < MIN_PASSWORD:
        raise ValidationError(f"Пароль має містити щонайменше {MIN_PASSWORD} символів")
    if len(password) > 128:
        raise ValidationError("Пароль задовгий (максимум 128 символів)")
    return password


def validate_profile(data):
    """Returns only the profile fields that were passed, validated."""
    out = {}
    if "display_name" in data:
        out["display_name"] = clean_text(data["display_name"], "Ім'я", max_len=40, required=True)
    if "sport" in data:
        out["sport"] = clean_text(data["sport"], "Вид спорту", max_len=40)
    if "level" in data:
        level = clean_text(data["level"], "Рівень", max_len=20).lower()
        if level not in LEVELS:
            raise ValidationError("Невірний рівень підготовки")
        out["level"] = level
    if "goals" in data:
        out["goals"] = clean_text(data["goals"], "Цілі", max_len=200)
    if "bio" in data:
        out["bio"] = clean_text(data["bio"], "Про себе", max_len=300)
    return out


def _sniff_image(data):
    """Detects the real image type from magic bytes (the client-sent type is never trusted)."""
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def validate_image(image, max_bytes):
    """Accepts a base64 data URL (or raw base64) of a JPEG/PNG/WebP picture; returns (mime, bytes)."""
    if not isinstance(image, str) or not image:
        raise ValidationError("Оберіть зображення")
    payload = image.split(",", 1)[1] if image.startswith("data:") and "," in image else image
    try:
        data = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError):
        raise ValidationError("Некоректне зображення") from None
    if len(data) > max_bytes:
        raise ValidationError(f"Зображення завелике (максимум {max_bytes // 1000} КБ)")
    mime = _sniff_image(data)
    if not mime:
        raise ValidationError("Підтримуються лише зображення JPEG, PNG або WebP")
    return mime, data


def validate_avatar(image):
    return validate_image(image, MAX_AVATAR_BYTES)


def validate_post(data):
    """Validates a new post: text and/or a picture. Visibility defaults to public."""
    body = clean_text(data.get("body"), "Допис", max_len=MAX_POST)
    image = validate_image(data["image"], MAX_POST_IMAGE_BYTES) if data.get("image") else None
    if not body and not image:
        raise ValidationError("Напишіть текст або додайте фото")
    return {"body": body, "image": image, "visibility": validate_visibility(data.get("visibility", PUBLIC))}


def validate_date(raw, today: date):
    try:
        d = date.fromisoformat(raw)
    except (TypeError, ValueError):
        raise ValidationError("Невірна дата (очікується РРРР-ММ-ДД)") from None
    if d > today + timedelta(days=1):
        raise ValidationError("Дата тренування не може бути в майбутньому")
    if d < date(2000, 1, 1):
        raise ValidationError("Дата тренування занадто давня")
    return d.isoformat()


def validate_visibility(raw):
    if raw not in VISIBILITIES:
        raise ValidationError("Видимість має бути «public» (публічне) або «private» (приватне)")
    return raw


def normalize_exercise_name(name):
    return re.sub(r"\s+", " ", name).strip()


def validate_workout(data, today: date):
    """Validates a workout creation body. Visibility defaults to private."""
    title = clean_text(data.get("title"), "Назва", max_len=60, required=True)
    notes = clean_text(data.get("notes"), "Нотатки", max_len=500)
    visibility = validate_visibility(data.get("visibility", PRIVATE))
    day = validate_date(data.get("date") or today.isoformat(), today)

    exercises = data.get("exercises")
    if not isinstance(exercises, list) or not exercises:
        raise ValidationError("Додайте хоча б одну вправу")
    if len(exercises) > MAX_EXERCISES:
        raise ValidationError(f"Забагато вправ (максимум {MAX_EXERCISES})")

    cleaned = []
    for i, ex in enumerate(exercises, start=1):
        if not isinstance(ex, dict):
            raise ValidationError(f"Вправа №{i}: невірний формат")
        name = normalize_exercise_name(clean_text(ex.get("name"), f"Назва вправи №{i}", max_len=50, required=True))
        sets = ex.get("sets")
        if not isinstance(sets, list) or not sets:
            raise ValidationError(f"Вправа «{name}»: додайте хоча б один підхід")
        if len(sets) > MAX_SETS:
            raise ValidationError(f"Вправа «{name}»: забагато підходів (максимум {MAX_SETS})")
        cs = []
        for j, s in enumerate(sets, start=1):
            if not isinstance(s, dict):
                raise ValidationError(f"Вправа «{name}», підхід {j}: невірний формат")
            reps, weight = s.get("reps"), s.get("weight_kg", 0)
            if isinstance(reps, bool) or not isinstance(reps, int) or not 1 <= reps <= MAX_REPS:
                raise ValidationError(f"Вправа «{name}», підхід {j}: повторень має бути від 1 до {MAX_REPS}")
            if isinstance(weight, bool) or not isinstance(weight, (int, float)) or not 0 <= weight <= MAX_WEIGHT:
                raise ValidationError(f"Вправа «{name}», підхід {j}: вага має бути від 0 до {MAX_WEIGHT} кг")
            cs.append({"reps": reps, "weight_kg": round(float(weight), 2)})
        cleaned.append({"name": name, "sets": cs})

    return {"title": title, "notes": notes, "visibility": visibility, "date": day, "exercises": cleaned}
