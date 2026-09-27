# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import base64
import json
import uuid
from google.adk.tools import ToolContext
from google import genai
from google.genai import types
from google.cloud import firestore, storage

# Hardcoded project ID and bucket name as required
PROJECT_ID = "qwiklabs-gcp-02-8ae187b0c087"
BUCKET_NAME = "smart-pantry-agent-media-qwiklabs-gcp-02-8ae187b0c087"

db = firestore.Client(project=PROJECT_ID)



def list_pantry_items() -> str:
    """Gets the current inventory of items in the pantry.

    Returns:
        A JSON string listing all items currently stored in the pantry with quantity and unit.
    """
    items_ref = db.collection("pantry_items")
    docs = items_ref.stream()
    items = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        items.append(data)
    if not items:
        return "The pantry is currently empty."
    return json.dumps(items, indent=2)


def add_or_update_pantry_item(name: str, quantity: float, unit: str, category: str = "general") -> str:
    """Adds a new item or updates the quantity of an existing item in the pantry.

    Args:
        name: Name of the item (e.g., "Olive Oil", "Garlic", "Eggs").
        quantity: Amount of the item.
        unit: Unit of measurement (e.g., "tbsp", "cloves", "count", "grams").
        category: Food category (e.g., "produce", "spices", "dairy", "pantry").

    Returns:
        A confirmation message indicating the item was updated or added.
    """
    doc_id = name.lower().replace(" ", "_")
    doc_ref = db.collection("pantry_items").document(doc_id)
    item_data = {
        "name": name,
        "quantity": quantity,
        "unit": unit,
        "category": category
    }
    doc_ref.set(item_data, merge=True)
    return f"Successfully added/updated {name} ({quantity} {unit}) in the pantry."


def remove_pantry_item(name: str) -> str:
    """Removes an item from the pantry inventory.

    Args:
        name: Name of the item to remove.

    Returns:
        A confirmation message indicating deletion status.
    """
    doc_id = name.lower().replace(" ", "_")
    doc_ref = db.collection("pantry_items").document(doc_id)
    doc_ref.delete()
    return f"Removed {name} from the pantry."


def search_recipes(query: str = "") -> str:
    """Searches the recipe database by name, cuisine, or ingredient keyword.

    Args:
        query: Optional search keyword (e.g., "chicken", "pasta", "italian", "salad").

    Returns:
        A JSON string containing matching recipes.
    """
    recipes_ref = db.collection("recipes")
    docs = recipes_ref.stream()
    results = []
    q_lower = query.lower().strip()
    
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        if not q_lower:
            results.append(data)
        else:
            title = data.get("title", "").lower()
            cuisine = data.get("cuisine", "").lower()
            ingredients = [ing.lower() for ing in data.get("ingredients", [])]
            if q_lower in title or q_lower in cuisine or any(q_lower in ing for ing in ingredients):
                results.append(data)

    if not results:
        return f"No recipes found matching query '{query}'."
    return json.dumps(results, indent=2)


def add_recipe(title: str, description: str, ingredients: list[str], cuisine: str = "General", prep_time_mins: int = 20, calories: int = 400) -> str:
    """Adds a new recipe to the recipe collection in Firestore.

    Args:
        title: Title of the recipe (e.g., "Garlic Butter Pasta").
        description: Short summary or instructions for preparing the dish.
        ingredients: List of ingredient strings needed for the recipe.
        cuisine: Cuisine style (e.g., "Italian", "Mexican", "Asian").
        prep_time_mins: Total preparation and cooking time in minutes.
        calories: Estimated calories per serving.

    Returns:
        A confirmation message indicating the recipe was added.
    """
    doc_id = title.lower().replace(" ", "_")
    doc_ref = db.collection("recipes").document(doc_id)
    recipe_data = {
        "title": title,
        "description": description,
        "ingredients": ingredients,
        "cuisine": cuisine,
        "prep_time_mins": prep_time_mins,
        "calories": calories
    }
    doc_ref.set(recipe_data)
    return f"Successfully saved recipe '{title}' to Firestore."


