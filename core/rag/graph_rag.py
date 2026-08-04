"""
core/rag/graph_rag.py - LegalGraphRAG Pipeline
Graph-based retrieval augmented generation with multi-hop reasoning
"""

import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

from core.llm import LLMMessage, get_router
from core.db import db
from core.ingestion.pipeline import EmbeddingGenerator

logger = logging.getLogger(__name__)


@dataclass
class LegalNode:
    """Node in the legal knowledge graph"""
    id: str
    node_type: str  # 'case', 'statute', 'principle', 'concept', 'issue'
    label: str
    content: str
    embedding: List[float]
    metadata: Dict = field(default_factory=dict)
    score: float = 0.0


@dataclass
class LegalEdge:
    """Edge in the legal knowledge graph"""
    source_id: str
    target_id: str
    edge_type: str  # 'cites', 'applies', 'distinguishes', 'overrules', 'follows'
    weight: float = 1.0
    metadata: Dict = field(default_factory=dict)


class LegalGraphRAG:
    """Graph-based RAG pipeline for legal reasoning"""
    
    def __init__(self):
        self.router = get_router()
        self.embedder = EmbeddingGenerator()
    
    async def build_graph(self, query: str, documents: List[Dict]) -> Dict:
        """Build legal knowledge graph from retrieved documents"""
        
        nodes = []
        edges = []
        
        # Extract entities and relationships
        for doc in documents:
            # Create case node
            node = LegalNode(
                id=doc.get('id', ''),
                node_type='case',
                label=doc.get('citation', ''),
                content=doc.get('full_text', '')[:500],
                embedding=doc.get('embedding', []),
                metadata=doc.get('metadata', {})
            )
            nodes.append(node)
            
            # Extract cited cases
            cited_cases = doc.get('cases_cited', [])
            for cited in cited_cases:
                edge = LegalEdge(
                    source_id=doc.get('id', ''),
                    target_id=cited,
                    edge_type='cites',
                    weight=1.0
                )
                edges.append(edge)
        
        return {
            'nodes': nodes,
            'edges': edges,
            'node_count': len(nodes),
            'edge_count': len(edges)
        }
    
    async def traverse_graph(self, query: str, graph: Dict, max_hops: int = 2) -> List[Dict]:
        """Traverse the knowledge graph to find relevant information"""
        
        visited = set()
        results = []
        
        # Start with the most relevant nodes
        for node in graph['nodes'][:5]:
            if node.id not in visited:
                visited.add(node.id)
                results.append({
                    'node': node,
                    'path': [node.id],
                    'score': node.score or 0.5
                })
        
        # Multi-hop traversal
        for hop in range(max_hops - 1):
            new_results = []
            for result in results:
                node_id = result['path'][-1]
                
                # Find edges from this node
                for edge in graph['edges']:
                    if edge.source_id == node_id and edge.target_id not in visited:
                        visited.add(edge.target_id)
                        target_node = self._find_node(graph['nodes'], edge.target_id)
                        if target_node:
                            new_results.append({
                                'node': target_node,
                                'path': result['path'] + [target_node.id],
                                'score': result['score'] * edge.weight * 0.8,
                                'edge_type': edge.edge_type
                            })
            
            results.extend(new_results)
            results = sorted(results, key=lambda x: x['score'], reverse=True)[:10]
        
        return results
    
    def _find_node(self, nodes: List[LegalNode], node_id: str) -> Optional[LegalNode]:
        """Find a node by ID"""
        for node in nodes:
            if node.id == node_id:
                return node
        return None
    
    async def graph_retrieve(self, query: str, top_k: int = 10) -> Dict:
        """Retrieve relevant documents using graph-based search"""
        
        # Step 1: Initial retrieval using hybrid search
        embedding = await self.embedder.generate_embedding(query)
        
        results = await db.fetch("""
            SELECT id, citation, title, full_text, embedding, metadata,
                   (1 - (embedding <=> $1)) * 0.7 + 
                   ts_rank(search_vector, plainto_tsquery('english', $2)) * 0.3 as score
            FROM case_law
            WHERE embedding IS NOT NULL
            ORDER BY score DESC
            LIMIT $3
        """, embedding, query, top_k * 2)
        
        # Step 2: Build graph
        documents = [dict(r) for r in results]
        graph = await self.build_graph(query, documents)
        
        # Step 3: Graph traversal
        traversed = await self.traverse_graph(query, graph)
        
        # Step 4: Multi-hop reasoning
        reasoning = await self._multi_hop_reasoning(query, traversed)
        
        return {
            'query': query,
            'initial_documents': documents[:top_k],
            'graph': graph,
            'traversed_nodes': traversed,
            'reasoning': reasoning
        }
    
    async def _multi_hop_reasoning(self, query: str, traversed: List[Dict]) -> str:
        """Perform multi-hop reasoning over the graph"""
        
        if not traversed:
            return "No relevant legal paths found."
        
        # Build reasoning context
        context = "Legal reasoning paths found:\n\n"
        for i, item in enumerate(traversed[:5]):
            node = item['node']
            path = ' → '.join([str(p) for p in item['path']])
            context += f"Path {i+1}: {path}\n"
            context += f"Node: {node.label}\n"
            context += f"Content: {node.content[:200]}...\n\n"
        
        messages = [
            LLMMessage(role="system", content="""You are a legal reasoning expert.
            Analyze the provided legal reasoning paths and synthesize a comprehensive answer.
            Identify legal principles, trace their application, and provide a reasoned conclusion.
            Cite the relevant legal sources from the paths."""),
            LLMMessage(role="user", content=f"Query: {query}\n\nContext:\n{context}")
        ]
        
        response = await self.router.chat(messages, complexity="complex")
        return response.content


