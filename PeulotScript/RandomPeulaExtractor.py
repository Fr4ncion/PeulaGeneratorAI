import requests
from bs4 import BeautifulSoup
import time
import re

BASE_URL = "https://xn--8dbbvwj.net"
FORUM_URL = BASE_URL + "/forum/20"


def normalize_href(href_path):
    """Cleans and normalizes a path extracted from an href attribute."""
    if not href_path:
        return None
    if href_path.startswith('./'):
        href_path = href_path[2:]
    elif href_path.startswith('.'):
        href_path = href_path[1:]
    href_path = href_path.split('?')[0]
    href_path = href_path.split('#')[0]
    if not href_path.startswith('/') and not href_path.startswith('http'):
        href_path = '/' + href_path
    return href_path


def get_topic_links(forum_page_url):
    """Fetches the forum page and extracts links to individual topics."""
    topic_links = []
    try:
        print(f"Fetching topic list from: {forum_page_url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(forum_page_url, headers=headers, timeout=20)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "html.parser")

        # Using the generic selector that worked for you previously to get topic links
        print(f"Using generic selector for topic links on {forum_page_url}.")
        all_page_links = soup.select('a[href*="/topic/"]')
        temp_topic_elements = []
        for link_tag in all_page_links:
            href_attr = link_tag.get('href', '')
            if ("/topic/" in href_attr and
                    not any(kw in href_attr for kw in ['unread', 'last', 'teaser', '?page=']) and
                    not any(parent.name in ['small', 'span'] and 'pag' in parent.get('class', '').lower() for parent in
                            link_tag.parents) and
                    link_tag.get_text(strip=True)
            ):
                temp_topic_elements.append(link_tag)

        if temp_topic_elements:
            print(f"Found {len(temp_topic_elements)} links with generic selector.")

        for link_tag in temp_topic_elements:
            raw_href = link_tag.get('href')
            cleaned_href_path = normalize_href(raw_href)
            if cleaned_href_path:
                full_url = BASE_URL + cleaned_href_path if not cleaned_href_path.startswith(
                    'http') else cleaned_href_path
                if full_url not in topic_links:
                    topic_links.append(full_url)

        if not topic_links:
            print(
                f"Warning: No topic links found on {forum_page_url}. The HTML structure might be unexpected or JS-rendered.")

        print(f"Found {len(topic_links)} unique topic links on {forum_page_url}")
        return list(set(topic_links))

    except requests.exceptions.RequestException as e:
        print(f"Error fetching forum page {forum_page_url}: {e}")
        return []
    except Exception as e:
        print(f"An error occurred while parsing forum page {forum_page_url}: {e}")
        return []


def extract_activity_from_topic(topic_url):
    """
    Fetches a topic page and attempts to extract the content of the first post.
    """
    try:
        print(f"Fetching activity from: {topic_url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(topic_url, headers=headers, timeout=20)
        response.raise_for_status()
        response.encoding = response.apparent_encoding  # Use detected encoding
        soup = BeautifulSoup(response.text, "html.parser")

        # For debugging: save the HTML content received by requests
        # filename = "debug_page_" + topic_url.split("/")[-1].split("?")[0] + ".html"
        # with open(filename, "w", encoding='utf-8') as f_debug:
        #     f_debug.write(soup.prettify())
        # print(f"Saved HTML for {topic_url} to {filename}")

        first_post_content_div = None

        # Attempt 1: Find the first list item that represents a post
        # NodeBB typically uses li elements with component="post" for posts
        all_post_lis = soup.select('li[component="post"]')
        if all_post_lis:
            first_post_li = all_post_lis[0]
            # Now, within this first post li, find the div with class="content"
            # It might also have component="post/content"
            first_post_content_div = first_post_li.select_one('div.content[component="post/content"]')
            if not first_post_content_div:
                # Fallback: just div.content within the first post li
                print(
                    f"Selector 'div.content[component=\"post/content\"]' failed in first post for {topic_url}. Trying simpler 'div.content'.")
                first_post_content_div = first_post_li.select_one('div.content')
        else:
            print(f"Could not find any 'li[component=\"post\"]' elements on {topic_url}.")

        # Attempt 2: Broader search if the li structure isn't found or doesn't contain content div
        if not first_post_content_div:
            print(
                f"Attempt 1 failed for {topic_url}. Trying broader selector for the first 'div.content' with post component attribute.")
            first_post_content_div = soup.select_one('div.content[component="post/content"]')

        if not first_post_content_div:
            print(f"Attempt 2 failed for {topic_url}. Trying broadest: first 'div.content' on page.")
            # Very broad: just take the first div with class 'content'. This is risky as other elements might have this class.
            first_post_content_div = soup.select_one('div.content')

        if first_post_content_div:
            # Remove any quoted text (reply blocks)
            for quote in first_post_content_div.select(
                    'blockquote.inline-quote, div.quote-container, blockquote[data-username]'):
                quote.decompose()

            text_segments = list(first_post_content_div.stripped_strings)
            activity_text = "\n".join(text_segments)
            activity_text = re.sub(r'\n\s*\n', '\n\n', activity_text).strip()  # Clean up multiple newlines

            # Additional check: if activity_text is very short, it might be an error or placeholder
            if len(activity_text) < 50 and ("loading" in activity_text.lower() or "טוען" in activity_text.lower()):
                print(
                    f"Warning: Extracted text from {topic_url} seems very short or indicates loading. Content might be JS-driven.")
                return None  # Or return the short text if that's acceptable.
            return activity_text
        else:
            print(
                f"Could not find any activity content structure in {topic_url} after all attempts. Content is likely JS-rendered or page structure is very different.")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching topic page {topic_url}: {e}")
        return None
    except Exception as e:
        print(f"An error occurred while parsing topic page {topic_url}: {e}")
        return None


if __name__ == "__main__":
    print(f"Starting activity extraction from: {FORUM_URL}\n")

    topic_urls = get_topic_links(FORUM_URL)

    # Basic pagination attempt (you might need to adjust the URL pattern)
    # Example: for pages like /forum/20, /forum/20/2, /forum/20/3 ... (if page numbers are directly in path)
    # max_pages_to_scrape = 3
    # if topic_urls: # Only try pagination if the first page yielded results
    #     for page_num in range(2, max_pages_to_scrape + 1):
    #         # Adjust this URL pattern based on actual site pagination
    #         # e.g. f"{FORUM_URL}?page={page_num}" OR f"{FORUM_URL}/p/{page_num}"
    #         paginated_forum_url = f"{FORUM_URL}/{page_num}" # A common pattern for path-based pagination
    #         print(f"\nFetching topics from paginated URL: {paginated_forum_url}")
    #         new_links = get_topic_links(paginated_forum_url)
    #         if not new_links:
    #             print(f"No new links found on {paginated_forum_url}, stopping pagination.")
    #             break
    #         original_count = len(topic_urls)
    #         topic_urls.extend(link for link in new_links if link not in topic_urls)
    #         if len(topic_urls) > original_count:
    #             print(f"Added {len(topic_urls) - original_count} new unique links from page {page_num}.")
    #         time.sleep(1)

    if not topic_urls:
        print("No topic URLs found. Exiting.")
    else:
        print(f"\nTotal unique topic URLs to process: {len(topic_urls)}")
        all_activities_count = 0
        for i, url in enumerate(topic_urls):
            print(f"\nProcessing URL {i + 1}/{len(topic_urls)}: {url}")
            activity = extract_activity_from_topic(url)
            if activity:
                all_activities_count += 1
                print("----------------------------------------------------")
                print(f"Activity from: {url}")
                print("----------------------------------------------------")
                print(activity)
                print("----------------------------------------------------\n")
            else:
                print(f"No activity text extracted from {url}")

            if i < len(topic_urls) - 1:
                time.sleep(1.5)

        print(
            f"\nFinished processing. Extracted {all_activities_count} activities from {len(topic_urls)} unique topics found.")
        if all_activities_count == 0 and topic_urls:
            print(
                "\nWARNING: No activities were successfully extracted. This strongly suggests that the content is loaded dynamically with JavaScript, or the site structure is significantly different than anticipated.")
            print(
                "Consider using a browser automation tool like Selenium or Playwright for sites that rely heavily on JavaScript.")