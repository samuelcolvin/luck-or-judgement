import logfire
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import IsInstance, LLMJudge

from s05_research_companies import research_agent, research_company
from shared import KNOWN_COMPANIES_FILE, Company, companies_schema

logfire.configure(console=False, scrubbing=False)
logfire.instrument_pydantic_ai()

companies = companies_schema.validate_json(KNOWN_COMPANIES_FILE.read_bytes())
company_indexes = [1, 25, 50, 75, 100]
cases: list[Case[Company, str]] = []
for index in company_indexes:
    company = companies[index]
    case = Case(name=company.name, inputs=company)
    cases.append(case)

dataset = Dataset(
    cases=cases,
    evaluators=[
        IsInstance(type_name='str'),
        LLMJudge(
            rubric='Company report should be concise and contain as much information.',
            model='anthropic:claude-sonnet-4-0',
            score={'evaluation_name': 'informative', 'include_reason': True},
            assertion=False,
        ),
        LLMJudge(
            rubric='Any events mentioned should include their data.',
            model='anthropic:claude-sonnet-4-0',
            score={'evaluation_name': 'events-include-date', 'include_reason': True},
            assertion=False,
        ),
        LLMJudge(
            rubric='The report should not contain stock price data.',
            model='anthropic:claude-sonnet-4-0',
            score=False,
            assertion={'evaluation_name': 'no-stock-price', 'include_reason': True},
        ),
    ],
)

with research_agent.override(model='google-vertex:gemini-2.5-flash'):
    report = dataset.evaluate_sync(research_company, name='Gemini 2.5 flash')
    report.print(include_input=False, include_output=False)
