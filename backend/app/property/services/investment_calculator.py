"""Deterministic financial service functions; no model training or network calls.

Money rounds to cents HALF_UP per monthly payment/interest and annual cash item.
Percentages are six decimal places; IRR uses annual end-of-year cash flows.
"""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP, localcontext

from app.property.schemas.investment import AnnualInvestmentCashFlow, InvestmentInputs, InvestmentResult

FORMULA_VERSION = 'investment-v1.0'
TAX_SCHEDULE_VERSION = 'ZA-transfer-duty-2025-04-01-2027-03-31'
D = Decimal


def money(value: Decimal) -> Decimal:
    return value.quantize(D('.01'), rounding=ROUND_HALF_UP)


def percent(numerator: Decimal, denominator: Decimal) -> Decimal:
    return (numerator / denominator * 100).quantize(D('.000001'), rounding=ROUND_HALF_UP)


def transfer_duty(value: Decimal, acquired: date) -> Decimal:
    if not date(2025, 4, 1) <= acquired <= date(2027, 3, 31):
        raise ValueError('Unsupported transfer-duty effective date.')
    if not value.is_finite() or value < 0:
        raise ValueError('Transfer-duty value must be finite and non-negative.')
    bands = [(1210000, 0, 0), (1663800, 1210000, '.03'),
             (2329300, 1663800, '.06'), (2994800, 2329300, '.08'),
             (13310000, 2994800, '.11')]
    bases = [0, 0, 13614, 53544, 106784]
    for (ceiling, lower, rate), base in zip(bands, bases):
        if value <= ceiling:
            return money(D(base) + (value - D(lower)) * D(rate))
    return money(D('1241456') + (value - D('13310000')) * D('.13'))


def _payment(balance: Decimal, rate: Decimal, months: int) -> Decimal:
    return money(balance / months if rate == 0 else balance * rate / (1 - (1 + rate) ** -months))


def _annual_irr(flows: list[Decimal]) -> Decimal | None:
    nonzero = [value for value in flows if value != 0]
    changes = sum((a < 0) != (b < 0) for a, b in zip(nonzero, nonzero[1:]))
    # Multiple sign changes can have multiple IRRs. Do not silently select one.
    if changes != 1 or flows[0] >= 0:
        return None

    def npv(rate):
        return sum(value / (1 + rate) ** year for year, value in enumerate(flows))

    low, high = D('-.9999'), D('1')
    while npv(high) > 0 and high < D('1048576'):
        high *= 2
    if npv(low) < 0 or npv(high) > 0:
        return None
    for _ in range(140):
        middle = (low + high) / 2
        if npv(middle) > 0:
            low = middle
        else:
            high = middle
    return percent((low + high) / 2, D(1))


def calculate_investment(inputs: InvestmentInputs) -> InvestmentResult:
    """Calculate from validated assumptions, without changing or persisting them."""
    with localcontext() as context:
        context.prec = 50
        return _calculate(inputs)


