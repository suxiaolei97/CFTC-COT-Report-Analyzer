# CFTC COT Report Analyzer

A Python Textual TUI dashboard for browsing and analyzing CFTC Commitments of Traders (COT) reports with real-time DeepSeek AI streaming analysis.

## Features

- **7 COT Report Types** — Legacy, Disaggregated, Supplemental, TFF (futures & options)
- **Multi-Year Data** — Download and merge years of historical COT data with local caching
- **Three-Panel Layout** — Market list with debounced search, color-coded DataTable, detail pane
- **COT Index** — 0-100 indicator showing current net position in historical range
- **ASCII Sparklines** — Unicode block-element trend visualization of net positions
- **DeepSeek AI Analysis (F4)** — Real-time streaming analysis with configurable model and thinking intensity
- **Arrow-Key Navigation** — `← →` switch panels, `↑ ↓` navigate items
- **Persistent Settings (F12)** — API key, model, thinking, report type, year range

## Screenshot

```
┌─ COT Dashboard — Legacy 期货+期权 ──────── [◉] ───── 2026-05-29 14:30 ─┐
│                                                                         │
│ ┌─ Left Panel ───┐ ┌─ Data Table ──────────┐ ┌─ Detail Panel ────────┐ │
│ │[Legacy 期货+期权]│ │                         │ │CORN - CBOT           │ │
│ │Latest: 2026-05-19│ │ Date      OI  ncm_L... │ │▂▃▄▅▆▇█▇▆▅▄▃▂▁       │ │
│ │[Search markets..]│ │ 2026-05-19  ...       │ │COT Index: 84 Extreme│ │
│ │                  │ │ 2026-05-12  ...       │ │                      │ │
│ │ WHEAT-SRW        │ │ 2026-05-05  ...       │ │非商业               │ │
│ │ CORN          ██ │ │ 2026-04-28  ...       │ │  Long:  537,404     │ │
│ │ SOYBEANS         │ │                         │ │  Short: 213,077     │ │
│ │                  │ │                         │ │  Net:  +324,327    │ │
│ └──────────────────┘ └────────────────────────┘ └─────────────────────┘ │
│ F2 Dataset F4 Analysis F5 Refresh F12 Settings q Quit | FLASH · medium │
└─────────────────────────────────────────────────────────────────────────┘
```

## Quick Start

```powershell
# Clone and run
git clone https://github.com/suxiaolei97/CFTC-COT-Report-Analyzer.git
cd CFTC-COT-Report-Analyzer
pip install -r requirements.txt
python main.py
```

First launch downloads ~1MB of COT data from cftc.gov. Subsequent runs load from local cache (~0.3s).

## Key Bindings

| Key | Action |
|-----|--------|
| `↑` `↓` | Navigate market list |
| `Enter` | Select market → update table + detail |
| `←` `→` | Switch panels (list ↔ table ↔ detail) |
| `Tab` | Alternate panel cycling |
| `/` | Focus search |
| `Esc` | Clear search / focus list |
| `F2` | Switch report type |
| `F4` | DeepSeek AI analysis |
| `F5` | Force re-download data |
| `F12` | Settings (API key, model, thinking, year range) |
| `q` | Quit |

## Settings (F12)

Settings persist to `~/.cot_tui_config.json`:

| Setting | Options | Default |
|---------|---------|---------|
| API Key | DeepSeek key | — |
| Model | V4 Flash / V4 Pro | Pro |
| Thinking | Disabled / Low / Medium / High | Medium |
| Report Type | 7 types | legacy_futopt |
| End Year | Year to load through | 2026 |
| Start Year | Multi-year range start | 2020 |

## COT Index

Measures where current non-commercial net position sits in its historical range (0-100):

- **> 80** — Extreme Long (potential reversal)
- **< 20** — Extreme Short (potential reversal)
- **20-80** — Neutral range

Requires 3+ years of data for reliable signals. Set Start Year to 2018 or earlier for best results.

## Stack

| Component | Usage |
|-----------|-------|
| Python 3.14+ | Runtime |
| Textual 8.2.7 | TUI framework |
| Pandas 3.x | Data processing |
| cot_reports 0.1.3 | CFTC data download |
| httpx 0.28 | DeepSeek API (SSE streaming) |
| Rich 15.x | Text styling |

## Project Structure

```
├── main.py                    # Entry point, HTTP timeout patch
├── app.py                     # App bindings, panel cycling, screen management
├── config.py                  # Report types, colors, config persistence
├── requirements.txt
├── models/
│   └── cot_model.py           # Data model, column discovery, COT Index, sparklines
└── screens/
    ├── loading_screen.py      # Loading spinner + async data fetch
    ├── main_screen.py         # 3-panel main view
    ├── dataset_screen.py      # Report type selector
    ├── analysis_screen.py     # DeepSeek streaming analysis
    └── settings_screen.py     # Global settings
```

## License

GPL-3.0

## Acknowledgments

- [cot_reports](https://github.com/NDelventhal/cot_reports) by Niall Delventhal — CFTC COT data download and parsing
- [Textual](https://github.com/Textualize/textual) by Textualize — terminal UI framework
- [DeepSeek](https://deepseek.com) — AI language model API
- [pandas](https://pandas.pydata.org) — data manipulation
- [httpx](https://www.python-httpx.org) — HTTP client with streaming
- [Rich](https://github.com/Textualize/rich) — terminal rich text rendering
