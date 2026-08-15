import { ChatPanel } from '@/components/chat/ChatPanel';

export const metadata = { title: 'Chat' };

/**
 * The project's default tab is Chat (design §5.3: "the Chat tab is the default
 * landing surface because asking a question is the most common intent"). The
 * surrounding shell (nav, breadcrumb, project loading) is provided by the
 * project layout.
 */
export default function ProjectChatPage(): React.JSX.Element {
  return <ChatPanel />;
}
