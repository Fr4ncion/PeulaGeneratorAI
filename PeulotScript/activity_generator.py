import sqlite3
import json
import os
from dotenv import load_dotenv
from llama_index.llms.gemini import Gemini  # Or your preferred Gemini SDK
# For embeddings, you might use:
# from llama_index.embeddings.gemini import GeminiEmbedding
# from sentence_transformers import SentenceTransformer # For open-source models
# For a simple vector store (in-memory for this example):
# import faiss # Needs installation: pip install faiss-cpu (or faiss-gpu if you have a GPU)
# import numpy as np
import random
import re

# --- Configuration ---
DB_NAME = "scout_activities.db"
load_dotenv()
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")


# EMBEDDING_MODEL_NAME = "models/embedding-001" # Example for Gemini embedding
# EMBEDDING_MODEL_NAME_OPENSOURCE = 'paraphrase-multilingual-MiniLM-L12-v2' # Example

# --- Database Interaction ---
def get_all_activities_from_db():
    """Fetches all activities for embedding or initial retrieval pool."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # Access columns by name
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, topic, description, games_and_methods, age_group, duration, materials, tags, source_url FROM scout_activities")
    activities = cursor.fetchall()
    conn.close()
    return activities


def get_activity_by_id(activity_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM scout_activities WHERE id = ?", (activity_id,))
    activity = cursor.fetchone()
    conn.close()
    return activity


# --- Similarity/Retrieval (Conceptual - needs an embedding strategy) ---
# This section is simplified. In a real app, you'd pre-compute and store embeddings.
# For this example, we'll do a very basic keyword-based retrieval.
# A proper implementation would use vector embeddings.

def get_relevant_activities_keyword_based(user_prompt, all_activities, num_to_retrieve=3):
    """
    Simplified keyword-based retrieval.
    A proper RAG would use semantic search with embeddings.
    """
    scores = []
    prompt_keywords = set(re.findall(r'\b\w+\b', user_prompt.lower()))  # Simple keyword extraction

    for activity in all_activities:
        score = 0
        # Combine text from various fields for matching
        search_text = f"{activity['topic']} {activity['description']} {activity['games_and_methods']} {' '.join(json.loads(activity['tags'] or '[]'))}"
        activity_keywords = set(re.findall(r'\b\w+\b', search_text.lower()))

        common_keywords = prompt_keywords.intersection(activity_keywords)
        score = len(common_keywords)

        # Bonus for topic match
        if activity['topic'] and any(kw in activity['topic'] for kw in user_prompt.split()):
            score += 5

        scores.append((score, activity))

    # Sort by score descending
    scores.sort(key=lambda x: x[0], reverse=True)

    retrieved = [activity for score, activity in scores[:num_to_retrieve] if score > 0]
    print(f"Generator: Retrieved {len(retrieved)} activities based on keywords.")
    return retrieved


# --- LLM Interaction ---
def generate_activity_with_llm(user_prompt, user_duration_minutes=None, user_age_pref=None,
                               relevant_activities_context=""):
    if not GEMINI_API_KEY:
        print("Generator: Error - GOOGLE_API_KEY not found.")
        return None
    try:
        llm = Gemini(api_key=GEMINI_API_KEY, model_name="models/gemini-2.0-flash")  # Use a powerful model
    except Exception as e:
        print(f"Generator: Error initializing Gemini LLM: {e}")
        return None

    # Default values if not provided by user
    target_duration_text = f"{user_duration_minutes} דקות" if user_duration_minutes else "כ-120 דקות (שעתיים)"
    target_age_text = user_age_pref if user_age_pref else "גילאי 12-15 (כיתות ז-ט)"

    # --- The Core Prompt ---
    # This prompt incorporates your requirements and "internal questions" for the LLM.
    prompt = f"""
    אתה מומחה בכיר בתכנון פעולות לצופים, בעל יצירתיות רבה וידע נרחב במשחקים ומתודות.
    המשימה שלך היא ליצור תוכנית פעולה חדשה ומפורטת ב**עברית** על סמך בקשת המשתמש והדוגמאות הרלוונטיות שסופקו (אם ישנן).

    **בקשת המשתמש:** "{user_prompt}"
    **משך זמן מבוקש לפעולה:** {target_duration_text}
    **קבוצת גיל מבוקשת (אם צוינה, אחרת הערכה כללית):** {target_age_text}

    **לפני יצירת הפעולה, שקול לעצמך (ואל תציג את התשובות לשאלות אלו בפלט הסופי):**
    1.  **נושא מרכזי:** מהו הנושא העיקרי של הפעולה המבוקשת? כיצד הוא יכול לבוא לידי ביטוי? ({user_prompt})
    2.  **גיל יעד:** מהו הגיל המתאים ביותר לפעולה זו? ({target_age_text}) כיצד זה משפיע על בחירת המשחקים והשפה?
    3.  **אווירה ורצינות:** האם הפעולה צריכה להיות קלילה וכיפית, רצינית ומעמיקה, או שילוב?
    4.  **צריכת אנרגיה:** האם הפעולה צריכה להיות אנרגטית ופיזית, או רגועה יותר? (לשאוף לפעילות צורכת אנרגיה במידה מסוימת).
    5.  **מסרים וערכים:** אילו מסרים או ערכים ניתן לשלב בפעולה בהתאם לנושא?
    6.  **מגוון וייחודיות:** כיצ दीन ניתן ליצור רצף פעילויות מגוון, עם משחקים ייחודיים ולא שגרתיים, ולהימנע מחזרתיות?
    7.  **התאמת משחקים:** אילו משחקים ומתודות ספציפיים (כולל משחקים ייחודיים ולא רק הנפוצים ביותר) יתאימו לנושא, לגיל, ולאווירה? חשוב על משחקים שאולי לא מופיעים בדוגמאות אך רלוונטיים.
    8.  **זרימה והדרגתיות:** כיצד לבנות את הפעולה עם זרימה טובה בין השלבים? האם יש צורך בהקדמה, גוף פעולה וסיכום?
    9.  **חלוקת זמן:** כיצד לחלק את הזמן הכולל ({target_duration_text}) בין המתודות והמשחקים השונים באופן הגיוני? כל משחק/מתודה חייב לקבל הערכת זמן.
    10. **ציוד נדרש:** איזה ציוד יידרש לכל חלק בפעולה?

    **דוגמאות לפעולות רלוונטיות מהמאגר (אם סופקו, השתמש בהן כהשראה לסגנון, סוגי משחקים ורמת פירוט, אך צור תוכן חדש ומקורי):**
    --- דוגמאות ---
    {relevant_activities_context if relevant_activities_context else "לא סופקו דוגמאות קונקרטיות מהמאגר."}
    --- סוף דוגמאות ---

    **דרישות לפלט:**
    - הפלט חייב להיות תוכנית פעולה מפורטת **בעברית בלבד**.
    - התחל עם כותרת קצרה וקליטה לפעולה.
    - חלק את הפעולה לשלבים ברורים (למשל, פתיחה, משחק 1, דיון, משחק 2, סיכום).
    - **לכל שלב, ציין הערכת זמן משוערת (לדוגמה: "15 דקות - משחק X", "10 דקות - התארגנות"). סכום הזמנים הכולל צריך להתאים למשך המבוקש.**
    - תאר כל משחק או מתודה בצורה ברורה ומספקת. **השתדל להציע משחקים ייחודיים ומגוונים.**
    - הפעולה צריכה להיות **לא משעממת, בעלת אנרגיה מסוימת, ומותאמת לנושא ולגיל.**
    - אם נדרש ציוד, ציין אותו בסוף הפעולה או לצד כל מתודה רלוונטית.
    - הפעולה צריכה להיות **מקורית וחדשה**, ולא העתקה ישירה של הדוגמאות.

    **תוכנית הפעולה המפורטת:**
    """

    print("Generator: Sending request to Gemini for activity generation...")
    try:
        response = llm.complete(prompt)
        generated_text = response.text.strip()
        print("Generator: Received generated activity from Gemini.")
        return generated_text
    except Exception as e:
        print(f"Generator: An error occurred while communicating with Gemini: {e}")
        return None


# --- Main Application Logic ---
def main():
    print("מחולל פעולות לצופים (מבוסס מאגר קיים ו-AI)")
    print("--------------------------------------------")

    all_db_activities = get_all_activities_from_db()
    if not all_db_activities:
        print("שגיאה: לא נמצאו פעילויות במאגר הנתונים. המחולל לא יכול לעבוד ללא מאגר.")
        return

    print(f"טען {len(all_db_activities)} פעילויות מהמאגר.")

    while True:
        user_input_prompt = input(
            "\nהזן בקשה לפעולה (לדוגמה: 'פעולה על חשיבות עבודת צוות לשכב\"ג, שעה וחצי'): \nאו הקש Enter ליציאה.\n> ")
        if not user_input_prompt:
            break

        # Basic parsing for duration and age from prompt (can be improved)
        duration_match = re.search(r'(\d+)\s*(דקות|דקה|שעות|שעה וחצי|שעתיים)', user_input_prompt)
        user_duration_minutes = None
        if duration_match:
            num = int(duration_match.group(1))
            unit = duration_match.group(2)
            if "דקות" in unit or "דקה" in unit:
                user_duration_minutes = num
            elif "שעה וחצי" in unit:  # Handles "שעה וחצי" as specific case
                user_duration_minutes = 90
            elif "שעות" in unit or "שעה" in unit:
                user_duration_minutes = num * 60
            if user_duration_minutes:
                print(f"זיהוי משך: {user_duration_minutes} דקות.")

        # (Add similar regex for age if desired, e.g., "לשכבג", "לכיתות ז")
        user_age_pref = None  # Placeholder

        # 1. Retrieve relevant activities from DB (simplified keyword search for now)
        relevant_activities = get_relevant_activities_keyword_based(user_input_prompt, all_db_activities,
                                                                    num_to_retrieve=3)

        context_for_llm = ""
        if relevant_activities:
            context_for_llm += "להלן מספר פעולות דומות מהמאגר שיכולות לשמש כהשראה:\n\n"
            for i, act in enumerate(relevant_activities):
                context_for_llm += f"--- דוגמה {i + 1} (מקור: {act['source_url'] or 'לא ידוע'}) ---\n"
                context_for_llm += f"נושא: {act['topic']}\n"
                context_for_llm += f"תיאור קצר: {act['description']}\n"
                context_for_llm += f"משחקים ומתודות עיקריים:\n{act['games_and_methods'][:500]}...\n"  # Truncate for brevity
                context_for_llm += f"קבוצת גיל: {act['age_group']}\n"
                context_for_llm += f"משך: {act['duration']}\n"
                context_for_llm += "---------------------------------\n\n"
        else:
            print("לא נמצאו פעולות רלוונטיות במיוחד במאגר לבקשה זו, ה-AI ייצר מאפס.")

        # 2. Generate new activity using LLM with context
        print("\nמייצר פעולה חדשה, אנא המתן...\n")
        generated_activity_plan = generate_activity_with_llm(
            user_input_prompt,
            user_duration_minutes,
            user_age_pref,
            context_for_llm
        )

        if generated_activity_plan:
            print("\n--- פעולה מומלצת שנוצרה: ---")
            print(generated_activity_plan)
            print("----------------------------")
        else:
            print("מצטער, לא הצלחתי לייצר פעולה כרגע. נסה שוב או שנה את הבקשה.")

    print("\nתודה ולהתראות!")


if __name__ == "__main__":
    main()