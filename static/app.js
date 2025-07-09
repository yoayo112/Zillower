// Sky Vercauteren
// Zillower
// Updated July 2025

document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements (cache them for performance)
    const listingsContainer = document.getElementById("listingsContainer");
    const editPopup = document.getElementById("editPopup");
    const editListingForm = document.getElementById("editListingForm");

    // Get references to new manual input elements
    const manualHtmlUrlInput = document.getElementById("manualHtmlUrl");
    const manualHtmlInput = document.getElementById("rawHtmlInput");
    const manualRoommatesInput = document.getElementById("manualRoommates");
    const addManualListingBtn = document.getElementById("addManualListingBtn");
    const manualOverallRatingInput = document.getElementById("manualOverallRating"); // Added this based on your HTML

    // Collapsible elements
    const toggleManualInputBtn = document.getElementById("toggleManualInput");
    const manualInputContent = document.getElementById("manualInputContent");
    const manualInputContainer = document.getElementById('manualInputContainer'); // Added for showMessage
    const toggleAutoInputBtn = document.getElementById("toggleAutoInput");
    const autoInputContent = document.getElementById("addListingForm");

    //event listener for typed spiel
    document.getElementById("spiel").addEventListener("blur", async (event) =>{
        const text = document.getElementById("spiel").value;
        console.log(text);
        const response = await fetch("/save_spiel", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    spiel:text
                })
            });

            const result = await response.json();

            if (result.success) {
                showMessage(document.getElementById("spielbox"), "Saved Speil!", false);
            } else {
                console.log("shit");
                showMessage(document.getElementById("spielbox"), "Couldnt save speil. "+ result.error, true);
            }
    });
    document.getElementById("spiel").addEventListener("focus", ()=>{
        const text = document.getElementById("spiel").value;
        navigator.clipboard.writeText(text)
        .then(() => {
            showMessage(document.getElementById("spielbox"), "Copied to clipboard.", false);
        }).catch(err => {
            showMessage(document.getElementById("spielbox"), "Failed to copy.", true);
        });
    });


    // NEW Image Paste Elements
    const pasteImageBtn = document.getElementById("pasteImageBtn");
    const pasteImageMessage = document.getElementById("pasteImageMessage"); // This should be a div or span to show messages in

    // Event listener for sort dropdown
    document.getElementById("sort").addEventListener("change", loadAndFilterListings);

    // Event listener for group filter radios
    document.querySelectorAll('input[name="group"]').forEach((radio) => {
        radio.addEventListener("change", loadAndFilterListings);
    });

    // Settings button toggle
    document.getElementById("settingsButton").addEventListener("click", () => {
        let settings = document.getElementById("settingsOverlay");
        if (settings.classList.contains("visible")) {
            settings.classList.remove("visible");
        } else {
            settings.classList.add("visible");
        }
    });

    // Settings form submission
    document.getElementById("settingsForm").addEventListener("submit", async (event) => {
        event.preventDefault();

        const originAddress = document.getElementById("originAddress").value;
        const rentWeight = parseFloat(document.getElementById("rent_weight").value);
        const sqftWeight = parseFloat(document.getElementById("sqft_weight").value);
        const bedsWeight = parseFloat(document.getElementById("bedrooms_weight").value);
        const bathsWeight = parseFloat(document.getElementById("bathrooms_weight").value);
        const distWeight = parseFloat(document.getElementById("distance_weight").value);

        // Basic validation for weights
        const totalWeight = rentWeight + sqftWeight + bedsWeight + bathsWeight + distWeight;
        if (isNaN(totalWeight) || Math.abs(totalWeight - 1.0) > 0.01) { // Allow for small floating point inaccuracies
            showMessage(document.getElementById("settingsForm"), "Weights must sum to approximately 1.0", true);
            return;
        }

        try {
            const response = await fetch("/update_settings", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    address: originAddress,
                    rent: rentWeight,
                    sqft: sqftWeight,
                    beds: bedsWeight,
                    baths: bathsWeight,
                    dist: distWeight
                })
            });

            const result = await response.json();

            if (result.success) {
                showMessage(document.getElementById("settingsForm"), "Settings updated successfully!");
                document.getElementById("settingsOverlay").classList.remove("visible");
                loadAndFilterListings(); // Reload listings with new weights
            } else {
                showMessage(document.getElementById("settingsForm"), "Failed to update settings: " + result.error, true);
            }
        } catch (error) {
            console.error("Error updating settings:", error);
            showMessage(document.getElementById("settingsForm"), "Network error updating settings.", true);
        }
    });

    // Handle automated listing submission
    const automatedListingForm = document.getElementById("addListingForm");
    automatedListingForm.addEventListener("submit", async (event) => {
        event.preventDefault();

        const formData = new FormData(automatedListingForm);
        const url = formData.get("url").trim();
        // Retrieve utility_estimate from the automated form
        let utilityEstimate = formData.get("utility_estimate"); 
        let roommates = parseInt(formData.get("roommates"), 10);
        const overallRating = parseInt(formData.get("overall_rating"), 10);

        if (!url) {
            showMessage(automatedListingForm, "Please enter a Zillow URL.", true);
            return;
        }

        // --- Data sanitization for automated form ---
        roommates = isNaN(roommates) || roommates < 0 ? 1 : roommates; // Default to 1 if invalid/empty
        
        // Handle utility_estimate from automated form
        if (utilityEstimate === '' || utilityEstimate === null || utilityEstimate === undefined) {
            utilityEstimate = null; // Send as null if blank
        } else {
            utilityEstimate = parseFloat(utilityEstimate);
            if (isNaN(utilityEstimate)) {
                utilityEstimate = null; // Send as null if not a valid number
            }
        }
        // --- End data sanitization ---

        if (overallRating < 1 || overallRating > 10) { // Check after parsing
            showMessage(automatedListingForm, "Overall rating must be between 1 and 10.", true);
            return;
        }

        showMessage(automatedListingForm, "Scraping listing... This may take a moment. The browser may open.", false);

        try {
            const response = await fetch("/add_listing", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ url, roommates, overall_rating: overallRating, utility_estimate: utilityEstimate }),
            });
            const result = await response.json();

            if (result.success) {
                showMessage(automatedListingForm, "Listing added successfully!");
                automatedListingForm.reset(); // Clear form
                loadAndFilterListings(); // Refresh the list
            } else {
                showMessage(automatedListingForm, "Failed to add listing: " + result.error, true);
            }
        } catch (error) {
            console.error("Error adding listing:", error);
            showMessage(automatedListingForm, "Network error adding listing.", true);
        }
    });

    // Handle manual HTML listing submission
    addManualListingBtn.addEventListener("click", async () => {
        const rawHtml = manualHtmlInput.value.trim();
        const url = manualHtmlUrlInput.value.trim();
        let roommates = parseInt(manualRoommatesInput.value, 10);
        const overallRating = parseInt(manualOverallRatingInput.value, 10);

        // Retrieve utility_estimate from the manual form
        let manualUtilityEstimate = document.getElementById("manualUtilityEstimate").value; // Assuming ID for manual utilities input

        if (!rawHtml) {
            showMessage(manualInputContainer, "Please paste the full HTML content.", true);
            return;
        }
        if (!url) {
            showMessage(manualInputContainer, "Please enter the original Zillow URL.", true);
            return;
        }

        // --- Data sanitization for manual form ---
        roommates = isNaN(roommates) || roommates < 0 ? 1 : roommates; // Default to 1 if invalid/empty
        
        // Handle manualUtilityEstimate
        if (manualUtilityEstimate === '' || manualUtilityEstimate === null || manualUtilityEstimate === undefined) {
            manualUtilityEstimate = null; // Send as null if blank
        } else {
            manualUtilityEstimate = parseFloat(manualUtilityEstimate);
            if (isNaN(manualUtilityEstimate)) {
                manualUtilityEstimate = null; // Send as null if not a valid number
            }
        }
        // --- End data sanitization ---

        if (overallRating < 1 || overallRating > 10) { // Check after parsing
            showMessage(manualInputContainer, "Overall rating must be between 1 and 10.", true);
            return;
        }

        showMessage(manualInputContainer, "Processing HTML... This may take a moment.", false);

        try {
            const response = await fetch("/add_listing_from_html", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ raw_html: rawHtml, url: url, roommates: roommates, overall_rating: overallRating, utility_estimate: manualUtilityEstimate }),
            });
            const result = await response.json();

            if (result.success) {
                showMessage(manualInputContainer, "Listing added from HTML successfully!");
                manualHtmlInput.value = ""; // Clear input
                manualHtmlUrlInput.value = ""; // Clear URL input
                manualRoommatesInput.value = "1"; // Reset to default
                manualOverallRatingInput.value = "5"; // Reset to default
                document.getElementById("manualUtilityEstimate").value = ""; // Clear manual utility estimate
                loadAndFilterListings(); // Refresh the list
            } else {
                showMessage(manualInputContainer, "Failed to add listing from HTML: " + result.error, true);
            }
        } catch (error) {
            console.error("Error adding listing from HTML:", error);
            showMessage(manualInputContainer, "Network error adding listing from HTML.", true);
        }
    });

    // Toggle manual input section visibility
    toggleManualInputBtn.addEventListener("click", () => {
        if (manualInputContent.style.display === "none" || manualInputContent.style.display === "") { // Check for initial state too
            manualInputContent.style.display = "flex";
            toggleManualInputBtn.textContent = "▼"; // Use down triangle for "Hide"
        } else {
            manualInputContent.style.display = "none";
            toggleManualInputBtn.textContent = "▶"; // Use right triangle for "Show"
        }
    });
    // and for auto
    toggleAutoInputBtn.addEventListener("click", () => {
        if (autoInputContent.style.display === "none" || autoInputContent.style.display === "") { // Check for initial state too
            autoInputContent.style.display = "flex";
            toggleAutoInputBtn.textContent = "▼"; // Use down triangle for "Hide"
        } else {
            autoInputContent.style.display = "none";
            toggleAutoInputBtn.textContent = "▶"; // Use right triangle for "Show"
        }
    });

    // Handle Save Button for Edit Popup
    editListingForm.addEventListener("submit", async (event) => {
        event.preventDefault();

        const formData = new FormData(editListingForm);
        
        // Start with a base object for updated data
        const updatedData = {
            id: parseInt(formData.get("id"), 10),
            address: formData.get("address"),
            date_available: formData.get("date_available")
        };

        // --- Data sanitization for Edit Form ---
        // Price
        let price = formData.get("price");
        if (price === '' || price === null || price === undefined) {
            updatedData.price = null; // Or 0, depending on your backend's preference for 'no price'
        } else {
            updatedData.price = parseFloat(price);
            if (isNaN(updatedData.price)) {
                updatedData.price = null; // Send as null if not a valid number
            }
        }

        // Square Footage
        let sqft = formData.get("square_footage");
        updatedData.square_footage = parseInt(sqft, 10);
        if (isNaN(updatedData.square_footage) || updatedData.square_footage < 0) {
            updatedData.square_footage = null; // Or 0, depending on preference
        }

        // Bedrooms
        let bedrooms = formData.get("bedrooms");
        updatedData.bedrooms = parseInt(bedrooms, 10);
        if (isNaN(updatedData.bedrooms) || updatedData.bedrooms < 0) {
            updatedData.bedrooms = null; // Or 0, depending on preference
        }

        // Bathrooms
        let bathrooms = formData.get("bathrooms");
        updatedData.bathrooms = parseFloat(bathrooms);
        if (isNaN(updatedData.bathrooms) || updatedData.bathrooms < 0) {
            updatedData.bathrooms = null; // Or 0, depending on preference
        }

        // Overall Rating
        let overallRating = formData.get("overall_rating");
        updatedData.overall_rating = parseInt(overallRating, 10);
        if (isNaN(updatedData.overall_rating) || updatedData.overall_rating < 1 || updatedData.overall_rating > 10) {
            updatedData.overall_rating = 5; // Default to 5 if invalid
        }

        // Roommates (Occupants)
        let roommates = formData.get("roommates");
        updatedData.roommates = parseInt(roommates, 10);
        if (isNaN(updatedData.roommates) || updatedData.roommates < 0) {
            updatedData.roommates = 1; // Default to 1 if invalid/empty
        }

        // Utility Estimate
        let utilityEstimate = formData.get("utility_estimate");
        if (utilityEstimate === '0' || utilityEstimate === null || utilityEstimate === undefined) {
            updatedData.utility_estimate = null; // Send as null if blank
        } else {
            updatedData.utility_estimate = parseFloat(utilityEstimate);
            if (isNaN(updatedData.utility_estimate)) {
                updatedData.utility_estimate = null; // Send as null if not a valid number
            }
        }
        // --- End data sanitization ---

        if (isNaN(updatedData.id)) {
            showMessage(editListingForm, "Error: Listing ID is missing.", true);
            return;
        }

        try {
            const response = await fetch("/edit_listing", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(updatedData),
            });

            if (!response.ok) {
                const errorData = await response.json();
                showMessage(editListingForm, `Failed to save listing: ${errorData.error || response.statusText}`, true);
                return;
            }

            const result = await response.json();

            if (result.success) {
                showMessage(editListingForm, "Listing saved successfully!", false);
                editPopup.classList.add("hidden");
                loadAndFilterListings(); // Refresh the list to show updated values and scores
            } else {
                showMessage(editListingForm, "Error: Save operation failed: " + result.error, true);
                editPopup.classList.add("hidden"); // Still hide on logical failure for now
            }
        } catch (error) {
            console.error("Error saving listing:", error);
            showMessage(editListingForm, "An unexpected error occurred during save. Check console for details.", true);
        }
    });

    // NEW EVENT LISTENER FOR PASTE IMAGE BUTTON
    pasteImageBtn.addEventListener("click", async () => {
        const listingId = editListingForm.dataset.listingId;
        if (!listingId) {
            showMessage(pasteImageMessage, "Please select a listing to edit first.", true);
            return;
        }

        pasteImageMessage.textContent = "Attempting to paste image...";
        pasteImageMessage.style.color = "orange";
        pasteImageMessage.style.display = "block";

        try {
            const clipboardItems = await navigator.clipboard.read();
            let imageFound = false;

            for (const item of clipboardItems) {
                // Check for common image MIME types
                if (item.types.includes("image/png") || item.types.includes("image/jpeg") || item.types.includes("image/gif")) {
                    const mimeType = item.types.includes("image/png") ? "image/png" :
                                     item.types.includes("image/jpeg") ? "image/jpeg" :
                                     item.types.includes("image/gif") ? "image/gif" : null;

                    if (!mimeType) { // Should not happen if one of the above is true
                        continue;
                    }

                    const blob = await item.getType(mimeType);

                    const reader = new FileReader();
                    reader.onloadend = async () => {
                        // reader.result is already the full Data URL (e.g., "data:image/png;base64,...")
                        const fullDataUri = reader.result;

                        try {
                            const response = await fetch("/edit_listing", {
                                method: "POST",
                                headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({
                                    id: parseInt(listingId),
                                    new_image_base64: fullDataUri // Send the FULL Data URI
                                }),
                            });
                            const result = await response.json();

                            if (result.success) {
                                showMessage(pasteImageMessage, "Image pasted and saved successfully!");
                                loadAndFilterListings(); // Refresh the list to show updated images
                            } else {
                                showMessage(pasteImageMessage, "Failed to save image: " + result.error, true);
                            }
                        } catch (error) {
                            console.error("Error sending image to backend:", error);
                            showMessage(pasteImageMessage, "Network error saving image.", true);
                        }
                    };
                    reader.readAsDataURL(blob); // Convert Blob to Data URL
                    imageFound = true;
                    break; // Process only the first image found
                }
            }

            if (!imageFound) {
                showMessage(pasteImageMessage, "No image found in clipboard. Please copy an image first.", true);
            }

        } catch (error) {
            console.error("Error reading clipboard:", error);
            // Provide user-friendly message for clipboard permission issues
            if (error.name === "NotAllowedError" || error.name === "SecurityError") {
                showMessage(pasteImageMessage, "Permission denied to access clipboard. Please ensure your browser allows clipboard access for this site.", true);
            } else {
                showMessage(pasteImageMessage, "Error accessing clipboard. Please try again.", true);
            }
        }
    });
    // END NEW IMAGE PASTE LISTENER

    // Function to load and display listings with current sort and filter
    async function loadAndFilterListings() {
        const sortBy = document.getElementById("sort").value;
        const selectedGroup = document.querySelector('input[name="group"]:checked').value;
    
        // Get a reference to listingsContainer (it's already done at the top, but good to ensure scope)
        const listingsContainer = document.getElementById("listingsContainer"); // Make sure this is accessible
    
        try {
            const response = await fetch(`/listings?sort_by=${sortBy}`);
            const listings = await response.json();
        
            listingsContainer.innerHTML = ""; // Clear existing content
        
            const filteredListings = listings.filter(
                (listing) => selectedGroup === "none" || listing.group === selectedGroup
            );
        
            if (filteredListings.length === 0) {
                listingsContainer.innerHTML = "<p>No listings found for the selected criteria.</p>";
            } else {
                filteredListings.forEach((listing) => {
                    const cardElement = createListingCard(listing); // Get the returned HTML element
                    listingsContainer.appendChild(cardElement); // <--- THIS IS THE MISSING LINE
                });
            }
        } catch (error) {
            console.error("Error loading listings:", error);
            listingsContainer.innerHTML = '<p style="color: red;">Error loading listings.</p>';
        }
    }

    async function loadSpiel()
    {
        try {
            const response = await fetch('/get_spiel_content', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                console.error(`HTTP error! status: ${response.status}`);
                return ''; // Return empty string on HTTP error
            }

            const result = await response.json();

            if (result.success) {
                // The server sends an empty string if the file is empty or doesn't exist
                return result.spiel || ''; 
            } else {
                console.error("Server reported error fetching spiel:", result.error);
                return ''; // Return empty string on server-side logical error
            }
        } catch (error) {
            console.error("Network or parsing error fetching spiel:", error);
            return ''; // Return empty string on network/parsing error
        }
    }

    // Initial state setup (important for the first load)
    // Set the initial button text based on the default display:none
    toggleManualInputBtn.textContent = "▶";
    toggleAutoInputBtn.textContent = "▼";

    // Initial load of listings when the page loads
    loadAndFilterListings();
    loadSpiel();
});