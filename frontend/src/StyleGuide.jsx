import React from 'react';

const ColorBlock = ({ className, name, hex }) => (
    <div className="flex flex-col items-center mb-4">
        <div className={`w-24 h-24 rounded-lg shadow-md ${className}`}></div>
        <p className="mt-2 font-medium">{name}</p>
        <p className="text-sm text-ui">{hex}</p>
    </div>
);

const ColorSection = ({ title, colors }) => (
    <div className="mb-8">
        <h2 className="text-xl font-bold mb-4 text-ui-dark">{title}</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {colors.map((color) => (
                <ColorBlock key={color.name} {...color} />
            ))}
        </div>
    </div>
);

const StyleGuide = () => {
    const colorGroups = [
        {
            title: "Primary Colors",
            colors: [
                { className: "bg-primary", name: "Primary", hex: "#2563EB" },
                { className: "bg-primary-hover", name: "Hover", hex: "#1D4ED8" },
                { className: "bg-primary-light", name: "Light", hex: "#60A5FA" },
                { className: "bg-primary-dark", name: "Dark", hex: "#1E40AF" },
            ]
        },
        {
            title: "Success Colors",
            colors: [
                { className: "bg-success", name: "Success", hex: "#10B981" },
                { className: "bg-success-hover", name: "Hover", hex: "#059669" },
                { className: "bg-success-light", name: "Light", hex: "#D1FAE5" },
            ]
        },
        {
            title: "Danger Colors",
            colors: [
                { className: "bg-danger", name: "Danger", hex: "#EF4444" },
                { className: "bg-danger-hover", name: "Hover", hex: "#DC2626" },
                { className: "bg-danger-light", name: "Light", hex: "#FEE2E2" },
            ]
        },
        {
            title: "UI Grays",
            colors: [
                { className: "bg-ui-dark", name: "Dark", hex: "#111827" },
                { className: "bg-ui", name: "Default", hex: "#374151" },
                { className: "bg-ui-light", name: "Light", hex: "#D1D5DB" },
                { className: "bg-ui-lighter", name: "Lighter", hex: "#F3F4F6" },
                { className: "bg-ui-hover", name: "Hover", hex: "#030712" },
            ]
        },
        {
            title: "League Colors",
            colors: [
                { className: "bg-league-blue", name: "League", hex: "#4F46E5" },
                { className: "bg-league-hover", name: "Hover", hex: "#4338CA" },
                { className: "bg-league-text text-white", name: "Text", hex: "#E0E7FF" },
            ]
        },
        {
            title: "Notice Colors",
            colors: [
                { className: "bg-notice-orange", name: "Orange", hex: "#F97316" },
                { className: "bg-notice-yellow", name: "Yellow", hex: "#EAB308" },
                { className: "bg-notice-yellowBg", name: "Light", hex: "#FEF3C7" },
            ]
        }
    ];

    return (
        <div className="container mx-auto px-4 py-8">
            <h1 className="text-3xl font-bold mb-8 text-ui-dark">Color Style Guide</h1>
            {colorGroups.map((group) => (
                <ColorSection key={group.title} {...group} />
            ))}
        </div>
    );
};

export default StyleGuide;