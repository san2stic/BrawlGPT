/**
 * Trophy chart component - displays brawler trophies as a bar chart
 */

import type { ReactElement } from "react";
import type { TrophyChartProps, BrawlerStats } from "../types";

/** Get color based on trophy count */
function getTrophyColor(trophies: number): string {
  if (trophies >= 750) return "bg-gradient-to-r from-purple-500 to-pink-500";
  if (trophies >= 500) return "bg-gradient-to-r from-yellow-500 to-orange-500";
  if (trophies >= 300) return "bg-gradient-to-r from-blue-500 to-cyan-500";
  if (trophies >= 100) return "bg-gradient-to-r from-green-500 to-emerald-500";
  return "bg-gradient-to-r from-slate-500 to-slate-400";
}

/** Get rank badge color */
function getRankBadgeColor(rank: number): string {
  if (rank >= 30) return "bg-purple-600";
  if (rank >= 25) return "bg-pink-600";
  if (rank >= 20) return "bg-yellow-600";
  if (rank >= 15) return "bg-blue-600";
  if (rank >= 10) return "bg-green-600";
  return "bg-slate-600";
}

function TrophyChart({ brawlers }: TrophyChartProps): ReactElement | null {
  if (!brawlers || brawlers.length === 0) {
    return null;
  }

  // Sort by trophies descending and take top 15
  const sortedBrawlers = [...brawlers]
    .sort((a, b) => b.trophies - a.trophies)
    .slice(0, 15);

  const maxTrophies = Math.max(...sortedBrawlers.map((b) => b.trophies), 1);

  // Calculate total and average
  const totalTrophies = brawlers.reduce((sum, b) => sum + b.trophies, 0);
  const avgTrophies = Math.round(totalTrophies / brawlers.length);

  return (
    <div className="w-full max-w-4xl mx-auto p-4 mt-6 animate-fade-in">
      <div className="bg-slate-800/80 backdrop-blur-sm rounded-2xl p-6 border border-cyan-500/30 shadow-[0_0_30px_rgba(6,182,212,0.15)]">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-600 flex items-center gap-2">
            <span>🏆</span> Trophées par Brawler
          </h3>
          <div className="flex gap-4 text-sm">
            <div className="text-slate-400">
              Total: <span className="text-yellow-400 font-bold">{totalTrophies.toLocaleString()}</span>
            </div>
            <div className="text-slate-400">
              Moyenne: <span className="text-cyan-400 font-bold">{avgTrophies}</span>
            </div>
          </div>
        </div>

        {/* Chart */}
        <div className="space-y-3">
          {sortedBrawlers.map((brawler: BrawlerStats, index: number) => {
            const percentage = (brawler.trophies / maxTrophies) * 100;

            return (
              <div
                key={brawler.id}
                className="group relative"
                style={{ animationDelay: `${index * 50}ms` }}
              >
                <div className="flex items-center gap-3">
                  {/* Rank Position */}
                  <div className="w-6 text-slate-500 text-sm font-mono">
                    #{index + 1}
                  </div>

                  {/* Brawler Name */}
                  <div className="w-28 truncate text-slate-300 font-medium text-sm">
                    {brawler.name}
                  </div>

                  {/* Bar Container */}
                  <div className="flex-1 h-8 bg-slate-700/50 rounded-lg overflow-hidden relative">
                    {/* Trophy Bar */}
                    <div
                      className={`h-full ${getTrophyColor(brawler.trophies)} rounded-lg transition-all duration-500 ease-out flex items-center justify-end pr-2`}
                      style={{ width: `${Math.max(percentage, 8)}%` }}
                    >
                      {percentage > 20 && (
                        <span className="text-white text-xs font-bold drop-shadow-md">
                          {brawler.trophies}
                        </span>
                      )}
                    </div>

                    {/* Trophy count if bar is too small */}
                    {percentage <= 20 && (
                      <span className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 text-xs font-bold">
                        {brawler.trophies}
                      </span>
                    )}
                  </div>

                  {/* Power Level */}
                  <div className="w-10 text-center">
                    <span className="text-xs text-slate-500">P</span>
                    <span className="text-sm text-white font-bold">{brawler.power}</span>
                  </div>

                  {/* Rank Badge */}
                  <div
                    className={`w-8 h-8 ${getRankBadgeColor(brawler.rank)} rounded-full flex items-center justify-center`}
                  >
                    <span className="text-white text-xs font-black">{brawler.rank}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Legend */}
        <div className="mt-6 pt-4 border-t border-slate-700/50">
          <div className="flex flex-wrap gap-4 justify-center text-xs">
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded bg-gradient-to-r from-purple-500 to-pink-500"></div>
              <span className="text-slate-400">750+</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded bg-gradient-to-r from-yellow-500 to-orange-500"></div>
              <span className="text-slate-400">500-749</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded bg-gradient-to-r from-blue-500 to-cyan-500"></div>
              <span className="text-slate-400">300-499</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded bg-gradient-to-r from-green-500 to-emerald-500"></div>
              <span className="text-slate-400">100-299</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded bg-gradient-to-r from-slate-500 to-slate-400"></div>
              <span className="text-slate-400">&lt;100</span>
            </div>
          </div>
        </div>

        {/* Show more indicator */}
        {brawlers.length > 15 && (
          <div className="text-center mt-4 text-slate-500 text-sm">
            Affichage des 15 meilleurs sur {brawlers.length} brawlers
          </div>
        )}
      </div>
    </div>
  );
}

export default TrophyChart;
