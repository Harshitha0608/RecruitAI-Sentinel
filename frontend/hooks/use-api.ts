import { useState, useCallback, useEffect, useRef } from "react";

interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

// Overload 1: Lazy mode (default)
export function useApi<T, Args extends any[]>(
  apiFunc: (...args: Args) => Promise<T>,
  immediate?: false
): {
  data: T | null;
  loading: boolean;
  error: string | null;
  execute: (...args: Args) => Promise<T>;
  setData: (data: T | null) => void;
};

// Overload 2: Immediate mode
export function useApi<T, Args extends any[]>(
  apiFunc: (...args: Args) => Promise<T>,
  immediate: true,
  ...immediateArgs: Args
): {
  data: T | null;
  loading: boolean;
  error: string | null;
  execute: (...args: Args) => Promise<T>;
  setData: (data: T | null) => void;
};

// Overload 3: General boolean mode
export function useApi<T, Args extends any[]>(
  apiFunc: (...args: Args) => Promise<T>,
  immediate: boolean,
  ...immediateArgs: any[]
): {
  data: T | null;
  loading: boolean;
  error: string | null;
  execute: (...args: Args) => Promise<T>;
  setData: (data: T | null) => void;
};

// Implementation
export function useApi<T, Args extends any[]>(
  apiFunc: (...args: Args) => Promise<T>,
  immediate: boolean = false,
  ...immediateArgs: any[]
) {
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: immediate,
    error: null,
  });

  const apiFuncRef = useRef(apiFunc);
  
  useEffect(() => {
    apiFuncRef.current = apiFunc;
  }, [apiFunc]);

  const execute = useCallback(
    async (...args: Args): Promise<T> => {
      setState((prev) => ({ ...prev, loading: true, error: null }));
      try {
        const result = await apiFuncRef.current(...args);
        setState({ data: result, loading: false, error: null });
        return result;
      } catch (err: any) {
        const errMsg = err.message || "An unexpected error occurred.";
        setState({ data: null, loading: false, error: errMsg });
        throw err;
      }
    },
    []
  );

  useEffect(() => {
    if (immediate) {
      execute(...(immediateArgs as unknown as Args)).catch(() => { });
    }
  }, [immediate, execute]); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    ...state,
    execute,
    setData: (data: T | null) => setState((prev) => ({ ...prev, data })),
  };
}
