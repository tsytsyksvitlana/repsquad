"""RepSquad business logic: accounts, workouts, privacy, follows, reactions, records."""
import functools
import hashlib
import hmac
import secrets
import threading
from datetime import datetime, timedelta

from . import validation as v
from .db import connect
from .errors import Conflict, Forbidden, NotFound, Unauthorized, ValidationError
from .privacy import VISIBLE_SQL, can_view

SESSION_TTL = timedelta(days=30)
PAGE_MAX = 50
KINDS = ("all", "workouts", "posts")

EXERCISE_CATALOG = [
    "Жим лежачи", "Жим гантелей лежачи", "Жим стоячи", "Присідання зі штангою", "Болгарські присідання", "Фронтальні присідання",
    "Станова тяга", "Румунська тяга", "Тяга штанги в нахилі", "Підтягування", "Віджимання на брусах",
    "Віджимання від підлоги", "Тяга верхнього блоку", "Тяга нижнього блоку", "Підйом на біцепс",
    "Французький жим", "Розведення гантелей", "Випади", "Жим ногами", "Підйом на носки", "Планка",
    "Скручування", "Махи гирею", "Гіперекстензія", "Ривок штанги", "Поштовх штанги",
]


def est_1rm(weight, reps):
    """Estimated one-rep max using the Epley formula."""
    if weight <= 0:
        return 0.0
    return round(weight if reps == 1 else weight * (1 + reps / 30), 1)


def locked(fn):
    @functools.wraps(fn)
    def wrapper(self, *args, **kwargs):
        with self.lock:
            return fn(self, *args, **kwargs)
    return wrapper


def _limit_offset(limit, offset):
    try:
        limit = int(limit if limit is not None else 20)
        offset = int(offset if offset is not None else 0)
    except (TypeError, ValueError):
        raise ValidationError("limit і offset мають бути числами") from None
    return max(1, min(limit, PAGE_MAX)), max(0, offset)


