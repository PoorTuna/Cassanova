from unittest.mock import MagicMock, patch

import pytest
from cassandra.cluster import Session


@pytest.fixture
def mock_session():
    session = MagicMock(spec=Session)
    session.execute = MagicMock(return_value=[])
    session.cluster = MagicMock()
    return session
