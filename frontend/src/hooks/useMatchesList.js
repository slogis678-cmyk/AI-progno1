/**
 * Custom hook for fetching matches list with filtering.
 * Extracts data loading logic from Dashboard component.
 */
import { useState, useEffect, useMemo, useCallback } from 'react';
import { api } from '@/lib/api';

export function useMatchesList() {
  const [matches, setMatches] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const { data } = await api.get('/matches');
      setMatches(data);
    } catch (err) {
      console.error('Failed to load matches:', err);
      setError('Błąd ładowania meczów');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return { matches, loading, error, reload: load };
}

export function useMatchFilters(matches) {
  const [filter, setFilter] = useState('');
  const [leagueFilter, setLeagueFilter] = useState('ALL');
  const [minEdge, setMinEdge] = useState(0);

  const allLeagues = useMemo(() => {
    const set = new Set();
    (matches || []).forEach((m) => set.add(m.league));
    return Array.from(set).sort();
  }, [matches]);

  const filtered = useMemo(() => {
    const arr = matches || [];
    const query = filter.toLowerCase();
    
    return arr.filter((m) => {
      // Text search
      if (query) {
        const matchesQuery = 
          m.home_team.toLowerCase().includes(query) ||
          m.away_team.toLowerCase().includes(query) ||
          m.league.toLowerCase().includes(query);
        if (!matchesQuery) return false;
      }
      
      // League filter
      if (leagueFilter !== 'ALL' && m.league !== leagueFilter) {
        return false;
      }
      
      // Min edge filter
      const edgePct = (m.edge_summary?.best_edge || 0) * 100;
      if (edgePct < minEdge) return false;
      
      return true;
    });
  }, [matches, filter, leagueFilter, minEdge]);

  return {
    filter,
    setFilter,
    leagueFilter,
    setLeagueFilter,
    minEdge,
    setMinEdge,
    allLeagues,
    filtered,
  };
}
