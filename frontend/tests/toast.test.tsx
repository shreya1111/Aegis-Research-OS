import { act, render, renderHook, screen } from '@testing-library/react';
import { useEffect } from 'react';
import { describe, expect, it, vi } from 'vitest';

import { Toaster } from '@/components/feedback/Toaster';
import { ToastProvider, useToast } from '@/lib/toast/toast-context';

describe('toast system', () => {
  it('notify adds a toast and dismiss removes it', () => {
    vi.useFakeTimers();
    try {
      const { result } = renderHook(() => useToast(), { wrapper: ToastProvider });

      act(() => {
        result.current.notify('success', 'Saved.');
      });
      expect(result.current.toasts).toHaveLength(1);

      const id = result.current.toasts[0]!.id;
      act(() => {
        result.current.dismiss(id);
      });
      expect(result.current.toasts).toHaveLength(0);
    } finally {
      vi.useRealTimers();
    }
  });

  it('auto-dismisses a success toast after its timeout', () => {
    vi.useFakeTimers();
    try {
      const { result } = renderHook(() => useToast(), { wrapper: ToastProvider });

      act(() => {
        result.current.notify('success', 'Saved.');
      });
      expect(result.current.toasts).toHaveLength(1);

      act(() => {
        vi.advanceTimersByTime(4000);
      });
      expect(result.current.toasts).toHaveLength(0);
    } finally {
      vi.useRealTimers();
    }
  });

  it('useToast throws outside a provider', () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    expect(() => renderHook(() => useToast())).toThrow('must be used within a ToastProvider');
    consoleError.mockRestore();
  });

  it('Toaster renders the message with a polite live region', () => {
    function Emitter(): null {
      const { notify } = useToast();
      useEffect(() => {
        notify('error', 'Something failed.');
      }, [notify]);
      return null;
    }

    render(
      <ToastProvider>
        <Emitter />
        <Toaster />
      </ToastProvider>,
    );

    // The mount effect runs synchronously under the testing-library act wrapper,
    // so the toast is present without waiting (avoids waitFor + fake timers).
    expect(screen.getByText('Something failed.')).toBeInTheDocument();
    const region = screen.getByText('Something failed.').closest('[aria-live]');
    expect(region).toHaveAttribute('aria-live', 'polite');
  });
});
