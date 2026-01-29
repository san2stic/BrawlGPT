import { ReactElement, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, User, LogOut } from 'lucide-react';
import GameScheduler from '../components/GameScheduler';
import ScheduleGenerator from '../components/ScheduleGenerator';
import { useAuth } from '../context/AuthContext';
import { type Schedule } from '../services/api';

export default function SchedulePage(): ReactElement {
    const { user, logout } = useAuth();
    const [refreshKey, setRefreshKey] = useState(0);

    const handleScheduleGenerated = (schedule: Schedule) => {
        console.log('Schedule generated:', schedule);
        // Trigger calendar refresh
        setRefreshKey(prev => prev + 1);
    };

    const handleScheduleChange = () => {
        // Trigger calendar refresh
        setRefreshKey(prev => prev + 1);
    };

    if (!user) {
        return (
            <div className="min-h-screen bg-slate-950 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-slate-900 via-slate-950 to-black flex items-center justify-center p-4">
                <div className="text-center space-y-6">
                    <h2 className="text-3xl font-bold text-white">Connexion Requise</h2>
                    <p className="text-slate-400">
                        Vous devez être connecté pour accéder au planning personnalisé.
                    </p>
                    <div className="flex gap-4 justify-center">
                        <Link
                            to="/login"
                            className="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-medium transition-colors"
                        >
                            Se connecter
                        </Link>
                        <Link
                            to="/"
                            className="px-6 py-3 bg-slate-800 hover:bg-slate-700 text-white rounded-lg font-medium transition-colors"
                        >
                            Retour
                        </Link>
                    </div>
                </div>
            </div>
        );
    }

    if (!user.brawl_stars_tag) {
        return (
            <div className="min-h-screen bg-slate-950 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-slate-900 via-slate-950 to-black flex items-center justify-center p-4">
                <div className="text-center space-y-6 max-w-lg">
                    <div className="text-6xl">🔒</div>
                    <h2 className="text-3xl font-bold text-white">Profil Non Lié</h2>
                    <p className="text-slate-400">
                        Vous devez lier votre profil Brawl Stars avant de générer un planning personnalisé.
                    </p>
                    <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4 text-left">
                        <p className="text-sm text-blue-300">
                            💡 <strong>Comment lier mon profil ?</strong><br />
                            Retournez à l'accueil, recherchez votre joueur, puis cliquez sur "Claim this profile".
                        </p>
                    </div>
                    <Link
                        to="/"
                        className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-medium transition-colors"
                    >
                        <ArrowLeft className="w-5 h-5" />
                        Retour à l'accueil
                    </Link>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-slate-950 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-slate-900 via-slate-950 to-black text-white">
            <div className="container mx-auto px-4 py-8">
                {/* Header */}
                <div className="flex items-center justify-between mb-8">
                    <div className="flex items-center gap-4">
                        <Link
                            to="/"
                            className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
                        >
                            <ArrowLeft className="w-5 h-5" />
                            Retour
                        </Link>
                        <div>
                            <div>
                                <h1 className="text-4xl font-black bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-600">
                                    Mon Planning IA
                                </h1>
                                <p className="text-slate-400 mt-1 flex items-center gap-2">
                                    <span>🎮 Profil lié:</span>
                                    <span className="font-mono bg-slate-800 px-2 py-0.5 rounded text-blue-400">
                                        {user.brawl_stars_tag}
                                    </span>
                                </p>
                            </div>
                        </div>
                    </div>

                    {/* User Menu */}
                    <div className="flex items-center gap-4">
                        <div className="flex items-center gap-2 text-slate-300">
                            <User className="w-5 h-5" />
                            <span className="font-medium">{user.email}</span>
                        </div>
                        <button
                            onClick={logout}
                            className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-sm font-medium transition-colors"
                        >
                            <LogOut className="w-4 h-4" />
                            Déconnexion
                        </button>
                    </div>
                </div>

                {/* Main Content */}
                <div className="space-y-8">
                    {/* Schedule Generator */}
                    <ScheduleGenerator onScheduleGenerated={handleScheduleGenerated} />

                    {/* Calendar */}
                    <GameScheduler key={refreshKey} onScheduleChange={handleScheduleChange} />
                </div>

                {/* Footer Info */}
                <div className="mt-12 bg-gradient-to-r from-purple-500/10 to-blue-500/10 border border-purple-500/30 rounded-xl p-6">
                    <h3 className="text-lg font-bold text-white mb-3">💡 Comment utiliser le planning ?</h3>
                    <div className="grid md:grid-cols-3 gap-4 text-sm text-slate-300">
                        <div>
                            <div className="font-semibold text-purple-400 mb-1">1. Générer</div>
                            <p>Configurez vos préférences et laissez l'IA créer un planning optimisé pour vous</p>
                        </div>
                        <div>
                            <div className="font-semibold text-blue-400 mb-1">2. Consulter</div>
                            <p>Cliquez sur les événements du calendrier pour voir les détails et conseils</p>
                        </div>
                        <div>
                            <div className="font-semibold text-green-400 mb-1">3. Jouer</div>
                            <p>Suivez les recommandations pour maximiser votre progression</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
