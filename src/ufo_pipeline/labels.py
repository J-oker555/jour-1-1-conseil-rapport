import re
from dataclasses import dataclass

import pandas as pd

HOAX_TERMS = ("hoax", "fake", "prank", "joke", "joking", "balloon prank")
HOAX_PATTERN = re.compile(r"\b(?:" + "|".join(re.escape(term) for term in HOAX_TERMS) + r")\b", re.IGNORECASE)
HOAX_RULE = (
    "un releve est marque comme canular si le temoignage contient un mot explicite "
    "comme hoax, fake, prank, joke, joking ou balloon prank"
)


@dataclass(frozen=True)
class HoaxLabelResult:
    labels: pd.Series
    rule: str
    positive_count: int
    positive_rate: float
    trigger_counts: dict[str, int]
    examples: list[str]
    limitation: str


def build_hoax_label(comments: pd.Series) -> pd.Series:
    return describe_hoax_label(comments).labels


def describe_hoax_label(comments: pd.Series) -> HoaxLabelResult:
    text = comments.fillna("").astype(str)
    labels = text.str.contains(HOAX_PATTERN, regex=True)
    trigger_counts = {
        term: int(text.str.contains(rf"\b{re.escape(term)}\b", case=False, regex=True).sum())
        for term in HOAX_TERMS
    }
    examples = text[labels].drop_duplicates().head(5).tolist()
    return HoaxLabelResult(
        labels=labels,
        rule=HOAX_RULE,
        positive_count=int(labels.sum()),
        positive_rate=float(labels.mean()),
        trigger_counts={term: count for term, count in trigger_counts.items() if count > 0},
        examples=examples,
        limitation=(
            "Cette regle rate les canulars qui ne sont pas avoues dans le texte et peut "
            "attraper a tort un temoignage qui nie explicitement le canular."
        ),
    )

