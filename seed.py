"""RepSquad demo data: python3 seed.py  (all passwords: demo12345)"""
import base64
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from backend.services import RepSquad

PASSWORD = "demo12345"
IMAGES = Path(__file__).parent / "backend" / "seed_images"  # demo photos used by the demo posts

USERS = [
    ("olena_fit", "Олена Коваленко", "Кросфіт", "середній", "Підтягнути витривалість і підняти станову до 100 кг", "Тренуюсь 4 рази на тиждень."),
    ("taras_pl", "Тарас Шевчук", "Пауерліфтинг", "просунутий", "Виступити на регіональних змаганнях", "Люблю важкі присідання."),
    ("iryna_run", "Ірина Мельник", "Біг і силові", "початківець", "Пробігти півмарафон", ""),
    ("max_gym", "Максим Бондар", "Бодібілдинг", "середній", "Набір м'язової маси", "Ділюсь програмами тренувань."),
]

# (user, days ago, title, visibility, exercises)
WORKOUTS = [
    ("taras_pl", 21, "Присід + жим", "public", [("Присідання зі штангою", [(5, 120), (5, 130), (3, 140)]), ("Жим лежачи", [(5, 90), (5, 95), (3, 100)])]),
    ("taras_pl", 14, "Станова тяга", "public", [("Станова тяга", [(5, 150), (3, 170), (1, 190)])]),
    ("taras_pl", 7, "Присід + жим", "public", [("Присідання зі штангою", [(5, 125), (5, 135), (3, 145)]), ("Жим лежачи", [(5, 92.5), (5, 97.5), (2, 105)])]),
    ("taras_pl", 3, "Підготовка до змагань", "private", [("Присідання зі штангою", [(2, 160), (1, 170)])]),
    ("olena_fit", 38, "Станова: початок циклу", "public", [("Станова тяга", [(8, 55), (8, 60), (6, 65)])]),
    ("olena_fit", 31, "Станова тяга", "public", [("Станова тяга", [(8, 60), (6, 70), (5, 75)])]),
    ("olena_fit", 24, "Тяга й підтягування", "public", [("Станова тяга", [(8, 65), (6, 75), (5, 80)]), ("Підтягування", [(6, 0), (5, 0), (5, 0)])]),
    ("olena_fit", 10, "Тяга та підтягування", "public", [("Станова тяга", [(8, 70), (6, 80), (5, 85)]), ("Підтягування", [(8, 0), (7, 0), (6, 0)])]),
    ("olena_fit", 4, "Ноги", "public", [("Присідання зі штангою", [(10, 60), (8, 65), (8, 65)]), ("Випади", [(12, 20), (12, 20)])]),
    ("olena_fit", 2, "Особисте: контрольна станова", "private", [("Станова тяга", [(3, 95), (1, 100)])]),
    ("max_gym", 8, "Груди й трицепс", "public", [("Жим лежачи", [(10, 70), (8, 75), (6, 80)]), ("Французький жим", [(12, 30), (10, 35)])]),
    ("max_gym", 5, "Спина й біцепс", "public", [("Тяга верхнього блоку", [(12, 55), (10, 60), (8, 65)]), ("Підйом на біцепс", [(12, 20), (10, 22.5)])]),
    ("max_gym", 1, "Ноги (вдома)", "private", [("Присідання зі штангою", [(12, 80), (10, 90)])]),
    ("iryna_run", 6, "Силова після бігу", "public", [("Присідання зі штангою", [(12, 30), (12, 35)]), ("Планка", [(1, 0)])]),
]


