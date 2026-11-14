"""
Analytics context: loads the joined alarm facts + state histories ONCE from MySQL, enriches them
(replay de-duplication, priority, ack status, floods, chatter) and caches the result in memory.
The dataset is static, so every API call reuses the same context (fast responses).
"""
import threading
import time

from sqlalchemy.orm import Session

from app.repositories import alarm_repo, event_repo, incident_repo, master_repo
from app.services import flood_service, nuisance_service, prioritization
from generator.events import StateIndex

_lock = threading.Lock()
_ctx = None


class AnalyticsContext:
    def __init__(self, db: Session):
        t0 = time.time()
        self.alarms = alarm_repo.fetch_alarm_facts(db)
        self.by_id = {a["alarm_event_id"]: a for a in self.alarms}
        self.state_events = event_repo.fetch_all_state_events(db)
        self.ilk_events = event_repo.fetch_all_interlock_events(db)
        self.state_index = StateIndex(self.state_events, "machine_id", "OFF")
        self.ilk_index = StateIndex(self.ilk_events, "interlock_id", "ENGAGED")
        self.interlocks_by_machine = {}
        for i in master_repo.list_interlocks(db):
            self.interlocks_by_machine.setdefault(i.machine_id, []).append(i.interlock_id)
        self.incidents = incident_repo.list_incidents(db)
        self.links = incident_repo.all_links(db)
        self.actions = [
            {c: getattr(a, c) for c in ("action_id", "incident_id", "action_type", "description", "owner_id",
                                        "created_ts", "due_ts", "status", "started_ts", "completed_ts",
                                        "verified_ts", "verified_by", "closed_ts")}
            for a in incident_repo.list_actions(db)]
        self.machines = master_repo.list_machines(db)

        # 1) replay de-duplication: same (machine, definition, PLC source_seq) -> keep first received
        first = {}
        for a in sorted(self.alarms, key=lambda x: (x["received_ts"], x["alarm_event_id"])):
            key = (a["machine_id"], a["alarm_def_id"], a["source_seq"])
            a["is_replay"] = key in first
            a["replay_of"] = first.get(key)
            first.setdefault(key, a["alarm_event_id"])
        self.unique_alarms = [a for a in self.alarms if not a["is_replay"]]
        # 2) priority + ack status   3) chatter / nuisance   4) floods (chatter excluded)
        prioritization.enrich(self.alarms, self.ilk_index, self.interlocks_by_machine)
        self.chatter_pairs = nuisance_service.detect_chatter(self.alarms)
        self.floods = flood_service.detect_floods(self.alarms)
        self.window_start = min(a["raised_ts"] for a in self.alarms)
        self.window_end = max(a["raised_ts"] for a in self.alarms)
        self.build_seconds = round(time.time() - t0, 2)


def get_context(db: Session) -> AnalyticsContext:
    global _ctx
    if _ctx is None:
        with _lock:
            if _ctx is None:
                _ctx = AnalyticsContext(db)
    return _ctx


def reset_context() -> None:
    global _ctx
    _ctx = None