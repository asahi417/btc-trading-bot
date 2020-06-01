"""
- SFD
- swap point
https://bitflyer.com/ja-jp/commission
swap point is calculated every 00:00:00 JST.
WARNING, API employ UTC so need to be converted

-　deposit
https://note.mu/otominet/n/ndec4b9d24aad
- long, short

commission rate is supposed to be zero so, if bitflyer start asking commission rate for FX, need modify a bit.
"""


import time
import traceback
import sys
from . import model
from .. import api
from ..util import utc_to_unix, get_logger, if_swap_point
from .minimum_price import minimum_price

ASSET_LIST = ['FX_BTC_JPY']
MAX_API_REQUEST = 1
MIN_ORDER_VOLUME = 0.01


class ExecutorFX:
    """
    Instance to execute FX order
    """

    __model = None

    def __init__(self,
                 id_api: dict,
                 asset_name: str='FX_BTC_JPY',
                 max_spread: float=1000.0,
                 latency: float = 60.0,
                 loss_cut_margin: float = 10,
                 min_profit_take_margin: float = 100,
                 max_profit_take_margin: float = 500,
                 max_volume: float = 0.005,
                 min_volume: float = 0.001,
                 minute_to_expire: int=1000,
                 logger_output: str='./order_execution.log',
                 set_jst: bool = True,
                 minute_for_sp: int = 5,
                 slack_webhook_url: dict = None):

        """

        :param latency: latency of order (life time of order, second)
        :param loss_cut_margin: margin for loss cut
        :param min_profit_take_margin: margin for profit-taking
        :param max_profit_take_margin: max profit_take_price -> max(prediction, max_profit_take_price)
        :param max_volume: Max volume of one order. Order volume is decided by
                           min([max_volume, min([best_bit_size, best_ask_size])])
        :param id_api: password for bF API
        :param logger_output: pass to output logger file.
        :param minute_for_sp: Will release position `minute_for_sp` before 00:00:00 to avoid swap point
        """

        # target asset
        self.__asset_name = asset_name
        if self.__asset_name not in ASSET_LIST:
            raise ValueError('Unknown currency: %s' % self.__asset_name)

        # parameters for model
        self.__max_profit_take_margin = max_profit_take_margin
        self.__latency_model = latency
        self.__loss_cut_margin = loss_cut_margin
        self.__min_profit_take_margin = min_profit_take_margin
        self.__max_spread = max_spread
        self.__max_volume = max_volume
        self.__min_volume = min_volume
        self.__minute_to_expire = minute_to_expire
        self.__minute_for_sp = minute_for_sp

        # API connection instance
        self.api_public = api.Public(**id_api)
        self.api_order = api.Order(**id_api)

        # setup logger
        self.__log = get_logger(logger_output, set_jst=set_jst, slack_webhook_url=slack_webhook_url)
        self.__log("Trading engine configuration", to_slack=True)
        self.__log(" - asset             : %s" % asset_name, to_slack=True)
        self.__log(" - latency           : %0.2f" % latency, to_slack=True)
        self.__log(" - loss_cut_margin   : %0.2f" % loss_cut_margin, to_slack=True)
        self.__log(" - min_profit_take_margin: %0.2f" % min_profit_take_margin, to_slack=True)
        self.__log(" - max_profit_take_margin: %0.2f" % max_profit_take_margin, to_slack=True)
        self.__log(" - max_spread        : %0.2f" % max_spread, to_slack=True)
        self.__log(" - max_volume        : %0.2f" % max_volume, to_slack=True)
        self.__log(" - min_volume        : %0.2f" % min_volume, to_slack=True)
        self.__log(" - minute_to_expire  : %0.2f" % minute_to_expire, to_slack=True)
        self.__log(" - minute_for_sp     : %0.2f" % minute_for_sp, to_slack=True)

        self.__best_ask_past = 0
        self.__best_bit_past = 0
        assert self.__min_profit_take_margin < self.__max_profit_take_margin

    def safe_api_request(self,
                         api_instance,
                         api_parameter: dict=None,
                         sec_to_wait: int=5):
        """ Keep requesting till it succeed.
        :param sec_to_wait: sec to wait if api fail to request
        :return: return value from api
        """
        n = 0
        while True:
            if api_parameter is None:
                api_result = api_instance()
            else:
                api_result = api_instance(**api_parameter)
            if type(api_result) is dict and "status" in api_result.keys() and api_result["status"] == "-1":
                n += 1
                self.__log('API request get error (%s times)' % n)
                if 'error_message' in api_result.keys():
                    self.__log(' - error_message: %s' % api_result['error_message'])
                time.sleep(sec_to_wait)
            else:
                break
            if n > MAX_API_REQUEST:
                raise ValueError('API request failed')
        return api_result

    def offset_order(self, side, size):
        self.__log('offset order')
        parameter = dict(
            product_code=self.__asset_name,
            child_order_type="MARKET",
            side='SELL' if side == 'BUY' else 'BUY',
            size=size,
            time_in_force='GTC'
        )
        value = ''
        while True:
            try:
                value = self.safe_api_request(self.api_order.send_child_order, parameter)
                parameter = dict(
                    product_code=self.__asset_name,
                    child_order_acceptance_id=value['child_order_acceptance_id']
                )
                break
            except Exception:
                self.__log(str(value))
                time.sleep(10)

        while True:
            # keep 10 sec interval to avoid 'Over API limit per minute' error
            time.sleep(10)
            value = self.safe_api_request(self.api_order.get_child_orders, parameter)
            order_info_child = value[0]
            # self.__log(' - get_child_orders: %s' % str(order_info_child))
            if order_info_child['child_order_state'] == 'COMPLETED':
                self.__log(' - offset order is completed')
                break

    def cleanup_positions(self):
        self.__log('CLEAN UP ALL POSITION')
        # cancel all orders (in case something went wrong and some orders are still remained)
        active_parent_orders = self.safe_api_request(self.api_order.get_parent_orders,
                                                     dict(product_code=self.__asset_name, parent_order_state="ACTIVE"))
        if type(active_parent_orders) is list:
            for i in active_parent_orders:
                self.safe_api_request(self.api_order.cancel_parent_order,
                                      dict(product_code=self.__asset_name, parent_order_id=i['parent_order_id']))
        self.safe_api_request(self.api_order.cancel_all_child_orders, dict(product_code=self.__asset_name))

        # get position
        value = self.safe_api_request(self.api_order.get_positions, dict(product_code=self.__asset_name))
        if type(value) is list:
            self.__log(' - found positions %i' % len(value), to_slack=True)
            self.__log(str(value))
            flg = False
            for n, _value in enumerate(value):
                self.__log('   - offset orders: %i' % n)
                if _value['size'] < MIN_ORDER_VOLUME:
                    self.__log('     - ignore due to small volume')
                else:
                    self.offset_order(_value['side'], _value['size'])
                    flg = True
            return flg
        else:
            self.__log(' - no positions', to_slack=True)
            return False

    def __swap_point(self):
        """ Module to avoid swap point. Swap point will be calculated every 00:00:00 JST so at that time, net position
        need to be zero. This module order opposite order to make the net position zero.
        """
        if if_swap_point(self.__minute_for_sp):
            self.__log('preparing to avoid swap point', to_slack=True)
            self.cleanup_positions()
            value = self.safe_api_request(self.api_order.get_collateral)
            self.__log(' - sleep until tomorrow. good night :)', to_slack=True)
            self.__log("   - collateral         : %0.5f" % value["collateral"])
            self.__log("   - require_collateral : %0.5f" % value["require_collateral"])
            self.__log("   - open_position_pnl  : %0.5f" % value["open_position_pnl"])
            time.sleep(self.__minute_for_sp * 60)

    def __current_market(self, health_check: bool = True):
        """ module to get current market state """
        ticker = self.safe_api_request(self.api_public.ticker, dict(product_code=self.__asset_name))
        if health_check:
            health = self.safe_api_request(self.api_public.get_board_state, dict(product_code=self.__asset_name))
        else:
            health = None
        try:
            timestamp = utc_to_unix(ticker['timestamp'])  # API's timestamp is UTC based
            best_bid = int(ticker['best_bid'])
            best_ask = int(ticker['best_ask'])
            best_bid_size = float(ticker['best_bid_size'])
            best_ask_size = float(ticker['best_ask_size'])
            spread = best_ask - best_bid
            self.__log(' - api time   : %s' % ticker['timestamp'], to_slack=True)
            self.__log(' - ask (size) : %0.2f (%0.2f)' % (best_ask, best_ask_size), to_slack=True)
            self.__log('    * %0.4f' % (best_ask - self.__best_ask_past), to_slack=True)
            self.__log(' - bit (size) : %0.2f (%0.2f)' % (best_bid, best_bid_size), to_slack=True)
            self.__log('    * %0.4f' % (best_bid - self.__best_bit_past), to_slack=True)
            self.__log(' - spread     : %0.2f' % spread, to_slack=True)
            if health_check:
                self.__log(' - exchange   : health (%s), state (%s)' % (health['health'], health['state']), to_slack=True)
            self.__best_ask_past = best_ask
            self.__best_bit_past = best_bid

            # If time-delay is more than latency, skip order and reset model buffer
            if time.time() - timestamp > self.__latency_model * 2:
                self.__model.reset_buffer()
                self.__log('ticker API has delayed: %0.2f sec' % (time.time() - timestamp), to_slack=True)
                self.__log(' - reset model buffer', to_slack=True)
            if health_check:
                return best_bid, best_ask, best_bid_size, best_ask_size, spread, health['health'], health['state']
            else:
                return best_bid, best_ask, best_bid_size, best_ask_size, spread, None, None
        except KeyError:
            self.__log('unknown API error')
            self.__log('health: %s' % str(ticker))
            self.__log('ticker: %s' % str(ticker))
            return None

    def __tracking_active_order(self,
                                acceptance_order_id,
                                current_asset_jpy,
                                initial_asset_jpy,
                                order_timestamp):
        """Module to track active order by `get_child_orders` API return, which consists of ANCHOR and OCO order.
        Basically, ANCHOR is limit and OCO consists of limit profit-take (PT) order and market loss-cut (LC) orders,
        and both of PT and LC order have their trigger, so once the market price reach the trigger price, one of
        them will be ordered and the other will be cancelled. The `get_child_orders` API will return information of
        orders, which have been ordered, so if OCO has not been triggered, API return only include ANCHOR order.
        Thus, with [`value` = `get_child_orders` API return],

        A) `value` has one info means one of following cases
            - `anchor` has been executed and the market price dose not reach any triggers of OCO (OCO is not ordered)
            - `anchor` has been ordered (not executed), so COC is not ordered regardless of market price
        B) `value` has two info means `anchor` has been executed and COC has been ordered

        Then, it should be ensured that the entire orders (ANCHOR and OCO) do not end up with holding any positions. If
        there are any positions after all orders has finished, opposite position order should be executed so that the
        NET position becomes zero. The cases of opposite position order is needed are as below.

        A) `value` has one info with ACTIVE status -> ANCHOR is not executed yet
        B) `value` has one info with COMPLETED status -> ANCHOR has been executed, and OCO is not triggered
        C) `value` has two info and OCO with ACTIVE status -> ANCHOR has been executed, and OCO has been ordered
        D) `value` has two info and OCO with COMPLETED status -> ANCHOR and OCO has been executed

        E) `value` has no info -> ANCHOR has been expired
        F) `value` has two info and OCO with EXPIRED status -> ANCHOR has been executed, and OCO has been expired
        G) `value` has one info with COMPLETED status but it's after expired_date
            -> ANCHOR has been executed, but somehow OCO has been rejected or failed.
        J) the other cases

        As next Action:
          A, B, C -> wait
          D, E -> finish
          F, G, J -> end up with positions, so execute opposite order

        K) Sometimes OCO goes mad (especially when exchange is very busy), so that it execute PT but also LC. In
        this case, net position eventually not become zero, so need to order opposite order


         Return
        -------------------------------
        True if orders are still active else False
        """

        def profit_loss():
            """ When calculate PL, net position is supposed to be zero but due to unstable crappy bitflyer API,
             sometimes it dose not zero. In this case, firstly execute offset order and then calculate PL """

            self.__log('PROFIT LOSS', is_pl=True, to_slack=True)
            __value = self.safe_api_request(self.api_order.get_collateral)
            pl_total = __value["collateral"] - initial_asset_jpy
            pl_one_step = __value["collateral"] - current_asset_jpy
            self.__log(' - PL total           : %0.3f' % pl_total, is_pl=True, to_slack=True)
            self.__log(' - PL one step        : %0.3f' % pl_one_step, is_pl=True, to_slack=True)
            self.__log(" - collateral         : %0.5f" % __value["collateral"], is_pl=True, to_slack=True)
            self.__log(" - require_collateral : %0.5f" % __value["require_collateral"], is_pl=True, to_slack=True)
            self.__log(" - open_position_pnl  : %0.5f" % __value["open_position_pnl"], is_pl=True, to_slack=True)
            __current_asset = __value["collateral"]
            return __current_asset

        self.__log('TRACKING ACTIVE ORDERS', to_slack=True)
        value = self.safe_api_request(self.api_order.get_parent_order,
                                      dict(parent_order_acceptance_id=acceptance_order_id))
        if 'parent_order_id' not in value:
            self.__log(' - unexpected API return: %s' % str(value), to_slack=True)
            return True, current_asset_jpy

        parent_order_id = value['parent_order_id']

        self.__log(' - get_parent_order: parent_order_acceptance_id (%s)' % acceptance_order_id)
        parameter = dict(product_code=self.__asset_name,
                         count=10,
                         parent_order_id=parent_order_id)
        child_order = self.safe_api_request(self.api_order.get_child_orders, parameter)
        self.__log(' - get_child_orders: parent_order_id (%s), order number (%i)' % (parent_order_id, len(child_order)))

        if type(child_order) is dict:  # case (E) or (J)
            parent_orders = self.safe_api_request(self.api_order.get_parent_orders,
                                                  dict(product_code=self.__asset_name, count=1))
            target_order = [_p for _p in parent_orders if _p['parent_order_id'] == parent_order_id]
            if len(target_order) == 0:
                raise ValueError('invalid parent_order_id: %s'
                                 'get_child_orders API return no result: %s'
                                 'get_parent_orders API return no result: %s'
                                 % (parent_order_id, str(child_order), str(parent_orders)))
            if target_order[0]['parent_order_state'] == 'EXPIRED':
                # case (E)
                self.__log(' - status: ANCHOR [expired]', to_slack=True)
                if_any_order = self.cleanup_positions()
                if if_any_order:
                    current_asset_jpy = profit_loss()
                return False, current_asset_jpy
            elif target_order[0]['parent_order_state'] == 'ACTIVE':
                # case (A)
                if time.time() - order_timestamp < self.__minute_to_expire * 60:
                    self.__log(' - status: ANCHOR [active] -> keep tracking', to_slack=True)
                    return True, current_asset_jpy
                else:
                    self.__log(' - status: ANCHOR [active] -> offset orders (expired)', to_slack=True)
            else:
                # case (J)
                self.__log(' - status: unclear state -> offset orders', to_slack=True)

        else:  # case (A), (B), (C), (D), (F) or (G)
            state = dict()
            total_commission = 0
            expire_date_unix = None
            for n, child_dict in enumerate(child_order):
                state[child_dict['side']] = child_dict['child_order_state']
                total_commission += float(child_dict['total_commission'])
                expire_date_unix = utc_to_unix(child_dict['expire_date'])  # API's timestamp is UTC based

            # case (A)
            if len(state.keys()) == 1 and list(state.values())[0] == 'ACTIVE':

                if time.time() - order_timestamp < self.__minute_to_expire * 60:
                    self.__log(' - status: ANCHOR [active] -> keep tracking', to_slack=True)
                    return True, current_asset_jpy
                else:
                    self.__log(' - status: ANCHOR [active] -> offset orders (expired)', to_slack=True)

            # case (B) or (J)
            elif len(state.keys()) == 1 and list(state.values())[0] == 'COMPLETED':
                if time.time() < expire_date_unix:
                    # case (B)
                    self.__log(' - status: ANCHOR [completed], OCO [not triggered] -> keep tracking',
                               to_slack=True)
                    if time.time() - order_timestamp < self.__minute_to_expire * 60:
                        self.__log(' - status: ANCHOR [completed], OCO [not triggered] -> keep tracking',
                                   to_slack=True)
                        return True, current_asset_jpy
                    else:
                        self.__log(' - status: ANCHOR [completed], OCO [not triggered] '
                                   '-> offset orders (expired)', to_slack=True)
                else:
                    # case (J)
                    self.__log(' - status: ANCHOR [completed], OCO [rejected] -> offset orders',
                               to_slack=True)

            # case (C)
            elif len(state.keys()) == 2 and 'ACTIVE' in list(state.values()):
                if time.time() - order_timestamp < self.__minute_to_expire * 60:
                    self.__log(' - status: ANCHOR [completed], OCO [active] -> keep tracking',
                               to_slack=True)
                    return True, current_asset_jpy
                else:
                    self.__log(' - status: ANCHOR [completed], OCO [active] '
                               '-> offset orders (expired)', to_slack=True)

            # case (D)
            elif len(state.keys()) == 2 and len([v for v in state.values() if v != 'COMPLETED']) == 0:
                self.__log(' - status: ANCHOR [completed], OCO [completed] (commission: %0.8f)'
                           % total_commission, to_slack=True)
                self.cleanup_positions()
                current_asset_jpy = profit_loss()
                return False, current_asset_jpy

            # case (F) or (G)
            elif len(state.keys()) == 2 and 'EXPIRED' in list(state.values()):
                # case (F)
                self.__log(' - status: ANCHOR [completed], OCO [expired] -> offset orders',
                           to_slack=True)
            else:
                # case (G)
                self.__log(' - status: unclear state (%s) -> offset orders' % str(state), to_slack=True)

        if_any_order = self.cleanup_positions()
        if if_any_order:
            current_asset_jpy = profit_loss()

        return False, current_asset_jpy

    def __new_order(self,
                    pred_ask,
                    trend,
                    best_ask,
                    best_bid,
                    best_ask_size,
                    best_bid_size,
                    spread,
                    commission_rate,
                    health_health,
                    health_state):
        ##################
        # Skip Condition #
        ##################
        # skip if bF is dead
        if health_health is not None and health_state is not None:
            if health_health != 'NORMAL' or health_state != 'RUNNING':
                self.__log(' - skip order: unstable server, health (%s), state (%s)' % (health_health, health_state),
                           to_slack=True)
                return False, None, None

        # skip if buffer is not enough
        if pred_ask is None:
            self.__log(' - skip order: for model buffer', to_slack=True)
            return False, None, None

        # skip if market has trend
        if trend:
            self.__log(' - skip order: detect market trend', to_slack=True)
            return False, None, None

        # skip if spread is too large
        if spread > self.__max_spread:
            self.__log(' - skip order: too large spread %0.1f' % spread, to_slack=True)
            return False, None, None

        # skip if min(best_bid, ask_size) is too small
        volume = min(best_ask_size, best_bid_size)
        if volume < self.__min_volume:
            self.__log(' - skip order: too small volume %0.6f' % volume, to_slack=True)
            return False, None, None

        # skip if current best_ask is larger than prediction or margin is too small.
        volume = min(self.__max_volume, volume)
        volume = round(volume*10**3)*10**-3
        min_price_for_profit, _ = minimum_price(commission=commission_rate, volume=volume, price=best_ask)
        min_profit_take_margin = min_price_for_profit - best_ask + self.__min_profit_take_margin
        predicted_margin = min(self.__max_profit_take_margin, pred_ask - best_ask)

        if predicted_margin < min_profit_take_margin:
            self.__log(' - skip order: predicted margin < min profit margin: %0.2f < %0.2f'
                       % (predicted_margin, min_profit_take_margin), to_slack=True)
            return False, None, None

        execute_price = predicted_margin + best_ask

        #################
        # Execute Order #
        #################
        loss_cut_price = best_bid - spread - self.__loss_cut_margin
        self.__log('NEW ORDER', to_slack=True)
        self.__log(' - volume     : %0.4f' % volume, to_slack=True)
        self.__log(' - price_buy  : %0.2f' % best_ask, to_slack=True)
        self.__log(' - price_sell : (%0.2f, %0.2f)' % (loss_cut_price, execute_price), to_slack=True)

        parameter = dict(
            order_method="IFDOCO",
            minute_to_expire=self.__minute_to_expire,
            time_in_force="GTC",
            parameters=[
                {
                    "product_code": self.__asset_name,
                    "condition_type": "LIMIT",
                    "side": "BUY",
                    "price": best_ask,
                    "size": volume
                },
                {
                    "product_code": self.__asset_name,
                    "condition_type": 'LIMIT',
                    "side": "SELL",
                    "price": execute_price,
                    "size": volume
                },
                {
                    "product_code": self.__asset_name,
                    "condition_type": "STOP",
                    "side": "SELL",
                    "trigger_price": loss_cut_price,
                    "size": volume
                }
            ]
        )
        order_info = self.safe_api_request(self.api_order.send_parent_order, parameter)
        try:
            acceptance_order_id = order_info['parent_order_acceptance_id']
            self.__log(' - parent_order_acceptance_id: %s' % acceptance_order_id, to_slack=True)
            timestamp = time.time()
            return True, acceptance_order_id, timestamp
        except Exception:
            msg = traceback.format_exc()
            self.__log('- order failed', to_slack=True)
            self.__log(msg, to_slack=True)
            self.__log('return of send_parent_order API: %s' % str(order_info), to_slack=True)
            return False, None, None

    def run(self):
        value = self.safe_api_request(self.api_order.get_collateral)
        try:
            initial_asset_jpy = value["collateral"]
        except KeyError:
            self.__log('unknown API error')
            self.__log('get_collateral: %s' % str(value))
            raise KeyError
        msg = ''

        try:
            try:
                self.__run()
            except KeyboardInterrupt:
                msg = 'Finish trading: KeyboardInterrupt'
        except Exception:
            msg = traceback.format_exc()

        self.__log(msg, push_all=True, to_slack=True)
        self.cleanup_positions()
        # PL calculation
        self.__log('Trading report', is_pl=True, to_slack=True)
        __value = self.safe_api_request(self.api_order.get_collateral)
        try:
            pl_total = __value["collateral"] - initial_asset_jpy
            self.__log(' - PL total           : %0.3f' % pl_total, is_pl=True, to_slack=True)
            self.__log(" - collateral         : %0.5f" % __value["collateral"], is_pl=True, to_slack=True)
            self.__log(" - require_collateral : %0.5f" % __value["require_collateral"], is_pl=True, to_slack=True)
            self.__log(" - open_position_pnl  : %0.5f" % __value["open_position_pnl"], is_pl=True, to_slack=True)
        except KeyError:
            self.__log('unknown API error')
            self.__log('get_collateral: %s' % str(__value))

        self.__log("Exit", is_pl=True, to_slack=True, push_all=True)
        sys.exit()

    def __run(self):
        if self.__model is None:
            raise ValueError('Error: set model before run executor.')

        param_prod_code = dict(product_code=self.__asset_name)
        value = self.safe_api_request(self.api_order.get_trading_commission, param_prod_code)
        commission_rate = value['commission_rate']
        value = self.safe_api_request(self.api_order.get_collateral)

        self.__log("Account configuration", is_pl=True, to_slack=True)
        self.__log(" - commission_rate    : %0.5f" % commission_rate, is_pl=True, to_slack=True)
        self.__log(" - collateral         : %0.5f" % value["collateral"], is_pl=True, to_slack=True)
        self.__log(" - require_collateral : %0.5f" % value["require_collateral"], is_pl=True, to_slack=True)
        self.__log(" - open_position_pnl  : %0.5f" % value["open_position_pnl"], is_pl=True, to_slack=True)

        initial_asset_jpy = value["collateral"]
        current_asset_jpy = value["collateral"]

        if value["collateral"] == 0:
            raise ValueError("Error: invalid initial account condition")
        if commission_rate != 0.0:
            raise ValueError("Error: commission rate is not zero ")

        # information of active order
        if_holding_position = False
        order_timestamp = 0
        predicted_time = 0
        acceptance_order_id = None
        flag_health_check = 0
        flag_track_order = 0

        while True:
            self.__log("#########################")
            self.__log("##### START PROCESS #####", to_slack=True)
            self.__log("#########################")
            # wait order to keep latency
            waiting_time = max(0, self.__latency_model - (time.time() - predicted_time))
            self.__log('RUN TRADER: sleep %0.3f sec to keep latency' % waiting_time)
            time.sleep(waiting_time)
            # swap point
            self.__swap_point()
            # current market
            if flag_health_check >= 10:
                flag_health_check = 0
                data = self.__current_market(True)
            else:
                flag_health_check += 1
                data = self.__current_market(False)

            if data is None:
                self.__log('sleep for a minute')
                time.sleep(60.0)
                continue

            best_bid, best_ask, best_bid_size, best_ask_size, spread, health_health, health_state = data
            # prediction: model need update buffer so conduct prediction regardless of order
            pred_ask, trend = self.__model.predict(best_ask)
            predicted_time = time.time()
            if pred_ask is not None:
                pred_ask = round(pred_ask)
                self.__log(" - predict ask (trend): %0.2f (%s)" % (pred_ask, str(trend)), to_slack=True)

            # track order or order new one
            if if_holding_position:
                if flag_track_order >= 5:
                    flag_track_order = 0
                    # track active order
                    if_holding_position, current_asset_jpy = self.__tracking_active_order(
                        acceptance_order_id,
                        order_timestamp=order_timestamp,
                        initial_asset_jpy=initial_asset_jpy,
                        current_asset_jpy=current_asset_jpy
                    )
                else:
                    flag_track_order += 1

            else:
                # make new order
                if_holding_position, acceptance_order_id, order_timestamp = self.__new_order(
                    pred_ask,
                    trend,
                    best_ask,
                    best_bid,
                    best_ask_size,
                    best_bid_size,
                    spread,
                    commission_rate,
                    health_health,
                    health_state
                )

    def set_model(self,
                  model_name: str,
                  model_parameter: dict=None):

        if model_name == 'ma':
            if model_parameter is None:
                self.__model = model.MovingAverage()
            else:
                self.__model = model.MovingAverage(**model_parameter)
        else:
            raise ValueError('unknown model name: %s' % model_parameter)
