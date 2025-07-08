// Sky Vercauteren
// Zillower
// Updated July 2025

/**
 * Formats a number as currency (e.g., 1234.56 -> $1,234.56).
 * @param {number} amount - The numeric amount.
 * @returns {string} The formatted currency string.
 */
function formatCurrency(amount) {
    if (typeof amount !== 'number' || isNaN(amount)) {
        return 'N/A';
    }
    return `$${amount.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;
}

/**
 * Formats a number with comma separators (e.g., 12345 -> 12,345).
 * @param {number} num - The number to format.
 * @returns {string} The formatted number string.
 */
function formatNumber(num) {
    if (typeof num !== 'number' || isNaN(num)) {
        return 'N/A';
    }
    return num.toLocaleString();
}

/**
 * Converts a currency string (e.g., "$1,234.56") to a float.
 * @param {string} currencyString - The currency string.
 * @returns {number} The float value.
 */
function currencyToFloat(currencyString) {
    if (typeof currencyString !== 'string') {
        return NaN;
    }
    const cleanedString = currencyString.replace(/[$,]/g, '');
    return parseFloat(cleanedString);
}

/**
 * Converts a Data URI string (e.g., "data:image/png;base64,...") to a Blob object.
 * Useful for sending image data to a server.
 * @param {string} dataURI - The Data URI string.
 * @returns {Blob} The Blob object.
 */
function dataURItoBlob(dataURI) {
    if (!dataURI) return null;
    // Split metadata from data
    const parts = dataURI.split(',');
    const mime = parts[0].match(/:(.*?);/)[1];
    const b64data = parts[1];

    // Decode base64 (for older browsers that don't support `atob` with unicode)
    const byteString = atob(b64data);

    // Create ArrayBuffer
    const ab = new ArrayBuffer(byteString.length);
    const ia = new Uint8Array(ab);
    for (let i = 0; i < byteString.length; i++) {
        ia[i] = byteString.charCodeAt(i);
    }

    // Create Blob
    return new Blob([ab], { type: mime });
}