# (user, hours ago, visibility, text, photo file or None); the photos are the images in backend/seed_images
POSTS = [
    ("olena_fit", 3, "public",
     "Прогрес за пів року: спина нарешті почала проявлятися. Ключ — підтягування й тяга верхнього блоку двічі на тиждень та повноцінний сон. Далі — працюю над деталями 💚",
     "090d1c12f690413245bf66d99a96bc84.jpg"),  # back double-biceps pose
    ("max_gym", 6, "public",
     "Тяга гантелі в нахилі — моя улюблена вправа для спини. Лікоть притиснутий до корпуса, піднімаю до пояса й без розгойдування. Сьогодні 3×8 із найважчою гантеллю, яку можу контролювати.",
     "46b302105936daa1d1e054b3719296e6.jpg"),  # one-arm dumbbell row
    ("iryna_run", 11, "public",
     "День тяги: верхній блок 4×12. Навушники, плейлист і нічого зайвого. Силові двічі на тиждень реально допомагають бігу — спина тримається рівніше на довгих дистанціях.",
     "af003aba8f85345a86d2257ea9b381ab.jpg"),  # lat pulldown, headphones
    ("olena_fit", 20, "public",
     "Ягодичний міст зі штангою. Відпочинок між підходами — 90 секунд, а ще додала 5 кг до минулого тижня. Малі кроки, зате щотижня 🍑",
     "bb7decb17c6ba9837f7600e1c7fa09f1.jpg"),  # hip thrust
    ("iryna_run", 27, "public",
     "Підсумок сьогодні: 381 ккал і середній пульс 107. Короткий, але щільний комплекс із гантелями та гирею. Краще 40 хвилин регулярно, ніж 2 години раз на місяць.",
     "c2865d34cc3d900455ec5a5ada88d07b.jpg"),  # smart watch, dumbbells, kettlebell
    ("max_gym", 34, "public",
     "Біцепс: 4×10 з повільною негативною фазою. Без розгойдування корпусом — краще взяти легшу вагу, але зробити чисто. М'яз росте від напруження, а не від інерції.",
     "d09811b643272f8fbe8ae4872c14d9f0.jpg"),  # biceps curl
    ("iryna_run", 48, "public",
     "Вечірня доріжка з видом на захід сонця. Коли за вікном темно чи дощ, біжу в залі — головне, не пропускати тренування. Сьогодні 6 км у легкому темпі.",
     "d8d2625bf88744d2fa7ccde6e4404122.jpg"),  # treadmills at sunset
    ("taras_pl", 56, "public",
     "Жим гантелей на похилій лавці — чудова допоміжна вправа для жиму лежачи. Сьогодні по 22 кг у кожній руці, 4×8. Амплітуда повна, лопатки зведені, лікті під кутом близько 45°.",
     "f299c8afa185261e47a50859958473ae.jpg"),  # incline dumbbell press
    ("olena_fit", 72, "public",
     "Знімаю техніку на відео — так легше помітити помилки. Сьогодні перевіряла положення лопаток у тязі верхнього блоку. Раджу всім спробувати: камера не бреше!",
     "f9b3002f6b1d2c54e7aad29b36870777.jpg"),  # phone on a tripod filming a lat pulldown
    ("taras_pl", 75, "public", "Порада новачкам: не женіться за вагою. Спочатку техніка, потім кілограми. Краще 5×5 з чистою технікою, ніж одне повторення з розхитаною спиною.", None),
    ("iryna_run", 100, "public", "Хто бігає зранку — що ви їсте перед пробіжкою? Я зазвичай обмежуюсь бананом, але на довгих дистанціях не вистачає сил.", None),
    ("max_gym", 140, "private", "Нотатка собі: наступного тижня додати 2,5 кг у жимі й розведення на задню дельту.", None),
]


# (post author, start of the post text, [users who liked it], [(commenter, comment text)])
POST_REACTIONS = [
    ("olena_fit", "Прогрес за пів року", ["taras_pl", "max_gym", "iryna_run"], [
        ("taras_pl", "Відчутний прогрес! Яка схема тренувань на спину?"),
        ("olena_fit", "Дякую! Підтягування та верхній блок двічі на тиждень по 4×10.")]),
    ("max_gym", "Тяга гантелі в нахилі", ["olena_fit", "taras_pl"], [
        ("iryna_run", "Техніка чудова, лікоть справді варто тримати ближче до корпуса.")]),
    ("iryna_run", "День тяги", ["olena_fit"], [
        ("max_gym", "Згоден: сильна спина допомагає бігунам.")]),
    ("taras_pl", "Жим гантелей на похилій лавці", ["max_gym"], [
        ("olena_fit", "Дякую за підказку про кут 45° — спробую на наступному тренуванні.")]),
    ("olena_fit", "Знімаю техніку на відео", ["iryna_run", "taras_pl"], [
        ("iryna_run", "Теж знімаю підходи — так реально видно помилки.")]),
]


