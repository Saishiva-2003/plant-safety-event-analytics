"""Alarm explorer: filter, sort (priority first = severe alarms prioritised) and paginate."""
ALARM_FIELDS = ["alarm_event_id", "plant_id", "machine_id", "machine_name", "alarm_def_id", "alarm_code", "alarm_name",
                "category", "severity", "raised_ts", "cleared_ts", "machine_state", "interlock_state_at_raise",
                "zone_id", "hazard_level", "repeat_24h", "priority_score", "ack_status", "response_sec",
                "ack_operator_id", "shift_id", "flood_id", "chatter", "is_replay"]


def list_alarms(ctx, plant=None, machine=None, severity=None, category=None, ack_status=None, flood_only=False,
                include_replays=False, search=None, date_from=None, date_to=None, sort="priority",
                page=1, size=50) -> dict:
    items = ctx.alarms if include_replays else ctx.unique_alarms
    if plant:
        items = [a for a in items if a["plant_id"] == plant]
    if machine:
        items = [a for a in items if a["machine_id"] == machine]
    if severity:
        items = [a for a in items if a["severity"] == severity]
    if category:
        items = [a for a in items if a["category"] == category]
    if ack_status:
        items = [a for a in items if a["ack_status"] == ack_status]
    if flood_only:
        items = [a for a in items if a["flood_id"]]
    if date_from:
        items = [a for a in items if a["raised_ts"].date() >= date_from]
    if date_to:
        items = [a for a in items if a["raised_ts"].date() <= date_to]
    if search:
        s = search.lower()
        items = [a for a in items if s in a["alarm_event_id"].lower() or s in a["alarm_code"].lower()
                 or s in a["alarm_name"].lower()]
    if sort == "priority":
        items = sorted(items, key=lambda a: (-a["priority_score"], a["severity_rank"], a["raised_ts"]))
    elif sort == "oldest":
        items = sorted(items, key=lambda a: a["raised_ts"])
    else:
        items = sorted(items, key=lambda a: a["raised_ts"], reverse=True)
    total = len(items)
    page_items = items[(page - 1) * size: page * size]
    return {"total": total, "page": page, "size": size, "pages": (total + size - 1) // size,
            "items": [{k: a.get(k) for k in ALARM_FIELDS} for a in page_items]}