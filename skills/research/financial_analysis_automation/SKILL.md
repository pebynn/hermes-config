---
author: unknown
description: "Create automated financial analysis skills with scheduled execution\
  \ and result storage.\nUse when you need to build custom stock/scanning analysis\
  \ that runs automatically \nand saves results to Obsidian for daily review.\n"
name: financial_analysis_automation
version: 1.0.0
---

# Financial Analysis Automation Skill

Use this skill to create automated financial analysis workflows that:
1. Scan multiple sources for investment opportunities
2. Run on a schedule (via cron jobs)
3. Save formatted results to Obsidian vault
4. Can be monitored and tracked

## When to Use
- When you want to create custom stock/scanning analysis
- When you need analysis to run automatically on a schedule
- When you want results saved to your Obsidian vault for review
- When you need to track multiple financial data sources
- When you want to combine web crawling with sentiment analysis

## Core Components

### 1. Analysis Skill Creation
Create a custom skill that includes:
- **Data Sources**: Define where to get information (websites, APIs, social media)
- **Analysis Logic**: Define what to look for (volume spikes, sentiment, patterns)
- **Output Format**: Define how results should be presented
- **Error Handling**: Define what to do when sources fail

### 2. Automation Setup
Set up scheduled execution using:
- **Cron Jobs**: Schedule the skill to run at specific times
- **Skill Chaining**: Combine multiple skills (e.g., analysis + note saving)
- **Time Filtering**: Ensure only recent data is analyzed
- **Source Validation**: Validate data quality and freshness

### 3. Result Storage
Configure automatic saving to:
- **Obsidian Vault**: Save results as formatted notes
- **Proper Frontmatter**: Include metadata for filtering and linking
- **Consistent Naming**: Use date-based filenames for easy sorting
- **Tagging System**: Add relevant tags for discovery

## Workflow Steps

### Step 1: Define Analysis Requirements
- What financial instruments to analyze (stocks, crypto, etc.)
- What data sources to use (financial sites, social media, news)
- What specific metrics or patterns to look for
- What time sensitivity is required (real-time, daily, weekly)

### Step 2: Create the Analysis Skill
Create a custom Hermes skill that:
- Uses appropriate data extraction methods (firecrawl, web_search, etc.)
- Applies your analysis logic and filters
- Formats output in a consistent, readable way
- Includes risk disclaimers and limitations

### Step 3: Set Up Automation
Configure a cron job that:
- Runs your analysis skill on the desired schedule
- Chains with appropriate output skills (obi-notes, etc.)
- Includes proper error handling and logging
- Runs during appropriate market hours

### Step 4: Configure Output Storage
Set up the result saving to:
- Create appropriate folder structure in Obsidian
- Generate properly formatted markdown with frontmatter
- Include metadata about the analysis (time, sources, etc.)
- Add relevant tags for easy discovery and filtering

### Step 5: Monitor and Maintain
- Check that the cron job runs successfully
- Verify output is correctly formatted and saved
- Update analysis logic as market conditions change
- Refresh API keys and credentials as needed

## Example: Market Alpha Scout
The market_alpha_scout skill demonstrates this workflow:
- **Analysis Skill**: market_alpha_scout (research category)
- **Data Sources**: 
  - Stockbro.id (firecrawl crawl with Google Workspace auth)
  - Financial news sites (Google search: detik, kontan, bisnis)
  - Social sentiment (Google search: X/Twitter content like @happenfed)
- **Schedule**: Weekdays at 08:15 WIB (before market open)
- **Output**: Saved to Notes/Stockpick/Stockpick - [Tanggal].md
- **Features**: 
  - Volume filtering (V > V_avg20)
  - Time sensitivity (last 12 hours)
  - Multi-source validation
  - High conviction setup identification
  - Sector diversification

## Integration Notes
This approach integrates multiple Hermes skills:
- **crawl4ai** (primary): Self-hosted web scraping via Crawl4AI (free, unlimited)
- **firecrawl** (fallback): For web crawling when Crawl4AI unavailable
- **web_search**: DuckDuckGo search via Crawl4AI wrapper
- **obi-notes**: For saving results to Obsidian vault
- **cronjob**: For scheduling automated execution
- **skill-documentation**: For maintaining skill documentation

## Prerequisites
- Crawl4AI: installed in Hermes venv (`pip install crawl4ai` + `playwright install chromium`)
- Python 3.11 (Hermes venv): `~/.hermes/hermes-agent/venv/bin/python3.11`
- Firecrawl (optional fallback): API key for when Crawl4AI fails
- Access to financial data sources
- Obsidian vault configured for saving analysis results

## Customization Options
This workflow can be adapted for:
- Different financial instruments (crypto, forex, commodities)
- Different analysis techniques (technical, fundamental, sentiment)
- Different schedules (intraday, daily, weekly, monthly)
- Different output formats (alerts, reports, watchlists)
- Different notification methods (email, messaging, dashboard)

## Verification Checklist
After setting up financial analysis automation:
- [ ] Analysis skill creates and executes without errors
- [ ] Data is correctly extracted from all sources
- [ ] Analysis logic is applied correctly (filters, calculations)
- [ ] Output is properly formatted and readable
- [ ] Results are saved to the correct Obsidian location
- [ ] Frontmatter and metadata are correctly included
- [ ] Cron job runs on the scheduled time
- [ ] Results are generated and saved as expected
- [ ] Error handling works appropriately when sources fail