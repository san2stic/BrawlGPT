/**
 * Notification Bell Component
 * Real-time notification display with WebSocket integration
 */

import React, { useState } from 'react';
import { useWebSocket, Notification } from '../hooks/useWebSocket';
import './NotificationBell.css';

interface NotificationBellProps {
    userId: string | null;
}

const NotificationBell: React.FC<NotificationBellProps> = ({ userId }) => {
    const { notifications, isConnected, clearNotifications, removeNotification } = useWebSocket(userId);
    const [isOpen, setIsOpen] = useState(false);

    const unreadCount = notifications.length;

    const formatNotificationMessage = (notif: Notification): string => {
        switch (notif.type) {
            case 'meta_shift':
                return `🔄 ${notif.brawler} ${notif.change} (${notif.delta})`;
            case 'event_rotation':
                return `🎮 New events: ${notif.new_events?.map(e => e.map).join(', ')}`;
            case 'milestone':
                return `🏆 Achievement unlocked: ${notif.achievement} with ${notif.brawler}!`;
            default:
                return notif.message || 'New notification';
        }
    };

    const formatTimestamp = (timestamp: string): string => {
        try {
            const date = new Date(timestamp);
            const now = new Date();
            const diff = now.getTime() - date.getTime();
            const minutes = Math.floor(diff / 60000);

            if (minutes < 1) return 'Just now';
            if (minutes < 60) return `${minutes}m ago`;

            const hours = Math.floor(minutes / 60);
            if (hours < 24) return `${hours}h ago`;

            const days = Math.floor(hours / 24);
            return `${days}d ago`;
        } catch {
            return 'Recently';
        }
    };

    const getNotificationIcon = (type: string): string => {
        switch (type) {
            case 'meta_shift': return '🔄';
            case 'event_rotation': return '🎮';
            case 'milestone': return '🏆';
            default: return '🔔';
        }
    };

    if (!userId) {
        return null; // Don't show bell when not logged in
    }

    return (
        <div className="notification-bell-container">
            <button
                className="notification-bell-button"
                onClick={() => setIsOpen(!isOpen)}
                aria-label="Notifications"
            >
                <span className="bell-icon">🔔</span>
                {unreadCount > 0 && (
                    <span className="notification-badge">{unreadCount > 99 ? '99+' : unreadCount}</span>
                )}
            </button>

            {isOpen && (
                <>
                    <div className="notification-overlay" onClick={() => setIsOpen(false)} />
                    <div className="notification-dropdown">
                        <div className="notification-header">
                            <div className="header-left">
                                <h3>Notifications</h3>
                                <span className={`connection-indicator ${isConnected ? 'connected' : 'disconnected'}`}>
                                    {isConnected ? '● Live' : '○ Disconnected'}
                                </span>
                            </div>
                            {notifications.length > 0 && (
                                <button className="clear-button" onClick={clearNotifications}>
                                    Clear All
                                </button>
                            )}
                        </div>

                        <div className="notification-list">
                            {notifications.length === 0 ? (
                                <div className="empty-state">
                                    <span className="empty-icon">🔕</span>
                                    <p>No notifications yet</p>
                                    <small>You'll be notified about meta shifts and events</small>
                                </div>
                            ) : (
                                notifications.map((notif, idx) => (
                                    <div key={idx} className={`notification-item notification-${notif.type}`}>
                                        <div className="notification-content">
                                            <span className="notification-icon">
                                                {getNotificationIcon(notif.type)}
                                            </span>
                                            <div className="notification-text">
                                                <p className="notification-message">
                                                    {formatNotificationMessage(notif)}
                                                </p>
                                                <small className="notification-time">
                                                    {formatTimestamp(notif.timestamp)}
                                                </small>
                                            </div>
                                        </div>
                                        <button
                                            className="remove-button"
                                            onClick={() => removeNotification(idx)}
                                            aria-label="Dismiss"
                                        >
                                            ✕
                                        </button>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                </>
            )}
        </div>
    );
};

export default NotificationBell;
