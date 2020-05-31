import btc_trader
import toml
import os

API_KEYS = os.getenv("API_KEYS", "./api_keys.toml")
CONFIG = os.getenv("CONFIG", "./config.toml")
LOG = os.getenv("LOG", "./run_trader.log")

if __name__ == '__main__':

    id_api = toml.load(open(API_KEYS))
    config = toml.load(open(CONFIG))
    executor = btc_trader.ExecutorFX(
        id_api=id_api,
        logger_output=LOG,
        **config['executor_parameter']
    )
    executor.set_model(model_name=config['model_name'], model_parameter=config['model_parameter'])
    executor.run()

