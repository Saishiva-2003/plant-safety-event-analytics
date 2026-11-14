-- =====================================================================
--  Plant Safety Event Analytics  -  Tier 3 (MySQL 8) schema
--  Database : safety_db            Charset : utf8mb4
--  Load order: master tables -> event tables -> bridge tables -> ground truth
--  History is append-only: state changes are rows in *_state_event tables.
--  Rule-level violations (e.g. ack before alarm) are NOT blocked by constraints
--  on purpose: labelled anomalies must be loadable so they can be detected.
-- =====================================================================
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS ground_truth, corrective_action, incident_alarm, incident, acknowledgement,
    alarm_event, interlock_state_event, machine_state_event, operator_shift, staff,
    alarm_definition, interlock, machine_zone, machine, safety_zone, plant;
SET FOREIGN_KEY_CHECKS = 1;

-- ----------------------------- MASTER DATA ---------------------------
CREATE TABLE plant (
    plant_id      VARCHAR(8)   NOT NULL,
    plant_name    VARCHAR(100) NOT NULL,
    city          VARCHAR(60)  NOT NULL,
    state         VARCHAR(60)  NOT NULL,
    country       CHAR(2)      NOT NULL,
    timezone      VARCHAR(40)  NOT NULL,
    status        VARCHAR(12)  NOT NULL,
    opened_date   DATE         NOT NULL,
    PRIMARY KEY (plant_id),
    CONSTRAINT ck_plant_status CHECK (status IN ('ACTIVE','INACTIVE'))
) ENGINE=InnoDB;

CREATE TABLE safety_zone (
    zone_id        VARCHAR(16)  NOT NULL,           -- SAFE-P01-001
    plant_id       VARCHAR(8)   NOT NULL,
    zone_name      VARCHAR(100) NOT NULL,
    zone_type      VARCHAR(20)  NOT NULL,
    hazard_level   TINYINT      NOT NULL,           -- 1 (low) .. 5 (high)
    effective_from DATE         NOT NULL,
    effective_to   DATE         NULL,
    status         VARCHAR(12)  NOT NULL,
    PRIMARY KEY (zone_id),
    CONSTRAINT fk_zone_plant FOREIGN KEY (plant_id) REFERENCES plant (plant_id),
    CONSTRAINT ck_zone_hazard CHECK (hazard_level BETWEEN 1 AND 5)
) ENGINE=InnoDB;

CREATE TABLE machine (
    machine_id        VARCHAR(12)  NOT NULL,        -- P01-M001
    plant_id          VARCHAR(8)   NOT NULL,
    machine_name      VARCHAR(100) NOT NULL,
    machine_type      VARCHAR(20)  NOT NULL,
    manufacturer      VARCHAR(40)  NOT NULL,
    criticality       CHAR(1)      NOT NULL,        -- A / B / C
    commissioned_date DATE         NOT NULL,
    status            VARCHAR(12)  NOT NULL,
    PRIMARY KEY (machine_id),
    CONSTRAINT fk_machine_plant FOREIGN KEY (plant_id) REFERENCES plant (plant_id),
    CONSTRAINT ck_machine_crit CHECK (criticality IN ('A','B','C'))
) ENGINE=InnoDB;

-- N:M bridge machine <-> safety_zone (one primary zone per machine)
CREATE TABLE machine_zone (
    machine_id     VARCHAR(12) NOT NULL,
    zone_id        VARCHAR(16) NOT NULL,
    is_primary     TINYINT(1)  NOT NULL,
    effective_from DATE        NOT NULL,
    effective_to   DATE        NULL,
    PRIMARY KEY (machine_id, zone_id),
    KEY ix_mz_zone (zone_id),
    CONSTRAINT fk_mz_machine FOREIGN KEY (machine_id) REFERENCES machine (machine_id),
    CONSTRAINT fk_mz_zone    FOREIGN KEY (zone_id)    REFERENCES safety_zone (zone_id)
) ENGINE=InnoDB;

