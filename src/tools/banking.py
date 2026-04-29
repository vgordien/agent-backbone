# src/tools/banking.py
from langchain_core.tools import tool
from pydantic import BaseModel, Field
import random

class BalanceInput(BaseModel):
    account_id: str = Field(description="ID счёта, например: 'ACC-7742'")

class LoanInput(BaseModel):
    amount: float = Field(description="Сумма кредита в RUB")
    months: int = Field(description="Срок в месяцах")

class ConvertCurrencyInput(BaseModel):
    amount: float = Field(description="Сумма для конвертации")
    from_currency: str = Field(description="Исходная валюта: RUB, USD, EUR, CNY")
    to_currency: str = Field(description="Целевая валюта: RUB, USD, EUR, CNY")

@tool(args_schema=BalanceInput)
def get_account_balance(account_id: str) -> dict:
    """Возвращает текущий баланс и статус счёта."""
    return {"account_id": account_id, "balance": round(random.uniform(15000, 420000), 2), "status": "active"}

@tool(args_schema=LoanInput)
def calculate_loan_payment(amount: float, months: int) -> dict:
    """Рассчитывает ежемесячный платёж по ставке 14.5% годовых."""
    rate = 0.145 / 12
    payment = (amount * rate) / (1 - (1 + rate) ** -months)
    return {"amount": amount, "months": months, "monthly_payment": round(payment, 2), "currency": "RUB"}

@tool
def fetch_policy_excerpt(topic: str) -> str:
    """Ищет выдержку из банковских политик по ключевому слову."""
    policies = {
        "commission": "Комиссия за переводы внутри банка — 0%, на сторонние карты — 1.5%.",
        "mortgage": "Ипотека от 12% годовых, первоначальный взнос от 15%."
    }
    return policies.get(topic.lower(), "Информация по запросу не найдена. Уточните тему.")

@tool(args_schema=ConvertCurrencyInput)
def convert_currency(amount: float, from_currency: str, to_currency: str) -> dict:
    """Конвертирует сумму между валютами по фиксированному курсу."""
    rates = {"RUB": 1.0, "USD": 0.011, "EUR": 0.010, "CNY": 0.079}
    fc = from_currency.upper()
    tc = to_currency.upper()
    if fc not in rates:
        return {"error": f"Неизвестная валюта: {fc}"}
    if tc not in rates:
        return {"error": f"Неизвестная валюта: {tc}"}
    converted = amount / rates[fc] * rates[tc]
    return {"amount": amount, "from": fc, "result": round(converted, 2), "to": tc}

# ⬇️ ОБЯЗАТЕЛЬНО: список инструментов для bind_tools() и tool_node
tools = [get_account_balance, calculate_loan_payment, fetch_policy_excerpt, convert_currency]