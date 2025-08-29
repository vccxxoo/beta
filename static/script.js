document.addEventListener("DOMContentLoaded", () => {
    const imageTab = document.getElementById("imageTab");
    const manualTab = document.getElementById("manualTab");
    const tabButtons = document.querySelectorAll(".tab-btn");
    const analyzeBtn = document.getElementById("analyzeBtn");
    const manualAnalyzeBtn = document.getElementById("manualAnalyzeBtn");
    const foodImage = document.getElementById("foodImage");
    const preview = document.getElementById("preview");
    const resultBox = document.getElementById("result");
    
    // Tab switching functionality
    tabButtons.forEach(button => {
        button.addEventListener("click", () => {
            const tab = button.dataset.tab;
            
            // Update active tab button
            tabButtons.forEach(btn => btn.classList.remove("active"));
            button.classList.add("active");
            
            // Show active tab content
            document.querySelectorAll(".tab-content").forEach(content => {
                content.classList.remove("active");
            });
            document.getElementById(`${tab}Tab`).classList.add("active");
        });
    });
    
    // Image preview functionality
    foodImage.addEventListener("change", function() {
        if (this.files && this.files[0]) {
            const reader = new FileReader();
            
            reader.onload = function(e) {
                preview.innerHTML = `<img src="${e.target.result}" alt="Food preview">`;
            }
            
            reader.readAsDataURL(this.files[0]);
        }
    });
    
    // Image analysis
    analyzeBtn.addEventListener("click", async () => {
        if (!foodImage.files.length) {
            resultBox.innerHTML = '<div class="error">Please select a food image first!</div>';
            return;
        }
        
        const quantity = document.getElementById("imageQuantity").value || 100;
        analyzeFood({ image: foodImage.files[0], quantity });
    });
    
    // Manual analysis
    manualAnalyzeBtn.addEventListener("click", async () => {
        const foodName = document.getElementById("foodName").value.trim();
        if (!foodName) {
            resultBox.innerHTML = '<div class="error">Please enter a food name!</div>';
            return;
        }
        
        const quantity = document.getElementById("manualQuantity").value || 100;
        analyzeFood({ foodName, quantity });
    });
    
    // Generic analysis function
    async function analyzeFood(data) {
        resultBox.innerHTML = '<div class="loading">Analyzing... Please wait.</div>';
        
        const formData = new FormData();
        
        if (data.image) {
            formData.append("file", data.image);
        } else if (data.foodName) {
            formData.append("food_name", data.foodName);
        }
        
        formData.append("quantity", data.quantity);
        
        try {
            const response = await fetch("http://127.0.0.1:5000/analyze", {
                method: "POST",
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`);
            }
            
            const result = await response.json();
            displayResults(result);
        } catch (error) {
            console.error("Fetch error:", error);
            resultBox.innerHTML = '<div class="error">❌ Failed to fetch. Is the backend running?</div>';
        }
    }
    
    // Display results in a formatted way
    function displayResults(data) {
        let html = `
            <h3>Analysis Results</h3>
            <p><strong>Food Identified:</strong> ${data.food || 'Unknown'}</p>
            <p><strong>Quantity:</strong> ${data.quantity} grams</p>
            <div class="nutrition-facts">
                <p><strong>Calories:</strong> ${data.calories || 'N/A'}</p>
                <p><strong>Protein:</strong> ${data.protein || 'N/A'}</p>
                <p><strong>Carbohydrates:</strong> ${data.carbs || 'N/A'}</p>
                <p><strong>Fat:</strong> ${data.fat || 'N/A'}</p>
            </div>
        `;
        
        if (data.additionalInfo) {
            html += `<div class="additional-info"><strong>Additional Information:</strong> ${data.additionalInfo}</div>`;
        }
        
        resultBox.innerHTML = html;
    }
});