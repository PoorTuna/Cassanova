from re import match


def sanitize_identifier(name: str) -> str:
    if not match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name):
        raise ValueError(f"Invalid CQL identifier: {name}")
    return name
