/**
 * Custom hook for fetching and managing player data
 */

import { useState, useCallback, useRef, useEffect } from "react";
import type { Player, BattleLog, PlayerAnalysisResponse } from "../types";
import { getPlayerAnalysis, ApiError } from "../services/api";

interface UsePlayerDataState {
  player: Player | null;
  battles: BattleLog | null;
  insights: string | null;
  loading: boolean;
  error: string | null;
}

interface UsePlayerDataReturn extends UsePlayerDataState {
  search: (tag: string) => Promise<void>;
  refresh: () => Promise<void>;
  reset: () => void;
  currentTag: string | null;
}

const DEBOUNCE_MS = 300;

/**
 * Hook for fetching player data with debouncing and error handling
 */
export function usePlayerData(): UsePlayerDataReturn {
  const [state, setState] = useState<UsePlayerDataState>({
    player: null,
    battles: null,
    insights: null,
    loading: false,
    error: null,
  });

  const abortControllerRef = useRef<AbortController | null>(null);
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastTagRef = useRef<string | null>(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  const search = useCallback(async (tag: string): Promise<void> => {
    // Clear any pending debounce
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    // Cancel any in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Validate input
    const cleanTag = tag.trim();
    if (!cleanTag) {
      setState((prev) => ({
        ...prev,
        error: "Please enter a player tag",
        loading: false,
      }));
      return;
    }

    // Start loading immediately for better UX
    setState((prev) => ({
      ...prev,
      loading: true,
      error: null,
    }));

    // Debounce the actual API call
    return new Promise((resolve) => {
      debounceTimerRef.current = setTimeout(async () => {
        abortControllerRef.current = new AbortController();

        try {
          const data: PlayerAnalysisResponse = await getPlayerAnalysis(cleanTag);

          // Store the last successful tag
          lastTagRef.current = cleanTag;

          setState({
            player: data.player,
            battles: data.battles,
            insights: data.insights,
            loading: false,
            error: null,
          });
        } catch (err) {
          // Don't update state if request was aborted
          if (err instanceof Error && err.name === "AbortError") {
            resolve();
            return;
          }

          let errorMessage = "An unexpected error occurred";

          if (err instanceof ApiError) {
            errorMessage = err.message;

            // Provide user-friendly messages for common errors
            if (err.statusCode === 404) {
              errorMessage = "Player not found. Please check the tag and try again.";
            } else if (err.statusCode === 429) {
              errorMessage = "Too many requests. Please wait a moment and try again.";
            } else if (err.statusCode === 400) {
              errorMessage = "Invalid player tag format.";
            } else if (err.statusCode === 0) {
              errorMessage = "Unable to connect to server. Please check your connection.";
            }
          } else if (err instanceof Error) {
            errorMessage = err.message;
          }

          setState((prev) => ({
            ...prev,
            player: null,
            battles: null,
            insights: null,
            loading: false,
            error: errorMessage,
          }));
        }

        resolve();
      }, DEBOUNCE_MS);
    });
  }, []);

  const refresh = useCallback(async (): Promise<void> => {
    if (lastTagRef.current) {
      await search(lastTagRef.current);
    }
  }, [search]);

  const reset = useCallback(() => {
    // Cancel any pending operations
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    lastTagRef.current = null;

    setState({
      player: null,
      battles: null,
      insights: null,
      loading: false,
      error: null,
    });
  }, []);

  return {
    ...state,
    search,
    refresh,
    reset,
    currentTag: lastTagRef.current,
  };
}

export default usePlayerData;
