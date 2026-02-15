"""
Web-related tools for Hcode.
Includes WebFetch and WebSearch capabilities.
"""

from datetime import datetime, timedelta
from typing import List, Optional

import html2text
import httpx
from hcode.tools.base.base_tool import BaseTool, ToolResult, ToolParameter, ToolCategory


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
            ToolParameter("Url", "string", "URL to fetch content from", required=True),
            ToolParameter("Prompt", "string", "Prompt to process the content with", required=True),
            # Legacy
            ToolParameter("url", "string", "Alias for Url", default=None),
            ToolParameter("prompt", "string", "Alias for Prompt", default=None),
        ]

    def validate_parameters(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate parameters allowing for strict aliases"""
        if "Url" not in kwargs and "url" not in kwargs:
             return False, "Missing required parameter: Url (or url)"
        if "Prompt" not in kwargs and "prompt" not in kwargs:
             return False, "Missing required parameter: Prompt (or prompt)"
        return True, None

    async def execute(self, Url: str = None, Prompt: str = None, url: str = None, prompt: str = None, **kwargs) -> ToolResult:
        """Fetch and process web content"""
        # Parameter Normalization
        final_url = Url or url
        final_prompt = Prompt or prompt
        
        if not final_url:
             return ToolResult(success=False, output="", error="Url (or url) is required")
        if not final_prompt:
             return ToolResult(success=False, output="", error="Prompt (or prompt) is required")
             
        # Use final variables
        url = final_url
        prompt = final_prompt
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
            ToolParameter("Query", "string", "Search query", required=True),
            ToolParameter("NumResults", "integer", "Number of results to return", default=5),
            ToolParameter(
                "AllowedDomains", "array", "Only include results from these domains", default=None
            ),
            ToolParameter(
                "BlockedDomains", "array", "Exclude results from these domains", default=None
            ),
            # Legacy
            ToolParameter("query", "string", "Alias for Query", default=None),
            ToolParameter("num_results", "integer", "Alias for NumResults", default=None),
            ToolParameter("allowed_domains", "array", "Alias for AllowedDomains", default=None),
            ToolParameter("blocked_domains", "array", "Alias for BlockedDomains", default=None),
        ]

    def validate_parameters(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate parameters allowing for strict aliases"""
        if "Query" not in kwargs and "query" not in kwargs:
             return False, "Missing required parameter: Query (or query)"
        return True, None

    async def execute(
        self,
        Query: str = None,
        NumResults: int = 5,
        AllowedDomains: Optional[List[str]] = None,
        BlockedDomains: Optional[List[str]] = None,
        query: str = None,
        num_results: int = None,
        allowed_domains: Optional[List[str]] = None,
        blocked_domains: Optional[List[str]] = None,
        **kwargs
    ) -> ToolResult:
        """Search the web"""
        # Parameter Normalization
        final_query = Query or query
        final_num = NumResults or num_results or 5
        final_allowed = AllowedDomains or allowed_domains
        final_blocked = BlockedDomains or blocked_domains
        
        if not final_query:
            return ToolResult(success=False, output="", error="Query (or query) is required")
            
        # Map to internal names
        query = final_query
        num_results = final_num
        allowed_domains = final_allowed
        blocked_domains = final_blocked
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
            ToolParameter("Url", "string", "URL to scrape", required=True),
            ToolParameter(
                "Selector", "string", "CSS selector for elements to extract", default=None
            ),
            ToolParameter("ExtractLinks", "boolean", "Extract all links", default=False),
            # Legacy
            ToolParameter("url", "string", "Alias for Url", default=None),
            ToolParameter("selector", "string", "Alias for Selector", default=None),
            ToolParameter("extract_links", "boolean", "Alias for ExtractLinks", default=None),
        ]

    def validate_parameters(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate parameters allowing for strict aliases"""
        if "Url" not in kwargs and "url" not in kwargs:
             return False, "Missing required parameter: Url (or url)"
        return True, None

    async def execute(
        self, Url: str = None, Selector: Optional[str] = None, ExtractLinks: bool = False,
        url: str = None, selector: str = None, extract_links: bool = None, **kwargs
    ) -> ToolResult:
        """Scrape website content"""
        # Parameter Normalization
        final_url = Url or url
        final_selector = Selector or selector
        final_extract = ExtractLinks or extract_links or False
        
        if not final_url:
            return ToolResult(success=False, output="", error="Url (or url) is required")
            
        url = final_url
        selector = final_selector
        extract_links = final_extract
        
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