def generate_grocery_shopping_list(recipe_name: str, servings: int = 1) -> str:
    """Generates a grocery shopping list by checking required recipe ingredients against current pantry inventory in Firestore.

    Args:
        recipe_name: Name or title keyword of the recipe (e.g., "Garlic Chicken Rice Bowl", "Penne").
        servings: Number of servings to scale ingredient requirements for. Default is 1.

    Returns:
        A JSON string detailing missing ingredients that need to be purchased vs items already in stock.
    """
    pantry_docs = db.collection("pantry_items").stream()
    pantry = {}
    for doc in pantry_docs:
        d = doc.to_dict()
        pantry[d.get("name", "").lower()] = d

    recipes_docs = db.collection("recipes").stream()
    matched_recipe = None
    r_query = recipe_name.lower().strip()
    for doc in recipes_docs:
        r = doc.to_dict()
        title = r.get("title", "").lower()
        if r_query in title or r_query in doc.id:
            matched_recipe = r
            break

    if not matched_recipe:
        return f"Could not find recipe matching '{recipe_name}' in the database."

    recipe_title = matched_recipe.get("title", recipe_name)
    raw_ingredients = matched_recipe.get("ingredients", [])

    missing_items = []
    in_stock_items = []

    for ing in raw_ingredients:
        if isinstance(ing, dict):
            ing_name = ing.get("name", "")
            req_qty = ing.get("quantity", 1) * servings
            unit = ing.get("unit", "")
        else:
            ing_name = str(ing)
            req_qty = 1 * servings
            unit = "portion"

        match = pantry.get(ing_name.lower())
        if match:
            avail_qty = match.get("quantity", 0)
            avail_unit = match.get("unit", unit)
            if avail_qty >= req_qty:
                in_stock_items.append(f"{ing_name}: {req_qty} {unit} needed (Have {avail_qty} {avail_unit})")
            else:
                needed = req_qty - avail_qty
                missing_items.append(f"{ing_name}: Need {needed} {unit} more (Have {avail_qty} {avail_unit})")
        else:
            missing_items.append(f"{ing_name}: Need {req_qty} {unit} (Not in pantry)")

    result = {
        "recipe": recipe_title,
        "servings": servings,
        "missing_ingredients_to_buy": missing_items,
        "items_in_stock": in_stock_items
    }
    return json.dumps(result, indent=2)


def fetch_online_recipes(query: str = "chicken") -> str:
    """Searches the free public TheMealDB API for online recipe ideas matching a query.

    Args:
        query: Ingredient or dish keyword to search online (e.g., "chicken", "pasta", "curry").

    Returns:
        A JSON string containing online recipe suggestions, ingredients, instructions, and image URLs.
    """
    import urllib.request
    import urllib.parse

    q = urllib.parse.quote(query.strip())
    url = f"https://www.themealdb.com/api/json/v1/1/search.php?s={q}"
    req = urllib.request.Request(url, headers={"User-Agent": "SmartPantryAgent/1.0"})

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            meals = data.get("meals")
            if not meals:
                return f"No online recipes found matching query '{query}'."

            results = []
            for meal in meals[:3]:
                ingredients = []
                for i in range(1, 21):
                    ing = meal.get(f"strIngredient{i}")
                    measure = meal.get(f"strMeasure{i}")
                    if ing and ing.strip():
                        ingredients.append(f"{measure.strip() if measure else ''} {ing.strip()}".strip())

                results.append({
                    "title": meal.get("strMeal"),
                    "category": meal.get("strCategory"),
                    "cuisine": meal.get("strArea"),
                    "instructions": meal.get("strInstructions", "")[:250] + "...",
                    "image_url": meal.get("strMealThumb"),
                    "youtube_url": meal.get("strYoutube"),
                    "ingredients": ingredients
                })
            return json.dumps(results, indent=2)
    except Exception as e:
        return f"Error fetching online recipes: {str(e)}"


def geocode_address(address: str) -> str:
    """Converts a street address or location name into geographic coordinates (latitude and longitude).

    Args:
        address: Location address or city name (e.g., "1600 Amphitheatre Pkwy, Mountain View, CA" or "San Francisco").

    Returns:
        A JSON string containing formatted address, latitude, and longitude.
    """
    import os
    import urllib.request
    import urllib.parse
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return "Error: GOOGLE_MAPS_API_KEY environment variable is not set."

    q = urllib.parse.quote(address.strip())
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={q}&key={api_key}"

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("status") != "OK" or not data.get("results"):
                return f"Geocoding failed for address '{address}'. Status: {data.get('status')}"

            result = data["results"][0]
            loc = result["geometry"]["location"]
            return json.dumps({
                "address": result.get("formatted_address"),
                "latitude": loc.get("lat"),
                "longitude": loc.get("lng")
            }, indent=2)
    except Exception as e:
        return f"Error executing geocode request: {str(e)}"


