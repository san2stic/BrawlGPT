import os
import logging
from collections import defaultdict, Counter
from datetime import datetime
from dotenv import load_dotenv
from brawlstars import BrawlStarsClient

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()
API_KEY = os.getenv("BRAWL_API_KEY")
PLAYER_TAG = "#Y08U22LV9"

if not API_KEY:
    logger.error("BRAWL_API_KEY not found in .env")
    exit(1)

def analyze_history():
    client = BrawlStarsClient(API_KEY)
    
    try:
        # Fetch Player Profile (for context)
        player = client.get_player(PLAYER_TAG)
        logger.info(f"Analyzing history for: {player['name']} ({player['tag']})")
        
        # Fetch Battle Log
        battle_log = client.get_battle_log(PLAYER_TAG)
        battles = battle_log.get('items', [])
        logger.info(f"Fetched {len(battles)} recent battles")
        
        # Analysis Data Structures
        teammates = defaultdict(lambda: {'wins': 0, 'losses': 0, 'draws': 0, 'total': 0, 'modes': Counter()})
        opponents = defaultdict(lambda: {'wins': 0, 'losses': 0, 'draws': 0, 'total': 0})
        
        # Process Battles
        for battle_record in battles:
            battle = battle_record.get('battle', {})
            event = battle_record.get('event', {})
            mode = event.get('mode')
            result = battle.get('result') # victory, defeat, draw
            
            # Identify "My" Team and "Enemy" Team
            # Teams structure varies by mode
            # Standard 3v3: teams is a list of lists [[p1, p2, p3], [e1, e2, e3]]
            # Duo Showdown: teams is list of lists
            # Solo Showdown: players is list
            
            my_team = []
            enemy_teams = []
            
            if 'teams' in battle:
                # Find which team contains the player
                found_me = False
                for team in battle['teams']:
                    # Check if player is in this team
                    is_my_team = False
                    for p in team:
                        if p['tag'] == player['tag']:
                            is_my_team = True
                            break
                    
                    if is_my_team:
                        my_team = team
                        found_me = True
                    else:
                        enemy_teams.append(team)
            elif 'players' in battle:
                # Solo modes usually
                # We can't really track "teammates" in solo, only opponents if we want
                pass
            
            # Record Teammates
            for p in my_team:
                if p['tag'] == player['tag']:
                    continue
                
                t_tag = p['tag']
                t_name = p['name']
                t_hero = p['brawler']['name']
                
                start_stat = teammates[(t_name, t_tag)]
                start_stat['total'] += 1
                start_stat['modes'][mode] += 1
                
                if result == 'victory':
                    start_stat['wins'] += 1
                elif result == 'defeat':
                    start_stat['losses'] += 1
                else:
                    start_stat['draws'] += 1

        # Generate Report
        generate_report(player, teammates, len(battles))
        generate_mermaid_graph(player, teammates)
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        import traceback
        traceback.print_exc()

def generate_report(player, teammates, total_battles):
    report_path = "/Users/bastienjavaux/.gemini/antigravity/brain/a34e9600-0892-455c-a115-9fd4959a7ec3/analysis_report.md"
    
    # Sort teammates by games played
    sorted_teammates = sorted(teammates.items(), key=lambda x: x[1]['total'], reverse=True)
    
    with open(report_path, "w") as f:
        f.write(f"# Rapport d'Analyse: {player['name']} ({player['tag']})\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"**Parties Analysées:** {total_battles} (Dernières parties disponibles via API)\n\n")
        
        f.write("## 🤝 Partenaires de Jeu\n\n")
        f.write("| Joueur | Parties | Victoires | Défaites | Win Rate | Modes Favoris |\n")
        f.write("|---|---|---|---|---|---|\n")
        
        for (name, tag), stats in sorted_teammates:
            win_rate = (stats['wins'] / stats['total']) * 100
            top_mode = stats['modes'].most_common(1)[0][0] if stats['modes'] else "N/A"
            f.write(f"| **{name}** | {stats['total']} | {stats['wins']} | {stats['losses']} | {win_rate:.1f}% | {top_mode} |\n")
            
        if not sorted_teammates:
            f.write("\n_Aucun partenaire trouvé dans les parties récentes (probablement que du Solo ou Randoms)._\n")

        f.write("\n## 🧠 Analyse de Synergie\n\n")
        if sorted_teammates:
            best_partner = max(sorted_teammates, key=lambda x: (x[1]['wins'] / x[1]['total']) if x[1]['total'] > 1 else 0)
            worst_partner = min(sorted_teammates, key=lambda x: (x[1]['wins'] / x[1]['total']) if x[1]['total'] > 1 else 1)
            
            f.write(f"- 🌟 **Meilleur Duo:** Avec **{best_partner[0][0]}**, vous avez un taux de victoire de **{(best_partner[1]['wins']/best_partner[1]['total'])*100:.1f}%**.\n")
            if best_partner != worst_partner:
                f.write(f"- ⚠️ **Duo Difficile:** Avec **{worst_partner[0][0]}**, le taux de victoire chute à **{(worst_partner[1]['wins']/worst_partner[1]['total'])*100:.1f}%**.\n")
        else:
            f.write("Pas assez de données multijoueur pour l'analyse de synergie.\n")

    logger.info(f"Report generated at {report_path}")

def generate_mermaid_graph(player, teammates):
    graph_path = "/Users/bastienjavaux/.gemini/antigravity/brain/a34e9600-0892-455c-a115-9fd4959a7ec3/player_graph.md"
    
    # Filter for significant interactions (e.g., played together more than once OR mostly wins)
    # Since API returns limited history (25 games), we simulate 'all' for now
    
    with open(graph_path, "w") as f:
        f.write("# Graphe des Interactions\n\n")
        f.write("```mermaid\n")
        f.write("graph TD\n")
        f.write(f"    ME(({player['name']}))\n")
        f.write("    style ME fill:#f9f,stroke:#333,stroke-width:4px\n")
        
        for (name, tag), stats in teammates.items():
            # Sanitize name for mermaid id
            safe_name = name.replace(" ", "_").replace("'", "").replace('"', "")
            
            # Determine link style based on win rate
            win_rate = stats['wins'] / stats['total']
            
            if win_rate >= 0.6:
                link_style = "-->" # Good synergy
                style_def = "fill:#9f9,stroke:#333" # Green
            elif win_rate <= 0.4:
                link_style = "-.->" # Bad synergy
                style_def = "fill:#f99,stroke:#333" # Red
            else:
                link_style = "---" # Neutral
                style_def = "fill:#ff9,stroke:#333" # Yellow
                
            f.write(f"    {safe_name}[{name}] {link_style}|{stats['total']} games| ME\n")
            f.write(f"    style {safe_name} {style_def}\n")
            
        f.write("```\n")
    
    logger.info(f"Graph generated at {graph_path}")

if __name__ == "__main__":
    analyze_history()
