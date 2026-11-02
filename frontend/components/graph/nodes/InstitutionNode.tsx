'use client';

/**
 * Custom node component for institution entities in the knowledge graph.
 */

import React from 'react';
import { Handle, Position, type NodeProps } from 'reactflow';
import { Building2 } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { NODE_TYPE_COLORS } from '@/types/graph';

export function InstitutionNode({ data, selected }: NodeProps): React.JSX.Element {
  return (
    <div
      className={`min-w-[120px] rounded-md border-2 bg-white px-3 py-2 shadow-md ${
        selected ? 'border-amber-500' : 'border-gray-200'
      }`}
      style={{
        borderColor: selected ? NODE_TYPE_COLORS.institution : undefined,
      }}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="h-3 w-3"
        style={{ background: NODE_TYPE_COLORS.institution }}
      />

      <div className="flex items-center space-x-2">
        <div
          className="flex h-6 w-6 items-center justify-center rounded-full"
          style={{ backgroundColor: NODE_TYPE_COLORS.institution }}
        >
          <Building2 className="h-3 w-3 text-white" />
        </div>
        <div className="flex-1">
          <div className="max-w-[100px] truncate text-sm font-medium text-gray-900">
            {data.label}
          </div>
          <Badge variant="secondary" className="text-xs">
            Institution
          </Badge>
        </div>
      </div>

      <Handle
        type="source"
        position={Position.Bottom}
        className="h-3 w-3"
        style={{ background: NODE_TYPE_COLORS.institution }}
      />
    </div>
  );
}
