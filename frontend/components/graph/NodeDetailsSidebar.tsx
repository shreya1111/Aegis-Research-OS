'use client';

/**
 * Sidebar component for displaying detailed information about a selected node.
 */

import React from 'react';
import { X, User, Tag, Building2, Calendar, Hash } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import type { NodeDetails, NodeType, EdgeType } from '@/types/graph';
import { NODE_TYPE_LABELS, EDGE_TYPE_LABELS, NODE_TYPE_COLORS } from '@/types/graph';

interface NodeDetailsSidebarProps {
  details: NodeDetails | null;
  onClose: () => void;
  className?: string;
}

export function NodeDetailsSidebar({
  details,
  onClose,
  className,
}: NodeDetailsSidebarProps): React.JSX.Element | null {
  if (!details) return null;

  const { node, neighbors, connections } = details;

  const getNodeIcon = (type: NodeType) => {
    switch (type) {
      case 'author':
        return <User className="h-4 w-4" />;
      case 'topic':
        return <Tag className="h-4 w-4" />;
      case 'institution':
        return <Building2 className="h-4 w-4" />;
      default:
        return <Hash className="h-4 w-4" />;
    }
  };

  return (
    <div className={`w-80 overflow-y-auto border-l border-gray-200 bg-white ${className}`}>
      <div className="p-4">
        {/* Header */}
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Node Details</h2>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Node Information */}
        <Card className="mb-4">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center space-x-2 text-base">
              <div
                className="flex h-8 w-8 items-center justify-center rounded-full"
                style={{ backgroundColor: NODE_TYPE_COLORS[node.type] }}
              >
                {getNodeIcon(node.type)}
              </div>
              <div>
                <div className="font-medium">{node.name}</div>
                <Badge variant="secondary" className="text-xs">
                  {NODE_TYPE_LABELS[node.type]}
                </Badge>
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center space-x-2 text-sm text-gray-600">
              <Calendar className="h-3 w-3" />
              <span>Created {new Date(node.createdAt).toLocaleDateString()}</span>
            </div>

            {Object.keys(node.metadata).length > 0 && (
              <div>
                <div className="mb-2 text-xs font-medium text-gray-700">Metadata</div>
                <div className="space-y-1">
                  {Object.entries(node.metadata).map(([key, value]) => (
                    <div key={key} className="flex justify-between text-xs">
                      <span className="text-gray-600">{key}:</span>
                      <span className="max-w-32 truncate text-gray-900">
                        {typeof value === 'string' ? value : JSON.stringify(value)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Neighbors */}
        {neighbors.length > 0 && (
          <Card className="mb-4">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Connected Nodes ({neighbors.length})</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="max-h-40 space-y-2 overflow-y-auto">
                {neighbors.map((neighbor) => (
                  <div
                    key={neighbor.id}
                    className="flex items-center space-x-2 rounded-md bg-gray-50 p-2"
                  >
                    <div
                      className="flex h-6 w-6 items-center justify-center rounded-full"
                      style={{ backgroundColor: NODE_TYPE_COLORS[neighbor.type] }}
                    >
                      {getNodeIcon(neighbor.type)}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm font-medium">{neighbor.name}</div>
                      <Badge variant="outline" className="text-xs">
                        {NODE_TYPE_LABELS[neighbor.type]}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Connections */}
        {connections.length > 0 && (
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Relationships ({connections.length})</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="max-h-48 space-y-3 overflow-y-auto">
                {connections.map((connection) => (
                  <div key={connection.id} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Badge variant="secondary" className="text-xs">
                        {EDGE_TYPE_LABELS[connection.type as EdgeType] || connection.type}
                      </Badge>
                      <span className="text-xs text-gray-600">
                        Weight: {connection.weight.toFixed(1)}
                      </span>
                    </div>
                    <div className="text-xs text-gray-600">
                      {connection.sourceId === node.id ? 'Outgoing' : 'Incoming'} relationship
                    </div>
                    {Object.keys(connection.metadata).length > 0 && (
                      <div className="space-y-1 text-xs">
                        {Object.entries(connection.metadata)
                          .slice(0, 2)
                          .map(([key, value]) => (
                            <div key={key} className="flex justify-between">
                              <span className="text-gray-500">{key}:</span>
                              <span className="max-w-24 truncate text-gray-700">
                                {typeof value === 'string' ? value : JSON.stringify(value)}
                              </span>
                            </div>
                          ))}
                      </div>
                    )}
                    <Separator />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
