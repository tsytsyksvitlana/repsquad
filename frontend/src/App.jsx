import { useEffect } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./context/AuthContext.jsx";
import Topbar from "./components/Topbar.jsx";
import { Loading } from "./components/common.jsx";
import AuthPage from "./pages/AuthPage.jsx";
import { DiscoverPage, FeedPage, MinePage } from "./pages/ListPages.jsx";
import PeoplePage from "./pages/PeoplePage.jsx";
import NewWorkoutPage from "./pages/NewWorkoutPage.jsx";
import AiPage from "./pages/AiPage.jsx";
import WorkoutPage from "./pages/WorkoutPage.jsx";
import ProfilePage from "./pages/ProfilePage.jsx";
import RecordsPage from "./pages/RecordsPage.jsx";

export default function App() {
  const { status } = useAuth();
  const { pathname } = useLocation();

  // Every navigation starts at the top of the page.
  useEffect(() => { window.scrollTo(0, 0); }, [pathname]);

  if (status === "loading") return <main><Loading /></main>;
  if (status === "anon") return <main><AuthPage /></main>;
  return (
    <>
      <Topbar />
      <main>
        <Routes>
          <Route path="/feed" element={<FeedPage />} />
          <Route path="/discover" element={<DiscoverPage />} />
          <Route path="/search" element={<PeoplePage />} />
          <Route path="/new" element={<NewWorkoutPage />} />
          <Route path="/ai" element={<AiPage />} />
          <Route path="/mine" element={<MinePage />} />
          <Route path="/records" element={<RecordsPage />} />
          <Route path="/w/:id" element={<WorkoutPage />} />
          <Route path="/u/:username" element={<ProfilePage />} />
          <Route path="*" element={<Navigate to="/feed" replace />} />
        </Routes>
      </main>
    </>
  );
}
