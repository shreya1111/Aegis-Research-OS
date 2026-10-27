'use client';

/**
 * Custom edge component for relationships in the knowledge graph.
 */

import React from 'react';
import { 
  BaseEdge, 
  EdgeLabelRenderer, 
  getSmoothStepPath,
  type EdgeProps 
} from 'reactflow';

import { Badge } from '@/components/ui/badge';
import { EDGE_TYPE_COLORS, EDGE_TYPE_LABELS } from '@/types/graph';

export function CustomEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  selected,
}: EdgeProps): React.JSX.Element {
  const edgeType = data?.edgeType || 'co_author';
  const weight = data?.weight || 1;
  const color = EDGE_TYPE_COLORS[edgeType as keyof typeof EDGE_TYPE_COLORS] || '#64748b';
  
  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          stroke: color,
          strokeWidth: Math.max(1, weight * 2),
          opacity: selected ? 1 : 0.7,
        }}
      />
      
      {selected && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
              pointerEvents: 'all',
            }}
            className="nodrag nopan"
          >
            <Badge 
              variant="secondary" 
              className="text-xs bg-white border"
              style={{ borderColor: color }}
            >
              {EDGE_TYPE_LABELS[edgeType as keyof typeof EDGE_TYPE_LABELS] || edgeType}
              {weight > 1 && ` (${weight.toFixed(1)})`}
            </Badge>
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}