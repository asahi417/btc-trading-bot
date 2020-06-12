# Bitcoin Auto-Trading Bot 
Simple Bitcoin auto-trading system with [bitFlyer API](https://lightning.bitflyer.com/docs?lang=en).

## Get Started
Clone and install requirements.

```bash
git clone https://github.com/asahi417/btc-trading-bot
cd btc-trading-bot
pip install .
```

All executions are done via bitFlyer, so one needs to make an account and get **api_key** and **api_secret**,
and put them in `./api_keys.toml` file.

Run a trading bot: 

```bash
export API_KEYS=./api_keys.toml
export CONFIG=./config.toml
python run_trader.py
```

Any configurations for either model or executions can be tuned by the [config file](./config.toml).

## Notes
### Timezone
Bitflyer API employs UTC as return value about date information (eg, `open_date`), but swap point is calculated based 
on JST.

### API limits
According to [official websit](https://lightning.bitflyer.com/docs?lang=en),

```
Please be aware of the HTTP API usage limits below.

The private API is limited to approx. 200 queries per minute
Each IP address is limited to approx. 500 queries per minute


Users who place a large quantity of orders with an amount of 0.1 or less may be temporarily limited to 10 orders per minute.
We may restrict API use if we find that the same order is being repeatedly placed with the intent of placing a heavy load on our system.
```
