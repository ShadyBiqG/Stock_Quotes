# Migration to Stock Quotes v3.0

## Overview of Changes

Version 3.0 introduces major architectural improvements:

### Key Changes

1. **Removed `data/samples/Stock quotes.xlsx`**
   - Company list now stored in `config/companies.json`
   - Quotes fetched automatically via Yahoo Finance API
   - All data stored in database

2. **Configuration Split**
   - `config/api_keys.yaml` - API keys (in .gitignore)
   - `config/llm_config.yaml` - LLM model settings (in .gitignore)
   - `config/companies.json` - company list (in .gitignore)

3. **Automatic Quote Fetching**
   - New module `src/price_fetcher.py`
   - Yahoo Finance API integration
   - Fallback to default values

4. **Enhanced Company Management**
   - Add companies via web interface
   - Automatic save to `companies.json`
   - Export company list for backup

## Benefits of v3.0

✅ **Security**: API keys separated from code, not in Git  
✅ **Flexibility**: Easy company list management without Excel  
✅ **Automation**: Quotes update automatically  
✅ **Backup**: Company list always current  
✅ **Scalability**: Easy to add new data sources

## Automatic Migration

### Step 1: Run Migration Script

```bash
python scripts/migrate_to_v3.py
```

The script will:
1. Export companies from DB to `config/companies.json`
2. Create `config/api_keys.yaml` and `config/llm_config.yaml`
3. Optionally: clear DB (quotes and analyses)
4. Backup old files
5. Remove `data/samples/Stock quotes.xlsx`

### Step 2: Verify Configuration

After migration, check files:

```
config/
├── api_keys.yaml          # Verify API keys
├── llm_config.yaml        # Verify model settings
└── companies.json         # Verify company list
```

### Step 3: Testing

Run the application:

```bash
# CLI
python main.py

# Web interface
streamlit run app.py
```

## Manual Migration

If automatic migration fails, do it manually:

### 1. Create Structure

```bash
mkdir config
```

### 2. Create api_keys.yaml

Copy from `config.yaml`:

```yaml
# config/api_keys.yaml
openrouter_api_key: "sk-or-v1-your-key"
alphavantage_api_key: ""
```

### 3. Create llm_config.yaml

Copy remaining settings from `config.yaml`:

```yaml
# config/llm_config.yaml
openrouter:
  base_url: "https://openrouter.ai/api/v1"

models:
  - name: "GPT-4 Turbo"
    id: "openai/gpt-4-turbo"
    temperature: 0.3
    max_tokens: 1000
  # ... other models

# ... other sections
```

### 4. Create companies.json

Export companies from DB or create manually:

```json
{
  "companies": [
    {
      "ticker": "AAPL",
      "name": "Apple Inc.",
      "sector": "Technology",
      "industry": "Consumer Electronics"
    }
  ],
  "last_updated": "2026-02-04T12:00:00"
}
```

### 5. Update .gitignore

Ensure these are added:

```
config/api_keys.yaml
config/llm_config.yaml
config/companies.json
```

## Breaking Changes

### 1. Data Loading

**Before (v2.x):**
```python
from src.data_loader import load_stock_data

stocks = load_stock_data("data/samples/Stock quotes.xlsx", database=db)
```

**After (v3.0):**
```python
from src.data_loader import load_stock_data
from src.price_fetcher import YahooFinanceFetcher

price_fetcher = YahooFinanceFetcher()
stocks = load_stock_data("config/companies.json", database=db, price_fetcher=price_fetcher)
```

### 2. Configuration

**Before (v2.x):**
```python
import yaml

with open("config.yaml", 'r') as f:
    config = yaml.safe_load(f)
```

**After (v3.0):**
```python
# Use load_config() function from main.py or app.py
# It automatically handles the new structure
```

### 3. Adding Companies

**Before (v2.x):**
- Manual Excel file editing
- Adding rows with Ticker, Price, Change, Volume

**After (v3.0):**
- Via web interface: Settings → Company Management → Add
- Automatic price fetching via Yahoo Finance
- Automatic save to `companies.json`

## Rollback to v2.x

If issues occur, you can revert:

1. Restore backup `config.yaml`:
   ```bash
   copy config_backup_YYYYMMDD_HHMMSS.yaml config.yaml
   ```

2. Restore Excel file:
   ```bash
   copy "data\samples\Stock quotes_backup_YYYYMMDD_HHMMSS.xlsx" "data\samples\Stock quotes.xlsx"
   ```

3. Remove `config/` folder (optional)

4. Rollback code to previous commit:
   ```bash
   git checkout HEAD~1
   ```

## FAQ

### Q: What if migration fails with an error?

A: Check:
1. Presence of `config.yaml` in project root
2. Presence of database `data/stock_analysis.db`
3. Write permissions for `config/` folder

Run migration again - it's safe to re-run.

### Q: Can I use the old config.yaml?

A: Yes, v3.0 supports fallback to old format. But migration is recommended for:
- Better security (API keys in .gitignore)
- Automatic quote fetching
- Convenient company management

### Q: Where are quotes stored in v3.0?

A: All quotes are stored in database `data/stock_analysis.db`. When adding a new company:
1. Info fetched via LLM
2. Current price fetched via Yahoo Finance
3. Data saved to DB
4. Ticker added to `companies.json` for backup

### Q: How to add a company in v3.0?

A: Two ways:

**Via web interface (recommended):**
1. Open `streamlit run app.py`
2. Go to "Settings"
3. "Company Management" section → "Add new company"
4. Enter ticker (e.g., TSLA)
5. Click "Add"

**Manually:**
1. Edit `config/companies.json`
2. Add ticker to `companies` array
3. Quotes will be fetched automatically on next run

### Q: Should I delete old config.yaml?

A: Not required. Migration script creates a backup. You can delete `config.yaml` after successful v3.0 testing.

### Q: What if Yahoo Finance doesn't return data?

A: System automatically uses fallback:
1. Attempt to fetch via Yahoo Finance
2. On error - use default values (price=100.0, change=0%)
3. Data source saved in `price_sources` table

Check logs for details: `logs/analysis.log`

### Q: How to export company list?

A: In web interface:
1. Settings → Company Management
2. "Export to JSON" button
3. All companies from DB will be saved to `config/companies.json`

Use this for backup or transfer to another server.

## Support

If issues occur:
1. Check logs: `logs/analysis.log`
2. Ensure all config files are created
3. Check access rights to `config/` and `data/` folders
4. Create GitHub issue with problem description

## Migration Checklist

- [ ] Backup created for `config.yaml`
- [ ] Backup created for DB `data/stock_analysis.db`
- [ ] Run `python scripts/migrate_to_v3.py`
- [ ] Verified files in `config/`
- [ ] API keys correct in `config/api_keys.yaml`
- [ ] Company list in `config/companies.json`
- [ ] Tested launch: `python main.py`
- [ ] Tested web interface: `streamlit run app.py`
- [ ] Added test company via web interface
- [ ] Verified automatic sync with `companies.json`
- [ ] Deleted backups (after successful testing)
