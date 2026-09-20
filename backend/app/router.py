import os
import re
from enum import Enum
from typing import Optional, Dict, Set
from pydantic import BaseModel
from backend.app.config import settings


class IntentType(str, Enum):
    # Core 14 Intents
    GREETING = "GREETING"
    CASUAL_CONVERSATION = "CASUAL_CONVERSATION"
    EMOTIONAL_CONVERSATION = "EMOTIONAL_CONVERSATION"
    FOLLOW_UP = "FOLLOW_UP"
    GENERAL_QA = "GENERAL_QA"
    COLLEGE = "COLLEGE"
    HANDBOOK = "HANDBOOK"
    TECHNICAL = "TECHNICAL"
    CODING = "CODING"
    CANVAS = "CANVAS"
    DOCUMENT = "DOCUMENT"
    CURRENT_INFO = "CURRENT_INFO"
    CREATIVE = "CREATIVE"
    COMPLEX_REASONING = "COMPLEX_REASONING"

    # Backward-compatible aliases
    GRATITUDE = "GRATITUDE"
    FAREWELL = "FAREWELL"
    SIMPLE_CONVERSATION = "SIMPLE_CONVERSATION"
    HANDBOOK_QUERY = "HANDBOOK"
    FACTUAL_QUERY = "GENERAL_QA"
    REASONING = "COMPLEX_REASONING"
    COMPLEX_TASK = "COMPLEX_REASONING"
    UNKNOWN = "GENERAL_QA"


CONVERSATIONAL_INTENTS: Set[IntentType] = {
    IntentType.GREETING,
    IntentType.CASUAL_CONVERSATION,
    IntentType.EMOTIONAL_CONVERSATION,
    IntentType.GRATITUDE,
    IntentType.FAREWELL,
    IntentType.SIMPLE_CONVERSATION,
}


class IntentClassificationResult(BaseModel):
    intent: IntentType
    is_conversational: bool
    confidence: float
    routing_reason: str
    maximum_rung: int = 3


