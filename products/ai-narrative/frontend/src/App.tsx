import { useState } from "react";
import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { AppStateProvider } from "./context/AppStateContext";
import { useAppState } from "./context/AppStateContext";
import OnboardingGuide from "./components/OnboardingGuide";
import ProtectedRoute from "./components/ProtectedRoute";
import Sidebar from "./components/Sidebar";
import LoginView from "./views/LoginView";
import NarrativeView from "./views/NarrativeView";
import BatchView from "./views/BatchView";
import ReferenceLibraryView from "./views/ReferenceLibraryView";
import AnalyticsView from "./views/AnalyticsView";
import SettingsView from "./views/SettingsView";
import AdminView from "./views/AdminView";
import ChatView from "./views/ChatView";
import DocsView from "./views/DocsView";
import StandardsView from "./views/StandardsView";
import "./App.css";

// NarrativeView and BatchView stay mounted so their form state
// (uploaded file, results, selections) is preserved when switching tabs.
function PersistentViews() {
  const { pathname } = useLocation();
  const show = (path: string): React.CSSProperties =>
    pathname === path ? { height: "100%" } : { display: "none" };
  return (
    <>
      <div style={show("/score")}><NarrativeView /></div>
      <div style={show("/batch")}><BatchView /></div>
    </>
  );
}

function AppLayout() {
  const { user } = useAppState();
  const sessionSkipped = sessionStorage.getItem("onboarding_skipped") === "1";
  const [skipped, setSkipped] = useState(sessionSkipped);
  const showOnboarding = !!user && !user.onboarding_completed && !skipped;

  const handleSkip = () => {
    sessionStorage.setItem("onboarding_skipped", "1");
    setSkipped(true);
  };

  return (
    <div className="app-container">
      <Sidebar />
      <main className="main-content">
        <PersistentViews />
        <Routes>
          <Route path="/" element={<Navigate to="/score" replace />} />
          <Route path="/score" element={null} />
          <Route path="/batch" element={null} />
          <Route path="/chat" element={<ChatView />} />
          <Route path="/references" element={<ReferenceLibraryView />} />
          <Route path="/analytics" element={<AnalyticsView />} />
          <Route path="/settings" element={<SettingsView />} />
          <Route path="/docs" element={<DocsView />} />
          <Route path="/standards" element={<StandardsView />} />
          <Route path="/admin" element={<AdminView />} />
          <Route path="*" element={<Navigate to="/score" replace />} />
        </Routes>
      </main>
      {showOnboarding && <OnboardingGuide onDismiss={handleSkip} />}
    </div>
  );
}

export default function App() {
  return (
    <AppStateProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginView />} />
          <Route
            path="/*"
            element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }
          />
        </Routes>
      </BrowserRouter>
    </AppStateProvider>
  );
}