import base64, hashlib
from app.core.config import settings

def _key(): return hashlib.sha256(settings.secret_key.encode()).digest()
def encrypt(value: str) -> str:
    if not value: return ""
    key = _key(); raw = value.encode(); out = bytes(b ^ key[i % len(key)] for i,b in enumerate(raw)); return base64.urlsafe_b64encode(out).decode()
def decrypt(value: str) -> str:
    if not value: return ""
    key = _key(); raw = base64.urlsafe_b64decode(value.encode()); return bytes(b ^ key[i % len(key)] for i,b in enumerate(raw)).decode()
