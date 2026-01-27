from bcrypt import checkpw, hashpw, gensalt


def hash_password(v: str) -> str:
    if isinstance(v, str) and not (v.startswith("$2b$") or v.startswith("$2a$")):
        return hashpw(v.encode('utf-8'), gensalt()).decode('utf-8')
    return v


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