class ConversationIntentClassifier:
    """
    Lightweight, deterministic intent classifier for Kifayat Gateway.
    Evaluates user input BEFORE repair-ladder escalation.
    Separates casual conversational messages (max_rung=1, no handbook)
    from knowledge, coding, canvas, and complex reasoning queries.
    """

    CANVAS_INDICATORS = [
        "canvas", "interactive app", "html app", "build an app in canvas", "calculator in html",
        "create a game", "interactive html", "web app", "interactive widget", "build a webpage",
        "render in canvas", "canvas code", "render in iframe", "interactive calculator",
        "build a calculator", "make a calculator", "create a calculator", "tic tac toe in html",
        "to-do list app", "todo app in html", "dashboard in html", "calculator in canvas"
    ]

    CODING_INDICATORS = [
        "write a python", "write python", "python function", "python script", "fastapi", "pydantic",
        "write html", "write css", "write javascript", "write js", "html and css", "html css js",
        "create a button", "create a card", "create an app", "create a counter",
        "create a form", "create a navbar", "write code", "implement a", "implement an",
        "write a function", "write a class", "binary search", "sieve of eratosthenes", "fibonacci",
        "palindrome check", "algorithm for", "build a java application", "build an application",
        "sql query", "react component", "debug this code", "fix this error", "code for",
        "write a script", "write c++", "write java", "regex for", "unit test"
    ]

    COMPLEX_REASONING_INDICATORS = [
        "compare these architectures", "architectural differences", "quantum annealing",
        "explain in depth", "derive the mathematical", "prove that", "step-by-step reasoning",
        "detailed tradeoff", "system design for", "thorough analysis", "formal proof",
        "algorithmic complexity proof", "game theory analysis"
    ]

    COLLEGE_HANDBOOK_INDICATORS = [
        "hostel", "hostel fee", "hostel rent", "hostel caution", "occupancy", "room rent",
        "mess", "mess fee", "veg mess", "egg counter", "central mess committee", "cmc",
        "attendance", "attendance condonation", "fa grade", "course detention", "minimum attendance",
        "placement", "tpc", "training and placement", "placement eligibility", "cgpa",
        "curfew", "in-time", "campus gate", "curfew timing",
        "scholarship", "financial aid", "prerna", "tuition waiver",
        "admission", "documents required", "tuition fee", "b.tech", "semester fee",
        "charaka", "health center", "medical emergency", "ambulance",
        "anti-ragging", "arc", "disciplinary committee", "grading policy", "kit",
        "kifayat institute", "campus rules", "dean of academic", "hostel warden"
    ]

    DOCUMENT_INDICATORS = [
        "summarize this document", "summarize the document", "uploaded file", "from the attachment",
        "analyze this pdf", "review this resume", "document summary", "extract text from",
        "read this file", "summarize attachment"
    ]

    CURRENT_INFO_INDICATORS = [
        "today's date", "current time", "what time is it", "latest news", "today's weather",
        "stock price today", "who won today", "current president", "recent news"
    ]

    CREATIVE_INDICATORS = [
        "write a poem", "write a story", "write a song", "write a haiku", "brainstorm names",
        "creative writing", "write a script", "write a dialogue", "compose a speech"
    ]

    TECHNICAL_INDICATORS = [
        "how does backpropagation work", "explain kubernetes", "tcp vs udp", "explain dns",
        "how do neural networks work", "difference between process and thread", "what is oauth2",
        "database indexing", "btree vs hash index", "explain raft consensus", "how does https work",
        "memory leak in", "garbage collection in", "rest vs graphql"
    ]

    FOLLOW_UP_INDICATORS = [
        "why?", "how come?", "explain that", "explain this", "what about it?", "can you elaborate",
        "tell me more", "how does it work?", "give an example of it", "what do you mean by that?",
        "is that true?", "more details", "how so?", "and then what?", "why did that happen?"
    ]

    GREETING_PATTERNS = [
        r"^hi\b", r"^hello\b", r"^hey\b", r"^good\s+morning\b", r"^good\s+evening\b",
        r"^good\s+afternoon\b", r"^namaste\b", r"^namaskar\b", r"^hello\s+bhai\b",
        r"^hey\s+there\b", r"^hola\b", r"^sup\b", r"^greetings\b"
    ]

    CASUAL_PATTERNS = [
        r"\bhow\s+are\s+you\b", r"\bhow\s+are\s+you\s+doing\b", r"\bhow(?:\'?s|\s+is)\s+it\s+going\b",
        r"\bwhat(?:\'?s|\s+is)\s+up\b", r"\bhow\s+is\s+your\s+day\b", r"\bkaise\s+ho\b", r"\bkaisa\s+hai\b",
        r"\bkya\s+haal\s+hai\b", r"\bkya\s+haal\b", r"\bkya\s+chal\s+raha\b", r"\ball\s+good\b",
        r"\bsab\s+theek\b", r"\bhow\s+do\s+you\s+do\b", r"\btell\s+me\s+about\s+yourself\b", r"\bwho\s+are\s+you\b"
    ]

    GRATITUDE_PATTERNS = [
        r"\bthanks\b", r"\bthank\s+you\b", r"\bthanks\s+a\s+lot\b", r"\bthank\s+you\s+so\s+much\b",
        r"\bdhanyawad\b", r"\bshukriya\b", r"\bthank\s+you\s+bhai\b", r"\bacha\s+thanks\b",
        r"\bthx\b", r"\bty\b", r"\bmany\s+thanks\b"
    ]

    FAREWELL_PATTERNS = [
        r"\bbye\b", r"\bgoodbye\b", r"\bgood\s+night\b", r"\bsee\s+you\b", r"\bsee\s+you\s+later\b",
        r"\bsee\s+ya\b", r"\balvida\b", r"\bbye\s+milte\s+hain\b", r"\bcya\b", r"\bhave\s+a\s+good\s+day\b"
    ]

    SIMPLE_PATTERNS = [
        r"^ok$", r"^okay$", r"^nice$", r"^great$", r"^cool$", r"^got\s+it$",
        r"^samajh\s+gaya$", r"^theek\s+hai$", r"^awesome$", r"^perfect$",
        r"^understood$", r"^sure$", r"^alright$"
    ]

    EMOTIONAL_PATTERNS = [
        r"\bstressed\b", r"\banxious\b", r"\bdepressed\b", r"\boverwhelmed\b", r"\bworried\b",
        r"\bfeeling down\b", r"\bfeeling sad\b", r"\bnot feeling good\b", r"\bso tired\b",
        r"\bburnout\b", r"\btension\b", r"\bpareshan\b", r"\bfeeling lonely\b", r"\blonely\b",
        r"\bfrustrated\b", r"\bpanic\b", r"\bdistressed\b", r"\bneed emotional support\b",
        r"\bfeeling hopeless\b", r"\blife is tough\b"
    ]

    @classmethod
    def classify(cls, text: str) -> IntentClassificationResult:
        if not text:
            return IntentClassificationResult(
                intent=IntentType.GENERAL_QA,
                is_conversational=False,
                confidence=0.0,
                routing_reason="Empty query; routing to default handler",
                maximum_rung=1
            )

        clean = text.strip()
        lower = clean.lower()
        normalized_words = re.sub(r"[^\w\s]", "", lower).strip()

        # Step 1: Canvas UI & Interactive Apps
        for indicator in cls.CANVAS_INDICATORS:
            if indicator in lower:
                return IntentClassificationResult(
                    intent=IntentType.CANVAS,
                    is_conversational=False,
                    confidence=0.98,
                    routing_reason=f"Interactive Canvas application detected ('{indicator}')",
                    maximum_rung=3
                )

        # Step 2: Coding & Implementation
        for indicator in cls.CODING_INDICATORS:
            if indicator in lower:
                return IntentClassificationResult(
                    intent=IntentType.CODING,
                    is_conversational=False,
                    confidence=0.95,
                    routing_reason=f"Coding intent detected ('{indicator}'); normal repair ladder enabled",
                    maximum_rung=3
                )

        # Step 3: Complex Reasoning & Tradeoff Analysis
        for indicator in cls.COMPLEX_REASONING_INDICATORS:
            if indicator in lower:
                return IntentClassificationResult(
                    intent=IntentType.COMPLEX_REASONING,
                    is_conversational=False,
                    confidence=0.92,
                    routing_reason=f"Complex reasoning/proof detected ('{indicator}'); normal repair ladder enabled",
                    maximum_rung=3
                )

        # Step 4: College & Student Handbook
        for indicator in cls.COLLEGE_HANDBOOK_INDICATORS:
            if indicator in lower:
                return IntentClassificationResult(
                    intent=IntentType.COLLEGE,
                    is_conversational=False,
                    confidence=0.95,
                    routing_reason=f"College handbook inquiry detected ('{indicator}'); grounded context enabled",
                    maximum_rung=3
                )

        # Step 5: Document Analysis
        for indicator in cls.DOCUMENT_INDICATORS:
            if indicator in lower:
                return IntentClassificationResult(
                    intent=IntentType.DOCUMENT,
                    is_conversational=False,
                    confidence=0.90,
                    routing_reason=f"Document analysis detected ('{indicator}')",
                    maximum_rung=3
                )

        # Step 6: Current Info / Temporal
        for indicator in cls.CURRENT_INFO_INDICATORS:
            if indicator in lower:
                return IntentClassificationResult(
                    intent=IntentType.CURRENT_INFO,
                    is_conversational=False,
                    confidence=0.88,
                    routing_reason=f"Current/temporal info inquiry detected ('{indicator}')",
                    maximum_rung=1
                )

        # Step 7: Creative Writing
        for indicator in cls.CREATIVE_INDICATORS:
            if indicator in lower:
                return IntentClassificationResult(
                    intent=IntentType.CREATIVE,
                    is_conversational=False,
                    confidence=0.92,
                    routing_reason=f"Creative writing intent detected ('{indicator}')",
                    maximum_rung=1
                )

        # Step 8: Technical Computer Science Concepts
        for indicator in cls.TECHNICAL_INDICATORS:
            if indicator in lower:
                return IntentClassificationResult(
                    intent=IntentType.TECHNICAL,
                    is_conversational=False,
                    confidence=0.90,
                    routing_reason=f"Technical inquiry detected ('{indicator}')",
                    maximum_rung=3
                )

        # Step 9: Follow-up Questions (short queries referencing prior context)
        if len(clean) < 40:
            for indicator in cls.FOLLOW_UP_INDICATORS:
                if indicator in lower or lower.startswith(indicator):
                    return IntentClassificationResult(
                        intent=IntentType.FOLLOW_UP,
                        is_conversational=False,
                        confidence=0.85,
                        routing_reason=f"Follow-up query detected ('{indicator}'); context continuity enabled",
                        maximum_rung=3
                    )

        # Step 10: Standalone Conversational Intents (Max Rung = 1, No Handbook)
        for pat in cls.GRATITUDE_PATTERNS:
            if re.search(pat, lower):
                return IntentClassificationResult(
                    intent=IntentType.CASUAL_CONVERSATION,
                    is_conversational=True,
                    confidence=0.98,
                    routing_reason="Conversational gratitude; maximum_rung=1",
                    maximum_rung=1
                )

        for pat in cls.FAREWELL_PATTERNS:
            if re.search(pat, lower):
                return IntentClassificationResult(
                    intent=IntentType.CASUAL_CONVERSATION,
                    is_conversational=True,
                    confidence=0.98,
                    routing_reason="Conversational farewell; maximum_rung=1",
                    maximum_rung=1
                )

        for pat in cls.CASUAL_PATTERNS:
            if re.search(pat, lower):
                return IntentClassificationResult(
                    intent=IntentType.CASUAL_CONVERSATION,
                    is_conversational=True,
                    confidence=0.98,
                    routing_reason="Casual conversation / small talk; maximum_rung=1",
                    maximum_rung=1
                )

        for pat in cls.EMOTIONAL_PATTERNS:
            if re.search(pat, lower):
                return IntentClassificationResult(
                    intent=IntentType.EMOTIONAL_CONVERSATION,
                    is_conversational=True,
                    confidence=0.98,
                    routing_reason="Emotional check-in / supportive conversation; maximum_rung=1",
                    maximum_rung=1
                )

        for pat in cls.SIMPLE_PATTERNS:
            if re.search(pat, normalized_words):
                return IntentClassificationResult(
                    intent=IntentType.CASUAL_CONVERSATION,
                    is_conversational=True,
                    confidence=0.95,
                    routing_reason="Simple acknowledgment; maximum_rung=1",
                    maximum_rung=1
                )

        for pat in cls.GREETING_PATTERNS:
            if re.search(pat, lower):
                if len(clean) < 45:
                    return IntentClassificationResult(
                        intent=IntentType.GREETING,
                        is_conversational=True,
                        confidence=0.98,
                        routing_reason="Simple conversational greeting; maximum_rung=1",
                        maximum_rung=1
                    )

        # Step 11: General QA
        return IntentClassificationResult(
            intent=IntentType.GENERAL_QA,
            is_conversational=False,
            confidence=0.75,
            routing_reason="General QA inquiry; normal repair ladder enabled",
            maximum_rung=3
        )


