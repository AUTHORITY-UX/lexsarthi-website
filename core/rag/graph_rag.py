"""
Graph RAG – Builds citation networks and relationship graphs from legal data.
Uses NetworkX for graph operations.
"""

import json
import pickle
import logging
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import networkx as nx
from core.config import Config
from core.rag.free_indian_rag import get_rag

logger = logging.getLogger(__name__)

class GraphRAG:
    """
    Graph-based RAG that builds a knowledge graph of legal relationships.
    Supports: citation networks, entity relationships, concept evolution.
    """

    def __init__(self):
        self.graph = nx.DiGraph()
        self.rag = get_rag()
        self._loaded = False
        self.graph_path = Config.GRAPH_PATH

    def load(self) -> bool:
        """Load the graph from cache or build from metadata."""
        if self._loaded:
            return True

        if self.graph_path.exists():
            try:
                with open(self.graph_path, 'rb') as f:
                    self.graph = pickle.load(f)
                self._loaded = True
                logger.info(f"✅ Graph RAG loaded: {len(self.graph.nodes)} nodes")
                return True
            except Exception as e:
                logger.warning(f"Graph cache load failed: {e}")

        # Build from metadata
        return self._build_from_metadata()

    def _build_from_metadata(self) -> bool:
        """Build the citation graph from RAG metadata."""
        if not self.rag.loaded or not self.rag.metadata:
            logger.warning("No metadata available for Graph RAG")
            return False

        try:
            logger.info("Building citation graph from metadata...")
            for doc in self.rag.metadata[:10000]:  # Limit for performance
                doc_id = doc.get("id") or doc.get("case_id")
                if not doc_id:
                    continue

                self.graph.add_node(
                    doc_id,
                    title=doc.get("title", ""),
                    court=doc.get("court", ""),
                    date=doc.get("date", ""),
                    citation=doc.get("citation", "")
                )

                citations = doc.get("citations", [])
                for cited in citations:
                    if isinstance(cited, dict):
                        cited_id = cited.get("id")
                    else:
                        cited_id = str(cited)
                    if cited_id:
                        self.graph.add_edge(doc_id, cited_id)

            self._loaded = True
            logger.info(f"✅ Graph built: {len(self.graph.nodes)} nodes, {len(self.graph.edges)} edges")

            # Cache the graph
            with open(self.graph_path, 'wb') as f:
                pickle.dump(self.graph, f)

            return True

        except Exception as e:
            logger.error(f"Graph build failed: {e}")
            return False

    def find_path(self, source: str, target: str) -> List[str]:
        """Find the shortest path between two nodes."""
        try:
            return nx.shortest_path(self.graph, source, target)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []

    def get_central_cases(self, top_k: int = 10) -> List[Tuple[str, float]]:
        """Get the most influential cases by degree centrality."""
        centrality = nx.degree_centrality(self.graph)
        return sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:top_k]

    def get_clusters(self) -> List[List[str]]:
        """Find communities in the citation network."""
        try:
            undirected = self.graph.to_undirected()
            communities = nx.community.louvain_communities(undirected)
            return [list(c) for c in communities]
        except Exception:
            return []

    def search_by_entity(self, entity: str, top_k: int = 10) -> List[Dict]:
        """Find nodes related to an entity."""
        results = []
        for node, attrs in self.graph.nodes(data=True):
            if entity.lower() in str(attrs.get("title", "")).lower():
                results.append({"id": node, **attrs})
                if len(results) >= top_k:
                    break
        return results

    def get_stats(self) -> Dict[str, Any]:
        return {
            "loaded": self._loaded,
            "nodes": len(self.graph.nodes),
            "edges": len(self.graph.edges),
            "components": nx.number_connected_components(self.graph.to_undirected()) if self._loaded else 0
        }

_graph_rag = None

def get_graph_rag():
    global _graph_rag
    if _graph_rag is None:
        _graph_rag = GraphRAG()
        _graph_rag.load()
    return _graph_rag