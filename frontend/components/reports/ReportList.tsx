'use client';

import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Download,
  Loader2,
  ScrollText,
  Trash2,
  type LucideIcon,
} from 'lucide-react';
import { useState } from 'react';

import { exportReport, generateSummary, type ExportFormat } from '@/lib/api/reports';
import { useAuth } from '@/lib/auth/auth-context';
import { useToast } from '@/lib/toast/toast-context';
import { cn } from '@/lib/utils/cn';
import { formatDistanceToNow } from '@/lib/utils/format';
import type { Report } from '@/types/report';

import { EmptyState } from '@/components/feedback/EmptyState';
import { Skeleton } from '@/components/feedback/Skeleton';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

interface ReportListProps {
  reports: Report[];
  isLoading: boolean;
  onDelete?: (reportId: string) => void;
}

interface StatusStyle {
  label: string;
  className: string;
  Icon: LucideIcon;
  spin?: boolean;
}

const STATUS_STYLES: Record<Report['status'], StatusStyle> = {
  pending: { label: 'Queued', className: 'border-info/30 bg-info/10 text-info', Icon: Clock },
  generating: {
    label: 'Generating',
    className: 'border-info/30 bg-info/10 text-info',
    Icon: Loader2,
    spin: true,
  },
  completed: {
    label: 'Completed',
    className: 'border-success/30 bg-success/10 text-success',
    Icon: CheckCircle2,
  },
  failed: {
    label: 'Failed',
    className: 'border-destructive/30 bg-destructive/10 text-destructive',
    Icon: AlertCircle,
  },
};

const EXPORT_FORMATS: ReadonlyArray<{ value: ExportFormat; label: string }> = [
  { value: 'pdf', label: 'PDF' },
  { value: 'docx', label: 'Word (.docx)' },
  { value: 'html', label: 'HTML' },
  { value: 'latex', label: 'LaTeX' },
  { value: 'markdown', label: 'Markdown' },
];

function reportTypeLabel(type: Report['type']): string {
  switch (type) {
    case 'literature_review':
      return 'Literature review';
    case 'gap_analysis':
      return 'Gap analysis';
    case 'source_comparison':
      return 'Source comparison';
    case 'survey':
      return 'Survey';
    default:
      return type;
  }
}

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback;
}

export function ReportList({ reports, isLoading, onDelete }: ReportListProps): React.JSX.Element {
  const { getValidAccessToken } = useAuth();
  const { notify } = useToast();
  const [exportingId, setExportingId] = useState<string | null>(null);
  const [summarisingId, setSummarisingId] = useState<string | null>(null);
  const [summary, setSummary] = useState<{ title: string; text: string } | null>(null);

  async function handleExport(report: Report, format: ExportFormat): Promise<void> {
    setExportingId(report.id);
    try {
      const token = await getValidAccessToken();
      if (!token) throw new Error('Your session has expired.');

      const blob = await exportReport(report.id, format, token);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${report.title.replace(/[^\w.-]+/g, '-')}.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      notify('success', `Exported as ${format.toUpperCase()}.`);
    } catch (caught) {
      notify('error', errorMessage(caught, 'Could not export the report.'));
    } finally {
      setExportingId(null);
    }
  }

  async function handleGenerateSummary(report: Report): Promise<void> {
    setSummarisingId(report.id);
    try {
      const token = await getValidAccessToken();
      if (!token) throw new Error('Your session has expired.');

      const text = await generateSummary(report.id, token);
      setSummary({ title: report.title, text });
    } catch (caught) {
      notify('error', errorMessage(caught, 'Could not generate a summary.'));
    } finally {
      setSummarisingId(null);
    }
  }

  if (isLoading) {
    return (
      <div className="flex flex-col gap-4">
        {[0, 1, 2].map((index) => (
          <Card key={index}>
            <CardHeader>
              <Skeleton className="h-5 w-2/3" />
              <Skeleton className="h-4 w-40" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-4 w-full" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (reports.length === 0) {
    return (
      <EmptyState
        title="No reports yet"
        description="Generate an artifact above. Completed reports can be exported as PDF, Word, HTML, LaTeX, or Markdown."
      />
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {reports.map((report) => {
        const status = STATUS_STYLES[report.status];
        const StatusIcon = status.Icon;

        return (
          <Card key={report.id}>
            <CardHeader className="flex-row items-start justify-between gap-4">
              <div className="flex min-w-0 flex-col gap-1">
                <CardTitle className="truncate">{report.title}</CardTitle>
                <p className="text-caption text-muted-foreground">
                  {reportTypeLabel(report.type)} · {formatDistanceToNow(report.created_at)}
                </p>
              </div>
              <span
                className={cn(
                  'inline-flex shrink-0 items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-caption font-medium',
                  status.className,
                )}
              >
                <StatusIcon className={cn('size-3.5', status.spin && 'animate-spin')} aria-hidden />
                {status.label}
              </span>
            </CardHeader>

            {(report.status === 'completed' || report.status === 'failed') && (
              <CardContent className="flex flex-wrap items-center justify-between gap-3">
                {report.status === 'failed' ? (
                  <p className="min-w-0 text-body-sm text-destructive">
                    {report.error_message ?? 'Generation failed.'}
                  </p>
                ) : (
                  <p className="text-body-sm text-muted-foreground">Ready to read or export.</p>
                )}

                <div className="ml-auto flex items-center gap-2">
                  {report.status === 'completed' && (
                    <>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => void handleGenerateSummary(report)}
                        disabled={summarisingId === report.id}
                      >
                        <ScrollText className="size-4" aria-hidden />
                        {summarisingId === report.id ? 'Summarising…' : 'Summary'}
                      </Button>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            disabled={exportingId === report.id}
                          >
                            <Download className="size-4" aria-hidden />
                            {exportingId === report.id ? 'Exporting…' : 'Export'}
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          {EXPORT_FORMATS.map((format) => (
                            <DropdownMenuItem
                              key={format.value}
                              onClick={() => void handleExport(report, format.value)}
                            >
                              {format.label}
                            </DropdownMenuItem>
                          ))}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </>
                  )}
                  {onDelete && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="text-destructive"
                      aria-label={`Delete ${report.title}`}
                      onClick={() => onDelete(report.id)}
                    >
                      <Trash2 className="size-4" aria-hidden />
                    </Button>
                  )}
                </div>
              </CardContent>
            )}
          </Card>
        );
      })}

      <Dialog
        open={summary !== null}
        onOpenChange={(open) => {
          if (!open) setSummary(null);
        }}
      >
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Executive summary</DialogTitle>
            <p className="text-body-sm text-muted-foreground">{summary?.title}</p>
          </DialogHeader>
          <div className="max-h-[60vh] overflow-y-auto whitespace-pre-wrap text-body-sm">
            {summary?.text}
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="outline">
                Close
              </Button>
            </DialogClose>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
