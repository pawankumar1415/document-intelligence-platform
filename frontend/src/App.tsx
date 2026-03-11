import { Navigate, Route, Routes } from "react-router-dom";

import Navbar from "./components/Navbar";
import ProtectedRoute from "./components/ProtectedRoute";
import { AppStateProvider } from "./context/AppStateContext";
import DashboardPage from "./pages/DashboardPage";
import GeneratePage from "./pages/GeneratePage";
import LoginPage from "./pages/LoginPage";
import OutputsPage from "./pages/OutputsPage";
import UploadPage from "./pages/UploadPage";
import "./App.css";

function App() {
  return (
    <AppStateProvider>
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="*"
          element={
            <ProtectedRoute>
              <div className="app-shell">
                <Navbar />
                <main className="main-content">
                  <Routes>
                    <Route path="/dashboard" element={<DashboardPage />} />
                    <Route path="/upload" element={<UploadPage />} />
                    <Route path="/generate" element={<GeneratePage />} />
                    <Route path="/outputs" element={<OutputsPage />} />
                    <Route path="*" element={<Navigate to="/dashboard" replace />} />
                  </Routes>
                </main>
              </div>
            </ProtectedRoute>
          }
        />
      </Routes>
    </AppStateProvider>
  );
}

export default App;
