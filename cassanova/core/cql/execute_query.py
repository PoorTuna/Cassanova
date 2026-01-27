from typing import Any, NoReturn

from cassandra import InvalidRequest
from cassandra.cluster import Session, ResultSet, NoHostAvailable
from cassandra.protocol import SyntaxException
from cassandra.query import SimpleStatement

from cassanova.models.cql_query import CQLQuery


import re

def execute_query_cql(session: Session, query: CQLQuery) -> list[dict[str, Any]] | str | NoReturn:
    return _execute_with_retry(session, query, attempt=1)

def _execute_with_retry(session: Session, query: CQLQuery, attempt: int) -> list[dict[str, Any]] | str | NoReturn:
    statement = SimpleStatement(query_string=query.cql, consistency_level=query.cl)
    try:
        result_set = session.execute(statement, trace=query.enable_tracing)
        result = [row._asdict() for row in result_set]
        if query.enable_tracing:
            result = {'result': result, 'trace': get_trace_info(result_set)}
        return {'result': result}
    except InvalidRequest as e:
        msg = str(e).lower()
        match = re.search(r"table ([a-z0-9_]+) does not exist", msg) or re.search(r"unconfigured table ([a-z0-9_]+)", msg)
        
        if match and attempt == 1:
            missing_table = match.group(1)
            metadata = session.cluster.metadata
            found_real_name = None
            
            for ks_meta in metadata.keyspaces.values():
                for table_name in ks_meta.tables.keys():
                    if table_name.lower() == missing_table and table_name != missing_table:
                        found_real_name = table_name
                        break
                if found_real_name: break
            
            if found_real_name:
                new_cql = re.sub(f"\\b{missing_table}\\b", f'"{found_real_name}"', query.cql, flags=re.IGNORECASE)
                if new_cql != query.cql:
                    new_query = CQLQuery(cql=new_cql, cl=query.cl, enable_tracing=query.enable_tracing)
                    return _execute_with_retry(session, new_query, attempt=2)

        return str(e)
    except (SyntaxException, NoHostAvailable) as e:
        return str(e)
    except Exception as e:
        raise e


def get_trace_info(result_set: ResultSet) -> dict[str, Any]:
    trace = result_set.get_query_trace()
    
    if isinstance(trace.duration, int):
        duration_ms = trace.duration / 1000.0
    elif trace.duration:
        duration_ms = trace.duration.total_seconds() * 1000.0
    else:
        duration_ms = 0.0

    events = []
    for e in trace.events:
        ms = e.source_elapsed.total_seconds() * 1000.0
        events.append({'description': e.description, 'source': e.source, 'elapsed_ms': ms})

    if duration_ms == 0 and events:
        duration_ms = max(e['elapsed_ms'] for e in events)

    return {
        'request_type': trace.request_type,
        'duration_ms': duration_ms,
        'coordinator': trace.coordinator,
        'parameters': trace.parameters,
        'events': events
    }
