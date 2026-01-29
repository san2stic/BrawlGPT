/**
 * WebSocket Hook for Real-Time Notifications
 * Manages WebSocket connection and notification state
 */

import { useEffect, useRef, useState, useCallback } from 'react';

export interface Notification {
    type: string;
    message?: string;
    brawler?: string;
    change?: string;
    delta?: string;
    achievement?: string;
    new_events?: Array<{ mode: string; map: string }>;
    timestamp: string;
}

interface UseWebSocketReturn {
    notifications: Notification[];
    isConnected: boolean;
    clearNotifications: () => void;
    removeNotification: (index: number) => void;
}

// Construct WebSocket URL dynamically based on current page
// For production: use wss:// with same domain. For dev: use env var or localhost
const getWebSocketURL = () => {
    if (import.meta.env.VITE_WS_URL) {
        return import.meta.env.VITE_WS_URL;
    }
    // Production: use same domain as the page
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.host}`;
};

const WS_URL = getWebSocketURL();

export function useWebSocket(userId: string | null): UseWebSocketReturn {
    const [notifications, setNotifications] = useState<Notification[]>([]);
    const [isConnected, setIsConnected] = useState(false);
    const ws = useRef<WebSocket | null>(null);
    const reconnectTimeout = useRef<number | null>(null);
    const pingInterval = useRef<number | null>(null);

    const connect = useCallback(() => {
        if (!userId) return;

        const wsUrl = `${WS_URL}/ws/${userId}`;
        console.log(`[WebSocket] Connecting to: ${wsUrl}`);

        try {
            ws.current = new WebSocket(wsUrl);

            ws.current.onopen = () => {
                console.log('[WebSocket] Connected');
                setIsConnected(true);

                // Set up ping interval for keep-alive (every 30 seconds)
                pingInterval.current = setInterval(() => {
                    if (ws.current?.readyState === WebSocket.OPEN) {
                        ws.current.send('ping');
                    }
                }, 30000);
            };

            ws.current.onmessage = (event) => {
                try {
                    // Ignore pong responses
                    if (event.data === 'pong') return;

                    const notification: Notification = JSON.parse(event.data);
                    console.log('[WebSocket] Received notification:', notification);

                    // Don't add connection messages to notifications list
                    if (notification.type === 'connection') return;

                    setNotifications((prev) => [notification, ...prev].slice(0, 50)); // Keep max 50
                } catch (error) {
                    console.error('[WebSocket] Error parsing message:', error);
                }
            };

            ws.current.onerror = (error) => {
                console.error('[WebSocket] Error:', error);
            };

            ws.current.onclose = (event) => {
                console.log(`[WebSocket] Disconnected: ${event.code} ${event.reason}`);
                setIsConnected(false);

                // Clear ping interval
                if (pingInterval.current) {
                    clearInterval(pingInterval.current);
                    pingInterval.current = null;
                }

                // Attempt to reconnect after 5 seconds
                reconnectTimeout.current = setTimeout(() => {
                    console.log('[WebSocket] Attempting to reconnect...');
                    connect();
                }, 5000);
            };
        } catch (error) {
            console.error('[WebSocket] Connection error:', error);
            setIsConnected(false);
        }
    }, [userId]);

    useEffect(() => {
        connect();

        return () => {
            // Cleanup
            if (ws.current) {
                ws.current.close();
                ws.current = null;
            }
            if (reconnectTimeout.current) {
                clearTimeout(reconnectTimeout.current);
            }
            if (pingInterval.current) {
                clearInterval(pingInterval.current);
            }
        };
    }, [connect]);

    const clearNotifications = useCallback(() => {
        setNotifications([]);
    }, []);

    const removeNotification = useCallback((index: number) => {
        setNotifications((prev) => prev.filter((_, i) => i !== index));
    }, []);

    return {
        notifications,
        isConnected,
        clearNotifications,
        removeNotification,
    };
}
