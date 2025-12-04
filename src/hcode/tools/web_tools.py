"""
Web-related tools for Hcode.
Includes WebFetch and WebSearch capabilities.
"""

from datetime import datetime, timedelta
from typing import List, Optional

import html2text
import httpx
from hcode.tools.base_tool import BaseTool, ToolResult, ToolParameter, ToolCategory


class WebFetchTool(BaseTool):
    """
    Fetch content from URLs and convert to markdown.
    Includes caching for better performance.
    """

    def __init__(self):
        super().__init__()
        self.category = ToolCategory.WEB
        self.cache = {}  # Simple in-memory cache
        self.cache_duration = timedelta(minutes=15)

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("url", "string", "URL to fetch content from", required=True),
            ToolParameter("prompt", "string", "Prompt to process the content with", required=True),
        ]

    async def execute(self, url: str, prompt: str) -> ToolResult:
        """Fetch and process web content"""
        try:
            # Check cache
            cache_key = f"{url}:{prompt}"
            if cache_key in self.cache:
                cached_time, cached_result = self.cache[cache_key]
                if datetime.now() - cached_time < self.cache_duration:
                    return cached_result

            # Upgrade HTTP to HTTPS
            if url.startswith("http://"):
                url = url.replace("http://", "https://", 1)

            # Fetch content
            async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
                response = await client.get(url)

                # Check for redirects to different host
                if response.url.host != httpx.URL(url).host:
                    return ToolResult(
                        success=True,
                        output=f"Redirected to: {response.url}",
                        metadata={"redirect_url": str(response.url), "original_url": url},
                    )

                response.raise_for_status()

                # Convert HTML to markdown
                h = html2text.HTML2Text()
                h.ignore_links = False
                h.ignore_images = False
                markdown_content = h.handle(response.text)

                # Process with prompt (simplified - in production you'd use AI here)
                processed_content = f"# Content from {url}\n\n{markdown_content[:5000]}"

                result = ToolResult(
                    success=True,
                    output=processed_content,
                    metadata={
                        "url": str(response.url),
                        "status_code": response.status_code,
                        "content_length": len(markdown_content),
                    },
                )

                # Cache result
                self.cache[cache_key] = (datetime.now(), result)

                return result

        except httpx.HTTPStatusError as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"HTTP {e.response.status_code}: {e.response.reason_phrase}",
            )
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class WebSearchTool(BaseTool):
    """
    Search the web and return results.
    Note: Requires search API key (e.g., Brave Search, Google Custom Search)
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__()
        self.category = ToolCategory.WEB
        self.api_key = api_key

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("query", "string", "Search query", required=True),
            ToolParameter("num_results", "integer", "Number of results to return", default=5),
            ToolParameter(
                "allowed_domains", "array", "Only include results from these domains", default=None
            ),
            ToolParameter(
                "blocked_domains", "array", "Exclude results from these domains", default=None
            ),
        ]

    async def execute(
        self,
        query: str,
        num_results: int = 5,
        allowed_domains: Optional[List[str]] = None,
        blocked_domains: Optional[List[str]] = None,
    ) -> ToolResult:
        """Search the web"""
        try:
            if not self.api_key:
                return ToolResult(
                    success=False,
                    output=None,
                    error="Web search requires API key. Set SEARCH_API_KEY environment variable.",
                )

            # Use Brave Search API as an example
            url = "https://api.search.brave.com/res/v1/web/search"

            params = {"q": query, "count": num_results}

            headers = {"Accept": "application/json", "X-Subscription-Token": self.api_key}

            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                data = response.json()

            # Process results
            results = []
            for item in data.get("web", {}).get("results", [])[:num_results]:
                # Filter by domains if specified
                if allowed_domains:
                    if not any(domain in item["url"] for domain in allowed_domains):
                        continue

                if blocked_domains:
                    if any(domain in item["url"] for domain in blocked_domains):
                        continue

                results.append(
                    {
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "description": item.get("description", ""),
                    }
                )

            # Format output
            output = "\n\n".join(
                [f"**{r['title']}**\n{r['url']}\n{r['description']}" for r in results]
            )

            return ToolResult(
                success=True, output=output, metadata={"query": query, "num_results": len(results)}
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class WebScrapeTool(BaseTool):
    """
    Scrape structured data from websites.
    """

    def __init__(self):
        super().__init__()
        self.category = ToolCategory.WEB

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("url", "string", "URL to scrape", required=True),
            ToolParameter(
                "selector", "string", "CSS selector for elements to extract", default=None
            ),
            ToolParameter("extract_links", "boolean", "Extract all links", default=False),
        ]

    async def execute(
        self, url: str, selector: Optional[str] = None, extract_links: bool = False
    ) -> ToolResult:
        """Scrape website content"""
        try:
            from bs4 import BeautifulSoup

            async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")

                if extract_links:
                    links = [a.get("href") for a in soup.find_all("a", href=True)]
                    # Convert relative URLs to absolute
                    base_url = str(response.url)
                    absolute_links = []
                    for link in links:
                        if link.startswith("http"):
                            absolute_links.append(link)
                        elif link.startswith("/"):
                            absolute_links.append(f"{base_url.rstrip('/')}{link}")
                    output = "\n".join(absolute_links)

                elif selector:
                    elements = soup.select(selector)
                    output = "\n\n".join([elem.get_text(strip=True) for elem in elements])

                else:
                    output = soup.get_text(separator="\n", strip=True)

                return ToolResult(
                    success=True,
                    output=output,
                    metadata={"url": url, "items_extracted": len(output.split("\n"))},
                )

        except ImportError:
            return ToolResult(
                success=False,
                output=None,
                error="BeautifulSoup4 not installed. Run: pip install beautifulsoup4",
            )
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))
