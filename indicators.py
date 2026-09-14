import numpy as np, pandas as pd
def ema(s,n): return s.ewm(span=n,adjust=False).mean()
def atr(df,n=14):
    p=df.close.shift(1)
    tr=pd.concat([df.high-df.low,(df.high-p).abs(),(df.low-p).abs()],axis=1).max(axis=1)
    return tr.ewm(alpha=1/n,adjust=False).mean()
def rsi(s,n=14):
    d=s.diff(); up=d.clip(lower=0); dn=-d.clip(upper=0)
    au=up.ewm(alpha=1/n,adjust=False).mean(); ad=dn.ewm(alpha=1/n,adjust=False).mean()
    rs=au/ad.replace(0,np.nan); return 100-100/(1+rs)
def cci(df,n=20):
    tp=(df.high+df.low+df.close)/3; ma=tp.rolling(n).mean()
    md=tp.rolling(n).apply(lambda x: np.mean(np.abs(x-np.mean(x))),raw=True)
    return (tp-ma)/(0.015*md.replace(0,np.nan))
def adx(df,n=14):
    h,l,c=df.high,df.low,df.close; up=h.diff(); dn=-l.diff()
    pdm=up.where((up>dn)&(up>0),0.0); mdm=dn.where((dn>up)&(dn>0),0.0)
    p=c.shift(1); tr=pd.concat([h-l,(h-p).abs(),(l-p).abs()],axis=1).max(axis=1)
    a=tr.ewm(alpha=1/n,adjust=False).mean()
    pdi=100*pdm.ewm(alpha=1/n,adjust=False).mean()/a
    mdi=100*mdm.ewm(alpha=1/n,adjust=False).mean()/a
    dx=100*(pdi-mdi).abs()/(pdi+mdi).replace(0,np.nan)
    return dx.ewm(alpha=1/n,adjust=False).mean()
def stoch(s):
    r=rsi(s); lo=r.rolling(14).min(); hi=r.rolling(14).max()
    x=100*(r-lo)/(hi-lo).replace(0,np.nan); k=x.rolling(3).mean(); return k,k.rolling(3).mean()
def macd(s):
    m=ema(s,12)-ema(s,26); q=ema(m,9); return m,q,m-q
def supertrend(df,n=10,mult=7.8):
    a=atr(df,n); mid=(df.high+df.low)/2; up=mid+mult*a; lo=mid-mult*a
    fu=up.copy(); fl=lo.copy(); tr=pd.Series(index=df.index,dtype=int); tr.iloc[0]=1
    for i in range(1,len(df)):
        fu.iloc[i]=up.iloc[i] if up.iloc[i]<fu.iloc[i-1] or df.close.iloc[i-1]>fu.iloc[i-1] else fu.iloc[i-1]
        fl.iloc[i]=lo.iloc[i] if lo.iloc[i]>fl.iloc[i-1] or df.close.iloc[i-1]<fl.iloc[i-1] else fl.iloc[i-1]
        tr.iloc[i]=1 if (tr.iloc[i-1]==-1 and df.close.iloc[i]>fu.iloc[i]) else (-1 if (tr.iloc[i-1]==1 and df.close.iloc[i]<fl.iloc[i]) else tr.iloc[i-1])
    return tr
def add_indicators(df):
    d=df.copy(); d['ema50']=ema(d.close,50); d['ema200']=ema(d.close,200); d['adx']=adx(d)
    d['rsi']=rsi(d.close); d['cci']=cci(d); d['stoch_k'],d['stoch_d']=stoch(d.close)
    d['macd'],d['macd_signal'],d['macd_hist']=macd(d.close); d['atr']=atr(d); d['st_trend']=supertrend(d)
    return d
