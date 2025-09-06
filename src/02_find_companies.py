import asyncio
from datetime import date

import logfire
from pydantic_ai import Agent, WebSearchTool, WebSearchUserLocation

from shared import FIND_COMPANIES_DIR

logfire.configure()
logfire.instrument_pydantic_ai()

find_agent = Agent(
    builtin_tools=[
        WebSearchTool(
            search_context_size='high',
            user_location=WebSearchUserLocation(
                city='New York',
                country='US',
                region='NY',
                timezone='America/New_York',
            ),
            max_uses=10,
        )
    ],
    instructions="""\
You are a research agent responsible for creating a comprehensive but concise report on potential small-cap stocks
to invest in.

Market cap of the companies should be under $300m, all companies must be listed on US exchanges.

Find up to 50 (fifty) companies, for each company return: name, ticker symbol, exchange and a brief description.

Use the web search tool up to ten times to find potential companies.

Find any information that might be relevant to the stocks performance, either positive or negative for each company.

DO NOT return data as a table ever, instead use markdown headers, lists and bullet points.

DO NOT include any stock price information, e.g. current price, historical prices or market cap, etc.

DO NOT attempt to evaluate performance or give your opinions in the report, just provide the information.
""",
)


@find_agent.instructions
def current_date():
    return f"Today's date is {date.today()}."


async def find_companies(model: str) -> None:
    result = await find_agent.run('Find up to 50 companies.', model=model)
    (FIND_COMPANIES_DIR / f'{model}.txt').write_text(result.output)


models = ['openai-responses:gpt-4.1', 'google-vertex:gemini-2.5-pro', 'anthropic:claude-sonnet-4-0']


async def main():
    with logfire.span('finding companies'):
        async with asyncio.TaskGroup() as tg:
            for model in models:
                tg.create_task(find_companies(model=model))


if __name__ == '__main__':
    asyncio.run(main())
