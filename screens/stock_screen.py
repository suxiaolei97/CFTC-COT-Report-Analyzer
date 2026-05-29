import json
import plotext as _plt
import time as _time_mod
from concurrent.futures import ThreadPoolExecutor

import requests

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import Button, DataTable, Input, Label, RichLog, Static

from rich.text import Text as RichText

from i18n import t
from models.stock_model import MAJOR_STOCKS

_NASDAQ_HDR = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}


class StockModel:
    def __init__(self):
        self._exec = ThreadPoolExecutor(max_workers=8)
        self._quotes = {}
        self._chart_data = {}
        self._chart_ready = False
        self._quotes_updated = False

    def shutdown(self): self._exec.shutdown(wait=False)

    def fetch_all(self, syms=None):
        self._exec.submit(self._do_fetch_all, list(syms or MAJOR_STOCKS))

    def fetch_chart(self, sym, interval="day"):
        self._exec.submit(self._do_fetch_chart, sym, interval)

    def dynamic_fetch(self, sym):
        self._exec.submit(self._do_dynamic, sym)

    def _fetch_quote(self, sym):
        try:
            r = requests.get(f"https://api.nasdaq.com/api/quote/{sym}/info?assetclass=stocks", headers=_NASDAQ_HDR, timeout=5)
            if r.status_code != 200: return self._empty(sym)
            d = r.json().get("data") or {}
            p = d.get("primaryData") or {}
            ps = p.get("lastSalePrice","").replace("$","").replace(",","")
            cs = p.get("netChange","").replace("$","").replace(",","")
            pct = p.get("percentageChange","").replace("%","")
            pr = float(ps) if ps and ps!="N/A" else 0
            return {"symbol":sym,"price":pr,"change":float(cs) if cs and cs!="N/A" else 0,
                    "change_pct":float(pct) if pct and pct!="N/A" else 0,
                    "name":d.get("companyName",sym) or sym}
        except: return self._empty(sym)

    def _empty(self,s): return {"symbol":s,"price":0,"change":0,"change_pct":0,"name":s}

    def _do_fetch_all(self, syms):
        import re
        r={}
        for i in range(0,len(syms),60):
            b=syms[i:i+60]
            try:
                resp=requests.get(f"http://qt.gtimg.cn/q={','.join('us'+x for x in b)}",timeout=12)
                if resp.status_code==200:
                    for ln in resp.text.strip().split("\n"):
                        m=re.search(r'v_us(\w+)="(.*)"',ln.strip())
                        if m:
                            s=m.group(1);v=m.group(2).split("~")
                            if len(v)>33:
                                r[s]={"symbol":s,"price":float(v[3]) if v[3] else 0,
                                      "change":float(v[31])if v[31]else 0,
                                      "change_pct":float(v[32])if v[32]else 0,
                                      "name":v[46]if len(v)>46 and v[46]else v[1],
                                      "pe":v[47]if len(v)>47 else"",
                                      "high_52w":v[48]if len(v)>48 else"","low_52w":v[49]if len(v)>49 else"",
                                      "high":v[33]if len(v)>33 else"","low":v[34]if len(v)>34 else""}
            except: pass
        self._quotes=r; self._quotes_updated=True

    def _do_dynamic(self,sym):
        self._quotes[sym]=self._fetch_quote(sym)
        self._quotes_updated=True

    def _do_fetch_chart(self,sym,interval):
        period="3mo" if interval=="day" else("6mo" if interval=="week" else "5d")
        try:
            r=requests.get(f"https://api.nasdaq.com/api/quote/{sym}/chart?assetclass=stocks&fromdate=2026-01-01&todate=2026-06-01",headers=_NASDAQ_HDR,timeout=10)
            if r.status_code==200:
                chart=(r.json().get("data",{})or{}).get("chart",[])or[]
                opens,highs,lows,closes=[],[],[],[]
                for c in chart:
                    z=c.get("z",{})
                    try:
                        o=float(z.get("open",0)or 0);hi=float(z.get("high",0)or 0)
                        lo=float(z.get("low",0)or 0);cl=float(z.get("close",0)or 0)
                        if o and cl:
                            opens.append(o);highs.append(hi);lows.append(lo);closes.append(cl)
                    except: pass
                if interval=="week":
                    opens,highs,lows,closes=self._to_weekly(opens,highs,lows,closes)
                n=max(len(opens)//20,1)
                self._chart_data={"Open":opens[::n],"High":highs[::n],"Low":lows[::n],"Close":closes[::n]}
        except: self._chart_data={}
        self._chart_ready=True

    def _to_weekly(self,o,h,l,c):
        wo,wh,wl,wc=[],[],[],[]
        for i in range(0,len(o),5):
            b=o[i:i+5]
            if not b: break
            wo.append(b[0])
            wh.append(max(h[i:i+5]))
            wl.append(min(l[i:i+5]))
            wc.append(c[min(i+4,len(c)-1)])
        return wo,wh,wl,wc

    @staticmethod
    def chart_render(data, width=70, height=15):
        if not data or not data.get("Open"): return RichText("No chart data")
        try:
            _plt.clear_figure()
            _plt.date_form('')
            x=list(range(len(data["Open"])))
            _plt.candlestick(x,data,colors=[(200,60,60),(60,200,60)])
            _plt.plotsize(max(width,30),max(height,8))
            _plt.theme('dark')
            _plt.ticks_color((180,180,180))
            _plt.canvas_color((18,18,42))
            _plt.axes_color((42,42,90))
            raw=_plt.build()
            return RichText.from_ansi(raw)
        except:
            return RichText("Chart render error")


class StockScreen(Screen[None]):
    CSS = """
    StockScreen { layout: horizontal; background: #0f0f1a; }
    #stock-left { width: 3fr; height: 100%; padding: 1; border-right: thick #2a2a5a; }
    #stock-right { width: 4fr; height: 100%; padding: 1; }
    #stock-search { width: 100%; margin-bottom: 1; }
    #stock-table-container { height: 2fr; border: solid #2a2a5a; background: #16162a; }
    #stock-table { height: 100%; }
    #stock-chart-container { height: 3fr; border: solid #2a2a5a; background: #16162a; }
    #stock-chart-title { color: #7aafff; text-style: bold; height: 1; padding: 0 1; background: #1a1a3a; }
    #stock-chart { height: 1fr; padding: 0 1; }
    #stock-info { height: 2fr; border: solid #2a2a5a; background: #16162a; margin-top: 1; }
    #stock-info-title { color: #7aafff; text-style: bold; height: 1; padding: 0 1; background: #1a1a3a; }
    #stock-info-log { height: 1fr; }
    #stock-hint { height: 1; padding: 0 1; margin-top: 1; background: #1a1a3a; color: #c0c0e0; }
    #stock-count { color: #606080; }
    Button { margin-right: 1; }
    """

    def __init__(self):
        super().__init__()
        self.title="Stock Market"
        self.model=StockModel()
        self._selected=""
        self._interval="day"

    def compose(self):
        with Container(id="stock-left"):
            with Horizontal():
                yield Input(placeholder=f"{t('search')}", id="stock-search")
                yield Static("Loading...", id="stock-count")
            with Container(id="stock-table-container"):
                yield DataTable(id="stock-table", cursor_type="row")
            yield Static(f"F3:COT | Enter:select | {t('stock_auto_refresh')}", id="stock-hint")

        with Container(id="stock-right"):
            with Container(id="stock-chart-container"):
                yield Label("Chart", id="stock-chart-title")
                yield Static("", id="stock-chart")
            with Container(id="stock-info"):
                yield Label(t("stock_detail"), id="stock-info-title")
                yield RichLog(id="stock-info-log", highlight=True, markup=True, wrap=True)
            with Horizontal(id="chart-buttons"):
                yield Button("Day", id="btn-day", variant="primary")
                yield Button("Week", id="btn-week", variant="default")
                yield Button("Intraday", id="btn-intra", variant="default")

    def on_mount(self):
        self.model.fetch_all()
        self.set_interval(0.1, self._poll)

    def _poll(self):
        if self.model._quotes_updated:
            self.model._quotes_updated=False
            self._update_table()
            try: self.query_one("#stock-count",Static).update(f"{len(self.model._quotes)} stocks")
            except: pass
        if self.model._chart_ready:
            self._show_chart()
            self.model._chart_ready=False

    def _row_data(self,sym,q):
        pr=q.get("price",0);pct=q.get("change_pct",0);nm=q.get("name",sym);
        if not pr: return (sym,RichText(nm[:18],style="dim"),RichText("--",style="dim"),RichText("--",style="dim"))
        cs="bold green" if pct>=0 else "bold red"
        return (RichText(sym,style=cs),RichText(nm[:18],style=""),
                RichText(f"{pr:.2f}",style=cs),
                RichText(f"{pct:+.2f}%",style="bold green" if pct>=0 else "bold red"))

    def _update_table(self):
        try:
            dt=self.query_one("#stock-table",DataTable)
            dt.clear(columns=True)
            dt.add_columns(t("symbol"),t("stock_name"),t("stock_price"),t("stock_change"))
            for s in sorted(self.model._quotes.keys()):
                dt.add_row(*self._row_data(s,self.model._quotes[s]))
        except: pass

    def on_input_changed(self,event):
        if event.input.id!="stock-search": return
        q=event.value.strip().upper()
        try:
            dt=self.query_one("#stock-table",DataTable)
            dt.clear(columns=True)
            dt.add_columns(t("symbol"),t("stock_name"),t("stock_price"),t("stock_change"))
            for s in sorted(self.model._quotes.keys()):
                d=self.model._quotes[s];nm=str(d.get("name",s))
                if q and q not in s.upper() and q.upper() not in nm.upper(): continue
                dt.add_row(*self._row_data(s,d))
            if q and q not in self.model._quotes:
                self.model.dynamic_fetch(q)
        except: pass

    def on_data_table_row_highlighted(self,event):
        try:
            dt=self.query_one("#stock-table",DataTable)
            sym=str(dt.get_row(event.row_key)[0])
            if sym==self._selected: return
            self._selected=sym
            self._show_info()
            self.model.fetch_chart(sym,self._interval)
        except: pass

    def _show_info(self):
        try:
            log=self.query_one("#stock-info-log",RichLog)
            log.clear()
            q=self.model._quotes.get(self._selected,{})
            if not q: return
            pr=q.get("price",0);pct=q.get("change_pct",0);nm=q.get("name",self._selected)
            c="green" if pct>=0 else "red"
            log.write(f"[bold]{nm} ({self._selected})[/]")
            log.write(f"[{c}]${pr:.2f}  {pct:+.2f}%[/]")
            for k,lb in [("pe","PE"),("high_52w","52W High"),("low_52w","52W Low"),("high","Day High"),("low","Day Low")]:
                v=q.get(k,""); 
                if v: log.write(f"{lb}: {v}")
        except: pass

    def _show_chart(self):
        try:
            chart=self.query_one("#stock-chart",Static)
            r=StockModel.chart_render(self.model._chart_data,width=65,height=12)
            chart.update(r)
        except: pass

    def on_button_pressed(self,event):
        bid=event.button.id
        if bid=="btn-day": self._interval="day"
        elif bid=="btn-week": self._interval="week"
        elif bid=="btn-intra": self._interval="intra"
        else: return
        for b in self.query("Button"):
            b.variant="primary" if b.id==bid else "default"
        if self._selected:
            self.model.fetch_chart(self._selected,self._interval)
