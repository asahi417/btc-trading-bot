# TODO:Refactor


import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import mpl_finance as mpf
import matplotlib.dates as mdates
from matplotlib import ticker
from .util.util import unix_time, date_time


def candle_ohlc(con, period, start=None, end=None, limit=None, ma=[5, 10], volume=False, adjust=False,
                figsize=(10, 8)):

    query = "select * from price where sample_period = %i" % period
    if start is not None and type(start) == str:
        query += " and close_unix_time > %i" % unix_time(start)
    if end is not None and type(end) == str:
        query += " and close_unix_time < %i" % unix_time(end)
    query += " order by close_unix_time desc"
    if limit is not None and type(limit) == int:
        query += " limit %i" % limit
    price_volume = []
    date = []

    for i in con.engine.connect().execute(query):
        date.append(date_time(i[1]))
        price_volume.append(list(i[3:8]))

    ohlc = pd.DataFrame(price_volume[::-1], columns=["open", "high", "low", "close", "volume"], index=date[::-1])
    ohlc = ohlc[ohlc["low"] != 0]
    fig, ax = _candle(ohlc, ma, volume, figsize)
    if adjust and ma is not None:
        plt.xlim([np.max(ma) - 2, ohlc.shape[0] - 1])
    else:
        # plt.xlim([-1, ohlc.shape[0] - 1])
        pass
    return (fig, ax), query


def _candle(ohlc, ma=None, volume=False, figsize=(10, 8)):
    # plt.rcParams['font.family'] = 'Times New Roman'
    plt.rcParams['font.size'] = 20

    fig, ax = plt.subplots(figsize=figsize)

    # candle plot
    width = 0.8
    mpf.candlestick2_ohlc(ax, opens=ohlc.open.values, closes=ohlc.close.values,
                          lows=ohlc.low.values, highs=ohlc.high.values,
                          width=width, colorup='r', colordown='b')

    # moving average
    if ma is not None and type(ma) == list:
        for _ma in ma:
            sma = ohlc.close.rolling(_ma).mean()
            v_stack = np.vstack((range(len(sma)), sma.values.T)).T
            ax.plot(v_stack[:, 0], v_stack[:, 1], label="ma(%i)" % _ma)
            plt.legend(loc="upper left")

    # volume
    if volume:
        ax2 = ax.twinx()  # connect two axis
        ax2.plot(ohlc.volume.values, label="volume", marker=".", linestyle=":", color="black")
        plt.legend(loc="upper right")

    # x axis -> time
    xdate = ohlc.index
    ax.xaxis.set_major_locator(ticker.MaxNLocator(10))

    ax.grid(True)

    def mydate(x, pos):
        try:
            return xdate[int(x)]
        except IndexError:
            return ''

    ax.xaxis.set_major_formatter(ticker.FuncFormatter(mydate))
    ax.format_xdata = mdates.DateFormatter('%Y-%m-%d')
    fig.autofmt_xdate()
    fig.tight_layout()
    return fig, ax
