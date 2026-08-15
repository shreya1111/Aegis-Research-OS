'use client';

import { useState } from 'react';

import { formatBytes, formatDate } from '@/lib/utils/format';
import type { Document } from '@/types/api';

import { Alert } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { DeleteDocumentDialog } from '@/components/documents/DeleteDocumentDialog';
import { DocumentStatusBadge } from '@/components/documents/DocumentStatusBadge';

export interface DocumentRowProps {
  document: Document;
  isDeleting: boolean;
  onDelete: (documentId: string) => void;
}

/**
 * One document in the list, with an expandable metadata panel and delete
 * action (design §5.7 DocumentRow + DocumentMetadataPanel, FR-C10). On mobile
 * this is a stacked row rather than a wide table (design §5.8).
 */
export function DocumentRow({
  document,
  isDeleting,
  onDelete,
}: DocumentRowProps): React.JSX.Element {
  const [expanded, setExpanded] = useState(false);
  const { metadata } = document;

  return (
    <li className="rounded-surface border">
      <div className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0 space-y-1">
          <p className="truncate font-medium">{document.filename}</p>
          <p className="text-caption text-muted-foreground">
            Uploaded {formatDate(document.uploaded_at)} · {formatBytes(metadata.size_bytes)}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <DocumentStatusBadge status={document.status} />
          <Button
            type="button"
            variant="ghost"
            size="sm"
            aria-expanded={expanded}
            onClick={() => setExpanded((value) => !value)}
          >
            {expanded ? 'Hide' : 'Details'}
          </Button>
          <DeleteDocumentDialog
            filename={document.filename}
            isDeleting={isDeleting}
            onConfirm={() => onDelete(document.id)}
            trigger={
              <Button type="button" variant="ghost" size="sm" className="text-destructive">
                Delete
              </Button>
            }
          />
        </div>
      </div>

      {expanded && (
        <div className="space-y-3 border-t p-4 text-body-sm">
          {document.status === 'failed' && metadata.failure_reason && (
            <Alert variant="destructive">{metadata.failure_reason}</Alert>
          )}
          {metadata.ocr_low_confidence && (
            <Alert variant="warning">
              This document was read with OCR at low confidence; extracted text may be unreliable.
            </Alert>
          )}
          <dl className="grid grid-cols-1 gap-x-6 gap-y-2 sm:grid-cols-2">
            <MetadataField label="Title" value={metadata.title ?? '—'} />
            <MetadataField
              label="Authors"
              value={metadata.authors.length > 0 ? metadata.authors.join(', ') : '—'}
            />
            <MetadataField
              label="Pages"
              value={metadata.page_count !== null ? String(metadata.page_count) : '—'}
            />
            <MetadataField label="Type" value={metadata.mime_type} />
            <MetadataField label="Size" value={formatBytes(metadata.size_bytes)} />
            <MetadataField label="OCR used" value={metadata.ocr_used ? 'Yes' : 'No'} />
          </dl>
        </div>
      )}
    </li>
  );
}

function MetadataField({ label, value }: { label: string; value: string }): React.JSX.Element {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-caption text-muted-foreground">{label}</dt>
      <dd className="break-words">{value}</dd>
    </div>
  );
}
