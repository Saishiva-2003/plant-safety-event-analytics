"""Incident list with filters."""


def list_incidents(ctx, plant=None, machine=None, rule=None, status=None, severity=None) -> dict:
    items = ctx.incidents
    if plant:
        items = [i for i in items if i["plant_id"] == plant]
    if machine:
        items = [i for i in items if i["machine_id"] == machine]
    if rule:
        items = [i for i in items if i["rule_code"] == rule]
    if status:
        items = [i for i in items if i["status"] == status]
    if severity:
        items = [i for i in items if i["severity"] == severity]
    items = sorted(items, key=lambda i: i["opened_ts"], reverse=True)
    return {"total": len(items), "items": [i | {"traceable": bool(i["trigger_alarm_id"] or i["linked_alarms"])}
                                           for i in items]}