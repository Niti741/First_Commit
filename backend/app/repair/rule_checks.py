from typing import Tuple


class CheapRuleChecker:
    """
    Deterministic instant checks to prevent unnecessary expensive judge LLM calls.
    Catches empty answers, canned refusals, and obvious failures.
    """

    REFUSAL_TRIGGERS = [
        "as an ai language model",
        "i am an ai",
        "i cannot fulfill this request",
        "i do not possess personal",
        "i am unable to answer",
        "as a large language model"
    ]

    @classmethod
    def check_answer(cls, answer: str, question: str = "") -> Tuple[bool, str]:
        """
        Returns (is_valid, reason).
        If is_valid is False, the answer fails immediately without calling the judge.
        """
        if not answer:
            return False, "Answer is completely empty."

        clean = answer.strip()
        if not clean:
            return False, "Answer is whitespace only."

        # Require at least one alphanumeric character (allows valid short answers like '4', '2+2=4', 'Yes')
        if not any(c.isalnum() for c in clean):
            return False, "Answer contains no alphanumeric characters."

        clean_lower = clean.lower()
        for trigger in cls.REFUSAL_TRIGGERS:
            if trigger in clean_lower:
                return False, f"Answer contains canned AI refusal trigger: '{trigger}'."

        # Quality check for coding queries: If user specifically asks for code, ensure code block is present
        if question:
            q_lower = question.lower()
            coding_intents = [
                "write a python", "write html", "write css", "write javascript", "write js",
                "create a button", "create a card", "create an app", "create a counter",
                "create a calculator", "create a form", "create a navbar", "write code",
                "implement a", "fastapi endpoint", "pydantic model", "function in python",
                "code in html", "code in javascript", "3d card in html"
            ]
            if any(intent in q_lower for intent in coding_intents):
                if "```" not in clean:
                    return False, "Coding request was answered without required markdown code block."

        return True, "Passed deterministic rule checks."
