'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Separator } from '@/components/ui/separator';
import { useToast } from '@/lib/toast/toast-context';
import { createReport } from '@/lib/api/reports';
import type { Report, ReportType } from '@/types/report';

import { ReportList } from './ReportList';

const REPORT_TYPES: Array<{ value: ReportType; label: string; description: string }> = [
  {
    value: 'literature_review',
    label: 'Literature Review',
    description: 'Structured review with thematic sections, synthesis, and gaps',
  },
  {
    value: 'gap_analysis',
    label: 'Gap Analysis', 
    description: 'Identify research gaps, contradictions, and future directions',
  },
  {
    value: 'source_comparison',
    label: 'Source Comparison',
    description: 'Compare methodologies, findings, and limitations across sources',
  },
  {
    value: 'survey',
    label: 'Survey',
    description: 'Comprehensive overview combining review, comparison, and analysis',
  },
];

export function ReportGenerationPanel(): React.JSX.Element {
  const params = useParams();
  const projectId = params.id as string;
  const { notify } = useToast();

  const [selectedType, setSelectedType] = useState<ReportType>('literature_review');
  const [title, setTitle] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [reports] = useState<Report[]>([]);
  const [isLoading] = useState(false);

  const handleGenerate = async () => {
    if (!title.trim()) {
      notify('error', 'Please enter a title for your report');
      return;
    }

    setIsGenerating(true);
    try {
      await createReport(projectId, selectedType, title.trim());
      notify('success', 'Report generation started. Check back in a few minutes.');
      setTitle('');
      // In a full implementation, this would refresh the reports list
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : null;
      notify('error', message || 'Failed to start report generation');
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-h2 font-semibold">Research Artifacts</h1>
        <p className="text-body text-muted-foreground">
          Generate comprehensive research artifacts from your project documents using AI agents.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Generate New Report</CardTitle>
          <CardDescription>
            Choose the type of research artifact to generate from your uploaded documents.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div>
            <Label htmlFor="title">Report Title</Label>
            <Input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Enter a descriptive title for your report"
              className="mt-1"
              disabled={isGenerating}
            />
          </div>

          <div>
            <Label>Report Type</Label>
            <RadioGroup
              value={selectedType}
              onValueChange={(value: string) => setSelectedType(value as ReportType)}
              className="mt-2"
              disabled={isGenerating}
            >
              {REPORT_TYPES.map((type) => (
                <div key={type.value} className="flex items-start space-x-2">
                  <RadioGroupItem value={type.value} id={type.value} className="mt-0.5" />
                  <div className="grid gap-1.5 leading-none">
                    <Label
                      htmlFor={type.value}
                      className="text-sm font-medium cursor-pointer"
                    >
                      {type.label}
                    </Label>
                    <p className="text-xs text-muted-foreground">{type.description}</p>
                  </div>
                </div>
              ))}
            </RadioGroup>
          </div>

          <Button
            onClick={handleGenerate}
            disabled={isGenerating || !title.trim()}
            className="w-full"
          >
            {isGenerating ? 'Generating...' : 'Generate Report'}
          </Button>
        </CardContent>
      </Card>

      <Separator />

      <div>
        <h2 className="text-h3 font-semibold mb-4">Generated Reports</h2>
        <ReportList reports={reports} isLoading={isLoading} />
      </div>
    </div>
  );
}