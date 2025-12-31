//  JavaScript for Starting with flash
window.addEventListener('load', function () {
    const splashScreen = document.getElementById('splash-screen');

    if (splashScreen) {
        setTimeout(() => {
            splashScreen.style.opacity = '0';
            setTimeout(() => {
                splashScreen.style.display = 'none';
            }, 1000); // match CSS transition
        }, 3000); // splash duration (3 sec)
    }
});



document.addEventListener('DOMContentLoaded', function() {
    // Consignment Tracking Form (on the tracking page itself)
    const trackingForm = document.getElementById('tracking-form');
    if (trackingForm) {
        trackingForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const consignmentNumber = document.getElementById('consignment_number').value;
            const resultDiv = document.getElementById('tracking-result');

            // Construct URL for GET request on the same page
            fetch(`${window.location.pathname}?consignment_number=${consignmentNumber}`)
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        const c = data.consignment;
                        resultDiv.innerHTML = `
                            <div class="alert alert-success">
                                <h4>Tracking Details for ${c.consignment_number}</h4>
                                <p><strong>Status:</strong> ${c.status}</p>
                                <p><strong>Origin:</strong> ${c.origin}</p>
                                <p><strong>Destination:</strong> ${c.destination}</p>
                                <p><strong>Current Location:</strong> ${c.current_location}</p>
                                <p><strong>Estimated Delivery:</strong> ${c.estimated_delivery}</p>
                                <p><em>Last Updated: ${c.updated_at}</em></p>
                            </div>
                        `;
                    } else {
                        resultDiv.innerHTML = `<div class="alert alert-danger">${data.message}</div>`;
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    resultDiv.innerHTML = `<div class="alert alert-danger">An error occurred. Please try again.</div>`;
                });
        });
    }

    // Homepage Header Tracking Form
    const homeTrackingForm = document.getElementById('home-tracking-form');
    if (homeTrackingForm) {
        homeTrackingForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const trackingId = document.getElementById('home-tracking-id').value;
            if (trackingId) {
                // Redirect to the main tracking page with the ID as a query parameter
                window.location.href = `/track-consignment/?consignment_number=${trackingId}`;
            }
        });
    }
});

