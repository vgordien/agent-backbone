# src/tools/banking.py
from langchain_core.tools import tool
from pydantic import BaseModel, Field
import random

class BalanceInput(BaseModel):
    account_id: str = Field(description="ID счёта, например: 'ACC-7742'")

class LoanInput(BaseModel):
    amount: float = Field(description="Сумма кредита в RUB")
    months: int = Field(description="Срок в месяцах")

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

# ⬇️ ОБЯЗАТЕЛЬНО: список инструментов для bind_tools() и tool_node
tools = [get_account_balance, calculate_loan_payment, fetch_policy_excerpt]