from flask import Flask, jsonify
app=Flask(__name__)
@app.get('/health')
def health(): return jsonify(status='ok',service='MULTI-COIN SCANNER BACKTEST V2',real_orders=False)
if __name__=='__main__':
    import os
    app.run(host='0.0.0.0',port=int(os.environ.get('PORT','8080')))
