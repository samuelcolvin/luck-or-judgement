from decimal import Decimal

from shared import DAY_PORTFOLIO_FILE, TRADES_FILES, Trade, portfolios_schema, trades_schema

PORTFOLIO_SIZE = 1000


def main():
    portfolios = portfolios_schema.validate_json(DAY_PORTFOLIO_FILE.read_bytes())

    trades: dict[str, Trade] = {}
    for source, portfolio in portfolios.items():
        for new_investment in portfolio.investments:
            if trade := trades.get(new_investment.identifier()):
                trade.amount += new_investment.investment_amount
                trade.sources.append(source)
            else:
                trades[new_investment.identifier()] = Trade(
                    amount=Decimal(new_investment.investment_amount),
                    sources=[source],
                    symbol=new_investment.symbol,
                    exchange=new_investment.exchange,
                )

    adjustment = Decimal(f'{PORTFOLIO_SIZE / sum(trade.amount for trade in trades.values()):0.5f}')
    for trade in trades.values():
        trade.amount = trade.amount * adjustment

    trades_list = sorted(trades.values(), key=lambda trade: trade.amount, reverse=True)
    TRADES_FILES.write_bytes(trades_schema.dump_json(trades_list, indent=2))
    print(f'Written {len(trades_list)} trades to file, totaling ${sum(trade.amount for trade in trades.values()):.2f}')


if __name__ == '__main__':
    main()
