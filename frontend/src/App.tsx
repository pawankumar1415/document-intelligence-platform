import { Navigate, Route, Routes } from "react-router-dom";

import ProtectedRoute from "./components/ProtectedRoute";
import Sidebar from "./components/Sidebar";
import { AppStateProvider } from "./context/AppStateContext";
import AdminView from "./views/AdminView";
import LoginView from "./views/LoginView";
import OutputsView from "./views/OutputsView";
import SettingsView from "./views/SettingsView";
import StudioView from "./views/StudioView";
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
                    <Route path="/outputs" element={<OutputsView />} />
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