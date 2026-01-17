from typing import Any, NoReturn

from cassandra import InvalidRequest
from cassandra.cluster import Session, ResultSet, NoHostAvailable
from cassandra.protocol import SyntaxException
from cassandra.query import SimpleStatement

from cassanova.models.cql_query import CQLQuery


def execute_query_cql(session: Session, query: CQLQuery) -> list[dict[str, Any]] | str | NoReturn:
    statement = SimpleStatement(query_string=query.cql, consistency_level=query.cl)
    try:
        result_set = session.execute(statement, trace=query.enable_tracing)
        result = [row._asdict() for row in result_set]
        if query.enable_tracing:
            result = {'result': result, 'trace': get_trace_info(result_set)}
        return {'result': result}
    except (SyntaxException, InvalidRequest, NoHostAvailable) as e:
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
