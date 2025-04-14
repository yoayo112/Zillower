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

    document.getElementById("sort").addEventListener("change", () =>{
        const sortBy = document.getElementById("sort").value; // Get selected value
        fetch(`/listings?sort_by=${sortBy}`)
            .then((response) => response.json())
            .then((listings) => {
                listingsContainer.innerHTML = ""; // Clear existing content
                listings.forEach((listing) => addListingCard(listing)); // Render each listing
            })
            .catch((error) => {
                console.error("Error loading listings:", error);
            });
    });
    
    document.querySelectorAll('input[name="group"]').forEach((radio) => {
        radio.addEventListener("change", () => {
            const selectedGroup = document.querySelector('input[name="group"]:checked').value;
            const sortBy = document.getElementById("sort").value; // Get current sorting option
    
            fetch(`/listings?sort_by=${sortBy}`)
                .then((response) => response.json())
                .then((listings) => {
                    listingsContainer.innerHTML = ""; // Clear existing listings
                    listings
                        .filter((listing) => selectedGroup === "none" || listing.group === selectedGroup) // Display all if "none" is selected
                        .forEach((listing) => addListingCard(listing)); // Render filtered listings
                })
                .catch((error) => {
                    console.error("Error loading filtered listings:", error);
                });
        });
    });

    document.getElementById("settingsButton").addEventListener("click", () => {
        let settings = document.getElementById("settingsOverlay");
        if(settings.classList.contains("visible")){
            settings.classList.remove("visible");
        }else{
            settings.classList.add("visible");
        }
    });
    
    document.getElementById("settingsForm").addEventListener("submit", async (event) => {
        event.preventDefault();
        
        const originAddress = document.getElementById("originAddress").value;
        console.log(document.getElementById("distance_weight").value)
        console.log(document.getElementById("rent_weight").value)
        
        const response = await fetch("/update_settings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ 
                address :originAddress,
                rent:document.getElementById("rent_weight").value,
                sqft: document.getElementById("sqft_weight").value,
                beds:document.getElementById("bedrooms_weight").value,
                baths:document.getElementById("bathrooms_weight").value,
                dist: document.getElementById("distance_weight").value
             })
        });
    
        const result = await response.json();
    
        if (result.success) {
            document.getElementById("settingsOverlay").classList.remove("visible");
        } else {
            alert("Failed to update settings.");
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

        const contacted = document.createElement("div");
        contacted.className = "green-check";
        contacted.id = "contacted";
        const contacted_label = document.createElement("label");
        contacted_label.for="contact_check";
        contacted_label.textContent = "Contacted";
        contacted_label.style="margin-left:10px";
        const contact_check = document.createElement("input");
        contact_check.type = "checkbox";
        contact_check.id="contact_check";
        contact_check.addEventListener("change", async () => {contacted_action();});
        contacted.appendChild(contact_check);
        contacted.appendChild(contacted_label);
        async function contacted_action(){
            const response = await fetch("/contacted", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ id: listing.id, selected:contact_check.checked}),
            });
            const result = await response.json();
            if(result.success && contact_check.checked)
                {
                    contacted.style = "background-color:#1b9458;"
                }
            else if(result.success && contact_check.checked==false)
                {
                    contacted.style = "background-color:none;"
                }      
        }
        if(listing.contacted){contact_check.checked = true;}
        contacted_action();

        const applied = document.createElement("div");
        applied.className = "green-check";
        applied.id = "applied";
        const applied_label = document.createElement("label");
        applied_label.for="applied_check";
        applied_label.textContent = "Applied";
        applied_label.style="margin-left:10px";
        const applied_check = document.createElement("input");
        applied_check.type = "checkbox";
        applied_check.id="applied_check";
        applied_check.addEventListener("change", async () =>{applied_action();});
        applied.appendChild(applied_check);
        applied.appendChild(applied_label);
        async function applied_action(){
            const response = await fetch("/applied", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ id: listing.id, selected:applied_check.checked}),
            });
            const result = await response.json();
            if(result.success && applied_check.checked)
                {
                    applied.style = "background-color:#1b9458;"
                }
            else if(result.success && applied_check.checked==false)
                {
                    applied.style = "background-color:none;"
                }      
        }
        if(listing.applied){applied_check.checked=true;}
        applied_action();
    
        // Create edit button separately to ensure proper placement
        const editButton = document.createElement("button");
        editButton.className = "edit-button";
        editButton.textContent = "Edit";
    
        editButton.addEventListener("click", () => {
            editPopup.classList.remove("hidden");
            console.log("editClick");
            editListingForm.dataset.listingId = listing.id;
            Object.keys(listing).forEach(key => {
                const input = editListingForm.querySelector(`[name=${key}]`);
                if (input) input.value = listing[key];
            });
        });

        // Create delete button separately to ensure proper placement
        const deleteButton = document.createElement("button");
        deleteButton.className = "delete-button";
        deleteButton.textContent = "Delete";
    
        deleteButton.addEventListener("click", async () => {
            console.log("deleteClick");
            const response = await fetch("/delete_listing", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ id: listing.id }),
            });
            const result = await response.json();
            if (result.success) {
                listingsContainer.removeChild(card);
            }
        });

        const buttonPanel = document.createElement("div");
        buttonPanel.style="margin-top:15px;margin-bottom:5px;";
        //buttonPanel.style="display:flex";
        buttonPanel.appendChild(editButton);
        buttonPanel.appendChild(deleteButton);
    
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
        card.appendChild(contacted);
        card.appendChild(applied);
        card.appendChild(buttonPanel);
        card.dataset.group = listing.group || "none"; // Default group
        
        // Radio Selection for Group
        const groupSelector = document.createElement("div");
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
                    if (result.success) card.dataset.group = input.value;
                });
        
                groupSelector.appendChild(input);
            });
        
        card.appendChild(groupSelector);
        
        // Handle Save Button
        editListingForm.addEventListener("submit", async (event) => {
            event.preventDefault();

            // Get the stored listing ID from the dataset
            const listingId = editListingForm.dataset.listingId;
            if (!listingId) {
                alert("Error: Listing ID is missing.");
                return;
            }
            
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
