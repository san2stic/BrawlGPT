import React, { type ReactElement } from "react";
import { Link } from 'react-router-dom';
import { LogIn, UserPlus, User, CalendarDays, Globe } from 'lucide-react';
import PlayerInput from "../components/PlayerInput";
import StatsCard from "../components/StatsCard";
import TrophyChart from "../components/TrophyChart";
import NetworkGraph from "../components/NetworkGraph";
import AiAdvice from "../components/AiAdvice";
import ChatInterface from "../components/ChatInterface";
import MetaAnalysis from "../components/MetaAnalysis";
import { usePlayerData } from "../hooks/usePlayerData";
import { useAuth } from "../context/AuthContext";
import Button from "../components/Button";
import './Home.css';

export default function Home(): ReactElement {
    const { player, insights, loading, error, search, refresh } = usePlayerData();
    const { user, logout, claimProfile } = useAuth();
    const [claiming, setClaiming] = React.useState(false);

    const handleClaim = async () => {
        if (!player || !user) return;
        setClaiming(true);
        try {
            await claimProfile(player.tag);
        } catch (error) {
            console.error("Failed to claim profile", error);
            // In a real app, use a toast notification here
        } finally {
            setClaiming(false);
        }
    };


    return (
        <div className="home-container">
            <div className="home-content">
                {/* Auth Navigation */}
                <div className="auth-nav">
                    {user ? (
                        <>
                            <div className="auth-user-info">
                                <User size={20} />
                                <span>{user.email}</span>
                            </div>
                            <Button
                                onClick={logout}
                                variant="secondary"
                                size="sm"
                            >
                                Logout
                            </Button>
                        </>
                    ) : (
                        <div className="auth-links">
                            <Link to="/login" className="auth-link">
                                <LogIn size={16} />
                                Login
                            </Link>
                            <Link to="/register" className="auth-link auth-link-primary">
                                <UserPlus size={16} />
                                Register
                            </Link>
                        </div>
                    )}
                </div>

                {/* Header */}
                <header className="home-header">
                    <h1 className="home-title">
                        BRAWL GPT
                    </h1>
                    <p className="home-subtitle">
                        Stats & Coaching propulsés par l'IA
                    </p>
                    <div className="home-actions">
                        <Link to="/meta">
                            <Button
                                variant="primary"
                                size="lg"
                                icon={<Globe size={20} />}
                            >
                                Méta Globale
                            </Button>
                        </Link>
                        {user && user.brawl_stars_tag && (
                            <Link to="/schedule">
                                <Button
                                    variant="primary"
                                    size="lg"
                                    icon={<CalendarDays size={20} />}
                                >
                                    Mon Planning IA
                                </Button>
                            </Link>
                        )}
                    </div>
                </header>

                {/* Search Input */}
                <PlayerInput onSearch={search} loading={loading} />

                {/* Error Display */}
                {error && (
                    <div className="max-w-md mx-auto mt-6 bg-red-500/10 border border-red-500/50 text-red-400 p-4 rounded-xl text-center animate-fade-in">
                        <div className="flex items-center justify-center gap-2">
                            <svg
                                className="w-5 h-5"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                            >
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                                />
                            </svg>
                            <span className="font-bold">{error}</span>
                        </div>
                    </div>
                )}

                {/* Results */}
                {player && (
                    <div className="mt-12 space-y-8">
                        {/* CLAIM PROFILE BUTTON */}
                        {user && (
                            <div className="flex justify-center mb-4">
                                {user.brawl_stars_tag === player.tag ? (
                                    <div className="px-4 py-2 bg-green-500/10 border border-green-500/50 text-green-400 rounded-lg flex items-center gap-2">
                                        <span>✅ Profile Claimed</span>
                                    </div>
                                ) : (
                                    <button
                                        className="px-6 py-2 bg-yellow-600/20 hover:bg-yellow-600/30 border border-yellow-500/50 text-yellow-400 rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50"
                                        onClick={handleClaim}
                                        disabled={claiming}
                                    >
                                        <span>{claiming ? "Claiming..." : "👑 Claim this profile"}</span>
                                    </button>
                                )}
                            </div>
                        )}

                        {/* Refresh Button */}
                        <div className="flex justify-center">
                            <button
                                onClick={refresh}
                                disabled={loading}
                                className="group flex items-center gap-2 px-6 py-3 bg-slate-800 hover:bg-slate-700 border border-slate-600 hover:border-cyan-500/50 rounded-xl text-slate-300 hover:text-white font-medium transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                <svg
                                    className={`w-5 h-5 transition-transform group-hover:rotate-180 duration-500 ${loading ? "animate-spin" : ""}`}
                                    fill="none"
                                    stroke="currentColor"
                                    viewBox="0 0 24 24"
                                >
                                    <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        strokeWidth={2}
                                        d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                                    />
                                </svg>
                                {loading ? "Actualisation..." : "Actualiser les données"}
                            </button>
                        </div>

                        <StatsCard player={player} />
                        <NetworkGraph playerTag={player.tag} />
                        <TrophyChart brawlers={player.brawlers} />
                        <MetaAnalysis playerTag={player.tag} />
                        <AiAdvice insights={insights} />
                    </div>
                )}

                {/* Footer */}
                <footer className="text-center mt-16 text-slate-600 text-sm">
                    <p>
                        Propulsé par l'IA • Non affilié à Supercell
                    </p>
                </footer>
            </div>

            {/* Chat Interface */}
            <ChatInterface player={player} />
        </div>
    );
}
