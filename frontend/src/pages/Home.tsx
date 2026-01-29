import React, { type ReactElement } from "react";
import { Link } from 'react-router-dom';
import { LogIn, UserPlus, User, CalendarDays } from 'lucide-react';
import PlayerInput from "../components/PlayerInput";
import StatsCard from "../components/StatsCard";
import TrophyChart from "../components/TrophyChart";
import NetworkGraph from "../components/NetworkGraph";
import AiAdvice from "../components/AiAdvice";
import ChatInterface from "../components/ChatInterface";
import MetaAnalysis from "../components/MetaAnalysis";
import { usePlayerData } from "../hooks/usePlayerData";
import { useAuth } from "../context/AuthContext";

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
        <div className="min-h-screen bg-slate-950 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-slate-900 via-slate-950 to-black font-sans text-white overflow-x-hidden relative">
            <div className="container mx-auto px-4 py-8">
                {/* Auth Navigation */}
                <div className="absolute top-4 right-4 flex gap-4">
                    {user ? (
                        <div className="flex items-center gap-4">
                            <div className="flex items-center gap-2 text-slate-300">
                                <User className="w-5 h-5" />
                                <span className="font-medium">{user.email}</span>
                            </div>
                            <button
                                onClick={logout}
                                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-sm font-medium transition-colors"
                            >
                                Logout
                            </button>
                        </div>
                    ) : (
                        <div className="flex gap-3">
                            <Link
                                to="/login"
                                className="flex items-center gap-2 px-4 py-2 text-slate-300 hover:text-white transition-colors"
                            >
                                <LogIn className="w-4 h-4" />
                                Login
                            </Link>
                            <Link
                                to="/register"
                                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg font-medium transition-colors shadow-lg shadow-blue-900/20"
                            >
                                <UserPlus className="w-4 h-4" />
                                Register
                            </Link>
                        </div>
                    )}
                </div>

                {/* Header */}
                <header className="text-center mb-12 animate-fade-in-down pt-8">
                    <h1 className="text-5xl md:text-7xl font-black bg-clip-text text-transparent bg-gradient-to-b from-yellow-400 to-orange-600 drop-shadow-sm tracking-tighter">
                        BRAWL GPT
                    </h1>
                    <p className="text-slate-400 mt-2 font-medium">
                        Stats & Coaching propulsés par l'IA
                    </p>
                    <div className="flex flex-wrap gap-3 justify-center mt-6">
                        <Link
                            to="/meta"
                            className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 text-white rounded-lg font-bold shadow-lg shadow-purple-900/30 transition-all transform hover:scale-105"
                        >
                            <span className="text-xl">🌍</span>
                            Méta Globale
                        </Link>
                        {user && user.brawl_stars_tag && (
                            <Link
                                to="/schedule"
                                className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white rounded-lg font-bold shadow-lg shadow-blue-900/30 transition-all transform hover:scale-105"
                            >
                                <CalendarDays className="w-5 h-5" />
                                Mon Planning IA
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
