"""
core/reasoning/multi_hop.py - Multi-Hop Legal Reasoning
"""

import json
import logging
from typing import List, Dict, Any, Optional
from collections import defaultdict

from core.db import db
from core.llm import LLMMessage, get_router

logger = logging.getLogger(__name__)


class MultiHopReasoner:
    """Multi-hop legal reasoning engine"""
    
    def __init__(self):
        self.router = get_router()
        self.max_hops = 3
    
    async def reason(self, query: str, context: Dict = None) -> Dict:
        """Perform multi-hop reasoning"""
        
        # Step 1: Extract entities
        entities = await self._extract_entities(query)
        
        # Step 2: Build reasoning graph
        graph = await self._build_reasoning_graph(query, entities)
        
        # Step 3: Traverse graph
        paths = await self._traverse_graph(graph, entities)
        
        # Step 4: Synthesize reasoning
        synthesis = await self._synthesize_reasoning(query, paths)
        
        # Step 5: Generate conclusion
        conclusion = await self._generate_conclusion(query, synthesis, paths)
        
        return {
            'query': query,
            'entities': entities,
            'reasoning_paths': paths,
            'synthesis': synthesis,
            'conclusion': conclusion,
            'confidence': self._calculate_confidence(paths)
        }
    
    async def _extract_entities(self, query: str) -> List[str]:
        """Extract legal entities from query"""
        messages = [
            LLMMessage(role="system", content="""Extract legal entities from the query.
            Return as JSON array of strings. Entities: cases, statutes, legal concepts, parties."""),
            LLMMessage(role="user", content=query)
        ]
        
        try:
            response = await self.router.chat(messages, complexity="medium")
            return json.loads(response.content)
        except:
            return query.split()[:5]
    
    async def _build_reasoning_graph(self, query: str, entities: List[str]) -> Dict:
        """Build reasoning graph from entities"""
        nodes = []
        edges = []
        
        for entity in entities:
            # Search for entity in database
            try:
                rows = await db.fetchall("""
                    SELECT id, title, content FROM moat_knowledge
                    WHERE content ILIKE $1
                    LIMIT 10
                """, f'%{entity}%')
                
                for row in rows:
                    node = {
                        'id': row['id'],
                        'label': entity,
                        'content': row['content'][:500],
                        'type': 'knowledge'
                    }
                    nodes.append(node)
                    
                    # Add edges between related entities
                    for other in entities:
                        if other != entity and other in row['content']:
                            edges.append({
                                'source': entity,
                                'target': other,
                                'type': 'related'
                            })
            except:
                pass
        
        return {'nodes': nodes, 'edges': edges}
    
    async def _traverse_graph(self, graph: Dict, entities: List[str]) -> List[Dict]:
        """Traverse graph to find reasoning paths"""
        paths = []
        visited = set()
        
        for entity in entities[:3]:
            path = await self._dfs_traverse(entity, graph, visited, depth=0)
            if path:
                paths.append(path)
        
        return paths
    
    async def _dfs_traverse(self, node: str, graph: Dict, visited: set, depth: int) -> List[Dict]:
        """Depth-first search traversal"""
        if depth > self.max_hops or node in visited:
            return []
        
        visited.add(node)
        path = [{'node': node, 'depth': depth}]
        
        # Find connected nodes
        for edge in graph.get('edges', []):
            if edge['source'] == node:
                child = edge['target']
                if child not in visited:
                    child_path = await self._dfs_traverse(child, graph, visited, depth + 1)
                    if child_path:
                        path.extend(child_path)
                        break
        
        return path
    
    async def _synthesize_reasoning(self, query: str, paths: List[Dict]) -> str:
        """Synthesize reasoning from paths"""
        if not paths:
            return "No reasoning paths found."
        
        context = f"Query: {query}\n\nReasoning Paths:\n"
        for path in paths[:3]:
            context += f"{' → '.join([p['node'] for p in path])}\n"
        
        messages = [
            LLMMessage(role="system", content="Synthesize legal reasoning from the provided paths. Be concise and logical."),
            LLMMessage(role="user", content=context)
        ]
        
        response = await self.router.chat(messages, complexity="complex")
        return response.content
    
    async def _generate_conclusion(self, query: str, synthesis: str, paths: List[Dict]) -> str:
        """Generate final conclusion"""
        messages = [
            LLMMessage(role="system", content="Based on the reasoning, generate a clear legal conclusion."),
            LLMMessage(role="user", content=f"Query: {query}\n\nReasoning: {synthesis}")
        ]
        
        response = await self.router.chat(messages, complexity="complex")
        return response.content
    
    def _calculate_confidence(self, paths: List[Dict]) -> float:
        """Calculate confidence in reasoning"""
        if not paths:
            return 0.0
        
        # More paths = more confidence
        path_score = min(len(paths) / 5, 1.0) * 0.6
        
        # Longer paths = more reasoning
        avg_length = sum(len(p) for p in paths) / len(paths)
        length_score = min(avg_length / 5, 1.0) * 0.4
        
        return path_score + length_score


multi_hop_reasoner = MultiHopReasoner()