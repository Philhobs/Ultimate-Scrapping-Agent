"""HTML cleaning and structured data extraction using BeautifulSoup."""

from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup, Tag

# Tags to remove during cleaning
_STRIP_TAGS = {"script", "style", "nav", "footer", "header", "noscript", "svg", "iframe"}


def clean_html(html: str) -> BeautifulSoup:
    """Parse HTML and remove script/style/nav/boilerplate tags.

    Args:
        html: Raw HTML string.

    Returns:
        Cleaned BeautifulSoup object.
    """
    soup = BeautifulSoup(html, "lxml")
    for tag_name in _STRIP_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()
    # Remove HTML comments
    from bs4 import Comment

    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    return soup


def extract_text(html: str, selector: str | None = None) -> str:
    """Extract clean text from HTML.

    Args:
        html: Raw HTML string.
        selector: Optional CSS selector to scope extraction.
    """
    soup = clean_html(html)
    if selector:
        target = soup.select_one(selector)
        if target is None:
            return ""
        return target.get_text(separator="\n", strip=True)
    return soup.get_text(separator="\n", strip=True)


def extract_links(html: str, selector: str | None = None) -> list[dict[str, str]]:
    """Extract all links from HTML.

    Args:
        html: Raw HTML string.
        selector: Optional CSS selector to scope extraction.

    Returns:
        List of dicts with 'text' and 'href' keys.
    """
    soup = clean_html(html)
    container = soup.select_one(selector) if selector else soup
    if container is None:
        return []

    links = []
    for a in container.find_all("a", href=True):
        links.append({
            "text": a.get_text(strip=True),
            "href": a["href"],
        })
    return links


def extract_tables(html: str, selector: str | None = None) -> list[list[list[str]]]:
    """Extract tables from HTML as lists of rows.

    Args:
        html: Raw HTML string.
        selector: Optional CSS selector to scope to specific tables.

    Returns:
        List of tables, each a list of rows, each a list of cell strings.
    """
    soup = clean_html(html)
    container = soup.select_one(selector) if selector else soup
    if container is None:
        return []

    tables = []
    for table in container.find_all("table"):
        rows = []
        for tr in table.find_all("tr"):
            cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            if cells:
                rows.append(cells)
        if rows:
            tables.append(rows)
    return tables


def extract_elements(
    html: str, selector: str, attributes: list[str] | None = None
) -> list[dict[str, Any]]:
    """Extract elements matching a CSS selector.

    Args:
        html: Raw HTML string.
        selector: CSS selector to match elements.
        attributes: Optional list of attribute names to extract.
            If None, extracts text content and all attributes.

    Returns:
        List of dicts with element data.
    """
    soup = clean_html(html)
    results = []

    for element in soup.select(selector):
        item: dict[str, Any] = {"text": element.get_text(strip=True)}

        if attributes:
            for attr in attributes:
                item[attr] = element.get(attr)
        else:
            if isinstance(element, Tag):
                item["attributes"] = dict(element.attrs)

        results.append(item)

    return results