CREATE TABLE interlock (
    interlock_id   VARCHAR(20)  NOT NULL,           -- ILK-P01-M001-01
    machine_id     VARCHAR(12)  NOT NULL,
    zone_id        VARCHAR(16)  NOT NULL,
    interlock_type VARCHAR(16)  NOT NULL,
    description    VARCHAR(150) NOT NULL,
    sil_level      TINYINT      NOT NULL,
    initial_state  VARCHAR(10)  NOT NULL,
    installed_date DATE         NOT NULL,
    status         VARCHAR(12)  NOT NULL,
    PRIMARY KEY (interlock_id),
    KEY ix_ilk_machine (machine_id),
    CONSTRAINT fk_ilk_machine FOREIGN KEY (machine_id) REFERENCES machine (machine_id),
    CONSTRAINT fk_ilk_zone    FOREIGN KEY (zone_id)    REFERENCES safety_zone (zone_id),
    CONSTRAINT ck_ilk_type CHECK (interlock_type IN ('GUARD_DOOR','LIGHT_CURTAIN','E_STOP','PRESSURE'))
) ENGINE=InnoDB;

CREATE TABLE alarm_definition (
    alarm_def_id   VARCHAR(8)   NOT NULL,           -- AD-0001
    alarm_code     VARCHAR(20)  NOT NULL,
    base_code      VARCHAR(16)  NOT NULL,
    alarm_name     VARCHAR(150) NOT NULL,
    category       VARCHAR(12)  NOT NULL,
    severity       VARCHAR(10)  NOT NULL,
    machine_type   VARCHAR(20)  NOT NULL,
    interlock_type VARCHAR(16)  NULL,
    ack_required   TINYINT(1)   NOT NULL,
    ack_sla_sec    INT          NOT NULL,           -- seconds
    effective_from DATE         NOT NULL,
    status         VARCHAR(12)  NOT NULL,
    PRIMARY KEY (alarm_def_id),
    UNIQUE KEY uq_alarm_code (alarm_code),
    CONSTRAINT ck_ad_sev CHECK (severity IN ('CRITICAL','HIGH','MEDIUM','LOW')),
    CONSTRAINT ck_ad_cat CHECK (category IN ('SAFETY','PROCESS','EQUIPMENT','SYSTEM'))
) ENGINE=InnoDB;

CREATE TABLE staff (
    staff_id     VARCHAR(12)  NOT NULL,             -- OP-P01-01 / QE-P01-01
    plant_id     VARCHAR(8)   NOT NULL,
    role         VARCHAR(10)  NOT NULL,
    display_name VARCHAR(60)  NOT NULL,
    PRIMARY KEY (staff_id),
    CONSTRAINT fk_staff_plant FOREIGN KEY (plant_id) REFERENCES plant (plant_id),
    CONSTRAINT ck_staff_role CHECK (role IN ('OPERATOR','ENGINEER'))
) ENGINE=InnoDB;

CREATE TABLE operator_shift (
    shift_id    VARCHAR(24) NOT NULL,               -- SHF-P01-20261001-A
    plant_id    VARCHAR(8)  NOT NULL,
    shift_code  CHAR(1)     NOT NULL,
    shift_date  DATE        NOT NULL,
    start_ts    DATETIME(3) NOT NULL,
    end_ts      DATETIME(3) NOT NULL,
    operator_id VARCHAR(12) NOT NULL,
    PRIMARY KEY (shift_id),
    KEY ix_shift_plant_time (plant_id, start_ts),
    CONSTRAINT fk_shift_plant    FOREIGN KEY (plant_id)    REFERENCES plant (plant_id),
    CONSTRAINT fk_shift_operator FOREIGN KEY (operator_id) REFERENCES staff (staff_id),
    CONSTRAINT ck_shift_code CHECK (shift_code IN ('A','B','C'))
) ENGINE=InnoDB;

-- ----------------------------- EVENT HISTORY -------------------------
CREATE TABLE machine_state_event (
    state_event_id VARCHAR(24)  NOT NULL,           -- MSE-P01-M001-000001
    machine_id     VARCHAR(12)  NOT NULL,
    event_ts       DATETIME(3)  NOT NULL,
    from_state     VARCHAR(12)  NOT NULL,
    to_state       VARCHAR(12)  NOT NULL,
    reason         VARCHAR(100) NOT NULL,
    PRIMARY KEY (state_event_id),
    KEY ix_mse_machine_time (machine_id, event_ts),
    CONSTRAINT fk_mse_machine FOREIGN KEY (machine_id) REFERENCES machine (machine_id)
) ENGINE=InnoDB;