class MultiHopReasoner:
    """Multi-hop legal reasoning engine"""
    
    def __init__(self):
        self.router = get_router()
    
    async def reason(self, query: str, graph_results: Dict) -> Dict:
        """Perform multi-hop reasoning over legal knowledge"""
        
        # Extract key entities
        entities = await self._extract_entities(query)
        
        # Find legal paths
        paths = await self._find_legal_paths(query, entities, graph_results)
        
        # Synthesize reasoning
        reasoning = await self._synthesize_reasoning(query, paths)
        
        return {
            'entities': entities,
            'paths': paths,
            'reasoning': reasoning,
            'confidence': self._calculate_confidence(paths)
        }
    
    async def _extract_entities(self, query: str) -> List[str]:
        """Extract legal entities from query"""
        messages = [
            LLMMessage(role="system", content="""Extract legal entities from the query.
            Return as JSON list. Entities: statutes, cases, legal concepts, principles."""),
            LLMMessage(role="user", content=query)
        ]
        
        response = await self.router.chat(messages, complexity="medium")
        try:
            return json.loads(response.content)
        except:
            return query.split()
    
    async def _find_legal_paths(self, query: str, entities: List[str], graph: Dict) -> List[Dict]:
        """Find legal reasoning paths"""
        paths = []
        
        for entity in entities:
            # Search for entity in graph
            for node in graph.get('nodes', []):
                if entity.lower() in node.label.lower() or entity.lower() in node.content.lower():
                    paths.append({
                        'source': entity,
                        'target': node.label,
                        'relationship': 'related_to',
                        'content': node.content[:500]
                    })
        
        return paths
    
    async def _synthesize_reasoning(self, query: str, paths: List[Dict]) -> str:
        """Synthesize legal reasoning from paths"""
        if not paths:
            return "No legal reasoning paths found for this query."
        
        context = "Legal reasoning paths:\n"
        for path in paths[:5]:
            context += f"- {path['source']} → {path['target']}: {path['content'][:200]}...\n"
        
        messages = [
            LLMMessage(role="system", content="""Synthesize legal reasoning from the provided paths.
            Identify the legal principle, trace its application, and provide a reasoned conclusion."""),
            LLMMessage(role="user", content=f"Query: {query}\n\n{context}")
        ]
        
        response = await self.router.chat(messages, complexity="complex")
        return response.content
    
    def _calculate_confidence(self, paths: List[Dict]) -> float:
        """Calculate confidence in the reasoning"""
        if not paths:
            return 0.0
        
        # More paths = more confidence (up to a point)
        path_score = min(len(paths) / 5, 1.0) * 0.6
        
        # Better relationships = better confidence
        relation_score = 0.4  # Default
        
        return path_score + relation_score