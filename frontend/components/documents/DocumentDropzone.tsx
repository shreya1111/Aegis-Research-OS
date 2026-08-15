'use client';

import { useCallback, useRef, useState } from 'react';

import { cn } from '@/lib/utils/cn';

import { Button } from '@/components/ui/button';

const ACCEPTED_EXTENSIONS = ['.pdf', '.docx'];
const ACCEPTED_ATTRIBUTE = ACCEPTED_EXTENSIONS.join(',');

export interface DocumentDropzoneProps {
  onFilesSelected: (files: File[]) => void;
  disabled?: boolean;
}

/**
 * Drag-and-drop upload target (design §5.7, FR-C). Accepts PDF and DOCX; the
 * backend re-validates every upload, so client-side filtering here is purely a
 * UX convenience (design §9.3 rule 1). Fully keyboard-operable (design §5.9).
 */
export function DocumentDropzone({
  onFilesSelected,
  disabled = false,
}: DocumentDropzoneProps): React.JSX.Element {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const emit = useCallback(
    (fileList: FileList | null) => {
      if (!fileList || fileList.length === 0) {
        return;
      }
      onFilesSelected(Array.from(fileList));
    },
    [onFilesSelected],
  );

  function handleDrop(event: React.DragEvent<HTMLDivElement>): void {
    event.preventDefault();
    setIsDragging(false);
    if (disabled) {
      return;
    }
    emit(event.dataTransfer.files);
  }

  function openFilePicker(): void {
    if (!disabled) {
      inputRef.current?.click();
    }
  }

  return (
    <div
      role="button"
      tabIndex={disabled ? -1 : 0}
      aria-disabled={disabled}
      aria-label="Upload documents. Drag and drop, or activate to browse."
      onClick={openFilePicker}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          openFilePicker();
        }
      }}
      onDragOver={(event) => {
        event.preventDefault();
        if (!disabled) setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
      className={cn(
        'flex flex-col items-center justify-center gap-3 rounded-surface border-2 border-dashed px-6 py-12 text-center transition-colors',
        disabled && 'cursor-not-allowed opacity-60',
        !disabled && 'cursor-pointer',
        isDragging ? 'border-primary bg-accent' : 'border-input hover:border-primary/50',
      )}
    >
      <span aria-hidden="true" className="text-2xl">
        📄
      </span>
      <div className="space-y-1">
        <p className="text-body-sm font-medium">
          Drag and drop, or <span className="text-primary">browse</span>
        </p>
        <p className="text-caption text-muted-foreground">PDF or DOCX, up to 100 MB each.</p>
      </div>
      <Button type="button" variant="outline" size="sm" disabled={disabled} tabIndex={-1}>
        Choose files
      </Button>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_ATTRIBUTE}
        multiple
        className="sr-only"
        disabled={disabled}
        onChange={(event) => {
          emit(event.target.files);
          // Reset so selecting the same file again re-triggers change.
          event.target.value = '';
        }}
      />
    </div>
  );
}
