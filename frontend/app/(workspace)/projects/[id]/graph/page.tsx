'use client';

import { AlertCircle, Database, Loader2, Network } from 'lucide-react';
import { useParams } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

import { getGraphData, getGraphStats, getNodeDetails, rebuildGraph } from '@/lib/api/graph';
import { getAuthToken } from '@/lib/auth/client';
import type { GraphData, GraphStats, NodeDetails } from '@/types/graph';

import { GraphVisualization } from '@/components/graph/GraphVisualization';
import { NodeDetailsSidebar } from '@/components/graph/NodeDetailsSidebar';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';

export default function ProjectGraphPage(): React.JSX.Element {
  const params = useParams<{ id: string }>();
  const projectId = params.id;

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
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load the knowledge graph.');
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  const handleNodeClick = useCallback(
    async (nodeId: string) => {
      try {
        const token = getAuthToken();
        setNodeDetails(await getNodeDetails(projectId, nodeId, { token }));
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : 'Could not load node details.');
      }
    },
    [projectId],
  );

  const handleCloseDetails = useCallback(() => {
    setNodeDetails(null);
  }, []);

  const handleRebuildGraph = useCallback(async () => {
    try {
      const token = getAuthToken();
      await rebuildGraph(projectId, { token });
      // Extraction runs in the background; give it a moment before reloading.
      window.setTimeout(() => void loadGraphData(), 2000);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not rebuild the graph.');
    }
  }, [loadGraphData, projectId]);

  useEffect(() => {
    void loadGraphData();
  }, [loadGraphData]);

  if (loading && !graphData) {
    return (
      <div className="flex flex-col gap-6 p-6">
        <div className="flex items-center gap-2">
          <Network className="size-5 text-muted-foreground" aria-hidden />
          <h1 className="text-h2 font-semibold">Knowledge graph</h1>
        </div>
        <div className="flex h-96 items-center justify-center rounded-surface border border-dashed">
          <p className="flex items-center gap-2 text-body-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin" aria-hidden />
            Loading graph…
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b px-6 py-4">
        <div className="flex items-center gap-2">
          <Network className="size-5 text-muted-foreground" aria-hidden />
          <h1 className="text-h2 font-semibold">Knowledge graph</h1>
        </div>

        <div className="flex flex-wrap items-center gap-4">
          {graphStats && (
            <p className="flex items-center gap-2 text-body-sm text-muted-foreground">
              <Database className="size-4" aria-hidden />
              <span>{graphStats.totalNodes.toLocaleString()} nodes</span>
              <span aria-hidden>·</span>
              <span>{graphStats.totalEdges.toLocaleString()} connections</span>
            </p>
          )}
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => void handleRebuildGraph()}
          >
            Rebuild graph
          </Button>
        </div>
      </div>

      {error && (
        <div className="px-6 pt-4">
          <Alert variant="destructive">
            <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        </div>
      )}

      <div className="flex min-h-0 flex-1">
        <div className="min-w-0 flex-1">
          <GraphVisualization
            data={graphData}
            loading={loading}
            onRefresh={loadGraphData}
            onNodeClick={handleNodeClick}
            className="h-full"
          />
        </div>

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
