from src.tools.banking import calculate_loan_payment, fetch_policy_excerpt, convert_currency

def test_loan_calc():
    res = calculate_loan_payment.invoke({"amount": 1_000_000, "months": 12})
    assert res["monthly_payment"] > 0
    assert res["currency"] == "RUB"

def test_policy_fallback():
    res = fetch_policy_excerpt.invoke({"topic": "несуществующее"})
    assert "не найдена" in res.lower()

def test_convert_rub_to_usd():
    res = convert_currency.invoke({"amount": 1000.0, "from_currency": "RUB", "to_currency": "USD"})
    assert res["from"] == "RUB"
    assert res["to"] == "USD"
    assert res["amount"] == 1000.0
    assert abs(res["result"] - 11.0) < 0.5  # 1000 * 0.011 = 11.0

def test_convert_usd_to_eur():
    res = convert_currency.invoke({"amount": 100.0, "from_currency": "USD", "to_currency": "EUR"})
    assert res["from"] == "USD"
    assert res["to"] == "EUR"
    # 100 USD → RUB: 100/0.011 ≈ 9090.9 → EUR: 9090.9*0.010 ≈ 90.9
    assert abs(res["result"] - 90.9) < 1.0

def test_convert_same_currency():
    res = convert_currency.invoke({"amount": 500.0, "from_currency": "RUB", "to_currency": "RUB"})
    assert res["result"] == 500.0

def test_convert_unknown_currency():
    res = convert_currency.invoke({"amount": 100.0, "from_currency": "XYZ", "to_currency": "RUB"})
    assert "error" in res
    assert "XYZ" in res["error"]