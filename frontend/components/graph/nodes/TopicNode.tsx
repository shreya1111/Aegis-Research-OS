'use client';

/**
 * Custom node component for topic entities in the knowledge graph.
 */

import React from 'react';
import { Handle, Position, type NodeProps } from 'reactflow';
import { Tag } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { NODE_TYPE_COLORS } from '@/types/graph';

export function TopicNode({ data, selected }: NodeProps): React.JSX.Element {
  return (
    <div
      className={`px-3 py-2 shadow-md rounded-md bg-white border-2 min-w-[120px] ${
        selected ? 'border-emerald-500' : 'border-gray-200'
      }`}
      style={{
        borderColor: selected ? NODE_TYPE_COLORS.topic : undefined,
      }}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="w-3 h-3"
        style={{ background: NODE_TYPE_COLORS.topic }}
      />
      
      <div className="flex items-center space-x-2">
        <div
          className="flex items-center justify-center w-6 h-6 rounded-full"
          style={{ backgroundColor: NODE_TYPE_COLORS.topic }}
        >
          <Tag className="w-3 h-3 text-white" />
        </div>
        <div className="flex-1">
          <div className="font-medium text-sm text-gray-900 truncate max-w-[100px]">
            {data.label}
          </div>
          <Badge variant="secondary" className="text-xs">
            Topic
          </Badge>
        </div>
      </div>

      <Handle
        type="source"
        position={Position.Bottom}
        className="w-3 h-3"
        style={{ background: NODE_TYPE_COLORS.topic }}
      />
    </div>
  );
}