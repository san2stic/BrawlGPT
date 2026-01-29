import { ReactElement } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate, NavLink } from "react-router-dom";
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
import ClubAnalysis from './pages/ClubAnalysis';
import './App.css';

function App(): ReactElement {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <Router>
          <div className="app">
            <header className="app-header">
              <div className="header-content">
                <NavLink to="/" className="logo">
                  <h1>🎮 BrawlGPT</h1>
                </NavLink>
                <nav className="main-nav">
                  <NavLink to="/" end>Home</NavLink>
                  <NavLink to="/meta">Meta Dashboard</NavLink>
                  <NavLink to="/counters">Counters</NavLink>
                  <NavLink to="/team-builder">Team Builder</NavLink>
                  <NavLink to="/club">Club Analysis</NavLink>
                </nav>
                <div className="header-actions">
                  <ThemeToggle />
                </div>
              </div>
            </header>
            <main className="app-main">
              <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />
                <Route path="/schedule" element={<Schedule />} />
                <Route path="/meta" element={<GlobalMetaDashboard />} />
                <Route path="/counters" element={<Counters />} />
                <Route path="/team-builder" element={<TeamBuilder />} />
                <Route path="/club" element={<ClubAnalysis />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </main>
          </div>
        </Router>
      </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;
