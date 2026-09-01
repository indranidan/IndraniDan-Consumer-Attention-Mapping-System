"""
AI Document Repository
======================
High-performance MongoDB repository for AI pipeline outputs,
shopper coordinate trajectories, attention events, product interactions, and executive reports.
Includes seamless in-memory caching fallback when MongoDB is offline during testing.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import uuid

# pyrefly: ignore [missing-import]
import pymongo
# pyrefly: ignore [missing-import]
from pymongo.database import Database as SyncDatabase
# pyrefly: ignore [missing-import]
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database.mongodb import get_mongo_db, get_sync_mongo_db
from app.core.redis_client import redis_client

logger = logging.getLogger("ai_document_repository")


class AIDocumentRepository:
    """
    Data access layer for MongoDB AI collections.
    Supports both async methods (for FastAPI endpoints) and sync methods (for background workers and services).
    Falls back gracefully to memory store if MongoDB is offline.
    """

    # ── Collection Names ──────────────────────────────────────────
    COLL_JOB_REPORTS = "job_reports"
    COLL_SHOPPER_JOURNEYS = "shopper_journeys"
    COLL_ATTENTION_EVENTS = "attention_events"
    COLL_INTERACTION_EVENTS = "interaction_events"
    COLL_MODULE4_ANALYSES = "module4_analyses"
    COLL_MODULE5_ANALYSES = "module5_analyses"
    COLL_MODULE6_ANALYSES = "module6_consumer_behavior"

    # In-memory store for fallback / offline test execution
    _memory_store: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def _cache_set(cls, prefix: str, key: str, data: Any):
        cls._memory_store.setdefault(prefix, {})[key] = data
        if redis_client:
            try:
                redis_client.setex(f"ai_repo:{prefix}:{key}", 3600, json.dumps(data, default=str))
            except Exception as e:
                logger.warning(f"Redis cache set failed: {e}")

    @classmethod
    def _cache_get(cls, prefix: str, key: str) -> Optional[Any]:
        if redis_client:
            try:
                val = redis_client.get(f"ai_repo:{prefix}:{key}")
                if val:
                    return json.loads(val)
            except Exception as e:
                logger.warning(f"Redis cache get failed: {e}")
        return cls._memory_store.get(prefix, {}).get(key)

    @classmethod
    def ensure_indexes_sync(cls, db: SyncDatabase) -> None:
        """Create necessary indexes for performance and fast lookups."""
        try:
            db[cls.COLL_JOB_REPORTS].create_index([("job_id", pymongo.ASCENDING)], unique=True)
            db[cls.COLL_MODULE4_ANALYSES].create_index([("job_id", pymongo.ASCENDING)], unique=True)
            db[cls.COLL_MODULE5_ANALYSES].create_index([("job_id", pymongo.ASCENDING)], unique=True)
            db[cls.COLL_MODULE6_ANALYSES].create_index([("job_id", pymongo.ASCENDING)], unique=True)
            db[cls.COLL_SHOPPER_JOURNEYS].create_index([
                ("job_id", pymongo.ASCENDING),
                ("tracking_id", pymongo.ASCENDING),
            ])
            db[cls.COLL_ATTENTION_EVENTS].create_index([
                ("job_id", pymongo.ASCENDING),
                ("track_id", pymongo.ASCENDING),
                ("target_id", pymongo.ASCENDING),
            ])
            db[cls.COLL_INTERACTION_EVENTS].create_index([
                ("job_id", pymongo.ASCENDING),
                ("track_id", pymongo.ASCENDING),
                ("product_id", pymongo.ASCENDING),
                ("event_type", pymongo.ASCENDING),
            ])
            logger.info("MongoDB AI collections indexes verified.")
        except Exception as exc:
            logger.warning(f"Error creating MongoDB indexes: {exc}")

    # ── Synchronous Worker & Service Persistence ──────────────────

    @classmethod
    def ingest_job_artifacts_sync(
        cls,
        job_id: uuid.UUID,
        output_dir: Path,
        store_id: Optional[uuid.UUID] = None,
        camera_id: Optional[uuid.UUID] = None,
    ) -> bool:
        """
        Parse and ingest all generated JSON reports for a completed AI job into MongoDB / Document store.
        """
        db = get_sync_mongo_db()
        job_id_str = str(job_id)
        store_id_str = str(store_id) if store_id else None
        camera_id_str = str(camera_id) if camera_id else None

        try:
            # 1. Ingest Phase 6 Summary Report
            p6_json = output_dir / "phase6" / "reports" / "attention_report.json"
            p6_md = output_dir / "phase6" / "reports" / "attention_report.md"
            if p6_json.exists():
                with open(p6_json, "r", encoding="utf-8") as f:
                    report_data = json.load(f)
                md_content = ""
                if p6_md.exists():
                    try:
                        md_content = p6_md.read_text(encoding="utf-8")
                    except Exception:
                        pass

                doc = {
                    "job_id": job_id_str,
                    "store_id": store_id_str,
                    "camera_id": camera_id_str,
                    "ingested_at": datetime.now(timezone.utc).isoformat(),
                    "report": report_data,
                    "markdown_report": md_content,
                }
                if db is not None:
                    cls.ensure_indexes_sync(db)
                    db[cls.COLL_JOB_REPORTS].update_one(
                        {"job_id": job_id_str},
                        {"$set": doc},
                        upsert=True,
                    )
                else:
                    cls._cache_set("job_reports", job_id_str, doc)

            # 2. Ingest Shopper Journeys & Trajectories (Phases 3 & 4)
            sessions_file = output_dir / "phase3" / "reports" / "sessions.json"
            paths_file = output_dir / "phase3" / "reports" / "paths.json"
            zone_visits_file = output_dir / "phase3" / "reports" / "zone_visits.json"

            paths_map: Dict[int, list] = {}
            if paths_file.exists():
                try:
                    with open(paths_file, "r", encoding="utf-8") as f:
                        raw_paths = json.load(f).get("paths", {})
                        for k, v in raw_paths.items():
                            paths_map[int(k)] = v
                except Exception as exc:
                    logger.warning(f"Could not parse paths.json: {exc}")

            zone_visits_map: Dict[int, list] = {}
            if zone_visits_file.exists():
                try:
                    with open(zone_visits_file, "r", encoding="utf-8") as f:
                        raw_visits = json.load(f).get("zone_visits", [])
                        for zv in raw_visits:
                            tid = zv.get("tracking_id")
                            if tid is not None:
                                zone_visits_map.setdefault(int(tid), []).append(zv)
                except Exception as exc:
                    logger.warning(f"Could not parse zone_visits.json: {exc}")

            if sessions_file.exists():
                try:
                    with open(sessions_file, "r", encoding="utf-8") as f:
                        sessions = json.load(f).get("sessions", [])

                    journey_docs = []
                    for s in sessions:
                        tid = s.get("tracking_id")
                        if tid is None:
                            continue
                        tid = int(tid)
                        journey_docs.append({
                            "job_id": job_id_str,
                            "store_id": store_id_str,
                            "camera_id": camera_id_str,
                            "tracking_id": tid,
                            "session": s,
                            "path": paths_map.get(tid, []),
                            "zone_visits": zone_visits_map.get(tid, []),
                        })

                    if journey_docs:
                        if db is not None:
                            db[cls.COLL_SHOPPER_JOURNEYS].delete_many({"job_id": job_id_str})
                            db[cls.COLL_SHOPPER_JOURNEYS].insert_many(journey_docs)
                        else:
                            cls._cache_set("shopper_journeys", job_id_str, journey_docs)
                except Exception as exc:
                    logger.warning(f"Error ingesting shopper journeys: {exc}")

            # 3. Ingest Attention Events (Phase 5)
            attn_events_file = output_dir / "phase5" / "reports" / "attention_events.json"
            if attn_events_file.exists():
                try:
                    with open(attn_events_file, "r", encoding="utf-8") as f:
                        events = json.load(f).get("events", [])
                    if events:
                        mongo_events = []
                        for ev in events:
                            d = dict(ev)
                            d["job_id"] = job_id_str
                            d["store_id"] = store_id_str
                            d["track_id"] = int(d.get("track_id") or d.get("tracking_id") or 0)
                            mongo_events.append(d)
                        if db is not None:
                            db[cls.COLL_ATTENTION_EVENTS].delete_many({"job_id": job_id_str})
                            db[cls.COLL_ATTENTION_EVENTS].insert_many(mongo_events)
                        else:
                            cls._cache_set("attn_events", job_id_str, mongo_events)
                except Exception as exc:
                    logger.warning(f"Error ingesting attention events: {exc}")

            return True
        except Exception as exc:
            logger.error(f"Failed to ingest AI artifacts: {exc}")
            return False

    @classmethod
    def save_module4_analysis_sync(
        cls,
        job_id: uuid.UUID,
        analysis_data: Dict[str, Any],
        events: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """Save Module 4 attention analysis and granular events to MongoDB or memory fallback."""
        job_id_str = str(job_id)
        doc = {
            "job_id": job_id_str,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "analysis": analysis_data,
        }

        # Always update memory store for instantaneous fallback
        cls._cache_set("m4", job_id_str, doc)

        if events:
            mongo_evts = []
            for ev in events:
                e = dict(ev)
                e["job_id"] = job_id_str
                e["track_id"] = int(e.get("track_id") or e.get("tracking_id") or 0)
                mongo_evts.append(e)
            cls._cache_set("attn_events", job_id_str, mongo_evts)

        db = get_sync_mongo_db()
        if db is not None:
            cls.ensure_indexes_sync(db)
            db[cls.COLL_MODULE4_ANALYSES].update_one(
                {"job_id": job_id_str},
                {"$set": doc},
                upsert=True,
            )
            if events:
                db[cls.COLL_ATTENTION_EVENTS].delete_many({"job_id": job_id_str})
                if mongo_evts:
                    db[cls.COLL_ATTENTION_EVENTS].insert_many(mongo_evts)

        return True

    @classmethod
    def save_module5_analysis_sync(
        cls,
        job_id: uuid.UUID,
        analysis_data: Dict[str, Any],
        events: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """Save Module 5 interaction analysis and granular events to MongoDB or memory fallback."""
        job_id_str = str(job_id)
        doc = {
            "job_id": job_id_str,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "analysis": analysis_data,
        }

        cls._cache_set("m5", job_id_str, doc)

        if events:
            mongo_evts = []
            for ev in events:
                e = dict(ev)
                e["job_id"] = job_id_str
                e["track_id"] = int(e.get("track_id") or e.get("tracking_id") or 0)
                mongo_evts.append(e)
            cls._cache_set("int_events", job_id_str, mongo_evts)

        db = get_sync_mongo_db()
        if db is not None:
            cls.ensure_indexes_sync(db)
            db[cls.COLL_MODULE5_ANALYSES].update_one(
                {"job_id": job_id_str},
                {"$set": doc},
                upsert=True,
            )
            if events:
                db[cls.COLL_INTERACTION_EVENTS].delete_many({"job_id": job_id_str})
                if mongo_evts:
                    db[cls.COLL_INTERACTION_EVENTS].insert_many(mongo_evts)

        return True

    @classmethod
    def save_module6_analysis_sync(
        cls,
        job_id: uuid.UUID,
        analysis_data: Dict[str, Any],
    ) -> bool:
        """Save Module 6 behavioral analysis to MongoDB or memory fallback."""
        job_id_str = str(job_id)
        
        # Always update memory store for instantaneous fallback
        cls._cache_set("m6", job_id_str, analysis_data)

        db = get_sync_mongo_db()
        if db is not None:
            cls.ensure_indexes_sync(db)
            db[cls.COLL_MODULE6_ANALYSES].update_one(
                {"job_id": job_id_str},
                {"$set": analysis_data},
                upsert=True,
            )

        return True

    # ── Synchronous Query Methods ─────────────────────────────────

    @classmethod
    def get_module4_analysis_sync(cls, job_id: str) -> Optional[Dict[str, Any]]:
        db = get_sync_mongo_db()
        if db is not None:
            doc = db[cls.COLL_MODULE4_ANALYSES].find_one({"job_id": job_id}, {"_id": 0})
            if doc:
                return doc.get("analysis")
        mem_doc = cls._cache_get("m4", job_id)
        return mem_doc.get("analysis") if mem_doc else None

    @classmethod
    def get_module5_analysis_sync(cls, job_id: str) -> Optional[Dict[str, Any]]:
        db = get_sync_mongo_db()
        if db is not None:
            doc = db[cls.COLL_MODULE5_ANALYSES].find_one({"job_id": job_id}, {"_id": 0})
            if doc:
                return doc.get("analysis")
        mem_doc = cls._cache_get("m5", job_id)
        return mem_doc.get("analysis") if mem_doc else None

    @classmethod
    def get_module6_analysis_sync(cls, job_id: str) -> Optional[Dict[str, Any]]:
        db = get_sync_mongo_db()
        if db is not None:
            doc = db[cls.COLL_MODULE6_ANALYSES].find_one({"job_id": job_id}, {"_id": 0})
            if doc:
                return doc
        return cls._cache_get("m6", job_id)

    @classmethod
    def get_batch_module4_analyses_sync(cls, job_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Batch fetch Module 4 attention analysis documents for multiple jobs."""
        if not job_ids:
            return {}
        results: Dict[str, Dict[str, Any]] = {}
        db = get_sync_mongo_db()
        if db is not None:
            try:
                cursor = db[cls.COLL_MODULE4_ANALYSES].find(
                    {"job_id": {"$in": job_ids}},
                    {"_id": 0}
                )
                for doc in cursor:
                    jid = doc.get("job_id")
                    if jid:
                        results[jid] = doc.get("analysis", {})
            except Exception as exc:
                logger.warning(f"Batch M4 query failed: {exc}")

        for jid in job_ids:
            if jid not in results:
                cached = cls._cache_get("m4", jid)
                if cached:
                    results[jid] = cached.get("analysis", {})
        return results

    @classmethod
    def get_batch_module5_analyses_sync(cls, job_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Batch fetch Module 5 interaction analysis documents for multiple jobs."""
        if not job_ids:
            return {}
        results: Dict[str, Dict[str, Any]] = {}
        db = get_sync_mongo_db()
        if db is not None:
            try:
                cursor = db[cls.COLL_MODULE5_ANALYSES].find(
                    {"job_id": {"$in": job_ids}},
                    {"_id": 0}
                )
                for doc in cursor:
                    jid = doc.get("job_id")
                    if jid:
                        results[jid] = doc.get("analysis", {})
            except Exception as exc:
                logger.warning(f"Batch M5 query failed: {exc}")

        for jid in job_ids:
            if jid not in results:
                cached = cls._cache_get("m5", jid)
                if cached:
                    results[jid] = cached.get("analysis", {})
        return results

    @classmethod
    def get_batch_module6_analyses_sync(cls, job_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Batch fetch Module 6 behavioral analysis documents for multiple jobs."""
        if not job_ids:
            return {}
        results: Dict[str, Dict[str, Any]] = {}
        db = get_sync_mongo_db()
        if db is not None:
            try:
                cursor = db[cls.COLL_MODULE6_ANALYSES].find(
                    {"job_id": {"$in": job_ids}},
                    {"_id": 0}
                )
                for doc in cursor:
                    jid = doc.get("job_id")
                    if jid:
                        results[jid] = doc.get("analysis", {}) or doc
            except Exception as exc:
                logger.warning(f"Batch M6 query failed: {exc}")

        for jid in job_ids:
            if jid not in results:
                mem = cls._cache_get("m6", jid) or {}
                if mem:
                    results[jid] = mem.get("analysis", {}) or mem
        return results

    @classmethod
    def get_ai_document_sync(cls, job_id: str, collection_name: str) -> Optional[Dict[str, Any]]:
        """Generic sync document retrieval helper for any AI collection."""
        db = get_sync_mongo_db()
        if db is not None:
            doc = db[collection_name].find_one({"job_id": job_id}, {"_id": 0})
            if doc:
                return doc
        if collection_name == cls.COLL_MODULE6_ANALYSES:
            return cls._cache_get("m6", job_id)
        if collection_name == cls.COLL_MODULE5_ANALYSES:
            return cls._cache_get("m5", job_id)
        if collection_name == cls.COLL_MODULE4_ANALYSES:
            return cls._cache_get("m4", job_id)
        return cls._cache_get(collection_name, job_id)

    @classmethod
    def get_attention_events_sync(
        cls,
        job_id: str,
        track_id: Optional[int] = None,
        target_id: Optional[str] = None,
        target_type: Optional[str] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        db = get_sync_mongo_db()
        if db is not None:
            query: Dict[str, Any] = {"job_id": job_id}
            if track_id is not None:
                query["track_id"] = track_id
            if target_id is not None:
                query["target_id"] = target_id
            if target_type is not None:
                query["target_type"] = target_type

            total = db[cls.COLL_ATTENTION_EVENTS].count_documents(query)
            cursor = db[cls.COLL_ATTENTION_EVENTS].find(query, {"_id": 0}).sort("start_time", pymongo.ASCENDING)
            if page is not None and page_size is not None:
                cursor = cursor.skip((page - 1) * page_size).limit(page_size)

            return list(cursor), total

        # Fallback to in-memory store
        events = (cls._cache_get("attn_events", job_id) or [])
        filtered = []
        for ev in events:
            if track_id is not None and ev.get("track_id") != track_id:
                continue
            if target_id is not None and ev.get("target_id") != target_id:
                continue
            if target_type is not None and ev.get("target_type") != target_type:
                continue
            filtered.append(ev)

        total = len(filtered)
        if page is not None and page_size is not None:
            start = (page - 1) * page_size
            filtered = filtered[start : start + page_size]
        return filtered, total

    @classmethod
    def get_interaction_events_sync(
        cls,
        job_id: str,
        track_id: Optional[int] = None,
        event_type: Optional[str] = None,
        product_id: Optional[str] = None,
        shelf_id: Optional[str] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        db = get_sync_mongo_db()
        if db is not None:
            query: Dict[str, Any] = {"job_id": job_id}
            if track_id is not None:
                query["track_id"] = track_id
            if event_type is not None:
                query["event_type"] = event_type
            if product_id is not None:
                query["product_id"] = product_id
            if shelf_id is not None:
                query["shelf_id"] = shelf_id

            total = db[cls.COLL_INTERACTION_EVENTS].count_documents(query)
            cursor = db[cls.COLL_INTERACTION_EVENTS].find(query, {"_id": 0}).sort("start_time", pymongo.ASCENDING)
            if page is not None and page_size is not None:
                cursor = cursor.skip((page - 1) * page_size).limit(page_size)

            return list(cursor), total

        # Fallback to in-memory store
        events = (cls._cache_get("int_events", job_id) or [])
        filtered = []
        for ev in events:
            if track_id is not None and ev.get("track_id") != track_id:
                continue
            if event_type is not None and ev.get("event_type") != event_type:
                continue
            if product_id is not None and ev.get("product_id") != product_id:
                continue
            if shelf_id is not None and ev.get("shelf_id") != shelf_id:
                continue
            filtered.append(ev)

        total = len(filtered)
        if page is not None and page_size is not None:
            start = (page - 1) * page_size
            filtered = filtered[start : start + page_size]
        return filtered, total

    # ── Asynchronous Query Methods ────────────────────────────────

    @classmethod
    async def get_job_report_async(cls, job_id: str, db: Optional[AsyncIOMotorDatabase] = None) -> Optional[Dict[str, Any]]:
        mongo = db or get_mongo_db()
        if mongo is not None:
            return await mongo[cls.COLL_JOB_REPORTS].find_one({"job_id": job_id}, {"_id": 0})
        return cls._cache_get("job_reports", job_id)

    @classmethod
    async def get_shopper_journey_async(
        cls, job_id: str, tracking_id: int, db: Optional[AsyncIOMotorDatabase] = None
    ) -> Optional[Dict[str, Any]]:
        mongo = db or get_mongo_db()
        if mongo is not None:
            return await mongo[cls.COLL_SHOPPER_JOURNEYS].find_one(
                {"job_id": job_id, "tracking_id": tracking_id}, {"_id": 0}
            )
        journeys = (cls._cache_get("shopper_journeys", job_id) or [])
        for j in journeys:
            if j.get("tracking_id") == tracking_id:
                return j
        return None

    @classmethod
    async def list_shopper_journeys_async(
        cls, job_id: str, skip: int = 0, limit: int = 50, db: Optional[AsyncIOMotorDatabase] = None
    ) -> List[Dict[str, Any]]:
        mongo = db or get_mongo_db()
        if mongo is not None:
            cursor = mongo[cls.COLL_SHOPPER_JOURNEYS].find(
                {"job_id": job_id}, {"_id": 0}
            ).skip(skip).limit(limit)
            return await cursor.to_list(length=limit)
        journeys = (cls._cache_get("shopper_journeys", job_id) or [])
        return journeys[skip : skip + limit]

    @classmethod
    async def get_module6_analysis_async(cls, job_id: str, db: Optional[AsyncIOMotorDatabase] = None) -> Optional[Dict[str, Any]]:
        mongo = db or get_mongo_db()
        if mongo is not None:
            return await mongo[cls.COLL_MODULE6_ANALYSES].find_one({"job_id": job_id}, {"_id": 0})
        return cls._cache_get("m6", job_id)
