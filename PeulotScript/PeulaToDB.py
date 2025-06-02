import sqlite3
import json
import os
from dotenv import load_dotenv
from llama_index.llms.gemini import Gemini

# --- Configuration ---
DB_NAME = "scout_activities.db"
load_dotenv()
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")


# --- Database Functions ---
def setup_database():
    """Creates the database and scout_activities table if they don't exist."""
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
            tags TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print(f"Database '{DB_NAME}' checked/created successfully.")


def add_activity_to_db(activity_data: dict):
    """Adds an activity to the SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        games_and_methods_text = activity_data.get("games_and_methods", "")

        db_values = {
            "topic": activity_data.get("topic") or "נושא לא צוין (שגיאת ניתוח)",
            "description": activity_data.get("description") or "תיאור לא נותח",
            "games_and_methods": games_and_methods_text,
            "age_group": activity_data.get("age_group") or "לא ידוע",
            "duration": activity_data.get("duration") or "לא ידוע",
            "materials": json.dumps(activity_data.get("materials", []), ensure_ascii=False),
            "tags": json.dumps(activity_data.get("tags", ["untagged"]), ensure_ascii=False)
        }

        print(f"  DEBUG (DB Insert): games_and_methods: ---BEGIN---\n{db_values['games_and_methods']}\n---END---")

        cursor.execute('''
            INSERT INTO scout_activities (topic, description, games_and_methods, age_group, duration, materials, tags)
            VALUES (:topic, :description, :games_and_methods, :age_group, :duration, :materials, :tags)
        ''', db_values)
        conn.commit()
        print(f"Activity (Topic: '{db_values['topic']}') added to the database.")
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()


# --- AI Parsing Function ---
def parse_activity_with_gemini(full_activity_input: str) -> dict | None:
    """
    Sends the user's full activity plan to Gemini for parsing metadata.
    Returns a dictionary with parsed metadata or None if an error occurs.
    """
    if not GEMINI_API_KEY:
        print("Error: GOOGLE_API_KEY not found. Please set it in your .env file.")
        return None

    try:
        # The DeprecationWarning is noted, but not the cause of the current JSON error.
        # You can update to llama-index-llms-google-genai later if desired.
        llm = Gemini(api_key=GEMINI_API_KEY, model_name="models/gemini-1.5-flash-latest")
    except Exception as e:
        print(f"Error initializing Gemini LLM: {e}")
        return None

    # Enhanced prompt to strongly emphasize JSON escaping rules
    prompt = f"""
    You are an expert Scout activity planner. Your task is to analyze the following complete Scout activity plan,
    which is provided in Hebrew, and extract specific metadata.
    The activity plan itself (the detailed steps, games, methods) will be stored separately.
    Your job is to provide the structured metadata based on this plan.

    Structure your output ONLY as a single, valid JSON object with the following keys:
    - "topic": (string) A concise title or topic for the activity in Hebrew, derived from the overall plan.
    - "description": (string) A summary of the activity's essence in Hebrew, based on the provided plan. This should capture the main goals or flow.
    - "age_group": (string) The most appropriate age group (e.g., "גילאי 9-11 (כיתות ד-ו)", "גילאי 12-13 (כיתות ז-ח)", "גילאי 14-15 (כיתות ט-י)", "גילאי 16-18 (שכבה בוגרת)"). Infer this from the plan if not explicit.
    - "duration": (string) Estimated total duration in minutes (e.g., "45 דקות", "110 דקות"). If timings are listed (e.g., "10דק X", "15דק Y"), sum them up. If no timings, make a reasonable estimate.
    - "materials": (LIST OF STRINGS) A list of materials needed, in Hebrew or English.
      Infer materials strongly implied (e.g., "משחק כדורגל" -> "כדור"; "משחק ביצים" -> "ביצים"; "כתיבה" -> "נייר", "כלי כתיבה"). If none, an empty list [].
    - "tags": (list of strings) A list of 3-5 descriptive keywords in English (e.g., ["teamwork", "outdoors", "icebreaker"]).

    CRITICAL JSON FORMATTING RULES:
    1. The entire output MUST be a SINGLE, VALID JSON object.
    2. All string values must be enclosed in double quotes (e.g., "example string").
    3. If a string value itself contains a double quote character ("), that inner double quote MUST be escaped with a backslash (e.g., "a string with an \\"inner quote\\" in it"). This is absolutely essential for JSON validity.
    4. Ensure all textual Hebrew content (topic, description, etc.) is in Hebrew.

    Full Activity Plan Provided:
    ---
    {full_activity_input}
    ---

    JSON Output (metadata only):
    """

    print("\nSending full activity plan to Gemini for parsing metadata...")
    try:
        response = llm.complete(prompt)
        response_text = response.text.strip()

        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        print(f"\nRaw Gemini response for metadata:\n{response_text}")

        parsed_data = json.loads(response_text)
        print("\nSuccessfully parsed metadata from Gemini.")
        return parsed_data
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from Gemini: {e}")
        # Provide context around the error position in the JSON string
        context_window = 40
        start_pos = max(0, e.pos - context_window)
        end_pos = min(len(e.doc), e.pos + context_window)
        error_snippet = e.doc[start_pos:end_pos]
        pointer = " " * (e.pos - start_pos) + "^"
        print(f"Problematic JSON snippet (char {e.pos}):\n...{error_snippet}...\n...{pointer}...")
        print(f"Complete raw response was: {response_text}")
        return None
    except Exception as e:
        print(f"An error occurred while communicating with Gemini: {e}")
        return None


# --- Main Application Logic ---
def main():
    """Main function to run the scout activity logger."""
    print("Scout Activity Logger")
    print("---------------------")

    setup_database()

    print("\nהזן את תיאור הפעולה המלא לצופים (בעברית).")
    print("כולל משחקים, מתודות, תזמונים, וכל פרט רלוונטי.")
    print("הפעולה המלאה תישמר בשלמותה, וגם תנותח על ידי AI לחילוץ פרטים נוספים.")
    print("כדי לסיים את הקלט, הקלד 'סיום' (או 'END') בשורה חדשה ולחץ Enter.")  # Clarified "בשורה חדשה"

    lines = []
    print(">> התחל להזין את הפעולה (הקלד 'סיום' או 'END' בשורה חדשה לסיום):")
    while True:
        try:
            line = input(">> ")
            # Check if the entire line (stripped and lowercased) is the terminator
            if line.strip().lower() in ["סיום", "end"]:
                break
            lines.append(line)
        except EOFError:
            print("\nקלט הסתיים (EOF).")
            break

    full_activity_text = "\n".join(lines)

    if not full_activity_text.strip():
        print("לא הוזן תיאור פעולה. התוכנית מסיימת.")
        return

    print(f"\n--- התקבל קלט פעולה מלאה ---")

    parsed_metadata_from_gemini = parse_activity_with_gemini(full_activity_text)

    final_activity_data = {}

    if parsed_metadata_from_gemini:
        final_activity_data = parsed_metadata_from_gemini.copy()
        final_activity_data["games_and_methods"] = full_activity_text
    else:
        print("\nאזהרה: ניתוח פרטי הפעולה על ידי Gemini נכשל.")
        print("הפעולה המלאה תישמר עם ערכי ברירת מחדל עבור שדות המטא-דאטה.")
        final_activity_data = {
            "games_and_methods": full_activity_text,
        }
        final_activity_data.setdefault("topic", "נושא לא צוין (שגיאת ניתוח)")
        final_activity_data.setdefault("description", "תיאור לא נותח")
        final_activity_data.setdefault("age_group", "לא ידוע")
        final_activity_data.setdefault("duration", "לא ידוע")
        final_activity_data.setdefault("materials", [])
        final_activity_data.setdefault("tags", ["parsing_failed"])

    print("\n--- נתונים סופיים לשמירה במסד הנתונים ---")
    for key, value in final_activity_data.items():
        if key == "games_and_methods":
            print(f"  {key}: ---BEGIN---\n{value}\n---END---")
        else:
            print(f"  {key}: {value}")
    print("---------------------------------------------")

    add_activity_to_db(final_activity_data)

    print("\nהתוכנית סיימה את פעולתה.")


if __name__ == "__main__":
    main()