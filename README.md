# 📰 News-Bot

**Automated multi-category news digest — fetched, deduplicated, summarized by Gemini, and delivered to Telegram every day at 8:00 AM IST.**

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini_2.5_Flash-8E75B2?style=for-the-badge&logo=googlegemini&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram_Bot_API-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?style=for-the-badge&logo=githubactions&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

---

## 🧭 Overview

News-Bot is a fully automated news pipeline that pulls from **7 curated RSS categories**, removes near-duplicate stories with Jaccard similarity, summarizes each category into 5 clean headlines via **Gemini 2.5 Flash**, and delivers a formatted digest straight to Telegram — with zero manual intervention, running on a daily **GitHub Actions cron schedule**.

| Category | Description |
|---|---|
| 📌 Technology & Science | Global tech, science breakthroughs |
| 🌍 Geopolitics | International relations, conflicts, diplomacy |
| 💰 Economics | Markets, policy, macroeconomic news |
| 📈 Stock Markets | Equities, IPOs, corporate earnings |
| 🇮🇳 India News & Politics | National news and political developments |
| 🐅 Tamil Nadu Politics | State politics — Tamil-language output, English proper nouns preserved in Roman script |
| 🤖 AI News | AI industry, research, and safety developments |

---

## 🏗️ Architecture

```mermaid
flowchart TD
    subgraph Trigger
        CRON["⏰ GitHub Actions Cron<br/>8:00 AM IST Daily"]
    end

    subgraph Fetch
        RSS["📡 RSS Feeds<br/>7 Categories"] --> DEDUP["🔍 Dedup Engine<br/>Jaccard Similarity ≥ 0.50"]
    end

    subgraph Summarize
        DEDUP --> PROMPT["📝 Build Category Prompt"]
        PROMPT --> GEMINI["✨ Gemini 2.5 Flash<br/>thinking disabled · JSON mode"]
        GEMINI --> VALIDATE{"Valid JSON<br/>+ Schema?"}
        VALIDATE -- No --> RETRY["🔁 Retry (transient)<br/>or Skip (permanent)"]
        RETRY --> GEMINI
    end

    subgraph Deliver
        VALIDATE -- Yes --> FORMAT["🎨 Format MarkdownV2<br/>1 message per category"]
        FORMAT --> TELEGRAM["📬 Telegram Bot API"]
        TELEGRAM --> TRACK["🗂️ Track message_id + date"]
    end

    subgraph Cleanup
        TRACK --> STATE["💾 telegram_state.json<br/>committed to repo"]
        STATE -.next day.-> DELETE["🗑️ Delete previous<br/>day's messages"]
        DELETE --> FORMAT
    end

    CRON --> RSS

    style CRON fill:#2088FF,color:#fff
    style GEMINI fill:#8E75B2,color:#fff
    style TELEGRAM fill:#26A5E4,color:#fff
    style DEDUP fill:#4CAF50,color:#fff
```

---

## ✨ Features

- **7-category coverage** — technology, geopolitics, economics, markets, India news, Tamil Nadu politics (bilingual), and AI news
- **Smart deduplication** — Jaccard similarity (0.50 threshold) strips near-identical stories before they ever reach the LLM
- **Cost-efficient summarization** — Gemini 2.5 Flash with `thinking_budget=0` and native JSON mode: no wasted reasoning tokens, no markdown-fence parsing needed
- **Resilient retries** — distinguishes transient errors (429 rate limits, 5xx) from permanent ones (bad request, auth) so it never wastes time retrying a failure that can't succeed
- **Schema-validated output** — malformed Gemini responses are filtered, not trusted blindly
- **Clean Telegram delivery** — one MarkdownV2 message per category, headline + summary together
- **Self-cleaning** — every message is tracked and automatically deleted the following day
- **Zero-touch automation** — GitHub Actions cron runs the entire pipeline daily; no server, no manual trigger

---

## 🛠️ Tech Stack

| Tool | Purpose |
|---|---|
| ![Python](https://img.shields.io/badge/-Python-3776AB?style=flat-square&logo=python&logoColor=white) | Core language |
| ![Gemini](https://img.shields.io/badge/-Gemini_2.5_Flash-8E75B2?style=flat-square&logo=googlegemini&logoColor=white) | Summarization engine |
| ![Telegram](https://img.shields.io/badge/-Telegram_Bot_API-26A5E4?style=flat-square&logo=telegram&logoColor=white) | Delivery channel |
| ![GitHub Actions](https://img.shields.io/badge/-GitHub_Actions-2088FF?style=flat-square&logo=githubactions&logoColor=white) | Daily scheduler / CI |
| ![RSS](https://img.shields.io/badge/-RSS-FFA500?style=flat-square&logo=rss&logoColor=white) | Source feeds |

---

## 📂 Project Structure

```
news-bot/
├── fetchers/
│   ├── __init__.py          # fetch_all_categories() aggregator
│   ├── config.py            # category definitions, feed URLs
│   ├── rss_fetcher.py        # RSS parsing
│   ├── tamil_politics.py     # native/fallback routing for TN politics
│   └── dedup.py              # Jaccard similarity deduplication
├── summarizer.py              # Gemini summarization + retry logic
├── telegram_delivery.py       # Telegram send + auto-cleanup
├── main.py                    # pipeline entry point (fetch → summarize → deliver)
├── requirements.txt
├── telegram_state.json        # tracks sent message_ids for next-day cleanup
├── .env.example
├── .gitignore
└── .github/
    └── workflows/
        └── daily-digest.yml   # 8:00 AM IST cron
```

---

## ⚙️ Setup

**1. Clone and install:**
```bash
git clone https://github.com/ajeemsuban060-glitch/news-bot.git
cd news-bot
pip install -r requirements.txt
```

**2. Configure environment** — copy `.env.example` to `.env` and fill in:
```
GEMINI_API_KEY=your_gemini_api_key
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

**3. Run locally:**
```bash
python main.py
```

**4. Enable automation** — add the same three values as **repository secrets** (Settings → Secrets and variables → Actions), then the workflow in `.github/workflows/daily-digest.yml` runs automatically every day at 8:00 AM IST. Trigger it manually anytime from the **Actions** tab via `workflow_dispatch`.

---

## 🔒 Security

- `.env` is git-ignored — never committed
- Secrets live only in GitHub Actions repository secrets
- If a token is ever exposed, rotate it immediately via BotFather (Telegram) or Google AI Studio (Gemini)

---

## 📜 License

MIT — see [LICENSE](LICENSE) for details.
