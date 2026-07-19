from collections.abc import Generator

from sqlalchemy import String, event, create_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    sessionmaker,
    with_loader_criteria,
)

from app.core.identity import DEFAULT_OWNER_ID, current_owner_id
from app.core.settings import get_settings


class Base(DeclarativeBase):
    pass


class OwnerScoped:
    owner_id: Mapped[str] = mapped_column(
        String(160),
        nullable=False,
        default=DEFAULT_OWNER_ID,
        index=True,
    )


@event.listens_for(Session, "do_orm_execute")
def apply_owner_scope(execute_state) -> None:
    owner_id = current_owner_id.get()
    if owner_id is None or execute_state.execution_options.get("skip_owner_scope"):
        return
    if execute_state.is_select or execute_state.is_update or execute_state.is_delete:
        execute_state.statement = execute_state.statement.options(
            with_loader_criteria(
                OwnerScoped,
                lambda record: record.owner_id == owner_id,
                include_aliases=True,
            )
        )


@event.listens_for(Session, "before_flush")
def assign_owner_scope(session: Session, _flush_context, _instances) -> None:
    owner_id = current_owner_id.get()
    if owner_id is None:
        return
    for record in session.new:
        if not isinstance(record, OwnerScoped):
            continue
        record_owner_id = getattr(record, "owner_id", None)
        if record_owner_id is None:
            record.owner_id = owner_id
        elif record_owner_id != owner_id:
            raise ValueError("Cannot create data for another owner")


settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
