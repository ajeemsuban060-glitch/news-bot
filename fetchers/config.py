"""
RSS feed sources per category.
All feeds are free, no API key, no rate limit.
"""

CATEGORY_FEEDS = {
    "technology_science": {
        "label": "📌 Technology & Science",
        "feeds": [
            "https://techcrunch.com/feed/",
            "https://feeds.arstechnica.com/arstechnica/index",
            "https://www.theverge.com/rss/index.xml",
        ],
    },
    "geopolitics": {
        "label": "🌍 Geopolitics",
        "feeds": [
            "https://www.theguardian.com/world/rss",
            "https://www.aljazeera.com/xml/rss/all.xml",
            "https://feeds.bbci.co.uk/news/world/rss.xml",
        ],
    },
    "economics": {
        "label": "💰 Economics",
        "feeds": [
            "https://www.financialexpress.com/feed/",
            "https://www.theguardian.com/uk/business/rss",
        ],
    },
    "stock_markets": {
        "label": "📈 Stock Markets",
        "feeds": [
            "https://www.moneycontrol.com/rss/latestnews.xml",
            "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
        ],
    },
    "india_news_politics": {
        "label": "🇮🇳 India News & Politics",
        "feeds": [
            "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms",
            "https://www.thehindu.com/news/national/feeder/default.rss",
        ],
    },
    "tamil_nadu_politics": {
        "label": "🐅 தமிழ்நாடு செய்திகள் (Tamil Nadu Politics)",
        # Primary: native Tamil source, filtered by politics keywords (see tamil_politics.py)
        "feeds": [
            "https://tamil.oneindia.com/rss/feeds/tamil-news-fb.xml",
        ],
        # Fallback ONLY if primary yields < MIN_ITEMS after keyword filtering
        "fallback_feeds": [
            "https://timesofindia.indiatimes.com/rssfeeds/3947261.cms",  # TOI Tamil Nadu
            "https://www.thehindu.com/news/national/tamil-nadu/feeder/default.rss",
        ],
        "is_tamil_native": True,
    },
    "ai_news": {
        "label": "🤖 AI News",
        "feeds": [
            "https://techcrunch.com/category/artificial-intelligence/feed/",
            "https://venturebeat.com/category/ai/feed/",
            "https://www.artificialintelligence-news.com/feed/rss/",
        ],
    },
}

MIN_ITEMS_PER_CATEGORY = 5
LOOKBACK_ESCALATION_HOURS = [24, 48, 72]  # tries in order until MIN_ITEMS is hit

TAMIL_POLITICS_KEYWORDS = [
    "திமுக", "அதிமுக", "தவெக", "பாஜக", "காங்கிரஸ்","நாம் தமிழர் கட்சி",
    "தமிழக அரசு","சீமான்", "முதலமைச்சர்", "ஆளுநர்", "எம்எல்ஏ", "எம்பி",
    "சட்டமன்றம்", "தேர்தல்", "அரசியல்",
]
TAMIL_POLITICS_KEYWORDS_EN = [
    "DMK", "AIADMK", "TVK", "BJP", "Congress", "NTK",
    "Naam Tamilar Katchi", "Seeman", "Tamil Nadu government",
    "Chief Minister", "Governor", "MLA", "MP",
    "Legislative Assembly", "election", "politics",
]