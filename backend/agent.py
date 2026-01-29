"""
AI Agent for BrawlGPT.
Generates coaching insights using OpenRouter API with dynamic tools support.
"""

import logging
import json
from typing import Any, Optional
from datetime import datetime

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from exceptions import AIGenerationError
from db_models import Interaction, Insight, ConversationMemory, PlayerHistory
from agent_tools import AGENT_TOOLS, AgentToolExecutor

logger = logging.getLogger(__name__)


# =============================================================================
# SYSTEM PROMPTS
# =============================================================================

SYSTEM_PROMPT_BASE = """Tu es BrawlCoach, un coach IA expert de Brawl Stars avec accès à des données en temps réel.

## Tes Capacités
- Analyse complète des profils joueurs (tous les brawlers, historique de combats)
- Accès à la meta actuelle par tranche de trophées via les tools
- Connaissance des events en rotation
- Suivi de la progression dans le temps
- Recommandations personnalisées basées sur les données réelles

## Tes Tools Disponibles
Tu peux appeler ces tools pour obtenir des informations en temps réel:
- `get_brawler_stats`: Stats détaillées d'un brawler (HP, damage, gadgets, star powers)
- `get_current_meta`: Meta actuelle (tier list, win rates) pour une tranche de trophées
- `get_best_brawlers_for_mode`: Meilleurs brawlers pour un mode spécifique
- `analyze_matchup`: Analyse d'un matchup entre 2 brawlers
- `get_current_events`: Events actuellement en rotation
- `get_player_progression`: Historique de progression du joueur
- `compare_with_similar_players`: Comparaison avec joueurs similaires
- `get_trending_compositions`: Compositions d'équipe gagnantes
- `analyze_player_brawler`: Performance d'un brawler spécifique pour ce joueur
- `set_player_goal`: Définir un objectif de progression

## Comment Utiliser les Tools
- Utilise les tools quand le joueur demande des infos spécifiques
- Pour "quoi jouer?" → utilise get_current_meta ou get_best_brawlers_for_mode
- Pour infos sur un brawler → utilise get_brawler_stats
- Pour les events → utilise get_current_events
- Pour la progression → utilise get_player_progression

## Format de Réponse
- Utilise le Markdown pour la mise en forme
- Sois précis et actionnable
- Base tes conseils sur les données réelles
- Mentionne les brawlers spécifiques avec leurs stats
- Adapte ton niveau de détail au niveau du joueur

## Langue
RÉPONDS TOUJOURS EN FRANÇAIS."""


SYSTEM_PROMPT_ANALYSIS = """Tu es un coach expert de Brawl Stars. Fournis des conseils concis et actionnables en format Markdown. Sois encourageant mais honnête sur les points à améliorer. RÉPONDS TOUJOURS EN FRANÇAIS."""


