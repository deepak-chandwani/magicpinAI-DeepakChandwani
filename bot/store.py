from threading import RLock
from utils import now_iso


class ContextStore:
    """Small in-memory store matching the challenge's versioned context contract."""

    def __init__(self):
        self.lock = RLock()
        self.scopes = {"category": {}, "merchant": {}, "customer": {}, "trigger": {}}
        self.conversations = {}
        self.sent_keys = set()

    def put(self, scope, context_id, version, payload):
        with self.lock:
            bucket = self.scopes[scope]
            old = bucket.get(context_id)
            if old and version <= old["version"]:
                return False, old["version"]
            bucket[context_id] = {
                "version": version,
                "payload": payload,
                "delivered_at": now_iso(),
            }
            return True, version

    def get(self, scope, context_id):
        item = self.scopes.get(scope, {}).get(context_id)
        return item["payload"] if item else None

    def all_context_ids(self, scope):
        return list(self.scopes.get(scope, {}).keys())

    def mark_sent(self, key):
        with self.lock:
            if key in self.sent_keys:
                return False
            self.sent_keys.add(key)
            return True

    def is_sent(self, key):
        return key in self.sent_keys

    def create_conversation(self, conversation_id, state):
        self.conversations[conversation_id] = state

    def get_conversation(self, conversation_id):
        return self.conversations.get(conversation_id)

    def counts(self):
        return {k: len(v) for k, v in self.scopes.items()}
