import { ComingSoon } from '@/components/feedback/ComingSoon';

export const metadata = { title: 'Knowledge Graph' };

export default function ProjectGraphPage(): React.JSX.Element {
  return (
    <ComingSoon
      title="Knowledge Graph"
      description="Visual exploration of the relationships between papers, authors, topics, and institutions across this project. This is a stretch feature planned after the core research workflow is complete."
    />
  );
}
