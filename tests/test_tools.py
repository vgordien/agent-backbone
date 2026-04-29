from src.tools.banking import calculate_loan_payment, fetch_policy_excerpt

def test_loan_calc():
    res = calculate_loan_payment.invoke({"amount": 1_000_000, "months": 12})
    assert res["monthly_payment"] > 0
    assert res["currency"] == "RUB"

def test_policy_fallback():
    res = fetch_policy_excerpt.invoke({"topic": "несуществующее"})
    assert "не найдена" in res.lower()