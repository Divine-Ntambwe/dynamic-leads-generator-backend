import hashlib

def hash_url(url):
    return hashlib.sha256(url.encode()).hexdigest()

def normalize(value):
    if not value:
        return ""
    return value.lower().strip()

def generate_fingerprint(school):
    raw = (
        normalize(school.get("name")) +
        normalize(school.get("phone")) +
        normalize(school.get("email"))
    )
    return hashlib.sha256(raw.encode()).hexdigest()