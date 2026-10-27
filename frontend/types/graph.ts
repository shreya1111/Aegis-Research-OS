/**
 * TypeScript types for knowledge graph (Phase 7).
 */

export type NodeType = 'author' | 'topic' | 'institution';
export type EdgeType = 'co_author' | 'citation' | 'topic_membership' | 'institutional_affiliation';

export interface GraphNode {
  id: string;
  type: NodeType;
  data: {
    label: string;
    nodeType: NodeType;
    metadata: Record<string, unknown>;
    createdAt: string;
  };
  position: {
    x: number;
    y: number;
  };
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: EdgeType;
  data: {
    weight: number;
    edgeType: EdgeType;
    metadata: Record<string, unknown>;
    createdAt: string;
  };
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface NodeDetails {
  node: {
    id: string;
    name: string;
    type: NodeType;
    metadata: Record<string, unknown>;
    createdAt: string;
  };
  neighbors: Array<{
    id: string;
    name: string;
    type: NodeType;
  }>;
  connections: Array<{
    id: string;
    type: EdgeType;
    weight: number;
    sourceId: string;
    targetId: string;
    metadata: Record<string, unknown>;
  }>;
}

export interface GraphStats {
  totalNodes: number;
  totalEdges: number;
  nodesByType: Record<string, number>;
  edgesByType: Record<string, number>;
}

export interface NodeSearchResult {
  id: string;
  name: string;
  type: NodeType;
  metadata: Record<string, unknown>;
}

export interface CreateRelationshipRequest {
  sourceNodeId: string;
  targetNodeId: string;
  relationshipType: EdgeType;
  weight?: number;
  metadata?: Record<string, unknown>;
}

export const NODE_TYPE_LABELS: Record<NodeType, string> = {
  author: 'Author',
  topic: 'Topic',
  institution: 'Institution',
};

export const EDGE_TYPE_LABELS: Record<EdgeType, string> = {
  co_author: 'Co-authorship',
  citation: 'Citation',
  topic_membership: 'Topic Membership',
  institutional_affiliation: 'Institutional Affiliation',
};

export const NODE_TYPE_COLORS: Record<NodeType, string> = {
  author: '#3b82f6',    // blue
  topic: '#10b981',     // emerald
  institution: '#f59e0b', // amber
};

export const EDGE_TYPE_COLORS: Record<EdgeType, string> = {
  co_author: '#6366f1',              // indigo
  citation: '#8b5cf6',               // violet
  topic_membership: '#06b6d4',       // cyan
  institutional_affiliation: '#f97316', // orange
};