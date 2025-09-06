from datetime import date

import logfire
from pydantic_ai import Agent, WebSearchTool, WebSearchUserLocation

from shared import Company

logfire.configure()
logfire.instrument_pydantic_ai()

research_agent = Agent(
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
You are an expert researcher responsible for creating a comprehensive but concise report on the performance of
the given company, the report will be used to inform investment decisions.

Use the web search tool up to ten times to find information about the company.

Find any information that might be relevant to the stock's performance, either positive or negative.

Pay special attention to any recent news or events that may impact the stock price over the next few weeks.
Where possible include dates when the event occurred.

The maximum time horizon you should consider is one quarter.

Return the data as markdown paragraph or bullet points, DO NOT EVER format data in tables.

DO NOT include any stock price information, e.g. current price, historical prices, market cap, etc.

DO NOT include any of your knowledge about the company or market in the report, just information you retrieved
from search.

DO NOT attempt to evaluate performance or give your opinions in the report, just provide a neutral report.
""",
)


@research_agent.instructions
def current_date():
    return f"Today's date is {date.today()}."


async def research_company(company: Company, model: str) -> str:
    result = await research_agent.run(f'company_ticker_symbol={company.symbol} name={company.name}', model=model)
    return result.output
