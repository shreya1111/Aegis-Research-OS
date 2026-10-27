'use client';

import React, { useState, useCallback, useEffect } from 'react';
import { useParams } from 'next/navigation';

import { GraphVisualization } from '@/components/graph/GraphVisualization';
import { NodeDetailsSidebar } from '@/components/graph/NodeDetailsSidebar';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle, BarChart3, Shuffle } from 'lucide-react';

import { getGraphData, getNodeDetails, getGraphStats, rebuildGraph } from '@/lib/api/graph';
import { getAuthToken } from '@/lib/auth/client';
import type { GraphData, NodeDetails, GraphStats } from '@/types/graph';

export default function ProjectGraphPage(): React.JSX.Element {
  const params = useParams();
  const projectId = params.id as string;

  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [nodeDetails, setNodeDetails] = useState<NodeDetails | null>(null);
  const [graphStats, setGraphStats] = useState<GraphStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadGraphData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const token = getAuthToken();
      const [data, stats] = await Promise.all([
        getGraphData(projectId, { token }),
        getGraphStats(projectId, { token }),
      ]);
      
      setGraphData(data);
      setGraphStats(stats);
    } catch (err) {
      console.error('Failed to load graph data:', err);
      setError(err instanceof Error ? err.message : 'Failed to load knowledge graph');
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  const handleNodeClick = useCallback(async (nodeId: string) => {
    try {
      const token = getAuthToken();
      const details = await getNodeDetails(projectId, nodeId, { token });
      setNodeDetails(details);
    } catch (err) {
      console.error('Failed to load node details:', err);
      setError(err instanceof Error ? err.message : 'Failed to load node details');
    }
  }, [projectId]);

  const handleCloseDetails = useCallback(() => {
    setNodeDetails(null);
  }, []);

  const handleRebuildGraph = useCallback(async () => {
    try {
      const token = getAuthToken();
      await rebuildGraph(projectId, { token });
      // Reload data after rebuild
      setTimeout(loadGraphData, 2000); // Give some time for processing
    } catch (err) {
      console.error('Failed to rebuild graph:', err);
      setError(err instanceof Error ? err.message : 'Failed to rebuild knowledge graph');
    }
  }, [projectId, loadGraphData]);

  useEffect(() => {
    loadGraphData();
  }, [loadGraphData]);

  if (loading && !graphData) {
    return (
      <div className="container mx-auto py-6">
        <div className="flex items-center space-x-2 mb-6">
          <Shuffle className="h-6 w-6" />
          <h1 className="text-2xl font-bold">Knowledge Graph</h1>
        </div>
        <div className="flex h-96 items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p>Loading knowledge graph...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <div className="border-b bg-white px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Shuffle className="h-6 w-6" />
            <h1 className="text-2xl font-bold">Knowledge Graph</h1>
          </div>
          
          <div className="flex items-center space-x-4">
            {/* Stats */}
            {graphStats && (
              <div className="flex items-center space-x-4 text-sm text-gray-600">
                <div className="flex items-center space-x-1">
                  <BarChart3 className="h-4 w-4" />
                  <span>{graphStats.totalNodes} nodes</span>
                </div>
                <div>{graphStats.totalEdges} connections</div>
              </div>
            )}
            
            {/* Actions */}
            <Button variant="outline" onClick={handleRebuildGraph}>
              Rebuild Graph
            </Button>
          </div>
        </div>
        
        {error && (
          <Alert className="mt-4">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
      </div>

      {/* Main Content */}
      <div className="flex-1 flex">
        {/* Graph Visualization */}
        <div className="flex-1">
          <GraphVisualization
            data={graphData}
            loading={loading}
            onRefresh={loadGraphData}
            onNodeClick={handleNodeClick}
            className="h-full"
          />
        </div>

        {/* Node Details Sidebar */}
        {nodeDetails && (
          <NodeDetailsSidebar
            details={nodeDetails}
            onClose={handleCloseDetails}
            className="h-full"
          />
        )}
      </div>
    </div>
  );
}
