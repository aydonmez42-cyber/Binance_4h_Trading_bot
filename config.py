# Binance 4H Trend-Cross Trading Bot
# Baseline strategy configuration

SYMBOL = "BTCUSDT"
INTERVAL = "4h"

# Indicator parameters
EMA_FAST = 50
EMA_SLOW = 100
ADX_LENGTH = 14
ADX_THRESHOLD = 20
CCI_LENGTH = 20
CCI_LONG_THRESHOLD = 50
CCI_SHORT_THRESHOLD = -50
RSI_LENGTH = 14
RSI_LONG_THRESHOLD = 50
RSI_SHORT_THRESHOLD = 50

STOCH_RSI_RSI_LENGTH = 14
STOCH_RSI_STOCH_LENGTH = 14
STOCH_RSI_K_SMOOTH = 3
STOCH_RSI_D_SMOOTH = 3
STOCH_LONG_THRESHOLD = 20
STOCH_SHORT_THRESHOLD = 80

# Historical condition validity
CCI_VALID_BARS = 3
STOCH_VALID_BARS = 3

# Backtest execution / costs
INITIAL_CAPITAL = 10000.0
POSITION_SIZE_PCT = 1.0       # 100% of available equity per trade
LEVERAGE = 1.0
FEE_RATE = 0.0004            # 0.04% per side; change to your actual fee tier
SLIPPAGE_RATE = 0.0002       # 0.02% assumed execution slippage

# Backtest data
DATA_START = "2020-01-01"
DATA_END = None              # e.g. "2026-09-01"

# Output
TRADES_CSV = "backtest_trades.csv"
EQUITY_CSV = "backtest_equity.csv"
