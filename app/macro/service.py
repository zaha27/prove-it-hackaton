"""Macro service module."""

from typing import List

from app.macro.models import MacroNewsItem


class MacroService:
    """Macro service for world macro view endpoints."""

    async def get_macro_news(self) -> List[MacroNewsItem]:
        """Return mock global macro news for world view."""
        return [
            MacroNewsItem(
                title="US inflation slows, but core services remain sticky",
                source="Reuters",
                timestamp="2026-04-04T08:00:00Z",
                sentiment="mixed",
                summary=(
                    "Headline inflation eased month-on-month, while core services "
                    "prices stayed elevated, reinforcing a higher-for-longer policy "
                    "narrative for developed markets."
                ),
            ),
            MacroNewsItem(
                title="Fed signals data-dependent pause as labor market cools gradually",
                source="Bloomberg",
                timestamp="2026-04-04T09:15:00Z",
                sentiment="neutral",
                summary=(
                    "Federal Reserve officials reiterated a cautious stance, balancing "
                    "cooling hiring momentum against still-above-target inflation and "
                    "volatile financial conditions."
                ),
            ),
            MacroNewsItem(
                title="ECB keeps restrictive tone amid uneven eurozone growth",
                source="Financial Times",
                timestamp="2026-04-04T10:05:00Z",
                sentiment="negative",
                summary=(
                    "The ECB emphasized inflation vigilance despite weak industrial "
                    "activity in key economies, increasing recession risk in sectors "
                    "sensitive to credit conditions."
                ),
            ),
            MacroNewsItem(
                title="Red Sea disruptions lift freight premiums on key trade corridors",
                source="Wall Street Journal",
                timestamp="2026-04-04T11:20:00Z",
                sentiment="negative",
                summary=(
                    "Shipping reroutes and higher insurance costs continue to pressure "
                    "delivery times and landed input prices, with spillovers into "
                    "energy and industrial commodity supply chains."
                ),
            ),
            MacroNewsItem(
                title="China's policy support stabilizes commodity import demand",
                source="CNBC",
                timestamp="2026-04-04T12:10:00Z",
                sentiment="positive",
                summary=(
                    "Targeted stimulus for infrastructure and property completion has "
                    "improved near-term demand visibility for metals and bulk inputs, "
                    "while private consumption remains uneven."
                ),
            ),
        ]

    async def get_macro_insight(self) -> str:
        """Return a detailed mock global macroeconomic overview."""
        return (
            "Macro Context (Dobânzi/Bănci Centrale): În ultimele trimestre, "
            "dezinflația avansează lent, dar componentele de servicii și salariile "
            "rămân reziliente, ceea ce menține băncile centrale majore într-un regim "
            "restrictiv și dependent de date. FED și BCE transmit că ritmul potențial "
            "al relaxării monetare va fi gradual, pentru a evita o reaprindere a "
            "inflației de bază, iar această combinație susține costuri de finanțare "
            "ridicate pentru companii și state. "
            "Geopolitică & Supply Chain: Tensiunile din coridoarele maritime, inclusiv "
            "zona Mării Roșii, continuă să crească volatilitatea costurilor logistice, "
            "să extindă timpii de tranzit și să introducă prime de risc în prețurile "
            "energiei, metalelor și bunurilor intermediare. În paralel, cererea din "
            "China arată semne de stabilizare pe segmentele legate de infrastructură, "
            "dar rămâne neuniformă în consumul intern, ceea ce produce impulsuri "
            "asimetice între commodities industriale și cele defensive. "
            "Concluzie / Risc Global: Piața globală a materiilor prime rămâne într-un "
            "echilibru fragil între politica monetară încă restrictivă și șocurile "
            "geopolitice recurente asupra ofertei. Scenariul de bază sugerează "
            "volatilitate ridicată cu episoade de repricing rapid, iar riscul principal "
            "pe termen scurt este o combinație între blocaje logistice persistente și "
            "surprize inflaționiste care întârzie relaxarea dobânzilor."
        )

