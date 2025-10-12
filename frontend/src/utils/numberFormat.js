/**
 * Formats a number to display with one decimal point for non-zero decimals,
 * and no decimal point for whole numbers.
 * 
 * Examples:
 * 10.0 -> "10"
 * 1.33333333333333333333333 -> "1.3"
 * 5.0 -> "5"
 * 2.7 -> "2.7"
 * 15 -> "15"
 */
export const formatNumber = (num) => {
  if (num === null || num === undefined || isNaN(num)) {
    return "0";
  }
  
  const number = parseFloat(num);
  
  // Check if it's a whole number
  if (number % 1 === 0) {
    return number.toString();
  }
  
  // Format to 1 decimal place for non-whole numbers
  return number.toFixed(1);
};

/**
 * Formats a number for display with proper rounding
 * Alias for formatNumber for consistency
 */
export const displayNumber = formatNumber;
