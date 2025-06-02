import requests
from bs4 import BeautifulSoup
import time
import re

BASE_URL = "https://xn--8dbbvwj.net"
FORUM_URL = BASE_URL + "/forum/20?start=150"  # FINISHED 0-150


def normalize_href(href_path):
    if not href_path: return None
    if href_path.startswith('./'):
        href_path = href_path[2:]
    elif href_path.startswith('.'):
        href_path = href_path[1:]
    href_path = href_path.split('?')[0]
    href_path = href_path.split('#')[0]
    if not href_path.startswith('/') and not href_path.startswith('http'):
        href_path = '/' + href_path
    return href_path


def get_topic_links_from_page(forum_page_url):
    topic_links = []
    try:
        print(f"Scraper: Fetching topic list from: {forum_page_url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(forum_page_url, headers=headers, timeout=20)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "html.parser")

        all_page_links = soup.select('a[href*="/topic/"]')
        temp_topic_elements = []
        for link_tag in all_page_links:
            href_attr = link_tag.get('href', '')
            if ("/topic/" in href_attr and
                    not any(kw in href_attr for kw in ['unread', 'last', 'teaser', '?page=']) and
                    not any(parent.name in ['small', 'span'] and 'pag' in parent.get('class', '').lower() for parent in
                            link_tag.parents) and
                    link_tag.get_text(strip=True)):
                temp_topic_elements.append(link_tag)

        for link_tag in temp_topic_elements:
            raw_href = link_tag.get('href')
            cleaned_href_path = normalize_href(raw_href)
            if cleaned_href_path:
                full_url = BASE_URL + cleaned_href_path if not cleaned_href_path.startswith(
                    'http') else cleaned_href_path
                if full_url not in topic_links:
                    topic_links.append(full_url)

        print(f"Scraper: Found {len(topic_links)} unique topic links on {forum_page_url}")
        return list(set(topic_links))
    except Exception as e:
        print(f"Scraper: Error fetching/parsing topic list from {forum_page_url}: {e}")
        return []


def extract_activity_from_topic_page(topic_url):
    try:
        print(f"Scraper: Fetching activity from: {topic_url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(topic_url, headers=headers, timeout=20)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "html.parser")

        first_post_content_div = None
        all_post_lis = soup.select('li[component="post"]')
        if all_post_lis:
            first_post_li = all_post_lis[0]
            first_post_content_div = first_post_li.select_one('div.content[component="post/content"]')
            if not first_post_content_div:
                first_post_content_div = first_post_li.select_one('div.content')

        if not first_post_content_div:
            first_post_content_div = soup.select_one('div.content[component="post/content"]')
        if not first_post_content_div:
            first_post_content_div = soup.select_one('div.content')

        if first_post_content_div:
            for quote in first_post_content_div.select(
                    'blockquote.inline-quote, div.quote-container, blockquote[data-username]'):
                quote.decompose()
            text_segments = list(first_post_content_div.stripped_strings)
            activity_text = "\n".join(text_segments)
            activity_text = re.sub(r'\n\s*\n', '\n\n', activity_text).strip()
            if len(activity_text) < 50 and ("loading" in activity_text.lower() or "טוען" in activity_text.lower()):
                return None
            return activity_text
        else:
            # For debugging, save the HTML content received by requests
            # filename = "debug_scraper_page_" + topic_url.split("/")[-1].split("?")[0] + ".html"
            # with open(filename, "w", encoding='utf-8') as f_debug:
            #     f_debug.write(soup.prettify())
            # print(f"Scraper: Saved HTML for {topic_url} to {filename} due to no content found.")
            print(f"Scraper: Could not find activity content in {topic_url}.")
            return None
    except Exception as e:
        print(f"Scraper: Error fetching/parsing activity from {topic_url}: {e}")
        return None


def scrape_forum_for_activities(start_forum_url=FORUM_URL, max_pages=1):
    """
    Scrapes the forum for activities.
    Returns a list of tuples: (url, activity_text)
    """
    print(f"Scraper: Starting activity extraction from: {start_forum_url}")
    all_extracted_activities = []  # List of (url, text)

    # Get links from the first page
    all_topic_urls = get_topic_links_from_page(start_forum_url)

    # Basic pagination attempt (example: /forum/20, /forum/20/page/2 ...)
    # NodeBB often uses /page/N for pagination
    if max_pages > 1:
        for page_num in range(2, max_pages + 1):
            # Adjust this URL pattern based on actual site pagination
            paginated_forum_url = f"{start_forum_url}/page/{page_num}"
            print(f"\nScraper: Fetching topics from paginated URL: {paginated_forum_url}")
            new_links = get_topic_links_from_page(paginated_forum_url)
            if not new_links:
                print(f"Scraper: No new links found on {paginated_forum_url}, stopping pagination.")
                break
            for link in new_links:
                if link not in all_topic_urls:
                    all_topic_urls.append(link)
            all_topic_urls = list(set(all_topic_urls))  # Keep unique
            time.sleep(0.5)  # Be respectful when paginating

    if not all_topic_urls:
        print("Scraper: No topic URLs found. Exiting.")
        return all_extracted_activities

    print(f"\nScraper: Total unique topic URLs to process: {len(all_topic_urls)}")
    for i, url in enumerate(all_topic_urls):
        print(f"\nScraper: Processing URL {i + 1}/{len(all_topic_urls)}: {url}")
        activity_text = extract_activity_from_topic_page(url)
        if activity_text:
            all_extracted_activities.append((url, activity_text))
        else:
            print(f"Scraper: No activity text extracted from {url}")

        if i < len(all_topic_urls) - 1:
            time.sleep(1)  # Be respectful to the server

    print(
        f"\nScraper: Finished processing. Found {len(all_extracted_activities)} potential activities from {len(all_topic_urls)} topics.")
    return all_extracted_activities


if __name__ == "__main__":
    # This part is for testing the scraper module itself
    print("Testing forum_scraper.py module...")
    # Scrape only the first page for testing
    scraped_data = scrape_forum_for_activities(max_pages=1)
    if scraped_data:
        print(f"\nSuccessfully scraped {len(scraped_data)} items. First item's URL: {scraped_data[0][0]}")
        print("First item's text (first 200 chars):")
        print(scraped_data[0][1][:200] + "...")
    else:
        print("No data scraped in test run.")