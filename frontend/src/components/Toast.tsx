/**
 * Toast Notification Component
 * Displays user-facing notifications for API errors and success messages
 */

import React, { useEffect } from 'react';
import './Toast.css';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface ToastProps {
    message: string;
    type: ToastType;
    duration?: number;
    onClose: () => void;
}

const Toast: React.FC<ToastProps> = ({ message, type, duration = 5000, onClose }) => {
    useEffect(() => {
        const timer = setTimeout(() => {
            onClose();
        }, duration);

        return () => clearTimeout(timer);
    }, [duration, onClose]);

    const icons = {
        success: '✓',
        error: '✕',
        warning: '⚠',
        info: 'ℹ',
    };

    return (
        <div className={`toast toast-${type}`} role="alert">
            <div className="toast-icon">{icons[type]}</div>
            <div className="toast-message">{message}</div>
            <button
                className="toast-close"
                onClick={onClose}
                aria-label="Close notification"
            >
                ✕
            </button>
        </div>
    );
};

export default Toast;
