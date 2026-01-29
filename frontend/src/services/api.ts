/**
 * API Service for BrawlGPT
 * Centralized API communication layer
 */

import type { PlayerAnalysisResponse, APIError, ChatMessage, ChatResponse, Player } from "../types";

const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://localhost:8000";

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

  const url = `${API_BASE_URL}/api/player/${cleanedTag}`;

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
    const response = await fetch(`${API_BASE_URL}/health`);
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
  const url = `${API_BASE_URL}/api/chat`;

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

export const playerService = {
  getPlayerAnalysis,
  checkHealth,
  sendChatMessage,
};

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

  const url = `${API_BASE_URL}/api/schedule/generate`;

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

  const url = `${API_BASE_URL}/api/schedule/current`;

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

  const url = `${API_BASE_URL}/api/schedule/all`;

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

  const url = `${API_BASE_URL}/api/schedule/${scheduleId}`;

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
