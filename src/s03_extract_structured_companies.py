import asyncio
from pathlib import Path

import logfire
from pydantic_ai import Agent

from shared import COMPANY_DATA_DIR, FIND_COMPANIES_DIR, Company, companies_schema

logfire.configure()
logfire.instrument_pydantic_ai()

extract_agent = Agent(
    'openai:gpt-5',
    output_type=list[Company],
    instructions='Extract data on all companies from the provided data',
)


async def extract_companies(file: Path) -> None:
    with logfire.span('{file=}', file=file.name) as span:
        result = await extract_agent.run(file.read_text())
        span.set_attribute('company_count', len(result.output))
        (COMPANY_DATA_DIR / f'{file.stem}.json').write_bytes(companies_schema.dump_json(result.output, indent=2))


async def main():
    with logfire.span('extracting structured data about companies'):
        async with asyncio.TaskGroup() as tg:
            for file in FIND_COMPANIES_DIR.iterdir():
                tg.create_task(extract_companies(file))


if __name__ == '__main__':
    asyncio.run(main())
