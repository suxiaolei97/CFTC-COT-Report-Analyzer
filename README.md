# CFTC COT Report Analyzer

A Python Textual TUI dashboard for browsing and analyzing CFTC Commitments of Traders (COT) reports with real-time DeepSeek AI streaming analysis.

## Features

- **7 COT Report Types** — Legacy, Disaggregated, Supplemental, TFF with auto category detection
- **Multi-Year Data** — `data/` folder caching; COT Index accurate with 3+ years
- **Three-Panel Layout** — Searchable market list, color-coded DataTable, detail pane
- **COT Index (0-100)** — Net position in historical range; >80 extreme long, <20 extreme short
- **ASCII Sparklines** — Unicode ▁-█ trend visualization
- **DeepSeek AI (F4)** — Streaming analysis with editable system prompt and context
- **Searchable Market Chooser** — Type to filter 500+ markets in ListView
- **i18n CN/EN** — Instant language switch via F12 Settings
- **Copyable Results** — TextArea output supports text selection

## Quick Start

```powershell
git clone https://github.com/suxiaolei97/CFTC-COT-Report-Analyzer.git
cd CFTC-COT-Report-Analyzer
pip install -r requirements.txt
python main.py
```

First launch downloads COT data to `data/`. Subsequent runs load from cache (~0.3s).

## Key Bindings

| Key | Action |
|-----|--------|
| `↑` `↓` | Navigate lists |
| `Enter` | Select market |
| `←` `→` | Switch panels |
| `Tab` | Alt panel cycling |
| `/` | Focus search |
| `Esc` | Clear search |
| `F2` | Switch report type |
| `F4` | AI analysis |
| `F5` | Force refresh |
| `F12` | Settings |
| `q` | Quit |

## Settings (F12)

Saved to `~/.cot_tui_config.json`:

| Setting | Options | Default |
|---------|---------|---------|
| API Key | DeepSeek key | — |
| Model | V4 Flash / V4 Pro | Pro |
| Thinking | Disabled/Low/Medium/High | Medium |
| Report Type | 7 types | legacy_futopt |
| End Year | — | 2026 |
| Start Year | — | 2018 |
| Top N | Analysis rank count | 5 |
| Language | 中文 / English | 中文 |

## Category Systems

Auto-detected per report type:

| Legacy | Disaggregated | TFF |
|--------|--------------|-----|
| Non-Commercial | Producer/Merchant | Dealer |
| Commercial | Swap Dealers | Asset Manager |
| Non-Reportable | Managed Money | Leveraged Funds |
| Total Reportable | Other Reportables | Other Rept |
| — | Non-Reportable | Non-Reportable |
| — | Total Reportable | Total Reportable |

## Stack

| Component | Usage |
|-----------|-------|
| Textual 8.2.7 | TUI framework |
| cot_reports | CFTC data |
| pandas | Processing |
| httpx | DeepSeek API (SSE) |
| Rich | Text styling |

## License

GPL-3.0

## Acknowledgments

- [cot_reports](https://github.com/NDelventhal/cot_reports) — CFTC data
- [Textual](https://github.com/Textualize/textual) — TUI framework
- [DeepSeek](https://deepseek.com) — AI API
- [pandas](https://pandas.pydata.org) — data
- [httpx](https://www.python-httpx.org) — HTTP
- [Rich](https://github.com/Textualize/rich) — rendering
