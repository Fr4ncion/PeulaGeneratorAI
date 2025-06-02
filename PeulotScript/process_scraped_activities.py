import forum_scraper  # Assuming your refactored scraper is named forum_scraper.py
import peula_db_manager  # Assuming your DB/Gemini script is peula_db_manager.py
import time
import re

# --- Configuration for Orchestrator ---
# How many pages of the forum to scrape (e.g., /forum/20, /forum/20/page/2, ...)
# Be mindful of the number of topics per page and total API calls.
MAX_FORUM_PAGES_TO_SCRAPE = 1  # Start with 1 for testing

MIN_ACTIVITY_LENGTH = 100  # Characters, very basic filter
MIN_LINES_FOR_ACTIVITY = 5  # Another basic filter


def is_activity_worthy(text, url="N/A"):
    """
    A heuristic-based function to decide if the scraped text is likely an activity.
    This will need tuning and won't be perfect.
    """
    if not text or not isinstance(text, str):
        return False

    text_lower = text.lower()

    # 1. Length checks
    if len(text) < MIN_ACTIVITY_LENGTH:
        print(f"Orchestrator: Content from {url} too short ({len(text)} chars), skipping.")
        return False
    if len(text.splitlines()) < MIN_LINES_FOR_ACTIVITY:
        print(f"Orchestrator: Content from {url} has too few lines ({len(text.splitlines())}), skipping.")
        return False

    # 2. Positive Keywords (Hebrew examples)
    #    More weight if multiple keywords appear.
    positive_keywords = [
        "משחק", "פעילות", "מטרה", "חניכים", "מדריך", "דקות", "שלב",
        "צ'ופר", "מהלך", "לוז", "לו\"ז", "הסבר", "הוראות", "ציוד",
        "1.", "2.", "א.", "ב."  # Common list indicators
    ]
    positive_hits = sum(1 for keyword in positive_keywords if keyword in text)  # Check in original text for Hebrew

    # 3. Negative Keywords (Hebrew examples - indicating questions or non-activity posts)
    negative_keywords_exact = ["מישהו מכיר", "שאלה:", "מחפש/ת", "רעיון ל", "מה דעתכם", "דיון:"]
    for neg_kw in negative_keywords_exact:
        if neg_kw in text:
            print(f"Orchestrator: Content from {url} contains negative keyword '{neg_kw}', skipping.")
            return False

    # Simple logic: needs some positive indicators.
    # This is highly tunable.
    if positive_hits >= 2:  # Require at least 2 positive keyword hits
        print(f"Orchestrator: Content from {url} deemed worthy (positive hits: {positive_hits}).")
        return True

    # Check for common activity structures (e.g., lines starting with numbers/times)
    lines_with_activity_structure = 0
    for line in text.splitlines():
        line_strip = line.strip()
        if line_strip.startswith(("1.", "2.", "3.", "4.", "5.", "- ", "* ")) or \
                re.match(r"^\d+דק", line_strip) or \
                re.match(r"^\d{1,2}:\d{2}", line_strip):  # e.g., 10דק or 10:00
            lines_with_activity_structure += 1

    if lines_with_activity_structure >= 2 and positive_hits >= 1:  # Structure + at least one general keyword
        print(
            f"Orchestrator: Content from {url} deemed worthy by structure (lines: {lines_with_activity_structure}, positive: {positive_hits}).")
        return True

    print(
        f"Orchestrator: Content from {url} did not meet worthiness criteria (positive hits: {positive_hits}, structured lines: {lines_with_activity_structure}). Skipping.")
    return False


def main_orchestrator():
    print("Orchestrator: Starting process...")

    # 1. Setup Database (ensure table exists)
    peula_db_manager.setup_database()

    # 2. Scrape activities from the forum
    #    The scraper function now returns a list of (url, text)
    scraped_items = forum_scraper.scrape_forum_for_activities(
        start_forum_url=forum_scraper.FORUM_URL,
        max_pages=MAX_FORUM_PAGES_TO_SCRAPE
    )

    if not scraped_items:
        print("Orchestrator: No items were scraped from the forum. Exiting.")
        return

    print(f"\nOrchestrator: Scraped {len(scraped_items)} potential items. Now processing...")

    successful_adds = 0
    worthy_count = 0

    for source_url, activity_text in scraped_items:
        print(f"\nOrchestrator: --- Processing item from: {source_url} ---")

        # 3. Check if the activity is "worthy"
        if is_activity_worthy(activity_text, source_url):
            worthy_count += 1
            # 4. Parse with Gemini (pass the full scraped text)
            # The 'activity_text' is the 'full_activity_input' for Gemini
            parsed_metadata = peula_db_manager.parse_activity_with_gemini(activity_text,
                                                                          source_url_for_context=source_url)

            if parsed_metadata:
                # 5. Prepare data for DB
                # The full scraped text becomes the 'games_and_methods'
                final_data_for_db = parsed_metadata.copy()
                final_data_for_db["games_and_methods"] = activity_text
                final_data_for_db["source_url"] = source_url  # Add source URL

                # 6. Add to Database
                if peula_db_manager.add_activity_to_db(final_data_for_db):
                    successful_adds += 1
            else:
                print(f"Orchestrator: Gemini parsing failed for content from {source_url}. Not added to DB.")
        else:
            print(f"Orchestrator: Scraped content from {source_url} was NOT deemed worthy. Skipping DB insertion.")

        time.sleep(1)  # Small delay between processing items, especially if Gemini is called

    print(f"\nOrchestrator: --- Summary ---")
    print(f"Total items scraped: {len(scraped_items)}")
    print(f"Items deemed worthy: {worthy_count}")
    print(f"Items successfully added to DB: {successful_adds}")
    print("Orchestrator: Process finished.")


if __name__ == "__main__":
    main_orchestrator()