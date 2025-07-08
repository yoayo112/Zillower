// Sky Vercauteren
// Zillower
// Updated July 2025

/**
 * Displays a message (error or success) to the user.
 * This is a general utility function that directly manipulates the DOM for messages.
 * @param {HTMLElement} targetElement - The element to display the message next to (or within).
 * @param {string} message - The message text.
 * @param {boolean} isError - True if it's an error message (red text), false for success (green text).
 */
function showMessage(targetElement, message, isError = false) {
    let messageDiv = targetElement.querySelector('.message');
    if (!messageDiv) {
        // If message div doesn't exist, create it (e.g., for form-level messages)
        messageDiv = document.createElement('div');
        messageDiv.className = 'message';
        targetElement.appendChild(messageDiv);
    }
    messageDiv.textContent = message;
    messageDiv.style.color = isError ? "red" : "green";
    messageDiv.style.display = "block";
    setTimeout(() => {
        messageDiv.style.display = "none";
    }, 5000);
}

/**
 * Creates and returns a single listing card HTML element.
 * @param {Object} listing - The listing data.
 * @returns {HTMLElement} The created listing card element.
 */
function createListingCard(listing) {
    const card = document.createElement("div");
    card.className = "card"; // Original class name
    card.id = listing.id;

    // Display the first image if available, otherwise use placeholder
    const imageUrl = (listing.image && listing.image.length > 0)
        ? listing.image[0] // Use the full Data URI directly
        : 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAiIGhlaWdodD0iMTAwIj48cmVjdCB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgZmlsbD0iI2U2ZTZlNiIvPjxwYXRoIGQ9Ik0zMCAxMGgzNnAzIDIgMCAwaDI1cDIgMyAwIDh-OTZsLTE0LTE0djkyaC02NnptLTUgNjBsLTE3LTI2IDIyLTIzIDQ3IDQ4eiIgZmlsbD0iI2ZmZiIvPjx0ZXh0IHg9IjUwIiB5PSI1NSIgZm9udC1mYW1pbHk9IlNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTBweCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZmlsbD0iIzY2NiI-Tm8gSW1hZ2U8L3RleHQ-PC9zdmc-'; // Placeholder SVG

    // --- Safely parse numeric values for display and calculation ---
    const rentValue = parseFloat(listing.price) || 0; // Default to 0 if parsing fails or price is null/undefined
    const utilityValue = parseFloat(listing.utility_estimate) || 0; // Default to 0 if parsing fails or utility_estimate is null/undefined
    const roommatesValue = parseInt(listing.roommates) || 0; // Default to 0 if parsing fails or roommates is null/undefined


    let totalCostPerOccupant = "N/A";
    if (rentValue > 0 && roommatesValue > 0) { // Only calculate if rent is valid and there's at least one occupant
        totalCostPerOccupant = ((rentValue + utilityValue) / roommatesValue).toFixed(2);
    } else if (rentValue > 0 && roommatesValue === 0) {
        // If roommates is 0, it means living alone, so cost per occupant is just total cost
        totalCostPerOccupant = (rentValue + utilityValue).toFixed(2);
    }


    card.innerHTML = `
        <h3>${listing.address}</h3>
        <img src="${imageUrl}" alt="Listing Image" style="max-width: 100%; border-radius: 10px;">
        <p><strong>Rent:</strong> $${listing.price || "N/A"}</p>
        <p><strong>Estimated Utilities:</strong> $${listing.utility_estimate !== null && listing.utility_estimate !== undefined ? listing.utility_estimate : "0"}</p>
        <p><strong>Square Footage:</strong> ${listing.square_footage || "N/A"} sqft</p>
        <p><strong>Bedrooms:</strong> ${listing.bedrooms || "N/A"}</p>
        <p><strong>Bathrooms:</strong> ${listing.bathrooms || "N/A"}</p>
        <p><strong>Date Available:</strong> ${listing.date_available || "N/A"}</p>
        <p><strong>Distance:</strong> ${listing.distance !== null && listing.distance !== undefined ? (listing.distance) : "N/A"}</p>
        <p><strong>Recommended Score:</strong> ${typeof listing.score === 'number' ? (listing.score.toFixed(2) *100 + "%"): "N/A"}</p>
        <p><strong>Your Rating:</strong> ${listing.overall_rating || "N/A"}</p>
        <p><strong>Cost per Square Foot:</strong> $${listing.cost_per_sqft || "N/A"}</p>
        <p><strong>Occupants:</strong> ${listing.roommates !== undefined && listing.roommates !== null ? listing.roommates : "N/A"}</p>
        <p><strong>Cost per Occupant:</strong> $${rentValue.toFixed(2)} rent + $${utilityValue.toFixed(2)} util = $${totalCostPerOccupant} </p>
        <p><a href="${listing.url}" class="hyperlink" target="_blank">Link to Zillow</a></p>
    `;

    // Checkbox for Contacted
    const contactedDiv = document.createElement("div");
    contactedDiv.className = "green-check";
    contactedDiv.id = `contacted-${listing.id}`; // Unique ID
    const contactedLabel = document.createElement("label");
    contactedLabel.htmlFor = `contact_check-${listing.id}`;
    contactedLabel.textContent = "Contacted";
    contactedLabel.style.marginLeft = "10px";
    const contactCheck = document.createElement("input");
    contactCheck.type = "checkbox";
    contactCheck.id = `contact_check-${listing.id}`;
    if (listing.contacted) {
        contactCheck.checked = true;
        contactedDiv.style.backgroundColor = "#1b9458";
    }
    contactCheck.addEventListener("change", async () => {
        const response = await fetch("/contacted", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id: listing.id, selected: contactCheck.checked }),
        });
        const result = await response.json();
        if (result.success) {
            contactedDiv.style.backgroundColor = contactCheck.checked ? "#1b9458" : "transparent";
            // No explicit loadAndFilterListings here to avoid full refresh on simple status change
            // The app.js `loadAndFilterListings` function is responsible for calling `createListingCard`
        } else {
            alert("Error updating contacted status: " + result.error);
            contactCheck.checked = !contactCheck.checked; // Revert
        }
    });
    contactedDiv.appendChild(contactCheck);
    contactedDiv.appendChild(contactedLabel);
    card.appendChild(contactedDiv);


    // Checkbox for Applied
    const appliedDiv = document.createElement("div");
    appliedDiv.className = "green-check";
    appliedDiv.id = `applied-${listing.id}`; // Unique ID
    const appliedLabel = document.createElement("label");
    appliedLabel.htmlFor = `applied_check-${listing.id}`;
    appliedLabel.textContent = "Applied";
    appliedLabel.style.marginLeft = "10px";
    const appliedCheck = document.createElement("input");
    appliedCheck.type = "checkbox";
    appliedCheck.id = `applied_check-${listing.id}`;
    if (listing.applied) {
        appliedCheck.checked = true;
        appliedDiv.style.backgroundColor = "#1b9458";
    }
    appliedCheck.addEventListener("change", async () => {
        const response = await fetch("/applied", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id: listing.id, selected: appliedCheck.checked }),
        });
        const result = await response.json();
        if (result.success) {
            appliedDiv.style.backgroundColor = appliedCheck.checked ? "#1b9458" : "transparent";
            // No explicit loadAndFilterListings here
        } else {
            alert("Error updating applied status: " + result.error);
            appliedCheck.checked = !appliedCheck.checked; // Revert
        }
    });
    appliedDiv.appendChild(appliedCheck);
    appliedDiv.appendChild(appliedLabel);
    card.appendChild(appliedDiv);

    // Edit button
    const editButton = document.createElement("button");
    editButton.className = "edit-button";
    editButton.textContent = "Edit";
    editButton.addEventListener("click", () => {
        const editPopup = document.getElementById("editPopup"); // Get reference here
        const editListingForm = document.getElementById("editListingForm"); // Get reference here

        editPopup.classList.remove("hidden");
        editListingForm.dataset.listingId = listing.id; // Store ID on form
        // Populate edit form fields
        document.getElementById("editId").value = listing.id;
        document.getElementById("editAddress").value = listing.address;
        document.getElementById("editPrice").value = listing.price || ''; // Use empty string for better UX if null
        document.getElementById("editSquareFootage").value = listing.square_footage || '';
        document.getElementById("editBedrooms").value = listing.bedrooms || '';
        document.getElementById("editBathrooms").value = listing.bathrooms || '';
        document.getElementById("editDateAvailable").value = listing.date_available || '';
        document.getElementById("editOverallRating").value = listing.overall_rating || '';
        
        // Ensure utility_estimate is correctly populated, defaulting to empty string if null/undefined
        document.getElementById("editUtilityEstimate").value = listing.utility_estimate !== null && listing.utility_estimate !== undefined ? listing.utility_estimate : '0'; 

        // Populate roommates field. Use 0 if it's explicitly 0, otherwise 1 as a default, or actual value.
        // Backend uses 'roommates' as the key.
        document.getElementById("editRoommates").value = listing.roommates !== null && listing.roommates !== undefined ? listing.roommates : 1; 
    });

    // Delete button
    const deleteButton = document.createElement("button");
    deleteButton.className = "delete-button";
    deleteButton.textContent = "Delete";
    deleteButton.addEventListener("click", async () => {
        if (confirm("Are you sure you want to delete this listing?")) {
            const response = await fetch("/delete_listing", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ id: listing.id }),
            });
            const result = await response.json();
            if (result.success) {
                // Remove the card from the DOM directly
                card.remove();
                // Optionally, trigger a full reload to re-sort/filter if needed,
                // but direct removal is faster for single item deletion.
                // loadAndFilterListings(); // Uncomment if you want a full refresh
            } else {
                alert("Error deleting listing: " + result.error);
            }
        }
    });

    const buttonPanel = document.createElement("div");
    buttonPanel.style = "margin-top:15px;margin-bottom:5px;";
    buttonPanel.appendChild(editButton);
    buttonPanel.appendChild(deleteButton);
    card.appendChild(buttonPanel);

    // Group radio selection
    const groupSelector = document.createElement("div");
    groupSelector.className = "group-selector";
    ["none", "red", "blue", "green", "yellow", "purple"].forEach(color => {
        const input = document.createElement("input");
        input.type = "radio";
        input.name = `group-${listing.id}`;
        input.value = color;
        input.className = `group-circle group-${color}`;
        if (listing.group === color) input.checked = true;

        input.addEventListener("change", async () => {
            const response = await fetch("/update_group", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ id: listing.id, group: input.value }),
            });
            const result = await response.json();
            if (result.success) {
                card.dataset.group = input.value;
                // No explicit loadAndFilterListings here for a simple group change
            } else {
                alert("Error updating group: " + result.message);
            }
        });
        groupSelector.appendChild(input);
    });
    card.appendChild(groupSelector);

    //Comments Section
    const commentSection = document.createElement("textarea");
    commentSection.rows = 4;
    commentSection.cols = 40;
    commentSection.value = listing.comments || ''; // Populate comments
    commentSection.placeholder = "Add comments here...";
    // Add an event listener to save comments on blur (when focus leaves the textarea)
    commentSection.addEventListener('blur', async () => {
        const response = await fetch('/update_comment', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: listing.id, comments: commentSection.value })
        });
        const result = await response.json();
        if (!result.success) {
            console.error("Error saving comment:", result.error);
            showMessage(card, "Error saving comment.", true);
        }
    });

    card.appendChild(commentSection);

    // Return the created card element. The calling function (in app.js) will append it.
    return card;
}