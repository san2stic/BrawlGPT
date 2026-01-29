import { ReactElement } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate, Link } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import ErrorBoundary from "./components/ErrorBoundary";
import Home from "./pages/Home";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Schedule from "./pages/Schedule";
import GlobalMetaDashboard from "./components/GlobalMetaDashboard";
import Counters from "./pages/Counters";
import TeamBuilder from "./pages/TeamBuilder";
import ThemeToggle from './components/ThemeToggle';
import './App.css'; // Assuming this is needed for the new structure

function App(): ReactElement {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <Router>
          <div className="app">
            <header className="app-header">
              <div className="header-content">
                <Link to="/" className="logo">
                  <h1>🎮 BrawlGPT</h1>
                </Link>
                <nav className="main-nav">
                  <Link to="/">Home</Link>
                  <Link to="/meta">Meta Dashboard</Link>
                  <Link to="/counters">Counters</Link>
                  <Link to="/team-builder">Team Builder</Link>
                </nav>
                <ThemeToggle />
              </div>
            </header>
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route path="/schedule" element={<Schedule />} />
              <Route path="/meta" element={<GlobalMetaDashboard />} />
              <Route path="/counters" element={<Counters />} />
              <Route path="/team-builder" element={<TeamBuilder />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </div>
        </Router>
      </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;
