from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

# Optional config via environment variables
HF_API_KEY = os.getenv('HF_API_KEY')
USDA_API_KEY = os.getenv('USDA_API_KEY')

# If API keys are not provided, the server will return demo values.
HF_MODEL = "nateraw/food"  # default model name on Hugging Face

@app.route("/analyze", methods=["POST"])
def analyze():
    quantity = request.form.get("quantity", 100, type=float)
    
    # Check if we have an image or a food name
    if 'file' in request.files:
        image_file = request.files['file']
        
        # Step 1: classify image using Hugging Face Inference API if key provided
        label = None
        if HF_API_KEY:
            try:
                headers = {"Authorization": f"Bearer {HF_API_KEY}"}
                # send raw image bytes
                resp = requests.post(
                    f"https://api-inference.huggingface.co/models/{HF_MODEL}", 
                    headers=headers, 
                    data=image_file.read(), 
                    timeout=60
                )
                resp.raise_for_status()
                preds = resp.json()
                if isinstance(preds, list) and len(preds) > 0 and isinstance(preds[0], dict):
                    label = preds[0].get('label')
                image_file.seek(0)  # Reset file pointer for potential reuse
            except Exception as e:
                print('HF error', e)
                label = None
    else:
        # Use the provided food name
        label = request.form.get("food_name", "").strip().lower()
    
    # If no label could be determined
    if not label:
        return jsonify({
            "error": "Could not identify food. Please try a clearer image or specify the food name."
        }), 400
    
    # Step 2: fetch nutrition from USDA if key provided
    nutrition = {}
    additional_info = ""
    
    if USDA_API_KEY:
        try:
            # First search for the food
            search_response = requests.get(
                "https://api.nal.usda.gov/fdc/v1/foods/search",
                params={
                    "api_key": USDA_API_KEY, 
                    "query": label, 
                    "pageSize": 5,  # Get more results to find the best match
                    "dataType": "Survey (FNDDS),SR Legacy,Foundation"
                },
                timeout=30
            )
            search_response.raise_for_status()
            data = search_response.json()
            foods = data.get('foods') or []
            
            if foods:
                # Try to find the best match
                best_match = None
                for food in foods:
                    if label.lower() in food.get('description', '').lower():
                        best_match = food
                        break
                
                # If no exact match, use the first result
                if not best_match and foods:
                    best_match = foods[0]
                
                if best_match:
                    # Get additional info
                    additional_info = best_match.get('description', '')
                    
                    # Get nutrients and scale by quantity
                    nutrients = best_match.get('foodNutrients', [])
                    for n in nutrients:
                        name = (n.get('nutrientName') or '').lower()
                        val = n.get('value', 0)
                        unit = n.get('unitName') or ''
                        
                        # Scale the value based on quantity (assuming original is for 100g)
                        scaled_val = val * (quantity / 100)
                        
                        if 'energy' in name or 'calories' in name:
                            nutrition['calories'] = f"{scaled_val:.1f} {unit}"
                        elif 'protein' in name:
                            nutrition['protein'] = f"{scaled_val:.1f} {unit}"
                        elif 'carbohydrate' in name:
                            nutrition['carbs'] = f"{scaled_val:.1f} {unit}"
                        elif 'fat' in name and 'total' in name:
                            nutrition['fat'] = f"{scaled_val:.1f} {unit}"
        except Exception as e:
            print('USDA error', e)
            nutrition = {}
    
    # If no nutrition data found, use generic values based on food type
    if not nutrition:
        # These are example values per 100g - will be scaled by quantity
        generic_nutrition = {
            "apple": {"calories": 52, "protein": 0.3, "carbs": 14, "fat": 0.2},
            "banana": {"calories": 89, "protein": 1.1, "carbs": 23, "fat": 0.3},
            "pizza": {"calories": 266, "protein": 11, "carbs": 33, "fat": 10},
            "chicken": {"calories": 165, "protein": 31, "carbs": 0, "fat": 3.6},
            "rice": {"calories": 130, "protein": 2.7, "carbs": 28, "fat": 0.3},
            "bread": {"calories": 265, "protein": 9, "carbs": 49, "fat": 3.2},
        }
        
        # Find the closest match
        matched_food = None
        for food_key in generic_nutrition:
            if food_key in label.lower():
                matched_food = food_key
                break
        
        if matched_food:
            nut = generic_nutrition[matched_food]
            # Scale values based on quantity
            scale = quantity / 100
            nutrition = {
                "calories": f"{nut['calories'] * scale:.1f} kcal",
                "protein": f"{nut['protein'] * scale:.1f} g",
                "carbs": f"{nut['carbs'] * scale:.1f} g",
                "fat": f"{nut['fat'] * scale:.1f} g"
            }
            additional_info = "Note: These are generic values for this food type. For accurate results, provide USDA API key."
        else:
            # Fallback to pizza nutrition
            scale = quantity / 100
            nutrition = {
                "calories": f"{266 * scale:.1f} kcal",
                "protein": f"{11 * scale:.1f} g",
                "carbs": f"{33 * scale:.1f} g",
                "fat": f"{10 * scale:.1f} g"
            }
            additional_info = "Note: Using generic nutrition values. For accurate results, provide USDA API key."

    return jsonify({
        "food": label,
        "quantity": quantity,
        "calories": nutrition.get("calories"),
        "protein": nutrition.get("protein"),
        "fat": nutrition.get("fat"),
        "carbs": nutrition.get("carbs"),
        "additionalInfo": additional_info
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)