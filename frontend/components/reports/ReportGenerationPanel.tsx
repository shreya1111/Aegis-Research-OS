'use client';

import { useParams } from 'next/navigation';
import { useState } from 'react';

import { createReport } from '@/lib/api/reports';
import { useToast } from '@/lib/toast/toast-context';
import type { Report, ReportType } from '@/types/report';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';

import { ReportList } from './ReportList';

const REPORT_TYPES: ReadonlyArray<{ value: ReportType; label: string; description: string }> = [
  {
    value: 'literature_review',
    label: 'Literature review',
    description: 'Thematic sections, synthesis, and open gaps.',
  },
  {
    value: 'gap_analysis',
    label: 'Gap analysis',
    description: 'Research gaps, contradictions, and future directions.',
  },
  {
    value: 'source_comparison',
    label: 'Source comparison',
    description: 'Methodologies, findings, and limitations compared across sources.',
  },
  {
    value: 'survey',
    label: 'Survey',
    description: 'An overview combining review, comparison, and analysis.',
  },
];

export function ReportGenerationPanel(): React.JSX.Element {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const { notify } = useToast();

  const [selectedType, setSelectedType] = useState<ReportType>('literature_review');
  const [title, setTitle] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [reports] = useState<Report[]>([]);
  const [isLoading] = useState(false);

  async function handleGenerate(): Promise<void> {
    if (!title.trim()) {
      notify('error', 'Enter a title for the report.');
      return;
    }

    setIsGenerating(true);
    try {
      await createReport(projectId, selectedType, title.trim());
      notify('success', 'Report generation started. It will appear here when it finishes.');
      setTitle('');
    } catch (caught) {
      notify(
        'error',
        caught instanceof Error && caught.message
          ? caught.message
          : 'Could not start report generation.',
      );
    } finally {
      setIsGenerating(false);
    }
  }

  return (
    <div className="container flex max-w-3xl flex-col gap-6 py-10">
      <div>
        <h1 className="text-h1 font-semibold">Reports</h1>
        <p className="text-body-sm text-muted-foreground">
          Generate a cited artifact from this project&apos;s documents.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Generate a report</CardTitle>
          <CardDescription>
            Choose the artifact to generate. Every claim will cite a retrieved source.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-6">
          <div className="flex flex-col gap-2">
            <Label htmlFor="report-title">Title</Label>
            <Input
              id="report-title"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="e.g. Retrieval evaluation methods, 2020–2025"
              disabled={isGenerating}
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label id="report-type-label">Type</Label>
            <RadioGroup
              aria-labelledby="report-type-label"
              value={selectedType}
              onValueChange={(value: string) => setSelectedType(value as ReportType)}
              className="gap-3"
              disabled={isGenerating}
            >
              {REPORT_TYPES.map((type) => (
                <div key={type.value} className="flex items-start gap-3">
                  <RadioGroupItem value={type.value} id={type.value} className="mt-0.5" />
                  <Label htmlFor={type.value} className="flex cursor-pointer flex-col gap-0.5">
                    <span className="text-body-sm font-medium">{type.label}</span>
                    <span className="text-caption font-normal text-muted-foreground">
                      {type.description}
                    </span>
                  </Label>
                </div>
              ))}
            </RadioGroup>
          </div>

          <Button
            type="button"
            onClick={() => void handleGenerate()}
            disabled={isGenerating || !title.trim()}
            className="w-full"
          >
            {isGenerating ? 'Generating…' : 'Generate report'}
          </Button>
        </CardContent>
      </Card>

      <section className="flex flex-col gap-3 border-t pt-6">
        <h2 className="text-h2 font-semibold">Generated reports</h2>
        <ReportList reports={reports} isLoading={isLoading} />
      </section>
    </div>
  );
}
