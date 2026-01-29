/**
 * API Service for BrawlGPT
 * Centralized API communication layer
 */

import type { PlayerAnalysisResponse, APIError, ChatMessage, ChatResponse, Player } from "../types";

// Using relative URLs - nginx routes /api/ to backend

/**
 * Custom error class for API errors
 */
export class ApiError extends Error {
  public statusCode: number;
  public errorType?: string;

  constructor(message: string, statusCode: number, errorType?: string) {
    super(message);
    this.name = "ApiError";
    this.statusCode = statusCode;
    this.errorType = errorType;
  }
}

/**
 * Clean and format a player tag
 */
function cleanTag(tag: string): string {
  return tag.toUpperCase().replace("#", "").trim();
}

/**
 * Fetch player analysis from the API
 * @param tag - Player tag (with or without #)
 * @returns Player analysis including stats and AI insights
 * @throws ApiError if the request fails
 */
export async function getPlayerAnalysis(
  tag: string
): Promise<PlayerAnalysisResponse> {
  const cleanedTag = cleanTag(tag);

  if (!cleanedTag) {
    throw new ApiError("Player tag cannot be empty", 400);
  }

  const url = `/api/player/${cleanedTag}`;

  try {
    const response = await fetch(url, {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
    });

    if (!response.ok) {
      let errorMessage = "Failed to fetch player data";
      let errorType: string | undefined;

      try {
        const errorData: APIError = await response.json();
        errorMessage = errorData.detail || errorMessage;
        errorType = errorData.error_type;
      } catch {
        // If response is not JSON, use status text
        errorMessage = response.statusText || errorMessage;
      }

      throw new ApiError(errorMessage, response.status, errorType);
    }

    const data: PlayerAnalysisResponse = await response.json();
    return data;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }

    // Network or other errors
    if (error instanceof TypeError && error.message.includes("fetch")) {
      throw new ApiError(
        "Unable to connect to server. Please check your connection.",
        0
      );
    }

    throw new ApiError(
      error instanceof Error ? error.message : "An unexpected error occurred",
      500
    );
  }
}

/**
 * Check API health status
 */
export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`/health`);
    return response.ok;
  } catch {
    return false;
  }
}

/**
 * Send a chat message to the AI agent
 * @param messages - Chat history
 * @param playerContext - Current player data for context
 */
export async function sendChatMessage(
  messages: ChatMessage[],
  playerContext: Player | null
): Promise<string> {
  const url = `/api/chat`;

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({
        messages,
        player_context: playerContext,
      }),
    });

    if (!response.ok) {
      throw new ApiError("Failed to send message", response.status);
    }

    const data: ChatResponse = await response.json();
    return data.response;
  } catch (error) {
    console.error("Chat API Error:", error);
    throw new ApiError("Failed to communicate with AI agent", 500);
  }
}

/**
 * Stream chat messages from the AI agent using Server-Sent Events
 * @param messages - Chat history
 * @param playerContext - Current player data for context
 * @param onChunk - Callback for each received chunk
 * @param onComplete - Callback when streaming completes
 * @param onError - Callback for errors
 */
export async function sendChatMessageStream(
  messages: ChatMessage[],
  playerContext: Player | null,
  onChunk: (chunk: string) => void,
  onComplete?: () => void,
  onError?: (error: Error) => void
): Promise<void> {
  const url = `/api/chat/stream`;

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      body: JSON.stringify({
        messages,
        player_context: playerContext,
      }),
    });

    if (!response.ok) {
      throw new ApiError("Failed to start streaming", response.status);
    }

    const reader = response.body!.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        onComplete?.();
        break;
      }

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));

            if (data.error) {
              throw new Error(data.error);
            }

            if (data.content) {
              onChunk(data.content);
            }
          } catch (parseError) {
            console.error('Failed to parse SSE data:', parseError);
          }
        }
      }
    }
  } catch (error) {
    console.error("Chat Stream Error:", error);
    const apiError = error instanceof ApiError
      ? error
      : new ApiError("Failed to stream chat response", 500);
    onError?.(apiError);
    throw apiError;
  }
}

export const playerService = {
  getPlayerAnalysis,
  checkHealth,
  sendChatMessage,
  sendChatMessageStream,
  getCounterPicks,
  analyzeEnemyTeam,
  analyzeSynergy,
  suggestThirdBrawler,
};

// =============================================================================
// COUNTER-PICK API
// =============================================================================

export interface CounterPick {
  brawler_id: number;
  brawler_name: string;
  win_rate: number;
  sample_size: number;
  mode: string | null;
  reasoning: string;
  confidence: 'low' | 'medium' | 'high';
}

export interface CounterPickResponse {
  brawler: string;
  mode: string;
  counters: CounterPick[];
  message?: string;
}

export interface TeamCounterAnalysis {
  enemy_team: string[];
  recommended_picks: CounterPick[];
  synergy_score: number;
  mode: string;
  analysis: string;
}

/**
 * Get counter-picks for a specific brawler
 */
export async function getCounterPicks(
  brawlerName: string,
  mode?: string,
  topN: number = 5
): Promise<CounterPickResponse> {
  try {
    const params = new URLSearchParams();
    if (mode) params.append('mode', mode);
    params.append('top_n', topN.toString());

    const url = `/api/counters/${encodeURIComponent(brawlerName)}${params.toString() ? '?' + params.toString() : ''}`;

    const response = await fetch(url);

    if (!response.ok) {
      throw new ApiError(
        `Failed to get counters: ${response.statusText}`,
        response.status
      );
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(
      error instanceof Error ? error.message : 'Unknown error getting counters',
      500
    );
  }
}

/**
 * Analyze enemy team composition and get counter recommendations
 */
export async function analyzeEnemyTeam(
  enemyBrawlers: string[],
  mode?: string
): Promise<TeamCounterAnalysis> {
  try {
    const response = await fetch(`/api/counters/team`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        enemy_brawlers: enemyBrawlers,
        mode: mode || null,
      }),
    });

    if (!response.ok) {
      throw new ApiError(
        `Failed to analyze team: ${response.statusText}`,
        response.status
      );
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(
      error instanceof Error ? error.message : 'Unknown error analyzing team',
      500
    );
  }
}