class RepSquad:
    def __init__(self, path=":memory:", *, clock=None, pbkdf2_iterations=200_000):
        self.conn = connect(path)
        self.lock = threading.RLock()
        self.clock = clock or datetime.now
        self.iterations = pbkdf2_iterations

    # ---------- helpers ----------
    def now(self):
        return self.clock().replace(microsecond=0)

    def _hash(self, password, salt_hex):
        return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), self.iterations).hex()

    @staticmethod
    def _token_hash(token):
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _one(self, sql, params=()):
        return self.conn.execute(sql, params).fetchone()

    def _all(self, sql, params=()):
        return self.conn.execute(sql, params).fetchall()

    # ---------- REQ-1: accounts ----------
    def _new_session(self, user_id):
        token = secrets.token_urlsafe(32)
        self.conn.execute("INSERT INTO sessions(token_hash, user_id, created_at) VALUES (?,?,?)",
                          (self._token_hash(token), user_id, self.now().isoformat()))
        return token

    @locked
    def register(self, username, password, display_name=None):
        username = v.validate_username(username)
        v.validate_password(password)
        name = v.clean_text(display_name if display_name else username, "Ім'я", max_len=40, required=True)
        if self._one("SELECT 1 FROM users WHERE username = ?", (username,)):
            raise Conflict("Цей логін уже зайнятий")
        salt = secrets.token_hex(16)
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO users(username, password_hash, salt, display_name, created_at) VALUES (?,?,?,?,?)",
                (username, self._hash(password, salt), salt, name, self.now().isoformat()))
            token = self._new_session(cur.lastrowid)
        return self.get_profile(username, cur.lastrowid), token

    @locked
    def login(self, username, password):
        row = self._one("SELECT * FROM users WHERE username = ?", (username if isinstance(username, str) else "",))
        salt = row["salt"] if row else "00" * 16
        candidate = self._hash(password if isinstance(password, str) else "", salt)
        if not row or not hmac.compare_digest(candidate, row["password_hash"]):
            raise Unauthorized("Невірний логін або пароль")
        with self.conn:
            token = self._new_session(row["id"])
        return self.get_profile(row["username"], row["id"]), token

    @locked
    def logout(self, token):
        with self.conn:
            self.conn.execute("DELETE FROM sessions WHERE token_hash = ?", (self._token_hash(token or ""),))

    @locked
    def authenticate(self, token):
        """Returns the user id for a token or raises Unauthorized."""
        if not token:
            raise Unauthorized("Потрібна авторизація")
        row = self._one("SELECT user_id, created_at FROM sessions WHERE token_hash = ?", (self._token_hash(token),))
        if not row or self.now() - datetime.fromisoformat(row["created_at"]) > SESSION_TTL:
            raise Unauthorized("Сесія недійсна або завершилась")
        return row["user_id"]

    # ---------- profile ----------
    def _user_row(self, username):
        row = self._one("SELECT * FROM users WHERE username = ?", (username,))
        if not row:
            raise NotFound("Користувача не знайдено")
        return row

    @staticmethod
    def _avatar_url(username, version):
        """Versioned URL, so browsers can cache the picture forever and still see changes."""
        return f"/api/users/{username}/avatar?v={version}" if version else None

    def _user_view(self, row, viewer_id):
        uid = row["id"]
        avatar = self._one("SELECT version FROM user_avatars WHERE user_id = ?", (uid,))
        visible = self._one(
            f"SELECT COUNT(*) AS n FROM workouts w WHERE w.user_id = :uid AND {VISIBLE_SQL}",
            {"uid": uid, "viewer": viewer_id})["n"]
        return {
            "id": uid, "username": row["username"], "display_name": row["display_name"],
            "sport": row["sport"], "level": row["level"], "goals": row["goals"], "bio": row["bio"],
            "created_at": row["created_at"],
            "avatar_url": self._avatar_url(row["username"], avatar["version"] if avatar else 0),
            "followers": self._one("SELECT COUNT(*) AS n FROM follows WHERE followee_id = ?", (uid,))["n"],
            "following": self._one("SELECT COUNT(*) AS n FROM follows WHERE follower_id = ?", (uid,))["n"],
            "workouts": visible,
            "posts": self._one(f"SELECT COUNT(*) AS n FROM posts w WHERE w.user_id = :uid AND {VISIBLE_SQL}",
                               {"uid": uid, "viewer": viewer_id})["n"],
            "is_me": uid == viewer_id,
            "followed_by_me": bool(viewer_id and self._one(
                "SELECT 1 FROM follows WHERE follower_id = ? AND followee_id = ?", (viewer_id, uid))),
        }

    @locked
    def get_profile(self, username, viewer_id):
        return self._user_view(self._user_row(username), viewer_id)

    @locked
    def update_profile(self, user_id, data):
        fields = v.validate_profile(data)
        if fields:
            sets = ", ".join(f"{k} = :{k}" for k in fields)
            with self.conn:
                self.conn.execute(f"UPDATE users SET {sets} WHERE id = :id", {**fields, "id": user_id})
        row = self._one("SELECT * FROM users WHERE id = ?", (user_id,))
        return self._user_view(row, user_id)

    @locked
    def set_avatar(self, user_id, image):
        mime, data = v.validate_avatar(image)
        previous = self._one("SELECT version FROM user_avatars WHERE user_id = ?", (user_id,))
        with self.conn:
            self.conn.execute(
                "INSERT INTO user_avatars(user_id, mime, data, version) VALUES (?,?,?,?) "
                "ON CONFLICT(user_id) DO UPDATE SET mime = excluded.mime, data = excluded.data, version = excluded.version",
                (user_id, mime, data, (previous["version"] if previous else 0) + 1))
        return self._user_view(self._one("SELECT * FROM users WHERE id = ?", (user_id,)), user_id)

    @locked
    def delete_avatar(self, user_id):
        with self.conn:
            self.conn.execute("DELETE FROM user_avatars WHERE user_id = ?", (user_id,))
        return self._user_view(self._one("SELECT * FROM users WHERE id = ?", (user_id,)), user_id)

    @locked
    def get_avatar(self, username):
        """(mime, bytes) of a user's picture; avatars are public like names, so no viewer is needed."""
        row = self._one("SELECT a.mime, a.data FROM user_avatars a JOIN users u ON u.id = a.user_id WHERE u.username = ?", (username,))
        if not row:
            raise NotFound("Фото не знайдено")
        return row["mime"], bytes(row["data"])

    @locked
    def search_users(self, q, viewer_id, limit=20):
        q = (q or "").strip()
        limit, _ = _limit_offset(limit, 0)
        like = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        rows = self._all(
            "SELECT * FROM users WHERE username LIKE :q ESCAPE '\\' OR display_name LIKE :q ESCAPE '\\' "
            "ORDER BY username LIMIT :n", {"q": like, "n": limit})
        return [self._user_view(r, viewer_id) for r in rows]

    # ---------- REQ-4: follows ----------
    @locked
    def follow(self, user_id, username):
        target = self._user_row(username)
        if target["id"] == user_id:
            raise ValidationError("Не можна підписатись на самого себе")
        with self.conn:
            self.conn.execute("INSERT OR IGNORE INTO follows(follower_id, followee_id, created_at) VALUES (?,?,?)",
                              (user_id, target["id"], self.now().isoformat()))
        return self._user_view(target, user_id)

    @locked
    def unfollow(self, user_id, username):
        target = self._user_row(username)
        with self.conn:
            self.conn.execute("DELETE FROM follows WHERE follower_id = ? AND followee_id = ?", (user_id, target["id"]))
        return self._user_view(target, user_id)

    # ---------- REQ-2, 3: workouts ----------
    _BASE = ("SELECT w.id, w.user_id, w.title, w.date, w.visibility, w.notes, w.created_at, "
             "u.username, u.display_name, (SELECT version FROM user_avatars a WHERE a.user_id = u.id) AS avatar_v "
             "FROM workouts w JOIN users u ON u.id = w.user_id")

    def _views(self, rows, viewer_id):
        """Turns workouts rows into full views (4 queries for a whole page)."""
        if not rows:
            return []
        ids = [r["id"] for r in rows]
        marks = ",".join("?" * len(ids))
        exercises = {}
        for e in self._all(f"SELECT * FROM workout_exercises WHERE workout_id IN ({marks}) ORDER BY position", ids):
            exercises.setdefault(e["workout_id"], []).append({"id": e["id"], "name": e["name"], "sets": []})
        by_we = {e["id"]: e for lst in exercises.values() for e in lst}
        if by_we:
            wmarks = ",".join("?" * len(by_we))
            for s in self._all(f"SELECT * FROM sets WHERE workout_exercise_id IN ({wmarks}) ORDER BY position",
                               list(by_we)):
                by_we[s["workout_exercise_id"]]["sets"].append({"reps": s["reps"], "weight_kg": s["weight_kg"]})
        likes = {r["workout_id"]: r["n"] for r in self._all(
            f"SELECT workout_id, COUNT(*) AS n FROM likes WHERE workout_id IN ({marks}) GROUP BY workout_id", ids)}
        mine = {r["workout_id"] for r in self._all(
            f"SELECT workout_id FROM likes WHERE user_id = ? AND workout_id IN ({marks})", [viewer_id, *ids])}
        comments = {r["workout_id"]: r["n"] for r in self._all(
            f"SELECT workout_id, COUNT(*) AS n FROM comments WHERE workout_id IN ({marks}) GROUP BY workout_id", ids)}
        views = []
        for r in rows:
            exs = exercises.get(r["id"], [])
            for e in exs:
                e.pop("id")
            all_sets = [s for e in exs for s in e["sets"]]
            views.append({
                "type": "workout", "id": r["id"], "title": r["title"], "date": r["date"], "visibility": r["visibility"],
                "notes": r["notes"], "created_at": r["created_at"],
                "author": {"username": r["username"], "display_name": r["display_name"],
                           "avatar_url": self._avatar_url(r["username"], r["avatar_v"])},
                "is_mine": r["user_id"] == viewer_id,
                "exercises": exs,
                "sets_count": len(all_sets),
                "volume_kg": round(sum(s["reps"] * s["weight_kg"] for s in all_sets), 1),
                "likes": likes.get(r["id"], 0),
                "liked_by_me": r["id"] in mine,
                "comments_count": comments.get(r["id"], 0),
            })
        return views

    def _visible_row(self, workout_id, viewer_id):
        """The workout row if the viewer may see it; otherwise NotFound (existence is not revealed)."""
        row = self._one(self._BASE + " WHERE w.id = ?", (workout_id,))
        if not row or not can_view(row["user_id"], row["visibility"], viewer_id):
            raise NotFound("Тренування не знайдено")
        return row

    def _previous_max(self, user_id):
        rows = self._all(
            "SELECT e.name_key, MAX(s.weight_kg) AS w FROM workout_exercises e "
            "JOIN workouts w ON w.id = e.workout_id JOIN sets s ON s.workout_exercise_id = e.id "
            "WHERE w.user_id = ? GROUP BY e.name_key", (user_id,))
        return {r["name_key"]: r["w"] for r in rows}

    @locked
    def create_workout(self, user_id, data):
        clean = v.validate_workout(data, self.now().date())
        before = self._previous_max(user_id)
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO workouts(user_id, title, date, visibility, notes, created_at) VALUES (?,?,?,?,?,?)",
                (user_id, clean["title"], clean["date"], clean["visibility"], clean["notes"], self.now().isoformat()))
            wid = cur.lastrowid
            for pos, ex in enumerate(clean["exercises"]):
                ecur = self.conn.execute(
                    "INSERT INTO workout_exercises(workout_id, position, name, name_key) VALUES (?,?,?,?)",
                    (wid, pos, ex["name"], ex["name"].casefold()))
                for spos, s in enumerate(ex["sets"]):
                    self.conn.execute("INSERT INTO sets(workout_exercise_id, position, reps, weight_kg) VALUES (?,?,?,?)",
                                      (ecur.lastrowid, spos, s["reps"], s["weight_kg"]))
        records = []
        for ex in clean["exercises"]:
            best = max(ex["sets"], key=lambda s: (s["weight_kg"], s["reps"]))
            prev = before.get(ex["name"].casefold())
            if prev is not None and best["weight_kg"] > prev and not any(r["exercise"] == ex["name"] for r in records):
                records.append({"exercise": ex["name"], "weight_kg": best["weight_kg"], "reps": best["reps"],
                                "previous_kg": prev})
        return self._views([self._visible_row(wid, user_id)], user_id)[0], records

    @locked
    def get_workout(self, workout_id, viewer_id):
        row = self._visible_row(workout_id, viewer_id)
        view = self._views([row], viewer_id)[0]
        view["comments"] = self._comments(workout_id, viewer_id, row["user_id"])
        return view

    def _owned_row(self, workout_id, user_id):
        row = self._visible_row(workout_id, user_id)
        if row["user_id"] != user_id:
            raise Forbidden("Це тренування належить іншому користувачу")
        return row

    @locked
    def update_workout(self, workout_id, user_id, data):
        self._owned_row(workout_id, user_id)
        fields = {}
        if "title" in data:
            fields["title"] = v.clean_text(data["title"], "Назва", max_len=60, required=True)
        if "notes" in data:
            fields["notes"] = v.clean_text(data["notes"], "Нотатки", max_len=500)
        if "visibility" in data:
            fields["visibility"] = v.validate_visibility(data["visibility"])
        if "date" in data:
            fields["date"] = v.validate_date(data["date"], self.now().date())
        if fields:
            sets = ", ".join(f"{k} = :{k}" for k in fields)
            with self.conn:
                self.conn.execute(f"UPDATE workouts SET {sets} WHERE id = :id", {**fields, "id": workout_id})
        return self.get_workout(workout_id, user_id)

    @locked
    def delete_workout(self, workout_id, user_id):
        self._owned_row(workout_id, user_id)
        with self.conn:
            self.conn.execute("DELETE FROM workouts WHERE id = ?", (workout_id,))

    def _page(self, where, params, viewer_id, limit, offset, kind="workouts", where_posts=None):
        """One page of the timeline: workouts, posts or both, newest first.

        `where` may only use columns that both tables share under the alias "w" (user_id, visibility);
        `where_posts` overrides it for posts when the two kinds need different rules."""
        if kind not in KINDS:
            raise ValidationError("Невірний тип: all, workouts або posts")
        limit, offset = _limit_offset(limit, offset)
        args = {**params, "viewer": viewer_id, "n": offset + limit + 1}
        tagged = []  # (sort key, kind, row)
        if kind in ("all", "workouts"):
            for r in self._all(f"{self._BASE} WHERE {where} AND {VISIBLE_SQL} "
                               "ORDER BY w.date DESC, w.created_at DESC, w.id DESC LIMIT :n", args):
                tagged.append(((r["date"], r["created_at"], r["id"]), "workout", r))
        if kind in ("all", "posts"):
            for r in self._all(f"{self._POST_BASE} WHERE {where_posts or where} AND {VISIBLE_SQL} "
                               "ORDER BY w.created_at DESC, w.id DESC LIMIT :n", args):
                tagged.append(((r["created_at"][:10], r["created_at"], r["id"]), "post", r))
        tagged.sort(key=lambda t: t[0], reverse=True)
        chosen = tagged[offset:offset + limit]
        # views are built only for the rows that actually made it onto the page
        workouts = {x["id"]: x for x in self._views([r for _, k, r in chosen if k == "workout"], viewer_id)}
        posts = {x["id"]: x for x in self._post_views([r for _, k, r in chosen if k == "post"], viewer_id)}
        return {"items": [(workouts if k == "workout" else posts)[r["id"]] for _, k, r in chosen],
                "has_more": len(tagged) > offset + limit}

    @locked
    def user_workouts(self, username, viewer_id, limit=20, offset=0, visibility=None, kind="workouts"):
        target = self._user_row(username)
        where, params = "w.user_id = :uid", {"uid": target["id"]}
        if visibility:
            where += " AND w.visibility = :vis"
            params["vis"] = v.validate_visibility(visibility)
        return self._page(where, params, viewer_id, limit, offset, kind)

    @locked
    def feed(self, viewer_id, limit=20, offset=0, kind="workouts"):
        """Items of the people the user follows. Own posts are included too, so a fresh post shows up right away;
        own workouts are not (they live under "My workouts")."""
        followed = "w.user_id IN (SELECT followee_id FROM follows WHERE follower_id = :me)"
        return self._page(followed, {"me": viewer_id}, viewer_id, limit, offset, kind,
                          where_posts=f"({followed} OR w.user_id = :me)")

    @locked
    def discover(self, viewer_id, limit=20, offset=0, kind="workouts"):
        """All public items (for discovering new people)."""
        return self._page("w.visibility = 'public'", {}, viewer_id, limit, offset, kind)

    # ---------- posts ----------
    _POST_BASE = ("SELECT w.id, w.user_id, w.body, w.visibility, w.created_at, u.username, u.display_name, "
                  "(SELECT version FROM user_avatars a WHERE a.user_id = u.id) AS avatar_v, "
                  "EXISTS(SELECT 1 FROM post_images i WHERE i.post_id = w.id) AS has_image "
                  "FROM posts w JOIN users u ON u.id = w.user_id")

    def _post_views(self, rows, viewer_id):
        if not rows:
            return []
        ids = [r["id"] for r in rows]
        marks = ",".join("?" * len(ids))
        likes = {r["post_id"]: r["n"] for r in self._all(
            f"SELECT post_id, COUNT(*) AS n FROM post_likes WHERE post_id IN ({marks}) GROUP BY post_id", ids)}
        mine = {r["post_id"] for r in self._all(
            f"SELECT post_id FROM post_likes WHERE user_id = ? AND post_id IN ({marks})", [viewer_id, *ids])}
        comments = {r["post_id"]: r["n"] for r in self._all(
            f"SELECT post_id, COUNT(*) AS n FROM post_comments WHERE post_id IN ({marks}) GROUP BY post_id", ids)}
        return [{
            "type": "post", "id": r["id"], "body": r["body"], "visibility": r["visibility"], "created_at": r["created_at"],
            "author": {"username": r["username"], "display_name": r["display_name"],
                       "avatar_url": self._avatar_url(r["username"], r["avatar_v"])},
            "is_mine": r["user_id"] == viewer_id,
            "image_url": f"/api/posts/{r['id']}/image" if r["has_image"] else None,
            "likes": likes.get(r["id"], 0), "liked_by_me": r["id"] in mine, "comments_count": comments.get(r["id"], 0),
        } for r in rows]

    def _visible_post(self, post_id, viewer_id):
        """The post row if the viewer may see it; otherwise NotFound (existence is not revealed)."""
        row = self._one(self._POST_BASE + " WHERE w.id = ?", (post_id,))
        if not row or not can_view(row["user_id"], row["visibility"], viewer_id):
            raise NotFound("Допис не знайдено")
        return row

    def _owned_post(self, post_id, user_id):
        row = self._visible_post(post_id, user_id)
        if row["user_id"] != user_id:
            raise Forbidden("Цей допис належить іншому користувачу")
        return row

    @locked
    def get_post(self, post_id, viewer_id):
        row = self._visible_post(post_id, viewer_id)
        view = self._post_views([row], viewer_id)[0]
        view["comments"] = self._post_comments(post_id, viewer_id, row["user_id"])
        return view

    @locked
    def toggle_post_like(self, post_id, user_id):
        self._visible_post(post_id, user_id)
        with self.conn:
            deleted = self.conn.execute("DELETE FROM post_likes WHERE user_id = ? AND post_id = ?", (user_id, post_id)).rowcount
            if not deleted:
                self.conn.execute("INSERT INTO post_likes(user_id, post_id) VALUES (?,?)", (user_id, post_id))
        n = self._one("SELECT COUNT(*) AS n FROM post_likes WHERE post_id = ?", (post_id,))["n"]
        return {"liked": not deleted, "likes": n}

    def _post_comments(self, post_id, viewer_id, owner_id):
        rows = self._all(
            "SELECT c.id, c.user_id, c.body, c.created_at, u.username, u.display_name, "
            "(SELECT version FROM user_avatars a WHERE a.user_id = u.id) AS avatar_v FROM post_comments c "
            "JOIN users u ON u.id = c.user_id WHERE c.post_id = ? ORDER BY c.id", (post_id,))
        return [{"id": r["id"], "body": r["body"], "created_at": r["created_at"],
                 "author": {"username": r["username"], "display_name": r["display_name"],
                            "avatar_url": self._avatar_url(r["username"], r["avatar_v"])},
                 "can_delete": viewer_id in (r["user_id"], owner_id)} for r in rows]

    @locked
    def add_post_comment(self, post_id, user_id, body):
        row = self._visible_post(post_id, user_id)
        body = v.clean_text(body, "Коментар", max_len=v.MAX_COMMENT, required=True)
        with self.conn:
            self.conn.execute("INSERT INTO post_comments(post_id, user_id, body, created_at) VALUES (?,?,?,?)",
                              (post_id, user_id, body, self.now().isoformat()))
        return self._post_comments(post_id, user_id, row["user_id"])

    @locked
    def delete_post_comment(self, comment_id, user_id):
        c = self._one("SELECT id, user_id, post_id FROM post_comments WHERE id = ?", (comment_id,))
        if not c:
            raise NotFound("Коментар не знайдено")
        row = self._visible_post(c["post_id"], user_id)
        if user_id not in (c["user_id"], row["user_id"]):
            raise Forbidden("Видалити коментар може лише його автор або автор допису")
        with self.conn:
            self.conn.execute("DELETE FROM post_comments WHERE id = ?", (comment_id,))
        return self._post_comments(c["post_id"], user_id, row["user_id"])

    @locked
    def create_post(self, user_id, data):
        clean = v.validate_post(data)
        with self.conn:
            cur = self.conn.execute("INSERT INTO posts(user_id, body, visibility, created_at) VALUES (?,?,?,?)",
                                    (user_id, clean["body"], clean["visibility"], self.now().isoformat()))
            if clean["image"]:
                self.conn.execute("INSERT INTO post_images(post_id, mime, data) VALUES (?,?,?)",
                                  (cur.lastrowid, *clean["image"]))
        return self._post_views([self._visible_post(cur.lastrowid, user_id)], user_id)[0]

    @locked
    def update_post(self, post_id, user_id, data):
        row = self._owned_post(post_id, user_id)
        fields = {}
        if "body" in data:
            fields["body"] = v.clean_text(data["body"], "Допис", max_len=v.MAX_POST, required=not row["has_image"])
        if "visibility" in data:
            fields["visibility"] = v.validate_visibility(data["visibility"])
        if fields:
            sets = ", ".join(f"{k} = :{k}" for k in fields)
            with self.conn:
                self.conn.execute(f"UPDATE posts SET {sets} WHERE id = :id", {**fields, "id": post_id})
        return self._post_views([self._visible_post(post_id, user_id)], user_id)[0]

    @locked
    def delete_post(self, post_id, user_id):
        self._owned_post(post_id, user_id)
        with self.conn:
            self.conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))

    @locked
    def get_post_image(self, post_id, viewer_id):
        """(mime, bytes) of a post picture; it obeys the post's visibility."""
        self._visible_post(post_id, viewer_id)
        row = self._one("SELECT mime, data FROM post_images WHERE post_id = ?", (post_id,))
        if not row:
            raise NotFound("Фото не знайдено")
        return row["mime"], bytes(row["data"])

    # ---------- REQ-6: likes and comments ----------
    @locked
    def toggle_like(self, workout_id, user_id):
        self._visible_row(workout_id, user_id)
        with self.conn:
            deleted = self.conn.execute("DELETE FROM likes WHERE user_id = ? AND workout_id = ?",
                                        (user_id, workout_id)).rowcount
            if not deleted:
                self.conn.execute("INSERT INTO likes(user_id, workout_id) VALUES (?,?)", (user_id, workout_id))
        n = self._one("SELECT COUNT(*) AS n FROM likes WHERE workout_id = ?", (workout_id,))["n"]
        return {"liked": not deleted, "likes": n}

    def _comments(self, workout_id, viewer_id, owner_id):
        rows = self._all(
            "SELECT c.id, c.user_id, c.body, c.created_at, u.username, u.display_name, "
            "(SELECT version FROM user_avatars a WHERE a.user_id = u.id) AS avatar_v FROM comments c "
            "JOIN users u ON u.id = c.user_id WHERE c.workout_id = ? ORDER BY c.id", (workout_id,))
        return [{"id": r["id"], "body": r["body"], "created_at": r["created_at"],
                 "author": {"username": r["username"], "display_name": r["display_name"],
                            "avatar_url": self._avatar_url(r["username"], r["avatar_v"])},
                 "can_delete": viewer_id in (r["user_id"], owner_id)} for r in rows]

    @locked
    def add_comment(self, workout_id, user_id, body):
        row = self._visible_row(workout_id, user_id)
        body = v.clean_text(body, "Коментар", max_len=v.MAX_COMMENT, required=True)
        with self.conn:
            self.conn.execute("INSERT INTO comments(workout_id, user_id, body, created_at) VALUES (?,?,?,?)",
                              (workout_id, user_id, body, self.now().isoformat()))
        return self._comments(workout_id, user_id, row["user_id"])

    @locked
    def delete_comment(self, comment_id, user_id):
        c = self._one("SELECT c.id, c.user_id, c.workout_id FROM comments c WHERE c.id = ?", (comment_id,))
        if not c:
            raise NotFound("Коментар не знайдено")
        row = self._visible_row(c["workout_id"], user_id)
        if user_id not in (c["user_id"], row["user_id"]):
            raise Forbidden("Видалити коментар може лише його автор або автор тренування")
        with self.conn:
            self.conn.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
        return self._comments(c["workout_id"], user_id, row["user_id"])

    # ---------- REQ-9: records and progress ----------
    def _set_rows(self, user_id):
        return self._all(
            "SELECT e.name, e.name_key, w.id AS workout_id, w.date, s.reps, s.weight_kg FROM sets s "
            "JOIN workout_exercises e ON e.id = s.workout_exercise_id JOIN workouts w ON w.id = e.workout_id "
            "WHERE w.user_id = ? ORDER BY w.date, w.id", (user_id,))

    @locked
    def records(self, user_id):
        best = {}
        for r in self._set_rows(user_id):
            b = best.setdefault(r["name_key"], {
                "exercise": r["name"], "max_weight_kg": 0.0, "max_weight_reps": 0, "max_weight_date": None,
                "best_1rm": 0.0, "max_reps": 0, "workouts": set()})
            b["workouts"].add(r["workout_id"])
            if (r["weight_kg"], r["reps"]) > (b["max_weight_kg"], b["max_weight_reps"]):
                b["max_weight_kg"], b["max_weight_reps"], b["max_weight_date"] = r["weight_kg"], r["reps"], r["date"]
            b["best_1rm"] = max(b["best_1rm"], est_1rm(r["weight_kg"], r["reps"]))
            b["max_reps"] = max(b["max_reps"], r["reps"])
        out = []
        for b in best.values():
            b["workouts"] = len(b["workouts"])
            b["bodyweight"] = b["max_weight_kg"] == 0
            out.append(b)
        return sorted(out, key=lambda b: b["exercise"].casefold())

    @locked
    def progress(self, user_id, exercise):
        key = v.normalize_exercise_name(exercise or "").casefold()
        if not key:
            raise ValidationError("Вкажіть вправу")
        per = {}
        name = None
        for r in self._set_rows(user_id):
            if r["name_key"] != key:
                continue
            name = r["name"]
            p = per.setdefault(r["workout_id"], {"date": r["date"], "max_weight_kg": 0.0, "best_1rm": 0.0,
                                                 "max_reps": 0, "volume_kg": 0.0})
            p["max_weight_kg"] = max(p["max_weight_kg"], r["weight_kg"])
            p["best_1rm"] = max(p["best_1rm"], est_1rm(r["weight_kg"], r["reps"]))
            p["max_reps"] = max(p["max_reps"], r["reps"])
            p["volume_kg"] = round(p["volume_kg"] + r["reps"] * r["weight_kg"], 1)
        if not per:
            raise NotFound("Немає даних для цієї вправи")
        return {"exercise": name, "points": sorted(per.values(), key=lambda p: p["date"])}

    @locked
    def exercise_names(self, user_id):
        own = [r["name"] for r in self._all(
            "SELECT e.name FROM workout_exercises e JOIN workouts w ON w.id = e.workout_id WHERE w.user_id = ? "
            "GROUP BY e.name_key ORDER BY COUNT(*) DESC", (user_id,))]
        seen = {n.casefold() for n in own}
        return own + [n for n in EXERCISE_CATALOG if n.casefold() not in seen]

    # ---------- AI ----------
    @locked
    def profile_for_ai(self, user_id):
        row = self._one("SELECT sport, level, goals FROM users WHERE id = ?", (user_id,))
        return dict(row)
