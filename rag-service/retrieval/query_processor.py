"""
Noise-tolerant legal query preprocessing for Nyaayukti.

The preprocessor creates a *retrieval-only* canonical query while keeping the
user's original wording untouched.  It is deliberately deterministic: it does
not invent facts, infer missing dates, or translate arbitrary free-form Hindi.
It only normalizes high-confidence forms that commonly hurt legal retrieval:

* mixed Indian/Western date and time formats,
* INR amounts expressed as rupees/lakh/crore/million,
* legal/payment acronyms,
* common Hinglish legal-service phrases and slang,
* punctuation/whitespace/duration noise.

The final answer should continue to quote/display ``original_query`` where the
user's wording matters.  ``normalized_query`` is for classification, routing,
embedding/BM25 retrieval and evidence planning.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class ProcessedQuery:
    """Original + canonical retrieval representation with an audit trail."""

    original_query: str
    normalized_query: str
    char_count: int
    word_count: int
    transformations: tuple[str, ...] = field(default_factory=tuple)
    normalized_dates: tuple[str, ...] = field(default_factory=tuple)
    normalized_times: tuple[str, ...] = field(default_factory=tuple)
    normalized_amounts: tuple[str, ...] = field(default_factory=tuple)
    detected_hinglish_terms: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, object]:
        return {
            "original_query": self.original_query,
            "normalized_query": self.normalized_query,
            "char_count": self.char_count,
            "word_count": self.word_count,
            "transformations": list(self.transformations),
            "normalized_dates": list(self.normalized_dates),
            "normalized_times": list(self.normalized_times),
            "normalized_amounts": list(self.normalized_amounts),
            "detected_hinglish_terms": list(self.detected_hinglish_terms),
        }


# Canonical Indian statutory / procedural / payment acronym expansions.
# Appending the full form materially improves BM25 and embedding recall while
# preserving the short form users naturally type.
LEGAL_ACRONYM_EXPANSIONS = [
    (
        re.compile(r"\bBNS(?:\s+codes?)?\b", re.IGNORECASE),
        "BNS (Bharatiya Nyaya Sanhita, 2023)",
    ),
    (
        re.compile(r"\bBNSS\b", re.IGNORECASE),
        "BNSS (Bharatiya Nagarik Suraksha Sanhita, 2023)",
    ),
    (re.compile(r"\bBSA\b", re.IGNORECASE), "BSA (Bharatiya Sakshya Adhiniyam, 2023)"),
    (
        re.compile(r"\bIT\s+Act(?:\s*2000)?\b", re.IGNORECASE),
        "IT Act 2000 (Information Technology Act, 2000)",
    ),
    (re.compile(r"\bFIR\b", re.IGNORECASE), "FIR (First Information Report)"),
    (
        re.compile(r"\bNCRP\b", re.IGNORECASE),
        "NCRP (National Cyber Crime Reporting Portal)",
    ),
    (re.compile(r"\bIMPS\b", re.IGNORECASE), "IMPS (Immediate Payment Service)"),
    (
        re.compile(r"\bNEFT\b", re.IGNORECASE),
        "NEFT (National Electronic Funds Transfer)",
    ),
    (re.compile(r"\bRTGS\b", re.IGNORECASE), "RTGS (Real Time Gross Settlement)"),
    (re.compile(r"\bUPI\b", re.IGNORECASE), "UPI (Unified Payments Interface)"),
    (re.compile(r"\bRBI\b", re.IGNORECASE), "RBI (Reserve Bank of India)"),
    (
        re.compile(r"\bNPCI\b", re.IGNORECASE),
        "NPCI (National Payments Corporation of India)",
    ),
    (
        re.compile(r"\b(?:POCSO(?:\s+Act)?)\b", re.IGNORECASE),
        "POCSO (Protection of Children from Sexual Offences Act)",
    ),
    (
        re.compile(r"\b(?:POSH(?:\s+Act)?)\b", re.IGNORECASE),
        "POSH (Sexual Harassment of Women at Workplace Act)",
    ),
    (
        re.compile(r"\b(?:RTE(?:\s+Act)?)\b", re.IGNORECASE),
        "RTE (Right of Children to Free and Compulsory Education Act)",
    ),
    (
        re.compile(r"\b(?:RTI(?:\s+Act)?)\b", re.IGNORECASE),
        "RTI (Right to Information Act)",
    ),
    (
        re.compile(r"\b(?:GST(?:\s+Act)?)\b", re.IGNORECASE),
        "GST (Goods and Services Tax Act)",
    ),
    (
        re.compile(r"\b(?:IBC|IBC\s+Code)\b", re.IGNORECASE),
        "IBC (Insolvency and Bankruptcy Code)",
    ),
    (
        re.compile(r"\bCIRP\b", re.IGNORECASE),
        "CIRP (Corporate Insolvency Resolution Process)",
    ),
    (re.compile(r"\bICC\b", re.IGNORECASE), "ICC (Internal Complaints Committee)"),
    (re.compile(r"\bCSR\b", re.IGNORECASE), "CSR (Corporate Social Responsibility)"),
]


# High-confidence Hinglish / Indian legal-service vocabulary.  These are phrase
# replacements, not broad translation rules.  This keeps normalization auditable
# and avoids changing legal meaning in arbitrary Hindi sentences.
HINGLISH_CANONICAL_MAP = [
    (
        re.compile(
            r"\bHumne\s+National\s+Cyber\s+Crime\s+Reporting\s+Portal\s+pe\s+complain(?:t)?\s+register\s+kiya(?:\s+hai)?\b",
            re.IGNORECASE,
        ),
        "we registered a complaint on the National Cyber Crime Reporting Portal",
        "Humne ... Portal pe complaint register kiya",
    ),
    (
        re.compile(
            r"\b(?:local\s+)?police\s+station\s*\(\s*Thana\s*\)\s*wale\s+bol\s+rahe\s+hain\s+ki\s+FIR\s+duplicate\s+ho\s+jayegi\b",
            re.IGNORECASE,
        ),
        "local police station personnel are saying that duplicate FIR registration is a concern",
        "police/Thana duplicate FIR phrase",
    ),
    (
        re.compile(r"\bactual\s+problem\s+yeh\s+hai\s+ki\b", re.IGNORECASE),
        "actual problem is that",
        "actual problem yeh hai ki",
    ),
    (re.compile(r"\by[e]?h\s+hai\s+ki\b", re.IGNORECASE), "is that", "yeh hai ki"),
    (re.compile(r"\bhumne\b", re.IGNORECASE), "we", "humne"),
    (
        re.compile(r"\bcomplain(?:t)?\s+register\s+kiya(?:\s+hai)?\b", re.IGNORECASE),
        "registered a complaint",
        "complaint register kiya",
    ),
    (
        re.compile(r"\bNational\s+Cyber\s+Crime\s+Reporting\s+Portal\s+pe\b", re.IGNORECASE),
        "on the National Cyber Crime Reporting Portal",
        "portal pe",
    ),
    (
        re.compile(r"\b(?:local\s+)?police\s+station\s*\(\s*thana\s*\)\s*wale\b", re.IGNORECASE),
        "local police station personnel",
        "police station (Thana) wale",
    ),
    (
        re.compile(r"\bFIR\s+duplicate\s+ho\s+jayegi\b", re.IGNORECASE),
        "duplicate FIR registration concern",
        "FIR duplicate ho jayegi",
    ),
    (
        re.compile(r"\bthana\s+wale\b", re.IGNORECASE),
        "local police station personnel",
        "thana wale",
    ),
    (re.compile(r"\bthana\b", re.IGNORECASE), "police station", "thana"),
    (
        re.compile(r"\bbol\s+rahe\s+hain\s+ki\b", re.IGNORECASE),
        "are saying that",
        "bol rahe hain ki",
    ),
    (
        re.compile(r"\bbol\s+rahe\s+hain\b", re.IGNORECASE),
        "are saying",
        "bol rahe hain",
    ),
    (re.compile(r"\bbol\s+raha\s+hai\b", re.IGNORECASE), "is saying", "bol raha hai"),
    (re.compile(r"\bho\s+jayegi\b", re.IGNORECASE), "will occur", "ho jayegi"),
    (re.compile(r"\bho\s+jayega\b", re.IGNORECASE), "will occur", "ho jayega"),
    (
        re.compile(r"\bpukka\s+proof\b", re.IGNORECASE),
        "reliable admissible electronic evidence proof",
        "pukka proof",
    ),
    (
        re.compile(r"\bpakka\s+proof\b", re.IGNORECASE),
        "reliable admissible electronic evidence proof",
        "pakka proof",
    ),
    (re.compile(r"\bpaise\b", re.IGNORECASE), "money funds", "paise"),
    (
        re.compile(r"\bfraud\s+account\b", re.IGNORECASE),
        "fraudulent beneficiary bank account",
        "fraud account",
    ),
    (re.compile(r"\bjaldi\b", re.IGNORECASE), "quickly urgently", "jaldi"),
    (re.compile(r"\bturant\b", re.IGNORECASE), "immediately urgently", "turant"),
    (
        re.compile(r"\bpolice\s+complaint\s+kar(?:na|ni|di)\b", re.IGNORECASE),
        "file police complaint",
        "police complaint karna",
    ),
    (re.compile(r"\bcase\s+darj\b", re.IGNORECASE), "case registered", "case darj"),
    (re.compile(r"\bfir\s+darj\b", re.IGNORECASE), "FIR registered", "FIR darj"),
]


_MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


def _two_digit_year(year: int) -> int:
    # Legal/cyber questions in this corpus overwhelmingly concern modern dates.
    # 00-69 -> 2000-2069; 70-99 -> 1970-1999 mirrors datetime's common pivot.
    return 2000 + year if year <= 69 else 1900 + year


def _canonical_date(day: int, month: int, year: int) -> str | None:
    try:
        dt = datetime(year, month, day)
    except ValueError:
        return None
    return f"{dt.day:02d} {dt.strftime('%B')} {dt.year:04d}"


def _normalize_dates(text: str, audit: list[str]) -> tuple[str, list[str]]:
    normalized: list[str] = []

    # 15-Aug-26, 15 Aug 2026, 15/Aug/26
    month_name_pat = re.compile(
        r"\b(?P<day>\d{1,2})\s*[-/. ]\s*(?P<mon>Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s*[-/. , ]\s*(?P<year>\d{2,4})\b",
        re.IGNORECASE,
    )

    def repl_name(m: re.Match[str]) -> str:
        day = int(m.group("day"))
        mon = _MONTHS[m.group("mon").lower()]
        year = int(m.group("year"))
        if year < 100:
            year = _two_digit_year(year)
        canon = _canonical_date(day, mon, year)
        if not canon:
            return m.group(0)
        normalized.append(canon)
        audit.append("date_format")
        return f"{canon} ({m.group(0)})"

    text = month_name_pat.sub(repl_name, text)

    # India-first numeric dates: dd/mm/yyyy or dd-mm-yy.  We only normalize when
    # a valid day-month interpretation exists; invalid/ambiguous junk is retained.
    numeric_pat = re.compile(r"\b(?P<day>\d{1,2})[/-](?P<mon>\d{1,2})[/-](?P<year>\d{2,4})\b")

    def repl_numeric(m: re.Match[str]) -> str:
        day = int(m.group("day"))
        mon = int(m.group("mon"))
        year = int(m.group("year"))
        if year < 100:
            year = _two_digit_year(year)
        canon = _canonical_date(day, mon, year)
        if not canon:
            return m.group(0)
        normalized.append(canon)
        audit.append("date_format")
        return f"{canon} ({m.group(0)})"

    text = numeric_pat.sub(repl_numeric, text)
    return text, normalized


def _normalize_times(text: str, audit: list[str]) -> tuple[str, list[str]]:
    normalized: list[str] = []

    ampm_pat = re.compile(
        r"\b(?P<h>1[0-2]|0?[1-9])[:.](?P<m>[0-5]\d)\s*(?P<ampm>a\.?m\.?|p\.?m\.?)\b",
        re.IGNORECASE,
    )

    def repl_ampm(m: re.Match[str]) -> str:
        h = int(m.group("h"))
        minute = int(m.group("m"))
        ap = m.group("ampm").lower().replace(".", "")
        h24 = (h % 12) + (12 if ap == "pm" else 0)
        canon = f"{h24:02d}:{minute:02d}"
        normalized.append(canon)
        audit.append("time_format")
        return f"{canon} ({m.group(0)})"

    text = ampm_pat.sub(repl_ampm, text)

    military_pat = re.compile(
        r"\b(?P<h>[01]\d|2[0-3])(?P<m>[0-5]\d)\s*(?:hrs?|hours?)\b", re.IGNORECASE
    )

    def repl_military(m: re.Match[str]) -> str:
        canon = f"{int(m.group('h')):02d}:{int(m.group('m')):02d}"
        normalized.append(canon)
        audit.append("time_format")
        return f"{canon} ({m.group(0)})"

    text = military_pat.sub(repl_military, text)
    return text, normalized


def _format_decimal(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return (f"{value:.6f}").rstrip("0").rstrip(".")


def _amount_aliases(value: float) -> str:
    return (
        f"{_format_decimal(value / 100000.0)} lakh; "
        f"{_format_decimal(value / 10000000.0)} crore; "
        f"{_format_decimal(value / 1000000.0)} million"
    )


_NUMBER_ONES = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
}
_NUMBER_TENS = {
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}


def _parse_small_number_words(raw: str) -> float | None:
    tokens = [t for t in re.split(r"[\s-]+", raw.lower()) if t and t != "and"]
    if not tokens:
        return None
    total = 0
    current = 0
    for tok in tokens:
        if tok in _NUMBER_ONES:
            current += _NUMBER_ONES[tok]
        elif tok in _NUMBER_TENS:
            current += _NUMBER_TENS[tok]
        elif tok == "hundred":
            current = max(1, current) * 100
        elif tok == "thousand":
            total += max(1, current) * 1000
            current = 0
        else:
            return None
    return float(total + current)


def _normalize_amounts(text: str, audit: list[str]) -> tuple[str, list[str]]:
    normalized: list[str] = []
    placeholders: dict[str, str] = {}

    unit_multiplier = {
        "lakh": 100000.0,
        "lakhs": 100000.0,
        "lac": 100000.0,
        "lacs": 100000.0,
        "crore": 10000000.0,
        "crores": 10000000.0,
        "cr": 10000000.0,
        "million": 1000000.0,
        "millions": 1000000.0,
        "mn": 1000000.0,
    }

    currency_pat = re.compile(
        r"(?<!\w)(?P<prefix>₹|rs\.?|rupees?|inr)\s*(?P<num>\d[\d,]*(?:\.\d+)?)\s*(?P<unit>crores?|cr|lakhs?|lacs?|million(?:s)?|mn)?\s*(?:/-)?",
        re.IGNORECASE,
    )

    def repl_currency(m: re.Match[str]) -> str:
        numeric = float(m.group("num").replace(",", ""))
        unit = (m.group("unit") or "").lower()
        value = numeric * unit_multiplier.get(unit, 1.0)
        canon = f"INR {value:,.0f} ({_amount_aliases(value)}; original {m.group(0).strip()})"
        normalized.append(f"INR {value:,.0f}")
        audit.append("currency_format")
        key = f"__NYAYA_AMOUNT_{len(placeholders)}__"
        placeholders[key] = canon
        return key

    text = currency_pat.sub(repl_currency, text)

    # Bare lakh/crore/million numeric expressions are normalized as magnitude
    # aliases without assuming a currency.  This lets "7.5 million" and
    # "0.75 crore" retrieve the same financial-fraud concepts.
    bare_pat = re.compile(
        r"(?<![\w.])(?P<num>\d+(?:\.\d+)?)\s*(?P<unit>crores?|cr|lakhs?|lacs?|million(?:s)?|mn)\b",
        re.IGNORECASE,
    )

    def repl_bare(m: re.Match[str]) -> str:
        numeric = float(m.group("num"))
        unit = m.group("unit").lower()
        value = numeric * unit_multiplier[unit]
        audit.append("numeric_magnitude")
        return f"{value:,.0f} units ({_amount_aliases(value)}; original {m.group(0)})"

    text = bare_pat.sub(repl_bare, text)

    word_pat = re.compile(
        r"\b(?P<words>(?:(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|and)[\s-]+){0,6}(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand))\s+(?P<unit>crores?|lakhs?|lacs?|millions?)\b",
        re.IGNORECASE,
    )

    def repl_words(m: re.Match[str]) -> str:
        parsed = _parse_small_number_words(m.group("words"))
        if parsed is None:
            return m.group(0)
        unit = m.group("unit").lower()
        value = parsed * unit_multiplier[unit]
        audit.append("number_word_magnitude")
        return f"{value:,.0f} units ({_amount_aliases(value)}; original {m.group(0)})"

    text = word_pat.sub(repl_words, text)
    for key, value in placeholders.items():
        text = text.replace(key, value)
    return text, normalized


def _normalize_durations(text: str, audit: list[str]) -> str:
    original = text
    text = re.sub(r"\bmins?\b", "minutes", text, flags=re.IGNORECASE)
    text = re.sub(r"\bhrs?\b", "hours", text, flags=re.IGNORECASE)
    text = re.sub(r"\bsecs?\b", "seconds", text, flags=re.IGNORECASE)
    if text != original:
        audit.append("duration_unit")
    return text


def _normalize_hinglish(text: str, audit: list[str]) -> tuple[str, list[str]]:
    found: list[str] = []
    for pattern, replacement, label in HINGLISH_CANONICAL_MAP:
        if pattern.search(text):
            text = pattern.sub(replacement, text)
            found.append(label)
            audit.append("hinglish_legal_slang")
    return text, found


def _expand_acronyms(text: str, audit: list[str]) -> str:
    expanded = text
    for pattern, replacement in LEGAL_ACRONYM_EXPANSIONS:
        # Avoid recursively expanding already-canonical parenthetical forms.
        if replacement.lower() in expanded.lower():
            continue
        if pattern.search(expanded):
            expanded = pattern.sub(replacement, expanded)
            audit.append("legal_or_payment_acronym")
    return expanded


def process_query(query: str) -> ProcessedQuery:
    """Return a deterministic, noise-tolerant retrieval representation.

    No transformation is applied to ``original_query``.  The normalized version
    is safe to use for retrieval/classification but should not replace the raw
    text in evidentiary displays or user-visible quotations.
    """
    if not query or not isinstance(query, str):
        raise ValueError("Query string cannot be empty or null.")

    audit: list[str] = []

    # NFKC unifies smart-width punctuation / digits without semantic translation.
    cleaned = unicodedata.normalize("NFKC", query)
    cleaned = cleaned.replace("\u00a0", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        raise ValueError("Query cannot be blank or whitespace-only.")

    cleaned, hinglish = _normalize_hinglish(cleaned, audit)
    cleaned, dates = _normalize_dates(cleaned, audit)
    cleaned, times = _normalize_times(cleaned, audit)
    cleaned = _normalize_durations(cleaned, audit)
    cleaned, amounts = _normalize_amounts(cleaned, audit)
    cleaned = _expand_acronyms(cleaned, audit)

    # Canonical phrase expansions that often appear in noisy cyber-fraud facts.
    phrase_expansions = [
        (r"\bspoofed\s+email\b", "spoofed phishing email impersonation"),
        (
            r"\bmule\s+accounts?\b",
            "mule beneficiary bank accounts layered fund transfers",
        ),
        (
            r"\breverse\s+the\s+transaction\b",
            "reverse recall the fraudulent bank transaction",
        ),
    ]
    for pat, repl in phrase_expansions:
        if re.search(pat, cleaned, flags=re.IGNORECASE):
            cleaned = re.sub(pat, repl, cleaned, flags=re.IGNORECASE)
            audit.append("retrieval_synonym_expansion")

    cleaned = re.sub(r"(?<=\))\s+ko\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    return ProcessedQuery(
        original_query=query,
        normalized_query=cleaned,
        char_count=len(cleaned),
        word_count=len(cleaned.split()),
        transformations=tuple(dict.fromkeys(audit)),
        normalized_dates=tuple(dict.fromkeys(dates)),
        normalized_times=tuple(dict.fromkeys(times)),
        normalized_amounts=tuple(dict.fromkeys(amounts)),
        detected_hinglish_terms=tuple(dict.fromkeys(hinglish)),
    )
