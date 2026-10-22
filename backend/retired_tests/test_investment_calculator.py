"""Investment acceptance examples and financial boundaries, written before implementation."""
from copy import deepcopy
from datetime import date
from decimal import Decimal as D

import pytest
from pydantic import ValidationError

from app.property.schemas.investment import InvestmentInputs
from app.property.services.investment_calculator import calculate_investment, musgrave_preset, transfer_duty


def inputs(**changes):
    return InvestmentInputs.model_validate(musgrave_preset() | changes)


def test_cash_musgrave_matches_independently_checked_research():
    result = calculate_investment(inputs())
    assert result.initial_cash == D('1394200.00')
    assert result.annual_cash_flows[0].net_operating_income == D('75657.00')
    assert result.gross_yield_percent == D('10.222222')
    assert result.net_yield_percent == D('5.604222')
    assert abs(result.total_roi_percent - D('109.2645')) < D('.01')
    assert abs(result.annual_irr_percent - D('9.254668')) < D('.001')
    assert result.total_contributions == result.initial_cash
    assert result.currency == 'ZAR'
    assert result.before_personal_tax is True
    assert result.data_source == 'fictional_musgrave'


def test_financed_example_includes_topups_remaining_debt_and_interest():
    result = calculate_investment(inputs(financing={}))
    assert result.initial_cash == D('339200.00')
    assert abs(result.initial_monthly_bond_payment - D('10782.50')) <= D('.01')
    assert abs(result.total_topups - D('350574.72')) < D('2')
    assert abs(result.annual_cash_flows[-1].closing_debt - D('799088.68')) < D('2')
    assert abs(result.total_roi_percent - D('69.1669')) < D('.01')
    assert result.net_profit == result.total_distributions - result.total_contributions
    assert result.total_contributions == result.initial_cash + result.total_topups
    assert sum(row.principal for row in result.annual_cash_flows) + result.annual_cash_flows[-1].closing_debt == D('1080000')


def test_zero_interest_and_term_shorter_than_horizon_pay_off_exactly():
    result = calculate_investment(inputs(financing={'annual_interest_rate': '0', 'term_months': 12}))
    assert result.initial_monthly_bond_payment == D('90000')
    assert result.annual_cash_flows[0].closing_debt == 0
    assert result.annual_cash_flows[1].loan_payments == 0
    assert result.annual_cash_flows[1].loan_service_fees == 0
    assert sum(row.interest for row in result.annual_cash_flows) == 0


def test_rate_change_recalculates_payments_and_increases_funding_need():
    base = calculate_investment(inputs(financing={}))
    changed = calculate_investment(inputs(financing={'rate_changes': [{'start_month': 13, 'annual_rate': '.15'}]}))
    assert changed.annual_cash_flows[0] == base.annual_cash_flows[0]
    assert changed.annual_cash_flows[1].loan_payments > base.annual_cash_flows[1].loan_payments
    assert changed.total_topups > base.total_topups


def test_full_vacancy_retains_fixed_costs_and_no_management_fee():
    result = calculate_investment(inputs(vacancy_fraction='1'))
    first = result.annual_cash_flows[0]
    assert first.collected_rent == 0
    assert first.management == first.maintenance == 0
    assert first.net_operating_income == D('-38400')
    assert result.total_topups > 0


def test_special_levy_and_negative_appreciation_reduce_returns():
    base = calculate_investment(inputs())
    changed = calculate_investment(inputs(capital_growth='-.02', scheduled_costs=[{'year': 5, 'amount': '15000', 'kind': 'special_levy'}]))
    assert changed.annual_cash_flows[4].operating_cash == base.annual_cash_flows[4].operating_cash - D('15000')
    assert changed.total_roi_percent < base.total_roi_percent


@pytest.mark.parametrize('price,expected', [('1210000', '0'), ('1350000', '4200'), ('1663800', '13614'), ('2329300', '53544'), ('2994800', '106784'), ('13310000', '1241456'), ('14000000', '1331156')])
def test_transfer_duty_band_boundaries(price, expected):
    assert transfer_duty(D(price), date(2026, 10, 21)) == D(expected)


@pytest.mark.parametrize('changes', [
    {'purchase_price': 'NaN'}, {'purchase_price': 'Infinity'}, {'purchase_price': '0'},
    {'monthly_rent': '-1'}, {'vacancy_fraction': '1.01'}, {'horizon_years': 0},
    {'horizon_years': 41}, {'horizon_years': True}, {'currency': 'USD'},
    {'acquisition_date': '2027-04-01'}, {'acquisition_date': '2025-03-31'},
    {'scheduled_costs': [{'year': 11, 'amount': 1, 'kind': 'capex'}]},
    {'financing': {'rate_changes': [{'start_month': 1, 'annual_rate': '.1'}, {'start_month': 1, 'annual_rate': '.2'}]}},
    {'financing': {'deposit_fraction': '1'}}, {'financing': {'annual_interest_rate': 'NaN'}},
])
def test_rejects_invalid_or_unsupported_financial_inputs(changes):
    with pytest.raises(ValidationError):
        inputs(**changes)


def test_calculation_is_deterministic_and_does_not_mutate_inputs():
    payload = inputs(financing={})
    snapshot = deepcopy(payload.model_dump())
    assert calculate_investment(payload) == calculate_investment(payload)
    assert payload.model_dump() == snapshot


def test_non_unique_cash_flow_irr_is_explicitly_unavailable():
    # Interim very large capex followed by a sale creates multiple sign changes.
    result = calculate_investment(inputs(scheduled_costs=[{'year': 5, 'amount': '2000000', 'kind': 'capex'}]))
    assert result.annual_irr_percent is None
    assert result.irr_status == 'non_unique_or_unavailable'


def test_no_investor_cash_produces_undefined_return_instead_of_dividing_by_zero():
    result = calculate_investment(inputs(
        purchase_price='1000', transfer_legal_cost=0, initial_make_ready=0,
        monthly_rent='11500', exit_fixed_cost=0, financing={'deposit_fraction': '0', 'registration_cost': '0', 'annual_interest_rate': '0'},
    ))
    assert result.initial_cash == 0
    assert result.total_contributions == 0
    assert result.total_roi_percent is None
    assert result.year_one_cash_on_cash_percent is None
    assert result.annual_irr_percent is None


def test_negative_sale_equity_is_counted_as_additional_contribution():
    result = calculate_investment(inputs(capital_growth='-.50', financing={}))
    assert result.annual_cash_flows[-1].exit_equity < 0
    operating_topups = sum(max(-row.operating_cash, D(0)) for row in result.annual_cash_flows)
    assert result.total_topups == operating_topups - result.annual_cash_flows[-1].exit_equity
    assert result.net_profit == sum(row.total_cash for row in result.annual_cash_flows) - result.initial_cash
