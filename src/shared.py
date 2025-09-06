from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, TypeAdapter

ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / 'data'
FIND_COMPANIES_DIR = DATA_DIR / 'find-companies'
FIND_COMPANIES_DIR.mkdir(exist_ok=True, parents=True)
COMPANY_DATA_DIR = DATA_DIR / 'company-data'
COMPANY_DATA_DIR.mkdir(exist_ok=True, parents=True)
ASSETS_FILE = DATA_DIR / 'assets.parquet'
KNOWN_COMPANIES_FILE = DATA_DIR / 'known-companies.json'


Industry = Literal[
    'Technology & Software',
    'Financial Services',
    'Healthcare & Life Sciences',
    'Energy',
    'Mining & Natural Resources',
    'Real Estate',
    'Manufacturing',
    'Consumer & Retail',
    'Media & Entertainment',
    'Telecommunications',
    'Education',
    'Transportation & Logistics',
    'Defense & Security',
    'Travel & Hospitality',
    'Cannabis',
    'Nutrition & Wellness',
    'Robotics & Automation',
    'Business Services',
    'Investment Vehicles',
    'Specialized Services',
]


class Company(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    """Name of the company"""
    symbol: str
    """Ticker symbol of the company"""
    exchange: Literal['NYSE', 'AMEX', 'OTC', 'ARCA', 'NASDAQ', 'BATS']
    """Exchange where the company is listed"""
    industry: Industry
    """Industry the company belongs to.

    More details on each industry:
    Technology & Software: AI/ML, cloud communications, cybersecurity, SaaS, digital platforms, semiconductors
    Financial Services: Banking, fintech, payments, investment services, specialty finance, REITs
    Healthcare & Life Sciences: Biotechnology, pharmaceuticals, medical devices, healthcare IT, telehealth
    Energy: Oil & gas, renewable energy, energy technology, oilfield services
    Mining & Natural Resources: Metals, minerals, graphite, gold, water resources
    Real Estate: Real estate services, logistics, investment, development
    Manufacturing: Industrial manufacturing, additive manufacturing, electronics, automotive parts
    Consumer & Retail: Apparel, footwear, furniture, consumer electronics, e-commerce
    Media & Entertainment: Streaming, digital marketing, gaming/gambling platforms
    Telecommunications: Telecom equipment, communications infrastructure, networking
    Education: Education services, EdTech, training
    Transportation & Logistics: Third-party logistics, autonomous delivery, supply chain
    Defense & Security: Defense electronics, security products, surveillance systems
    Travel & Hospitality: Travel services, hospitality, tourism
    Cannabis: Cannabis retail, e-commerce, cultivation
    Nutrition & Wellness: Nutraceuticals, dietary supplements, wellness products
    Robotics & Automation: Industrial robotics, autonomous systems, automation software
    Business Services: Consulting, compliance software, business development
    Investment Vehicles: SPACs, BDCs, investment companies
    Specialized Services: CDMO services, research services, testing & certification
    """
    full_description: str
    """Full description of the company"""


companies_schema = TypeAdapter(list[Company])
