/**
 * Knowledge graph API client (Phase 7).
 */

import { apiRequest, type RequestOptions } from '@/lib/api/client';
import type {
  GraphData,
  GraphStats,
  NodeDetails,
  NodeSearchResult,
  CreateRelationshipRequest,
  NodeType,
  EdgeType,
} from '@/types/graph';

/**
 * Get knowledge graph visualization data.
 */
export async function getGraphData(
  projectId: string,
  options: {
    nodeType?: NodeType;
    edgeType?: EdgeType;
    token?: string | null;
    baseUrl?: string;
  } = {},
): Promise<GraphData> {
  const params = new URLSearchParams();
  if (options.nodeType) params.set('nodeType', options.nodeType);
  if (options.edgeType) params.set('edgeType', options.edgeType);
  
  const query = params.toString() ? `?${params.toString()}` : '';
  
  return apiRequest<GraphData>(
    `/projects/${projectId}/graph/data${query}`,
    {
      method: 'GET',
      token: options.token,
      baseUrl: options.baseUrl,
    },
  );
}

/**
 * Get knowledge graph statistics.
 */
export async function getGraphStats(
  projectId: string,
  options: RequestOptions = {},
): Promise<GraphStats> {
  return apiRequest<GraphStats>(
    `/projects/${projectId}/graph/stats`,
    {
      method: 'GET',
      ...options,
    },
  );
}

/**
 * Get detailed information about a specific node.
 */
export async function getNodeDetails(
  projectId: string,
  nodeId: string,
  options: RequestOptions = {},
): Promise<NodeDetails> {
  return apiRequest<NodeDetails>(
    `/projects/${projectId}/graph/nodes/${nodeId}`,
    {
      method: 'GET',
      ...options,
    },
  );
}

/**
 * Search for nodes by name.
 */
export async function searchNodes(
  projectId: string,
  query: string,
  options: {
    nodeType?: NodeType;
    token?: string | null;
    baseUrl?: string;
  } = {},
): Promise<NodeSearchResult[]> {
  const params = new URLSearchParams();
  params.set('q', query);
  if (options.nodeType) params.set('nodeType', options.nodeType);
  
  return apiRequest<NodeSearchResult[]>(
    `/projects/${projectId}/graph/search?${params.toString()}`,
    {
      method: 'GET',
      token: options.token,
      baseUrl: options.baseUrl,
    },
  );
}

/**
 * Create a manual relationship between nodes.
 */
export async function createRelationship(
  projectId: string,
  relationship: CreateRelationshipRequest,
  options: RequestOptions = {},
): Promise<{ id: string; message: string }> {
  return apiRequest<{ id: string; message: string }>(
    `/projects/${projectId}/graph/relationships`,
    {
      method: 'POST',
      body: relationship,
      ...options,
    },
  );
}

/**
 * Delete a node and all its relationships.
 */
export async function deleteNode(
  projectId: string,
  nodeId: string,
  options: RequestOptions = {},
): Promise<{ message: string }> {
  return apiRequest<{ message: string }>(
    `/projects/${projectId}/graph/nodes/${nodeId}`,
    {
      method: 'DELETE',
      ...options,
    },
  );
}

/**
 * Delete a specific relationship.
 */
export async function deleteRelationship(
  projectId: string,
  edgeId: string,
  options: RequestOptions = {},
): Promise<{ message: string }> {
  return apiRequest<{ message: string }>(
    `/projects/${projectId}/graph/relationships/${edgeId}`,
    {
      method: 'DELETE',
      ...options,
    },
  );
}

/**
 * Rebuild the knowledge graph from project documents.
 */
export async function rebuildGraph(
  projectId: string,
  options: RequestOptions = {},
): Promise<{ message: string }> {
  return apiRequest<{ message: string }>(
    `/projects/${projectId}/graph/rebuild`,
    {
      method: 'POST',
      ...options,
    },
  );
}