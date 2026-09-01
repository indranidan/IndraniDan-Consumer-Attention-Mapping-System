import re

with open('app/repositories/ai_document_repository.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('from app.database.mongodb import get_mongo_db, get_sync_mongo_db', 'from app.database.mongodb import get_mongo_db, get_sync_mongo_db\nfrom app.core.redis_client import redis_client')

helpers = '''
    @classmethod
    def _cache_set(cls, prefix: str, key: str, data: Any):
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
        return None
'''

memory_store_pattern = re.compile(r'    _memory_store: Dict\[str, Dict\[str, Any\]\] = \{.*?\n    \}', re.DOTALL)
content = memory_store_pattern.sub(helpers.strip(), content)

# cls._memory_store["m4"][job_id_str] = doc
content = re.sub(r'cls\._memory_store\["([^"]+)"\]\[([^\]]+)\] = (.*)', r'cls._cache_set("\1", \2, \3)', content)

# mem = cls._memory_store["m6"][jid]
content = re.sub(r'cls\._memory_store\["([^"]+)"\]\[([^\]]+)\]', r'(cls._cache_get("\1", \2) or {})', content)

# cls._memory_store.get("m4", {}).get(job_id)
content = re.sub(r'cls\._memory_store\.get\("([^"]+)",\s*\{\}\)\.get\(([^),]+)\)', r'cls._cache_get("\1", \2)', content)

# events = cls._memory_store.get("attn_events", {}).get(job_id, [])
content = re.sub(r'cls\._memory_store\.get\("([^"]+)",\s*\{\}\)\.get\(([^,]+),\s*\[\]\)', r'(cls._cache_get("\1", \2) or [])', content)

with open('app/repositories/ai_document_repository.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Refactor done')
