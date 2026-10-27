'use client';

import { useState } from 'react';
import { FileText, Download, Trash2, Clock, CheckCircle, AlertCircle, Sparkles } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { formatDistanceToNow } from '@/lib/utils/format';
import { exportReport, generateSummary, type ExportFormat } from '@/lib/api/reports';
import { useAuth } from '@/lib/auth/auth-context';
import { useToast } from '@/lib/toast/toast-context';
import type { Report } from '@/types/report';

interface ReportListProps {
  reports: Report[];
  isLoading: boolean;
  onDelete?: (reportId: string) => void;
}

function getStatusIcon(status: Report['status']) {
  switch (status) {
    case 'pending':
    case 'generating':
      return <Clock className="w-4 h-4" />;
    case 'completed':
      return <CheckCircle className="w-4 h-4" />;
    case 'failed':
      return <AlertCircle className="w-4 h-4" />;
  }
}

function getStatusVariant(status: Report['status']): 'default' | 'secondary' | 'destructive' {
  switch (status) {
    case 'pending':
    case 'generating':
      return 'secondary';
    case 'completed':
      return 'default';
    case 'failed':
      return 'destructive';
  }
}

function formatReportType(type: Report['type']): string {
  switch (type) {
    case 'literature_review':
      return 'Literature Review';
    case 'gap_analysis':
      return 'Gap Analysis';
    case 'source_comparison':
      return 'Source Comparison';
    case 'survey':
      return 'Survey';
    default:
      return type;
  }
}

export function ReportList({ reports, isLoading, onDelete }: ReportListProps): React.JSX.Element {
  const { getValidAccessToken } = useAuth();
  const { notify } = useToast();
  const [exportingId, setExportingId] = useState<string | null>(null);
  const [generatingSummaryId, setGeneratingSummaryId] = useState<string | null>(null);

  const handleExport = async (reportId: string, format: ExportFormat) => {
    setExportingId(reportId);
    try {
      const token = await getValidAccessToken();
      if (!token) throw new Error('Not authenticated');
      
      const blob = await exportReport(reportId, format, token);
      
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `report.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      
      notify({ message: `Report exported as ${format.toUpperCase()}`, type: 'success' });
    } catch (error: any) {
      notify({ message: error.message || 'Export failed', type: 'error' });
    } finally {
      setExportingId(null);
    }
  };

  const handleGenerateSummary = async (reportId: string) => {
    setGeneratingSummaryId(reportId);
    try {
      const token = await getValidAccessToken();
      if (!token) throw new Error('Not authenticated');
      
      const summary = await generateSummary(reportId, token);
      
      // Show summary in alert or modal
      alert(`Executive Summary:\n\n${summary}`);
      
      notify({ message: 'Summary generated successfully', type: 'success' });
    } catch (error: any) {
      notify({ message: error.message || 'Summary generation failed', type: 'error' });
    } finally {
      setGeneratingSummaryId(null);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <Card key={i}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <Skeleton className="h-6 w-48" />
                <Skeleton className="h-6 w-20" />
              </div>
              <Skeleton className="h-4 w-32" />
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
      <div className="text-center py-12">
        <FileText className="mx-auto h-12 w-12 text-muted-foreground" />
        <h3 className="mt-4 text-lg font-medium">No reports generated yet</h3>
        <p className="mt-2 text-sm text-muted-foreground">
          Generate your first research artifact to get started.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {reports.map((report) => (
        <Card key={report.id}>
          <CardHeader>
            <div className="flex items-start justify-between">
              <div className="space-y-1">
                <CardTitle className="text-lg">{report.title}</CardTitle>
                <CardDescription>
                  {formatReportType(report.type)} •{' '}
                  {formatDistanceToNow(new Date(report.created_at))} ago
                </CardDescription>
              </div>
              <Badge variant={getStatusVariant(report.status)} className="flex items-center gap-1">
                {getStatusIcon(report.status)}
                {report.status.replace('_', ' ')}
              </Badge>
            </div>
          </CardHeader>
          
          {(report.status === 'completed' || report.status === 'failed') && (
            <CardContent className="pt-0">
              <div className="flex items-center justify-between">
                {report.status === 'failed' && report.error_message && (
                  <p className="text-sm text-destructive">{report.error_message}</p>
                )}
                {report.status === 'completed' && (
                  <p className="text-sm text-muted-foreground">
                    Report ready for viewing and export
                  </p>
                )}
                
                <div className="flex items-center gap-2 ml-auto">
                  {report.status === 'completed' && (
                    <>
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={() => handleGenerateSummary(report.id)}
                        disabled={generatingSummaryId === report.id}
                      >
                        <Sparkles className="w-4 h-4 mr-1" />
                        {generatingSummaryId === report.id ? 'Generating...' : 'Summary'}
                      </Button>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button 
                            variant="outline" 
                            size="sm"
                            disabled={exportingId === report.id}
                          >
                            <Download className="w-4 h-4 mr-1" />
                            {exportingId === report.id ? 'Exporting...' : 'Export'}
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => handleExport(report.id, 'pdf')}>
                            Export as PDF
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleExport(report.id, 'docx')}>
                            Export as DOCX
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleExport(report.id, 'html')}>
                            Export as HTML
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleExport(report.id, 'latex')}>
                            Export as LaTeX
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleExport(report.id, 'markdown')}>
                            Export as Markdown
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </>
                  )}
                  {onDelete && (
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={() => onDelete(report.id)}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              </div>
            </CardContent>
          )}
        </Card>
      ))}
    </div>
  );
}