// Constants that used to be scattered through the components as magic numbers and strings.

export const PAGE_SIZE = 10;
export const SEARCH_DEBOUNCE_MS = 250;
export const TOAST_MS = { ok: 3200, err: 6000, pr: 6000 };

export const IMAGE = {
  accept: "image/jpeg,image/png,image/webp",
  avatarSize: 256,
  postMaxSide: 1080,
  jpegQuality: 0.85,
};

/** "All / Workouts / Posts" switch used above lists. */
export const KIND_OPTIONS = [["all", "Усе"], ["workouts", "Тренування"], ["posts", "Дописи"]];

/** Per-kind API path and user-facing messages; lets workouts and posts share likes and owner actions. */
export const ITEM_KINDS = {
  workout: {
    path: "/api/workouts",
    madePrivate: "Тренування тепер приватне",
    madePublic: "Тренування тепер публічне",
    deleted: "Тренування видалено",
    confirmDelete: "Видалити тренування без можливості відновлення?",
  },
  post: {
    path: "/api/posts",
    madePrivate: "Допис тепер приватний",
    madePublic: "Допис тепер публічний",
    deleted: "Допис видалено",
    confirmDelete: "Видалити допис без можливості відновлення?",
  },
};