def _calculate(a: InvestmentInputs) -> InvestmentResult:
    duty = transfer_duty(a.transfer_duty_value or a.purchase_price, a.acquisition_date)
    acquisition = money(a.purchase_price + duty + a.transfer_legal_cost + a.initial_make_ready)
    loan = a.financing
    balance = money(a.purchase_price * (1 - loan.deposit_fraction)) if loan else D('0.00')
    initial = money(acquisition - balance + (loan.registration_cost if loan else 0))
    rate = loan.annual_interest_rate / 12 if loan else D(0)
    payment = _payment(balance, rate, loan.term_months) if loan else D('0.00')
    changes = {item.start_month: item.annual_rate / 12 for item in loan.rate_changes} if loan else {}
    initial_payment = _payment(balance, changes.get(1, rate), loan.term_months) if loan else D('0.00')
    rows = []
    flows = [-initial]
    for year in range(1, a.horizon_years + 1):
        gross = money(a.monthly_rent * 12 * (1 + a.rent_growth) ** (year - 1))
        vacancy = money(gross * a.vacancy_fraction)
        collected = gross - vacancy
        fixed = money((a.monthly_levy + a.monthly_rates + a.monthly_insurance) * 12 * (1 + a.fixed_cost_growth) ** (year - 1))
        management = money(collected * a.management_fraction)
        maintenance = money(collected * a.maintenance_fraction)
        noi = collected - fixed - management - maintenance
        capital = sum((item.amount for item in a.scheduled_costs if item.year == year), D('0.00'))
        interest = principal = payments = fees = D('0.00')
        for month in range((year - 1) * 12 + 1, year * 12 + 1):
            if not loan or balance <= 0 or month > loan.term_months:
                continue
            if month in changes:
                rate = changes[month]
                payment = _payment(balance, rate, loan.term_months - month + 1)
            charged = money(balance * rate)
            paid = balance + charged if month == loan.term_months else min(payment, balance + charged)
            repaid = paid - charged
            balance = money(balance - repaid)
            interest += charged
            principal += repaid
            payments += paid
            fees += loan.monthly_service_fee
        operating = noi - capital - payments - fees
        sale = selling = exit_equity = D('0.00')
        if year == a.horizon_years:
            sale = money(a.purchase_price * (1 + a.capital_growth) ** year)
            selling = money(sale * a.selling_cost_fraction) + a.exit_fixed_cost
            exit_equity = sale - selling - balance
        total = operating + exit_equity
        flows.append(total)
        rows.append(AnnualInvestmentCashFlow(
            year=year, scheduled_rent=gross, vacancy_loss=vacancy, collected_rent=collected,
            fixed_costs=fixed, management=management, maintenance=maintenance, net_operating_income=noi,
            scheduled_capital_costs=capital, interest=interest, principal=principal,
            loan_payments=payments, loan_service_fees=fees, operating_cash=operating,
            closing_debt=balance, sale_price=sale, selling_costs=selling, exit_equity=exit_equity, total_cash=total,
        ))
    topups = sum((max(-row.operating_cash, D(0)) for row in rows), D('0.00'))
    # A shortfall on sale is also an investor contribution, not a distribution.
    topups += max(-rows[-1].exit_equity, D(0))
    contributions = initial + topups
    distributions = sum((max(row.operating_cash, D(0)) for row in rows), D('0.00')) + max(rows[-1].exit_equity, D(0))
    profit = distributions - contributions
    irr = _annual_irr(flows)
    warnings = ['Nominal scenario before personal income tax and capital gains tax; no reinvestment.',
                'Purchase price and growth assumptions are not a calculated valuation or a guaranteed return.',
                'Standard non-VAT resale transfer duty only; transaction and insurance fees are user assumptions.']
    if a.data_source == 'fictional_musgrave':
        warnings.append('Fictional Musgrave preset: not observed market data or a trained prediction.')
    if topups:
        warnings.append('Additional investor cash is required; see total_topups and annual cash flows.')
    if irr is None:
        warnings.append('Annual IRR is unavailable or potentially non-unique for this cash-flow pattern.')
    if initial == 0 or contributions == 0:
        warnings.append('A return percentage with a zero cash denominator is undefined and is returned as null.')
    return InvestmentResult(
        formula_version=FORMULA_VERSION, tax_schedule_version=TAX_SCHEDULE_VERSION,
        data_source=a.data_source, transfer_duty=duty, acquisition_cost=acquisition,
        initial_cash=initial, initial_monthly_bond_payment=initial_payment,
        gross_yield_percent=percent(rows[0].scheduled_rent, a.purchase_price),
        net_yield_percent=percent(rows[0].net_operating_income, a.purchase_price),
        net_yield_on_cost_percent=percent(rows[0].net_operating_income, acquisition),
        year_one_cash_on_cash_percent=percent(rows[0].operating_cash, initial) if initial else None,
        total_topups=money(topups), total_contributions=money(contributions), total_distributions=money(distributions),
        net_profit=money(profit), total_roi_percent=percent(profit, contributions) if contributions else None,
        annual_irr_percent=irr, irr_status='available' if irr is not None else 'non_unique_or_unavailable',
        warnings=warnings, annual_cash_flows=rows,
    )


def musgrave_preset() -> dict:
    """Return a fresh explicit fictional dataset; do not seed or invent a property."""
    return dict(data_source='fictional_musgrave', acquisition_date='2026-10-21',
                purchase_price='1350000', transfer_legal_cost='30000', initial_make_ready='10000',
                monthly_rent='11500', monthly_levy='2000', monthly_rates='1000', monthly_insurance='200',
                vacancy_fraction='.05', management_fraction='.08', maintenance_fraction='.05',
                rent_growth='.05', fixed_cost_growth='.05', capital_growth='.045',
                selling_cost_fraction='.0575', exit_fixed_cost='10000', horizon_years=10)
