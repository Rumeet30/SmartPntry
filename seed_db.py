#!/usr/bin/env python3
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

import sys
from google.cloud import firestore

# Hardcoded GCP Project ID string
PROJECT_ID = "qwiklabs-gcp-02-8ae187b0c087"


def seed_database():
    print(f"Connecting to Firestore for project: '{PROJECT_ID}'...")
    db = firestore.Client(project=PROJECT_ID)

    pantry_items = [
        {"name": "Olive Oil", "quantity": 500, "unit": "ml", "category": "pantry"},
        {"name": "Garlic", "quantity": 6, "unit": "cloves", "category": "produce"},
        {"name": "Eggs", "quantity": 12, "unit": "count", "category": "dairy"},
        {"name": "Jasmine Rice", "quantity": 2, "unit": "kg", "category": "pantry"},
        {"name": "Tomatoes", "quantity": 4, "unit": "count", "category": "produce"},
        {"name": "Chicken Breast", "quantity": 500, "unit": "grams", "category": "meat"},
        {"name": "Penne Pasta", "quantity": 400, "unit": "grams", "category": "pantry"},
        {"name": "Parmesan Cheese", "quantity": 150, "unit": "grams", "category": "dairy"},
    ]

    recipes = [
        {
            "title": "Garlic Chicken Rice Bowl",
            "description": "Seared chicken breast served over fluffy Jasmine rice with a rich garlic butter sauce.",
            "ingredients": ["Chicken Breast", "Jasmine Rice", "Garlic", "Olive Oil"],
            "cuisine": "Asian Fusion",
            "prep_time_mins": 25,
            "calories": 520,
        },
        {
            "title": "Tomato Basil Penne",
            "description": "Classic Italian pasta tossed in fresh tomato sauce, garlic, and freshly grated Parmesan cheese.",
            "ingredients": ["Penne Pasta", "Tomatoes", "Garlic", "Olive Oil", "Parmesan Cheese"],
            "cuisine": "Italian",
            "prep_time_mins": 20,
            "calories": 410,
        },
        {
            "title": "Savory Garlic Omelette",
            "description": "Quick fluffy omelette folded with minced garlic, tomatoes, and melted Parmesan.",
            "ingredients": ["Eggs", "Garlic", "Tomatoes", "Parmesan Cheese", "Olive Oil"],
            "cuisine": "Breakfast",
            "prep_time_mins": 10,
            "calories": 310,
        },
    ]

    print("Seeding pantry_items collection...")
    for item in pantry_items:
        doc_id = item["name"].lower().replace(" ", "_")
        db.collection("pantry_items").document(doc_id).set(item)
        print(f"  ✓ Added pantry item: {item['name']}")

    print("Seeding recipes collection...")
    for recipe in recipes:
        doc_id = recipe["title"].lower().replace(" ", "_")
        db.collection("recipes").document(doc_id).set(recipe)
        print(f"  ✓ Added recipe: {recipe['title']}")

    print("\nDatabase seeding completed successfully! 🎉")


if __name__ == "__main__":
    seed_database()
