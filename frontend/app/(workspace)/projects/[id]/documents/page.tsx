'use client';

import { useParams } from 'next/navigation';
import { useCallback, useEffect, useRef, useState } from 'react';

import { ApiError } from '@/lib/api/client';
import { deleteDocument, listDocuments, uploadDocument } from '@/lib/api/documents';
import { useAuth } from '@/lib/auth/auth-context';
import { useToast } from '@/lib/toast/toast-context';
import type { Document } from '@/types/api';

import { Alert } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { DocumentDropzone } from '@/components/documents/DocumentDropzone';
import { DocumentRow } from '@/components/documents/DocumentRow';
import { EmptyState } from '@/components/feedback/EmptyState';
import { Skeleton } from '@/components/feedback/Skeleton';

type LoadState = 'loading' | 'ready' | 'error';

//: Poll interval while any document is still being processed (design §5.11:
//: "observe progress (poll or stream)"). Ingestion is asynchronous, so the
//: list refreshes until every document reaches a terminal state.
const POLL_INTERVAL_MS = 2500;

function hasInFlightDocuments(documents: Document[]): boolean {
  return documents.some((doc) => doc.status === 'pending' || doc.status === 'processing');
}

export default function ProjectDocumentsPage(): React.JSX.Element {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const { getValidAccessToken } = useAuth();
  const { notify } = useToast();

  const [documents, setDocuments] = useState<Document[]>([]);
  const [loadState, setLoadState] = useState<LoadState>('loading');
  const [isUploading, setIsUploading] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const pollRef = useRef<number | null>(null);

  const fetchDocuments = useCallback(
    async (mode: 'initial' | 'refresh') => {
      if (mode === 'initial') {
        setLoadState('loading');
      }
      try {
        const token = await getValidAccessToken();
        if (!token) {
          setLoadState('error');
          return;
        }
        setDocuments(await listDocuments(token, projectId));
        setLoadState('ready');
      } catch {
        if (mode === 'initial') {
          setLoadState('error');
        }
      }
    },
    [getValidAccessToken, projectId],
  );

  useEffect(() => {
    void fetchDocuments('initial');
  }, [fetchDocuments]);

  // Poll only while work is in flight; stop as soon as everything settles.
  useEffect(() => {
    if (!hasInFlightDocuments(documents)) {
      return;
    }
    pollRef.current = window.setInterval(() => {
      void fetchDocuments('refresh');
    }, POLL_INTERVAL_MS);
    return () => {
      if (pollRef.current !== null) {
        window.clearInterval(pollRef.current);
      }
    };
  }, [documents, fetchDocuments]);

  const handleUpload = useCallback(
    async (files: File[]) => {
      setIsUploading(true);
      try {
        const token = await getValidAccessToken();
        if (!token) {
          notify('error', 'Your session has expired. Please sign in again.');
          return;
        }
        for (const file of files) {
          try {
            await uploadDocument(token, projectId, file);
            notify('success', `"${file.name}" uploaded and queued for processing.`);
          } catch (caught) {
            notify(
              'error',
              caught instanceof ApiError
                ? `"${file.name}": ${caught.message}`
                : `"${file.name}" could not be uploaded.`,
            );
          }
        }
        await fetchDocuments('refresh');
      } finally {
        setIsUploading(false);
      }
    },
    [fetchDocuments, getValidAccessToken, notify, projectId],
  );

  const handleDelete = useCallback(
    async (documentId: string) => {
      setDeletingId(documentId);
      try {
        const token = await getValidAccessToken();
        if (!token) {
          notify('error', 'Your session has expired. Please sign in again.');
          return;
        }
        await deleteDocument(token, documentId);
        setDocuments((current) => current.filter((doc) => doc.id !== documentId));
        notify('success', 'Document deleted.');
      } catch (caught) {
        notify(
          'error',
          caught instanceof ApiError ? caught.message : 'Could not delete the document.',
        );
      } finally {
        setDeletingId(null);
      }
    },
    [getValidAccessToken, notify],
  );

  return (
    <div className="container flex flex-col gap-6 py-10">
      <div>
        <h1 className="text-h1 font-semibold">Documents</h1>
        <p className="text-body-sm text-muted-foreground">
          Upload PDFs and Word documents to make them searchable and citable in this project.
        </p>
      </div>

      <DocumentDropzone onFilesSelected={handleUpload} disabled={isUploading} />

      {loadState === 'loading' && (
        <div className="flex flex-col gap-3">
          {Array.from({ length: 3 }, (_, index) => (
            <Skeleton key={index} className="h-16 w-full" />
          ))}
        </div>
      )}

      {loadState === 'error' && (
        <Alert variant="destructive" className="flex-col items-start gap-3">
          <span>Could not load documents.</span>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => void fetchDocuments('initial')}
          >
            Retry
          </Button>
        </Alert>
      )}

      {loadState === 'ready' && documents.length === 0 && (
        <EmptyState
          title="No documents yet"
          description="Upload a PDF or DOCX above. Once processed, its text becomes searchable and citable across this project."
        />
      )}

      {loadState === 'ready' && documents.length > 0 && (
        <ul className="flex flex-col gap-3">
          {documents.map((document) => (
            <DocumentRow
              key={document.id}
              document={document}
              isDeleting={deletingId === document.id}
              onDelete={handleDelete}
            />
          ))}
        </ul>
      )}
    </div>
  );
}
