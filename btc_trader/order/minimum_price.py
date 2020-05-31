
"""

Given parameter
------------------
p_b: price of buy order execution
v_b: volume of buy
c  : commission rate

Target variable
-------------------
p_s: price to sell
v_s: volume to sell

Condition
--------------
(1) Total asset balance of BTC shouldn't be changed by any executions
(2) Get profit in yen

Equation
---------------
From (1), to keep the amount of BTC,
    0 = v_b - v_s - c (v_b + v_s)
    v_s = (1-c) / (1+c) * v_b
Then, to ensure the profit
    p_s * v_s > p_b * v_b
    p_s > p_b * v_b / v_s
    p_s > p_b * (1+c) / (1-c)

So, at least you need to ensure that selling the btc more than {(1+c)/(1-c)}^2 p_b to avoid get loss
"""


def minimum_price(commission: float,
                  price: float,
                  volume: float,
                  if_long: bool = True):
    """
    :param commission: commission rate (not percentage)
    :param price: price for BUY order
    :param volume: trading volume
    :param if_long: True if long, False for short
    :return: minimum price to take profit
    """

    if commission != 0:
        volume_other_side = volume * (1 - commission) / (1 + commission)
        # minimum unit of bitflyer is 1e-8
        volume_other_side = round(volume_other_side * 10 ** 8 - 0.5) * 10 ** -8
    else:
        volume_other_side = volume

    if if_long:
        amount_rounded = round(price * volume + 0.5)
        price_other_side = round(amount_rounded / volume_other_side+0.5)
    else:
        amount_rounded = round(price * volume - 0.5)
        price_other_side = round(amount_rounded / volume_other_side - 0.5)
    # # price_sell = ((1 + commission) / (1 - commission))**2 * price_buy
    # price_sell = price_buy * (1 + commission) / (1 - commission)
    # # round to integer
    # price_sell = round(price_sell+0.5)
    return price_other_side, volume_other_side


# def minimum_price_2(commission: float,
#                     price_buy: float,
#                     volume_buy: float):
#     """
#
#     :param commission: commission rate
#     :param price_buy: price for BUY order
#     :param volume: trading volume
#     :return: minimum price to take profit
#     """
#     amount_sell = (100 + commission) / (100 - commission) * round(volume_buy * price_buy)
#     price_sell = (amount_sell + 0.5)/volume_buy
#     # (amount_sell + 0.5) / volume
#     return round(price_sell)
