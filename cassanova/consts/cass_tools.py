class CassTools:
    ALLOWED_TOOLS: tuple[str] = (
        "auditlogviewer", "cassandra-stress", "compaction-stress",
        "debug-cql", "fqltool", "generatetokens", "hash_password", "jmxtool", "nodetool",
        "sstabledump", "sstableexpiredblockers", "sstablelevelreset", "sstableloader",
        "sstablemetadata", "sstableofflinerelevel", "sstablepartitions", "sstablerepairedset",
        "sstablescrub", "sstablesplit", "sstableupgrade", "sstableutil", "sstableverify",
    )
    TOOLS_DIR = "/home/ubuntu/pycharm/app/cassanova/external_tools/cassandra-5-0-4/bin/"
