# Insider Signal Intelligence - Learning Project

> **Personal Learning Project**: This is an educational project created in my free time to learn about financial data analysis, web scraping, and automated workflows. All data used is publicly available.

## 📚 Project Overview

This project is a hands-on learning exercise to understand:
- **Web scraping** techniques using Python
- **Financial data analysis** from public sources
- **GitHub Actions** for workflow automation
- **Data enrichment** pipelines
- **Signal generation** algorithms
- **HTML report generation**

**Disclaimer**: This is purely for educational purposes. Not financial advice. All data is from public sources.

---

## 🎯 Learning Objectives

### What I'm Learning
1. **Python Programming**
   - Object-oriented design patterns
   - Data processing with pandas
   - Web scraping with BeautifulSoup and Selenium
   - SQLite database operations

2. **Financial Data Analysis**
   - Understanding insider trading patterns
   - SEC filing analysis (Form 4, 8-K)
   - Stock price analysis
   - Sector performance comparison

3. **DevOps & Automation**
   - GitHub Actions workflows
   - Automated scheduling (cron jobs)
   - CI/CD pipelines
   - GitHub Pages deployment

4. **Data Engineering**
   - ETL pipeline design
   - Data caching strategies
   - Multi-stage data enrichment
   - JSON data structures

---

## 🔍 What This Project Does

