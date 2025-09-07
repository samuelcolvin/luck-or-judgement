import asyncio
import re

import logfire
import polars as pl
from pydantic_ai import Agent

from shared import ASSETS_FILE, COMPANY_DATA_DIR, KNOWN_COMPANIES_FILE, Company, companies_schema

logfire.configure()
logfire.instrument_pydantic_ai()

assets = pl.read_parquet(ASSETS_FILE)


def simplify_name(name: str) -> str:
    name = name.lower().strip()
    name = re.sub(r'[\-_]', ' ', name)
    name = re.sub(' {2,}', ' ', name)
    name = re.sub('[,.]', '', name)
    return name


company_equality_agent = Agent(
    'groq:openai/gpt-oss-20b',
    output_type=bool,
    instructions='Do these two company names refer to the same company?',
)


async def known_company(c: Company) -> Company | None:
    df_match = assets.filter((pl.col('symbol') == c.symbol))
    if df_match.is_empty():
        return

    asset_data = df_match.to_dicts()[0]
    if c.exchange == asset_data['exchange']:
        # symbol and exchange match, good confidence
        return c

    if simplify_name(c.name) == simplify_name(asset_data['name']):
        # symbol, exchange, and name match, very good confidence
        return c

    result = await company_equality_agent.run(f'"{c.name}" VS "{asset_data["name"]}"')
    return c if result.output else None


known_companies: list[Company] = []


async def main():
    with logfire.span('filtering companies'):
        total = 0
        for f in COMPANY_DATA_DIR.iterdir():
            with logfire.span(f'reading {f.name}'):
                companies = companies_schema.validate_json(f.read_bytes())
                total += len(companies)
                r = await asyncio.gather(*[known_company(c) for c in companies])
                known_companies.extend([c for c in r if c is not None])

        logfire.info('matched {count} companies out of {total}', count=len(known_companies), total=total)
        KNOWN_COMPANIES_FILE.write_bytes(companies_schema.dump_json(known_companies, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
