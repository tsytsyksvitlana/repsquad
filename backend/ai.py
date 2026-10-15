"""AI trainer: builds a workout draft with Google Gemini (standard library only)."""
import difflib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

from .errors import AppError, ValidationError

MAX_PROMPT = 500

SYSTEM = (
    "Ти — фітнес-тренер. Складай тренування українською мовою. Відповідай ЛИШЕ JSON-об'єктом з полями: "
    "title (коротка назва, не більше 40 символів), notes (рядок, 1–2 речення порад), exercises (масив із 5–6 вправ). "
    "Кожна вправа: name (рядок), sets (масив із 3–4 підходів), кожен підхід: reps (ціле число; для утримання, "
    "як-от планка, це секунди), weight_kg (число; 0 для вправ з власною вагою). "
    "Усі вправи мають бути РІЗНІ й точно відповідати запиту (група м'язів, місце, обладнання, тривалість). "
    "Список вправ нижче — лише підказка назв: бери з нього вправи, що підходять до запиту, або додай свої."
)


class AiUnavailable(AppError):
    status = 503


GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models"
GEMINI_MODELS = ("gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite")  # primary model + fallbacks

# Response structure that Gemini is forced to follow (structured output)
GEMINI_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "title": {"type": "STRING"},
        "notes": {"type": "STRING"},
        "exercises": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
            "name": {"type": "STRING"},
            "sets": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
                "reps": {"type": "INTEGER"}, "weight_kg": {"type": "NUMBER"}},
                "required": ["reps", "weight_kg"]}}},
            "required": ["name", "sets"]}},
    },
    "required": ["title", "notes", "exercises"],
}


def _gemini_key():
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""


def _gemini_models():
    """The model from GEMINI_MODEL, or the default list: the next one is tried when a model is overloaded."""
    return [os.environ["GEMINI_MODEL"]] if os.environ.get("GEMINI_MODEL") else list(GEMINI_MODELS)


def active_model():
    """Model name for display purposes."""
    return f"Gemini ({_gemini_models()[0]})"


class _Retryable(AiUnavailable):
    """Temporary problem with one model (overload, rate limit, timeout): another model can be tried."""


def _gemini_request(model, payload):
    req = urllib.request.Request(
        f"{GEMINI_URL}/{urllib.parse.quote(model)}:generateContent", data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": _gemini_key()})
    try:
        with urllib.request.urlopen(req, timeout=40) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise _Retryable("Перевищено ліміт запитів Gemini. Зачекайте хвилину й спробуйте ще раз.") from None
        if e.code in (404, 500, 502, 503, 504):
            raise _Retryable(f"Gemini зараз перевантажений або модель {model} недоступна ({e.code}). Спробуйте ще раз.") from None
        try:
            detail = json.load(e)["error"].get("message", "")
        except Exception:  # noqa: BLE001 - the error body is optional
            detail = ""
        raise AiUnavailable(f"Gemini відхилив запит ({e.code}). Перевірте GEMINI_API_KEY. {detail}"[:300]) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise _Retryable("Не вдалося звернутися до Gemini (немає зв'язку або надто довга відповідь).") from None
    except ValueError:
        raise _Retryable("Gemini повернув неочікувану відповідь") from None
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError):
        reason = (data.get("promptFeedback") or {}).get("blockReason") if isinstance(data, dict) else None
        raise AiUnavailable("Gemini не повернув тренування" + (f" ({reason})" if reason else "") + ". Спробуйте переформулювати запит.") from None


def gemini_chat(messages):
    """Calls Gemini generateContent and returns the JSON text of the reply. The key goes in a header, not in the URL."""
    system = "\n".join(m["content"] for m in messages if m["role"] == "system")
    payload = {
        "contents": [{"role": "user", "parts": [{"text": m["content"]}]} for m in messages if m["role"] != "system"],
        "generationConfig": {"temperature": 0.5, "responseMimeType": "application/json", "responseSchema": GEMINI_SCHEMA},
    }
    if system:
        payload["systemInstruction"] = {"parts": [{"text": system}]}
    error = None
    for model in _gemini_models():
        try:
            return _gemini_request(model, payload)
        except _Retryable as e:
            error = e
    raise AiUnavailable(error.message)


