import { useState } from 'react';
import { Sparkles, Calendar, Target, Zap } from 'lucide-react';
import { generateSchedule, type GenerateScheduleRequest, type Schedule } from '../services/api';

interface ScheduleGeneratorProps {
    onScheduleGenerated: (schedule: Schedule) => void;
}

export default function ScheduleGenerator({ onScheduleGenerated }: ScheduleGeneratorProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [generating, setGenerating] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Form state
    const [scheduleType, setScheduleType] = useState<string>('weekly');
    const [durationDays, setDurationDays] = useState<number>(7);
    const [goals, setGoals] = useState<string>('');
    const [focusBrawlers, setFocusBrawlers] = useState<string>('');

    const handleGenerate = async () => {
        try {
            setGenerating(true);
            setError(null);

            const request: GenerateScheduleRequest = {
                schedule_type: scheduleType,
                duration_days: durationDays,
                goals: goals.split(',').map(g => g.trim()).filter(g => g.length > 0),
                focus_brawlers: focusBrawlers.split(',').map(b => b.trim()).filter(b => b.length > 0),
            };

            const schedule = await generateSchedule(request);
            onScheduleGenerated(schedule);
            setIsOpen(false);

            // Reset form
            setGoals('');
            setFocusBrawlers('');
        } catch (err) {
            console.error('Failed to generate schedule:', err);
            setError(err instanceof Error ? err.message : 'Échec de la génération du planning');
        } finally {
            setGenerating(false);
        }
    };

    if (!isOpen) {
        return (
            <button
                onClick={() => setIsOpen(true)}
                className="w-full group flex items-center justify-center gap-3 px-8 py-4 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 rounded-xl text-white font-bold text-lg shadow-lg shadow-blue-900/30 transition-all duration-200 transform hover:scale-105"
            >
                <Sparkles className="w-6 h-6 group-hover:rotate-12 transition-transform" />
                Générer un Planning IA
                <Sparkles className="w-6 h-6 group-hover:-rotate-12 transition-transform" />
            </button>
        );
    }

    return (
        <div className="bg-slate-900/50 border border-slate-700 rounded-xl p-6 space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h3 className="text-2xl font-bold text-white flex items-center gap-2 mb-2">
                        <Sparkles className="w-6 h-6 text-purple-400" />
                        Configurer le Planning
                    </h3>
                    <p className="text-slate-400 text-sm">
                        📊 Planning basé sur votre profil Brawl Stars et vos statistiques
                    </p>
                </div>
                <button
                    onClick={() => setIsOpen(false)}
                    className="text-slate-400 hover:text-white transition-colors"
                >
                    ✕
                </button>
            </div>

            {error && (
                <div className="bg-red-500/10 border border-red-500/50 text-red-400 p-4 rounded-lg">
                    {error}
                </div>
            )}

            {/* Schedule Type */}
            <div className="space-y-3">
                <label className="block text-slate-300 font-semibold flex items-center gap-2">
                    <Calendar className="w-5 h-5 text-blue-400" />
                    Type de Planning
                </label>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <button
                        onClick={() => setScheduleType('weekly')}
                        className={`p-4 rounded-lg border-2 transition-all ${scheduleType === 'weekly'
                            ? 'bg-blue-500/20 border-blue-500 text-blue-300'
                            : 'bg-slate-800/50 border-slate-600 text-slate-400 hover:border-slate-500'
                            }`}
                    >
                        <div className="text-lg font-bold">📅 Hebdomadaire</div>
                        <div className="text-sm mt-1">Progression équilibrée</div>
                    </button>

                    <button
                        onClick={() => setScheduleType('trophy_push')}
                        className={`p-4 rounded-lg border-2 transition-all ${scheduleType === 'trophy_push'
                            ? 'bg-yellow-500/20 border-yellow-500 text-yellow-300'
                            : 'bg-slate-800/50 border-slate-600 text-slate-400 hover:border-slate-500'
                            }`}
                    >
                        <div className="text-lg font-bold">🏆 Trophy Push</div>
                        <div className="text-sm mt-1">Maximiser les trophées</div>
                    </button>

                    <button
                        onClick={() => setScheduleType('brawler_mastery')}
                        className={`p-4 rounded-lg border-2 transition-all ${scheduleType === 'brawler_mastery'
                            ? 'bg-purple-500/20 border-purple-500 text-purple-300'
                            : 'bg-slate-800/50 border-slate-600 text-slate-400 hover:border-slate-500'
                            }`}
                    >
                        <div className="text-lg font-bold">⚡ Maîtrise</div>
                        <div className="text-sm mt-1">Focus brawlers spécifiques</div>
                    </button>
                </div>
            </div>

            {/* Duration */}
            <div className="space-y-3">
                <label className="block text-slate-300 font-semibold flex items-center gap-2">
                    <Zap className="w-5 h-5 text-yellow-400" />
                    Durée (jours)
                </label>
                <div className="flex gap-3">
                    {[3, 7, 14].map((days) => (
                        <button
                            key={days}
                            onClick={() => setDurationDays(days)}
                            className={`flex-1 py-3 rounded-lg font-semibold transition-all ${durationDays === days
                                ? 'bg-yellow-500/20 border-2 border-yellow-500 text-yellow-300'
                                : 'bg-slate-800/50 border-2 border-slate-600 text-slate-400 hover:border-slate-500'
                                }`}
                        >
                            {days} jours
                        </button>
                    ))}
                </div>
            </div>

            {/* Goals */}
            <div className="space-y-3">
                <label className="block text-slate-300 font-semibold flex items-center gap-2">
                    <Target className="w-5 h-5 text-green-400" />
                    Objectifs (optionnel)
                </label>
                <input
                    type="text"
                    value={goals}
                    onChange={(e) => setGoals(e.target.value)}
                    placeholder="Ex: Atteindre 25k trophées, Master Colt (séparez par des virgules)"
                    className="w-full px-4 py-3 bg-slate-800 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
                />
                <p className="text-sm text-slate-500">
                    Séparez plusieurs objectifs par des virgules
                </p>
            </div>

            {/* Focus Brawlers */}
            <div className="space-y-3">
                <label className="block text-slate-300 font-semibold flex items-center gap-2">
                    🎮 Brawlers à privilégier (optionnel)
                </label>
                <input
                    type="text"
                    value={focusBrawlers}
                    onChange={(e) => setFocusBrawlers(e.target.value)}
                    placeholder="Ex: Colt, Shelly, Edgar (séparez par des virgules)"
                    className="w-full px-4 py-3 bg-slate-800 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
                />
                <p className="text-sm text-slate-500">
                    Laissez vide pour que l'IA choisisse automatiquement
                </p>
            </div>

            {/* Actions */}
            <div className="flex gap-3 pt-4">
                <button
                    onClick={() => setIsOpen(false)}
                    disabled={generating}
                    className="flex-1 px-6 py-3 bg-slate-800 hover:bg-slate-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
                >
                    Annuler
                </button>
                <button
                    onClick={handleGenerate}
                    disabled={generating}
                    className="flex-1 px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white rounded-lg font-bold shadow-lg shadow-blue-900/30 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                >
                    {generating ? (
                        <>
                            <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                            Génération en cours...
                        </>
                    ) : (
                        <>
                            <Sparkles className="w-5 h-5" />
                            Générer
                        </>
                    )}
                </button>
            </div>

            {/* Info Box */}
            <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
                <p className="text-sm text-blue-300">
                    💡 L'IA analysera votre profil, vos statistiques et vos préférences pour créer un planning complètement personnalisé avec des recommandations de brawlers, modes de jeu et stratégies adaptées à votre niveau.
                </p>
            </div>
        </div>
    );
}
