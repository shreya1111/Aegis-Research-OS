import { ComingSoon } from '@/components/feedback/ComingSoon';

export const metadata = { title: 'Reports' };

export default function ProjectReportsPage(): React.JSX.Element {
  return (
    <ComingSoon
      title="Reports"
      description="Generated research artifacts — literature reviews, gap analyses, source comparisons, and surveys — will appear here, ready to export. Report generation is built on the agent pipeline in a later phase."
    />
  );
}
