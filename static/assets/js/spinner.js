// spinner.js

// Function to show the loader
function showLoader() {
    document.getElementById('loader').style.display = 'block';
}

// Function to hide the loader after a delay
function hideLoader(delay = 5000) {
    setTimeout(function() {
        document.getElementById('loader').style.display = 'none';
    }, delay);
}

// Event listener to hide the loader when the page loads
window.addEventListener('load', function() {
    hideLoader();
});
