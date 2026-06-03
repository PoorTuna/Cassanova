from pydantic import BaseModel, Field

from cassanova.config.node_recovery_config import NodeRecoveryConfig


class K8sConfig(BaseModel):
    enabled: bool = False
    kubeconfig: str | None = None
    contexts: list[str] | None = Field(
        default=None,
        description=(
            "Kubeconfig contexts to scrape. None = all contexts in the kubeconfig. "
            "Use to scrape multiple clusters from a merged kubeconfig."
        ),
    )
    namespace: str | None = None
    cluster_include: list[str] = Field(
        default_factory=list,
        description=(
            "Glob patterns matched against K8ssandraCluster metadata.name "
            "(fnmatch syntax: *, ?, [seq]). Empty list = match all clusters."
        ),
    )
    cluster_exclude: list[str] = Field(
        default_factory=list,
        description=(
            "Glob patterns matched against K8ssandraCluster metadata.name. "
            "Exclude takes precedence over include."
        ),
    )
    suffix: str = "-service"
    periodic_discovery_enabled: bool = Field(
        default=False, description="Enable periodic discovery of K8s clusters"
    )
    discovery_interval_seconds: int = Field(
        default=60, description="Interval in seconds for periodic discovery"
    )
    external_only: bool = Field(
        default=False,
        description=(
            "When true, skip cluster_ip and svc.cluster.local DNS fallbacks. "
            "Only LoadBalancer ingress IPs and external_ips are accepted as contact points. "
            "Required when Cassanova runs outside the target Kubernetes cluster."
        ),
    )
    stale_threshold: int = Field(
        default=3,
        ge=1,
        description=(
            "Number of consecutive missed discovery scans before a discovered cluster is evicted. "
            "Static clusters are never evicted."
        ),
    )
    node_recovery: NodeRecoveryConfig = NodeRecoveryConfig()
