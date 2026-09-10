import { useState, useMemo } from 'react';

export type SortDirection = 'asc' | 'desc' | false;

export interface SortConfig<T> {
  key: keyof T | string;
  direction: SortDirection;
}

export function useTableSort<T>(
  data: T[],
  defaultKey?: keyof T | string,
  defaultDirection: SortDirection = 'asc',
  customSortFn?: (a: T, b: T, config: SortConfig<T>) => number
) {
  const [sortConfig, setSortConfig] = useState<SortConfig<T> | null>(
    defaultKey ? { key: defaultKey, direction: defaultDirection } : null
  );

  const handleSort = (key: keyof T | string) => {
    let direction: SortDirection = 'asc';
    if (sortConfig && sortConfig.key === key) {
      if (sortConfig.direction === 'asc') {
        direction = 'desc';
      } else if (sortConfig.direction === 'desc') {
        direction = false;
      }
    }
    setSortConfig(direction ? { key, direction } : null);
  };

  const sortedData = useMemo(() => {
    let sortableItems = [...data];
    if (sortConfig !== null && sortConfig.direction !== false) {
      sortableItems.sort((a, b) => {
        if (customSortFn) {
          return customSortFn(a, b, sortConfig);
        }

        const key = sortConfig.key as keyof T;
        const valA = a[key];
        const valB = b[key];

        if (valA < valB) return sortConfig.direction === 'asc' ? -1 : 1;
        if (valA > valB) return sortConfig.direction === 'asc' ? 1 : -1;
        return 0;
      });
    }
    return sortableItems;
  }, [data, sortConfig, customSortFn]);

  return { sortConfig, handleSort, sortedData, setSortConfig };
}