CREATE TABLE interlock_state_event (
    interlock_event_id     VARCHAR(32)  NOT NULL,   -- ISE-ILK-P01-M001-01-0001
    interlock_id           VARCHAR(20)  NOT NULL,
    event_ts               DATETIME(3)  NOT NULL,
    from_state             VARCHAR(10)  NOT NULL,
    to_state               VARCHAR(10)  NOT NULL,
    machine_state_snapshot VARCHAR(12)  NOT NULL,
    reason                 VARCHAR(100) NOT NULL,
    actor                  VARCHAR(12)  NOT NULL,
    PRIMARY KEY (interlock_event_id),
    KEY ix_ise_ilk_time (interlock_id, event_ts),
    CONSTRAINT fk_ise_ilk FOREIGN KEY (interlock_id) REFERENCES interlock (interlock_id)
) ENGINE=InnoDB;

CREATE TABLE alarm_event (
    alarm_event_id VARCHAR(24) NOT NULL,            -- ALM-P01-M001-000001
    machine_id     VARCHAR(12) NOT NULL,
    alarm_def_id   VARCHAR(8)  NOT NULL,
    shift_id       VARCHAR(24) NOT NULL,
    interlock_id   VARCHAR(20) NULL,
    raised_ts      DATETIME(3) NOT NULL,
    cleared_ts     DATETIME(3) NULL,
    received_ts    DATETIME(3) NOT NULL,
    source_seq     INT         NOT NULL,            -- PLC sequence number
    machine_state  VARCHAR(12) NOT NULL,            -- snapshot at raise
    PRIMARY KEY (alarm_event_id),
    KEY ix_ae_raised (raised_ts),
    KEY ix_ae_machine_time (machine_id, raised_ts),
    KEY ix_ae_def (alarm_def_id),
    KEY ix_ae_shift (shift_id),
    KEY ix_ae_seq (machine_id, alarm_def_id, source_seq),
    CONSTRAINT fk_ae_machine FOREIGN KEY (machine_id)   REFERENCES machine (machine_id),
    CONSTRAINT fk_ae_def     FOREIGN KEY (alarm_def_id) REFERENCES alarm_definition (alarm_def_id),
    CONSTRAINT fk_ae_shift   FOREIGN KEY (shift_id)     REFERENCES operator_shift (shift_id),
    CONSTRAINT fk_ae_ilk     FOREIGN KEY (interlock_id) REFERENCES interlock (interlock_id)
) ENGINE=InnoDB;

CREATE TABLE acknowledgement (
    ack_id         VARCHAR(32)   NOT NULL,          -- ACK-<alarm-id>-01
    alarm_event_id VARCHAR(24)   NOT NULL,
    shift_id       VARCHAR(24)   NOT NULL,
    operator_id    VARCHAR(12)   NOT NULL,
    ack_ts         DATETIME(3)   NOT NULL,
    response_sec   DECIMAL(12,3) NOT NULL,          -- derived: ack_ts - raised_ts (seconds)
    ack_method     VARCHAR(8)    NOT NULL,
    PRIMARY KEY (ack_id),
    UNIQUE KEY uq_ack_alarm (alarm_event_id),       -- 1:1 alarm -> acknowledgement (optional)
    KEY ix_ack_shift (shift_id),
    CONSTRAINT fk_ack_alarm    FOREIGN KEY (alarm_event_id) REFERENCES alarm_event (alarm_event_id),
    CONSTRAINT fk_ack_shift    FOREIGN KEY (shift_id)       REFERENCES operator_shift (shift_id),
    CONSTRAINT fk_ack_operator FOREIGN KEY (operator_id)    REFERENCES staff (staff_id)
) ENGINE=InnoDB;

