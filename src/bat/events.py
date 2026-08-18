from __future__ import annotations

EVENT_COLUMNS = ["datetime", "city", "state", "country"]


def event_group_columns() -> list[str]:
    """Colonnes pressenties pour regrouper plusieurs temoins du meme evenement."""
    return EVENT_COLUMNS.copy()

