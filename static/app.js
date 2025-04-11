document.addEventListener("DOMContentLoaded", () => {
    // Function to fetch and display listings
    function loadListings() {
        fetch("/listings")
            .then((response) => response.json())
            .then((listings) => {
                listingsContainer.innerHTML = ""; // Clear existing content
                listings.forEach((listing) => addListingCard(listing)); // Render each listing
            })
            .catch((error) => {
                console.error("Error loading listings:", error);
            });
    }

    document.getElementById("settingsButton").addEventListener("click", () => {
        document.getElementById("settingsOverlay").classList.add("visible");
    });
    
    document.getElementById("closeSettings").addEventListener("click", () => {
        document.getElementById("settingsOverlay").classList.remove("visible");
    });
    
    document.getElementById("settingsForm").addEventListener("submit", async (event) => {
        event.preventDefault();
        
        const originAddress = document.getElementById("originAddress").value;
        
        const response = await fetch("/update_origin", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ originAddress })
        });
    
        const result = await response.json();
    
        if (result.success) {
            alert("Origin address updated!");
            document.getElementById("settingsOverlay").classList.remove("visible");
        } else {
            alert("Failed to update address.");
        }
    });


    const form = document.getElementById("addListingForm");
    const listingsContainer = document.getElementById("listingsContainer");

    // Handle form submission
    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        const formData = new FormData(form);
        const data = {
            url: formData.get("url"),
            roommates: parseInt(formData.get("roommates"), 10),
            overall_rating: parseInt(formData.get("overall_rating"), 10),
        };

        try {
            const response = await fetch("/add_listing", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(data),
            });
            const result = await response.json();

            if (result.success) {
                addListingCard(result.listing);
            }
        } catch (error) {
            console.error("Error adding listing:", error);
        }
    });

    function addListingCard(listing) {
        const card = document.createElement("div");
        card.className = "card";
        card.id = listing.id;
    
        // Create edit button separately to ensure proper placement
        const editButton = document.createElement("button");
        editButton.className = "edit-button";
        editButton.textContent = "Edit";
    
        editButton.addEventListener("click", () => {
            editPopup.classList.remove("hidden");
            console.log("editClick");
            Object.keys(listing).forEach(key => {
                const input = editListingForm.querySelector(`[name=${key}]`);
                if (input) input.value = listing[key];
            });
        });
    
        // Append button first, then inner HTML
        
        card.innerHTML += `
            <h3>${listing.address}</h3>
            <img src="data:image/jpeg;base64,${listing.image}" alt="Listing Image" style="max-width: 100%; border-radius: 10px;">
            <p><strong>Rent:</strong> $${listing.price}</p>
            <p><strong>Square Footage:</strong> ${listing.square_footage || "N/A"} sqft</p>
            <p><strong>Bedrooms:</strong> ${listing.bedrooms || "N/A"}</p>
            <p><strong>Bathrooms:</strong> ${listing.bathrooms || "N/A"}</p>
            <p><strong>Date Available:</strong> ${listing.date_available || "N/A"}</p>
            <p><strong>Distance:</strong> ${listing.distance || "N/A"}</p>
            <p><strong>Recommended Score: ${listing.score||"N/A"}%<p>
            <p><strong>Your Rating:</strong> ${listing.overall_rating || "N/A"}</p>
            <p><strong>Cost per Square Foot:</strong> $${listing.cost_per_sqft}</p>
            <p><strong>Cost per Roommate:</strong> $${listing.cost_per_roommate}</p>
            <p><a href="${listing.url}" class="hyperlink"> Link</a></p>
        `;
        card.appendChild(editButton);
    


        // Handle Delete Button
        deleteButton.addEventListener("click", async () => {
            const response = await fetch("/delete_listing", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ id: listing.id }),
            });
            const result = await response.json();
            if (result.success) {
                listingsContainer.removeChild(card);
                editPopup.classList.add("hidden");
            }
        });

        // Handle Save Button
        editListingForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            
            // Convert form data to an object
            const formData = new FormData(editListingForm);
            const updatedData = Object.fromEntries(formData);

            // Ensure the ID exists before making the request
            if (!updatedData.id) {
                alert("Error: Listing ID is required for saving.");
                return;
            }

            try {
                const response = await fetch("/edit_listing", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(updatedData),
                });

                if (!response.ok) {
                    alert(`Failed to save listing. Server responded with status ${response.status}`);
                    return;
                }

                const result = await response.json();

                if (result.success) {
                    // Update existing card HTML
                    const card = document.getElementById(updatedData.id.toString());
                    if (card) {
                        const paragraphs = card.querySelectorAll("p");
                        
                        paragraphs[0].innerHTML = `<strong>Rent:</strong> $${result.listing.price}`;
                        paragraphs[1].innerHTML = `<strong>Square Footage:</strong> ${result.listing.square_footage || "N/A"} sqft`;
                        paragraphs[2].innerHTML = `<strong>Bedrooms:</strong> ${result.listing.bedrooms || "N/A"}`;
                        paragraphs[3].innerHTML = `<strong>Bathrooms:</strong> ${result.listing.bathrooms || "N/A"}`;
                        paragraphs[4].innerHTML = `<strong>Date Available:</strong> ${result.listing.date_available || "N/A"}`;
                        paragraphs[5].innerHTML = `<strong>Distance:</strong> ${result.listing.distance || "N/A"}`;
                        paragraphs[6].innerHTML = `<strong>Your Rating:</strong> ${result.listing.overall_rating || "N/A"}`;
                        paragraphs[7].innerHTML = `<strong>Cost per Square Foot:</strong> $${result.listing.cost_per_sqft}`;
                        paragraphs[8].innerHTML = `<strong>Cost per Roommate:</strong> $${result.listing.cost_per_roommate}`;
                    }
        

                    editPopup.classList.add("hidden");
                } else {
                    alert("Error: Save operation failed.");
                    editPopup.classList.add("hidden");
                }
            } catch (error) {
                alert("An unexpected error occurred.");
            }
        });

        listingsContainer.appendChild(card);
    }
    loadListings();
});
