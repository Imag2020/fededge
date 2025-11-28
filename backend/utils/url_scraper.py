"""
URL Scraper - Scrape web pages and PDFs for RAG system
"""

import requests
from bs4 import BeautifulSoup
import logging
import tempfile
import os
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


def scrape_url(url: str, timeout: int = 30) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Scrape content from a URL (HTML or PDF)

    Args:
        url: URL to scrape
        timeout: Request timeout in seconds

    Returns:
        Tuple of (title, content, error_message)
        If successful, error_message is None
    """
    try:
        # Fetch URL
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()

        # Detect content type
        content_type = response.headers.get('content-type', '').lower()
        is_pdf = 'pdf' in content_type or url.lower().endswith('.pdf')

        if is_pdf:
            return _scrape_pdf(url, response.content)
        else:
            return _scrape_html(url, response.content)

    except requests.RequestException as e:
        logger.error(f"Failed to fetch URL {url}: {e}")
        return None, None, f"Failed to fetch URL: {str(e)}"
    except Exception as e:
        logger.error(f"Error scraping URL {url}: {e}", exc_info=True)
        return None, None, f"Error scraping: {str(e)}"


def _scrape_pdf(url: str, content: bytes) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Extract text from PDF content"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name

        try:
            # Try PyPDF2 (already in requirements)
            from PyPDF2 import PdfReader

            with open(tmp_path, 'rb') as f:
                reader = PdfReader(f)
                text_content = ""
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_content += page_text + "\n"

            # Extract title from URL
            title = url.split('/')[-1].replace('.pdf', '')

            logger.info(f"Extracted {len(text_content)} chars from PDF ({len(reader.pages)} pages)")

            if not text_content.strip():
                return None, None, "PDF appears to be empty or image-based"

            return title, text_content, None

        finally:
            os.remove(tmp_path)

    except Exception as e:
        logger.error(f"Failed to extract PDF: {e}", exc_info=True)
        return None, None, f"Failed to extract PDF: {str(e)}"


def _scrape_html(url: str, content: bytes) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Extract text from HTML content"""
    try:
        soup = BeautifulSoup(content, 'html.parser')

        # Remove scripts, styles, nav, footer
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        # Extract title
        title_tag = soup.find('title')
        title = title_tag.get_text().strip() if title_tag else url.split('//')[-1].split('/')[0]

        # Try to find main content (article, main, or full body)
        main_content = soup.find('article') or soup.find('main') or soup.find('body')

        if main_content:
            text_content = main_content.get_text()
        else:
            text_content = soup.get_text()

        # Clean text
        lines = (line.strip() for line in text_content.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text_content = '\n'.join(chunk for chunk in chunks if chunk)

        # Remove excessive newlines
        import re
        text_content = re.sub(r'\n\s*\n\s*\n+', '\n\n', text_content)
        text_content = text_content.strip()

        logger.info(f"Extracted {len(text_content)} chars from HTML")

        if len(text_content) < 100:
            return None, None, f"Extracted text too short ({len(text_content)} chars)"

        return title, text_content, None

    except Exception as e:
        logger.error(f"Failed to parse HTML: {e}", exc_info=True)
        return None, None, f"Failed to parse HTML: {str(e)}"
