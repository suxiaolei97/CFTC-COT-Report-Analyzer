# CFTC COT TUI Dashboard

## Overview

Python Textual TUI 数据大屏，结构化浏览 CFTC Commitments of Traders (COT) 报告，集成 DeepSeek AI 流式分析，支持中英文双语。

## Stack

| 组件 | 用途 |
|------|------|
| Python 3.14+ | 运行环境 |
| Textual 8.2.7 | TUI 框架 |
| cot_reports 0.1.3 | CFTC 数据下载与解析 |
| pandas 3.x | 数据处理 |
| httpx 0.28 | DeepSeek API (SSE 流式) |
| Rich 15.x | 文本着色 |

## Project Structure

```
├── main.py                     # 入口、CWD固定、HTTP超时patch
├── app.py                      # 按键分发、面板循环、视图管理
├── config.py                   # 报告类型、颜色主题、data/目录、配置持久化
├── i18n.py                     # 中英双语 (±70条)、动态热切换
├── requirements.txt
├── models/
│   └── cot_model.py            # CotData — 三套分类体系、动态列发现、多年合并、COT Index、sparkline
└── screens/
    ├── loading_screen.py       # Spinner + ThreadPoolExecutor + 轮询
    ├── main_screen.py          # 三栏：列表|DataTable着色|详情(sparkline+COT Index)
    ├── dataset_screen.py       # F2 — 切换报告类型
    ├── analysis_screen.py      # F4 — 市场列表+搜索、可编辑提示词、SSE流式分析
    └── settings_screen.py      # F12 — API Key/模型/思考/报告类型/年份/Top N/语言
```

## How to Run

```powershell
git clone https://github.com/suxiaolei97/CFTC-COT-Report-Analyzer.git
cd CFTC-COT-Report-Analyzer
pip install -r requirements.txt
python main.py
```

首次从 CFTC 下载到 `data/`，后续读缓存（~0.3s）。F5 强制重载。

## Key Bindings

| 键 | 功能 |
|-----|------|
| `↑` `↓` | 列表导航 |
| `Enter` | 选中市场 |
| `←` `→` | 面板切换 |
| `Tab` | 同上(备用) |
| `/` | 搜索市场 |
| `Esc` | 清空搜索 |
| `F2` | 切换报告类型 |
| `F4` | DeepSeek 分析 |
| `F5` | 强制刷新 |
| `F12` | 设置 |
| `q` | 退出 |

## Settings (F12)

| 项 | 说明 | 默认 |
|----|------|------|
| API Key | DeepSeek 密钥 | — |
| Model | V4 Flash / Pro | Pro |
| Thinking | Disabled/Low/Medium/High | Medium |
| Report Type | 7种 | legacy_futopt |
| End Year | 截止年 | 2026 |
| Start Year | 起始年 | 2018 |
| Top N | 排行榜数量 | 5 |
| Language | 中文/English | 中文 |

## COT Report Category Systems

三种报告类型体系自动检测：

| Legacy | Disaggregated | TFF |
|--------|--------------|-----|
| 非商业 Non-Commercial | 生产商 Producer/Merchant | 交易商 Dealer |
| 商业 Commercial | 掉期商 Swap Dealers | 资产管理 Asset Manager |
| 非报告 Non-Reportable | 管理基金 Managed Money | 杠杆基金 Leveraged |
| 报告合计 Total Reportable | 其他报告 Other Rept | 其他报告 Other Rept |
| — | 非报告 Non-Rept | 非报告 Non-Rept |
| — | 报告合计 Total Rept | 报告合计 Total Rept |

## DeepSeek Analysis (F4)

- **市场选择**：可搜索 ListView + 输入框，实时过滤 500+ 市场
- **System Prompt**：可编辑 TextArea，自动保存到配置
- **分析上下文**：可编辑，切换市场自动更新
- **结果**：TextArea(read_only)，可选中复制
- **流式输出**：SSE 逐 token，0.15s 刷新
- **防重复**：`_busy` 锁

## COT Index

0-100，当前净头寸在历史范围中的位置。`>80` 极端做多，`<20` 极端做空。需 3+ 年数据才有参考意义。

## Textual 8.x Compatibility

| 旧 | 新 |
|----|-----|
| `Label.renderable` | `Label.render().plain` |
| `ListView.preserve_focus()` | `clear()`+`extend()` |
| `Screen.call_from_thread()` | 轮询模式 |
| `RadioButton(value=key)` | `id="prefix-key"` |
| `\W` in regex | `[\W_]` (underscore is `\w` in Python) |
| Screen 无 layout | 需 `layout: vertical` |

## Future

### Phase 2
- [ ] 自选书签、多市场对比、列头排序、分类过滤、日期导航

### Phase 3
- [ ] 批量分析、自定义模板、分析历史、多轮对话

### Phase 4
- [ ] 主题切换、快捷键自定义、CSV导出、自动刷新、SQLite
