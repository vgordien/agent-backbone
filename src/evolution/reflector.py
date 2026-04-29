def reflect_node(state):
    logs = state.get("adaptation_log", [])
    recent = state["messages"][-4:]
    issues = [m.content for m in recent if any(k in m.content for k in ["Ошибка", "не найдена", "не удалось"])]
    if issues:
        logs.append(f"Урок: Проверять данные перед вызовом. Пример: {issues[0][:40]}...")
    state["adaptation_log"] = logs[-3:]
    return {"adaptation_log": state["adaptation_log"]}