import uuid
from collections import namedtuple
from datetime import datetime

from cassanova.core.constructors.serialize_to_primitive import serialize_to_primitive


class TestSerializeToPrimitive:
    def test_none_passthrough(self):
        assert serialize_to_primitive(None) is None

    def test_str_passthrough(self):
        assert serialize_to_primitive("hello") == "hello"

    def test_int_passthrough(self):
        assert serialize_to_primitive(42) == 42

    def test_float_passthrough(self):
        assert serialize_to_primitive(3.14) == 3.14

    def test_bool_passthrough(self):
        assert serialize_to_primitive(True) is True
        assert serialize_to_primitive(False) is False

    def test_dict_recursive(self):
        nested = {"a": {"b": [1, 2, 3]}, "c": None}
        result = serialize_to_primitive(nested)
        assert result == {"a": {"b": [1, 2, 3]}, "c": None}

    def test_list_recursive(self):
        assert serialize_to_primitive([1, "two", None]) == [1, "two", None]

    def test_tuple_converted_to_list(self):
        assert serialize_to_primitive((1, 2, 3)) == [1, 2, 3]

    def test_set_converted_to_list(self):
        result = serialize_to_primitive({42})
        assert result == [42]

    def test_named_tuple_via_asdict(self):
        Point = namedtuple("Point", ["x", "y"])
        result = serialize_to_primitive(Point(10, 20))
        assert result == {"x": 10, "y": 20}

    def test_object_with_as_cql_query(self):
        class FakeCqlType:
            def as_cql_query(self):
                return "text"

        assert serialize_to_primitive(FakeCqlType()) == "text"

    def test_object_with_dict_attr(self):
        class Simple:
            def __init__(self):
                self.name = "alice"
                self.age = 30

        result = serialize_to_primitive(Simple())
        assert result == {"name": "alice", "age": 30}

    def test_private_attrs_excluded(self):
        class WithPrivate:
            def __init__(self):
                self._secret = "hidden"
                self.visible = "shown"

        result = serialize_to_primitive(WithPrivate())
        assert result == {"visible": "shown"}
        assert "_secret" not in result

    def test_fallback_to_str(self):
        uid = uuid.UUID("12345678-1234-5678-1234-567812345678")
        assert serialize_to_primitive(uid) == str(uid)

        now = datetime(2025, 1, 1, 12, 0, 0)
        assert serialize_to_primitive(now) == str(now)

    def test_nested_complex_structure(self):
        Record = namedtuple("Record", ["id", "value"])
        data = {
            "records": [Record(1, "a"), Record(2, "b")],
            "meta": {"count": 2},
        }
        result = serialize_to_primitive(data)
        assert result == {
            "records": [{"id": 1, "value": "a"}, {"id": 2, "value": "b"}],
            "meta": {"count": 2},
        }
