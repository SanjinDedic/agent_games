import React from 'react';

const Button = ({ variant = 'primary', className = '', children, ...props }) => {
    const baseClasses = 'px-4 py-2 text-lg transition-colors duration-300 border-none cursor-pointer rounded';

    const variants = {
        primary: 'bg-primary hover:bg-primary-hover text-white',
        success: 'bg-success hover:bg-success-hover text-white',
        danger: 'bg-danger hover:bg-danger-hover text-white',
    };

    return (
        <button
            className={`${baseClasses} ${variants[variant]} ${className}`}
            {...props}
        >
            {children}
        </button>
    );
};

export default Button;