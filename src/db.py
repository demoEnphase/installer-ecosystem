"""SQLAlchemy models and CRUD helpers for overrides, comments, messages, snapshots."""
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, Float
from sqlalchemy.orm import DeclarativeBase, Session
import streamlit as st

DB_PATH = Path(__file__).resolve().parent.parent / "db" / "app.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    echo=False,
    connect_args={"check_same_thread": False, "timeout": 30},
)

from sqlalchemy import event as _sa_event

@_sa_event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_conn, _rec):
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.execute("PRAGMA cache_size=20000")
    cur.execute("PRAGMA temp_store=MEMORY")
    cur.execute("PRAGMA mmap_size=134217728")
    cur.close()


class Base(DeclarativeBase):
    pass


class Override(Base):
    __tablename__ = "overrides"
    id = Column(Integer, primary_key=True, autoincrement=True)
    join_key = Column(String, nullable=False, index=True)
    field = Column(String, nullable=False)        # e.g. 'Installer_Category'
    old_value = Column(String)
    new_value = Column(String)
    updated_by = Column(String)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    join_key = Column(String, nullable=False, index=True)
    installer_name = Column(String)
    country = Column(String)
    comment = Column(Text)
    created_by = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    join_key = Column(String, nullable=False, index=True)
    installer_name = Column(String)
    country = Column(String)
    from_user = Column(String)
    to_rsm = Column(String)
    subject = Column(String)
    message = Column(Text)
    scheduled_call_dt = Column(String)
    priority = Column(String, default="Normal")   # High / Normal
    status = Column(String, default="Open")       # Open / In Progress / Done
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ActionNote(Base):
    """One active action note per installer (upsert on join_key)."""
    __tablename__ = "action_notes"
    id         = Column(Integer, primary_key=True, autoincrement=True)
    join_key   = Column(String, nullable=False, unique=True, index=True)
    installer_name = Column(String)
    country    = Column(String)
    rsm        = Column(String)
    segment    = Column(String)
    priority   = Column(String)
    note       = Column(Text, default="")
    status     = Column(String, default="Open")   # Open / In Progress / Done
    updated_by = Column(String)
    updated_at = Column(DateTime, default=datetime.utcnow)


class QuarterSnapshot(Base):
    __tablename__ = "quarter_snapshots"
    id = Column(Integer, primary_key=True, autoincrement=True)
    join_key = Column(String, nullable=False, index=True)
    installer_name = Column(String)
    country = Column(String)
    quarter = Column(String)
    segment = Column(String)
    tier = Column(String)
    snapshot_date = Column(DateTime, default=datetime.utcnow)


# Create all tables on import
Base.metadata.create_all(engine)


# ── CRUD helpers ──────────────────────────────────────────────────────────────

def save_override(join_key: str, field: str, old_val: str, new_val: str, user: str):
    with Session(engine) as s:
        s.add(Override(join_key=join_key, field=field,
                       old_value=str(old_val), new_value=str(new_val), updated_by=user))
        s.commit()


@st.cache_data(ttl=30, show_spinner=False)
def get_overrides() -> dict:
    """Returns {join_key: {field: new_value}} from latest override per join_key+field."""
    with Session(engine) as s:
        rows = s.query(Override).order_by(Override.updated_at.asc()).all()
    result: dict = {}
    for r in rows:
        result.setdefault(r.join_key, {})[r.field] = r.new_value
    return result


def get_override_log():
    with Session(engine) as s:
        return [
            {"join_key": r.join_key, "field": r.field, "old": r.old_value,
             "new": r.new_value, "by": r.updated_by, "at": r.updated_at}
            for r in s.query(Override).order_by(Override.updated_at.desc()).all()
        ]


def save_comment(join_key: str, installer_name: str, country: str, text: str, user: str):
    with Session(engine) as s:
        s.add(Comment(join_key=join_key, installer_name=installer_name,
                      country=country, comment=text, created_by=user))
        s.commit()


def get_comments(join_key: str) -> list:
    with Session(engine) as s:
        return [
            {"text": r.comment, "by": r.created_by, "at": r.created_at}
            for r in s.query(Comment).filter_by(join_key=join_key)
            .order_by(Comment.created_at.desc()).all()
        ]


