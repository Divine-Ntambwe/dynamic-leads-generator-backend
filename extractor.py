import re
from bs4 import BeautifulSoup
from utils import generate_fingerprint
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig, LLMConfig
from crawl4ai.extraction_strategy import LLMExtractionStrategy
import tldextract
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator



def extract_school_data(html, url):
    soup = BeautifulSoup(html, "html.parser")

    text = soup.get_text(separator=" ")

    # Extract name (simple version — can improve later)
    title = soup.title.string.strip() if soup.title else None

    emails = re.findall(EMAIL_REGEX, text)
    phones = re.findall(PHONE_REGEX, text)

    if not title:
        return None

    school = {
        "name": title,
        "email": emails[0] if emails else None,
        "phone": phones[0] if phones else None,
        "website": url
    }

    school["fingerprint"] = generate_fingerprint(school)

    return school