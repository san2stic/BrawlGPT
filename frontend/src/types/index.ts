/**
 * TypeScript type definitions for BrawlGPT
 */

// Player Types
export interface PlayerIcon {
  id: number;
}

export interface ClubInfo {
  tag: string;
  name: string;
}

export interface BrawlerStats {
  id: number;
  name: string;
  power: number;
  rank: number;
  trophies: number;
  highestTrophies: number;
  gears?: Gear[];
  starPowers?: StarPower[];
  gadgets?: Gadget[];
}

export interface Gear {
  id: number;
  name: string;
  level: number;
}

export interface StarPower {
  id: number;
  name: string;
}

export interface Gadget {
  id: number;
  name: string;
}

export interface Player {
  tag: string;
  name: string;
  nameColor?: string;
  icon?: PlayerIcon;
  trophies: number;
  highestTrophies: number;
  expLevel: number;
  expPoints: number;
  isQualifiedFromChampionshipChallenge: boolean;
  "3vs3Victories": number;
  soloVictories: number;
  duoVictories: number;
  bestRoboRumbleTime?: number;
  bestTimeAsBigBrawler?: number;
  club?: ClubInfo;
  brawlers: BrawlerStats[];
}

// Battle Types
export interface BattleEvent {
  id?: number;
  mode?: string;
  map?: string;
}

export interface BattlePlayer {
  tag: string;
  name: string;
  brawler?: {
    id: number;
    name: string;
    power: number;
    trophies: number;
  };
}

export interface BattleInfo {
  mode?: string;
  type?: string;
  result?: "victory" | "defeat" | "draw";
  duration?: number;
  trophyChange?: number;
  starPlayer?: BattlePlayer;
  teams?: BattlePlayer[][];
  players?: BattlePlayer[];
}

export interface BattleLogItem {
  battleTime: string;
  event?: BattleEvent;
  battle?: BattleInfo;
}

export interface BattleLog {
  items: BattleLogItem[];
}

// API Response Types
export interface PlayerAnalysisResponse {
  player: Player;
  battles: BattleLog;
  insights: string;
}

export interface APIError {
  detail: string;
  error_type?: string;
}

// Component Props Types
export interface PlayerInputProps {
  onSearch: (tag: string) => void;
  loading: boolean;
}

export interface StatsCardProps {
  player: Player | null;
}

export interface AiAdviceProps {
  insights: string | null;
}

export interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export interface TrophyChartProps {
  brawlers: BrawlerStats[] | undefined;
}

// Chat Types
export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

export interface ChatRequest {
  messages: ChatMessage[];
  player_context: any; // Using any to avoid circular dependency complex mapping for now, or use Player
}

export interface ChatResponse {
  response: string;
}
