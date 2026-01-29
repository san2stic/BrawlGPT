/**
 * Player tag input component - redesigned with glassmorphism
 */

import type { ReactElement, FormEvent, ChangeEvent } from "react";
import { useState } from "react";
import { Search } from 'lucide-react';
import type { PlayerInputProps } from "../types";
import Button from "./Button";
import Card from "./Card";
import './PlayerInput.css';

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
    <Card variant="elevated" className="player-input-card">
      <form onSubmit={handleSubmit} className="player-input-form">
        <div className="input-wrapper-custom">
          <label htmlFor="tag" className="input-label-custom">
            Brawl Stars Player Tag
          </label>
          <div className="input-container-custom">
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
              className="input-field-custom"
            />
            <span className="input-icon-custom">#</span>
          </div>
        </div>
        <Button
          type="submit"
          variant="primary"
          size="lg"
          fullWidth
          loading={loading}
          disabled={!tag.trim()}
          icon={<Search size={20} />}
        >
          Brawl!
        </Button>
      </form>
    </Card>
  );
}

export default PlayerInput;