class AIAgent:
    """AI-powered coaching agent for Brawl Stars with tools support."""

    def __init__(self, api_key: str, brawl_client=None):
        """
        Initialize the AI agent.

        Args:
            api_key: OpenRouter API key
            brawl_client: Optional Brawl Stars client for tool execution
        """
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )
        self.brawl_client = brawl_client
        # Cost-effective model for gaming insights
        self.model = "moonshotai/kimi-k2.5"
        self.tools_enabled = True

    def _extract_player_summary(self, player_data: dict[str, Any]) -> dict[str, Any]:
        """
        Extract relevant player information for AI analysis.
        Now includes ALL brawlers, not just top 5.

        Args:
            player_data: Full player data from API

        Returns:
            Summarized player data
        """
        brawlers = player_data.get('brawlers', [])

        # Sort all brawlers by trophies
        all_brawlers_summary = [
            {
                "name": b.get('name'),
                "trophies": b.get('trophies'),
                "highestTrophies": b.get('highestTrophies', 0),
                "rank": b.get('rank'),
                "power": b.get('power'),
                "id": b.get('id')
            }
            for b in sorted(brawlers, key=lambda x: x.get('trophies', 0), reverse=True)
        ]

        return {
            "name": player_data.get('name', 'Unknown'),
            "tag": player_data.get('tag'),
            "trophies": player_data.get('trophies', 0),
            "highestTrophies": player_data.get('highestTrophies', 0),
            "expLevel": player_data.get('expLevel', 1),
            "3vs3Victories": player_data.get('3vs3Victories', 0),
            "soloVictories": player_data.get('soloVictories', 0),
            "duoVictories": player_data.get('duoVictories', 0),
            "totalBrawlers": len(brawlers),
            "allBrawlers": all_brawlers_summary,
            "topBrawlers": all_brawlers_summary[:10],  # Top 10 for quick reference
            "club": player_data.get('club', {}).get('name') if player_data.get('club') else None,
            "clubTag": player_data.get('club', {}).get('tag') if player_data.get('club') else None
        }

    def _extract_battle_summary(self, battle_log: dict[str, Any], limit: int = 25) -> list[dict[str, Any]]:
        """
        Extract and summarize recent battles.
        Now extracts up to 25 battles instead of 5.

        Args:
            battle_log: Full battle log from API
            limit: Number of battles to extract

        Returns:
            List of summarized battle information
        """
        battles = []

        if not isinstance(battle_log, dict) or 'items' not in battle_log:
            return battles

        for battle in battle_log['items'][:limit]:
            event = battle.get('event', {})
            battle_info = battle.get('battle', {})

            summary = {
                "mode": event.get('mode'),
                "map": event.get('map'),
                "result": battle_info.get('result'),
                "trophyChange": battle_info.get('trophyChange'),
                "duration": battle_info.get('duration'),
                "type": battle_info.get('type'),
                "rank": battle_info.get('rank'),  # For Showdown
            }

            # Extract brawler used
            star_player = battle_info.get('starPlayer', {})
            if star_player:
                summary["starPlayer"] = star_player.get('name')
                summary["starBrawler"] = star_player.get('brawler', {}).get('name')

            # Extract teams for 3v3
            if 'teams' in battle_info:
                summary["teams"] = battle_info['teams']

            battles.append(summary)

        return battles

    def _calculate_stats(self, player_summary: dict[str, Any], battle_summary: list[dict]) -> dict[str, Any]:
        """
        Calculate additional statistics for coaching.
        Enhanced with more detailed analysis.
        """
        # Win rate from recent battles (all available)
        if battle_summary:
            wins = sum(1 for b in battle_summary if b.get('result') == 'victory' or (b.get('rank') and b.get('rank') <= 4))
            win_rate = (wins / len(battle_summary)) * 100
        else:
            win_rate = None

        # Trophy efficiency
        total_victories = (
            player_summary.get('3vs3Victories', 0) +
            player_summary.get('soloVictories', 0) +
            player_summary.get('duoVictories', 0)
        )

        # Skill tier estimation based on trophies
        trophies = player_summary.get('trophies', 0)
        if trophies >= 50000:
            skill_tier = "Legendary"
            tier_description = "Joueur d'élite, top niveau mondial"
        elif trophies >= 30000:
            skill_tier = "Master"
            tier_description = "Joueur très expérimenté"
        elif trophies >= 20000:
            skill_tier = "Diamond"
            tier_description = "Joueur confirmé"
        elif trophies >= 10000:
            skill_tier = "Gold"
            tier_description = "Joueur intermédiaire"
        elif trophies >= 5000:
            skill_tier = "Silver"
            tier_description = "Joueur en progression"
        else:
            skill_tier = "Bronze"
            tier_description = "Joueur débutant"

        # Mode breakdown from battles
        mode_stats = {}
        for b in battle_summary:
            mode = b.get('mode', 'unknown')
            if mode not in mode_stats:
                mode_stats[mode] = {'wins': 0, 'games': 0}
            mode_stats[mode]['games'] += 1
            if b.get('result') == 'victory' or (b.get('rank') and b.get('rank') <= 4):
                mode_stats[mode]['wins'] += 1

        # Best and worst modes
        mode_win_rates = {
            mode: stats['wins'] / stats['games'] * 100
            for mode, stats in mode_stats.items()
            if stats['games'] >= 2
        }
        best_mode = max(mode_win_rates.items(), key=lambda x: x[1])[0] if mode_win_rates else None
        worst_mode = min(mode_win_rates.items(), key=lambda x: x[1])[0] if mode_win_rates else None

        # Brawler diversity score
        brawlers_used = set()
        for b in battle_summary:
            if b.get('starBrawler'):
                brawlers_used.add(b['starBrawler'])
        diversity_score = len(brawlers_used) / max(len(battle_summary), 1) * 100

        return {
            "recentWinRate": f"{win_rate:.1f}%" if win_rate is not None else "N/A",
            "recentWinRateValue": win_rate,
            "totalVictories": total_victories,
            "estimatedSkillTier": skill_tier,
            "tierDescription": tier_description,
            "avgTrophiesPerBrawler": trophies // max(player_summary.get('totalBrawlers', 1), 1),
            "bestMode": best_mode,
            "worstMode": worst_mode,
            "modeStats": mode_win_rates,
            "brawlerDiversity": f"{diversity_score:.0f}%",
            "battlesAnalyzed": len(battle_summary)
        }

    async def analyze_profile(
        self,
        player_data: dict[str, Any],
        battle_log: dict[str, Any],
        db: AsyncSession = None
    ) -> str:
        """
        Generate AI coaching insights for a player.
        Enhanced with more data and better analysis.
        """
        logger.info(f"Generating AI insights for player: {player_data.get('name', 'Unknown')}")

        # Extract comprehensive summaries
        player_summary = self._extract_player_summary(player_data)
        battle_summary = self._extract_battle_summary(battle_log, limit=25)
        calculated_stats = self._calculate_stats(player_summary, battle_summary)

        # Build comprehensive prompt
        prompt = f"""Tu es un coach expert de Brawl Stars. Analyse ce profil en profondeur et fournis un coaching personnalisé EN FRANÇAIS.

## Profil du Joueur
- **Nom**: {player_summary['name']}
- **Trophées Totaux**: {player_summary['trophies']:,}
- **Record de Trophées**: {player_summary['highestTrophies']:,}
- **Niveau d'Expérience**: {player_summary['expLevel']}
- **Club**: {player_summary['club'] or 'Aucun Club'}
- **Nombre de Brawlers**: {player_summary['totalBrawlers']}

## Statistiques de Victoires
- Victoires 3v3: {player_summary['3vs3Victories']:,}
- Victoires Solo: {player_summary['soloVictories']:,}
- Victoires Duo: {player_summary['duoVictories']:,}
- **Total**: {calculated_stats['totalVictories']:,}

## Top 10 Brawlers
{self._format_brawlers(player_summary['topBrawlers'])}

## Analyse des {calculated_stats['battlesAnalyzed']} Derniers Matchs
{self._format_battles_detailed(battle_summary[:10])}

## Statistiques Avancées
- **Taux de Victoire Récent**: {calculated_stats['recentWinRate']} (sur {calculated_stats['battlesAnalyzed']} matchs)
- **Niveau Estimé**: {calculated_stats['estimatedSkillTier']} - {calculated_stats['tierDescription']}
- **Moyenne Trophées/Brawler**: {calculated_stats['avgTrophiesPerBrawler']}
- **Meilleur Mode**: {calculated_stats['bestMode'] or 'N/A'}
- **Mode à Améliorer**: {calculated_stats['worstMode'] or 'N/A'}
- **Diversité de Brawlers**: {calculated_stats['brawlerDiversity']}

## Stats par Mode
{self._format_mode_stats(calculated_stats.get('modeStats', {}))}

---

Basé sur cette analyse complète, fournis EN FRANÇAIS:

1. **Évaluation Globale** (3-4 phrases): Évalue le niveau actuel, les points forts et les axes d'amélioration.

2. **5 Conseils Personnalisés pour Progresser**:
   - Chaque conseil doit être spécifique et basé sur les stats réelles
   - Mentionne des brawlers ou modes précis
   - Adapte au niveau {calculated_stats['estimatedSkillTier']}
   - Inclus au moins un conseil sur le mode à améliorer

3. **Plan de Progression**: Sur quoi se concentrer cette semaine pour gagner des trophées?

4. **Brawlers Recommandés**: 3 brawlers que ce joueur devrait push en priorité et pourquoi.

Formate ta réponse en Markdown propre avec des en-têtes. RÉPONDS UNIQUEMENT EN FRANÇAIS."""

        try:
            logger.debug("Sending request to OpenRouter API")
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT_ANALYSIS},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4000,
                temperature=0.7
            )

            insights = response.choices[0].message.content

            # Save insight and player history to DB
            if db and player_summary.get('tag'):
                await self._save_insight_and_history(db, player_summary, insights)

            logger.info("Successfully generated AI insights")
            return insights

        except Exception as e:
            logger.error(f"Failed to generate AI insights: {e}")
            raise AIGenerationError(f"Failed to generate coaching insights: {str(e)}")

    async def _save_insight_and_history(
        self,
        db: AsyncSession,
        player_summary: dict,
        insights: str
    ):
        """Save insight and player history snapshot."""
        try:
            player_tag = player_summary['tag'].upper().replace("#", "")

            # Save insight
            new_insight = Insight(
                player_tag=player_tag,
                content=insights,
                timestamp=datetime.utcnow()
            )
            db.add(new_insight)

            # Save player history snapshot
            history = PlayerHistory(
                player_tag=player_tag,
                timestamp=datetime.utcnow(),
                trophies=player_summary.get('trophies', 0),
                highest_trophies=player_summary.get('highestTrophies', 0),
                brawler_count=player_summary.get('totalBrawlers', 0),
                victories_3v3=player_summary.get('3vs3Victories', 0),
                solo_victories=player_summary.get('soloVictories', 0),
                duo_victories=player_summary.get('duoVictories', 0),
                exp_level=player_summary.get('expLevel', 1),
                club_name=player_summary.get('club'),
                club_tag=player_summary.get('clubTag')
            )
            db.add(history)

            await db.commit()
            logger.info("Saved insight and history to database")
        except Exception as e:
            logger.error(f"Failed to save to DB: {e}")
            await db.rollback()

    def _format_brawlers(self, brawlers: list[dict]) -> str:
        """Format brawler list for prompt."""
        if not brawlers:
            return "- Aucun brawler disponible"

        lines = []
        for b in brawlers:
            lines.append(
                f"- **{b['name']}**: {b['trophies']} trophées "
                f"(Rang {b['rank']}, Power {b['power']})"
            )
        return "\n".join(lines)

    def _format_battles_detailed(self, battles: list[dict]) -> str:
        """Format battle list with more details."""
        if not battles:
            return "- Aucun match récent"

        lines = []
        for b in battles:
            result = b.get('result', 'unknown')
            if b.get('rank'):
                result = f"Rang {b['rank']}"

            result_emoji = "✅" if result == 'victory' or (b.get('rank') and b.get('rank') <= 4) else "❌"
            trophy_change = b.get('trophyChange')
            trophy_str = f" ({trophy_change:+d})" if trophy_change is not None else ""

            mode = b.get('mode', 'Unknown')
            map_name = b.get('map', '')

            lines.append(f"- {result_emoji} **{mode}** sur {map_name}: {result}{trophy_str}")
        return "\n".join(lines)

    def _format_mode_stats(self, mode_stats: dict) -> str:
        """Format mode statistics."""
        if not mode_stats:
            return "- Pas assez de données par mode"

        lines = []
        for mode, win_rate in sorted(mode_stats.items(), key=lambda x: x[1], reverse=True):
            emoji = "🔥" if win_rate >= 60 else "✅" if win_rate >= 50 else "⚠️"
            lines.append(f"- {emoji} **{mode}**: {win_rate:.1f}% win rate")
        return "\n".join(lines)

    def _format_all_brawlers_summary(self, brawlers: list[dict]) -> str:
        """Format all brawlers for chat context."""
        if not brawlers:
            return "Aucun brawler trouvé."

        sorted_brawlers = sorted(brawlers, key=lambda x: x.get('trophies', 0), reverse=True)

        lines = ["**Liste des Brawlers** (triés par trophées):"]
        for b in sorted_brawlers[:20]:  # Limit to top 20 for context size
            lines.append(f"- {b['name']}: {b['trophies']} tr - R{b['rank']} - P{b['power']}")

        if len(sorted_brawlers) > 20:
            lines.append(f"... et {len(sorted_brawlers) - 20} autres brawlers")

        return "\n".join(lines)

    async def _get_chat_history(self, db: AsyncSession, player_tag: str, limit: int = 5) -> str:
        """Retrieve recent chat history from database."""
        try:
            stmt = select(Interaction).where(
                Interaction.player_tag == player_tag
            ).order_by(Interaction.timestamp.desc()).limit(limit)

            result = await db.execute(stmt)
            interactions = result.scalars().all()

            if not interactions:
                return ""

            history_text = "\n\n**Historique des conversations récentes:**\n"
            for interaction in reversed(interactions):
                history_text += f"User: {interaction.input_message}\nAssistant: {interaction.output_message[:200]}...\n"

            return history_text
        except Exception as e:
            logger.error(f"Failed to retrieve chat history: {e}")
            return ""

    async def _get_conversation_memory(self, db: AsyncSession, player_tag: str) -> str:
        """Retrieve long-term conversation memory."""
        try:
            stmt = select(ConversationMemory).where(
                ConversationMemory.player_tag == player_tag
            ).order_by(ConversationMemory.timestamp.desc()).limit(3)

            result = await db.execute(stmt)
            memories = result.scalars().all()

            if not memories:
                return ""

            memory_text = "\n\n**Mémoire du joueur:**\n"
            for mem in memories:
                if mem.user_goals:
                    memory_text += f"- Objectifs: {', '.join(mem.user_goals)}\n"
                if mem.key_points:
                    memory_text += f"- Points clés: {', '.join(mem.key_points[:3])}\n"

            return memory_text
        except Exception as e:
            logger.error(f"Failed to retrieve conversation memory: {e}")
            return ""

    async def chat(
        self,
        messages: list[dict[str, str]],
        player_context: Optional[dict[str, Any]] = None,
        db: AsyncSession = None
    ) -> str:
        """
        Chat with the AI agent with tools support.
        """
        try:
            # Build enriched system prompt
            system_content = SYSTEM_PROMPT_BASE

            player_tag = None
            if player_context:
                player_summary = self._extract_player_summary(player_context)
                player_tag = player_summary.get('tag', '').upper().replace("#", "")

                system_content += f"""

## Contexte du Joueur Actuel
- **Nom**: {player_summary['name']}
- **Trophées**: {player_summary['trophies']:,}
- **Niveau**: {player_summary['expLevel']}
- **Club**: {player_summary['club'] or 'Aucun'}
- **Brawlers**: {player_summary['totalBrawlers']}

{self._format_all_brawlers_summary(player_summary.get('allBrawlers', []))}
"""

            # Add conversation history and memory
            if db and player_tag:
                history = await self._get_chat_history(db, player_tag)
                memory = await self._get_conversation_memory(db, player_tag)
                if history:
                    system_content += history
                if memory:
                    system_content += memory
                system_content += "\nUtilise cet historique pour donner des conseils cohérents."

            # Prepare messages for API
            api_messages = [{"role": "system", "content": system_content}]

            last_user_message = ""
            for msg in messages:
                if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                    api_messages.append({"role": msg['role'], "content": msg['content']})
                    if msg['role'] == 'user':
                        last_user_message = msg['content']

            # First API call - may return tool calls
            logger.debug("Sending chat request to OpenRouter API")

            if self.tools_enabled and self.brawl_client and db:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=api_messages,
                    tools=AGENT_TOOLS,
                    tool_choice="auto",
                    max_tokens=2000,
                    temperature=0.7
                )

                # Handle tool calls if any
                response_message = response.choices[0].message

                if response_message.tool_calls:
                    # Execute tools and get results
                    tool_executor = AgentToolExecutor(
                        self.brawl_client,
                        db,
                        player_context
                    )

                    api_messages.append({
                        "role": "assistant",
                        "content": response_message.content,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            }
                            for tc in response_message.tool_calls
                        ]
                    })

                    for tool_call in response_message.tool_calls:
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)

                        logger.info(f"Executing tool: {function_name}")
                        tool_result = await tool_executor.execute_tool(function_name, function_args)

                        api_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(tool_result, ensure_ascii=False)
                        })

                    # Second API call with tool results
                    response = await self.client.chat.completions.create(
                        model=self.model,
                        messages=api_messages,
                        max_tokens=2000,
                        temperature=0.7
                    )

                response_text = response.choices[0].message.content

            else:
                # Simple chat without tools
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=api_messages,
                    max_tokens=2000,
                    temperature=0.7
                )
                response_text = response.choices[0].message.content

            # Save interaction to DB
            if db and player_tag and last_user_message:
                try:
                    new_interaction = Interaction(
                        player_tag=player_tag,
                        input_message=last_user_message,
                        output_message=response_text,
                        timestamp=datetime.utcnow()
                    )
                    db.add(new_interaction)
                    await db.commit()
                    logger.info("Saved interaction to database")
                except Exception as e:
                    logger.error(f"Failed to save interaction: {e}")

            return response_text

        except Exception as e:
            logger.error(f"Failed to generate chat response: {e}")
            raise AIGenerationError(f"Failed to generate response: {str(e)}")

    async def generate_game_schedule(
        self,
        player_data: dict[str, Any],
        battle_log: dict[str, Any],
        schedule_type: str,
        duration_days: int,
        goals: list[str],
        focus_brawlers: list[str]
    ) -> dict[str, Any]:
        """
        Generate a personalized game schedule using AI.
        
        Args:
            player_data: Full player data from Brawl Stars API
            battle_log: Recent battle log
            schedule_type: Type of schedule ("weekly", "trophy_push", "brawler_mastery")
            duration_days: Number of days to plan for
            goals: User-specified goals
            focus_brawlers: Specific brawlers to focus on
            
        Returns:
            Dictionary containing schedule description and list of events
        """
        logger.info(f"Generating {schedule_type} schedule for {duration_days} days")
        
        # Extract player summary
        player_summary = self._extract_player_summary(player_data)
        battle_summary = self._extract_battle_summary(battle_log, limit=25)
        calculated_stats = self._calculate_stats(player_summary, battle_summary)
        
        # Build comprehensive prompt for schedule generation
        prompt = f"""Tu es un coach expert de Brawl Stars. Crée un planning de jeux personnalisé ULTRA-DÉTAILLÉ pour ce joueur.

## Profil du Joueur
- **Nom**: {player_summary['name']}
- **Trophées Totaux**: {player_summary['trophies']:,}
- **Record**: {player_summary['highestTrophies']:,}
- **Niveau**: {calculated_stats['estimatedSkillTier']} - {calculated_stats['tierDescription']}
- **Win Rate Récent**: {calculated_stats['recentWinRate']}
- **Meilleur Mode**: {calculated_stats['bestMode'] or 'N/A'}
- **Mode à Améliorer**: {calculated_stats['worstMode'] or 'N/A'}

## Top 10 Brawlers
{self._format_brawlers(player_summary['topBrawlers'][:10])}

## Type de Planning
- **Type**: {schedule_type}
- **Durée**: {duration_days} jours
- **Objectifs**: {', '.join(goals) if goals else 'Progression générale'}
- **Focus spécifique**: {', '.join(focus_brawlers) if focus_brawlers else 'Tous les brawlers'}

---

**INSTRUCTIONS POUR LA GÉNÉRATION DU PLANNING:**

1. **Analyse la situation actuelle:**
   - Identifie les brawlers proches de milestones de rang (ex: 500, 750, 1000 trophées)
   - Considère le power level de chaque brawler
   - Regarde les performances récentes par mode
   - Tiens compte du niveau du joueur ({calculated_stats['estimatedSkillTier']})

2. **Crée des sessions quotidiennes optimales:**
   - Matin (10h-12h): Sessions courtes (1-2h) focus skill
   - Après-midi (14h-17h): Longues sessions grind optionnelles
   - Soirée (18h-21h): Peak time, sessions principales (2-3h)
   - Nuit (21h-23h): Sessions détente optionnelles

3. **Adapte au type de planning:**
   - **weekly**: Variété équilibrée, progression stable, 2-3 sessions par jour
   - **trophy_push**: Focus intensif sur les meilleurs brawlers, 3-4 sessions par jour
   - **brawler_mastery**: Sessions dédiées aux brawlers spécifiques, pratique ciblée

4. **Principes de coaching:**
   - Alterne les modes pour éviter le burnout
   - Planifie des pauses/repos après sessions intenses
   - Priorise les brawlers avec Power 9-11
   - Suggère des maps favorables quand possible
   - Inclus des notes de stratégie spécifiques

5. **Gestion de l'énergie:**
   - Jours 1-3: Intensité modérée, apprentissage
   - Jours 4-5: Peak performance, push principal
   - Jours 6-7: Consolidation et repos

**FORMAT DE SORTIE (JSON strict):**

{{
  "description": "Description détaillée du planning (2-3 phrases expliquant la stratégie globale)",
  "events": [
    {{
      "start": "2026-01-28T18:00:00",  // ISO format, heure de début
      "end": "2026-01-28T20:00:00",    // ISO format, heure de fin
      "title": "Push Colt - Trio Ranked",  // Titre court et clair
      "event_type": "ranked",  // "ranked", "practice", "challenge", "rest"
      "recommended_brawler": "Colt",  // Nom du brawler
      "recommended_mode": "gemGrab",  // gemGrab, brawlBall, heist, bounty, etc.
      "recommended_map": "Hard Rock Mine",  // Nom de map si pertinent, sinon null
      "notes": "Focus sur le positionnement mid. Utilise le second gadget pour l'engagement. Joue avec un heavweight en frontlane.",  // Conseils détaillés
      "priority": "high",  // "low", "medium", "high"
      "color": "#4CAF50"  // Couleur hex pour le calendrier
    }}
  ]
}}

**IMPORTANT:**
- Génère exactement {duration_days * 3} à {duration_days * 4} événements (3-4 par jour)
- Chaque événement doit avoir des notes coaching spécifiques
- Les horaires doivent être réalistes et progressifs
- Commence à partir d'aujourd'hui: 2026-01-28
- Varie les brawlers et modes intelligemment
- Inclus 1-2 sessions "rest" sur la période pour éviter le burnout
- Les couleurs doivent varier par type d'événement

**COULEURS PAR TYPE:**
- ranked: #4CAF50 (vert)
- practice: #2196F3 (bleu)
- challenge: #FF9800 (orange)
- rest: #9E9E9E (gris)

RÉPONDS UNIQUEMENT AVEC LE JSON, RIEN D'AUTRE."""

        try:
            logger.debug("Sending schedule generation request to AI")
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Tu es un expert coach de Brawl Stars. Génère UNIQUEMENT du JSON valide, rien d'autre."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=6000,
                temperature=0.8,  # Slightly higher for creative scheduling
                response_format={"type": "json_object"}  # Enforce JSON response
            )

            response_text = response.choices[0].message.content
            logger.debug(f"AI response: {response_text[:200]}...")
            
            # Parse JSON response
            schedule_data = json.loads(response_text)
            
            # Validate response structure
            if "events" not in schedule_data:
                raise ValueError("AI response missing 'events' field")
            
            if not isinstance(schedule_data["events"], list):
                raise ValueError("'events' must be a list")
            
            # Validate each event
            for event in schedule_data["events"]:
                required_fields = ["start", "end", "title"]
                for field in required_fields:
                    if field not in event:
                        raise ValueError(f"Event missing required field: {field}")
            
            logger.info(f"Successfully generated schedule with {len(schedule_data['events'])} events")
            return schedule_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            raise AIGenerationError(f"Invalid AI response format: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to generate schedule: {e}")
            raise AIGenerationError(f"Schedule generation failed: {str(e)}")
    
    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        player_context: Optional[dict[str, Any]] = None,
        db: AsyncSession = None
    ):
        """
        Stream chat responses chunk by chunk for real-time UI updates.
        
        Args:
            messages: Chat history
            player_context: Optional player data for context
            db: Database session
            
        Yields:
            String chunks of the AI response
        """
        try:
            # Build enriched system prompt (same as chat method)
            system_content = SYSTEM_PROMPT_BASE
            
            player_tag = None
            if player_context:
                player_summary = self._extract_player_summary(player_context)
                player_tag = player_summary.get('tag', '').upper().replace("#", "")
                
                system_content += f"""

## Contexte du Joueur Actuel
- **Nom**: {player_summary['name']}
- **Trophées**: {player_summary['trophies']:,}
- **Niveau**: {player_summary['expLevel']}
- **Club**: {player_summary['club'] or 'Aucun'}
- **Brawlers**: {player_summary['totalBrawlers']}

{self._format_all_brawlers_summary(player_summary.get('allBrawlers', []))}
"""
            
            # Add conversation history and memory
            if db and player_tag:
                history = await self._get_chat_history(db, player_tag)
                memory = await self._get_conversation_memory(db, player_tag)
                if history:
                    system_content += history
                if memory:
                    system_content += memory
                system_content += "\nUtilise cet historique pour donner des conseils cohérents."
            
            # Prepare messages for API
            api_messages = [{"role": "system", "content": system_content}]
            
            last_user_message = ""
            for msg in messages:
                if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                    api_messages.append({"role": msg['role'], "content": msg['content']})
                    if msg['role'] == 'user':
                        last_user_message = msg['content']
            
            logger.debug("Sending streaming chat request to OpenRouter API")
            
            # Create streaming response
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=api_messages,
                max_tokens=2000,
                temperature=0.7,
                stream=True  # Enable streaming
            )
            
            # Stream chunks
            full_response = ""
            async for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield content
            
            # Save interaction to DB after streaming completes
            if db and player_tag and last_user_message:
                try:
                    new_interaction = Interaction(
                        player_tag=player_tag,
                        input_message=last_user_message,
                        output_message=full_response,
                        timestamp=datetime.utcnow()
                    )
                    db.add(new_interaction)
                    await db.commit()
                    logger.info("Saved streamed interaction to database")
                except Exception as e:
                    logger.error(f"Failed to save streamed interaction: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to generate streaming chat response: {e}")
            raise AIGenerationError(f"Failed to generate streaming response: {str(e)}")
            raise AIGenerationError(f"AI returned invalid JSON: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to generate schedule: {e}")
            raise AIGenerationError(f"Failed to generate schedule: {str(e)}")
