// Insert manifest link in the head element when the script runs
(function() {
    // Check if the manifest link already exists to avoid duplicates
    if (!document.querySelector('link[rel="manifest"]')) {
        // Create the link element
        const manifestLink = document.createElement('link');
        manifestLink.rel = 'manifest';
        manifestLink.href = '/public/manifest.json';
        
        // Insert it into the head element
        document.head.appendChild(manifestLink);
    }
})();