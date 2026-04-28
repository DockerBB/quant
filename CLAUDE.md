# Quant Strategy System — Claude Code Reference

## 项目概述

A股多因子量化选股与信号生成系统，覆盖沪深A股 + 北交所 + ETF。

- **后端**: FastAPI + APScheduler + SQLite(元数据) + Parquet(行情/财务)
- **前端**: React 18 + Vite + Ant Design + ECharts + React Query
- **数据源**: akshare(主) + baostock(回退/历史)
- **运行环境**: Python 3.9（不要用 3.14，akshare 不支持），conda 环境名 `quant`

## 目录结构

```
backend/          # FastAPI 后端
  main.py         # 入口，注册路由和定时任务
  app/
    api/          # API 路由 (data, factors, strategies, signals, scheduler)
    core/         # 配置(Settings), 数据库(sqlite_session), 依赖注入
    data/         # 数据层: fetcher, store, pipeline, universe, adjust, limit_rules
    factors/      # 量化因子 (value/momentum/quality/growth/sentiment/technical/)
    strategy/     # Scorer(加权打分), SignalGenerator(信号生成), config_loader
    scheduler/    # APScheduler 管理
    models/       # Pydantic schemas
frontend/         # React 前端 (pnpm)
  src/pages/      # Dashboard, ScreeningResults, SignalDetail, SignalsRedirect, StockAdvisor, StrategyConfig, FactorManager, DataManagement
  src/hooks/      # useStockNameMap, useStockSectorMap, useStrategyApi, useDataApi, useFactorApi
  src/utils/      # indicators.ts (RSI, MACD, Volume 计算)
scripts/          # 数据脚本
  backfill_history.py      # 单线程批量回填沪深日线 (baostock)
  backfill_etf_history.py  # ETF 历史日线回填 (akshare fund_etf_hist_em)
  fetch_financials.py      # 批量拉取财报 (akshare 东方财富接口, 按季度)
  init_data.py             # 首次初始化全量数据
config/
  settings.yaml   # 全局配置
  strategies/     # 策略 YAML 定义
    strategy_template.yaml  # 价值动量精选
    pure_technical.yaml     # 纯技术面
```

## 当前策略（仅 2 个）

| 策略 | 风格 | 买入数 | 核心因子 |
|------|------|:------:|----------|
| 价值动量精选 | 均衡多因子 | 20 | PE+PB+ROE+MOM+RevenueYoY+GrossMargin+RSI+Turnover |
| 纯技术面 | 纯K线 | 10 | MOM(35%)+换手率变化(25%)+RSI(25%)+PS_TTM(15%) |

## 数据覆盖

| 市场 | 代码前缀 | 数据源 | 股票数 |
|------|----------|--------|:------:|
| 上证主板/科创板 | 60xxxx/688xxx | baostock(历史) + akshare(当日) | ~2,300 |
| 深证主板/创业板 | 00xxxx/30xxxx | baostock(历史) + akshare(当日) | ~2,900 |
| 北交所 | 8xxxxx/4xxxxx/92xxxx | akshare(历史+当日) | ~310 |
| ETF | 5xxxxx.SH/1xxxxx.SZ | akshare(历史+当日) | ~1,440 |

## 关键约定

- **Python 3.9** 运行。不用 Python 3.14（akshare 没适配）
- **conda 环境**: `quant`，位于 `D:\miniconda3\envs\quant`
- **前端包管理用 pnpm**，不用 npm（Node 24 的 npm 有兼容性问题）
- **数据追加不覆盖**: `write_daily()` / `write_parquet()` 会先读现有 Parquet，`pd.concat` 后 `drop_duplicates`，保留历史
- **因子不修改 Factor 基类**: 财务数据在策略运行时通过 `_enrich_with_financial()` merge 到日线 DataFrame
- **PE/PB 从 basic_eps/bps 计算**，不是直接取 pe/pb 列（baostock 数据没有这些列）
- **涨跌停阈值按板块**: 主板10% / 双创20% / 北交所30%（见 `limit_rules.py`）
- **ETF 无财报**: 财务因子返回 NaN，被 scorer 自动跳过。ETF 仅靠技术面因子（MOM/RSI/换手率）参与打分
- **ST 检测**: `refresh_stock_list()` 从名称前缀识别 ST/*ST（见 `pipeline.py:56-60`）
- **行业数据**: 来自财务批量API（`stock_yjbb_em`），存储在 `stock_info.industry`。`refresh_stock_list()` 会保留已有行业
- **后台不自动热重载 Python**: 修改后端代码后需手动重启

## 数据文件（不进入 Git）

| 文件 | 内容 | 生成方式 |
|------|------|----------|
| `data/parquet/daily/` | 日线 OHLCV，按年月分区 | `backfill_history.py` (baostock) + `backfill_etf_history.py` (akshare) |
| `data/financial/financial.parquet` | 季度财报 (ROE/毛利率/EPS等) | `fetch_financials.py` 或后端 `POST /api/data/refresh` (financial) |
| `data/quant.db` | 股票列表/交易日历/策略/信号 | `init_data.py` |

新电脑上从旧电脑拷贝 `data/` 文件夹即可，不用重新下载。

## 启动命令

```bash
# 后端 (Python 3.9, conda env: quant)
cd backend && python main.py          # http://127.0.0.1:8000

# 前端 (pnpm)
cd frontend && pnpm dev               # http://localhost:5173
```

## 数据更新

- 定时：每个交易日 15:30 自动刷新日线
- 手动日线：`python scripts/backfill_history.py`
- 手动 ETF 日线：`python scripts/backfill_etf_history.py`
- 手动财报：`python scripts/fetch_financials.py` 或前端「数据管理」→ 财务数据刷新
- 手动策略：`POST /api/strategies/{id}/run` 或前端「策略配置」→ 运行按钮

## 性能关键点

- **因子计算**: MOM_6M、RSI_14、Turnover_Change 使用 `groupby().apply()` 向量化，不要改回 `for code in universe` 循环
- **策略 lookback**: 250 天（等于 `strategies.py:141`），够覆盖 MOM_6M 的 147 个交易日
- **`read_daily()`**: 会按文件名（年月）跳过日期范围外的 Parquet 文件，按 ts_code 预检跳过不相关文件
- **信号 API**: `get_current_signals` 只查最新日期 + 5 列 SELECT（不含 detail_json），~0.3s 返回 7K 条
- **财务刷新**: `refresh_financial_batch()` 用批量 API `ak.stock_yjbb_em()`，8个季度 ~35s，不要改回逐个拉取

## 因子计算公式

- PE_TTM = close / basic_eps
- PB = close / bps
- PS_TTM = market_cap / revenue
- ROE_TTM = 直接取 `roe` 列
- MOM_6M = (close_{T-22} / close_{T-147}) - 1（扣除最近1月，避免短期反转）
- RSI_14 = 标准RSI公式（14日）
- Revenue_YoY / NetProfit_YoY = 直接取 `revenue_yoy` / `netprofit_yoy` 列
- GrossMargin_TTM = 直接取 `grossprofit_margin` 列
- Turnover_Change = (5日均换手 - 20日均换手) / 20日均换手
- Accruals_Ratio = (净利润 - 经营性现金流) / 总资产（当前缺少资产负债表，可能返回空）
- DYield = 需 `dv_ratio` 列（当前数据源缺失，返回空）
