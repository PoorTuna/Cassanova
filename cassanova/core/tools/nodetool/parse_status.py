from typing import List, Dict, Optional

from cassanova.consts.nodetool_patterns import NodeToolPatterns


def parse_nodetool_status(output: str) -> List[Dict[str, str]]:
    results = []
    lines = output.strip().splitlines()
    current_dc = None

    for line in lines:
        current_dc, node_info = _process_line(line.strip(), current_dc)
        if node_info:
            results.append(node_info)

    return results


def _process_line(line: str, current_dc: Optional[str]) -> (Optional[str], Optional[Dict[str, str]]):
    if _is_datacenter_line(line):
        return _parse_datacenter(line), None

    if _is_node_line(line):
        node_info = _parse_node_line(line, current_dc)
        return current_dc, node_info

    return current_dc, None


def _is_datacenter_line(line: str) -> bool:
    return line.startswith("Datacenter:")


def _parse_datacenter(line: str) -> str:
    return line.split(":", 1)[1].strip()


def _is_node_line(line: str) -> bool:
    return bool(NodeToolPatterns.NODE_LINE_PATTERN.match(line))


def _parse_node_line(line: str, current_dc: Optional[str] = None) -> dict[str, str]:
    match = NodeToolPatterns.NODE_LINE_PATTERN.match(line)
    if not match:
        return None

    entry = match.groupdict()
    state_code = entry.pop("state") or 'XX'
    return {
        **entry,
        **_parse_node_status(state_code),
        "dc": current_dc,
    }


def _parse_node_status(state_code: str) -> dict[str, str]:
    return {
        "status": NodeToolPatterns.STATE_MAP.get(state_code[0], "Unknown"),
        "state": NodeToolPatterns.STATE_MAP.get(state_code[1], "Unknown"),
    }
