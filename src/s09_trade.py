import os
from typing import Any

import logfire
from alpaca.data import StockHistoricalDataClient, StockLatestTradeRequest, Trade as AlpacaTrade
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import MarketOrderRequest
from dotenv import load_dotenv
from pydantic import BaseModel

from shared import TRADES_FILES, TRADES_LOG_DIR, Trade, trades_schema

logfire.configure()
logfire.instrument_httpx()

load_dotenv()
stock_client = StockHistoricalDataClient(os.environ['ALPACA_API_KEY'], os.environ['ALPACA_SECRET_KEY'])
trading_client = TradingClient(os.environ['ALPACA_API_KEY'], os.environ['ALPACA_SECRET_KEY'], paper=True)


class TradeLog(BaseModel):
    trade: Trade
    order_request: MarketOrderRequest
    market_order: Any | None = None


def main():
    trades = trades_schema.validate_json(TRADES_FILES.read_bytes())
    symbols = [t.symbol for t in trades]
    latest_trades = stock_client.get_stock_latest_trade(StockLatestTradeRequest(symbol_or_symbols=symbols))
    TRADES_LOG_DIR.mkdir(exist_ok=True)

    for trade in trades:
        trade_file = TRADES_LOG_DIR / f'{trade.symbol}.json'
        if trade_file.exists():
            logfire.info(f'Trade file exists for {trade.symbol}')
            continue

        latest_trade = latest_trades[trade.symbol]
        assert isinstance(latest_trade, AlpacaTrade), f'Expected AlpacaTrade, got {type(latest_trade)}'
        # equivalent to floor()
        quantity = int(float(trade.amount) / latest_trade.price)
        market_order_data = MarketOrderRequest(
            symbol=trade.symbol,
            qty=quantity,
            side=OrderSide.BUY,
            time_in_force=TimeInForce.DAY,
        )
        log = TradeLog(trade=trade, order_request=market_order_data)
        trade_file.write_text(log.model_dump_json(indent=2))
        with logfire.span(
            'Submitting order symbol={trade.symbol} quantity={quantity}', trade=trade, quantity=quantity
        ) as span:
            market_order = trading_client.submit_order(order_data=market_order_data)
            log.market_order = market_order
            trade_file.write_text(log.model_dump_json(indent=2))
            span.set_attribute('market_order', market_order)


if __name__ == '__main__':
    with logfire.span('trading'):
        main()
