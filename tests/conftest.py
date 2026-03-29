from unittest.mock import MagicMock

import pytest
from cassandra.cluster import Session


@pytest.fixture
def mock_session():
    session = MagicMock(spec=Session)
    session.execute = MagicMock(return_value=[])
    session.cluster = MagicMock()
    return session


@pytest.fixture
def mock_table_metadata():
    meta = MagicMock()
    columns = {}
    for name, cql_type in [("id", "int"), ("name", "text"), ("age", "int"), ("email", "text")]:
        col = MagicMock()
        col.cql_type = cql_type
        columns[name] = col
    meta.columns = columns
    meta.primary_key = [columns["id"]]
    meta.partition_key = [columns["id"]]
    meta.clustering_key = []
    return meta


@pytest.fixture
def mock_keyspace_metadata(mock_table_metadata):
    ks_meta = MagicMock()
    ks_meta.tables = {"test_table": mock_table_metadata}
    ks_meta.user_types = {}
    return ks_meta
