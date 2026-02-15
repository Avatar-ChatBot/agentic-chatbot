#!/usr/bin/env python3
"""
Crawl URLs using crawl4ai with AI analysis via OpenRouter.

Usage:
    # From JSON config
    python scripts/crawl_urls.py --config scripts/url_config.json

    # Interactive mode
    python scripts/crawl_urls.py --interactive

    # With custom model
    python scripts/crawl_urls.py --config scripts/url_config.json --model openrouter/openai/gpt-4o-mini
"""

import asyncio
import argparse
import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Try to import required packages
try:
    from crawl4ai import AsyncWebCrawler, LLMConfig, CrawlerRunConfig
    from crawl4ai.extraction_strategy import LLMExtractionStrategy
except ImportError as e:
    print(f"Error: crawl4ai not installed. Please install: pip install crawl4ai[all]")
    sys.exit(1)

# Import logging configuration
try:
    from utils.logging_config import setup_logging

    setup_logging(level=logging.INFO)
    logger = logging.getLogger(__name__)
except ImportError:
    # Fallback to basic logging if utils not available
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)


class URLConfig:
    """Represents a URL configuration entry"""

    def __init__(
        self,
        url: str,
        status: str = "accessible",
        description: str = "",
        source_sheets: List[str] = None,
    ):
        self.url = url
        self.status = status
        self.description = description
        self.source_sheets = source_sheets or []

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "URLConfig":
        """Create URLConfig from dictionary"""
        return cls(
            url=data.get("url", ""),
            status=data.get("status", "accessible"),
            description=data.get("description", ""),
            source_sheets=data.get("source_sheets", []),
        )


class KnowledgeBaseItem(BaseModel):
    """A structured knowledge base item extracted from web content"""

    title: str = Field(description="Title or headline of the content")
    category: str = Field(
        default="general",
        description="Category: news, announcement, event, information, program, research, other",
    )
    content: str = Field(description="Main content/summary in clean prose format")
    date: Optional[str] = Field(
        default=None,
        description="Publication or event date in ISO format (YYYY-MM-DD) if available",
    )
    tags: List[str] = Field(
        default_factory=list, description="Relevant tags/keywords for categorization"
    )
    entities: List[str] = Field(
        default_factory=list,
        description="Named entities mentioned (people, organizations, locations)",
    )


class KnowledgeBaseSchema(BaseModel):
    """Schema for knowledge base extraction"""

    crawl_timestamp: str = Field(description="ISO timestamp when content was crawled")
    source_url: str = Field(description="Original URL of the content")
    page_title: str = Field(description="Title of the webpage")
    page_description: Optional[str] = Field(
        default=None, description="Brief description of what the page is about"
    )
    items: List[KnowledgeBaseItem] = Field(
        default_factory=list,
        description="List of knowledge base items extracted from the page",
    )


EXTRACTION_INSTRUCTION = """
You are a knowledge base extraction specialist. Your task is to analyze the provided markdown content and extract structured information suitable for a RAG (Retrieval-Augmented Generation) knowledge base.

CONTEXT:
- The extracted data will be used as knowledge base entries for an AI assistant
- Users will query this knowledge base with natural language questions
- Each item should be self-contained and independently understandable

EXTRACTION GUIDELINES:

1. **Identify Meaningful Content Units**: 
   - News articles, announcements, events, programs, research findings
   - Each distinct topic should be a separate item
   - Skip navigation menus, footers, sidebars, and boilerplate

2. **Content Quality**:
   - Summarize into clear, factual prose (not bullet points from markdown)
   - Preserve important details: names, dates, numbers, locations
   - Make content searchable and answer-ready

3. **Date Extraction**:
   - Look for publication dates, event dates, deadlines
   - Format as YYYY-MM-DD (ISO format)
   - If relative date (e.g., "yesterday"), estimate based on current date: {current_date}

4. **Categorization**:
   - news: News articles and press releases
   - announcement: Official announcements
   - event: Events, seminars, workshops
   - program: Academic programs, courses, admissions
   - research: Research findings, publications
   - information: General information pages
   - other: Anything else

5. **Tags & Entities**:
   - Tags: 3-5 relevant keywords for search
   - Entities: Named people, organizations, locations mentioned

6. **Language**: Preserve the original language of the content (Indonesian or English)

Current crawl date/time: {current_datetime}
"""


def load_config_file(config_path: str) -> List[URLConfig]:
    """Load URLs from JSON config file"""
    try:
        with open(config_path, "r") as f:
            data = json.load(f)

        urls = data.get("urls", [])
        return [URLConfig.from_dict(url_data) for url_data in urls]
    except FileNotFoundError:
        logger.error(f"Config file not found: {config_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file: {e}")
        raise


