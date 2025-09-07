import asyncio
from collections import Counter
from datetime import date

import logfire
from pydantic_ai import Agent, format_as_xml
from rich.progress import Progress

from shared import (
    DAY_ANALYSIS_FILE,
    DAY_RESEARCH_DIR,
    KNOWN_COMPANIES_FILE,
    Analysis,
    Company,
    CompanyAnalysis,
    companies_schema,
    company_analysis_schema,
)

logfire.configure(console=False)
logfire.instrument_pydantic_ai()


# model = 'openai:gpt-5'
# model = 'google-vertex:gemini-2.5-pro'
model = 'anthropic:claude-opus-4-1-20250805'

analysis_agent = Agent(
    model=model,
    output_type=Analysis,
    instructions="""\
You are an expert financial analyst, creating a comprehensive but concise report on the small-cap company given.

Pay special attention to any recent news or events that may impact the stock price over the next few weeks.

The maximum time horizon you should consider is one quarter.

Be harsh in your analysis, of both quality and information score. We can only invest in a small number of companies,
so only the best companies should receive A and B grades.
""",
)


@analysis_agent.instructions
def current_date():
    return f"Today's date is {date.today()}."


async def analyse_company(company: Company) -> Analysis:
    with logfire.span(f'analysing {company.symbol}'):
        research_file = DAY_RESEARCH_DIR / f'{company.identifier()}.md'
        result = await analysis_agent.run(
            format_as_xml({'company': company, 'company_research': research_file.read_text()})
        )
        return result.output


async def main():
    companies = companies_schema.validate_json(KNOWN_COMPANIES_FILE.read_bytes())
    sem = asyncio.Semaphore(50)
    analysis: list[CompanyAnalysis] = []
    already_analysed: set[str] = set()
    if DAY_ANALYSIS_FILE.exists():
        analysis = company_analysis_schema.validate_json(DAY_ANALYSIS_FILE.read_bytes())
        for a in analysis:
            for k in a.analysis:
                already_analysed.add(f'{a.company.identifier()}-{k}')

    analysis_count = 0
    score_counter: Counter[str] = Counter()
    try:
        with logfire.span(f'Analysing {len(companies)} companies...'):
            with Progress() as progress:
                task = progress.add_task(f'Analysing {len(companies)} companies...', total=len(companies))

                async def analyse_company_save(company: Company) -> None:
                    nonlocal analysis_count

                    if f'{company.identifier()}-{model}' not in already_analysed:
                        async with sem:
                            a = await analyse_company(company)
                            analysis_count += 1
                            score_counter[f'{a.quality_score}{a.information_score}'] += 1
                            existing_company = next((c for c in analysis if c.company == company), None)
                            if existing_company:
                                existing_company.analysis[model] = a
                            else:
                                analysis.append(CompanyAnalysis(company=company, analysis={model: a}))
                        progress.update(task, advance=1)

                async with asyncio.TaskGroup() as tg:
                    for company in companies:
                        tg.create_task(analyse_company_save(company))
    finally:
        analysis.sort(key=lambda a: a.score(), reverse=True)
        DAY_ANALYSIS_FILE.write_bytes(company_analysis_schema.dump_json(analysis, indent=2))

    print(f'Analyse complete, {analysis_count} companies analysed, scores:')
    for rating, count in sorted(score_counter.items()):
        print(f'{rating}: {count}')


if __name__ == '__main__':
    asyncio.run(main())
