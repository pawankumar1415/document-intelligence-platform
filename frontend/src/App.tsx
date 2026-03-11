import { Navigate, Route, Routes } from "react-router-dom";

import Navbar from "./components/Navbar";
import { AppStateProvider } from "./context/AppStateContext";
import DashboardPage from "./pages/DashboardPage";
import GeneratePage from "./pages/GeneratePage";
import OutputsPage from "./pages/OutputsPage";
import UploadPage from "./pages/UploadPage";
import "./App.css";

function App() {
  return (
    <AppStateProvider>
      <div className="app-shell">
        <Navbar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/generate" element={<GeneratePage />} />
            <Route path="/outputs" element={<OutputsPage />} />
          </Routes>
        </main>
      </div>
    </AppStateProvider>
  );
}

export default App;