CREATE TABLE incident (
    incident_id      VARCHAR(16)  NOT NULL,         -- INC-2026-000001
    machine_id       VARCHAR(12)  NOT NULL,
    zone_id          VARCHAR(16)  NOT NULL,
    trigger_alarm_id VARCHAR(24)  NULL,             -- optional (manual reports)
    rule_code        VARCHAR(24)  NOT NULL,
    severity         VARCHAR(10)  NOT NULL,
    opened_ts        DATETIME(3)  NOT NULL,
    status           VARCHAR(16)  NOT NULL,
    closed_ts        DATETIME(3)  NULL,
    reported_by      VARCHAR(12)  NOT NULL,         -- staff_id or SYSTEM
    description      VARCHAR(200) NOT NULL,
    PRIMARY KEY (incident_id),
    KEY ix_inc_machine_time (machine_id, opened_ts),
    CONSTRAINT fk_inc_machine FOREIGN KEY (machine_id)       REFERENCES machine (machine_id),
    CONSTRAINT fk_inc_zone    FOREIGN KEY (zone_id)          REFERENCES safety_zone (zone_id),
    CONSTRAINT fk_inc_trigger FOREIGN KEY (trigger_alarm_id) REFERENCES alarm_event (alarm_event_id),
    CONSTRAINT ck_inc_status CHECK (status IN ('OPEN','INVESTIGATING','ACTION_PENDING','CLOSED'))
) ENGINE=InnoDB;

-- N:M bridge incident <-> alarm_event (TRIGGER / CONTEXT)
CREATE TABLE incident_alarm (
    incident_id    VARCHAR(16) NOT NULL,
    alarm_event_id VARCHAR(24) NOT NULL,
    link_role      VARCHAR(8)  NOT NULL,
    PRIMARY KEY (incident_id, alarm_event_id),
    KEY ix_ia_alarm (alarm_event_id),
    CONSTRAINT fk_ia_incident FOREIGN KEY (incident_id)    REFERENCES incident (incident_id),
    CONSTRAINT fk_ia_alarm    FOREIGN KEY (alarm_event_id) REFERENCES alarm_event (alarm_event_id),
    CONSTRAINT ck_ia_role CHECK (link_role IN ('TRIGGER','CONTEXT'))
) ENGINE=InnoDB;

CREATE TABLE corrective_action (
    action_id    VARCHAR(24)  NOT NULL,             -- ACT-INC-2026-000001-01
    incident_id  VARCHAR(16)  NOT NULL,
    action_type  VARCHAR(16)  NOT NULL,
    description  VARCHAR(150) NOT NULL,
    owner_id     VARCHAR(12)  NOT NULL,
    created_ts   DATETIME(3)  NOT NULL,
    due_ts       DATETIME(3)  NOT NULL,
    status       VARCHAR(24)  NOT NULL,
    started_ts   DATETIME(3)  NULL,
    completed_ts DATETIME(3)  NULL,
    verified_ts  DATETIME(3)  NULL,
    verified_by  VARCHAR(12)  NULL,
    closed_ts    DATETIME(3)  NULL,
    PRIMARY KEY (action_id),
    KEY ix_act_incident (incident_id),
    CONSTRAINT fk_act_incident FOREIGN KEY (incident_id) REFERENCES incident (incident_id),
    CONSTRAINT fk_act_owner    FOREIGN KEY (owner_id)    REFERENCES staff (staff_id),
    CONSTRAINT fk_act_verifier FOREIGN KEY (verified_by) REFERENCES staff (staff_id),
    CONSTRAINT ck_act_status CHECK (status IN ('OPEN','IN_PROGRESS','PENDING_VERIFICATION','VERIFIED','CLOSED'))
) ENGINE=InnoDB;

-- ------------------- GROUND TRUTH (evaluation only) -------------------
-- Never joined by the detection services; used only by /api/quality/evaluation.
CREATE TABLE ground_truth (
    gt_id             VARCHAR(10)  NOT NULL,
    category          VARCHAR(10)  NOT NULL,        -- ANOMALY / PATTERN
    issue_type        VARCHAR(32)  NOT NULL,
    record_type       VARCHAR(24)  NOT NULL,
    record_id         VARCHAR(32)  NOT NULL,
    related_id        VARCHAR(32)  NULL,
    event_ts          DATETIME(3)  NULL,
    detail            VARCHAR(400) NULL,
    expected_decision VARCHAR(40)  NOT NULL,
    PRIMARY KEY (gt_id),
    KEY ix_gt_issue (issue_type)
) ENGINE=InnoDB;