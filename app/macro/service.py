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
            "**AI Insight — World Macro View**\n\n"
            "- **Global conflict risk premium is rising:** The Russia-Ukraine war and Black Sea security risks keep grains vulnerable to shipment interruptions, while tensions around Iran and the Strait of Hormuz maintain upside risk for crude oil and tanker insurance costs.\n"
            "- **Red Sea disruption remains a key transmission channel:** Houthi-related attacks and rerouting via the Cape of Good Hope extend delivery times, tighten near-term energy logistics, and raise input costs across fertilizer and food supply chains.\n"
            "- **Fed policy remains the macro anchor:** A higher-for-longer stance supports the USD and restrains cyclical risk appetite, but any dovish pivot could quickly amplify commodity volatility through weaker real yields and easier financial conditions.\n"
            "- **China demand is the swing factor:** Stabilizing Chinese industrial activity can absorb part of the geopolitical supply shock by supporting energy and metals demand, while weak manufacturing or property data would cap broad commodity upside.\n"
            "- **Cross-asset implication:** Energy shocks can spill into agriculture through fuel, transport, and fertilizer channels, keeping wheat and food inflation sensitive to geopolitical escalation even when headline demand is mixed."
        )
