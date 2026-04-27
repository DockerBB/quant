# Quant Strategy System — Claude Code Reference

## 项目概述

A股多因子量化选股与信号生成系统。

- **后端**: FastAPI + APScheduler + SQLite(元数据) + Parquet(行情/财务)
- **前端**: React 18 + Vite + Ant Design + ECharts + React Query
- **数据源**: akshare(主) + baostock(回退/历史)
- **运行环境**: Python 3.9（不要用 3.14，akshare 不支持）

## 目录结构

```
backend/          # FastAPI 后端
  main.py         # 入口，注册路由和定时任务
  app/
    api/          # API 路由 (data, factors, strategies, signals, scheduler)
    core/         # 配置(Settings), 数据库(sqlite_session), 依赖注入
    data/         # 数据层: fetcher(Akshare/Baostock), store(Parquet/SQLite), pipeline, universe, adjust, limit_rules
    factors/      # 13个量化因子 (value/momentum/quality/growth/sentiment/technical/)
    strategy/     # Scorer(加权打分), SignalGenerator(信号生成), config_loader
    scheduler/    # APScheduler 管理
    models/       # Pydantic schemas
frontend/         # React 前端
  src/pages/      # Dashboard, ScreeningResults, SignalDetail, StockAdvisor, StrategyConfig, FactorManager, DataManagement
  src/hooks/      # useStockNameMap, useStockSectorMap, useStrategyApi, useDataApi, useFactorApi
  src/utils/      # indicators.ts (RSI, MACD, Volume 计算)
scripts/          # 数据脚本
  backfill_history.py   # 单线程批量回填日线 (baostock, 批量写Parquet)
  fetch_financials.py   # 批量拉取财报 (akshare 东方财富接口, 按季度)
  init_data.py          # 首次初始化全量数据
config/
  settings.yaml   # 全局配置
  strategies/     # 6个策略 YAML 定义
    strategy_template.yaml  # 价值动量精选(原始)
    deep_value.yaml         # 深度价值
    growth_momentum.yaml    # 成长动量
    quality_first.yaml      # 质量优先
    pure_technical.yaml     # 纯技术面
    dividend_lowvol.yaml    # 红利低波
```

## 关键约定

- **Python 3.9** 运行。不用 Python 3.14（akshare 没适配）
- **前端包管理用 pnpm**，不用 npm（Node 24 的 npm 有兼容性问题）
- **数据追加不覆盖**: `write_daily()` / `write_parquet()` 会先读现有 Parquet，`pd.concat` 后 `drop_duplicates`，保留历史
- **因子不修改 Factor 基类**: 财务数据在策略运行时通过 `_enrich_with_financial()` merge 到日线 DataFrame，因子自动发现新增列
- **PE/PB 从 basic_eps/bps 计算**，不是直接取 pe/pb 列（baostock 数据没有这些列）
- **涨跌停阈值按板块**: 主板10% / 双创20% / 北交所30%（见 `limit_rules.py`）

## 数据文件（不进入 Git）

| 文件 | 大小 | 内容 | 生成方式 |
|------|------|------|----------|
| `data/parquet/daily/` | ~133MB | 日线 OHLCV，按年月分区 | `backfill_history.py` (baostock) |
| `data/financial/financial.parquet` | ~7MB | 季度财报 (ROE/毛利率/EPS等) | `fetch_financials.py` (akshare 批量) |
| `data/quant.db` | ~11MB | 股票列表/交易日历/策略/信号 | `init_data.py` |

新电脑上从旧电脑拷贝 `data/` 文件夹即可，不用重新下载。

## 启动命令

```bash
# 后端 (Python 3.9)
cd backend && python main.py          # http://127.0.0.1:8000

# 前端 (pnpm)
cd frontend && pnpm dev               # http://localhost:5173
```

## 6个策略差异

| 策略 | 风格 | 买入数 | 核心因子 |
|------|------|:------:|----------|
| 价值动量精选 | 均衡多因子 | 20 | PE+PB+ROE+MOM+RevenueYoY+GrossMargin |
| 深度价值 | 纯低估值 | 20 | PE(30%)+PB(30%)+PS(20%)+股息(20%) |
| 成长动量 | 高成长追趋势 | 15 | RevenueYoY(25%)+NetProfitYoY(25%)+MOM(20%) |
| 质量优先 | 纯基本面 | 20 | ROE(30%)+毛利率(25%)+应计利润(20%) |
| 纯技术面 | 纯K线 | 10 | MOM(35%)+换手率变化(25%)+RSI(25%) |
| 红利低波 | 高股息稳健 | 25 | 股息率(35%)+PB(20%)+应计利润(15%) |

## 数据更新

- 定时：每个交易日 15:30 自动刷新日线，17:00 自动跑策略
- 手动日线：`python scripts/backfill_history.py`
- 手动财报：`python scripts/fetch_financials.py`
- 手动策略：`POST /api/strategies/{id}/run`

## 因子计算公式

- PE_TTM = close / basic_eps
- PB = close / bps
- PS_TTM = market_cap / revenue (market_cap = close × n_income / basic_eps)
- ROE_TTM = 直接取 `roe` 列
- MOM_6M = (T-1月价格 / T-7月价格) - 1
- RSI_14 = 标准RSI公式
- Revenue_YoY / NetProfit_YoY = 直接取 `revenue_yoy` / `netprofit_yoy` 列
- GrossMargin_TTM = 直接取 `grossprofit_margin` 列
- Accruals_Ratio = (净利润 - 经营性现金流) / 总资产（当前缺少资产负债表，可能返回空）
- DYield = 需 `dv_ratio` 列（当前数据源缺失，返回空）
