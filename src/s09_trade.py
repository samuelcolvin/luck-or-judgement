import os
from typing import Any

import logfire
import polars as pl
from alpaca.data import StockHistoricalDataClient, StockLatestTradeRequest, Trade as AlpacaTrade
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import MarketOrderRequest
from dotenv import load_dotenv
from pydantic import BaseModel

from shared import ASSETS_FILE, TRADES_FILES, TRADES_LOG_DIR, Trade, trades_schema

logfire.configure()
logfire.instrument_httpx()

load_dotenv()
paper = True
stock_client = StockHistoricalDataClient(os.environ['ALPACA_API_KEY'], os.environ['ALPACA_SECRET_KEY'])
trading_client = TradingClient(os.environ['ALPACA_API_KEY'], os.environ['ALPACA_SECRET_KEY'], paper=paper)
assets = pl.read_parquet(ASSETS_FILE)


class TradeLog(BaseModel):
    trade: Trade
    requested_quantity: float
    latest_trade: AlpacaTrade
    order_request: MarketOrderRequest
    market_order: Any | None = None


def main():
    trades = trades_schema.validate_json(TRADES_FILES.read_bytes())
    symbols = [t.symbol for t in trades]
    latest_trades = stock_client.get_stock_latest_trade(StockLatestTradeRequest(symbol_or_symbols=symbols))
    TRADES_LOG_DIR.mkdir(exist_ok=True)

    for trade in trades:
        trade_file = TRADES_LOG_DIR / f'{trade.symbol}-{paper=}.json'
        if trade_file.exists():
            logfire.info(f'Trade file exists for {trade.symbol}')
            continue

        latest_trade = latest_trades[trade.symbol]
        assert isinstance(latest_trade, AlpacaTrade), f'Expected AlpacaTrade, got {type(latest_trade)}'
        requested_quantity = float(trade.amount) / latest_trade.price

        df_match = assets.filter((pl.col('symbol') == trade.symbol))
        assert not df_match.is_empty(), f'No asset found for symbol {trade.symbol}'
        fractionable = df_match['fractionable'][0]
        if fractionable:
            quantity = round(requested_quantity, 2)
        else:
            # round down if not fractionable
            quantity = int(requested_quantity)
            if quantity == 0:
                if requested_quantity < 0.5:
                    logfire.info(f'Quantity is zero for {trade.symbol}, not trading {requested_quantity=}')
                    continue
                else:
                    quantity = 1

        market_order_data = MarketOrderRequest(
            symbol=trade.symbol,
            qty=quantity,
            side=OrderSide.BUY,
            time_in_force=TimeInForce.DAY,
        )
        log = TradeLog(
            trade=trade,
            requested_quantity=requested_quantity,
            latest_trade=latest_trade,
            order_request=market_order_data,
        )
        trade_file.write_text(log.model_dump_json(indent=2))
        with logfire.span(
            'Submitting order symbol={trade.symbol} {requested_quantity=:0.2f} {quantity=}',
            trade=trade,
            quantity=quantity,
            requested_quantity=requested_quantity,
            latest_trade=latest_trade,
        ) as span:
            market_order = trading_client.submit_order(order_data=market_order_data)
            log.market_order = market_order
            trade_file.write_text(log.model_dump_json(indent=2))
            span.set_attribute('market_order', market_order)


if __name__ == '__main__':
    if input(f'Are you sure you want to trade with {paper=}? (y/n) ') == 'y':
        with logfire.span('trading'):
            main()
    else:
        logfire.warn('Aborting trades')
        exit(1)
