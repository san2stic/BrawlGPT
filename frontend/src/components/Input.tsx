import React, { useState } from 'react';
import './Input.css';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
    label?: string;
    error?: string;
    icon?: React.ReactNode;
    iconPosition?: 'left' | 'right';
    fullWidth?: boolean;
}

const Input: React.FC<InputProps> = ({
    label,
    error,
    icon,
    iconPosition = 'left',
    fullWidth = false,
    className = '',
    id,
    ...props
}) => {
    const [isFocused, setIsFocused] = useState(false);
    const [hasValue, setHasValue] = useState(!!props.value || !!props.defaultValue);

    const inputId = id || `input-${Math.random().toString(36).substr(2, 9)}`;

    const handleFocus = () => setIsFocused(true);
    const handleBlur = (e: React.FocusEvent<HTMLInputElement>) => {
        setIsFocused(false);
        setHasValue(!!e.target.value);
        props.onBlur?.(e);
    };

    const inputClasses = [
        'input-wrapper',
        fullWidth ? 'input-full-width' : '',
        error ? 'input-error' : '',
        icon ? `input-with-icon-${iconPosition}` : '',
        className,
    ]
        .filter(Boolean)
        .join(' ');

    const labelClasses = [
        'input-label',
        isFocused || hasValue ? 'input-label-floating' : '',
    ]
        .filter(Boolean)
        .join(' ');

    return (
        <div className={inputClasses}>
            {label && (
                <label htmlFor={inputId} className={labelClasses}>
                    {label}
                </label>
            )}
            <div className="input-container">
                {icon && iconPosition === 'left' && (
                    <span className="input-icon input-icon-left">{icon}</span>
                )}
                <input
                    id={inputId}
                    className="input-field"
                    onFocus={handleFocus}
                    onBlur={handleBlur}
                    {...props}
                />
                {icon && iconPosition === 'right' && (
                    <span className="input-icon input-icon-right">{icon}</span>
                )}
            </div>
            {error && <span className="input-error-message">{error}</span>}
        </div>
    );
};

export default Input;
