# skills/news_skill.py
import feedparser
import logging

# A dictionary of reliable RSS feeds
NEWS_FEEDS = {
    "bbc": "http://feeds.bbci.co.uk/news/rss.xml",
    "sky": "https://feeds.skynews.com/feeds/rss/uk.xml",
    "reuters": "https://www.reuters.com/tools/rss",
    "parliament": "https://bills.parliament.uk/bills.rss"
}

def get_latest_news(context, source: str = "bbc", count: int = 3):
    """
    Fetches the latest news headlines from a specified source via its RSS feed.

    Args:
        context: The skill context for speaking.
        source (str): The news source to fetch from (e.g., 'bbc', 'sky', 'reuters'). Defaults to 'bbc'.
        count (int): The number of headlines to retrieve. Defaults to 3.
    """
    source_lower = source.lower()
    if source_lower not in NEWS_FEEDS:
        context.speak(f"Sorry, I don't recognize the news source '{source}'. Please choose from: {', '.join(NEWS_FEEDS.keys())}.")
        return

    feed_url = NEWS_FEEDS[source_lower]
    logging.info(f"[NewsSkill] Fetching news from {feed_url}")
    
    try:
        news_feed = feedparser.parse(feed_url)
        
        if not news_feed.entries:
            context.speak(f"Sorry, I couldn't retrieve any articles from {source} at the moment.")
            return

        context.speak(f"Here are the latest {count} headlines from {source}:")
        
        for i, entry in enumerate(news_feed.entries[:count]):
            context.speak(f"{i + 1}: {entry.title}")

    except Exception as e:
        logging.error(f"[NewsSkill] Failed to fetch or parse feed from {feed_url}: {e}", exc_info=True)
        context.speak(f"Sorry, I ran into an error trying to get the news from {source}.")

def _test_skill(context):
    """Runs a quick self-test for the news_skill module."""
    logging.info("[NewsSkillTest] Running self-test...")
    try:
        get_latest_news(context, source="bbc", count=1)
        logging.info("[NewsSkillTest] get_latest_news executed successfully.")
        
        get_latest_news(context, source="invalid_source")
        logging.info("[NewsSkillTest] Handled invalid source correctly.")

    except Exception as e:
        logging.error(f"[NewsSkillTest] Self-test FAILED: {e}", exc_info=True)
        raise 