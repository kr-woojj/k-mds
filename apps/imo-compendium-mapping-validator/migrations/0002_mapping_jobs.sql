-- 0002_mapping_jobs: 매핑 Job 저장소 (API 계층)
-- 기존 Registry snapshot 데이터는 변경하지 않는다 (구조 추가만).

CREATE TABLE IF NOT EXISTS mapping_job (
    seq                INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id             TEXT NOT NULL UNIQUE,
    source_dataset_id  TEXT NOT NULL,
    compendium_version TEXT NOT NULL REFERENCES compendium_version (version),
    created_at         TEXT NOT NULL,
    request_hash       TEXT NOT NULL,
    audit_id           TEXT NOT NULL,
    result_json        TEXT NOT NULL,
    review_json        TEXT
);

CREATE INDEX IF NOT EXISTS ix_mapping_job_job_id ON mapping_job (job_id);
