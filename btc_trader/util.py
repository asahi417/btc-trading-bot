import logging
import os
from datetime import datetime, date, timedelta
from time import time
import pytz
import slackweb
import traceback


######################
# slack notification #
######################

class SlackAlert:

    def __init__(self,
                 log: str,
                 profit_loss: str,
                 post_interval_sec: float=30.0
                 ):
        """ Slack message post instance
        To avoid error by too frequent request, buffering message for
        `post_interval_sec` seconds and send batch.

        :param log: slack webhook url for log channel
        :param profit_loss: slack webhook url for pl channel
        """

        self.__post_interval_sec = post_interval_sec
        self.__slack_log = slackweb.Slack(url=log)
        self.__slack_pl = slackweb.Slack(url=profit_loss)
        self.__check_log = 0.0
        self.__check_pl = 0.0
        self.__msg_log = []
        self.__msg_pl = []

    def __call__(self,
                 msg: str,
                 is_pl: bool = False,
                 push_all: bool = False):
        if is_pl or push_all:
            if len(msg) > 0:
                self.__msg_pl.append(msg)
            if push_all:
                if len(self.__msg_pl) > 0 :
                    self.__slack_pl.notify(text='\n'.join(self.__msg_pl))
                    self.__check_pl = time()
                    self.__msg_pl = []
            elif self.__post_interval_sec < time() - self.__check_pl:
                if len(self.__msg_pl) > 0:
                    self.__slack_pl.notify(text='\n'.join(self.__msg_pl))
                    self.__check_pl = time()
                    self.__msg_pl = []
        if not is_pl or push_all:
            self.__msg_log.append(msg)
            if push_all:
                if len(self.__msg_log) > 0:
                    self.__slack_log.notify(text='\n'.join(self.__msg_log))
                    self.__check_log = time()
                    self.__msg_log = []
            elif self.__post_interval_sec < time() - self.__check_log:
                if len(self.__msg_log) > 0:
                    self.__slack_log.notify(text='\n'.join(self.__msg_log))
                    self.__check_log = time()
                    self.__msg_log = []


#######################
# utility for pricing #
#######################


def if_swap_point(minute_buffer: int):
    """ Calculate minutes from now to tomorrow in JST and return diff_min < minute_buffer

    :param minute_buffer:
    :return:
    """
    # get dead-line in JST
    utc_datetime_now = datetime.now(pytz.timezone('UTC'))
    jst_datetime_now = utc_datetime_now.astimezone(pytz.timezone('Asia/Tokyo'))
    # round floating point of seconds
    jst_str_now = jst_datetime_now.isoformat().split('.')[0]
    jst_datetime_now = datetime.strptime(jst_str_now, '%Y-%m-%dT%H:%M:%S')
    jst_datetime_day = jst_datetime_now.replace(hour=0, minute=0, second=0)
    jst_datetime_tomorrow = jst_datetime_day + timedelta(days=1)
    # time from now to swap-point-calculation
    diff_datetime = jst_datetime_tomorrow - jst_datetime_now
    diff_sec_int = diff_datetime.seconds
    diff_min_int = round(diff_sec_int / 60)
    # print('jst_now:', jst_datetime_now)
    # print('jst_day:', jst_datetime_day)
    # print('jst_tom:', jst_datetime_tomorrow)
    # print('jst_dif:', diff_datetime, diff_sec_int, diff_min_int)
    if diff_min_int < minute_buffer:
        return True
    else:
        return False


######################
# utility in general #
######################


