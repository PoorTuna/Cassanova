from typing import Any, NoReturn

from cassandra import InvalidRequest
from cassandra.cluster import Session, ResultSet
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
    except (SyntaxException, InvalidRequest) as e:
        return str(e)
    except Exception as e:
        raise e


def get_trace_info(result_set: ResultSet) -> dict[str, Any]:
    trace = result_set.get_query_trace()
    trace_info = {
        'request_type': trace.request_type,
        'duration': trace.duration,
        'coordinator': trace.coordinator,
        'parameters': trace.parameters,
        'events': [{'description': e.description, 'source': e.source, 'duration': e.source_elapsed.total_seconds()} for e in
                   trace.events]
    }
    return trace_info
