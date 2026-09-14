import config as c
def cross_up(d,i):
    a=max(1,i-c.STOCH_VALID_BARS+1)
    return any(d.stoch_k.iloc[j]>d.stoch_d.iloc[j] and d.stoch_k.iloc[j-1]<=d.stoch_d.iloc[j-1] for j in range(a,i+1))
def cross_dn(d,i):
    a=max(1,i-c.STOCH_VALID_BARS+1)
    return any(d.stoch_k.iloc[j]<d.stoch_d.iloc[j] and d.stoch_k.iloc[j-1]>=d.stoch_d.iloc[j-1] for j in range(a,i+1))
def signal(d,i):
    if i<250:return None
    r=d.iloc[i]
    L=r.close>r.ema200 and r.ema50>r.ema200 and r.st_trend==1 and r.adx>c.ADX_THRESHOLD and c.LONG_RSI_MIN<r.rsi<=c.LONG_RSI_MAX and r.cci>c.LONG_CCI_MIN and cross_up(d,i) and r.stoch_d>c.LONG_STOCH_D_MIN and r.macd>r.macd_signal and r.macd_hist>0
    S=r.close<r.ema200 and r.ema50<r.ema200 and r.st_trend==-1 and r.adx>c.ADX_THRESHOLD and r.rsi<c.SHORT_RSI_MAX and r.cci<c.SHORT_CCI_MAX and cross_dn(d,i) and r.stoch_k<c.SHORT_STOCH_K_MAX
    return 'LONG' if L else ('SHORT' if S else None)