def default_chat(messages):
    if not _gemini_key():
        raise AiUnavailable("AI-тренер не налаштований: додайте GEMINI_API_KEY у файл .env (див. README).")
    return gemini_chat(messages)


def _num(value, lo, hi, default):
    try:
        n = float(value)
    except (TypeError, ValueError):
        return default
    return min(max(n, lo), hi)


def _snap_name(name, known):
    """Fixes model typos by snapping to the closest name from the list of known exercises."""
    lower = {k.casefold(): k for k in known}
    hit = difflib.get_close_matches(name.casefold(), list(lower), n=1, cutoff=0.78)
    return lower[hit[0]] if hit else name


def _parse_sets(ex):
    raw_sets = ex.get("sets")
    default_weight = ex.get("weight_kg", ex.get("weight"))
    reps_list = ex.get("reps")
    if isinstance(reps_list, list) and reps_list and not any(isinstance(x, dict) for x in (raw_sets or [])):
        # shape {"sets": [3, 4], "reps": [8, 10]}: sets are taken from the list of reps
        raw_sets = [{"reps": r, "weight_kg": default_weight} for r in reps_list[:8]]
    elif isinstance(raw_sets, (int, float)) and not isinstance(raw_sets, bool):
        # the model sometimes writes the number of sets as a plain number
        raw_sets = [{"reps": 10, "weight_kg": default_weight}] * int(_num(raw_sets, 1, 8, 3))
    sets = []
    if isinstance(raw_sets, list):
        for s in raw_sets[:8]:
            if isinstance(s, dict):
                weight = s.get("weight_kg", s.get("weight", default_weight))
                sets.append({"reps": int(_num(s.get("reps"), 1, 100, 10)), "weight_kg": round(_num(weight, 0, 500, 0), 2)})
    return sets


def sanitize_plan(raw, known=()):
    """Turns the model reply into a safe workout draft.

    Models often get the structure or numbers wrong, so every value is clamped
    to allowed limits and malformed exercises are dropped."""
    if isinstance(raw, str):
        match = re.search(r"\{.*\}", raw, re.S)
        try:
            raw = json.loads(match.group(0) if match else raw)
        except ValueError:
            raise AiUnavailable("AI повернув відповідь у невірному форматі. Спробуйте ще раз.") from None
    if not isinstance(raw, dict) or not isinstance(raw.get("exercises"), list):
        raise AiUnavailable("AI не склав тренування. Спробуйте уточнити запит.")

    exercises, seen = [], set()
    for ex in raw["exercises"][:12]:
        if not isinstance(ex, dict) or not isinstance(ex.get("name"), str):
            continue
        name = _snap_name(re.sub(r"\s+", " ", ex["name"]).strip()[:50], known)
        sets = _parse_sets(ex)
        if name and sets and name.casefold() not in seen:
            seen.add(name.casefold())
            exercises.append({"name": name, "sets": sets})
    if not exercises:
        raise AiUnavailable("AI не склав жодної вправи. Спробуйте переформулювати запит.")

    title = raw.get("title") if isinstance(raw.get("title"), str) else ""
    notes = raw.get("notes")
    if isinstance(notes, list):
        notes = " ".join(n for n in notes if isinstance(n, str))
    notes = notes if isinstance(notes, str) else ""
    return {"title": _fit_title(title) or "AI-тренування", "notes": notes.strip()[:500], "exercises": exercises}


def _fit_title(title, limit=60):
    """Shortens a title at a word boundary instead of in the middle of a word."""
    title = re.sub(r"\s+", " ", title).strip()
    if len(title) <= limit:
        return title
    return title[:limit].rsplit(" ", 1)[0].rstrip(" ,;:-–—(") or title[:limit]


