'use client';

import { createContext, useCallback, useContext, useMemo, useReducer } from 'react';

export type ToastVariant = 'success' | 'error' | 'info';

export interface Toast {
  id: string;
  variant: ToastVariant;
  message: string;
}

interface ToastContextValue {
  toasts: Toast[];
  notify: (variant: ToastVariant, message: string) => void;
  dismiss: (id: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

type ToastAction = { type: 'add'; toast: Toast } | { type: 'remove'; id: string };

function reducer(state: Toast[], action: ToastAction): Toast[] {
  switch (action.type) {
    case 'add':
      return [...state, action.toast];
    case 'remove':
      return state.filter((toast) => toast.id !== action.id);
  }
}

//: Toasts auto-dismiss after this many milliseconds (design §14.7: "slide in,
//: auto-dismiss, slide out"). Errors persist longer so they are not missed.
const AUTO_DISMISS_MS: Record<ToastVariant, number> = {
  success: 4000,
  info: 4000,
  error: 8000,
};

export function ToastProvider({ children }: { children: React.ReactNode }): React.JSX.Element {
  const [toasts, dispatch] = useReducer(reducer, []);

  const dismiss = useCallback((id: string) => {
    dispatch({ type: 'remove', id });
  }, []);

  const notify = useCallback((variant: ToastVariant, message: string) => {
    const id = crypto.randomUUID();
    dispatch({ type: 'add', toast: { id, variant, message } });
    window.setTimeout(() => dispatch({ type: 'remove', id }), AUTO_DISMISS_MS[variant]);
  }, []);

  const value = useMemo<ToastContextValue>(
    () => ({ toasts, notify, dismiss }),
    [toasts, notify, dismiss],
  );

  return <ToastContext.Provider value={value}>{children}</ToastContext.Provider>;
}

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider.');
  }
  return context;
}
