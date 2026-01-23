import bcrypt


def hash_password(v: str) -> str:
    if isinstance(v, str) and not (v.startswith("$2b$") or v.startswith("$2a$")):
        return bcrypt.hashpw(v.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    return v


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
