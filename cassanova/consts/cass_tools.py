import os


class CassTools:
    ALLOWED_TOOLS: tuple[str] = (
        "auditlogviewer", "cassandra-stress", "compaction-stress",
        "debug-cql", "fqltool", "generatetokens", "hash_password", "jmxtool", "nodetool",
        "sstabledump", "sstableexpiredblockers", "sstablelevelreset", "sstableloader",
        "sstablemetadata", "sstableofflinerelevel", "sstablepartitions", "sstablerepairedset",
        "sstablescrub", "sstablesplit", "sstableupgrade", "sstableutil", "sstableverify",
    )
    TOOLS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "external_tools", "cassandra-5-0-4", "bin")