### Data Collection (Public Sources Only)
- Scrapes **public** insider trading data from [OpenInsider.com](http://openinsider.com)
- Fetches **public** SEC filings from [SEC Edgar](https://www.sec.gov/edgar)
- Gets **public** stock prices from Yahoo Finance

### Data Processing
1. **Fetch**: Collect insider transaction data
2. **Parse**: Extract structured information
3. **Enrich**: Add context from SEC filings and market data
4. **Filter**: Keep only open-market purchases
5. **Analyze**: Generate buy signals using custom algorithms
6. **Report**: Create interactive HTML reports

### Automation
- Runs automatically every day at 6:35 AM ET
- Generates fresh reports with latest data
- Publishes to GitHub Pages for easy viewing

---

## 🛠️ Technical Stack

### Languages & Frameworks
- **Python 3.11** - Core programming language
- **BeautifulSoup4** - HTML parsing
- **SeleniumBase** - Web scraping with bot detection avoidance
- **Pandas** - Data manipulation
- **SQLite** - Local caching

### APIs & Data Sources
- **OpenInsider** - Public insider trading data
- **SEC Edgar API** - Public SEC filings
- **Yahoo Finance** - Public stock market data

### Infrastructure
- **GitHub Actions** - Automated workflows
- **GitHub Pages** - Report hosting
- **Git** - Version control

---

## 📊 Project Architecture

```
Pipeline Flow:
┌─────────────┐
│ OpenInsider │ → Scrape public insider trades
└──────┬──────┘
       ↓
┌─────────────┐
│   Parser    │ → Extract structured data
└──────┬──────┘
       ↓
┌─────────────┐
│ SEC Filings │ → Enrich with Form 4 data
└──────┬──────┘
       ↓
┌─────────────┐
│   Filter    │ → Keep only purchases
└──────┬──────┘
       ↓
┌─────────────┐
│ Enrichments │ → Add 7 context layers
└──────┬──────┘
       ↓
┌─────────────┐
│   Signals   │ → Generate buy signals
└──────┬──────┘
       ↓
┌─────────────┐
│   Reports   │ → Create HTML reports
└─────────────┘
```

---

## 🚀 Getting Started (Local Development)

### Prerequisites
- Python 3.11+
- Git
- Virtual environment (recommended)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/qcom-anilyada/Signal.git
   cd Signal
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the pipeline**
   ```bash
   python main.py
   ```

### Output
- **JSON files**: `output/ALL_insider_trades_*.json`
- **HTML reports**: `reports/report_*.html`
- **Master index**: `index.html`
- **Logs**: `logs/pipeline_*.log`

---

## 📈 Features

### 7 Enrichment Modules
1. **Earnings Context** - Post-earnings price reactions
2. **Price Context** - Drawdowns, 52-week ranges
3. **Sector Context** - Sector performance comparison
4. **Insider History** - Historical insider behavior
5. **Insider Price** - Current vs. insider buy price
6. **Position Sizing** - Transaction size vs. market cap
7. **Insider Behavior** - Cluster buying, repeat purchases

### Signal Generation
- **Three-layer hybrid factor aggregation**
- Combines conviction, credibility, timing, coordination, and positioning
- Classifies signals: Strong Buy, Buy, Weak, Noise

### Interactive Reports
- Live market status indicator
- Filter by signal strength
- Detailed factor analysis
- Responsive design

---

## 🤖 Automated Workflow

### GitHub Actions
- **Schedule**: Daily at 6:35 AM ET
- **Trigger**: Manual or automatic
- **Process**: 
  1. Install dependencies
  2. Run pipeline
  3. Generate reports
  4. Commit results
  5. Deploy to GitHub Pages

### Workflow Features
- Random jitter (anti-detection)
- Concurrency control
- Automatic cleanup
- Error handling

---

## 📖 Learning Resources

### Concepts Explored
- **Insider Trading**: Legal purchases/sales by company insiders
- **SEC Filings**: Form 4 (insider transactions), 8-K (material events)
- **Signal Generation**: Quantitative analysis of trading patterns
- **Web Scraping**: Ethical data collection from public sources
- **Data Pipelines**: ETL processes and data enrichment

### Skills Developed
- Python programming
- Data analysis
- Web scraping
- API integration
- Workflow automation
- Git/GitHub
- HTML/CSS
- Documentation

---

## ⚖️ Legal & Ethical Considerations

### Data Sources
- ✅ All data is **publicly available**
- ✅ No proprietary or confidential information
- ✅ No paid APIs or premium data
- ✅ Respects robots.txt and rate limits

### Usage
- ✅ **Educational purposes only**
- ✅ Not financial advice
- ✅ No commercial use
- ✅ Personal learning project

### Compliance
- ✅ No CCI (Confidential Company Information)
- ✅ No PII (Personally Identifiable Information)
- ✅ No API keys or credentials in code
- ✅ Fair use of public data

---

## 🎓 What I Learned

### Technical Skills
- Building end-to-end data pipelines
- Implementing caching strategies for performance
- Creating automated workflows with GitHub Actions
- Generating interactive HTML reports
- Handling rate limits and bot detection

### Domain Knowledge
- Understanding SEC filing structures
- Analyzing insider trading patterns
- Interpreting market signals
- Financial data normalization

### Best Practices
- Code organization and modularity
- Error handling and logging
- Documentation and README writing
- Git workflow and version control

---

## 🔮 Future Enhancements (Learning Goals)

- [ ] Add unit tests (pytest)
- [ ] Implement data visualization (matplotlib/plotly)
- [ ] Create REST API (FastAPI)
- [ ] Add email notifications
- [ ] Implement backtesting framework
- [ ] Add more enrichment modules
- [ ] Create mobile-responsive UI
- [ ] Add database support (PostgreSQL)

---

## 📝 Project Structure

```
Signal/
├── .github/workflows/       # GitHub Actions
├── enrichments/            # 7 enrichment modules
├── cache/                  # SQLite cache
├── logs/                   # Execution logs
├── output/                 # JSON data
├── reports/                # HTML reports
├── main.py                 # Entry point
├── pipeline.py             # Pipeline orchestration
├── signal_generator.py     # Signal generation
├── requirements.txt        # Dependencies
└── README.md              # This file
```

---

## 🤝 Contributing

This is a personal learning project, but suggestions and feedback are welcome! Feel free to:
- Open issues for bugs or questions
- Suggest improvements
- Share learning resources

---

## 📄 License

This project is for educational purposes only. All data is from public sources.

**Disclaimer**: This is not financial advice. Do not use this for actual trading decisions. This is a learning project to understand data analysis and automation.

---

## 🙏 Acknowledgments

### Data Sources
- [OpenInsider](http://openinsider.com) - Public insider trading data
- [SEC Edgar](https://www.sec.gov/edgar) - Public SEC filings
- [Yahoo Finance](https://finance.yahoo.com) - Public stock data

### Learning Resources
- Python documentation
- GitHub Actions documentation
- Financial data analysis tutorials
- Web scraping best practices

---

## ⚠️ Important Notes

1. **Not Financial Advice**: This project is for learning purposes only
2. **Public Data Only**: All data sources are publicly available
3. **Educational Purpose**: Created to learn Python, data analysis, and automation
4. **No Guarantees**: Signals are experimental and not validated
5. **Personal Project**: Built in free time for skill development

---

**Last Updated**: April 2026  
**Status**: Active Learning Project  
**Purpose**: Educational & Skill Development
