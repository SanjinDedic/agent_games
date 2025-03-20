import React from "react";

const DiceDisplay = ({ value, size = "medium" }) => {
  // Map dice values to Unicode dice characters
  const diceFaces = {
    1: "⚀",
    2: "⚁",
    3: "⚂",
    4: "⚃",
    5: "⚄",
    6: "⚅",
  };

  // Size classes
  const sizeClasses = {
    small: "w-8 h-8 text-xl",
    medium: "w-12 h-12 text-3xl",
    large: "w-16 h-16 text-4xl",
  };

  return (
    <div
      className={`
      inline-flex items-center justify-center 
      ${sizeClasses[size] || sizeClasses.medium}
      rounded-lg border-2 
      ${
        value === 1
          ? "bg-danger/20 text-danger border-danger/30"
          : "bg-success/20 text-success border-success/30"
      }
      shadow-md
    `}
    >
      {diceFaces[value] || value}
    </div>
  );
};

export default DiceDisplay;
