"""The single content privacy rule (REQ-3, REQ-13), shared by workouts and posts.

Private content is visible only to its author. Public content is visible to every signed-in user.
The rule exists in two equivalent forms that are always used together:
  * can_view()      - check for a single workout in code;
  * VISIBLE_SQL     - an SQL fragment for any query (feed, profile, search...).
The tests verify that both forms give the same result.
"""

PUBLIC = "public"
PRIVATE = "private"
VISIBILITIES = (PUBLIC, PRIVATE)

# The content table (workouts or posts) is aliased "w" in queries; the parameter is :viewer (user id or NULL).
VISIBLE_SQL = "(w.visibility = 'public' OR w.user_id = :viewer)"


def can_view(owner_id, visibility, viewer_id) -> bool:
    if visibility == PUBLIC:
        return True
    return viewer_id is not None and viewer_id == owner_id
