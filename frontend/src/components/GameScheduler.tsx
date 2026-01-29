import { useState, useEffect, useCallback } from 'react';
import { Calendar, momentLocalizer, Event } from 'react-big-calendar';
import moment from 'moment';
import 'react-big-calendar/lib/css/react-big-calendar.css';
import { Calendar as CalendarIcon, Trash2, RefreshCw, Info } from 'lucide-react';
import { getCurrentSchedule, deleteSchedule, type Schedule, type ScheduleEvent as APIScheduleEvent } from '../services/api';

const localizer = momentLocalizer(moment);

interface CalendarEvent extends Event {
    id: number;
    recommended_brawler?: string;
    recommended_mode?: string;
    recommended_map?: string;
    notes?: string;
    priority: string;
    color?: string;
    event_type: string;
}

interface GameSchedulerProps {
    onScheduleChange?: () => void;
}

export default function GameScheduler({ onScheduleChange }: GameSchedulerProps) {
    const [schedule, setSchedule] = useState<Schedule | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null);
    const [deleting, setDeleting] = useState(false);

    const loadSchedule = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);
            const data = await getCurrentSchedule();
            setSchedule(data);
        } catch (err) {
            console.error('Failed to load schedule:', err);
            setError(err instanceof Error ? err.message : 'Failed to load schedule');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadSchedule();
    }, [loadSchedule]);

    const handleDeleteSchedule = async () => {
        if (!schedule || deleting) return;

        if (!confirm('Êtes-vous sûr de vouloir supprimer ce planning ?')) {
            return;
        }

        try {
            setDeleting(true);
            await deleteSchedule(schedule.id);
            setSchedule(null);
            setSelectedEvent(null);
            if (onScheduleChange) {
                onScheduleChange();
            }
        } catch (err) {
            console.error('Failed to delete schedule:', err);
            alert('Erreur lors de la suppression du planning');
        } finally {
            setDeleting(false);
        }
    };

    // Convert API events to calendar events
    const events: CalendarEvent[] = schedule?.events.map((event: APIScheduleEvent) => ({
        id: event.id,
        title: event.title,
        start: new Date(event.start),
        end: new Date(event.end),
        recommended_brawler: event.recommended_brawler,
        recommended_mode: event.recommended_mode,
        recommended_map: event.recommended_map,
        notes: event.notes,
        priority: event.priority,
        color: event.color,
        event_type: event.event_type,
    })) || [];

    // Custom styling for events based on priority and type
    const eventStyleGetter = (event: CalendarEvent) => {
        const backgroundColor = event.color || '#2196F3';
        return {
            style: {
                backgroundColor,
                borderRadius: '6px',
                opacity: 0.9,
                color: 'white',
                border: '0px',
                display: 'block',
                fontWeight: event.priority === 'high' ? '600' : '400',
            }
        };
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[400px] bg-slate-900/50 rounded-xl border border-slate-700">
                <div className="flex flex-col items-center gap-4">
                    <RefreshCw className="w-8 h-8 text-blue-400 animate-spin" />
                    <p className="text-slate-400">Chargement du planning...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="bg-red-500/10 border border-red-500/50 text-red-400 p-6 rounded-xl">
                <p className="font-medium">Erreur: {error}</p>
                <button
                    onClick={loadSchedule}
                    className="mt-4 px-4 py-2 bg-red-500/20 hover:bg-red-500/30 rounded-lg transition-colors"
                >
                    Réessayer
                </button>
            </div>
        );
    }

    if (!schedule) {
        return (
            <div className="flex items-center justify-center min-h-[400px] bg-slate-900/50 rounded-xl border border-slate-700">
                <div className="text-center space-y-4">
                    <CalendarIcon className="w-16 h-16 text-slate-600 mx-auto" />
                    <div>
                        <h3 className="text-xl font-bold text-slate-300 mb-2">Aucun planning actif</h3>
                        <p className="text-slate-500">Générez un planning personnalisé pour commencer</p>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Schedule Header */}
            <div className="bg-gradient-to-r from-blue-600/20 to-purple-600/20 border border-blue-500/30 rounded-xl p-6">
                <div className="flex items-start justify-between">
                    <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                            <h3 className="text-2xl font-bold text-white">
                                Planning {schedule.schedule_type === 'weekly' ? 'Hebdomadaire' :
                                    schedule.schedule_type === 'trophy_push' ? 'Trophy Push' :
                                        'Maîtrise Brawler'}
                            </h3>
                            {schedule.player_name && (
                                <span className="px-3 py-1 bg-blue-500/20 text-blue-300 rounded-full text-sm font-medium flex items-center gap-1">
                                    🎮 {schedule.player_name}
                                </span>
                            )}
                        </div>
                        <p className="text-slate-300 mb-3">{schedule.description}</p>
                        {schedule.goals.length > 0 && (
                            <div className="flex flex-wrap gap-2">
                                {schedule.goals.map((goal, idx) => (
                                    <span key={idx} className="px-3 py-1 bg-blue-500/20 text-blue-300 rounded-full text-sm">
                                        🎯 {goal}
                                    </span>
                                ))}
                            </div>
                        )}
                    </div>
                    <button
                        onClick={handleDeleteSchedule}
                        disabled={deleting}
                        className="flex items-center gap-2 px-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg transition-colors disabled:opacity-50"
                    >
                        <Trash2 className="w-4 h-4" />
                        {deleting ? 'Suppression...' : 'Supprimer'}
                    </button>
                </div>
            </div>

            {/* Calendar */}
            <div className="bg-slate-900/50 border border-slate-700 rounded-xl p-6">
                <div className="calendar-container" style={{ height: '700px' }}>
                    <Calendar
                        localizer={localizer}
                        events={events}
                        startAccessor="start"
                        endAccessor="end"
                        style={{ height: '100%' }}
                        eventPropGetter={eventStyleGetter}
                        onSelectEvent={(event) => setSelectedEvent(event as CalendarEvent)}
                        views={['month', 'week', 'day', 'agenda']}
                        defaultView="week"
                        popup
                    />
                </div>
            </div>

            {/* Event Detail Modal */}
            {selectedEvent && (
                <div
                    className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4"
                    onClick={() => setSelectedEvent(null)}
                >
                    <div
                        className="bg-slate-900 border border-slate-700 rounded-xl p-6 max-w-lg w-full"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className="flex items-start justify-between mb-4">
                            <h3 className="text-2xl font-bold text-white">{selectedEvent.title}</h3>
                            <button
                                onClick={() => setSelectedEvent(null)}
                                className="text-slate-400 hover:text-white transition-colors"
                            >
                                ✕
                            </button>
                        </div>

                        <div className="space-y-4">
                            {/* Time */}
                            <div className="flex items-center gap-2 text-slate-300">
                                <CalendarIcon className="w-5 h-5" />
                                <span>
                                    {moment(selectedEvent.start).format('ddd DD MMM, HH:mm')} -{' '}
                                    {moment(selectedEvent.end).format('HH:mm')}
                                </span>
                            </div>

                            {/* Event Type & Priority */}
                            <div className="flex gap-2">
                                <span
                                    className="px-3 py-1 rounded-full text-sm font-medium"
                                    style={{ backgroundColor: selectedEvent.color || '#2196F3' }}
                                >
                                    {selectedEvent.event_type}
                                </span>
                                <span className={`px-3 py-1 rounded-full text-sm font-medium ${selectedEvent.priority === 'high' ? 'bg-red-500/20 text-red-400' :
                                    selectedEvent.priority === 'medium' ? 'bg-yellow-500/20 text-yellow-400' :
                                        'bg-green-500/20 text-green-400'
                                    }`}>
                                    Priorité: {selectedEvent.priority}
                                </span>
                            </div>

                            {/* Recommendations */}
                            {selectedEvent.recommended_brawler && (
                                <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
                                    <h4 className="text-sm font-semibold text-slate-400 mb-2">Recommandations</h4>
                                    <div className="space-y-2 text-slate-300">
                                        {selectedEvent.recommended_brawler && (
                                            <p>🎮 <strong>Brawler:</strong> {selectedEvent.recommended_brawler}</p>
                                        )}
                                        {selectedEvent.recommended_mode && (
                                            <p>🎯 <strong>Mode:</strong> {selectedEvent.recommended_mode}</p>
                                        )}
                                        {selectedEvent.recommended_map && (
                                            <p>🗺️ <strong>Map:</strong> {selectedEvent.recommended_map}</p>
                                        )}
                                    </div>
                                </div>
                            )}

                            {/* Notes */}
                            {selectedEvent.notes && (
                                <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
                                    <div className="flex items-start gap-2">
                                        <Info className="w-5 h-5 text-blue-400 mt-0.5 flex-shrink-0" />
                                        <div>
                                            <h4 className="text-sm font-semibold text-blue-400 mb-1">Conseils du Coach</h4>
                                            <p className="text-slate-300 text-sm">{selectedEvent.notes}</p>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>

                        <button
                            onClick={() => setSelectedEvent(null)}
                            className="mt-6 w-full px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition-colors"
                        >
                            Fermer
                        </button>
                    </div>
                </div>
            )}

            {/* Custom Styles */}
            <style>{`
        .calendar-container .rbc-calendar {
          color: #cbd5e1;
          background: transparent;
        }
        .calendar-container .rbc-header {
          padding: 12px 4px;
          font-weight: 600;
          color: #e2e8f0;
          border-color: #475569;
        }
        .calendar-container .rbc-today {
          background-color: rgba(59, 130, 246, 0.1);
        }
        .calendar-container .rbc-off-range-bg {
          background-color: rgba(15, 23, 42, 0.5);
        }
        .calendar-container .rbc-date-cell {
          padding: 4px;
          color: #94a3b8;
        }
        .calendar-container .rbc-event {
          padding: 4px 6px;
          font-size: 0.875rem;
        }
        .calendar-container .rbc-toolbar button {
          color: #cbd5e1;
          border-color: #475569;
          background-color: rgba(51, 65, 85, 0.5);
        }
        .calendar-container .rbc-toolbar button:hover {
          background-color: rgba(71, 85, 105, 0.7);
        }
        .calendar-container .rbc-toolbar button.rbc-active {
          background-color: rgba(59, 130, 246, 0.5);
          border-color: #3b82f6;
        }
        .calendar-container .rbc-month-view, .calendar-container .rbc-time-view {
          border-color: #475569;
        }
        .calendar-container .rbc-day-bg, .calendar-container .rbc-time-slot {
          border-color: #334155;
        }
        .calendar-container .rbc-time-header-content {
          border-color: #475569;
        }
        .calendar-container .rbc-current-time-indicator {
          background-color: #ef4444;
        }
      `}</style>
        </div>
    );
}
