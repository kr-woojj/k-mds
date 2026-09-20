-- 0001_initial: Registry 초기 스키마
-- 이 DDL은 app/registry/models.py의 ORM과 1:1로 동기화한다.
-- Snapshot은 immutable이다: 어떤 마이그레이션도 기존 버전 데이터를
-- UPDATE/DELETE 하지 않는다 (신규 구조 추가만 허용).

CREATE TABLE IF NOT EXISTS compendium_version (
    version          TEXT    NOT NULL PRIMARY KEY,
    source_hash      TEXT    NOT NULL,
    source_format    TEXT    NOT NULL,
    element_count    INTEGER NOT NULL,
    occurrence_count INTEGER NOT NULL,
    loaded           BOOLEAN NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS data_element (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    version         TEXT NOT NULL REFERENCES compendium_version (version),
    imo_data_number TEXT NOT NULL,
    name            TEXT NOT NULL,
    definition      TEXT,
    format_spec     TEXT,
    code_list       TEXT,
    business_rule   TEXT,
    status          TEXT NOT NULL,
    CONSTRAINT uq_element_version_number UNIQUE (version, imo_data_number)
);

CREATE INDEX IF NOT EXISTS ix_data_element_version
    ON data_element (version);
CREATE INDEX IF NOT EXISTS ix_data_element_number
    ON data_element (imo_data_number);

CREATE TABLE IF NOT EXISTS refmodel_occurrence (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    version         TEXT NOT NULL REFERENCES compendium_version (version),
    imo_data_number TEXT NOT NULL,
    dataset_key     TEXT,
    refmodel_path   TEXT,
    CONSTRAINT uq_occurrence_identity
        UNIQUE (version, imo_data_number, dataset_key, refmodel_path)
);

CREATE INDEX IF NOT EXISTS ix_refmodel_occurrence_version
    ON refmodel_occurrence (version);

CREATE TABLE IF NOT EXISTS audit_event (
    seq         INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type  TEXT NOT NULL,
    version     TEXT NOT NULL,
    source_hash TEXT NOT NULL,
    detail      TEXT NOT NULL
);
