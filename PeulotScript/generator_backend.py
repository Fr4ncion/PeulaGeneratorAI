import sqlite3
import json
import os
from dotenv import load_dotenv
from llama_index.llms.gemini import Gemini  # Or your preferred Gemini SDK
import random
import re
import time  # For simulating delay

# --- Configuration ---
DB_NAME = "scout_activities.db"  # Make sure this path is correct relative to where you run streamlit
load_dotenv()
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")


# --- Database Interaction (Simplified for frontend example) ---
def get_all_activities_from_db_simplified():
    """Simplified: Fetches a few activities for context example."""
    # In a real app, this would be your full DB loading and RAG indexing
    # For this example, we'll mock it or fetch a few random ones
    # Make sure your DB_NAME path is correct if you use this directly
    if not os.path.exists(DB_NAME):
        print("Backend: Database file not found. Cannot retrieve activities.")
        return []
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    # Fetch a few random activities for demo context
    cursor.execute(
        "SELECT id, topic, description, games_and_methods, age_group, duration, source_url FROM scout_activities ORDER BY RANDOM() LIMIT 3")
    activities = cursor.fetchall()
    conn.close()
    if activities:
        print(f"Backend: Loaded {len(activities)} sample activities for context.")
    return activities


def get_relevant_activities_for_frontend(user_prompt, num_to_retrieve=2):
    """
    Placeholder for RAG. Returns a formatted string of context.
    In a real app, this would use your actual RAG implementation.
    """
    # This is a MOCK RAG. Replace with your actual retrieval.
    print(f"Backend: Getting relevant activities for prompt: '{user_prompt[:50]}...'")
    # For now, let's just get a couple of random activities from the DB as context
    # Ideally, you'd use your keyword-based or embedding-based retrieval here.
    all_activities = get_all_activities_from_db_simplified()
    if not all_activities:
        return "לא נמצאו דוגמאות רלוונטיות במאגר."

    # Very basic keyword matching for demo
    prompt_keywords = set(user_prompt.lower().split())
    scored_activities = []
    for act in all_activities:
        activity_text = f"{act['topic']} {act['description']} {act['games_and_methods']}"
        activity_keywords = set(activity_text.lower().split())
        common = len(prompt_keywords.intersection(activity_keywords))
        scored_activities.append((common, act))

    scored_activities.sort(key=lambda x: x[0], reverse=True)

    relevant_ones = [act for score, act in scored_activities[:num_to_retrieve] if score > 0]
    if not relevant_ones and all_activities:  # if no good match, take some random ones
        relevant_ones = random.sample(all_activities, min(num_to_retrieve, len(all_activities)))

    context_str = "להלן מספר פעולות מהמאגר שיכולות לשמש כהשראה:\n\n"
    if relevant_ones:
        for i, act in enumerate(relevant_ones):
            context_str += f"--- דוגמה {i + 1} ---\n"
            context_str += f"נושא: {act['topic']}\n"
            # context_str += f"תיאור קצר: {act['description']}\n"
            context_str += f"תקציר משחקים:\n{act['games_and_methods'][:200]}...\n"
            context_str += "---------------------------------\n\n"
        return context_str
    return "לא סופקו דוגמאות קונקרטיות מהמאגר (או שלא נמצאו רלוונטיות)."


