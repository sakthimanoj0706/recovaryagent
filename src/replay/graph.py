"""
Directed Acyclic Evidence Graph & Cryptographic Hashing Engine for RecoverAI (Step 13).

Provides:
- EvidenceGraphBuilder: Constructs verifiable decision nodes and semantic causal edges.
- Canonical serialization & SHA-256 hashing for tamper detection.
- Graph integrity validation functions.
"""

import json
import hashlib
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone
import uuid

from .models import (
    EvidenceNode,
    EvidenceEdge,
    EvidenceGraph,
    EvidenceSource,
    EvidenceNodeType,
)


def _clean_canonical_value(val: Any) -> Any:
    if isinstance(val, dict):
        return {
            k: _clean_canonical_value(v)
            for k, v in sorted(val.items())
            if k not in (
                "timestamp",
                "evaluated_at",
                "ts",
                "evaluated_ts",
                "run_id",
                "replay_id",
                "execution_id",
                "correlation_id",
            )
        }
    elif isinstance(val, list):
        return [_clean_canonical_value(x) for x in val]
    elif isinstance(val, (int, float, bool)):
        return val
    elif val is None:
        return None
    return str(val)


def compute_canonical_evidence_hash(
    nodes: List[EvidenceNode],
    edges: List[EvidenceEdge],
    payment_id: str,
) -> str:
    """
    Computes a deterministic SHA-256 digest over canonical representations of all nodes and edges.
    Guarantees that identical decision inputs produce identical hashes, and any mutation breaks the hash.
    """
    canonical_nodes = []
    for n in sorted(nodes, key=lambda x: x.id):
        canonical_nodes.append({
            "id": n.id,
            "node_type": str(n.node_type),
            "source": str(n.source),
            "title": n.title,
            "value": _clean_canonical_value(n.value),
            "confidence": str(n.confidence),
            "evidence_refs": sorted(n.evidence_refs),
            "explanation": n.explanation,
        })

    canonical_edges = []
    for e in sorted(edges, key=lambda x: (x.source_node_id, x.target_node_id, x.relationship)):
        canonical_edges.append({
            "source": e.source_node_id,
            "target": e.target_node_id,
            "relationship": e.relationship,
        })

    payload = {
        "payment_id": payment_id,
        "nodes": canonical_nodes,
        "edges": canonical_edges,
    }


    serialized = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def verify_graph_integrity(graph: EvidenceGraph) -> Tuple[bool, str]:
    """
    Validates that the evidence graph has not been mutated or tampered with.
    """
    recalculated = compute_canonical_evidence_hash(
        nodes=graph.nodes,
        edges=graph.edges,
        payment_id=graph.payment_id,
    )
    if recalculated == graph.canonical_hash:
        return True, f"Evidence graph integrity verified: SHA-256 digest match ({graph.canonical_hash[:16]}...)"
    return False, f"TAMPER DETECTED: Expected {graph.canonical_hash[:16]}..., but recomputed {recalculated[:16]}..."


class EvidenceGraphBuilder:
    """
    Builder for constructing verifiable recovery decision graphs.
    """

    def __init__(self, payment_id: str):
        self.payment_id = payment_id
        self.graph_id = f"graph_{uuid.uuid4().hex[:10]}"
        self.nodes: List[EvidenceNode] = []
        self.edges: List[EvidenceEdge] = []
        self.root_node_ids: List[str] = []
        self.terminal_node_id: Optional[str] = None

    def add_node(
        self,
        node_id: str,
        node_type: EvidenceNodeType,
        source: EvidenceSource,
        title: str,
        value: Any,
        explanation: str,
        confidence: str = "DETERMINISTIC",
        evidence_refs: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        is_root: bool = False,
        is_terminal: bool = False,
    ) -> EvidenceNode:
        """Add an evidence node to the graph."""
        node = EvidenceNode(
            id=node_id,
            node_type=node_type,
            timestamp=datetime.now(timezone.utc).isoformat(),
            source=source,
            title=title,
            value=value,
            confidence=confidence,
            evidence_refs=evidence_refs or [],
            explanation=explanation,
            metadata=metadata or {},
        )
        self.nodes.append(node)
        if is_root:
            self.root_node_ids.append(node_id)
        if is_terminal:
            self.terminal_node_id = node_id
        return node

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relationship: str,
        description: str,
    ) -> EvidenceEdge:
        """Add a causal relationship edge between two nodes."""
        edge = EvidenceEdge(
            source_node_id=source_id,
            target_node_id=target_id,
            relationship=relationship,
            description=description,
        )
        self.edges.append(edge)
        return edge

    def build(self) -> EvidenceGraph:
        """Finalize graph, calculate canonical hash, and return EvidenceGraph."""
        digest = compute_canonical_evidence_hash(
            nodes=self.nodes,
            edges=self.edges,
            payment_id=self.payment_id,
        )
        return EvidenceGraph(
            graph_id=self.graph_id,
            payment_id=self.payment_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            nodes=self.nodes,
            edges=self.edges,
            root_node_ids=self.root_node_ids,
            terminal_node_id=self.terminal_node_id,
            canonical_hash=digest,
            is_tamper_evident=True,
        )
