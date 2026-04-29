# Дизайн: инструмент конвертации валют

**Дата:** 2026-04-29  
**Ветка:** tools  
**Статус:** Approved

## Цель

Добавить инструмент `convert_currency` в существующий банковский граф, чтобы продемонстрировать вызов инструмента с несколькими аргументами через GigaChat.

## Изменяемые файлы

| Файл | Изменение |
|---|---|
| `src/tools/banking.py` | Новый Pydantic-класс `ConvertCurrencyInput`, функция `convert_currency`, добавление в список `tools` |
| `tests/test_tools.py` | Новые тесты для `convert_currency` |

## Инструмент

```python
class ConvertCurrencyInput(BaseModel):
    amount: float = Field(description="Сумма для конвертации")
    from_currency: str = Field(description="Исходная валюта: RUB, USD, EUR, CNY")
    to_currency: str = Field(description="Целевая валюта: RUB, USD, EUR, CNY")

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
```

Обновлённый список инструментов:
```python
tools = [get_account_balance, calculate_loan_payment, fetch_policy_excerpt, convert_currency]
```

## Курсы (фиксированные, RUB как база)

| Валюта | Курс к RUB |
|---|---|
| RUB | 1.0 |
| USD | 0.011 (≈91 RUB) |
| EUR | 0.010 (≈100 RUB) |
| CNY | 0.079 (≈13 RUB) |

## Тесты

- Конвертация RUB → USD
- Конвертация USD → EUR (кросс-курс через RUB)
- Конвертация одинаковых валют (RUB → RUB)
- Неизвестная валюта → возвращает `{"error": "..."}`

## Ключевые решения

- Граф, промпты и маршрутизация не меняются — `bind_tools` подхватит новый инструмент автоматически
- Ошибка неизвестной валюты возвращается как dict (а не исключение), чтобы GigaChat мог объяснить её пользователю
- Валюты нормализуются через `.upper()` — GigaChat может прислать "usd" или "USD"
