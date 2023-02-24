# import os

from flask import Flask, render_template  # Flask 라이브러리 선언
app = Flask(__name__)

# import threading

import pandas as pd
pd.set_option('display.max_columns', None) ## 모든 열을 출력한다.

from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import telegram
from telegram.ext import Updater
from telegram.ext import CommandHandler

import ccxt

exchange = ccxt.binance()
# load all markets from the exchange
tickers = exchange.fetch_tickers()
count = 0
USDT_ticker = []
for i, ticker in enumerate(tickers):
    if ticker.find('/USDT') > -1:
        USDT_ticker.append(ticker)
        count += 1

# BOT_TOKEN = '5955241741:AAG3R-Pp7qi6IccU7YXirfJYIe0oE__E4MU'
# MY_ID ='538115311'
# CHAT_ID = '-1001778308558'

BOT_TOKEN = '6056998714:AAHa9RfCHGMf68cqD9hNSvO1VkQS0gp6lhY'
MY_ID = '5892267509'
CHAT_ID = '-1001874274156'



bot = telegram.Bot(BOT_TOKEN)
sched = BackgroundScheduler()
bot.send_message(chat_id=MY_ID, text='안녕하세요!! \n 작업을 시작하고플땐 /hstart \n 작업을 중지하고플땐 /stop \n 메세지를 전송해주세요.😄')
# pd.set_option('display.float_format', lambda x: '%.1f' %x)
# df = pyupbit.get_ohlcv("KRW-BTC")
# df['close'].ewm(span=9, adjust=False).mean()
#
# print(df)#지수이동평균선

def getJS(interval):
    result_u = []
    result_l = []
    print('get_JS')
    for i in USDT_ticker:

        day = exchange.fetch_ohlcv(i,interval, limit=1000)
        df = pd.DataFrame(day) #데이터프레임으로 만든다
        df.columns = (['Date','Open','High','Low','Close','Volume']) #컬럼 지정
        def parse_dates(ts):
            return datetime.fromtimestamp(ts/1000.0) #타임스탬프를 시간형식으로 전환
        df['Date'] = df['Date'].apply(parse_dates) #Date컬럼에 적용

        # df = get_df_binance(i,'15m')
        # df = exchange.fetch_ohlcv(i,'15m',limit=1) #값이 리스트로 반환된다
        w= 20 # 기준 이동평균일
        k= 2 # 기준 상수

        # 중심선 (MBB) : n일 이동평균선
        df["mbb"]=df["Close"].rolling(w).mean()
        df["MA20_std"]=df["Close"].rolling(w).std()

        #상한선 (UBB) : 중심선 + (표준편차 × K)
        #하한선 (LBB) : 중심선 - (표준편차 × K)
        df["ubb"]=df.apply(lambda x: x["mbb"]+k*x["MA20_std"],1)
        df["lbb"]=df.apply(lambda x: x["mbb"]-k*x["MA20_std"],1)

        df['ticker'] = i.replace('/USDT', '')

        for j in df:
            # 상승, 하락분을 알기위해 현재 종가에서 전일 종가를 빼서 데이터프레임에 추가하겠습니다.
            RSI_n=14
            df["upAndDown"]=[df.loc[j,"Close"]-df.loc[j-1,"Close"] if j>0 else 0 for j in range(len(df))]
            # j가 0일때는 전일값이 없어서 제외함, j는 데이터프레임의 index값

            # U(up): n일 동안의 종가 상승 분
            df["RSI_U"]=df["upAndDown"].apply(lambda x: x if x>0 else 0)

            # D(down): n일 동안의 종가 하락 분 --> 음수를 양수로 바꿔줌
            df["RSI_D"]=df["upAndDown"].apply(lambda x: x * (-1) if x<0 else 0)

            # AU(average ups): U값의 평균
            df["RSI_AU"]=df["RSI_U"].rolling(RSI_n).mean()

            # DU(average downs): D값의 평균
            df["RSI_AD"]=df["RSI_D"].rolling(RSI_n).mean()
            # if df["RSI_AU"].notna and df["RSI_AD"].notna:
            try:
                df["RSI"] = df.apply(lambda x:x["RSI_AU"]/(x["RSI_AU"]+ x["RSI_AD"]) * 100,1)
            except ZeroDivisionError:
                df["RSI"] = 0

        arr = df.iloc[-1]
        # arr['ticker_rename'] = arr['ticker'].replace('/USDT', '')

        #종가가 상한선 이상일때 & RSI값이 70이상일때
        if arr.Close > arr.ubb and arr.RSI >= 70:
            result_u.append(arr['ticker'])
        if arr.Close < arr.lbb and arr.RSI <= 30:
            result_l.append(arr['ticker'])

    print(result_u)
    print(result_l)
    return [result_u, result_l]

