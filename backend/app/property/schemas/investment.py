"""Finite, bounded assumptions and explicit financial output contracts."""
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Money = Annotated[Decimal, Field(ge=0, le=10_000_000_000, max_digits=13, decimal_places=2)]
Fraction = Annotated[Decimal, Field(ge=0, le=1, decimal_places=6)]
Growth = Annotated[Decimal, Field(ge=Decimal('-.50'), le=Decimal('.25'), decimal_places=6)]
PositiveId = Annotated[int, Field(gt=0, le=2147483647, strict=True)]


class StrictDTO(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False, from_attributes=True)


class RateChange(StrictDTO):
    start_month: int = Field(ge=1, le=480, strict=True)
    annual_rate: Fraction


class FinancingInputs(StrictDTO):
    deposit_fraction: Annotated[Decimal, Field(ge=0, lt=1, decimal_places=6)] = Decimal('.20')
    annual_interest_rate: Fraction = Decimal('.105')
    term_months: int = Field(default=240, ge=1, le=480, strict=True)
    registration_cost: Money = Decimal('25000')
    monthly_service_fee: Money = Decimal('69')
    rate_changes: list[RateChange] = Field(default_factory=list, max_length=40)

    @model_validator(mode='after')
    def valid_schedule(self):
        months = [step.start_month for step in self.rate_changes]
        if len(months) != len(set(months)) or any(month > self.term_months for month in months):
            raise ValueError('Rate changes require unique months within the loan term.')
        return self


class ScheduledCost(StrictDTO):
    year: int = Field(ge=1, le=40, strict=True)
    amount: Money
    kind: Literal['special_levy', 'capex']


class InvestmentInputs(StrictDTO):
    currency: Literal['ZAR'] = 'ZAR'
    data_source: Literal['user_assumptions', 'fictional_musgrave'] = 'user_assumptions'
    price_basis: Literal['assumed_purchase_price'] = 'assumed_purchase_price'
    acquisition_date: date
    purchase_price: Annotated[Decimal, Field(gt=0, le=10_000_000_000, max_digits=13, decimal_places=2)]
    # Duty base is explicit: price alone need not establish the statutory value.
    transfer_duty_value: Money | None = None
    transfer_legal_cost: Money = Decimal('0')
    initial_make_ready: Money = Decimal('0')
    monthly_rent: Money
    monthly_levy: Money = Decimal('0')
    monthly_rates: Money = Decimal('0')
    monthly_insurance: Money = Decimal('0')
    vacancy_fraction: Fraction = Decimal('.05')
    management_fraction: Fraction = Decimal('0')
    maintenance_fraction: Fraction = Decimal('0')
    rent_growth: Growth = Decimal('0')
    fixed_cost_growth: Growth = Decimal('0')
    capital_growth: Growth = Decimal('0')
    selling_cost_fraction: Fraction = Decimal('0')
    exit_fixed_cost: Money = Decimal('0')
    horizon_years: int = Field(default=10, ge=1, le=40, strict=True)
    financing: FinancingInputs | None = None
    scheduled_costs: list[ScheduledCost] = Field(default_factory=list, max_length=80)

    @model_validator(mode='after')
    def supported_inputs(self):
        if not date(2025, 4, 1) <= self.acquisition_date <= date(2027, 3, 31):
            raise ValueError('This version supports non-VAT resale acquisitions from 2025-04-01 through 2027-03-31 only.')
        if self.transfer_duty_value is not None and self.transfer_duty_value < self.purchase_price:
            raise ValueError('Transfer-duty value must be at least the purchase price.')
        if any(item.year > self.horizon_years for item in self.scheduled_costs):
            raise ValueError('Scheduled costs must fall within the holding period.')
        return self


class AnnualInvestmentCashFlow(StrictDTO):
    year: int
    scheduled_rent: Decimal
    vacancy_loss: Decimal
    collected_rent: Decimal
    fixed_costs: Decimal
    management: Decimal
    maintenance: Decimal
    net_operating_income: Decimal
    scheduled_capital_costs: Decimal
    interest: Decimal
    principal: Decimal
    loan_payments: Decimal
    loan_service_fees: Decimal
    operating_cash: Decimal
    closing_debt: Decimal
    sale_price: Decimal
    selling_costs: Decimal
    exit_equity: Decimal
    total_cash: Decimal


class InvestmentResult(StrictDTO):
    formula_version: str
    tax_schedule_version: str
    currency: Literal['ZAR'] = 'ZAR'
    data_source: Literal['user_assumptions', 'fictional_musgrave']
    before_personal_tax: Literal[True] = True
    nominal_amounts: Literal[True] = True
    timing: Literal['year_end_cash_flows_monthly_amortization'] = 'year_end_cash_flows_monthly_amortization'
    transfer_duty: Decimal
    acquisition_cost: Decimal
    initial_cash: Decimal
    initial_monthly_bond_payment: Decimal
    gross_yield_percent: Decimal
    net_yield_percent: Decimal
    net_yield_on_cost_percent: Decimal
    year_one_cash_on_cash_percent: Decimal | None
    total_topups: Decimal
    total_contributions: Decimal
    total_distributions: Decimal
    net_profit: Decimal
    total_roi_percent: Decimal | None
    annual_irr_percent: Decimal | None
    irr_status: Literal['available', 'non_unique_or_unavailable']
    warnings: list[str]
    annual_cash_flows: list[AnnualInvestmentCashFlow]


class InvestmentCalculationRequest(StrictDTO):
    estate_id: PositiveId
    property_id: PositiveId
    assumptions: InvestmentInputs


class InvestmentScenarioCreate(InvestmentCalculationRequest):
    name: str = Field(min_length=1, max_length=120, pattern=r'\S')
    revision_of: PositiveId | None = None

    @field_validator('name')
    @classmethod
    def printable_name(cls, value: str) -> str:
        if any(ord(character) < 32 for character in value):
            raise ValueError('Scenario names must not contain control characters.')
        return value.strip()


class InvestmentScenarioResponse(StrictDTO):
    scenario_id: int
    estate_id: int
    property_id: int
    name: str
    revision_of: int | None
    formula_version: str
    assumptions: InvestmentInputs
    result: InvestmentResult
    created_at: datetime