def seed_post_reactions(app, ids):
    """Adds the demo likes and comments to the demo posts; every item is checked first, so reruns add nothing."""
    added = 0
    for author, start, likers, comments in POST_REACTIONS:
        post = app._one("SELECT id FROM posts WHERE user_id = ? AND body LIKE ?", (ids[author], start + "%"))
        if not post:
            continue
        for user in likers:
            if not app._one("SELECT 1 FROM post_likes WHERE post_id = ? AND user_id = ?", (post["id"], ids[user])):
                app.toggle_post_like(post["id"], ids[user])
                added += 1
        for user, text in comments:
            if not app._one("SELECT 1 FROM post_comments WHERE post_id = ? AND user_id = ? AND body = ?", (post["id"], ids[user], text)):
                app.add_post_comment(post["id"], ids[user], text)
                added += 1
    return added


def seed_posts(app):
    """Adds the demo posts that are missing (matched by author and text), so it is safe to run repeatedly.
    Nothing happens when the demo users do not exist."""
    ids = {r["username"]: r["id"] for r in app._all("SELECT id, username FROM users")}
    if not all(u[0] in ids for u in USERS):
        return 0
    real_clock, now, added = app.clock, datetime.now(), 0
    try:
        for username, hours_ago, visibility, body, photo in POSTS:
            if app._one("SELECT 1 FROM posts WHERE user_id = ? AND body = ?", (ids[username], body)):
                continue
            app.clock = lambda h=hours_ago: now - timedelta(hours=h)  # spreads the posts over several days
            image = base64.b64encode((IMAGES / photo).read_bytes()).decode() if photo else None
            app.create_post(ids[username], {"body": body, "visibility": visibility, "image": image})
            added += 1
    finally:
        app.clock = real_clock
    seed_post_reactions(app, ids)
    return added


def seed(db_path="repsquad.db"):
    app = RepSquad(db_path)
    if app._one("SELECT 1 FROM users WHERE username = ?", (USERS[0][0],)):
        print("Демо-дані вже завантажено.")
    else:
        seed_core(app)
    added = seed_posts(app)
    if added:
        print(f"Додано демо-дописів: {added}.")


def seed_core(app):
    ids = {}
    for username, name, sport, level, goals, bio in USERS:
        user, _ = app.register(username, PASSWORD, name)
        ids[username] = user["id"]
        app.update_profile(user["id"], {"sport": sport, "level": level, "goals": goals, "bio": bio})
    for follower, followee in [("olena_fit", "taras_pl"), ("olena_fit", "max_gym"), ("iryna_run", "olena_fit"),
                               ("iryna_run", "max_gym"), ("max_gym", "taras_pl"), ("taras_pl", "olena_fit")]:
        app.follow(ids[follower], followee)
    today = date.today()
    for username, days_ago, title, vis, exercises in WORKOUTS:
        app.create_workout(ids[username], {
            "title": title, "date": (today - timedelta(days=days_ago)).isoformat(), "visibility": vis,
            "exercises": [{"name": n, "sets": [{"reps": r, "weight_kg": w} for r, w in sets]} for n, sets in exercises],
        })
    # a few interactions
    wid = app._one("SELECT id FROM workouts WHERE title = 'Присід + жим' ORDER BY date DESC LIMIT 1")["id"]
    for u in ("olena_fit", "max_gym", "iryna_run"):
        app.toggle_like(wid, ids[u])
    app.add_comment(wid, ids["olena_fit"], "Потужно! Яка техніка в присіді — з поясом чи без?")
    app.add_comment(wid, ids["taras_pl"], "Дякую! Пояс лише на підходах від 140 кг.")
    print(f"Створено користувачів: {len(USERS)}, тренувань: {len(WORKOUTS)}. Пароль для всіх: {PASSWORD}")


if __name__ == "__main__":
    seed(sys.argv[1] if len(sys.argv) > 1 else "repsquad.db")
