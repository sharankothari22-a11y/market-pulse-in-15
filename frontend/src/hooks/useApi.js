import { useState, useEffect, useCallback } from 'react';

export const useApi = (fetchFn, dependencies = [], immediate = true) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(immediate);
  const [error, setError] = useState(null);

  const execute = useCallback(async (...args) => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchFn(...args);
      setData(result);
      return result;
    } catch (err) {
      setError(err.message || 'An error occurred');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [fetchFn]);

  useEffect(() => {
    if (immediate) {
      execute();
    }
  }, dependencies);

  return { data, loading, error, execute, setData };
};

export const usePolling = (fetchFn, interval = 30000, dependencies = []) => {
  const { data, loading, error, execute } = useApi(fetchFn, dependencies, true);

  useEffect(() => {
    const timer = setInterval(() => {
      execute();
    }, interval);

    return () => clearInterval(timer);
  }, [execute, interval]);

  return { data, loading, error, refresh: execute };
};
