import os

import logfire
import polars as pl
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import AssetClass
from alpaca.trading.requests import GetAssetsRequest
from dotenv import load_dotenv

from shared import ASSETS_FILE

logfire.configure()
logfire.instrument_httpx()

load_dotenv()
pl.Config.set_tbl_cols(20)

with logfire.span('get assets'):
    trading_client = TradingClient(os.environ['ALPACA_API_KEY'], os.environ['ALPACA_SECRET_KEY'])

    with logfire.span('downloading assets from Alpaca'):
        assets = trading_client.get_all_assets(GetAssetsRequest(asset_class=AssetClass.US_EQUITY))

    with logfire.span('converting assets to polars DataFrame'):
        df = pl.from_dicts(assets)  # type: ignore
        df = df.drop('id')

    print(df)

    with logfire.span('writing assets to parquet'):
        df.write_parquet(ASSETS_FILE)
