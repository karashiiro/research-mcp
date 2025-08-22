"""
Web Content Fetcher

Handles fetching and cleaning web content with smart retry logic and HTML parsing.
"""

import asyncio
import re
from typing import Any

import httpx
from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString


class WebContentFetcher:
    """Handles web content fetching with intelligent parsing and error handling."""

    # Browser headers to avoid bot detection
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0",
    }

    # HTML elements that add noise to content
    NOISE_ELEMENTS = [
        "script",
        "style",
        "nav",
        "header",
        "footer",
        "aside",
        "advertisement",
        "ads",
        "sidebar",
        "menu",
        "popup",
        "cookie",
        "subscribe",
        "newsletter",
        "social",
        "share",
    ]

    # CSS selectors for noise removal
    NOISE_SELECTORS = [
        '[class*="ad"]',
        '[class*="advertisement"]',
        '[class*="sidebar"]',
        '[class*="menu"]',
        '[class*="nav"]',
        '[class*="header"]',
        '[class*="footer"]',
        '[class*="cookie"]',
        '[class*="popup"]',
        '[class*="modal"]',
        '[class*="overlay"]',
        '[id*="ad"]',
        '[id*="sidebar"]',
        '[id*="nav"]',
        '[id*="header"]',
        '[id*="footer"]',
    ]

    # CSS selectors for finding main content
    CONTENT_SELECTORS = [
        "main",
        "article",
        '[role="main"]',
        ".content",
        ".post-content",
        ".article-content",
        ".entry-content",
        "#content",
        "#main-content",
        ".post-body",
        ".article-body",
        ".content-body",
    ]

    def __init__(self, timeout: float = 30.0, max_content_length: int = 12000):
        self.timeout = timeout
        self.max_content_length = max_content_length

    async def fetch_content(
        self, url: str, prompt: str | None = None
    ) -> dict[str, Any]:
        """
        Fetch and clean content from a web URL.

        Args:
            url: The URL to fetch content from
            prompt: Optional prompt for context (not used currently but available for future)

        Returns:
            Dictionary with success status, content, title, and error info
        """
        if not self._is_valid_url(url):
            return self._error_response(
                url, "Invalid URL format. Must start with http:// or https://"
            )

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout, follow_redirects=True
            ) as client:
                response = await self._fetch_with_retry(client, url)

                if isinstance(response, dict):  # Error response
                    return response

                return self._parse_html_content(url, response.text, prompt)

        except Exception as e:
            return self._error_response(url, f"Unexpected error: {str(e)}")

    def _is_valid_url(self, url: str) -> bool:
        """Check if URL format is valid."""
        return url.startswith(("http://", "https://"))

    async def _fetch_with_retry(self, client: httpx.AsyncClient, url: str) -> Any:
        """Fetch URL with smart retry logic for rate limiting."""
        try:
            response = await client.get(url, headers=self.DEFAULT_HEADERS)
            response.raise_for_status()
            return response

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                # Rate limited - try once more after a brief wait
                try:
                    await asyncio.sleep(2)
                    retry_response = await client.get(url, headers=self.DEFAULT_HEADERS)
                    retry_response.raise_for_status()
                    return retry_response
                except Exception:
                    return self._error_response(
                        url,
                        "Rate limited (HTTP 429). Try an alternative source or search for similar content from a different website.",
                    )
            else:
                return self._error_response(
                    url,
                    f"HTTP {e.response.status_code}: {e.response.reason_phrase}. This site may be blocking requests or require login. Try searching for similar content from alternative sources like GameWith, Icy Veins, or community guides.",
                )

        except httpx.RequestError as e:
            return self._error_response(
                url,
                f"Request failed: {str(e)}. The site may be temporarily unavailable.",
            )

    def _parse_html_content(
        self, url: str, html: str, prompt: str | None
    ) -> dict[str, Any]:
        """Parse HTML content and extract clean text."""
        soup = BeautifulSoup(html, "html.parser")

        # Extract title
        title = self._extract_title(soup)

        # Clean up noise elements
        self._remove_noise_elements(soup)

        # Find main content area
        main_content = self._find_main_content(soup)

        # Extract clean text
        text_content = self._extract_clean_text(main_content)

        # Limit content length
        if len(text_content) > self.max_content_length:
            text_content = (
                text_content[: self.max_content_length]
                + "\n\n... [Content truncated for brevity]"
            )

        return {
            "url": url,
            "success": True,
            "title": title,
            "content": text_content,
            "content_length": len(text_content),
            "prompt_used": prompt
            or "Extract the main content and key information from this page",
        }

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title."""
        title_tag = soup.find("title")
        return title_tag.get_text().strip() if title_tag else "No title found"

    def _remove_noise_elements(self, soup: BeautifulSoup) -> None:
        """Remove unwanted elements that add noise."""
        # Remove noise elements by tag
        for element in soup(self.NOISE_ELEMENTS):
            element.decompose()

        # Remove noise elements by CSS selector
        for selector in self.NOISE_SELECTORS:
            try:
                for element in soup.select(selector):
                    element.decompose()
            except Exception:
                continue  # Skip invalid selectors

    def _find_main_content(self, soup: BeautifulSoup) -> Tag | BeautifulSoup:
        """Find the main content area of the page."""
        # Try to find main content areas
        for selector in self.CONTENT_SELECTORS:
            try:
                main_content = soup.select_one(selector)
                if main_content:
                    return main_content
            except Exception:
                continue

        # Fall back to body with additional noise removal
        body_element = soup.find("body")
        if body_element and isinstance(body_element, Tag):
            main_content = body_element
            for element in main_content(["nav", "header", "footer", "aside"]):
                element.decompose()
            return main_content

        # Last resort: use entire soup
        return soup

    def _extract_clean_text(self, element: Tag | BeautifulSoup) -> str:
        """Extract clean text with proper spacing between elements."""

        def extract_text_with_spacing(elem):
            if isinstance(elem, NavigableString):
                return str(elem).strip()

            text_parts = []
            for child in elem.children:
                child_text = extract_text_with_spacing(child)
                if child_text:
                    text_parts.append(child_text)

            # Add spacing based on element type
            if elem.name in [
                "p",
                "div",
                "section",
                "article",
                "h1",
                "h2",
                "h3",
                "h4",
                "h5",
                "h6",
            ]:
                return " ".join(text_parts) + "\n\n" if text_parts else ""
            elif elem.name in ["li"]:
                return "• " + " ".join(text_parts) + "\n" if text_parts else ""
            elif elem.name in ["br"]:
                return "\n"
            else:
                return " ".join(text_parts) + " " if text_parts else ""

        text_content = extract_text_with_spacing(element)

        # Clean up extra whitespace
        text_content = re.sub(
            r"\n\s*\n\s*\n", "\n\n", text_content
        )  # Max 2 consecutive newlines
        text_content = re.sub(r" +", " ", text_content)  # Collapse multiple spaces

        return text_content.strip()

    def _error_response(self, url: str, error_msg: str) -> dict[str, Any]:
        """Create a standardized error response."""
        return {
            "url": url,
            "success": False,
            "error": error_msg,
            "content": "",
            "title": "",
        }
