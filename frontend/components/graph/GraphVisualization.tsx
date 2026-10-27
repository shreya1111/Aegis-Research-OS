'use client';

/**
 * Knowledge graph visualization component using React Flow.
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type NodeTypes,
  type EdgeTypes,
  ConnectionMode,
  Panel,
} from 'reactflow';
import 'reactflow/dist/style.css';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@radix-ui/react-separator';
import { RefreshCw, Filter, Info } from 'lucide-react';

import type { 
  GraphData, 
  GraphNode as GraphNodeType, 
  NodeType, 
  EdgeType,
  NodeDetails,
} from '@/types/graph';
import { NODE_TYPE_COLORS } from '@/types/graph';
import { AuthorNode } from './nodes/AuthorNode';
import { TopicNode } from './nodes/TopicNode';
import { InstitutionNode } from './nodes/InstitutionNode';
import { CustomEdge } from './edges/CustomEdge';

const nodeTypes: NodeTypes = {
  author: AuthorNode,
  topic: TopicNode,
  institution: InstitutionNode,
};

const edgeTypes: EdgeTypes = {
  co_author: CustomEdge,
  citation: CustomEdge,
  topic_membership: CustomEdge,
  institutional_affiliation: CustomEdge,
};

interface GraphVisualizationProps {
  data: GraphData | null;
  loading: boolean;
  onRefresh: () => void;
  onNodeClick?: (nodeId: string) => void;
  onNodeDetails?: (details: NodeDetails | null) => void;
  className?: string;
}

export function GraphVisualization({
  data,
  loading,
  onRefresh,
  onNodeClick,
  className,
}: GraphVisualizationProps): React.JSX.Element {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNodeType, setSelectedNodeType] = useState<NodeType | 'all'>('all');
  const [selectedEdgeType, setSelectedEdgeType] = useState<EdgeType | 'all'>('all');

  // Convert graph data to React Flow format
  useEffect(() => {
    if (!data) {
      setNodes([]);
      setEdges([]);
      return;
    }

    // Apply layout algorithm (simple circle layout for demo)
    const layoutNodes = applyLayoutAlgorithm(data.nodes);
    setNodes(layoutNodes);
    setEdges(data.edges as Edge[]);
  }, [data, setNodes, setEdges]);

  // Filter nodes and edges based on selected types
  const filteredNodes = useMemo(() => {
    return nodes.filter(node => {
      if (selectedNodeType === 'all') return true;
      return node.data.nodeType === selectedNodeType;
    });
  }, [nodes, selectedNodeType]);

  const filteredEdges = useMemo(() => {
    return edges.filter(edge => {
      if (selectedEdgeType === 'all') return true;
      return edge.data?.edgeType === selectedEdgeType;
    });
  }, [edges, selectedEdgeType]);

  const onNodeClickHandler = useCallback((_event: React.MouseEvent, node: Node) => {
    onNodeClick?.(node.id);
  }, [onNodeClick]);

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="flex items-center space-x-2">
          <RefreshCw className="h-4 w-4 animate-spin" />
          <span>Loading knowledge graph...</span>
        </div>
      </div>
    );
  }

  if (!data || (data.nodes.length === 0 && data.edges.length === 0)) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Info className="h-5 w-5" />
            <span>Knowledge Graph</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <p className="text-gray-600 mb-4">
              No entities found in this project yet. Upload and process some documents to see relationships between authors, topics, and institutions.
            </p>
            <Button onClick={onRefresh} variant="outline">
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh Graph
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className={`h-full w-full ${className}`}>
      <ReactFlow
        nodes={filteredNodes}
        edges={filteredEdges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClickHandler}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        connectionMode={ConnectionMode.Loose}
        fitView
        attributionPosition="bottom-left"
      >
        <Background />
        <Controls />
        <MiniMap
          nodeColor={getNodeColor}
          maskColor="rgba(0, 0, 0, 0.2)"
          position="top-right"
        />
        
        {/* Filter Panel */}
        <Panel position="top-left">
          <Card className="w-64">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center space-x-2">
                <Filter className="h-4 w-4" />
                <span>Filters</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {/* Node Type Filter */}
              <div>
                <label className="text-xs font-medium text-gray-700 block mb-1">
                  Node Type
                </label>
                <select
                  value={selectedNodeType}
                  onChange={(e) => setSelectedNodeType(e.target.value as NodeType | 'all')}
                  className="w-full text-sm border rounded px-2 py-1"
                >
                  <option value="all">All Types</option>
                  <option value="author">Authors</option>
                  <option value="topic">Topics</option>
                  <option value="institution">Institutions</option>
                </select>
              </div>

              {/* Edge Type Filter */}
              <div>
                <label className="text-xs font-medium text-gray-700 block mb-1">
                  Relationship Type
                </label>
                <select
                  value={selectedEdgeType}
                  onChange={(e) => setSelectedEdgeType(e.target.value as EdgeType | 'all')}
                  className="w-full text-sm border rounded px-2 py-1"
                >
                  <option value="all">All Relationships</option>
                  <option value="co_author">Co-authorship</option>
                  <option value="citation">Citations</option>
                  <option value="topic_membership">Topic Membership</option>
                  <option value="institutional_affiliation">Affiliations</option>
                </select>
              </div>

              <Separator />

              {/* Stats */}
              <div className="space-y-2">
                <div className="flex justify-between text-xs">
                  <span>Nodes:</span>
                  <Badge variant="secondary">{filteredNodes.length}</Badge>
                </div>
                <div className="flex justify-between text-xs">
                  <span>Edges:</span>
                  <Badge variant="secondary">{filteredEdges.length}</Badge>
                </div>
              </div>

              <Button
                onClick={onRefresh}
                variant="outline"
                size="sm"
                className="w-full"
              >
                <RefreshCw className="h-3 w-3 mr-2" />
                Refresh
              </Button>
            </CardContent>
          </Card>
        </Panel>
      </ReactFlow>
    </div>
  );
}

// Helper function to get node color for minimap
function getNodeColor(node: Node): string {
  const nodeType = node.data.nodeType as NodeType;
  return NODE_TYPE_COLORS[nodeType] || '#64748b';
}

// Simple circle layout algorithm
function applyLayoutAlgorithm(nodes: GraphNodeType[]): Node[] {
  const centerX = 400;
  const centerY = 300;
  const radius = 200;

  return nodes.map((node, index) => {
    const angle = (index * 2 * Math.PI) / nodes.length;
    const x = centerX + radius * Math.cos(angle);
    const y = centerY + radius * Math.sin(angle);

    return {
      ...node,
      position: { x, y },
    };
  });
}