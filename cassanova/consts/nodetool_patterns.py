import re


class NodeToolPatterns:
    NODE_LINE_PATTERN = re.compile(
        r"^(?P<state>[UD][NLJM])\s+"
        r"(?P<address>\S+)\s+"
        r"(?P<load>\S+\s+\S+)\s+"
        r"(?P<tokens>\d+)\s+"
        r"(?P<owns>[\d.]+)%?\s+"
        r"(?P<host_id>[a-f0-9-]+)\s+"
        r"(?P<rack>\S+)$"
    )

    STATE_MAP = {
        "U": "Up",
        "D": "Down",
        "N": "Normal",
        "L": "Leaving",
        "J": "Joining",
        "M": "Moving"
    }
