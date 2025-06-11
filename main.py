from fastapi import FastAPI
from pydantic import BaseModel
import openai
import httpx
import re
from utils import get_api_key
from fastapi.responses import JSONResponse
import string
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

openai.api_key = get_api_key()
app = FastAPI()

# Mount static files (CSS, JS, images, etc.)
app.mount("/templates", StaticFiles(directory="templates"), name="templates")

# Setup templates
templates = Jinja2Templates(directory="templates")

class Query(BaseModel):
    message: str 
    ingredient: str = None # e.g. "How do I make a Margarita?"


def extract_drink_name(message: str) -> str:
    lowered = message.lower()
    cleaned = re.sub(r"how do i make|what's in a|tell me how to make|recipe for", "", lowered)
    cleaned = cleaned.strip()
    # Remove punctuation
    cleaned = cleaned.translate(str.maketrans('', '', string.punctuation))
    return cleaned

async def fetch_drink_info_by_name(drink_name: str):
    url = f"https://www.thecocktaildb.com/api/json/v1/1/search.php?s={drink_name}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()  # Remove 'await' here
    
async def fetch_drinks_by_ingredient(ingredient: str):
    url = f"https://www.thecocktaildb.com/api/json/v1/1/filter.php?i={ingredient}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        return await response.json()

def format_drink_data(drink):
    name = drink["strDrink"]
    ingredients = []
    for i in range(1, 16):
        ing = drink.get(f"strIngredient{i}")
        measure = drink.get(f"strMeasure{i}")
        if ing:
            if measure:
                ingredients.append(f"{measure.strip()} {ing.strip()}")
            else:
                ingredients.append(ing.strip())

    instructions = drink["strInstructions"]
    return f"{name}\nIngredients:\n- " + "\n- ".join(ingredients) + f"\n\nInstructions:\n{instructions}"

@app.post("/ask")
async def ask(query: Query):
    user_input = query.message
    search_term = extract_drink_name(user_input)

     # Check if ingredient-based search is requested
    if query.ingredient:
        ingredient = query.ingredient.lower()
        print(f"Ingredient search for: {ingredient}")
        data = await fetch_drinks_by_ingredient(ingredient)
        if not data or not data.get("drinks"):
            return JSONResponse(
                status_code=404,
                content={"response": f"Sorry, no drinks found with the ingredient '{ingredient}'."}
            )

        # If we find drinks, we return a list of drinks that use the ingredient
        drink_names = [drink["strDrink"] for drink in data["drinks"]]
        return {"response": f"Here are drinks that use {ingredient}: {', '.join(drink_names)}"}

    # Default name-based search
    print("Search term:", search_term)
    data = await fetch_drink_info_by_name(search_term)
    print("Raw API response:", data)

    if not data or data.get("drinks") is None:
        return JSONResponse(
            status_code=404,
            content={"response": f"Sorry, I couldn't find a drink for '{search_term}'."}
        )

    drink_info = format_drink_data(data["drinks"][0])

    messages = [
        {"role": "system", "content": "You are a helpful and friendly virtual bartender. Be informative, concise, and conversational."},
        {"role": "user", "content": f"The user asked: {user_input}"},
        {"role": "assistant", "content": f"Here's a drink recipe you can use:\n\n{drink_info}"},
        {"role": "user", "content": "Can you explain how to make it and offer any tips or variations?"}
    ]

    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",  # or "gpt-3.5-turbo"
        messages=messages,
        temperature=0.7,
        max_tokens=500,
    )

    
    return {"response": response.choices[0].message.content.strip()}

@app.get("/")
def read_root():
    return FileResponse("templates/front.html")