class ModelRouter:
    """
    Kifayat Central Model Router.
    Routes model requests for roles: 'cheap', 'strong', and 'judge'.
    Reads model IDs from environment variables / settings without hardcoding.
    """

    def __init__(
        self,
        cheap_model_id: Optional[str] = None,
        strong_model_id: Optional[str] = None,
        judge_model_id: Optional[str] = None
    ):
        self._models: Dict[str, str] = {
            "cheap": cheap_model_id or os.getenv("CHEAP_MODEL_ID", settings.CHEAP_MODEL_ID),
            "strong": strong_model_id or os.getenv("STRONG_MODEL_ID", settings.STRONG_MODEL_ID),
            "judge": judge_model_id or os.getenv("JUDGE_MODEL_ID", settings.JUDGE_MODEL_ID),
        }

    def get_model(self, role: str) -> str:
        """
        Returns the configured model ID for the given role.
        Raises ValueError with a controlled error message if role is unknown.
        """
        role_key = (role or "").strip().lower()
        if role_key not in self._models:
            valid_roles = list(self._models.keys())
            raise ValueError(f"Unknown model role '{role}'. Valid roles are: {valid_roles}")
        return self._models[role_key]

    @property
    def cheap(self) -> str:
        return self.get_model("cheap")

    @property
    def strong(self) -> str:
        return self.get_model("strong")

    @property
    def judge(self) -> str:
        return self.get_model("judge")
