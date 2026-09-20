"""SQLite Engine 생성과 SQL 마이그레이션 적용.

마이그레이션은 `migrations/*.sql`을 파일명 오름차순으로 적용하고 적용 이력을
`schema_migrations` 테이블에 기록한다. 이미 적용된 스크립트는 건너뛴다.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

DEFAULT_MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def create_engine_for(db_path: Path) -> Engine:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{db_path}", future=True)


def apply_migrations(engine: Engine, migrations_dir: Path | None = None) -> list[str]:
    """미적용 마이그레이션을 순서대로 적용하고 적용된 id 목록을 반환한다."""
    directory = migrations_dir if migrations_dir is not None else DEFAULT_MIGRATIONS_DIR
    with engine.begin() as connection:
        connection.execute(
            text("CREATE TABLE IF NOT EXISTS schema_migrations (id TEXT PRIMARY KEY)")
        )
        applied = {
            row[0]
            for row in connection.execute(text("SELECT id FROM schema_migrations"))
        }

    newly_applied: list[str] = []
    for script in sorted(directory.glob("*.sql")):
        migration_id = script.stem
        if migration_id in applied:
            continue
        sql = script.read_text(encoding="utf-8")
        raw = engine.raw_connection()
        try:
            raw.executescript(sql)  # type: ignore[attr-defined]
            raw.execute(
                "INSERT INTO schema_migrations (id) VALUES (?)", (migration_id,)
            )
            raw.commit()
        except Exception:
            raw.rollback()
            raise
        finally:
            raw.close()
        newly_applied.append(migration_id)
    return newly_applied


def init_db(db_path: Path, migrations_dir: Path | None = None) -> Engine:
    engine = create_engine_for(db_path)
    apply_migrations(engine, migrations_dir)
    return engine


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, future=True, expire_on_commit=False)
