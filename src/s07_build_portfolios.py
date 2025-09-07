import asyncio
from datetime import date

import logfire
from pydantic_ai import Agent

from shared import (
    DAY_ANALYSIS_FILE,
    DAY_PORTFOLIO_FILE,
    CompanyAnalysis,
    Portfolio,
    company_analysis_schema,
    portfolios_schema,
)

logfire.configure(scrubbing=False, console=False)
logfire.instrument_pydantic_ai()

models = 'openai:gpt-5', 'google-vertex:gemini-2.5-pro', 'anthropic:claude-opus-4-1-20250805'


investment_agent = Agent(
    output_type=Portfolio,
    instructions="""\
You are an expert financial analyst. Analyze the companies provided and build a portfolio of investments
that should maximize returns over one quarter.

You have $1000 (one thousand dollars USD) to invest.

Mark sure you build a diversified portfolio to maximize returns even if certain companies or industries underperform.
""",
)


@investment_agent.instructions
def current_date():
    return f"Today's date is {date.today()}."


async def build_portfolio(companies: list[CompanyAnalysis], model: str) -> Portfolio:
    with logfire.span(f'build portfolio with {model}'):
        prompt = '/n'.join(company.llm_xml() for company in companies)
        result = await investment_agent.run(prompt, model=model)
        return result.output


async def main():
    companies = company_analysis_schema.validate_json(DAY_ANALYSIS_FILE.read_bytes())[:20]
    portfolios: dict[str, Portfolio] = {}
    if DAY_PORTFOLIO_FILE.exists():
        portfolios = portfolios_schema.validate_json(DAY_PORTFOLIO_FILE.read_bytes())

    try:
        with logfire.span('Building portfolios'):

            async def build_portfolio_save(model: str) -> None:
                if model not in portfolios:
                    portfolios[model] = await build_portfolio(companies, model)

            async with asyncio.TaskGroup() as tg:
                for model in models:
                    tg.create_task(build_portfolio_save(model))
    finally:
        if portfolios:
            DAY_PORTFOLIO_FILE.write_bytes(portfolios_schema.dump_json(portfolios, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
