from datetime import datetime, date, time
from ipaddress import ip_address
from json import loads
from typing import Any
from uuid import UUID

def convert_value_for_cql(value: Any, cql_type: str) -> Any:
    cql_type = cql_type.lower()
    
    if value == "" or value is None:
        return None
    
    try:
        if "int" in cql_type or "counter" in cql_type or "varint" in cql_type:
            return int(value)
        elif "float" in cql_type or "double" in cql_type or "decimal" in cql_type:
            return float(value)
        elif "boolean" in cql_type or "bool" in cql_type:
             if isinstance(value, str):
                 return value.lower() in ('true', '1', 'yes', 'on')
             return bool(value)
        elif "uuid" in cql_type or "timeuuid" in cql_type:
            return UUID(str(value))
        
        elif "timestamp" in cql_type:
            try:
                return datetime.fromtimestamp(float(value))
            except (ValueError, TypeError):
                try:
                     return datetime.fromisoformat(value)
                except ValueError:
                    try:
                        from dateutil import parser
                        return parser.parse(value)
                    except (ImportError, ValueError):
                        raise ValueError(f"Cannot parse timestamp: {value}")
        
        elif "date" in cql_type:
            try:
                return date.fromordinal(int(value) + 719162)
            except (ValueError, TypeError):
                try:
                    return date.fromisoformat(value)
                except ValueError:
                    try:
                        from dateutil import parser
                        return parser.parse(value).date()
                    except (ImportError, ValueError):
                         raise ValueError(f"Cannot parse date: {value}")

        elif cql_type == "time":
            try:
                nanos = int(value)
                return time(nanos // (3600 * 10**9), (nanos % (3600 * 10**9)) // (60 * 10**9), (nanos % (60 * 10**9)) // 10**9, (nanos % 10**9) // 1000)
            except (ValueError, TypeError):
                try:
                    return time.fromisoformat(value)
                except ValueError:
                    try:
                        from dateutil import parser
                        return parser.parse(value).time()
                    except (ImportError, ValueError):
                        raise ValueError(f"Cannot parse time: {value}")

        elif "inet" in cql_type:
            return str(ip_address(value))
        
        elif "blob" in cql_type:
            return bytes.fromhex(value.replace('0x', ''))
        
        elif cql_type.startswith("list<") or cql_type.startswith("set<") or cql_type.startswith("map<"):
            return loads(value) if isinstance(value, str) else value
        
        else:
            return value

    except Exception as e:
        raise ValueError(str(e))
