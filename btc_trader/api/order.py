from .base import API

__all__ = (
    "Order"
)


class Order:
    """Order API (HTTP Private API)"""

    def __init__(self, api_key=None, api_secret=None, timeout=None):
        self.api = API(api_key, api_secret, timeout)

    def get_balance(self, **params):
        """Get Account Asset Balance
        amount != available if you have active order
        """
        self.api.check_keys()
        endpoint = "/v1/me/getbalance"
        return self.api.request(endpoint, params=params)

    def get_collateral(self, **params):
        """"""
        self.api.check_keys()
        endpoint = "/v1/me/getcollateral"
        return self.api.request(endpoint, params=params)

    def get_collateral_accounts(self, **params):
        """"""
        self.api.check_keys()
        endpoint = "/v1/me/getcollateralaccounts"
        return self.api.request(endpoint, params=params)

    def get_positions(self, **params):
        """ Get position for fx, will return
        [
          {
            "product_code": "FX_BTC_JPY",
            "side": "BUY",
            "price": 36000,
            "size": 10,
            "commission": 0,
            "swap_point_accumulate": -35,
            "require_collateral": 120000,
            "open_date": "2015-11-03T10:04:45.011",
            "leverage": 3,
            "pnl": 965,
            "sfd": -0.5
          }
        ]
        """
        self.api.check_keys()
        endpoint = "/v1/me/getpositions"
        return self.api.request(endpoint, params=params)

    def get_executions(self, **params):
        """List Executions
        Parameters
            product_code: Designate "BTC_JPY", "FX_BTC_JPY" or "ETH_BTC".
            count, before, after: See Pagination.
            child_order_id: Optional. When specified, a list of stipulations related to the order will be displayed.
            child_order_acceptance_id: Optional. Expects an ID from Send a New Order. When specified, a list of stipulations related to the corresponding order will be displayed.
        """
        self.api.check_keys()
        endpoint = "/v1/me/getexecutions"
        return self.api.request(endpoint, params=params)

    def get_trading_commission(self, **params):
        """
        Parameters
            product_code: Required. Designate "BTC_JPY", "FX_BTC_JPY" or "ETH_BTC".
        """
        self.api.check_keys()
        endpoint = "/v1/me/gettradingcommission"
        return self.api.request(endpoint, params=params)

    ###############
    # Child order #
    ###############

    def send_child_order(self, **params):
        """Send a New Order
        Parameters
            product_code: Required. The product being ordered. Designate "BTC_JPY", "FX_BTC_JPY" or "ETH_BTC".
            child_order_type: Required. For limit orders, it will be "LIMIT". For market orders, "MARKET".
            side: Required. For buy orders, "BUY". For sell orders, "SELL".
            price: Specify the price. This is a required value if child_order_type has been set to "LIMIT".
            size: Required. Specify the order quantity.
            minute_to_expire: Specify the time in minutes until the expiration time. If omitted, the value will be 525600 (365 days).
            time_in_force: Specify any of the following execution conditions - "GTC", "IOC", or "FOK". If omitted, the value defaults to "GTC".
        Response:
            If the parameters are correct, the status code will show 200 OK.
            child_order_acceptance_id: This is the ID for the API. To specify the order to return, please use this instead
            of child_order_id. Please confirm the item is either Cancel Order or Obtain Execution List.
        """
        self.api.check_keys()
        endpoint = "/v1/me/sendchildorder"
        return self.api.request(endpoint, "POST", params=params)

    def cancel_child_order(self, **params):
        """Cancel Order
        Parameters
            product_code: Required. The product for the corresponding order. Designate "BTC_JPY", "FX_BTC_JPY" or "ETH_BTC".
            Please specify only one between child_order_id and child_order_acceptance_id
            child_order_id: ID for the canceling order.
            child_order_acceptance_id: Expects an ID from Send a New Order. When specified, the corresponding order will be cancelled.
        Response: If the parameters are correct, the status code will show 200 OK.
        """
        self.api.check_keys()
        endpoint = "/v1/me/cancelchildorder"
        return self.api.request(endpoint, "POST", params=params)

    def cancel_all_child_orders(self, **params):
        """Cancel All Orders
        Parameters
            product_code: The product for the corresponding order. Designate "BTC_JPY", "FX_BTC_JPY" or "ETH_BTC".
        Response: If the parameters are correct, the status code will show 200 OK.
        """
        self.api.check_keys()
        endpoint = "/v1/me/cancelallchildorders"
        return self.api.request(endpoint, "POST", params=params)

    def get_child_orders(self, **params):
        """List Orders
        Parameters
            product_code: Designate "BTC_JPY", "FX_BTC_JPY" or "ETH_BTC".
            count, before, after: See Pagination.
            child_order_state: When specified, return only orders that match the specified value. You must specify one of the following:
                ACTIVE: Return open orders
                COMPLETED: Return fully completed orders
                CANCELED: Return orders that have been cancelled by the customer
                EXPIRED: Return order that have been cancelled due to expiry
                REJECTED: Return failed orders
            parent_order_id: If specified, a list of all orders associated with the parent order is obtained.
        """
        self.api.check_keys()
        endpoint = "/v1/me/getchildorders"
        return self.api.request(endpoint, params=params)

    ################
    # Parent order #
    ################

    def send_parent_order(self, **params):
        """Submit New Parent Order (Special order)
        It is possible to place orders including logic other than simple limit orders (LIMIT) and market orders (MARKET). Such orders are handled as parent orders. By using a special order, it is possible to place orders in response to market conditions or place multiple associated orders.
        Please read about the types of special orders and their methods in the bitFlyer Lightning documentation on special orders.
        Parameters
            order_method: The order method. Please set it to one of the following values. If omitted, the value defaults to "SIMPLE".
                "SIMPLE": A special order whereby one order is placed.
                "IFD": Conducts an IFD order. In this method, you place two orders at once, and when the first order is completed, the second order is automatically placed.
                "OCO": Conducts an OCO order. In this method, you place two orders at one, and when one of the orders is completed, the other order is automatically canceled.
                "IFDOCO": Conducts an IFD-OCO order. In this method, once the first order is completed, an OCO order is automatically placed.
            minute_to_expire: Specifies the time until the order expires in minutes. If omitted, the value defaults to 525600 (365 days).
            time_in_force: Specify any of the following execution conditions - "GTC", "IOC", or "FOK". If omitted, the value defaults to "GTC".
            parameters: Required value. This is an array that specifies the parameters of the order to be placed. The required length of the array varies depending upon the specified order_method.
                If "SIMPLE" has been specified, specify one parameter.
                If "IFD" has been specified, specify two parameters. The first parameter is the parameter for the first order placed. The second parameter is the parameter for the order to be placed after the first order is completed.
                If "OCO" has been specified, specify two parameters. Two orders are placed simultaneously based on these parameters.
                If "IFDOCO" has been specified, specify three parameters. The first parameter is the parameter for the first order placed. After the order is complete, an OCO order is placed with the second and third parameters.

            In the parameters, specify an array of objects with the following keys and values.

            product_code: Required value. This is the product to be ordered. Currently, only "BTC_JPY" is supported.
            condition_type: Required value. This is the execution condition for the order. Please set it to one of the following values.
                "LIMIT": Limit order.
                "MARKET": Market order.
                "STOP": Stop order.
                "STOP_LIMIT": Stop-limit order.
                "TRAIL": Trailing stop order.
            side: Required value. For buying orders, specify "BUY", for selling orders, specify "SELL".
            size: Required value. Specify the order quantity.
            price: Specify the price. This is a required value if condition_type has been set to "LIMIT" or "STOP_LIMIT".
            trigger_price: Specify the trigger price for a stop order. This is a required value if condition_type has been set to "STOP" or "STOP_LIMIT".
            offset: Specify the trail width of a trailing stop order as a positive integer. This is a required value if condition_type has been set to "TRAIL".
        Response:
            If the parameters are correct, the status code will show 200 OK.
            parent_order_acceptance_id: This is the ID for the API. To specify the order to return, please use this instead of parent_order_id.s
        """
        self.api.check_keys()
        endpoint = "/v1/me/sendparentorder"
        return self.api.request(endpoint, "POST", params=params)

    def cancel_parent_order(self, **params):
        """Cancel parent order
        Parameters
            product_code: Required. The product for the corresponding order. Designate "BTC_JPY", "FX_BTC_JPY" or "ETH_BTC".
            Please specify only one between parent_order_id and parent_order_acceptance_id
            parent_order_id: ID for the canceling order.
            parent_order_acceptance_id: Expects an ID from Submit New Parent Order. When specified, the corresponding order will be cancelled.
        Response: If the parameters are correct, the status code will show 200 OK.
        """
        self.api.check_keys()
        endpoint = "/v1/me/cancelparentorder"
        return self.api.request(endpoint, "POST", params=params)

    def get_parent_orders(self, **params):
        """List Parent Orders
        Parameters
            product_code: Designate "BTC_JPY", "FX_BTC_JPY" or "ETH_BTC".
            count, before, after: See Pagination.
            child_order_state: When specified, return only orders that match the specified value. You must specify one of the following:
                ACTIVE: Return open orders
                COMPLETED: Return fully completed orders
                CANCELED: Return orders that have been cancelled by the customer
                EXPIRED: Return order that have been cancelled due to expiry
                REJECTED: Return failed orders
        Response
            price and size values for parent orders with multiple associated orders are both reference values only.
            To obtain the detailed parameters for individual orders, use the API to obtain the details of the parent order. To obtain a list of associated orders, use the API to obtain the order list.
        """
        self.api.check_keys()
        endpoint = "/v1/me/getparentorders"
        return self.api.request(endpoint, params=params)

    def get_parent_order(self, **params):
        """Get Parent Order Details
        Parameters
            product_code: Designate "BTC_JPY", "FX_BTC_JPY" or "ETH_BTC".
                Please specify only parent_order_id or parent_order_acceptance_id.
            parent_order_id: The ID of the parent order in question.
            parent_order_acceptance_id: The acceptance ID for the API to place a new parent order. If specified, it returns the details of the parent order in question.
        """
        self.api.check_keys()
        endpoint = "/v1/me/getparentorder"
        return self.api.request(endpoint, params=params)



