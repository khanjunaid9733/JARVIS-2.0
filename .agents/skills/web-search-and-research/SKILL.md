---
name: web-search-and-research
description: Performs live web searches, fetches page content, summarizes articles, extracts structured data, and compiles research reports from any URL or search query. Supports DuckDuckGo, SerpAPI, Bing, and direct HTTP fetch pipelines.
---

# Web Search & Research Skill

## Purpose
Enables JARVIS to search the web, extract information, summarize content, and compile research reports on any topic in real-time.

## When to Activate
- "Search for <topic>"
- "What is the latest news on <topic>"
- "Summarize this article: <URL>"
- "Find me the documentation for <library>"
- "Research <topic> and give me a summary"
- "What's the current price of <stock/crypto>"

## Core Workflows

### 1. DuckDuckGo Instant Search (No API Key Required)
```python
import urllib.parse
import urllib.request
import json

def ddg_search(query: str, max_results: int = 5) -> list[dict]:
    """Search DuckDuckGo Instant Answers API."""
    encoded = urllib.parse.quote(query)
    url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"
    req = urllib.request.Request(url, headers={"User-Agent": "JARVIS/2.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    results = []
    if data.get("AbstractText"):
        results.append({"title": data["Heading"], "snippet": data["AbstractText"], "url": data["AbstractURL"]})
    for topic in data.get("RelatedTopics", [])[:max_results]:
        if "Text" in topic:
            results.append({"snippet": topic["Text"], "url": topic.get("FirstURL", "")})
    return results
```

### 2. Fetch & Extract Article Text
```python
from urllib.request import urlopen
from html.parser import HTMLParser

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self._skip = False
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "nav", "footer"):
            self._skip = True
    def handle_endtag(self, tag):
        if tag in ("script", "style", "nav", "footer"):
            self._skip = False
    def handle_data(self, data):
        if not self._skip and data.strip():
            self.text_parts.append(data.strip())

def fetch_article_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "JARVIS/2.0"})
    with urlopen(req, timeout=15) as resp:
        html = resp.read().decode("utf-8", errors="ignore")
    parser = TextExtractor()
    parser.feed(html)
    return " ".join(parser.text_parts[:500])  # Trim to first ~500 tokens
```

### 3. Research Pipeline (Search → Fetch → Summarize)
```
Step 1: Run ddg_search(query) -> extract top 3 result URLs
Step 2: For each URL, run fetch_article_text(url) -> raw text
Step 3: Pass combined text to ModelGateway for summarization
Step 4: Return structured summary with sources cited
```

### 4. Live Stock / Crypto Price
```python
# Yahoo Finance (no key needed)
def get_price(ticker: str) -> dict:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())
    result = data["chart"]["result"][0]["meta"]
    return {"ticker": ticker, "price": result.get("regularMarketPrice"), "currency": result.get("currency")}
```

## Best Practices & Safety Invariants
- Always cite sources in research output.
- Respect robots.txt and rate-limit HTTP requests (min 1s between fetches).
- Do not store fetched PII or personal data into the event log.
- Sanitize and truncate large article bodies before passing to ModelGateway.
