"""
Postgres/Neon-backed storage layer that mimics the subset of pymongo's
Collection API this app actually uses (find_one, find, insert_one,
update_one with $set/$push/$pull, delete_one/many, count_documents,
create_index, and one aggregate() pipeline). This lets every route/service
file that does `from app.database import users` etc. keep working
unchanged; only this file talks to the database directly.

Each "collection" is one Postgres table: (id TEXT PRIMARY KEY, data JSONB).
Documents are serialized with bson.json_util so ObjectId/datetime values
round-trip exactly like they did with real MongoDB.
"""
import logging
from datetime import datetime, timezone

import psycopg2
import psycopg2.pool
from bson import ObjectId, json_util
from pymongo.errors import DuplicateKeyError

from app.config import DATABASE_URL

logger = logging.getLogger(__name__)

_pool = psycopg2.pool.SimpleConnectionPool(0, 5, DATABASE_URL, sslmode="require")


def _get_conn():
    return _pool.getconn()


def _put_conn(conn):
    _pool.putconn(conn)


def _doc_to_json(doc: dict) -> str:
    return json_util.dumps(doc)


def _json_to_doc(raw) -> dict:
    return json_util.loads(raw if isinstance(raw, str) else json_util.dumps(raw))


def _get_path(doc, path):
    val = doc
    for part in path.split("."):
        if isinstance(val, dict):
            val = val.get(part)
        else:
            return None
    return val


def _match_one(doc, key, cond):
    if "." in key:
        head, _, tail = key.partition(".")
        values = doc.get(head)
        if isinstance(values, list):
            return any(isinstance(v, dict) and v.get(tail) == cond for v in values)
        return False
    actual = doc.get(key)
    if isinstance(cond, dict) and any(str(k).startswith("$") for k in cond):
        for op, val in cond.items():
            if op == "$ne" and actual == val:
                return False
            if op == "$in" and actual not in val:
                return False
            if op == "$nin" and actual in val:
                return False
            if op == "$gte" and not (actual is not None and actual >= val):
                return False
            if op == "$lte" and not (actual is not None and actual <= val):
                return False
            if op == "$gt" and not (actual is not None and actual > val):
                return False
            if op == "$lt" and not (actual is not None and actual < val):
                return False
        return True
    # MongoDB-style implicit array containment: if the stored field is a
    # list and the query value is a plain scalar, match when the scalar
    # appears anywhere in the list (e.g. find_one({"tokens": token})).
    if isinstance(actual, list) and not isinstance(cond, list):
        return cond in actual
    return actual == cond


def _match(doc, filt):
    return all(_match_one(doc, k, v) for k, v in (filt or {}).items())


def _sort_key(v):
    if v is None:
        return (0, "")
    if isinstance(v, datetime):
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return (1, v)
    return (1, v)


class _Result:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


class Cursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, key_or_list, direction=None):
        pairs = key_or_list if isinstance(key_or_list, list) else [(key_or_list, direction)]
        for key, dirn in reversed(pairs):
            self._docs.sort(key=lambda d: _sort_key(_get_path(d, key)), reverse=(dirn == -1))
        return self

    def skip(self, n):
        self._docs = self._docs[n:]
        return self

    def limit(self, n):
        self._docs = self._docs[:n]
        return self

    def __iter__(self):
        return iter(self._docs)

    def __len__(self):
        return len(self._docs)