def interactive_input() -> List[URLConfig]:
    """Prompt user for URLs interactively"""
    print("Enter URLs to crawl (one per line, empty line to finish):")
    urls = []
    while True:
        url = input(f"URL {len(urls) + 1}: ").strip()
        if not url:
            break
        urls.append(URLConfig(url=url))
    return urls


async def crawl_url(
    crawler: AsyncWebCrawler,
    url_config: URLConfig,
    model: str,
    api_key: str,
) -> Dict[str, Any]:
    """Crawl a single URL with LLM extraction"""
    try:
        logger.info(f"Crawling: {url_config.url}")

        current_dt = datetime.now()
        current_datetime = current_dt.isoformat()
        current_date = current_dt.strftime("%Y-%m-%d")

        instruction = EXTRACTION_INSTRUCTION.format(
            current_datetime=current_datetime, current_date=current_date
        )

        llm_config = LLMConfig(
            provider=model,
            api_token=api_key,
        )

        extraction_strategy = LLMExtractionStrategy(
            llm_config=llm_config,
            instruction=instruction,
            extraction_type="schema",
            schema=KnowledgeBaseSchema.model_json_schema(),
            extra_args={"temperature": 0.1, "max_tokens": 4000},
        )

        run_config = CrawlerRunConfig(
            extraction_strategy=extraction_strategy,
        )

        result = await crawler.arun(url=url_config.url, config=run_config)

        if result.extracted_content:
            try:
                extracted_content = json.loads(result.extracted_content)
            except json.JSONDecodeError:
                extracted_content = {"raw": result.extracted_content}
        elif result.markdown:
            extracted_content = {"fallback": True, "markdown": result.markdown}
        else:
            extracted_content = {}

        return {
            "url": url_config.url,
            "status": "success",
            "content": extracted_content,
            "metadata": {
                "description": url_config.description,
                "source_sheets": url_config.source_sheets,
                "crawl_timestamp": current_datetime,
            },
        }

    except Exception as e:
        logger.error(f"Error crawling {url_config.url}: {e}")
        return {"url": url_config.url, "status": "failed", "error": str(e)}


async def main(args):
    """Main entry point"""
    logger.info("Starting crawl4ai crawler")

    # Get OpenRouter API key from environment
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    if not openrouter_api_key:
        logger.error("OPENROUTER_API_KEY environment variable not set")
        sys.exit(1)

    # Load URLs
    if args.config:
        urls = load_config_file(args.config)
        logger.info(f"Loaded {len(urls)} URLs from config")
    elif args.interactive:
        urls = interactive_input()
        logger.info(f"Loaded {len(urls)} URLs from interactive input")
    else:
        logger.error("Must specify --config or --interactive")
        sys.exit(1)

    results = []

    start_time = datetime.now()

    semaphore = asyncio.Semaphore(5)

    async def crawl_with_semaphore(
        crawler: AsyncWebCrawler, url_config: URLConfig
    ) -> Dict[str, Any]:
        async with semaphore:
            return await crawl_url(
                crawler=crawler,
                url_config=url_config,
                model=args.model,
                api_key=openrouter_api_key,
            )

    async with AsyncWebCrawler(verbose=True) as crawler:
        tasks = [crawl_with_semaphore(crawler, url_config) for url_config in urls]
        results = await asyncio.gather(*tasks, return_exceptions=False)

    # Filter out exceptions (if any task failed with exception)
    results = [
        r
        for r in results
        if isinstance(r, dict) and r.get("status") in ["success", "failed"]
    ]

    end_time = datetime.now()
    execution_time = (end_time - start_time).total_seconds()

    # Generate summary statistics
    success_count = sum(1 for r in results if r.get("status") == "success")
    failed_count = sum(1 for r in results if r.get("status") == "failed")

    # Prepare output data
    output = {
        "results": results,
        "summary": {
            "total_urls": len(urls),
            "successful": success_count,
            "failed": failed_count,
            "execution_time_seconds": round(execution_time, 2),
        },
    }

    # Save to JSON file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"crawl_output/crawl_results_{timestamp}.json"

    with open(output_filename, "w") as f:
        json.dump(output, f, indent=2)

    logger.info(f"Total URLs processed: {len(urls)}")
    logger.info(f"Successful: {success_count}, Failed: {failed_count}")
    logger.info(f"Execution time: {execution_time:.2f} seconds")
    logger.info(f"Results saved to: {output_filename}")
    logger.info("Crawl complete")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Crawl URLs using crawl4ai with AI analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--config", type=str, help="Path to JSON config file with URLs to crawl"
    )
    parser.add_argument(
        "--interactive", action="store_true", help="Interactive mode: prompt for URLs"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="openrouter/qwen/qwen3-next-80b-a3b-instruct",
        help="LLM model to use (default: openrouter/qwen/qwen3-next-80b-a3b-instruct)",
    )

    args = parser.parse_args()

    if not args.config and not args.interactive:
        parser.print_help()
        sys.exit(1)

    asyncio.run(main(args))
