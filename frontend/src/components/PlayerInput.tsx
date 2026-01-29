/**
 * Player tag input component
 */

import type { ReactElement, FormEvent, ChangeEvent } from "react";
import { useState } from "react";
import type { PlayerInputProps } from "../types";

function PlayerInput({ onSearch, loading }: PlayerInputProps): ReactElement {
  const [tag, setTag] = useState<string>("");

  const handleSubmit = (e: FormEvent<HTMLFormElement>): void => {
    e.preventDefault();
    const trimmedTag = tag.trim();
    if (trimmedTag) {
      onSearch(trimmedTag);
    }
  };

  const handleChange = (e: ChangeEvent<HTMLInputElement>): void => {
    setTag(e.target.value);
  };

  return (
    <div className="w-full max-w-md mx-auto p-4">
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <label
          htmlFor="tag"
          className="text-white text-lg font-bold tracking-wide"
        >
          Brawl Stars Player Tag
        </label>
        <div className="relative">
          <input
            id="tag"
            type="text"
            value={tag}
            onChange={handleChange}
            placeholder="#9L9..."
            autoComplete="off"
            autoCorrect="off"
            autoCapitalize="characters"
            spellCheck={false}
            className="w-full bg-slate-800 text-white border-2 border-yellow-500 rounded-xl px-4 py-3 focus:outline-none focus:ring-4 focus:ring-yellow-500/50 shadow-[0_0_15px_rgba(234,179,8,0.3)] transition-all uppercase placeholder-slate-500 font-mono"
          />
          <span className="absolute right-4 top-1/2 -translate-y-1/2 text-yellow-500 font-bold">
            #
          </span>
        </div>
        <button
          type="submit"
          disabled={loading || !tag.trim()}
          className="w-full bg-gradient-to-r from-yellow-500 to-orange-600 text-white font-black text-xl py-3 rounded-xl shadow-lg hover:scale-[1.02] active:scale-95 transition-transform disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 uppercase tracking-wider"
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <svg
                className="animate-spin h-5 w-5"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              Loading...
            </span>
          ) : (
            "Brawl!"
          )}
        </button>
      </form>
    </div>
  );
}

export default PlayerInput;
