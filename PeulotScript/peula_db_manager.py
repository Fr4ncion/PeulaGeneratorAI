import sqlite3
import json
import os
from dotenv import load_dotenv
# Assuming you are using the LlamaIndex Gemini wrapper
# If you switched to google.generativeai, adjust imports accordingly
from llama_index.llms.gemini import Gemini

# --- Configuration ---
DB_NAME = "scout_activities.db" # Ensure this matches
load_dotenv() # Ensure .env file is in the same directory as the new orchestrator script or accessible
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- Database Functions ---
def setup_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scout_activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            description TEXT,
            games_and_methods TEXT NOT NULL,
            age_group TEXT,
            duration TEXT,
            materials TEXT,
            tags TEXT,
            source_url TEXT UNIQUE  -- Added to store the URL and prevent duplicates
        )
    ''')
    conn.commit()
    conn.close()
    print(f"DBManager: Database '{DB_NAME}' checked/created successfully.")

def add_activity_to_db(activity_data: dict):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        db_values = {
            "topic": activity_data.get("topic") or "נושא לא צוין (שגיאת ניתוח)",
            "description": activity_data.get("description") or "תיאור לא נותח",
            "games_and_methods": activity_data.get("games_and_methods", ""), # Full scraped text
            "age_group": activity_data.get("age_group") or "לא ידוע",
            "duration": activity_data.get("duration") or "לא ידוע",
            "materials": json.dumps(activity_data.get("materials", []), ensure_ascii=False),
            "tags": json.dumps(activity_data.get("tags", ["untagged"]), ensure_ascii=False),
            "source_url": activity_data.get("source_url") or "no URL source" # Store the source URL
        }
        cursor.execute('''
            INSERT INTO scout_activities 
            (topic, description, games_and_methods, age_group, duration, materials, tags, source_url)
            VALUES (:topic, :description, :games_and_methods, :age_group, :duration, :materials, :tags, :source_url)
        ''', db_values)
        conn.commit()
        print(f"DBManager: Activity (Topic: '{db_values['topic']}', URL: {db_values['source_url']}) added to the database.")
        return True
    except sqlite3.IntegrityError: # This will catch UNIQUE constraint violation for source_url
        print(f"DBManager: Activity from URL '{activity_data.get('source_url')}' already exists in the database.")
        return False
    except sqlite3.Error as e:
        print(f"DBManager: Database error: {e} for URL {activity_data.get('source_url')}")
        return False
    finally:
        conn.close()

# --- AI Parsing Function ---
def parse_activity_with_gemini(full_activity_input: str, source_url_for_context:str = "N/A") -> dict | None:
    if not GEMINI_API_KEY:
        print("DBManager: Error - GOOGLE_API_KEY not found.")
        return None
    try:
        llm = Gemini(api_key=GEMINI_API_KEY, model_name="models/gemini-1.5-flash-latest")
    except Exception as e:
        print(f"DBManager: Error initializing Gemini LLM: {e}")
        return None

    prompt = f"""
    You are an expert Scout activity planner. Analyze the following Scout activity plan,
    extracted from the URL: {source_url_for_context}
    Provide structured metadata. The activity plan itself (games_and_methods) will be stored from the raw input.

    Output ONLY as a single, VALID JSON object with keys: "topic", "description", "age_group", "duration", "materials", "tags".
    - "topic": (string) Concise activity title in Hebrew.
    - "description": (string) Brief summary in Hebrew.
    - "age_group": (string) e.g., "גילאי 9-11". Infer if not explicit.
    - "duration": (string) e.g., "45 דקות". Sum timings or estimate.
    - "materials": (LIST OF STRINGS) Materials in Hebrew/English. Infer if implied (e.g., "משחק כדורגל" -> "כדור"). Empty list [] if none.
    - "tags": (list of strings) 3-5 English keywords (e.g., ["teamwork", "outdoors"]).

    CRITICAL JSON FORMATTING: Ensure inner double quotes in strings are escaped (e.g., "a string with an \\"inner quote\\"").

    Full Activity Plan Provided:
    ---
    {full_activity_input}
    ---
    JSON Output (metadata only):
    """
    print(f"DBManager: Sending activity from {source_url_for_context} to Gemini for parsing...")
    try:
        response = llm.complete(prompt)
        response_text = response.text.strip()
        if response_text.startswith("```json"): response_text = response_text[7:]
        if response_text.endswith("```"): response_text = response_text[:-3]
        response_text = response_text.strip()

        # print(f"DBManager: Raw Gemini response for metadata:\n{response_text}") # For debugging
        parsed_data = json.loads(response_text)
        print("DBManager: Successfully parsed metadata from Gemini.")
        return parsed_data
    except json.JSONDecodeError as e:
        print(f"DBManager: Error decoding JSON from Gemini for {source_url_for_context}: {e}")
        # ... (optional: print error snippet as before) ...
        return None
    except Exception as e:
        print(f"DBManager: An error occurred with Gemini for {source_url_for_context}: {e}")
        return None

if __name__ == "__main__":
    print("Testing peula_db_manager.py functions...")
    setup_database()
    # Example test (optional)
    # test_activity_text = "משחק כדורגל 30 דקות. חומרים: כדור. גיל: 9-10"
    # parsed = parse_activity_with_gemini(test_activity_text, "http://example.com/test")
    # if parsed:
    #     parsed["games_and_methods"] = test_activity_text
    #     parsed["source_url"] = "http://example.com/test_unique"
    #     add_activity_to_db(parsed)
    # else:
    #     print("Test parsing failed.")