# CFTC COT TUI Dashboard

## Overview

Python Textual TUI 半可视化数据大屏，结构化管理 CFTC Commitments of Traders (COT) 报告，集成 DeepSeek AI 流式分析。

## Stack

| 组件 | 版本 | 用途 |
|------|------|------|
| Python | 3.14+ | 运行环境 |
| Textual | 8.2.7 | TUI 框架 |
| cot_reports | 0.1.3 | COT 数据下载与解析 |
| pandas | 3.0.3 | 数据处理与列映射 |
| httpx | 0.28.1 | DeepSeek API (SSE 流式) |
| requests | 2.34+ | HTTP 请求 (monkey-patch timeout) |
| rich | 15.0+ | DataTable 富文本着色 |

## Project Structure

```
COT report/
├── main.py                      # 入口 — CWD固定, socket超时, requests timeout monkey-patch
├── app.py                       # App — 按键分发, Tab/←→面板循环, 视图切换, start_year管理
├── config.py                    # REPORT_TYPES, COLORS, 配置持久化 (~/.cot_tui_config.json)
├── requirements.txt
├── MEMORY.md
├── models/
│   └── cot_model.py             # CotData — 动态列名发现, 多年合并, 本地缓存, COT Index, sparklines
└── screens/
    ├── loading_screen.py        # 旋转 spinner + ThreadPoolExecutor + 主线程轮询
    ├── main_screen.py           # 三栏: 市场列表 | DataTable着色 | 详情(sparkline+COT Index+持仓)
    ├── dataset_screen.py        # F2 — 切换报告类型
    ├── analysis_screen.py       # F4 — SSE流式分析 + markdown剥离 + 双重锁
    └── settings_screen.py       # F12 — API Key/Model/思考强度/报告类型/年份范围
```

## How to Run

```powershell
cd "C:\Users\suxia\Documents\Learning\COT report"
python main.py
```

首次运行从 CFTC 下载 ZIP 数据。后续读本地缓存。F5 删缓存强制重载。

## Data Source

`cot_reports` library. Default: `legacy_futopt`, year range 2020-2026.

**7 种报告类型 (F2):** legacy_fut / legacy_futopt / supplemental_futopt / disaggregated_fut / disaggregated_futopt / TFF_fut / TFF_futopt

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
| `F4` | DeepSeek 分析 |
| `F5` | 删除缓存 + 重新下载 |
| `F12` | 全局设置 |
| `q` | 退出 |

## Settings (`F12`)

配置保存在 `~/.cot_tui_config.json`，启动自动加载。

| 设置项 | 说明 | 默认值 |
|--------|------|--------|
| API Key | DeepSeek API 密钥 | — |
| Model | V4 Flash / V4 Pro | Pro |
| Thinking Intensity | Disabled / Low / Medium / High | Medium |
| Default Report Type | 7 种可选 | legacy_futopt |
| Default Year | 截止年份 | 2026 |
| Start Year | 起始年份（多年数据起点） | 2020 |

## Multi-Year Data

从 Start Year 到 Default Year 逐年下载并合并：
- 缓存格式: `{report}_{start}_{end}.txt` (如 `annualof_2020_2026.txt`)
- 多年数据使 COT Index 从 ~20 点 → N×52 点，准确度大幅提升
- CSS Sparkline 走势图自动变长

## DeepSeek Analysis (`F4`)

- **流式输出**: SSE 逐 token, 0.15s 轮询刷新
- **Markdown 剥离**: `##`, `**`, `*`, ` ``` ` 自动移除, RichLog markup=False
- **双重锁**: 禁止重复点击 Run
- **线程安全**: executor 用完自动 shutdown, timer 完成后 stop
- **System Prompt**: 中文 COT 分析师, 纯文本输出

## Data Model (`cot_model.py`)

### Column Detection
`_find_date_col()` / `_find_market_col()` 按正则自动匹配, 兼容所有 7 种报告类型的列名差异。

### COT Index
0-100 指示当前非商业净头寸在历史范围中的位置:
- `> 80` → 极端做多 (Extreme Long)
- `< 20` → 极端做空 (Extreme Short)
- 需 3 年以上历史数据才有参考意义

### ASCII Sparkline
Unicode 方块字符 `▁▂▃▄▅▆▇█` 绘制非商业净头寸历史走势, 显示在详情面板顶部。

### DataTable 着色
- 净头寸正值: 绿色加粗
- 净头寸负值: 红色加粗
- 多/空头寸正值: 绿色; 负值: 红色
- 零值: 灰色

## Loading Screen Architecture

工作线程只写简单属性 (`_status`, `_result`, `_error`, `_complete`), 主线程 `set_interval` 轮询:
- 正常: 读取 `_complete` → `dismiss(result)`
- 异常: 显示错误信息, spinner 停止

ThreadPoolExecutor 在完成/异常时自动 `shutdown(wait=False)`。

## Textual 8.x Compatibility Notes

| 旧 API | 8.x 替代 |
|--------|----------|
| `Label.renderable` | `Label.render().plain` |
| `ListItem.query_one(Label)` | `ListItem(name=xxx)` → `event.item.name` |
| `ListView.preserve_focus()` | 直接 `clear()` + `extend()` |
| `Screen.call_from_thread()` | 轮询模式: 写属性 + set_interval 读取 |
| `RadioButton(value=key)` | `id="prefix-key"`, 解析 id 获取键 |

## Color Theme

```python
COLORS = {
    "bg": "#0f0f1a",      "panel_bg": "#16162a",      "border": "#2a2a5a",
    "header": "#3a3a6a",  "text": "#c0c0e0",          "text_dim": "#606080",
    "accent": "#5a8ad4",  "accent_bright": "#7aafff",  "green": "#4ee04e",
    "red": "#e05050",     "yellow": "#e0c040",         "cyan": "#40c0c0",
    "orange": "#e08040",
}
```

---

## Future Enhancements

### Phase 2 — 交互增强
- [ ] **自选市场书签** — 收藏常用市场，快捷筛选
- [ ] **多市场对比** — 选中两个市场时并列显示持仓对比
- [ ] **数据排序** — 点击列头排序（按 OI、净头寸等）
- [ ] **市场分类过滤** — 按品种类别过滤（货币、能源、谷物、金属）
- [ ] **历史日期导航** — `←` `→` 切换历史报告日期，查看每周变化

### Phase 3 — AI 增强
- [ ] **批量分析** — 对 Top N 市场逐个调用 API，汇总报告
- [ ] **自定义分析模板** — 用户可编辑 System Prompt
- [ ] **历史分析记录** — 保存分析结果，支持回看
- [ ] **多轮对话** — 分析结果出来后可持续追问

### Phase 4 — 体验优化
- [ ] **主题切换** — 暗色/亮色主题
- [ ] **快捷键自定义** — 允许用户重绑定按键
- [ ] **数据导出** — 导出当前表格为 CSV / Excel
- [ ] **自动刷新** — 每周 CFTC 更新日自动拉取最新数据
- [ ] **SQLite 持久化** — 数据缓存到 SQLite，增量更新，更快启动
