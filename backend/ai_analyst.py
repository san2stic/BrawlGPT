"""
AI Analyst using Gemini Flash for high-speed meta analysis.
"""

import logging
import os
from typing import Dict, List, Any
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class MetaAnalyst:
    """
    Uses Gemini Flash to analyze aggregated battle data.
    """
    
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )
        self.model = "moonshotai/kimi-k2.5" # Efficient, fast model

    async def analyze_meta_report(self, meta_report: dict) -> str:
        """
        Generate insights from the crawler's meta report.
        """
        prompt = f"""
        Analyse ce rapport de "Meta" Brawl Stars basé sur les derniers matchs du joueur ({meta_report['analyzed_matches']} matchs analysés).
        
        Données brutes (Brawlers les plus vus):
        {meta_report['most_popular_brawlers']}
        
        Tâche:
        1. Identifie la "Meta" actuelle dans la tranche de trophées de ce joueur.
        2. Quels brawlers sont omniprésents ?
        3. Conseille 2-3 "Counters" efficaces contre ces brawlers populaires.
        
        Réponds de manière concise et stratégique, style "Rapport d'Intelligence", en Markdown.
        """
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Tu es une IA tactique avancée pour Brawl Stars using Google Gemini Flash. Tu analyses la meta."},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Gemini Analysis failed: {e}")
            return f"Analyse indisponible: {str(e)}"

    async def analyze_global_meta(self, global_data: Dict[str, Any]) -> str:
        """
        Analyze global meta data and generate comprehensive insights.
        """
        try:
            if not global_data:
                logger.warning("analyze_global_meta received empty global_data")
                return "Données d'analyse indisponibles."

            top_brawlers_data = global_data.get("top_brawlers", [])
            if top_brawlers_data is None:
                top_brawlers_data = [] # Handle explict None
            top_brawlers = top_brawlers_data[:15]

            mode_breakdown_data = global_data.get("mode_breakdown", {})
            if mode_breakdown_data is None:
                mode_breakdown_data = {} # Handle explicit None
            mode_breakdown = mode_breakdown_data
        
            prompt = f"""
            Analyse cette méta GLOBALE de Brawl Stars basée sur des données réelles de milliers de joueurs.
            
            📊 **Top 15 Brawlers**:
            {self._format_brawler_list(top_brawlers)}
            
            🎮 **Breakdown par Mode**:
            {self._format_mode_breakdown(mode_breakdown)}
            
            🎯 **Tâches**:
            1. Identifie les 5 brawlers DOMINANT la méta actuelle
            2. Analyse les tendances par mode de jeu
            3. Recommande une tier list S/A/B pour la méta actuelle
            4. Conseille les meilleurs picks pour chaque mode
            5. Identifie les counters efficaces contre les tops brawlers
            
            Réponds en Markdown structuré, style rapport d'analyste pro. Sois concis mais précis.
            """
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Tu es un analyste méta expert de Brawl Stars. Tu fournis des insights basés sur des données réelles de milliers de parties."
                    },
                    {"role": "user", "content": prompt}
                ]
            )
            
            if not response or not response.choices:
                logger.error("Empty response from AI provider")
                return "Erreur d'analyse: Pas de réponse de l'IA"
                
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Global meta analysis failed: {e}", exc_info=True)
            return f"# Analyse Globale Indisponible\n\nErreur: {str(e)}"

    async def generate_trend_insights(self, trend_data: List[Dict[str, Any]]) -> List[str]:
        """
        Generate insights from trending brawler data.
        
        Args:
            trend_data: List of brawlers with trend information
            
        Returns:
            List of insight strings (markdown format)
        """
        if not trend_data:
            return []
        
        rising = [b for b in trend_data if b.get("trend_direction") == "rising"]
        falling = [b for b in trend_data if b.get("trend_direction") == "falling"]
        
        prompt = f"""
        Analyse ces tendances de la méta Brawl Stars:
        
        📈 **En Montée** ({len(rising)} brawlers):
        {self._format_trend_list(rising[:5])}
        
        📉 **En Descente** ({len(falling)} brawlers):
        {self._format_trend_list(falling[:5])}
        
        Pour chaque tendance significative:
        1. Explique POURQUOI ce changement (méta shift, nerf/buff, nouveau mode, etc.)
        2. Conseille comment en profiter (pour montée) ou s'adapter (pour descente)
        
        Limite-toi aux 3 tendances les plus importantes. Format: bullet points concis.
        """
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Tu es un analyste expert des tendances méta de Brawl Stars."
                    },
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Split response into individual insights
            content = response.choices[0].message.content
            return [content]  # Return as single comprehensive insight
            
        except Exception as e:
            logger.error(f"Trend insight generation failed: {e}")
            return []

    async def analyze_brawler_synergies(self, synergy_data: List[Dict[str, Any]], brawler_name: str = None) -> str:
        """
        Analyze brawler synergies and provide strategic recommendations.
        
        Args:
            synergy_data: List of synergy records
            brawler_name: Optional specific brawler to focus on
            
        Returns:
            Markdown-formatted synergy analysis
        """
        if not synergy_data:
            return "# Aucune Donnée de Synergie Disponible\n\nPas assez de données pour analyser les synergies."
        
        focus_text = f" pour **{brawler_name}**" if brawler_name else ""
        
        prompt = f"""
        Analyse ces synergies de brawlers{focus_text} basées sur des données réelles:
        
        {self._format_synergy_list(synergy_data[:10])}
        
        🎯 **Tâches**:
        1. Identifie les 3 meilleures compositions d'équipe
        2. Explique POURQUOI ces synergies fonctionnent (gameplay, rôles complémentaires)
        3. Conseille les modes où ces combos excellent
        4. Mentionne les contre-stratégies adverses à anticiper
        
        Sois tactique et actionnable. Format Markdown.
        """
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Tu es un coach tactique expert de Brawl Stars spécialisé dans les synergies d'équipe."
                    },
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Synergy analysis failed: {e}")
            return f"# Analyse de Synergie Indisponible\n\nErreur: {str(e)}"

    def _format_brawler_list(self, brawlers: List[Dict]) -> str:
        """Format brawler list for AI prompt."""
        if not brawlers:
            return "Aucune donnée"
        
        lines = []
        for i, b in enumerate(brawlers, 1):
            lines.append(
                f"{i}. **{b.get('brawler_name', 'Unknown')}** - "
                f"Win Rate: {b.get('win_rate', 0):.1f}%, "
                f"Pick Rate: {b.get('pick_rate', 0):.1f}%, "
                f"Games: {b.get('games', 0)}"
            )
        return "\n".join(lines)

    def _format_mode_breakdown(self, modes: Dict[str, Any]) -> str:
        """Format mode breakdown for AI prompt."""
        if not modes:
            return "Aucune donnée"
        
        lines = []
        for mode, data in modes.items():
            best = data.get("best_brawlers", [])[:3]
            if best:
                brawler_names = ", ".join([b.get("name", "?") for b in best])
                lines.append(f"- **{mode}**: {brawler_names}")
        
        return "\n".join(lines) if lines else "Aucune donnée"

    def _format_trend_list(self, trends: List[Dict]) -> str:
        """Format trend data for AI prompt."""
        if not trends:
            return "Aucune tendance significative"
        
        lines = []
        for t in trends:
            lines.append(
                f"- **{t.get('brawler_name', 'Unknown')}**: "
                f"Win Rate {t.get('win_rate', 0):.1f}%, "
                f"Pick Rate {t.get('pick_rate', 0):.1f}% "
                f"(Force: {t.get('trend_strength', 0):.0%})"
            )
        return "\n".join(lines)

    def _format_synergy_list(self, synergies: List[Dict]) -> str:
        """Format synergy data for AI prompt."""
        if not synergies:
            return "Aucune synergie"
        
        lines = []
        for s in synergies:
            lines.append(
                f"- **{s.get('brawler_a_name', '?')} + {s.get('brawler_b_name', '?')}**: "
                f"Win Rate {s.get('win_rate', 0):.1f}%, "
                f"{s.get('games_together', 0)} games, "
                f"Quality: {s.get('sample_size_quality', 'unknown')}"
            )
        return "\n".join(lines)

