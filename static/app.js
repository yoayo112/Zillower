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


    const form = document.getElementById("addListingForm");
    const listingsContainer = document.getElementById("listingsContainer");

    // Handle form submission
    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        const formData = new FormData(form);
        const data = {
            url: formData.get("url"),
            roommates: parseInt(formData.get("roommates"), 10),
            distance_rating: parseInt(formData.get("distance_rating"), 10),
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

    // Create listing card dynamically
    function addListingCard(listing) {
        const card = document.createElement("div");
        card.className = "card";

        card.innerHTML = `
            <button class="edit-button">Edit</button>
            <h3>${listing.address}</h3>
            <p><strong>Rent:</strong> $${listing.price}</p>
            <p><strong>Square Footage:</strong> ${listing.square_footage || "N/A"} sqft</p>
            <p><strong>Bedrooms:</strong> ${listing.bedrooms || "N/A"}</p>
            <p><strong>Bathrooms:</strong> ${listing.bathrooms || "N/A"}</p>
            <p><strong>Date Available:</strong> ${listing.date_available || "N/A"}</p>
            <p><strong>Distance Rating:</strong> ${listing.distance_rating || "N/A"}</p>
            <p><strong>Overall Rating:</strong> ${listing.overall_rating || "N/A"}</p>
            <p><strong>Cost per Square Foot:</strong> $${listing.cost_per_sqft.toFixed(2)}</p>
            <p><strong>Cost per Roommate:</strong> $${listing.cost_per_roommate.toFixed(2)}</p>
        `;

        // Handle Edit Button
        card.querySelector(".edit-button").addEventListener("click", () => {
            editPopup.classList.remove("hidden");
            const formData = new FormData(editListingForm);
            Object.keys(listing).forEach(key => {
                const input = editListingForm.querySelector(`[name=${key}]`);
                if (input) input.value = listing[key];
            });
        });

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
            const formData = new FormData(editListingForm);
            const updatedData = Object.fromEntries(formData);
            const response = await fetch("/edit_listing", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(updatedData),
            });
            const result = await response.json();
            if (result.success) {
                Object.keys(updatedData).forEach(key => {
                    const element = card.querySelector(`[data-key=${key}]`);
                    if (element) element.textContent = updatedData[key];
                });
                editPopup.classList.add("hidden");
            }else{
                console.log("save failed");
                editPopup.classList.add("hidden");
            }
        });

        listingsContainer.appendChild(card);
    }
    loadListings();
});
