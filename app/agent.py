# ruff: noqa
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

import json
from pathlib import Path
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory import VertexAiMemoryBankService
from google.adk.tools import VertexAiLoadProfilesTool
from google.genai import types

from a2ui.schema.manager import A2uiSchemaManager
from a2ui.basic_catalog.provider import BasicCatalog
from app.a2ui_utils import a2ui_callback

from app.tools import (
    list_pantry_items,
    add_or_update_pantry_item,
    remove_pantry_item,
    search_recipes,
    add_recipe,
    generate_grocery_shopping_list,
    fetch_online_recipes,
    geocode_address,
    find_nearby_places,
    generate_recipe_image,
    generate_recipe_video,
)

# Load Agent Engine resource name from deployment_metadata.json if available
metadata_file = Path(__file__).parent.parent / "deployment_metadata.json"
agent_engine_resource_name = None
agent_engine_id = None

if metadata_file.exists():
    try:
        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)
            agent_engine_resource_name = metadata.get("remote_agent_runtime_id")
            if agent_engine_resource_name:
                agent_engine_id = agent_engine_resource_name.split("/")[-1]
    except Exception as e:
        print(f"Warning: Could not read deployment_metadata.json: {e}")

code_executor = AgentEngineSandboxCodeExecutor(
    agent_engine_resource_name=agent_engine_resource_name
)

# Configure Vertex AI Memory Bank service and profile loading tool for deployment
memory_service = None
tools_list = [
    list_pantry_items,
    add_or_update_pantry_item,
    remove_pantry_item,
    search_recipes,
    add_recipe,
    generate_grocery_shopping_list,
    fetch_online_recipes,
    geocode_address,
    find_nearby_places,
    generate_recipe_image,
    generate_recipe_video,
]

if agent_engine_id:
    memory_service = VertexAiMemoryBankService(
        project="qwiklabs-gcp-02-8ae187b0c087",
        location="us-central1",
        agent_engine_id=agent_engine_id,
    )
    tools_list.append(VertexAiLoadProfilesTool(memory_service=memory_service))

# Configure A2UI v0.8 System Prompt Schema
schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are Smart Pantry & Recipe Concierge, a helpful assistant that manages home pantry inventories, "
        "suggests grounded recipes based on available ingredients, generates grocery shopping lists, fetches online recipes, "
        "locates nearby supermarkets, generates plating photos and short videos for recipes, and executes Python code safely in a sandbox when needed. "
        "ALWAYS check, remember, and enforce all user allergies and dietary restrictions. When the user mentions allergies (e.g. peanuts, dairy, gluten, shellfish, eggs), "
        "remember them in memory and ensure all recipe suggestions, shopping lists, and meal recommendations strictly avoid any allergens."
    ),
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        '{"Image": {"url": {"literalString": "https://..."}}}. Never point an '
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    tools=tools_list,
    code_executor=code_executor,
    after_model_callback=a2ui_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
