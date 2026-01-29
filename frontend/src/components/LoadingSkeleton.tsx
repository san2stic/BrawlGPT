import React from 'react';
import './LoadingSkeleton.css';

export interface LoadingSkeletonProps {
    variant?: 'text' | 'rectangular' | 'circular';
    width?: string | number;
    height?: string | number;
    count?: number;
    className?: string;
}

const LoadingSkeleton: React.FC<LoadingSkeletonProps> = ({
    variant = 'rectangular',
    width,
    height,
    count = 1,
    className = '',
}) => {
    const skeletonClasses = [
        'skeleton',
        `skeleton-${variant}`,
        className,
    ]
        .filter(Boolean)
        .join(' ');

    const style: React.CSSProperties = {
        width: typeof width === 'number' ? `${width}px` : width,
        height: typeof height === 'number' ? `${height}px` : height,
    };

    // Auto heights for variants
    if (!height) {
        if (variant === 'text') {
            style.height = '1em';
        } else if (variant === 'circular') {
            style.height = width || '40px';
            style.borderRadius = '50%';
        }
    }

    return (
        <>
            {Array.from({ length: count }).map((_, index) => (
                <div key={index} className={skeletonClasses} style={style} />
            ))}
        </>
    );
};

export default LoadingSkeleton;
