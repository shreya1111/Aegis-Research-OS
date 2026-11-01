'use client';

import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useRef, useState } from 'react';

import { listNotifications, markNotificationRead } from '@/lib/api/notifications';
import { useAuth } from '@/lib/auth/auth-context';
import type { NotificationItem } from '@/types/api';

import { Button } from '@/components/ui/button';

/**
 * In-app notification bell (Phase 10, FR-H8).
 *
 * Long-running generation finishes in a background task, so the user needs a
 * place to learn about it without watching the Reports tab. The panel is a plain
 * absolutely-positioned region — no popover dependency — and polls on an
 * interval, because nothing in this system pushes server events to the browser.
 */
const POLL_INTERVAL_MS = 60_000;

function formatWhen(value: string): string {
  return new Date(value).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

export function NotificationsMenu(): React.JSX.Element | null {
  const { user, getValidAccessToken } = useAuth();
  const router = useRouter();

  const [items, setItems] = useState<NotificationItem[]>([]);
  const [unread, setUnread] = useState(0);
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const load = useCallback(async () => {
    const token = await getValidAccessToken();
    if (!token) return;
    try {
      const inbox = await listNotifications(token);
      setItems(inbox.items);
      setUnread(inbox.unread);
    } catch {
      // A failed poll is not worth a toast; the badge simply stays as it was.
    }
  }, [getValidAccessToken]);

  useEffect(() => {
    if (!user) return undefined;
    void load();
    const timer = window.setInterval(() => void load(), POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [user, load]);

  useEffect(() => {
    if (!open) return undefined;

    function onPointerDown(event: MouseEvent): void {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    function onKeyDown(event: KeyboardEvent): void {
      if (event.key === 'Escape') setOpen(false);
    }

    document.addEventListener('mousedown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('mousedown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [open]);

  async function handleSelect(notification: NotificationItem): Promise<void> {
    setOpen(false);
    if (!notification.read) {
      const token = await getValidAccessToken();
      if (token) {
        try {
          await markNotificationRead(token, notification.id);
          setItems((previous) =>
            previous.map((item) =>
              item.id === notification.id ? { ...item, read: true } : item,
            ),
          );
          setUnread((previous) => Math.max(0, previous - 1));
        } catch {
          // Leaving the badge as-is is recoverable; navigating still helps.
        }
      }
    }
    if (notification.link) router.push(notification.link);
  }

  if (!user) return null;

  const label = unread > 0 ? `Notifications (${unread} unread)` : 'Notifications';

  return (
    <div className="relative" ref={containerRef}>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-label={label}
        onClick={() => {
          setOpen((previous) => !previous);
          if (!open) void load();
        }}
      >
        <span aria-hidden="true">🔔</span>
        {unread > 0 ? (
          <span
            aria-hidden="true"
            className="ml-1 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-primary px-1 text-xs font-semibold text-primary-foreground"
          >
            {unread > 9 ? '9+' : unread}
          </span>
        ) : null}
      </Button>

      {open ? (
        <div
          role="dialog"
          aria-label="Notifications"
          className="absolute right-0 z-50 mt-2 w-80 rounded-surface border bg-card p-2 shadow-lg"
        >
          {items.length === 0 ? (
            <p className="px-2 py-4 text-body-sm text-muted-foreground">
              Nothing here yet. Report and invitation updates will appear here.
            </p>
          ) : (
            <ul className="flex max-h-80 flex-col overflow-y-auto">
              {items.map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    className="flex w-full flex-col gap-1 rounded-sm px-2 py-2 text-left hover:bg-muted"
                    onClick={() => void handleSelect(item)}
                  >
                    <span className="flex items-center gap-2 text-body-sm font-medium">
                      {!item.read ? (
                        <span
                          aria-hidden="true"
                          className="h-1.5 w-1.5 shrink-0 rounded-full bg-primary"
                        />
                      ) : null}
                      {item.title}
                    </span>
                    <span className="text-body-sm text-muted-foreground">{item.message}</span>
                    <span className="text-xs text-muted-foreground">
                      {formatWhen(item.created_at)}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </div>
  );
}
