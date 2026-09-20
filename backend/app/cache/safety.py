import re
from typing import Optional


class CacheSafetyValidator:
    """
    Evaluates whether a user query and context are safe for semantic response caching.
    Prevents caching of:
    - Personalized or private information (e.g., student ID, my attendance, my grades)
    - Time-sensitive questions (e.g., 'today', 'right now', 'current time', 'date today')
    - Conversation-dependent deictic references (e.g., 'that branch', 'who said that', 'earlier')
    - Authentication or payment states (e.g., 'my transaction status', 'my balance')
    """

    UNSAFE_PATTERNS = [
        # Personalized references
        r"\bmy\b", r"\bmine\b", r"\bmera\b", r"\bmeri\b", r"\bmere\b",
        r"\broll\s*(?:no|number)\b", r"\bstudent\s*id\b", r"\bapplication\s*number\b",
        # Real-time questions
        r"\btoday\b", r"\bright\s*now\b", r"\bcurrent\s*time\b", r"\baaj\b", r"\babhi\b",
        # Balance / payment specifics
        r"\bmy\s*balance\b", r"\bdues\b", r"\btransaction\s*id\b", r"\breceipt\s*no\b",
        # Deictic conversation references that cannot stand alone
        r"\bwhat\s+did\s+i\s+ask\b", r"\bpehle\s+kya\s+bola\b", r"\bthat\s+one\b",
        # Coding and instruction requests MUST always generate fresh responses tailored to user input
        r"\bcode\b", r"\bhtml\b", r"\bcss\b", r"\bjavascript\b", r"\bjs\b", r"\bpython\b",
        r"\bfunction\b", r"\bscript\b", r"\bcreate\b", r"\bbuild\b", r"\bwrite\b",
        r"\bimplement\b", r"\bmake\b", r"\badd\b", r"\bfix\b", r"\bchange\b",
        r"\bmodify\b", r"\bdebug\b", r"\bcomponent\b", r"\bpage\b", r"\bdesign\b",
        r"\bcart\b", r"\bcalculator\b", r"\btodo\b", r"\bbutton\b", r"\bcard\b"
    ]

    @classmethod
    def is_cacheable(cls, question: str, context: Optional[str] = None) -> bool:
        if not question or len(question.strip()) < 5:
            return False

        q_lower = question.lower().strip()

        # Check regex patterns
        for pattern in cls.UNSAFE_PATTERNS:
            if re.search(pattern, q_lower):
                return False

        # If question is pure pronouns or conversational filler
        if q_lower in ["yes", "no", "ok", "thanks", "thank you", "kya", "haan", "theek hai"]:
            return False

        return True
