/**
 * Player statistics card component
 */

import type { ReactElement } from "react";
import type { StatsCardProps } from "../types";

interface StatBoxProps {
  title: string;
  value: number | string;
  color: string;
}

function StatBox({ title, value, color }: StatBoxProps): ReactElement {
  // Format large numbers with locale formatting
  const formattedValue =
    typeof value === "number" ? value.toLocaleString() : value;

  return (
    <div
      className={`bg-slate-800 p-4 rounded-xl border-b-4 ${color} shadow-lg flex flex-col items-center justify-center gap-2 transform hover:-translate-y-1 transition-transform`}
    >
      <span className="text-slate-400 text-sm font-bold uppercase tracking-wider">
        {title}
      </span>
      <span className="text-white text-2xl font-black">{formattedValue}</span>
    </div>
  );
}

/**
 * Get player name color from nameColor field
 * Safely handles missing or malformed color values
 */
function getPlayerColor(nameColor?: string): string {
  if (!nameColor) {
    return "#FFFFFF";
  }

  // Remove '0xff' prefix if present (Brawl Stars API format)
  const cleanColor = nameColor.replace(/^0xff/i, "");

  // Validate hex color format
  if (/^[0-9A-Fa-f]{6}$/.test(cleanColor)) {
    return `#${cleanColor}`;
  }

  return "#FFFFFF";
}

function StatsCard({ player }: StatsCardProps): ReactElement | null {
  if (!player) {
    return null;
  }

  const playerColor = getPlayerColor(player.nameColor);

  return (
    <div className="w-full max-w-4xl mx-auto p-4 animate-fade-in">
      {/* Player Header */}
      <div className="text-center mb-8">
        <h2 className="text-4xl font-black text-white drop-shadow-[0_2px_4px_rgba(0,0,0,0.8)]">
          <span style={{ color: playerColor }}>{player.name}</span>
        </h2>
        <p className="text-yellow-400 font-bold text-lg mt-1">
          {player.club?.name || "No Club"}
        </p>
        <p className="text-slate-500 text-sm font-mono mt-1">{player.tag}</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatBox
          title="Trophies"
          value={player.trophies}
          color="border-yellow-500"
        />
        <StatBox
          title="Highest Trophies"
          value={player.highestTrophies}
          color="border-yellow-600"
        />
        <StatBox
          title="3v3 Victories"
          value={player["3vs3Victories"]}
          color="border-blue-500"
        />
        <StatBox
          title="Solo Victories"
          value={player.soloVictories}
          color="border-green-500"
        />
      </div>

      {/* Additional Stats */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mt-4">
        <StatBox
          title="Duo Victories"
          value={player.duoVictories}
          color="border-purple-500"
        />
        <StatBox
          title="Experience Level"
          value={player.expLevel}
          color="border-cyan-500"
        />
        <StatBox
          title="Brawlers Unlocked"
          value={player.brawlers?.length || 0}
          color="border-pink-500"
        />
      </div>
    </div>
  );
}

export default StatsCard;
