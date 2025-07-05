from random import choice
from typing import Optional

from cassanova.config.cluster_config import ClusterConnectionConfig
from cassanova.core.tools.execute_tool import execute_tool
from cassanova.core.tools.nodetool.parse_status import parse_nodetool_status
from cassanova.core.tools.tool_validation import get_tool_path
from cassanova.exceptions.nodetool_status_unavailable import NodeToolStatusUnavailable
from cassanova.models.nodetool.status import NodeToolStatus


async def get_nodetool_status(cluster_config: ClusterConnectionConfig) -> list[NodeToolStatus]:
    tool_path = get_tool_path('nodetool')
    username = cluster_config.jmx_credentials.username if cluster_config.jmx_credentials else None
    password = cluster_config.jmx_credentials.password if cluster_config.jmx_credentials else None
    random_contact = choice(cluster_config.contact_points)

    args = _format_nodetool_status_args(random_contact, username, password)
    stdout, stderr, return_code = await execute_tool(tool_path, args)

    print(return_code, stderr, stdout)
    if return_code != 0:
        raise NodeToolStatusUnavailable(stderr, return_code)
    return [NodeToolStatus(**node) for node in parse_nodetool_status(stdout)]


def _format_nodetool_status_args(host: str,
                                 username: Optional[str] = None, password: Optional[str] = None) -> list[str]:
    args = ['--host', host]
    if username and password:
        args += ['--username', username, '--password', password]
    args.append('status')
    return args