// =============================================================================
// TEAM SYNERGY API
// =============================================================================

export interface SynergyAnalysis {
  brawlers: string[];
  overall_synergy: number;
  pairwise_synergies: { [key: string]: number };
  strengths: string[];
  weaknesses: string[];
  mode: string | null;
}

export interface BrawlerSuggestion {
  brawler_id: number;
  brawler_name: string;
  synergy_score: number;
  win_rate_boost: number;
  reasoning: string;
  confidence: 'low' | 'medium' | 'high';
}

export interface ThirdBrawlerResponse {
  current_team: string[];
  suggestions: BrawlerSuggestion[];
  mode: string;
}

/**
 * Analyze the synergy of a team composition
 */
export async function analyzeSynergy(
  brawlers: string[],
  mode?: string
): Promise<SynergyAnalysis> {
  try {
    const response = await fetch(`/api/synergy/analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        brawlers: brawlers,
        mode: mode || null,
      }),
    });

    if (!response.ok) {
      throw new ApiError(
        `Failed to analyze synergy: ${response.statusText}`,
        response.status
      );
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(
      error instanceof Error ? error.message : 'Unknown error analyzing synergy',
      500
    );
  }
}

/**
 * Suggest the best third brawler to complete a team
 */
export async function suggestThirdBrawler(
  brawler1: string,
  brawler2: string,
  mode?: string,
  topN: number = 5
): Promise<ThirdBrawlerResponse> {
  try {
    const response = await fetch(`/api/synergy/suggest`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        brawler1: brawler1,
        brawler2: brawler2,
        mode: mode || null,
        top_n: topN,
      }),
    });

    if (!response.ok) {
      throw new ApiError(
        `Failed to get suggestions: ${response.statusText}`,
        response.status
      );
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(
      error instanceof Error ? error.message : 'Unknown error getting suggestions',
      500
    );
  }
}

// =============================================================================
// SCHEDULE API
// =============================================================================

export interface ScheduleEvent {
  id: number;
  title: string;
  start: string;  // ISO datetime
  end: string;
  event_type: string;
  recommended_brawler?: string;
  recommended_mode?: string;
  recommended_map?: string;
  notes?: string;
  priority: string;
  color?: string;
}

export interface Schedule {
  id: number;
  player_tag: string;
  player_name?: string;
  schedule_type: string;
  duration_days: number;
  description: string;
  goals: string[];
  created_at: string;
  events: ScheduleEvent[];
}

export interface GenerateScheduleRequest {
  schedule_type: string;
  duration_days: number;
  goals: string[];
  focus_brawlers: string[];
}

/**
 * Get authentication token from localStorage
 */
function getAuthToken(): string | null {
  return localStorage.getItem('token');
}

/**
 * Generate a new personalized schedule
 */
export async function generateSchedule(
  request: GenerateScheduleRequest
): Promise<Schedule> {
  const token = getAuthToken();
  if (!token) {
    throw new ApiError('Authentication required', 401);
  }

  const url = `/api/schedule/generate`;

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      let errorMessage = 'Failed to generate schedule';
      try {
        const errorData: APIError = await response.json();
        errorMessage = errorData.detail || errorMessage;
      } catch {
        errorMessage = response.statusText || errorMessage;
      }
      throw new ApiError(errorMessage, response.status);
    }

    const data: Schedule = await response.json();
    return data;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(
      error instanceof Error ? error.message : 'Unexpected error',
      500
    );
  }
}

/**
 * Get the current active schedule
 */
export async function getCurrentSchedule(): Promise<Schedule | null> {
  const token = getAuthToken();
  if (!token) {
    throw new ApiError('Authentication required', 401);
  }

  const url = `/api/schedule/current`;

  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new ApiError('Failed to fetch schedule', response.status);
    }

    const data: Schedule | null = await response.json();
    return data;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(
      error instanceof Error ? error.message : 'Unexpected error',
      500
    );
  }
}

/**
 * Get all schedules for the current user
 */
export async function getAllSchedules(): Promise<Schedule[]> {
  const token = getAuthToken();
  if (!token) {
    throw new ApiError('Authentication required', 401);
  }

  const url = `/api/schedule/all`;

  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new ApiError('Failed to fetch schedules', response.status);
    }

    const data: Schedule[] = await response.json();
    return data;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(
      error instanceof Error ? error.message : 'Unexpected error',
      500
    );
  }
}

/**
 * Delete a schedule
 */
export async function deleteSchedule(scheduleId: number): Promise<void> {
  const token = getAuthToken();
  if (!token) {
    throw new ApiError('Authentication required', 401);
  }

  const url = `/api/schedule/${scheduleId}`;

  try {
    const response = await fetch(url, {
      method: 'DELETE',
      headers: {
        'Accept': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      let errorMessage = 'Failed to delete schedule';
      try {
        const errorData: APIError = await response.json();
        errorMessage = errorData.detail || errorMessage;
      } catch {
        errorMessage = response.statusText || errorMessage;
      }
      throw new ApiError(errorMessage, response.status);
    }
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(
      error instanceof Error ? error.message : 'Unexpected error',
      500
    );
  }
}

export const scheduleService = {
  generateSchedule,
  getCurrentSchedule,
  getAllSchedules,
  deleteSchedule,
};

export default playerService;
