import { Navigate, Route, Routes } from "react-router-dom";

import ProtectedRoute from "./components/ProtectedRoute";
import Sidebar from "./components/Sidebar";
import { AppStateProvider } from "./context/AppStateContext";
import AdminView from "./views/AdminView";
import AnalyticsView from "./views/AnalyticsView";
import BatchValidateView from "./views/BatchValidateView";
import ChatView from "./views/ChatView";
import ClauseLibraryView from "./views/ClauseLibraryView";
import CompareView from "./views/CompareView";
import ExtractView from "./views/ExtractView";
import LoginView from "./views/LoginView";
import OutputsView from "./views/OutputsView";
import SettingsView from "./views/SettingsView";
import StudioView from "./views/StudioView";
import ValidateView from "./views/ValidateView";
import "./App.css";

function App() {
  return (
    <AppStateProvider>
      <Routes>
        {/* Public */}
        <Route path="/login" element={<LoginView />} />

        {/* Protected — with sidebar */}
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <div className="app-container">
                <Sidebar />
                <main className="main-content">
                  <Routes>
                    <Route path="/" element={<Navigate to="/studio" replace />} />
                    <Route path="/studio" element={<StudioView />} />
                    <Route path="/chat" element={<ChatView />} />
                    <Route path="/outputs" element={<OutputsView />} />
                    <Route path="/validate" element={<ValidateView />} />
                    <Route path="/batch-validate" element={<BatchValidateView />} />
                    <Route path="/compare" element={<CompareView />} />
                    <Route path="/extract" element={<ExtractView />} />
                    <Route path="/analytics" element={<AnalyticsView />} />
                    <Route path="/clauses" element={<ClauseLibraryView />} />
                    <Route path="/settings" element={<SettingsView />} />
                    <Route path="/admin" element={<AdminView />} />
                    {/* Legacy redirects */}
                    <Route path="/dashboard" element={<Navigate to="/studio" replace />} />
                    <Route path="/generate" element={<Navigate to="/studio" replace />} />
                    <Route path="/upload" element={<Navigate to="/studio" replace />} />
                    <Route path="*" element={<Navigate to="/studio" replace />} />
                  </Routes>
                </main>
              </div>
            </ProtectedRoute>
          }
        />

        <Route path="/" element={<Navigate to="/login" replace />} />
      </Routes>
    </AppStateProvider>
  );
}

export default App;