def find_nearby_places(latitude: float, longitude: float, place_type: str = "supermarket", radius_meters: float = 5000.0) -> str:
    """Finds nearby places of a given type around a coordinate using Places API (New).

    Args:
        latitude: Latitude of the center location.
        longitude: Longitude of the center location.
        place_type: Type of place to search for (e.g., "supermarket", "grocery_store", "bakery", "restaurant").
        radius_meters: Search radius in meters (default is 5000.0).

    Returns:
        A JSON string listing nearby places with key fields (name, address, location).
    """
    import os
    import urllib.request
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return "Error: GOOGLE_MAPS_API_KEY environment variable is not set."

    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location"
    }

    body = json.dumps({
        "includedTypes": [place_type],
        "maxResultCount": 5,
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": latitude,
                    "longitude": longitude
                },
                "radius": radius_meters
            }
        }
    }).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            raw_places = data.get("places", [])
            if not raw_places:
                return f"No nearby places of type '{place_type}' found within {radius_meters} meters."

            places = []
            for p in raw_places:
                display_name = p.get("displayName", {}).get("text", "")
                places.append({
                    "name": display_name,
                    "address": p.get("formattedAddress"),
                    "location": p.get("location")
                })
            return json.dumps(places, indent=2)
    except Exception as e:
        return f"Error executing Places API search: {str(e)}"


def generate_recipe_image(item_name: str, tool_context: ToolContext) -> str:
    """Generates an image for a food item or recipe using gemini-3.1-flash-lite-image in the global region,
    saves it to Playground Artifacts via tool_context.save_artifact, and uploads it to public Cloud Storage.

    Args:
        item_name: Name of the food item or recipe (e.g., "Garlic Chicken Rice Bowl").
        tool_context: ADK ToolContext injected by the agent framework.

    Returns:
        The public HTTPS URL of the uploaded image in Cloud Storage.
    """
    client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
    prompt = f"A professional, appetizing plating photo of {item_name}"

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=prompt,
        config=types.GenerateContentConfig(response_modalities=["IMAGE"])
    )

    img_bytes = response.candidates[0].content.parts[0].inline_data.data

    # 1. Save artifact for Playground Artifacts panel
    artifact_part = types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")
    filename = f"{item_name.lower().replace(' ', '_')}.jpg"
    tool_context.save_artifact(filename=filename, artifact=artifact_part)

    # 2. Upload to public GCS bucket directly from memory and return https URL
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob_name = f"recipe_{uuid.uuid4().hex[:8]}.jpg"
    blob = bucket.blob(blob_name)
    blob.upload_from_string(img_bytes, content_type="image/jpeg")

    return f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_name}"


def generate_recipe_video(item_name: str, tool_context: ToolContext) -> str:
    """Generates a short video for a food item or recipe using Google's Omni model (gemini-omni-flash-preview)
    in the global region, saves it to Playground Artifacts via tool_context.save_artifact, and uploads it to public Cloud Storage.

    Args:
        item_name: Name of the food item or recipe (e.g., "Sizzling Garlic Butter Shrimp").
        tool_context: ADK ToolContext injected by the agent framework.

    Returns:
        The public HTTPS URL of the uploaded video in Cloud Storage.
    """
    client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
    prompt = f"Generate a short video showing {item_name} being freshly prepared in a kitchen."

    response = client.interactions.create(
        model="gemini-omni-flash-preview",
        input=prompt
    )

    video_data_raw = response.output_video.data
    if isinstance(video_data_raw, str):
        video_bytes = base64.b64decode(video_data_raw)
    else:
        video_bytes = video_data_raw

    # 1. Save artifact for Playground Artifacts panel
    artifact_part = types.Part.from_bytes(data=video_bytes, mime_type="video/mp4")
    safe_name = item_name.lower().replace(' ', '_')
    filename = f"{safe_name}.mp4"
    tool_context.save_artifact(filename=filename, artifact=artifact_part)

    # 2. Upload to public GCS bucket directly from memory and return https URL
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob_name = f"video_{uuid.uuid4().hex[:8]}.mp4"
    blob = bucket.blob(blob_name)
    blob.upload_from_string(video_bytes, content_type="video/mp4")

    return f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_name}"