def __create_log(out_file_path=None,
                 set_jst: bool=True):
    """ Logging: make logger and save at `out_file_path`.
    If `out_file_path` is None, only show in terminal and if `out_file_path` exists, delete it and make new log file

    Usage
    -------------------
    logger.info(message)
    logger.error(error)
    """

    def custom_time(*args):
        utc_dt = pytz.utc.localize(datetime.utcnow())
        my_tz = pytz.timezone('Asia/Tokyo')
        converted = utc_dt.astimezone(my_tz)
        return converted.timetuple()

    handler_stream = logging.StreamHandler()
    if out_file_path is not None:
        if os.path.exists(out_file_path):
            os.remove(out_file_path)
        handler_output = logging.FileHandler(out_file_path)
    else:
        handler_output = None

    logger = logging.getLogger(out_file_path)
    # avoid overlap logger
    if len(logger.handlers) == 0:
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter("H1, %(asctime)s %(levelname)8s %(message)s")
        handler_stream.setFormatter(formatter)
        logger.addHandler(handler_stream)
        if handler_output is not None:
            handler_output.setFormatter(formatter)
            logger.addHandler(handler_output)
    if set_jst:
        logging.Formatter.converter = custom_time
    return logger


def get_logger(out_file_path=None,
               set_jst: bool=True,
               slack_webhook_url: dict=None):
    """ return instance that is easy to get log with slack notification """
    logger = __create_log(out_file_path, set_jst)
    if slack_webhook_url is not None:
        slack = SlackAlert(**slack_webhook_url)
    else:
        slack = None

    def __log(msg: str,
              to_slack: bool = False,
              is_pl: bool = False,
              push_all: bool = False):
        logger.info(msg)
        if to_slack:
            if slack is not None:
                try:
                    slack(msg, is_pl=is_pl, push_all=push_all)
                except Exception:
                    # sometimes get error due to too frequent request to slack webhook API
                    msg = traceback.format_exc()
                    logger.info(msg)
    return __log


def utc_to_unix(t):
    """ UTC Y-M-D -> UTC unix time (ignore float second point)
    t = "2000-01-01T00:00:00.111" """
    t = t.split('.')[0]
    dt = datetime.strptime(t, '%Y-%m-%dT%H:%M:%S')
    tz = pytz.timezone('UTC')
    dt = tz.localize(dt)
    unix_time = float(dt.timestamp())
    return unix_time


#######
# WIP #
#######
#     else:  # utc time
#         dt = datetime.fromtimestamp(unix_time_stamp).isoformat()  # unix time -> date time -> str format
#     return dt.split('+')[0]


#
#
# def jst_now():
#     utc_dt_object = datetime.now(pytz.timezone('UTC'))
#     jst_dt_object = utc_dt_object.astimezone(pytz.timezone('Asia/Tokyo'))
#     jst_dt_string = jst_dt_object.isoformat()
#     jst_dt_string_remove_detail = jst_dt_string.split('+')[0]
#     return jst_dt_string_remove_detail
#
#
# def utc_to_jst(t):
#     """ UTC to JST
#     t = "2000-01-01T00:00:00"
#     """
#     dt = datetime.strptime(t, '%Y-%m-%dT%H:%M:%S')
#     dt = dt.replace(tzinfo=TZ)
#     return dt.isoformat()
#
#
# def jst_to_unix(t):
#     """JST Y-M-D -> UTC unix time
#     t = "2000-01-01T00:00:00"
#     """
#     if t is None:
#         return None
#
#     dt = datetime.strptime(t, '%Y-%m-%dT%H:%M:%S')
#     dt = dt.replace(tzinfo=TZ)
#     return int(dt.timestamp())
#
#
# def unix_to_jst(unix_time_stamp, jst=True):
#     """ UTC unix time -> JST date time e.g.) "2000-01-01T00:00:00"
#     :param int unix_time_stamp: unix time (UTC)
#     :param bool jst: if True use jst else utc
#     :return:
#     """
#     if unix_time_stamp is None:
#         return None
#
#     if jst:  # jst time
#         dt = datetime.fromtimestamp(unix_time_stamp, tz=TZ).isoformat()  # unix time -> date time -> str format
#     else:  # utc time
#         dt = datetime.fromtimestamp(unix_time_stamp).isoformat()  # unix time -> date time -> str format
#     return dt.split('+')[0]
