import os
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI # <-- MODIFIED: Import OpenAI

# --- 1. INITIAL SETUP (MODIFIED FOR OPENROUTER) ---
# Load environment variables from .env file
load_dotenv()

# Configure the OpenAI client to point to OpenRouter
api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    raise ValueError("OPENROUTER_API_KEY not found in .env file")

client = OpenAI(
    api_key=api_key,
    base_url="https://openrouter.ai/api/v1" # This is the crucial part
)

# Initialize the FastAPI app
app = FastAPI(
    title="Smart Task Planner API",
    description="An API to break down goals into actionable tasks using AI.",
    version="1.0.0"
)

# --- 2. Pydantic Models for Request & Response ---
class GoalRequest(BaseModel):
    goal: str
    duration: str

# --- 3. The LLM Prompting Logic (MODIFIED FOR OPENROUTER/DEEPSEEK) ---
def get_llm_plan(goal: str, duration: str) -> dict:
    """
    Generates a task plan by calling an OpenRouter model.
    """
    # The model name from OpenRouter
    model_name = "deepseek/deepseek-r1-0528-qwen3-8b" 

    prompt = f"""
    Break down the following user goal into a detailed project plan.
    Goal: "{goal}"
    Timeframe: "{duration}"

    Provide the response as a valid JSON object with a single key "tasks".
    The value should be an array of task objects. Each task object must have the following fields:
    - "id": A unique integer identifier for the task.
    - "task_name": A short, descriptive name for the task.
    - "description": A one-sentence explanation of what needs to be done.
    - "duration_days": An estimated integer for how many days the task will take.
    - "dependencies": An array of integer IDs of tasks that must be completed before this one can start. An empty array [] means it has no dependencies.

    Ensure the total duration of all tasks logically fits within the user's requested timeframe.
    The output should be only the JSON object, with no other text before or after it.
    """

    try:
        print(f"--- Sending Prompt to OpenRouter (Model: {model_name}) ---")
        
        # This is the new OpenAI-compatible API call
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "user", "content": prompt},
            ],
            # This is a powerful feature to force JSON output!
            response_format={"type": "json_object"}, 
        )

        # The response content is now in a different place
        response_content = response.choices[0].message.content
        
        print("--- Raw Response from OpenRouter ---")
        print(response_content)
        print("--------------------------------")
        
        plan = json.loads(response_content)
        return plan
    except Exception as e:
        print(f"!!! AN ERROR OCCURRED !!!: {e}")
        return None

# --- 4. The API Endpoint (No changes needed here) ---
@app.post("/generate-plan", tags=["Planner"])
async def generate_plan_endpoint(request: GoalRequest):
    if not request.goal or not request.duration:
        raise HTTPException(status_code=400, detail="Goal and duration cannot be empty.")

    generated_plan = get_llm_plan(request.goal, request.duration)

    if not generated_plan or "tasks" not in generated_plan:
        raise HTTPException(status_code=500, detail="Failed to generate a valid plan from the AI model.")
    
    return generated_plan

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the Smart Task Planner API. Go to /docs to see the endpoints."}