class Collection:
    def __init__(self, name):
        self.name = name
        self._unique_fields = []  # list of field-name lists
        self._ttl = None  # (field, seconds)
        self._table_ready = False

    def _ensure_table(self):
        if self._table_ready:
            return
        conn = _get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(f'CREATE TABLE IF NOT EXISTS "{self.name}" (id TEXT PRIMARY KEY, data JSONB NOT NULL)')
            conn.commit()
            self._table_ready = True
        finally:
            _put_conn(conn)

    def _purge_expired(self):
        if not self._ttl:
            return
        field, seconds = self._ttl
        cutoff = datetime.now(timezone.utc).timestamp() - seconds
        keep = []
        expired_ids = []
        for doc in self._all_docs(raw=True):
            val = doc.get(field)
            if isinstance(val, datetime):
                ts = val.replace(tzinfo=val.tzinfo or timezone.utc).timestamp()
                if ts < cutoff:
                    expired_ids.append(str(doc["_id"]))
                    continue
            keep.append(doc)
        if expired_ids:
            conn = _get_conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(f'DELETE FROM "{self.name}" WHERE id = ANY(%s)', (expired_ids,))
                conn.commit()
            finally:
                _put_conn(conn)

    def _all_docs(self, raw=False):
        self._ensure_table()
        if not raw and self._ttl:
            self._purge_expired()
        conn = _get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(f'SELECT data FROM "{self.name}"')
                rows = cur.fetchall()
        finally:
            _put_conn(conn)
        return [_json_to_doc(r[0]) for r in rows]

    def find_one(self, filt=None):
        for doc in self._all_docs():
            if _match(doc, filt or {}):
                return doc
        return None

    def find(self, filt=None):
        return Cursor([d for d in self._all_docs() if _match(d, filt or {})])

    def insert_one(self, doc):
        self._ensure_table()
        if "_id" not in doc:
            doc["_id"] = ObjectId()
        for fields in self._unique_fields:
            existing = self.find_one({f: doc.get(f) for f in fields})
            if existing:
                raise DuplicateKeyError(f"Duplicate value for unique field(s) {fields} in {self.name}")
        conn = _get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f'INSERT INTO "{self.name}" (id, data) VALUES (%s, %s)',
                    (str(doc["_id"]), _doc_to_json(doc)),
                )
            conn.commit()
        finally:
            _put_conn(conn)
        return _Result(inserted_id=doc["_id"])

    def update_one(self, filt, update):
        self._ensure_table()
        doc = self.find_one(filt)
        if not doc:
            return _Result(matched_count=0, modified_count=0)
        for op, changes in update.items():
            if op == "$set":
                doc.update(changes)
            elif op == "$push":
                for k, v in changes.items():
                    doc.setdefault(k, [])
                    if isinstance(doc[k], list):
                        doc[k].append(v)
            elif op == "$pull":
                for k, v in changes.items():
                    if isinstance(doc.get(k), list):
                        doc[k] = [item for item in doc[k] if item != v]
            elif op == "$inc":
                for k, v in changes.items():
                    doc[k] = doc.get(k, 0) + v
        conn = _get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f'UPDATE "{self.name}" SET data = %s WHERE id = %s',
                    (_doc_to_json(doc), str(doc["_id"])),
                )
            conn.commit()
        finally:
            _put_conn(conn)
        return _Result(matched_count=1, modified_count=1)

    def delete_one(self, filt):
        self._ensure_table()
        doc = self.find_one(filt)
        if not doc:
            return _Result(deleted_count=0)
        conn = _get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(f'DELETE FROM "{self.name}" WHERE id = %s', (str(doc["_id"]),))
            conn.commit()
        finally:
            _put_conn(conn)
        return _Result(deleted_count=1)

    def delete_many(self, filt):
        self._ensure_table()
        docs = list(self.find(filt))
        if not docs:
            return _Result(deleted_count=0)
        ids = [str(d["_id"]) for d in docs]
        conn = _get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(f'DELETE FROM "{self.name}" WHERE id = ANY(%s)', (ids,))
            conn.commit()
        finally:
            _put_conn(conn)
        return _Result(deleted_count=len(ids))

    def count_documents(self, filt=None):
        return len(list(self.find(filt or {})))

    def create_index(self, field_spec, unique=False, expireAfterSeconds=None):
        if isinstance(field_spec, list):
            fields = [f for f, _ in field_spec]
        else:
            fields = [field_spec]
        if unique:
            self._unique_fields.append(fields)
        if expireAfterSeconds is not None:
            self._ttl = (fields[0], expireAfterSeconds)

    def aggregate(self, pipeline):
        self._ensure_table()
        docs = self._all_docs()
        for stage in pipeline:
            if "$match" in stage:
                docs = [d for d in docs if _match(d, stage["$match"])]
            elif "$group" in stage:
                group = stage["$group"]
                id_expr = group["_id"]
                buckets = {}
                order = []
                for d in docs:
                    if isinstance(id_expr, str) and id_expr.startswith("$"):
                        val = _get_path(d, id_expr[1:])
                    else:
                        val = id_expr
                    key = val if val is not None else None
                    if key not in buckets:
                        buckets[key] = {"_id": key, "count": 0}
                        order.append(key)
                    for out_field, agg in group.items():
                        if out_field == "_id":
                            continue
                        if isinstance(agg, dict) and "$sum" in agg:
                            buckets[key][out_field] = buckets[key].get(out_field, 0) + agg["$sum"] if isinstance(agg["$sum"], (int, float)) else buckets[key].get(out_field, 0) + 1
                docs = [buckets[k] for k in order]
            elif "$sort" in stage:
                for key, direction in reversed(list(stage["$sort"].items())):
                    docs.sort(key=lambda d: d.get(key, 0), reverse=(direction == -1))
            elif "$limit" in stage:
                docs = docs[: stage["$limit"]]
            elif "$skip" in stage:
                docs = docs[stage["$skip"]:]
        return docs


class _Admin:
    def command(self, cmd):
        conn = _get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        finally:
            _put_conn(conn)


class _Client:
    """Stand-in for pymongo's MongoClient — only what main.py needs."""
    admin = _Admin()

    def close(self):
        _pool.closeall()


client = _Client()
db = None  # unused, kept only so `from app.database import db` doesn't break

founder_profiles = Collection("founder_profiles")
startup_plans = Collection("startup_plans")
shared_analyses = Collection("shared_analyses")
saved_analyses = Collection("saved_analyses")
build_progress = Collection("build_progress")
analytics_events = Collection("analytics_events")
customer_strategies = Collection("customer_strategies")
decision_reports = Collection("decision_reports")
business_plans = Collection("business_plans")
customer_insights = Collection("customer_insights")
market_intelligence = Collection("market_intelligence")
ai_cofounder_chats = Collection("ai_cofounder_chats")
investor_tools = Collection("investor_tools")
marketing_hub = Collection("marketing_hub")
development_hubs = Collection("development_hubs")
growth_hubs = Collection("growth_hubs")
financial_plans = Collection("financial_plans")
launch_hubs = Collection("launch_hubs")
teams = Collection("teams")
team_invites = Collection("team_invites")
team_analyses = Collection("team_analyses")
comments = Collection("comments")
users = Collection("users")
saved_ideas = Collection("saved_ideas")
password_resets = Collection("password_resets")


def ensure_indexes():
    """Register uniqueness/TTL rules (enforced in Python, see Collection above)."""
    try:
        teams.create_index([("invite_code", 1)], unique=True)
        users.create_index([("email", 1)], unique=True)
        password_resets.create_index([("token", 1)], unique=True)
        password_resets.create_index([("created_at", 1)], expireAfterSeconds=900)
        logger.info("Postgres collection rules ensured.")
    except Exception as e:
        logger.warning("Failed to set up collection rules: %s", e)
