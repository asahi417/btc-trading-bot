import numpy as np
import pandas as pd
import requests
import json
from . import util, db


def update_time_stamp(con, debug=True):
    logger = util.create_log() if debug else None

    def log(msg):
        if logger is not None:
            logger.info(msg)

    log('update time stamp start')
    sql = """select ticker_index, sample_period from %s""" % db.UpdateTime.__tablename__
    ticks, periods, unix_times, date_times = [], [], [], []
    for tick, p in con.engine.connect().execute(sql):
        query = """select close_unix_time from price where sample_period = %i order by close_unix_time desc limit 1"""\
                % p
        for _i in con.engine.connect().execute(query):
            update_unix_time = _i[0] + 1
        # update_unix_time = int([_i for _i in con.engine.connect().execute(query)][0])
        update_date_time = util.unix_to_jst(update_unix_time)
        ticks.append(tick)
        periods.append(p)
        unix_times.append(update_unix_time)
        date_times.append(update_date_time)
    _clm = ["ticker_index", "sample_period", "update_unix_time", "update_time"]
    df = pd.DataFrame([ticks, periods, unix_times, date_times], index=_clm).T
    df.to_sql(db.UpdateTime.__tablename__, con.engine, if_exists='replace', index=False)

    log('update time finish successfully')


def update_price(con, period: int=None, debug: bool=True):
    """ update database

    :param con: ConnectPSQL instance
    :param debug: path to save log file
    :param period: sampling period, if None, update all.
    :return:
    """

    logger = util.create_log() if debug else None

    def log(msg):
        if logger is not None:
            logger.info(msg)

    clm = ["close_unix_time", "open_price", "high_price", "low_price", "close_price", "volume"]
    logger.info('update price start')

    if period is None:
        query = """select ticker_index, sample_period, update_unix_time from %s"""\
                % db.UpdateTime.__tablename__
    else:
        query = """select ticker_index, sample_period, update_unix_time from %s where sample_period = %i""" \
                % (db.UpdateTime.__tablename__, period)
    for ticker, period, update_unix_time in con.engine.connect().execute(query):
        try:
            # get price
            re = get_ohlc_bf(after=update_unix_time, period=period)  # descending order
            if "result" not in re.keys():
                log("tick %i period %i: latest" % (ticker, period))
                continue

            re = np.array(re["result"][str(period)])[:, 0:6]  # json -> list
            # print(re[:, 0].min(), re[:, 0].max(), update_unix_time)
            prices = pd.DataFrame(re, columns=clm)
            prices["ticker_index"] = [ticker] * len(re)
            prices["sample_period"] = [period] * len(re)

            # sometimes this API return duplicated record so drop duplicate
            prices = prices.drop_duplicates(
                subset=["ticker_index", "close_unix_time", "sample_period"], keep='first', inplace=False)

            # even though set `after` parameter for crypto-watch API, this API has bugs that you get several record
            # before set time so it have to be manually filtered to get correct records
            prices = prices[prices["close_unix_time"] >= update_unix_time]
            prices = prices.sort_values(by="close_unix_time")

            if prices.shape[0] == 1:
                log("tick %i period %i: latest" % (ticker, period))
                continue

            # last records is not completely calculated so remove it
            prices[:-1].to_sql(db.Price.__tablename__, con.engine, if_exists='append', index=False)

            # delete old time record
            con.engine.connect().execute("""delete from %s where ticker_index = %i and sample_period = %i"""
                                         % (db.UpdateTime.__tablename__, ticker, period))
            # update time
            update_unix_time = int(prices["close_unix_time"].values[-1])
            update_date_time = util.unix_to_jst(update_unix_time)
            _clm = ["ticker_index", "sample_period", "update_unix_time", "update_time"]
            df = pd.DataFrame([[ticker, period, update_unix_time, update_date_time]], columns=_clm)
            df.to_sql(db.UpdateTime.__tablename__, con.engine, if_exists='append', index=False)

            # logging
            log("tick %i period %i: %i records, update time (%s)"
                % (ticker, period, prices.shape[0]-1, update_date_time))
        except Exception as err:
            log(err)
    log('update price finish successfully')


def initialize_db(con):
    con.create_tables()


def get_ohlc_bf(before=None, after=None, period=None):
    """ Get OHLC from cryptowatch

    :param int before: unix time
    :param int after: unix time
    :param int period: if None, get all periods
    :return:
    """
    url = "https://api.cryptowat.ch/markets/bitflyer/btcfxjpy/ohlc"
    if period is None:  # sampling rate (sec)
        period =\
            ["60", "180", "300", "900", "1800", "3600", "7200", "14400", "21600", "43200", "86400", "259200", "604800"]
        query = {"periods": ','.join(period)}
    else:
        query = {"periods": period}

    # if not define term -> recent 500 records
    if before is not None:
        query["before"] = before
    if after is not None:
        query["after"] = after
    response = json.loads(requests.get(url, params=query).text)
    return response


if __name__ == "__main__":

    import numpy as np
    r = get_ohlc_bf(period=60, after=1521874040)
    row = r["result"]["60"]
    length = len(row)
    print(length)
    print(np.array(row)[-0, 0])
    print(np.array(row)[-1, 0])
    for ii, i in enumerate(row):
        print(i)
        if ii == 5:
            break
