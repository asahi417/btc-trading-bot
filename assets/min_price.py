"""
Script to get minimum price to sell
--volume: volume to trade
--profit_margin: margin for profit-taking
"""

import argparse
import btc_trader
import os
import toml


PASSWORD = os.getenv("PASSWORD", "./password.toml")


def get_options(parser):
    share_param = {'nargs': '?', 'action': 'store', 'const': None, 'choices': None, 'metavar': None}
    parser.add_argument('--product_code', default='FX_BTC_JPY', type=str, **share_param)
    parser.add_argument('--volume', default=None, type=float, **share_param)
    parser.add_argument('--profit_margin', default=None, type=int, **share_param)
    parser.add_argument('--short', action='store_true')
    return parser.parse_args()


def minimum_price_to_get_profit(volume_set: float = None,
                                profit_margin: int = None,
                                if_short: bool = False):

    id_api = toml.load(open(PASSWORD))
    api_public = btc_trader.api.Public(**id_api)
    api_order = btc_trader.api.Order(**id_api)

    # commission rate
    commission_rate = api_order.get_trading_commission(product_code=args.product_code)
    commission_rate = commission_rate['commission_rate']

    # current price
    ticker_value = api_public.ticker(product_code=args.product_code)
    best_bid = int(ticker_value['best_bid'])
    best_ask = int(ticker_value['best_ask'])
    best_bid_size = float(ticker_value['best_bid_size'])
    best_ask_size = float(ticker_value['best_ask_size'])
    volume = min(best_bid_size, best_ask_size)
    total_buy = round(best_ask * volume)

    # calculate
    min_price, volume_sell = btc_trader.minimum_price(commission_rate, best_ask, volume, not if_short)
    total_sell = round(min_price * volume_sell)
    commission_fee_btc = commission_rate * (volume + volume_sell)
    left = volume - volume_sell - commission_fee_btc
    commission_fee_jpy = commission_rate * volume * best_ask + commission_rate * volume_sell * min_price

    print("short", if_short)
    print()
    print("##### IDEAL VOLUME #####")
    print(' - commission : %0.7f' % commission_rate)
    print('BUY (yen)')
    print(' - unit price : %i' % best_ask)
    print(' - total price: %i' % total_buy)
    print(' - volume_BTC : %0.6f' % volume)
    print('SELL (yen)')
    print(' - unit price : %i [minimum price to take profit]' % min_price)
    print(' - total price: %i' % total_sell)
    print(' - volume_BTC : %0.6f' % volume_sell)
    print(' - margin     : %i' % (min_price - best_ask))
    print(' - best_bit   : %i' % best_bid)
    print('PROFIT        : %i' % (total_sell - total_buy))
    print('COMMISSION_JPY: %0.3f' % commission_fee_jpy)
    print('COMMISSION_BTC: %0.7f' % commission_fee_btc)
    print('REMAIN_BTC    : %0.7f' % left)

    if profit_margin is not None:
        print()
        min_price += profit_margin
        total_sell = round(min_price * volume_sell)
        commission_fee_btc = commission_rate * (volume + volume_sell)
        left = volume - volume_sell - commission_fee_btc
        commission_fee_jpy = commission_rate * volume * best_ask + commission_rate * volume_sell * min_price

        print('SELL (yen) with profit margin')
        print(' - unit price : %i' % min_price)
        print(' - total price: %i' % total_sell)
        print(' - margin     : %i' % (min_price - best_ask))
        print(' - best_bit   : %i' % best_bid)
        print('PROFIT        : %i' % (total_sell - total_buy))
        print('COMMISSION_JPY: %0.3f' % commission_fee_jpy)
        print('COMMISSION_BTC: %0.7f' % commission_fee_btc)
        print('REMAIN_BTC    : %0.7f' % left)

    if volume_set is not None:
        print()
        print()
        print("##### CONST. VOLUME #####")
        total_buy = round(best_ask * volume_set)
        min_price, volume_sell = btc_trader.minimum_price(commission_rate, best_ask, volume_set, not if_short)
        total_sell = round(min_price * volume_sell)
        commission_fee_btc = commission_rate * (volume_set + volume_sell)
        left = volume_set - volume_sell - commission_fee_btc
        commission_fee_jpy = commission_rate * volume_set * best_ask + commission_rate * volume_sell * min_price

        print('BUY (yen)')
        print(' - unit price : %i' % best_ask)
        print(' - total price: %i' % total_buy)
        print(' - volume_BTC : %0.6f' % volume_set)
        print('SELL (yen)')
        print(' - unit price : %i [minimum price to take profit]' % min_price)
        print(' - total price: %i' % total_sell)
        print(' - volume_BTC : %0.6f' % volume_sell)
        print(' - margin     : %i' % (min_price - best_ask))
        print(' - best_bit   : %i' % best_bid)
        print('PROFIT        : %i' % (total_sell - total_buy))
        print('COMMISSION_JPY: %0.3f' % commission_fee_jpy)
        print('COMMISSION_BTC: %0.7f' % commission_fee_btc)
        print('REMAIN_BTC    : %0.7f' % left)

        if profit_margin is not None:
            print()
            min_price += profit_margin
            total_sell = round(min_price * volume_sell)
            commission_fee_btc = commission_rate * (volume_set + volume_sell)
            left = volume_set - volume_sell - commission_fee_btc
            commission_fee_jpy = commission_rate * volume_set * best_ask + commission_rate * volume_sell * min_price

            print('SELL (yen) with profit margin')
            print(' - unit price : %i' % min_price)
            print(' - total price: %i' % total_sell)
            print(' - volume     : %0.6f' % volume_sell)
            print(' - margin     : %i' % (min_price - best_ask))
            print(' - best_bit   : %i' % best_bid)
            print('PROFIT        : %i' % (total_sell - total_buy))
            print('COMMISSION_JPY: %0.3f' % commission_fee_jpy)
            print('COMMISSION_BTC: %0.7f' % commission_fee_btc)
            print('REMAIN_BTC    : %0.7f' % left)


if __name__ == '__main__':
    _parser = argparse.ArgumentParser(description='This script is ...', formatter_class=argparse.RawTextHelpFormatter)
    args = get_options(_parser)
    minimum_price_to_get_profit(args.volume,
                                args.profit_margin,
                                args.short)
