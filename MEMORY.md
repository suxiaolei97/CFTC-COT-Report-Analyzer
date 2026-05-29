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
COT report/
├── main.py                      # 入口 — CWD固定, socket超时, requests monkey-patch
├── app.py                       # App — 按键分发, Tab/←→面板循环, 视图切换, start_year管理
├── config.py                    # 报告类型, 颜色主题, data/目录, 配置持久化
├── i18n.py                      # 中英文双语翻译 (动态热切换)
├── requirements.txt
├── models/
│   └── cot_model.py             # CotData — 动态列名发现, 多年合并, 本地缓存, COT Index, sparkline
└── screens/
    ├── loading_screen.py        # 旋转 spinner + ThreadPoolExecutor + 主线程轮询
    ├── main_screen.py           # 三栏: 市场列表 | DataTable着色 | 详情(sparkline+COT Index+持仓)
    ├── dataset_screen.py        # F2 — 切换报告类型
    ├── analysis_screen.py       # F4 — SSE流式分析 + markdown剥离 + 防重复调用
    └── settings_screen.py       # F12 — API Key/模型/思考强度/报告类型/年份范围/语言
```

## How to Run

```powershell
git clone https://github.com/suxiaolei97/CFTC-COT-Report-Analyzer.git
cd CFTC-COT-Report-Analyzer
pip install -r requirements.txt
python main.py
```

首次运行从 CFTC 下载数据到 `data/` 目录。后续读缓存（~0.3s）。F5 删缓存强制重载。

## Data Source

`cot_reports` library. Default: `legacy_futopt`, year range 2018-2026.

7 种报告类型 (F2): legacy_fut / legacy_futopt / supplemental_futopt / disaggregated_fut / disaggregated_futopt / TFF_fut / TFF_futopt

## Key Bindings

| 键 | 功能 |
|-----|------|
| `↑` `↓` | 市场列表内导航/高亮 |
| `Enter` | 选中市场 → 更新数据表 + 详情 |
| `←` `→` | 面板切换: 列表 ↔ 数据表 ↔ 详情 |
| `Tab` | 同上（备用） |
| `/` | 聚焦搜索栏 |
| `Esc` | 清空搜索 / 聚焦列表 |
| `F2` | 切换报告类型 |
| `F4` | DeepSeek 流式分析 |
| `F5` | 删除缓存 + 重新下载 |
| `F12` | 全局设置 |
| `q` | 退出 |

## Settings (F12)

配置保存在 `~/.cot_tui_config.json`。

| 设置项 | 说明 | 默认值 |
|--------|------|--------|
| API Key | DeepSeek API 密钥 | — |
| Model | V4 Flash / V4 Pro | Pro |
| Thinking Intensity | Disabled / Low / Medium / High | Medium |
| Default Report Type | 7 种可选 | legacy_futopt |
| End Year | 截止年份 | 2026 |
| Start Year | 起始年份（多年数据） | 2018 |
| Language | 中文 / English | 中文 |

## Multi-Year Data

从 Start Year 到 End Year 逐年下载并合并到 `data/{report}_{start}_{end}.txt`。多年数据使 COT Index 和 sparkline 准确度大幅提升。

## DeepSeek Analysis (F4)

- **流式输出**: SSE 逐 token, 0.15s 轮询刷新 RichLog
- **Markdown 剥离**: `##`, `**`, `*` 自动移除
- **防重复调用**: `_busy` 锁防止点击多次
- **线程安全**: executor 完成后 `shutdown`, timer 使用后 `stop`
- **System Prompt**: 通过 i18n 动态切换中英文

## Data Model

### Dynamic Column Detection
`_find_date_col()` / `_find_market_col()` 按正则自动匹配，兼容所有 7 种报告类型的列名差异。

### COT Index
0-100 指示当前非商业净头寸在历史范围中的位置:
- `> 80`: 极端做多, `< 20`: 极端做空, `20-80`: 中性

### ASCII Sparkline
Unicode 方块字符 `▁▂▃▄▅▆▇█` 绘制净头寸历史走势。

### DataTable 着色
净头寸正值绿色加粗, 负值红色加粗, 零值灰色。

## i18n

`i18n.py` 包含 70+ 条中英对照。使用 `t(key)` 获取翻译，`set_lang("en"/"zh")` 热切换。F12 切换语言后立即生效（刷新主界面所有标签）。

## Loading Screen Architecture

工作线程只写简单属性 (`_status`, `_result`, `_error`, `_complete`), 主线程 `set_interval` 轮询。excutor 完成后自动 shutdown。

## Textual 8.x Compatibility

| 旧 API | 8.x 替代 |
|--------|----------|
| `Label.renderable` | `Label.render().plain` |
| `ListItem.query_one(Label)` | `ListItem(name=xxx)` → `event.item.name` |
| `ListView.preserve_focus()` | 直接 `clear()` + `extend()` |
| `Screen.call_from_thread()` | 轮询模式 |
| `RadioButton(value=key)` | `id="prefix-key"` |
| `self._running` | 避用, 改 `self._busy` |
| Screen CSS 需 `layout: vertical` | 否则鼠标点击 crash |

## Color Theme

```python
bg: "#0f0f1a"  panel_bg: "#16162a"  border: "#2a2a5a"
text: "#c0c0e0"  accent: "#5a8ad4"  green: "#4ee04e"
red: "#e05050"  yellow: "#e0c040"  cyan: "#40c0c0"
```

---

## Future Enhancements

### Phase 2 — 交互增强
- [ ] 自选市场书签
- [ ] 多市场对比
- [ ] 数据排序（点击列头）
- [ ] 市场分类过滤
- [ ] 历史日期导航

### Phase 3 — AI 增强
- [ ] 批量分析
- [ ] 自定义分析模板
- [ ] 分析历史记录
- [ ] 多轮对话

### Phase 4 — 体验优化
- [ ] 主题切换
- [ ] 快捷键自定义
- [ ] 数据导出 CSV/Excel
- [ ] 自动刷新
- [ ] SQLite 持久化