def sendMessage(bot, msg):
    global CHAT_ID
    # for i in CHAT_ID:
    bot.send_message(chat_id=CHAT_ID, text=msg)

# 텔레그램 메시지 전송 함수
def send_links():
    global bot
    # 각 종목별 5분봉
    print(datetime.now())
    print('send_links')

    five_ticker = getJS('5m')
    print("5분봉:", five_ticker)
    sendMessage(bot, '5분봉=============')
    sendMessage(bot, "상: "+str(five_ticker[0]))
    sendMessage(bot, "하: "+str(five_ticker[1]))

    fifteen_ticker = getJS('15m')
    print("15분봉:", fifteen_ticker)
    sendMessage(bot, '15분봉=============')
    sendMessage(bot, "상: "+str(fifteen_ticker[0]))
    sendMessage(bot, "하: "+str(fifteen_ticker[1]))

    one_ticker = getJS('1h')
    print("60분봉:", one_ticker)
    sendMessage(bot, '60분봉=============')
    sendMessage(bot, "상: "+str(one_ticker[0]))
    sendMessage(bot, "하: "+str(one_ticker[1]))

    print(datetime.now())

def start(update, context):
    print('====scheduler start====')
    print(update.effective_chat.id)
    global sched

    context.bot.send_message(chat_id=update.effective_chat.id, text="작업을 시작합니다.\n 👉  scheduler start!")

    send_links()

    sched.add_job(send_links, 'interval', seconds=180, id='send')

    sched.start()


def stop(update, context):
    global sched
    context.bot.send_message(chat_id=update.effective_chat.id, text="작업을 중지합니다.\n ✊ scheduler stop!")
    # sched.remove_job(job_id='send')
    sched.remove_all_jobs()


def clear(update, context):
    global bot
    bot.stopPoll()

# def botMain():
updater = Updater(token=BOT_TOKEN, use_context=True)
dispatcher = updater.dispatcher

dispatcher.add_handler(CommandHandler('hstart', start))
dispatcher.add_handler(CommandHandler('stop', stop))

updater.start_polling()

def main():
    print('botMain')


    # updater.start_webhook(listen="0.0.0.0",
    #                       port=int(os.environ.get('PORT', 5000)),
    #                       url_path=BOT_TOKEN,
    #                       webhook_url=+ BOT_TOKEN
    #                       )
    # updater.idle()

# @app.route('/')
# def index():
#     print('main')
#     # bot.send_message(chat_id=MY_ID, text='안녕하세요!! \n 작업을 시작하고플땐 /hstart \n 작업을 중지하고플땐 /stop \n 메세지를 전송해주세요.😄')
#     return render_template('index.html')

# class FlaskThread(threading.Thread):
#     def run(self) -> None:
#         app.run(threaded=True)
# class TelegramThread(threading.Thread):
#     def run(self) -> None:
#         botMain()

if __name__ =='__main__':
    main()
#     # flask_thread = FlaskThread()
#     # flask_thread.start()
#
#     botMain()
#     app.run()
