'use client';

import { useEffect, useState, useCallback } from 'react';

const STORAGE_KEY = 'smartwaste:selectedDate';
const EVENT_NAME = 'smartwaste:dateChanged';

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

export function useSelectedDate(): [string, (next: string) => void] {
  // Always start with today on both server and client to avoid hydration mismatch.
  // Sync the stored value in via useEffect after hydration completes.
  const [date, setDate] = useState<string>(todayIso);

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored && stored !== date) setDate(stored);

    const handler = (e: Event) => {
      const value = (e as CustomEvent<string>).detail;
      if (value) setDate(value);
    };
    window.addEventListener(EVENT_NAME, handler);
    const onStorage = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY && e.newValue) setDate(e.newValue);
    };
    window.addEventListener('storage', onStorage);
    return () => {
      window.removeEventListener(EVENT_NAME, handler);
      window.removeEventListener('storage', onStorage);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const update = useCallback((next: string) => {
    setDate(next);
    if (typeof window !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, next);
      window.dispatchEvent(new CustomEvent(EVENT_NAME, { detail: next }));
    }
  }, []);

  return [date, update];
}

export function getStoredDate(): string {
  if (typeof window === 'undefined') return todayIso();
  return localStorage.getItem(STORAGE_KEY) || todayIso();
}
