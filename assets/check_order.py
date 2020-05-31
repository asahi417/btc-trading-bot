import json
import argparse
import btc_trader
import toml
import os
from datetime import datetime

PASSWORD = os.getenv("PASSWORD", "./password.toml")

api_list = [
    'board', 'ticker', 'execution', 'get_board_state', 'get_health', 'markets', 'get_collateral',
    'get_collateral_accounts',
    'get_position', 'get_balance', 'get_executions', 'get_trading_commission', 'get_child_orders',
    'get_parent_orders', 'get_parent_order',
    'cancel_all_child_orders'
]


def get_options(parser):
    share_param = {'nargs': '?', 'action': 'store', 'const': None, 'choices': None, 'metavar': None}
    parser.add_argument('mode', help='api name', type=str, **share_param)
    parser.add_argument('--product_code', default='FX_BTC_JPY', type=str, **share_param)
    parser.add_argument('--parent_order_id', default=None, type=str, **share_param)
    parser.add_argument('--parent_order_acceptance_id', default=None, type=str, **share_param)
    parser.add_argument('--child_order_id', default=None, type=str, **share_param)
    parser.add_argument('--child_order_state', default=None, type=str, **share_param)
    parser.add_argument('--child_order_acceptance_id', default=None, type=str, **share_param)
    parser.add_argument('--parent_order_state', default=None, type=str, **share_param)
    parser.add_argument('--count', default=10, type=int, **share_param)
    return parser.parse_args()


if __name__ == '__main__':
    _parser = argparse.ArgumentParser(description='This script is ...', formatter_class=argparse.RawTextHelpFormatter)
    args = get_options(_parser)

    id_api = toml.load(open(PASSWORD))
    api_order = btc_trader.api.Order(**id_api)
    api_public = btc_trader.api.Public(**id_api)

    if args.mode == 'board':
        tmp = api_public.board(product_code=args.product_code)

    elif args.mode == 'ticker':
        tmp = api_public.ticker(product_code=args.product_code)

    elif args.mode == 'executions':
        tmp = api_public.executions(product_code=args.product_code, count=args.count)

    elif args.mode == 'get_board_state':
        tmp = api_public.get_board_state(product_code=args.product_code)

    elif args.mode == 'get_health':
        tmp = api_public.get_health(product_code=args.product_code)

    elif args.mode == 'markets':
        tmp = api_public.markets()

    elif args.mode == 'get_collateral_accounts':
        tmp = api_order.get_collateral_accounts()

    elif args.mode == 'get_collateral':
        tmp = api_order.get_collateral()

    elif args.mode == 'get_positions':
        tmp = api_order.get_positions(product_code=args.product_code)

    elif args.mode == 'get_balance':
        tmp = api_order.get_balance()

    elif args.mode == 'get_executions':
        tmp = api_order.get_executions(product_code=args.product_code,
                                       count=args.count)
    elif args.mode == 'get_trading_commission':
        tmp = api_order.get_trading_commission(product_code=args.product_code)

    elif args.mode == 'get_child_orders':
        parameter = dict(product_code=args.product_code, count=args.count)
        if args.parent_order_id:
            parameter["parent_order_id"] = args.parent_order_id
        if args.child_order_acceptance_id:
            parameter["child_order_acceptance_id"] = args.child_order_acceptance_id
        if args.child_order_id:
            parameter["child_order_id"] = args.child_order_id
        if args.child_order_state:
            parameter['child_order_state'] = args.child_order_state
        tmp = api_order.get_child_orders(**parameter)

    elif args.mode == 'get_parent_orders':
        parameter = dict(product_code=args.product_code, count=args.count)
        if args.parent_order_state:
            parameter['parent_order_state'] = args.parent_order_state
        tmp = api_order.get_parent_orders(**parameter)

    elif args.mode == 'get_parent_order':
        parameter = dict()
        if args.parent_order_id:
            parameter["parent_order_id"] = args.parent_order_id
        elif args.parent_order_acceptance_id:
            parameter["parent_order_acceptance_id"] = args.parent_order_acceptance_id
        else:
            raise ValueError('No parameter')
        tmp = api_order.get_parent_order(**parameter)

    elif args.mode == 'cancel_all_child_orders':
        tmp = api_order.cancel_all_child_orders(product_code=args.product_code)
    else:
        raise ValueError('unknown api. should be one from %s' % str(api_list))

    print('API : %s' % args.mode)
    print('UTC : %s' % datetime.utcnow().isoformat())
    print('TYPE: %s' % type(tmp))

    if len(tmp) == 0:
        print('Empty return value')
    elif type(tmp) == dict:
        print(json.dumps(tmp, indent=4, sort_keys=True))
    else:
        for _b in tmp:
            print(json.dumps(_b, indent=4, sort_keys=True))