def save_message(join_key: str, installer_name: str, country: str,
                 from_user: str, to_rsm: str, subject: str, msg: str,
                 sched_dt: str = "", priority: str = "Normal"):
    with Session(engine) as s:
        s.add(Message(join_key=join_key, installer_name=installer_name, country=country,
                      from_user=from_user, to_rsm=to_rsm, subject=subject,
                      message=msg, scheduled_call_dt=sched_dt, priority=priority))
        s.commit()


def get_messages_for_rsm(rsm_name: str) -> list:
    with Session(engine) as s:
        return [
            {"id": r.id, "join_key": r.join_key, "installer": r.installer_name,
             "country": r.country, "from": r.from_user, "subject": r.subject,
             "message": r.message, "call_dt": r.scheduled_call_dt,
             "priority": r.priority, "status": r.status, "at": r.created_at}
            for r in s.query(Message).filter_by(to_rsm=rsm_name)
            .order_by(Message.created_at.desc()).all()
        ]


def get_sent_messages(from_user: str) -> list:
    with Session(engine) as s:
        return [
            {"id": r.id, "join_key": r.join_key, "installer": r.installer_name,
             "country": r.country, "to_rsm": r.to_rsm, "subject": r.subject,
             "message": r.message, "call_dt": r.scheduled_call_dt,
             "priority": r.priority, "status": r.status, "at": r.created_at}
            for r in s.query(Message).filter_by(from_user=from_user)
            .order_by(Message.created_at.desc()).all()
        ]


def update_message_status(msg_id: int, status: str):
    with Session(engine) as s:
        r = s.query(Message).filter_by(id=msg_id).first()
        if r:
            r.status = status
            r.updated_at = datetime.utcnow()
            s.commit()


def save_snapshot(master_df, quarter: str):
    """Save current classification as a snapshot for Lost-Regained detection."""
    import pandas as pd
    from datetime import datetime as _dt
    snap = master_df[["join_key", "Installer_Mapped", "Installer_Country",
                       "Installer_Category", "Installer_Group"]].copy()
    snap.columns = ["join_key", "installer_name", "country", "segment", "tier"]
    snap["quarter"] = quarter
    snap["snapshot_date"] = _dt.utcnow()
    snap.to_sql("quarter_snapshots", engine, if_exists="append",
                index=False, method="multi", chunksize=500)


def upsert_action_note(join_key: str, installer_name: str, country: str,
                       rsm: str, segment: str, priority: str,
                       note: str, status: str, user: str):
    """Insert or update a single action note for an installer."""
    with Session(engine) as s:
        row = s.query(ActionNote).filter_by(join_key=join_key).first()
        if row:
            row.note = note
            row.status = status
            row.updated_by = user
            row.updated_at = datetime.utcnow()
            row.rsm = rsm
            row.segment = segment
            row.priority = priority
        else:
            s.add(ActionNote(join_key=join_key, installer_name=installer_name,
                             country=country, rsm=rsm, segment=segment,
                             priority=priority, note=note, status=status,
                             updated_by=user))
        s.commit()


def get_all_action_notes() -> dict:
    """Returns {join_key: {note, status, updated_by, updated_at}}."""
    with Session(engine) as s:
        rows = s.query(ActionNote).all()
    return {
        r.join_key: {
            "note": r.note or "",
            "status": r.status or "Open",
            "updated_by": r.updated_by or "",
            "updated_at": r.updated_at,
        }
        for r in rows
    }


@st.cache_data(ttl=60, show_spinner=False)
def get_last_snapshot_lost() -> set:
    """Returns set of join_keys that were Lost in the most recent snapshot."""
    with Session(engine) as s:
        latest = s.query(QuarterSnapshot.quarter).order_by(
            QuarterSnapshot.snapshot_date.desc()).first()
        if not latest:
            return set()
        rows = s.query(QuarterSnapshot).filter_by(
            quarter=latest[0], segment="Lost").all()
    return {r.join_key for r in rows}
