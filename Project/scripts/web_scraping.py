import requests
import time
import json
from pathlib import Path
from bs4 import BeautifulSoup
from tqdm import tqdm
from urllib.parse import urljoin, urlparse
import re
import openai
from dotenv import load_dotenv
import os

# Load the API key from the .env file
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def translate_to_english(text):
    """Translate text from Russian to English using OpenAI API."""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Use the newer GPT model
            messages=[
                {"role": "system", "content": "You are a translator that translates Russian text to English."},
                {"role": "user", "content": text}
            ],
            max_tokens=4000,
            temperature=0.3,
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"Translation failed: {e}")
        return text  # Return the original text if translation fails

def get_webpage_content(url):
    """Fetch webpage content with error handling."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        print(f"Failed to get {url}: {e}")
        return None

def crawl_site_with_pagination(base_url, max_pages=10, max_depth=3):
    """Crawl a site starting from base_url with pagination handling."""
    visited = set()
    article_urls = set()
    domain = urlparse(base_url).netloc

    def crawl_page(url, depth):
        if url in visited or depth > max_depth:
            return
        visited.add(url)

        response = get_webpage_content(url)
        if response is None:
            return

        soup = BeautifulSoup(response.content, "html.parser")
        links = [urljoin(url, link["href"]) for link in soup.find_all("a", href=True)]
        for link in links:
            if urlparse(link).netloc == domain and link not in visited:
                crawl_page(link, depth + 1)

        if url != base_url:
            article_urls.add(url)

    for page_num in range(1, max_pages + 1):
        crawl_page(f"{base_url}/page/{page_num}", 0)

    return list(article_urls)

def replace_strange_chars(text):
    """Clean strange characters from text."""
    replacements = {
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2026": "...",
        "\xa0": " ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.strip()

def get_meta_data(soup):
    """Extract metadata from blog post soup."""
    meta = {}
    time_tags = soup.find_all("time")
    if time_tags:
        meta["created"] = time_tags[0].get("datetime", "")
        meta["updated"] = time_tags[1].get("datetime", "") if len(time_tags) > 1 else meta["created"]
    article = soup.find("article")
    if article and article.has_attr("class"):
        classes = article["class"]
        meta["tags"] = [cls.split("-")[1] for cls in classes if cls.startswith(("tag-", "category-"))]
    else:
        meta["tags"] = []
    return meta

def get_paragraphs(soup):
    """Extract cleaned paragraphs from blog post soup and translate them."""
    paragraphs_html = soup.find_all("p")
    paragraphs_clean = [
        replace_strange_chars(para.get_text().strip())
        for para in paragraphs_html
        if para.get_text().strip()
    ]

    paragraphs_translated = []
    total_length = 0

    for para in paragraphs_clean:
        para_length = len(para.encode('utf-8'))
        if total_length + para_length > 4000:
            print(f"Skipping paragraph due to size limit: {para[:50]}...")  # Log skipped paragraph
            continue
        translated_para = translate_to_english(para)
        paragraphs_translated.append(translated_para)
        total_length += len(translated_para.encode('utf-8'))

    return paragraphs_translated

def extract_blog_data(soup):
    """Extract all relevant blog data from soup."""
    return {
        "title": soup.find("h1", class_="entry-title").get_text().strip() if soup.find("h1", class_="entry-title") else "",
        "meta": get_meta_data(soup),
        "paragraphs": get_paragraphs(soup),
    }

def sanitize_filename(filename: str) -> str:
    """Sanitize a string to be safe for use as a filename."""
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

def main():
    base_url = "https://www.vinegret.cz/646868/afisha-1"
    data_path = Path("data/vinegret_articles")
    post_path_json = data_path / "json"
    post_path_json.mkdir(parents=True, exist_ok=True)
    file_url_list = data_path / "vinegret_articles_urls.csv"

    print("Crawling site with pagination to extract article URLs...")
    article_urls = crawl_site_with_pagination(base_url, max_pages=20, max_depth=3)

    print(f"Number of unique articles found: {len(article_urls)}")
    with open(file_url_list, "w", encoding="utf-8") as f:
        f.writelines(f"{url}\n" for url in sorted(article_urls))

    print("Extracting content and metadata for each article...")
    for url in tqdm(sorted(article_urls)):
        file_out = post_path_json / f"{sanitize_filename(url.replace(base_url, '').strip('/'))}.json"
        if file_out.exists():
            continue

        time.sleep(0.1)  # polite delay to avoid blocking
        response = get_webpage_content(url)
        if response is None:
            continue

        soup = BeautifulSoup(response.content, "html.parser")
        article_data = {"url": url, **extract_blog_data(soup)}
        with open(file_out, "w", encoding="utf-8") as json_file:
            json.dump(article_data, json_file, ensure_ascii=False, indent=4)

    print("Scraping completed.")

if __name__ == "__main__":
    main()