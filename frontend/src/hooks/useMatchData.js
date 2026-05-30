/**
 * Custom hook for fetching match details with error handling.
 * Extracts data loading logic from MatchDetail component.
 */
import { useState, useEffect, useCallback } from 'react';
import { api, formatApiError } from '@/lib/api';

export function useMatchData(matchId) {
  const [match, setMatch] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [history, setHistory] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const loadHistory = useCallback(async () => {
    try {
      const { data } = await api.get(`/matches/${matchId}/analyses`);
      setHistory(data);
    } catch (err) {
      console.error('Failed to load analysis history:', err);
      // History is optional - don't block UI
    }
  }, [matchId]);

  const loadMatch = useCallback(async () => {
    if (!matchId) return;
    
    setLoading(true);
    setError('');
    
    try {
      const { data } = await api.get(`/matches/${matchId}`);
      setMatch(data);
      if (data.latest_analysis) {
        setAnalysis(data.latest_analysis);
      }
      await loadHistory();
    } catch (err) {
      console.error('Failed to load match:', err);
      setError(formatApiError(err?.response?.data?.detail) || 'Błąd ładowania meczu');
    } finally {
      setLoading(false);
    }
  }, [matchId, loadHistory]);

  useEffect(() => {
    loadMatch();
  }, [loadMatch]);

  return {
    match,
    analysis,
    history,
    error,
    loading,
    reload: loadMatch,
    setAnalysis,
    reloadHistory: loadHistory,
  };
}
