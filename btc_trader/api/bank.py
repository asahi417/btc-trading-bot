from .base import API

__all__ = (
    "Banking"
)


class Banking:
    """Banking (HTTP Private API)"""

    def __init__(self, api_key=None, api_secret=None, timeout=None):
        self.api = API(api_key, api_secret, timeout)

    def get_addresses(self, **params):
        """Get Bitcoin/Ethereum Deposit Addresses
        Response
            type: "NORMAL" for general deposit addresses.
            currency_code: "BTC" for Bitcoin addresses and "ETH" for Ethereum addresses.
        """
        self.api.check_keys()
        endpoint = "/v1/me/getaddresses"
        return self.api.request(endpoint, params=params)

    def get_coin_ins(self, **params):
        """Get Bitcoin/Ether Deposit History
        Parameters
            count, before, after: See Pagination.
        Response
            status: If the Bitcoin deposit is being processed, it will be listed as "PENDING". If the deposit has been completed, it will be listed as "COMPLETED".
        """
        self.api.check_keys()
        endpoint = "/v1/me/getcoinins"
        return self.api.request(endpoint, params=params)

    def send_coin(self, **params):
        """Bitcoin/Ethereum External Delivery
        Parameters
            currency_code: Required. Type of currency to be sent. Please use "BTC" for Bitcoin and "ETH" for Ethereum.
            amount: Amount to be sent, specified as a number.
                If the currency_code is "BTC", then the units are in BTC.
                If the currency_code is `"ETC", then the units are in Ether.
            amount_text: Specifies the amount to be sent as a string. You are required to choose either amount or amount_text.
            address: Required. Specifies the address to which it will be sent.
                When currency_code is specified as "ETH", funds cannot be sent to a contract address.
                The address designated here will automatically be labeled as an external address.
            additional_fee: You may specify an additional fee to be paid to Bitcoin miners to prioritize their transaction. Standard fees based on transaction data size are paid by bitFlyer; however, the customer is responsible for any additional fees.
                Omitted values will be entered as "0".
                The upper limit is 0.0005 BTC .
                This can not be used if currency_code is specified as "ETH".
        Response
            message_id: Transaction Message Receipt ID

        If an error with a negative status value is returned, the transaction has not been broadcast.
        """
        self.api.check_keys()
        endpoint = "/v1/me/sendcoin"
        return self.api.request(endpoint, "POST", params=params)

    def get_coin_outs(self, **params):
        """Get Bitcoin/Ether Transaction History
        Parameters
            count, before, after: See Pagination.
            message_id: You can confirm delivery status by checking a transaction receipt ID with the Bitcoin/Ethereum External Delivery API.
        Response
            status: If the remittance is being processed, it will be listed as "PENDING". If the remittance has been completed, it will be listed as "COMPLETED".
        """
        self.api.check_keys()
        endpoint = "/v1/me/getcoinouts"
        return self.api.request(endpoint, params=params)

    def get_deposits(self, **params):
        """Get Cash Deposits
        Parameters
            count, before, after: See Pagination.
        Response
            status: If the cash deposit is being processed, it will be listed as "PENDING". If the deposit has been completed, it will be listed as "COMPLETED".
        """
        self.api.check_keys()
        endpoint = "/v1/me/getdeposits"
        return self.api.request(endpoint, params=params)

    def withdraw(self, **params):
        """Cancelling deposits
        Parameters
            currency_code: Required. Currently only compatible with "JPY".
            bank_account_id: Required. Specify id of the bank account.
            amount: Required. This is the amount that you are canceling.
            Additional fees apply for withdrawals. Please see the Fees and Taxes page for reference.
        Response
            message_id: Transaction Message Receipt ID
            If an error with a negative status value is returned, the cancellation has not been committed.
        """
        self.api.check_keys()
        endpoint = "/v1/me/withdraw"
        return self.api.request(endpoint, "POST", params=params)

    def get_withdrawals(self, **params):
        """Get Deposit Cancellation History
        Parameters
            count, before, after: See Pagination.
        Response
            status: If the cancellation is being processed, it will be listed as "PENDING". If the cancellation has been completed, it will be listed as "COMPLETED".
        """
        self.api.check_keys()
        endpoint = "/v1/me/getwithdrawals"
        return self.api.request(endpoint, params=params)

    def get_bank_accounts(self, **params):
        """Get Summary of Bank Accounts. Returns a summary of bank accounts registered to your account.
        Response
            id: ID for the account designated for withdrawals.
            is_verified: Will be return true if the account is verified and capable of sending money.
        """
        self.api.check_keys()
        endpoint = "/v1/me/getbankaccounts"
        return self.api.request(endpoint, params=params)

    def get_collateral(self, **params):
        """Get Margin Status
        Response
            collateral: This is the amount of deposited in Japanese Yen.
            open_position_pnl: This is the profit or loss from valuation.
            require_collateral: This is the current required margin.
            keep_rate: This is the current maintenance margin.
        """
        self.api.check_keys()
        endpoint = "/v1/me/getcollateral"
        return self.api.request(endpoint, params=params)

    def get_collateral_history(self, **params):
        """Get Margin Change History
        Response
            collateral: This is the amount of deposited in Japanese Yen.
            open_position_pnl: This is the profit or loss from valuation.
            require_collateral: This is the current required margin.
            keep_rate: This is the current maintenance margin.
        """
        self.api.check_keys()
        endpoint = "/v1/me/getcollateralhistory"
        return self.api.request(endpoint, params=params)