def _round_weight(kg):
    return max(2.5, round(kg / 2.5) * 2.5)


def personalize_weights(plan, records):
    """Replaces the weights guessed by the model with weights computed from the user's records.

    The model does not know the person's strength, so its number is only used as a "weighted exercise" flag.
    With history: weight = estimated 1RM / (1 + (reps + 2) / 30), i.e. the Epley formula inverted with
    2 reps in reserve. Without history the weight is not invented (0) and the user is asked to pick it.
    Every exercise gets weight_source: "history" | "needs" | None (bodyweight)."""
    best = {r["exercise"].casefold(): r["best_1rm"] for r in records if r["best_1rm"] > 0}
    for ex in plan["exercises"]:
        if not any(s["weight_kg"] > 0 for s in ex["sets"]):
            ex["weight_source"] = None
            continue
        one_rm = best.get(ex["name"].casefold())
        for s in ex["sets"]:
            s["weight_kg"] = _round_weight(one_rm / (1 + (s["reps"] + 2) / 30)) if one_rm else 0
        ex["weight_source"] = "history" if one_rm else "needs"
    return plan


# Muscle groups for the prompt hint: it helps the model pick exercises that match the request
MUSCLE_GROUPS = {
    "Груди": ["Жим лежачи", "Жим гантелей лежачи", "Віджимання від підлоги", "Розведення гантелей", "Віджимання на брусах"],
    "Спина": ["Підтягування", "Тяга верхнього блоку", "Тяга нижнього блоку", "Тяга штанги в нахилі", "Станова тяга", "Гіперекстензія"],
    "Плечі": ["Жим стоячи", "Махи гирею"],
    "Біцепс і трицепс": ["Підйом на біцепс", "Французький жим", "Віджимання на брусах"],
    "Ноги й сідниці": ["Присідання зі штангою", "Болгарські присідання", "Фронтальні присідання", "Румунська тяга", "Випади", "Жим ногами", "Підйом на носки"],
    "Прес і кор": ["Планка", "Скручування"],
    "Все тіло": ["Ривок штанги", "Поштовх штанги", "Махи гирею"],
}


def exercise_hint(known):
    """Hint text: exercises by muscle group plus the user's own exercises that are not in any group."""
    grouped = {n.casefold() for names in MUSCLE_GROUPS.values() for n in names}
    lines = [f"{group}: {', '.join(names)}" for group, names in MUSCLE_GROUPS.items()]
    extra = [n for n in known if n.casefold() not in grouped]
    if extra:
        lines.append("Інше: " + ", ".join(extra[:10]))
    return "\n".join(lines)


def build_messages(prompt, profile, known_exercises):
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValidationError("Опишіть, яке тренування вам потрібно")
    prompt = prompt.strip()
    if len(prompt) > MAX_PROMPT:
        raise ValidationError(f"Запит задовгий (максимум {MAX_PROMPT} символів)")
    about = "; ".join(f"{label}: {profile[key]}" for key, label in
                      (("sport", "вид спорту"), ("level", "рівень"), ("goals", "цілі")) if profile.get(key))
    user = f"Запит: {prompt}\n"
    if about:
        user += f"Про користувача — {about}.\n"
    user += "Підказка назв вправ за групами м'язів:\n" + exercise_hint(known_exercises)
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


def generate_workout(prompt, profile, known_exercises, chat=None, attempts=3, records=()):
    """Returns a workout draft. `chat` can be replaced in tests; a malformed reply is retried.
    `records` are the user's records (services.records), used to compute weights."""
    chat = chat or default_chat
    messages = build_messages(prompt, profile, known_exercises)
    for attempt in range(attempts):
        try:
            return personalize_weights(sanitize_plan(chat(messages), known_exercises), records)
        except AiUnavailable as e:
            if attempt == attempts - 1 or "Gemini" in e.message or "GEMINI" in e.message:
                raise