def generate_activity_with_llm_for_frontend(user_prompt, user_duration_minutes=None, user_age_pref=None,
                                            relevant_activities_context=""):
    print(f"Backend: Called generate_activity_with_llm_for_frontend for prompt: '{user_prompt[:50]}...'")
    if not GEMINI_API_KEY:
        return "שגיאה: מפתח ה-API של Gemini אינו מוגדר."
    try:
        # Ensure LlamaIndex's Gemini is used if that's your setup
        from llama_index.llms.gemini import Gemini
        llm = Gemini(api_key=GEMINI_API_KEY, model_name="models/gemini-2.0-flash")
    except Exception as e:
        return f"שגיאה ביצירת חיבור ל-Gemini: {e}"

    target_duration_text = f"{user_duration_minutes} דקות" if user_duration_minutes else "כ-120 דקות (שעתיים)"
    target_age_text = user_age_pref if user_age_pref else "גילאי 14-15 (כיתות ט-י)"

    prompt = f"""
    אתה מומחה בכיר בתכנון פעולות לצופים, בעל יצירתיות רבה וידע נרחב במשחקים ומתודות.
    המשימה שלך היא ליצור תוכנית פעולה חדשה ומפורטת ב**עברית** על סמך בקשת המשתמש והדוגמאות הרלוונטיות שסופקו (אם ישנן).

    **בקשת המשתמש:** "{user_prompt}"
    **משך זמן מבוקש לפעולה:** {target_duration_text}
    **קבוצת גיל מבוקשת (אם צוינה, אחרת הערכה כללית):** {target_age_text}

    **לפני יצירת הפעולה, שקול לעצמך (ואל תציג את התשובות לשאלות אלו בפלט הסופי):**
    1.  **נושא מרכזי:** מהו הנושא העיקרי של הפעולה המבוקשת? ({user_prompt})
    2.  **גיל יעד:** מהו הגיל המתאים ביותר לפעולה זו? ({target_age_text})
    3.  **אווירה ורצינות:** האם הפעולה צריכה להיות קלילה, רצינית, או שילוב?
    4.  **צריכת אנרגיה:** האם הפעולה צריכה להיות אנרגטית? (לשאוף לפעילות צורכת אנרגיה).
    5.  **מגוון וייחודיות:** כיצד ליצור רצף פעילויות מגוון, עם משחקים ייחודיים?
    6.  **חלוקת זמן:** כיצד לחלק את הזמן ({target_duration_text}) בין המתודות? כל משחק/מתודה חייב לקבל הערכת זמן.
    7.  **ציוד נדרש:** איזה ציוד יידרש?

    **דוגמאות לפעולות רלוונטיות מהמאגר (אם סופקו, השתמש בהן כהשראה אך צור תוכן חדש ומקורי):**
    --- דוגמאות ---
    {relevant_activities_context}
    --- סוף דוגמאות ---

    **דרישות לפלט:**
    - הפלט חייב להיות תוכנית פעולה מפורטת **בעברית בלבד**.
    - התחל עם כותרת קצרה וקליטה לפעולה.
    - חלק את הפעולה לשלבים ברורים עם הערכת זמן לכל שלב. סכום הזמנים צריך להתאים למשך המבוקש.
    - תאר כל משחק או מתודה בצורה ברורה. הצע משחקים ייחודיים ומגוונים.
    - הפעולה צריכה להיות לא משעממת, בעלת אנרגיה, ומותאמת לנושא ולגיל.
    - הפעולה צריכה להיות מקורית וחדשה.

    **תוכנית הפעולה המפורטת:**
    """
    print(f"Backend: Sending prompt to Gemini (length: {len(prompt)} chars)")
    try:
        # Simulate network delay for LLM call for better UX in Streamlit
        # time.sleep(2) # Remove this for actual LLM calls
        response = llm.complete(prompt)
        generated_text = response.text.strip()
        print(f"Backend: Received response from Gemini (length: {len(generated_text)} chars)")
        return generated_text
    except Exception as e:
        print(f"Backend: Gemini API call error: {e}")
        return f"שגיאה במהלך יצירת הפעולה מול Gemini: {e}"


# You can add simplified versions of other functions if needed by the orchestrator
# or call them directly if they don't have UI-blocking elements like input()

if __name__ == '__main__':
    # Test the backend functions
    print("Testing generator_backend.py...")
    sample_prompt = "פעולה כיפית לגיבוש כיתה ז, שעה"
    context = get_relevant_activities_for_frontend(sample_prompt)
    print("\nSample Context:\n", context)
    # result = generate_activity_with_llm_for_frontend(sample_prompt, user_duration_minutes=60, relevant_activities_context=context)
    # print("\nGenerated Activity:\n", result)