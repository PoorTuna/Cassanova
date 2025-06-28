from typing import Any


def serialize_to_primitive(obj: Any) -> Any:
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj

    if isinstance(obj, dict):
        return {serialize_to_primitive(k): serialize_to_primitive(v) for k, v in obj.items()}

    if isinstance(obj, (list, tuple, set)):
        return [serialize_to_primitive(v) for v in obj]

    if hasattr(obj, '_asdict') and callable(obj._asdict):
        return serialize_to_primitive(obj._asdict())

    if hasattr(obj, 'as_cql_query') and callable(obj.as_cql_query):
        return obj.as_cql_query()

    if hasattr(obj, '__dict__'):
        return {k: serialize_to_primitive(v) for k, v in vars(obj).items() if not k.startswith('_')}

    return str(obj)
