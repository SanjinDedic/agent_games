import React from 'react';
import { Link } from 'react-router-dom';

const NavLink = ({ className = '', children, ...props }) => {
    return (
        <Link
            className={`text-white no-underline px-4 py-2 hover:bg-ui-hover transition-colors duration-300 ${className}`}
            {...props}
        >
            {children}
        </Link>
    );
};

export default NavLink;