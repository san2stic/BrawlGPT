import React from 'react';
import './Card.css';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
    variant?: 'default' | 'elevated' | 'flat';
    hover?: boolean;
    glow?: boolean;
}

const Card: React.FC<CardProps> = ({
    children,
    variant = 'default',
    hover = true,
    glow = false,
    className = '',
    ...props
}) => {
    const cardClasses = [
        'card',
        `card-${variant}`,
        hover ? 'card-hover' : '',
        glow ? 'card-glow' : '',
        className,
    ]
        .filter(Boolean)
        .join(' ');

    return (
        <div className={cardClasses} {...props}>
            {children}
        </div>
    );
};

export default Card;
