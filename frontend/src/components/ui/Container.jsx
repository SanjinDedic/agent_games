import React from 'react';

const Container = ({ className = '', children, ...props }) => {
    return (
        <div
            className={`w-full px-4 mx-auto max-w-7xl ${className}`}
            {...props}
        >
            {children}
        </div>
    );
};

export default Container;