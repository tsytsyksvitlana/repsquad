import { createContext, useContext, useMemo, useRef } from "react";

const DraftContext = createContext(null);

/** Carries a workout draft (e.g. from the AI trainer) to the "new workout" form. */
export function DraftProvider({ children }) {
  const ref = useRef(null);
  const value = useMemo(() => ({
    setDraft: (draft) => { ref.current = draft; },
    peekDraft: () => ref.current, // pure read, safe to call while rendering
    clearDraft: () => { ref.current = null; },
  }), []);
  return <DraftContext.Provider value={value}>{children}</DraftContext.Provider>;
}

export const useDraft = () => useContext(DraftContext);
