from collections import defaultdict, Counter
from typing import Any, Optional

class PlayerAnalyzer:
    """Analyzer for player battle history and social connections."""

    @staticmethod
    def analyze_connections(player_tag: str, battle_log: dict[str, Any]) -> dict[str, Any]:
        """
        Analyze battle log to find teammates and calculate synergy.
        
        Args:
            player_tag: The tag of the main player (to identify "me").
            battle_log: The raw battle log from Brawl Stars API.
            
        Returns:
            Dictionary containing processed graph data and stats.
        """
        battles = battle_log.get('items', [])
        
        # Data Structures
        # Key: (name, tag) -> Value: Stats dict
        teammates = defaultdict(lambda: {'wins': 0, 'losses': 0, 'draws': 0, 'total': 0, 'modes': Counter()})
        
        # Normalize player tag for comparison
        my_tag = player_tag.upper().replace("#", "")

        for battle_record in battles:
            battle = battle_record.get('battle', {})
            event = battle_record.get('event', {})
            mode = event.get('mode')
            result = battle.get('result') # victory, defeat, draw
            
            my_team = []
            
            # Extract "My Team"
            if 'teams' in battle:
                # 3v3 or Duo Showdown
                for team in battle['teams']:
                    is_my_team = False
                    for p in team:
                        p_tag = p['tag'].upper().replace("#", "")
                        if p_tag == my_tag:
                            is_my_team = True
                            break
                    
                    if is_my_team:
                        my_team = team
                        break
            elif 'players' in battle:
                # Solo modes - no teammates to track
                continue

            # Process Teammates in My Team
            for p in my_team:
                p_tag = p['tag'].upper().replace("#", "")
                
                # Skip self
                if p_tag == my_tag:
                    continue
                
                p_name = p['name']
                
                # Use tuple key (name, tag) to ensure uniqueness
                key = (p_name, p_tag)
                
                stats = teammates[key]
                stats['total'] += 1
                if mode:
                    stats['modes'][mode] += 1
                
                if result == 'victory':
                    stats['wins'] += 1
                elif result == 'defeat':
                    stats['losses'] += 1
                else:
                    stats['draws'] += 1

        # Format results for API
        formatted_teammates = []
        best_partner = None
        worst_partner = None
        
        for (name, tag), stats in teammates.items():
            win_rate = (stats['wins'] / stats['total']) * 100 if stats['total'] > 0 else 0
            
            # Determine Synergy Rating
            if win_rate >= 60:
                synergy = "excellent"
            elif win_rate >= 45:
                synergy = "good"
            elif win_rate >= 30:
                synergy = "neutral"
            else:
                synergy = "bad"
                
            entry = {
                "name": name,
                "tag": tag,
                "stats": {
                    "total": stats['total'],
                    "wins": stats['wins'],
                    "losses": stats['losses'],
                    "winRate": round(win_rate, 1),
                    "favoriteMode": stats['modes'].most_common(1)[0][0] if stats['modes'] else None
                },
                "synergy": synergy
            }
            formatted_teammates.append(entry)

        # Sort by total games played, then win rate
        formatted_teammates.sort(key=lambda x: (x['stats']['total'], x['stats']['winRate']), reverse=True)

        return {
            "total_battles_analyzed": len(battles),
            "teammates": formatted_teammates
        }
