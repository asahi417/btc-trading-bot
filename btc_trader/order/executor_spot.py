"""
WARNING:
    This executor is outdated and might not work. We are focusing on fx trading and will not touch this executor
    anymore.

Deposit for IFDOCO order:
    For spot trading, if BTC in your account is less than volume to order, buy order will be fine but sell order will be rejected
    due to insufficient amount of BTC asset. Basically, when you execute sell order, your account need more than the amount
    to sell and it's same as special orders. So, before IFDOCO order, it should be ensured that your account has at
    least maximum trading volume. For instance, if you set max volume as 0.001, you have to have 0.001 BTC on your account.
"""

import time
from . import model
from .. import api
from ..util import utc_to_unix
from .minimum_price import minimum_price


class ExecutorSpot:
    """
    Instance to execute spot order
    """

    __model = None

    def __init__(self,
                 id_api: dict,
                 asset_name: str='BTC_JPY',
                 max_spread: float=1000.0,
                 latency: float = 60.0,
                 latency_model: float = 60.0,
                 loss_cut_margin: float = 10,
                 profit_take_margin: float = 100,
                 max_volume: float = 0.005,
                 min_volume: float = 0.001,
                 minute_to_expire: int=1000,
                 logger_output: str='./order_execution.log'
                 ):

        """

        :param latency: latency of order (life time of order, second)
        :param loss_cut_margin: margin for loss cut
        :param profit_take_margin: margin for profit-taking
        :param max_volume: Max volume of one order. Order volume is decided by
                           min([max_volume, min([best_bit_size, best_ask_size])])
        :param id_api: password for bF API
        :param logger_output: pass to output logger file.
        """
        # target asset
        self.__asset_name = asset_name
        if 'BTC' in self.__asset_name:
            self.__crypto = 'BTC'
        elif 'ETH' in self.__asset_name:
            self.__crypto = 'ETH'
        else:
            raise ValueError('Unknown currency: %s' % self.__asset_name)

        # parameters for model
        self.__latency = latency
        self.__latency_model = latency_model
        self.__loss_cut_margin = loss_cut_margin
        self.__profit_take_margin = profit_take_margin
        self.__max_spread = max_spread
        self.__max_volume = max_volume
        self.__min_volume = min_volume
        self.__minute_to_expire = minute_to_expire

        # API connection instance
        self.api_public = api.Public(**id_api)
        self.api_order = api.Order(**id_api)

        # setup logger
        logger = create_log(logger_output)
        self.__log = logger.info
        self.__log('setup executor')

    def api_error(self, api_result):
        if type(api_result) is dict and "status" in api_result.keys() and api_result["status"] == "error":
            self.__log('API request get error: %s' % str(api_result["msg"]))
            self.__log('  will sleep 60 sec')
            time.sleep(60)
            return True
        else:
            return False

    def get_jpy_btc(self):
        while True:
            balance = self.api_order.get_balance()
            if not self.api_error(balance):
                break

        jpy_amount = float([b['amount'] for b in balance if b['currency_code'] == 'JPY'][0])
        btc_amount = float([b['amount'] for b in balance if b['currency_code'] == self.__crypto][0])
        return jpy_amount, btc_amount

    def error_insufficient_btc(self, btc_amount):
        """ If btc in your account is less than volume to order, buy order will be fine but sell order will be rejected
        due to insufficient btc asset. Basically, when you execute sell order, your account need more than the amount
        to sell and it's same as special order. So, before IFDOCO order, it should be ensured that your account has at
        least maximum trading volume.
        """
        if btc_amount < self.__max_volume:
            raise ValueError('Kill the executor due to BTC insufficiency. (current: %0.6f < max volume: %0.6f)'
                             % (btc_amount, self.__max_volume))

    def run(self):  # long only strategy
        if self.__model is None:
            raise ValueError('set model before run executor.')

        self.__log('System start trading (long only strategy). Good luck :)')
        commission_rate = self.api_order.get_trading_commission(product_code=self.__asset_name)
        commission_rate = commission_rate['commission_rate']
        self.__log(' - commission_rate: %0.5f' % commission_rate)
        initial_asset, initial_asset_btc = self.get_jpy_btc()
        current_asset, current_asset_btc = self.get_jpy_btc()
        self.__log(' - initial asset  : %0.3f JPY, %0.6f %s' % (initial_asset, initial_asset_btc, self.__crypto))
        self.error_insufficient_btc(current_asset_btc)

        # information of active order
        flg_order = False  # True if execute order
        volume = 0

        def get_pl_log(__current_asset, __current_asset_btc):
            # get profit-loss log
            tmp_asset, tmp_asset_btc = self.get_jpy_btc()
            pl_total = tmp_asset - initial_asset
            pl_total_btc = tmp_asset_btc - initial_asset_btc
            pl_one_step = tmp_asset - __current_asset
            pl_one_step_btc = tmp_asset_btc - __current_asset_btc
            self.__log('PL')
            self.__log(' - total   : %0.3f yen' % pl_total)
            self.__log(' - one step: %0.3f yen' % pl_one_step)
            self.__log(' - total   : %0.6f %s' % (pl_total_btc, self.__crypto))
            self.__log(' - one step: %0.6f %s' % (pl_one_step_btc, self.__crypto))
            self.__log('Tmp asset mount: %0.3f JPY, %0.6f %s ' % (tmp_asset, tmp_asset_btc, self.__crypto))
            __current_asset = tmp_asset
            __current_asset_btc = tmp_asset_btc
            __flg_order = False
            return __flg_order, __current_asset, __current_asset_btc

        execute_time = 0
        predicted_time = 0
        acceptance_order_id = None

        while True:
            # wait order to keep latency
            waiting_time = max(0, self.__latency_model - (time.time() - predicted_time))
            self.__log('Waiting %0.3f sec ....' % waiting_time)
            time.sleep(waiting_time)

            self.__log('')
            self.__log('############################')
            self.__log('######## LOOP START ########')
            self.__log('############################')

            ###############
            # Current Val #
            ###############
            self.__log('Request current value')
            health = self.api_public.get_board_state(product_code=self.__asset_name)
            if self.api_error(health):
                continue

            ticker_value = self.api_public.ticker(product_code=self.__asset_name)
            if self.api_error(ticker_value):
                continue

            timestamp = utc_to_unix(ticker_value['timestamp'])
            best_bid = int(ticker_value['best_bid'])
            best_ask = int(ticker_value['best_ask'])
            best_bid_size = float(ticker_value['best_bid_size'])
            best_ask_size = float(ticker_value['best_ask_size'])
            spread = best_ask - best_bid
            self.__log(' - best ask   : %0.2f' % best_ask)
            self.__log(' - best bit   : %0.2f' % best_bid)
            self.__log(' - spread     : %0.2f' % spread)

            # If time-delay is more than latency, skip order and reset model buffer
            if time.time() - timestamp > self.__latency_model:
                self.__log('Ticker API has delayed: %0.2f sec' % (time.time() - timestamp))
                self.__model.reset_buffer()
                self.__log('Reset model buffer')
                self.__log('Bf status: health (%s), state (%s)' % (health['health'], health['state']))

            ##############
            # Prediction #
            ##############
            # model need update buffer so conduct prediction regardless of order
            pred_ask, trend = self.__model.predict(best_ask)
            if pred_ask is not None:
                pred_ask = round(pred_ask)
                self.__log(' - predict ask: %0.2f' % pred_ask)
                self.__log(' - margin     : %0.2f' % (pred_ask - best_ask))
            predicted_time = time.time()

            if flg_order:
                #######################
                # Track Active Order  #
                #######################
                self.__log('Tracking active order')

                # if time.time() - execute_time < self.__minute_to_expire * 60:
                #     self.__log(' - skip: wait for min_to_expire')
                #     continue

                api_val = self.api_order.get_parent_order(parent_order_acceptance_id=acceptance_order_id)
                if self.api_error(api_val):
                    continue

                self.__log(' - get_parent_order: parent_order_acceptance_id (%s)' % acceptance_order_id)
                self.__log(str(api_val))
                parent_order_id = api_val['parent_order_id']

                # - while loop tp avoid stacking by API problem
                # - child_orders API will return 1, or 2 orders
                #   (A) if it returns only for buy order with ACTIVE status, it means that trigger buy order is
                #       still ACTIVE.
                #   (B) if it returns only for buy order with COMPLETE status, it means that trigger buy order is
                #       completed and OCO sell order has been rejected. This rejection should be avoided by
                #       `error_insufficient_btc` so should be never happen hopefully.
                #   (C) if it returns both buy and OCO sell order (basically in this case, buy order has COMPLETE
                #       status), which means that trigger buy order is COMPLETE but OCO sell is still ACTIVE.
                #   (D) if it returns both buy and OCO sell order with COMPLETE status, it means that all order
                #       has finished.
                #   (E) Trigger order (BUY) is expired
                #   (F) OCO order (SELL) is expired
                # - next step
                #   new order: (D), (E)
                #   wait: (A), (C)
                #   execute offset order to remove position and kill executor: (B), (F)

                while True:
                    child_order = self.api_order.get_child_orders(
                        product_code=self.__asset_name,
                        count=10,
                        parent_order_id=parent_order_id
                    )
                    if self.api_error(child_order):
                        continue

                    if len(child_order) != 0:
                        break
                    else:
                        time.sleep(1)

                self.__log(' - get_child_orders: parent_order_id (%s), order number (%i)'
                           % (parent_order_id, len(child_order)))

                state = dict()
                total_commission = 0
                for n, child_dict in enumerate(child_order):
                    self.__log(' - order %i' % n)
                    for k, v in child_dict.items():
                        self.__log('    - %s: %s' % (k, v))
                    state[child_dict['side']] = child_dict['child_order_state']
                    total_commission += float(child_dict['total_commission'])

                # case (A): wait
                if len([v for v in state.values() if v == 'ACTIVE']) != 0:
                    self.__log('Partially active so keep tracking the order')
                    continue

                # case (D): new order
                if len([v for v in state.values() if v != 'COMPLETED']) == 0 and len(state) == 2:
                    self.__log('All orders completed !!')
                    self.__log('Total commission: %0.8f' % total_commission)
                    flg_order, current_asset, current_asset_btc = get_pl_log(current_asset, current_asset_btc)
                    continue

                # case (E): new order
                if 'BUY' in state.keys() and state['BUY'] == 'EXPIRED':
                    self.__log('All orders were expired :(')
                    flg_order, current_asset, current_asset_btc = get_pl_log(current_asset, current_asset_btc)
                    continue

                if len([v for v in state.values() if v != 'COMPLETED']) == 0 and len(state) == 1:
                    # case (B): offset order
                    self.__log('Only buy order has finished. Need to release position.')
                    offset_order = True
                elif 'SELL' in state.keys() and state['SELL'] == 'EXPIRED':
                    # case (F): offset order
                    self.__log('Only sell order has been expired. Need to release position.')
                    offset_order = True
                else:
                    offset_order = True

                if offset_order:
                    _, tmp_asset_btc = self.get_jpy_btc()
                    # sell volume as the difference from one step before
                    volume_offset = tmp_asset_btc - current_asset_btc
                    volume_offset = volume_offset * (1 - commission_rate)
                    volume_offset = round(volume_offset * 10 ** 8) * 10 ** -8
                    while True:
                        order_info_offset = self.api_order.send_child_order(
                            product_code=self.__asset_name,
                            child_order_type="MARKET",
                            side='SELL',
                            size=volume_offset,
                            time_in_force='GTC'
                        )
                        if self.api_error(order_info_offset):
                            continue
                        if 'status' in order_info_offset.keys():
                            self.__log('WARNING: offset order has error')
                            self.__log(' - error : %s' % order_info_offset['error_message'])
                            self.__log(' - status: %s' % order_info_offset['status'])
                            self.__log(' - volume: %0.10f' % volume_offset)
                            time.sleep(10)
                            continue
                        break

                    order_id = order_info_offset['child_order_acceptance_id']
                    self.__log(' - child_order_acceptance_id: %s' % order_id)
                    self.__log(' - volume    : %0.3f' % volume)

                    # wait till the offset order is completed
                    while True:
                        # keep 10 sec interval to avoid 'Over API limit per minute' error
                        time.sleep(5)
                        order_info_child = self.api_order.get_child_orders(product_code=self.__asset_name,
                                                                           child_order_acceptance_id=order_id)
                        if self.api_error(order_info_child):
                            continue

                        self.__log(' - get_child_orders: %s' % str(order_info_child))
                        order_info_child = order_info_child[0]
                        if order_info_child['child_order_state'] == 'COMPLETED':
                            self.__log(' - offset order is completed')
                            break

                    flg_order, current_asset, current_asset_btc = get_pl_log(current_asset, current_asset_btc)
                    self.__log('Reset model buffer')
                    self.__model.reset_buffer()

            else:
                ##################
                # Make New Order #
                ##################
                self.__log('Make new order')

                ##################
                # Skip Condition #
                ##################
                if time.time() - execute_time < self.__latency:
                    self.__log(' - skip order: latency')
                    continue
                # skip if bF is dead
                if health['health'] != 'NORMAL' or health['state'] != 'RUNNING':
                    self.__log(' - skip order: Unstable server. health (%s), state (%s)'
                               % (health['health'], health['state']))
                    continue
                # skip if buffer is not enough
                if pred_ask is None:
                    self.__log(' - skip order: Model buffer')
                    continue
                # skip if market has trend
                if trend != 0:
                    self.__log(' - skip order: Market trend (%i)' % trend)
                    continue
                # skip if spread is too large
                if spread > self.__max_spread:
                    self.__log(' - skip order: Large spread %0.1f' % spread)
                    continue
                # skip if min(best_bid, ask_size) is too small
                volume = min(best_ask_size, best_bid_size)
                if volume < self.__min_volume:
                    self.__log(' - skip order: too small volume %0.6f' % volume)
                    continue
                # skip if current best_ask is larger than prediction or margin is too small.
                volume = min(self.__max_volume, volume)
                min_price, volume_sell = minimum_price(commission=commission_rate,
                                                       volume=volume,
                                                       price_buy=best_ask)
                self.__log(' - margin: %0.2f (min margin: %0.2f + %0.2f)'
                           % (pred_ask - best_ask, min_price - best_ask, self.__profit_take_margin))
                if pred_ask < min_price + self.__profit_take_margin:
                    self.__log(' - skip order: no margin')
                    continue

                #################
                # Execute Order #
                #################
                self.error_insufficient_btc(current_asset_btc)

                self.__log('Execute order')
                self.__log(' - volume_buy  : %0.8f' % volume)
                self.__log(' - volume_sell : %0.8f' % volume_sell)
                self.__log(' - price       : %0.2f' % best_ask)
                self.__log(' - profit      : %0.2f' % pred_ask)
                self.__log(' - loss        : %0.2f' % (best_bid - spread - self.__loss_cut_margin))

                order_info = self.api_order.send_parent_order(
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
                            "price": pred_ask,
                            # "trigger_price": pred_ask,
                            "size": volume_sell
                        },
                        {
                            "product_code": self.__asset_name,
                            "condition_type": "STOP",
                            "side": "SELL",
                            "trigger_price": best_bid - spread - self.__loss_cut_margin,
                            "size": volume_sell
                        }
                    ]
                )
                if self.api_error(order_info):
                    continue

                if 'status' in order_info.keys():
                    self.__log('Error')
                    self.__log(' - error : %s' % order_info['error_message'])
                    self.__log(' - status: %s' % order_info['status'])
                else:
                    self.__log('Succeed')
                    acceptance_order_id = order_info['parent_order_acceptance_id']
                    self.__log(' - parent_order_acceptance_id: %s' % acceptance_order_id)
                    execute_time = time.time()
                    flg_order = True

    def set_model(self,
                  model_name: str,
                  model_parameter: dict=None
                  ):

        if model_name == 'ma':
            self.__model = model.MovingAverage(**model_parameter)
        else:
            raise ValueError('unknown model name: %s' % model_parameter)
