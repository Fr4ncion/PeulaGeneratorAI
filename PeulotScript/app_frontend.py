import streamlit as st
import re
import generator_backend

st.set_page_config(
    page_title="מחולל פעולות לצופים",
    page_icon="⚜️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS for RTL Optimization ---
st.markdown("""
<style>
    /* 1. Global RTL for the entire application flow */
    body, .main, .stApp {
        direction: rtl !important;
    }

    /* 2. Main content container within Streamlit */
    .main .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 1.5rem !important;
        padding-left: 1.5rem !important; /* Adjust padding for RTL */
        padding-right: 1.5rem !important;
    }

    /* 3. Headers and Titles */
    h1, h2, h3, h4, h5, h6 {
        text-align: right !important; /* Default for headers */
        width: 100%; /* Ensure they take up space to align right */
    }
    /* Specific override for the main page title to be centered */
    .main .block-container > div:first-child > div:first-child > div:first-child h1 {
        text-align: center !important;
        color: #006400; /* Dark Green */
        margin-bottom: 0.5rem;
    }
    /* Subtitle paragraph below main title */
    .main .block-container > div:first-child > div:first-child > div:nth-child(2) p {
        text-align: center !important;
        color: grey;
        margin-bottom: 2rem;
    }

    /* 4. Streamlit Widget Labels (text_area, text_input, selectbox, radio, etc.) */
    /* This targets the div that often wraps the label */
    div[data-testid="stWidgetLabel"] label p, /* Standard label */
    div[data-testid="stForm"] div[data-testid="stWidgetLabel"] label p /* Label inside a form */
    {
        direction: rtl !important;
        text-align: right !important;
        width: 100% !important; /* Make label span full width to align text */
        margin-bottom: 0.25rem !important;
        padding: 0 !important; /* Reset padding if any */
    }

    /* 5. Input Fields Content */
    .stTextArea textarea, 
    .stTextInput input,
    .stSelectbox div[data-baseweb="select"] > div, /* Displayed value in selectbox */
    .stSelectbox div[data-baseweb="select"] input /* Search input within selectbox */
    {
        direction: rtl !important;
        text-align: right !important;
        font-size: 1.05rem !important; /* Slightly larger font for inputs */
    }
    .stTextArea textarea { border: 1px solid #ccc; border-radius: 5px; }
    .stTextInput input { border: 1px solid #ccc; border-radius: 5px; }

    /* 6. Buttons */
    /* Generate Button (st.form_submit_button) */
    .stButton button[kind="formSubmit"], .stButton button[kind="secondary"] {
        background-color: #2E8B57 !important; /* Sea Green */
        color: white !important;
        border-radius: 5px !important;
        border: none !important;
        padding: 10px 24px !important;
        font-size: 16px !important;
        margin: 10px 0px !important; /* More vertical margin */
        cursor: pointer !important;
        width: 100% !important;
    }
    .stButton button[kind="formSubmit"]:hover, .stButton button[kind="secondary"]:hover {
        background-color: #257247 !important; /* Darker Sea Green */
    }

    /* Custom HTML Copy Button */
    .custom-copy-button {
        background-color: #4CAF50 !important;
        color: white !important;
        padding: 8px 16px !important;
        border-radius: 5px !important;
        border: none !important;
        cursor: pointer !important;
        font-size: 1em !important;
        margin-top: 15px !important; /* More space above copy button */
        margin-bottom: 5px !important; /* Space below copy button */
        display: inline-block !important;
    }
    .custom-copy-button:hover { background-color: #45a049 !important; }
    #copyFeedback { /* Feedback message for copy button */
        margin-right: 10px; 
        display: none; 
        font-size: 0.9em;
    }


    /* 7. Output Container for Generated Activity */
    .output-container {
        direction: rtl !important;
        background-color: #f0f2f6; /* Light mode background */
        color: #333333; /* Light mode text */
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 20px;
        margin-top: 20px;
        white-space: pre-wrap; /* Preserve formatting */
        text-align: right;
        font-size: 1.1rem;
        line-height: 1.8;
    }
    /* Dark Mode specific styles for output container */
    body[data-theme="dark"] .output-container {
        background-color: #262730 !important; /* Darker background for dark mode */
        color: #FAFAFA !important; /* Lighter text for dark mode */
        border: 1px solid #333 !important;
    }

    /* 8. Status Messages (info, warning, success, error) */
    div[data-testid="stAlert"] { /* General alert box */
        text-align: right !important;
        direction: rtl !important;
    }
    div[data-testid="stAlert"] p { /* Text inside alert box */
        text-align: right !important;
        direction: rtl !important;
    }


    /* 9. Footer text */
    .main .block-container > div:last-child > div > div > p { /* More robust selector for footer */
        text-align: center !important;
        font-size: 0.9em;
        color: grey;
        width: 100%;
        margin-top: 2rem;
    }

    /* 10. Sidebar */
    div[data-testid="stSidebarUserContent"] {
         direction: rtl !important;
         text-align: right !important; /* Default text align for sidebar content */
    }
    /* Ensure all direct children text elements in sidebar are also RTL aligned */
    div[data-testid="stSidebarUserContent"] > * {
        text-align: right !important;
    }
    div[data-testid="stSidebarUserContent"] h1, 
    div[data-testid="stSidebarUserContent"] h2,
    div[data-testid="stSidebarUserContent"] h3,
    div[data-testid="stSidebarUserContent"] p,
    div[data-testid="stSidebarUserContent"] li,
    div[data-testid="stSidebarUserContent"] strong,
    div[data-testid="stSidebarUserContent"] .stMarkdown p { /* Paragraphs inside st.markdown in sidebar */
        text-align: right !important;
        direction: rtl !important; /* Redundant but for emphasis */
    }
    /* Correct alignment for bullet points in sidebar */
    div[data-testid="stSidebarUserContent"] ul {
        padding-right: 20px !important; /* Standard RTL padding for lists */
        padding-left: 0 !important;
    }
     div[data-testid="stSidebarUserContent"] ol {
        padding-right: 20px !important; 
        padding-left: 0 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- JavaScript for Copy to Clipboard ---
copy_js_script = """
<script>
function fallbackCopyTextToClipboard(text, elementIdForFeedback) {
    var textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.style.position = "fixed"; document.body.appendChild(textArea);
    textArea.focus(); textArea.select();
    try {
        var successful = document.execCommand('copy');
        var msg = successful ? 'הפעולה הועתקה ללוח!' : 'שגיאה בהעתקה (fallback).';
        if (elementIdForFeedback) showCopyFeedback(msg, successful, elementIdForFeedback); else alert(msg);
    } catch (err) {
        var errorMsg = 'שגיאה קריטית בהעתקה (fallback): ' + err;
        if (elementIdForFeedback) showCopyFeedback(errorMsg, false, elementIdForFeedback); else alert(errorMsg);
    }
    document.body.removeChild(textArea);
}
async function copyActivityToClipboard(elementId, feedbackElementId) {
    var outputDiv = document.getElementById(elementId);
    if (!outputDiv) {
        if (feedbackElementId) showCopyFeedback("שגיאה: רכיב הפלט לא נמצא.", false, feedbackElementId);
        else alert("שגיאה: רכיב הפלט לא נמצא.");
        return;
    }
    var textToCopy = outputDiv.innerText; 
    if (!navigator.clipboard) { fallbackCopyTextToClipboard(textToCopy, feedbackElementId); return; }
    try {
        await navigator.clipboard.writeText(textToCopy);
        if (feedbackElementId) showCopyFeedback("הפעולה הועתקה ללוח!", true, feedbackElementId);
        else alert("הפעולה הועתקה ללוח!");
    } catch (err) {
        console.error('Async: Could not copy text: ', err);
        fallbackCopyTextToClipboard(textToCopy, feedbackElementId);
    }
}
function showCopyFeedback(message, success, elementId) {
    var feedbackEl = document.getElementById(elementId);
    if (feedbackEl) {
        feedbackEl.innerText = message;
        feedbackEl.style.color = success ? "green" : "red";
        feedbackEl.style.display = "inline-block"; /* Changed to inline-block */
        feedbackEl.style.marginLeft = "10px"; /* Add some space from the button */
        setTimeout(function() { feedbackEl.style.display = "none"; }, 3000);
    } else { alert(message); }
}
</script>
"""
st.components.v1.html(copy_js_script, height=0)

# --- Main Application ---
st.title("מחולל פעולות לצופים")  # CSS Selector for H1 title applies
st.markdown("<p>הזן בקשה ותן ל-AI ליצור עבורך פעולה מותאמת!</p>", unsafe_allow_html=True)  # CSS for p applies

if 'generated_activity_text' not in st.session_state:
    st.session_state.generated_activity_text = ""
if 'show_activity' not in st.session_state:
    st.session_state.show_activity = False

with st.form(key="activity_form"):
    prompt_text = st.text_area(
        "✍️ תאר את הפעולה שברצונך ליצור:",
        height=100,
        placeholder="לדוגמה: פעולה בנושא אחריות אישית לשכבה בוגרת, כשעה וחצי, שתהיה מאתגרת ומגבשת."
    )
    # Using st.columns might sometimes be tricky with RTL for visual order vs logical order.
    # For simple side-by-side, it should be okay if content within columns is RTL.
    col1, col2 = st.columns(2)
    with col1:
        duration_options = ["לא צוין (ברירת מחדל: שעתיים)", "30 דקות", "45 דקות", "60 דקות (שעה)", "75 דקות",
                            "90 דקות (שעה וחצי)", "120 דקות (שעתיים)", "150 דקות (שעתיים וחצי)"]
        duration_map = {
            "לא צוין (ברירת מחדל: שעתיים)": None, "30 דקות": 30, "45 דקות": 45, "60 דקות (שעה)": 60,
            "75 דקות": 75, "90 דקות (שעה וחצי)": 90, "120 דקות (שעתיים)": 120, "150 דקות (שעתיים וחצי)": 150
        }
        selected_duration_text = st.selectbox("⏳ משך הפעולה המשוער:", options=duration_options, index=0)
        user_duration_minutes = duration_map[selected_duration_text]
    with col2:
        age_group_options = ["לא צוין (ברירת מחדל: ~גיל 14)", "כיתות ד-ו (9-11)", "כיתות ז-ח (12-13)",
                             "כיתות ט-י (14-15)", "שכבה בוגרת (16-18)"]
        age_map = {
            "לא צוין (ברירת מחדל: ~גיל 14)": "גילאי 14-15 (כיתות ט-י)",
            "כיתות ד-ו (9-11)": "גילאי 9-11 (כיתות ד-ו)", "כיתות ז-ח (12-13)": "גילאי 12-13 (כיתות ז-ח)",
            "כיתות ט-י (14-15)": "גילאי 14-15 (כיתות ט-י)", "שכבה בוגרת (16-18)": "גילאי 16-18 (שכבה בוגרת)"
        }
        selected_age_text = st.selectbox("🎯 קבוצת גיל:", options=age_group_options, index=0)
        user_age_pref = age_map[selected_age_text]

    submit_button = st.form_submit_button(label="🚀 צור לי פעולה!")  # Uses .stButton button[kind="formSubmit"] style

if submit_button:
    if not prompt_text.strip():
        st.warning("אנא הזן תיאור לבקשת הפעולה.")
        st.session_state.show_activity = False
    else:
        st.session_state.show_activity = True
        st.session_state.generated_activity_text = ""  # Clear previous activity
        # Using placeholders for spinner messages for better control
        spinner_placeholder = st.empty()
        with spinner_placeholder.status("מעבד את הבקשה...", expanded=True) as status_main:
            st.write("מחפש פעילויות דומות במאגר...")
            relevant_context = generator_backend.get_relevant_activities_for_frontend(prompt_text)
            st.write("הקסם קורה... Gemini חושב על פעולה מושלמת! 🧙‍♂️")
            generated_activity = generator_backend.generate_activity_with_llm_for_frontend(
                user_prompt=prompt_text,
                user_duration_minutes=user_duration_minutes,
                user_age_pref=user_age_pref,
                relevant_activities_context=relevant_context
            )
            status_main.update(label="הפעולה מוכנה!", state="complete", expanded=False)

        st.session_state.generated_activity_text = generated_activity

if st.session_state.show_activity:
    activity_text_to_display = st.session_state.generated_activity_text
    if activity_text_to_display:
        if "שגיאה:" in activity_text_to_display:  # Check for error messages from backend
            st.error(activity_text_to_display)
        else:
            st.success("הפעולה נוצרה בהצלחה! 🎉")  # Alert type affected by CSS
            output_div_id = "generatedActivityOutput"
            copy_feedback_id = "copyFeedback"

            st.markdown(f"<div id='{output_div_id}' class='output-container'>{activity_text_to_display}</div>",
                        unsafe_allow_html=True)

            # HTML for the copy button and feedback span
            st.markdown(
                f"""
                <button class="custom-copy-button" onclick="copyActivityToClipboard('{output_div_id}', '{copy_feedback_id}')">
                    📋 העתק פעולה ללוח
                </button>
                <span id="{copy_feedback_id}" style="margin-right: 10px; display: none;"></span> 
                """, unsafe_allow_html=True
            )  # Feedback span style updated in JS
    elif submit_button:  # Only show general error if submit was pressed and no specific error from backend
        st.error("אופס! משהו השתבש ביצירת הפעולה. נסה שוב או שנה את הבקשה.")

st.markdown("---")
st.markdown("<p>פותח באהבה עבור קהילת המדריכים</p>", unsafe_allow_html=True)  # Footer p affected by CSS

with st.sidebar:  # Sidebar content affected by CSS
    st.header("אודות")
    st.markdown("""
    **מחולל פעולות לצופים** הוא כלי מבוסס AI ובינה מלאכותית (Gemini)
    שנועד לסייע למדריכים בתנועת הצופים ליצור פעולות חינוכיות,
    מהנות ומותאמות אישית.
    """)
    st.markdown("---")
    st.subheader("איך זה עובד?")
    st.markdown("""
    1.  **הזן בקשה.**
    2.  **(אופציונלי) בחר משך וגיל.**
    3.  **השראה מהמאגר (אם רלוונטי).**
    4.  **יצירת AI:** Gemini ינתח את בקשתך ליצירת תוכנית פעולה חדשה.
    """)
    if generator_backend.GEMINI_API_KEY:
        st.success("מפתח API של Gemini טעון בהצלחה.")
    else:
        st.error("שגיאה: מפתח API של Gemini אינו מוגדר. המחולל לא יוכל ליצור פעולות חדשות.")