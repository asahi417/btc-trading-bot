import btc_trader
import toml
import os

API_KEYS = os.getenv("API_KEYS", None)
CONFIG = os.getenv("CONFIG", None)
LOG = os.getenv("LOG", "./run_trader.log")

if __name__ == '__main__':
    if API_KEYS is None or CONFIG is None:
        raise ValueError('`API_KEYS` or `CONFIG` is not provided.')
    id_api = toml.load(open(API_KEYS))
    config = toml.load(open(CONFIG))
    executor = btc_trader.ExecutorFX(
        id_api=id_api,
        logger_output=LOG,
        **config['executor_parameter']
    )
    executor.set_model(model_name=config['model_name'], model_parameter=config['model_parameter'])
    executor.run()

