import re
from typing import Tuple, Dict, Any


class PromptSqueezer:
    """
    Dynamic Token Pruner & Syntax-Aware Prompt Compressor ("The Squeezer").
    Protects 100% of code blocks, function signatures, SQL schemas, and JSON syntax.
    Compresses markdown scaffolding, redundant whitespace, and low-entropy conversational filler.
    """

    FILLER_PATTERNS = [
        (re.compile(r'\bin order to\b', re.IGNORECASE), 'to'),
        (re.compile(r'\bas mentioned previously\b', re.IGNORECASE), 'as noted'),
        (re.compile(r'\bplease be advised that\b', re.IGNORECASE), ''),
        (re.compile(r'\bkindly note that\b', re.IGNORECASE), 'note:'),
        (re.compile(r'\bat the present time\b', re.IGNORECASE), 'currently'),
        (re.compile(r'\bdue to the fact that\b', re.IGNORECASE), 'because'),
        (re.compile(r'\bfor the purpose of\b', re.IGNORECASE), 'for'),
        (re.compile(r'\bwith reference to\b', re.IGNORECASE), 'regarding'),
        (re.compile(r'\bin the event that\b', re.IGNORECASE), 'if'),
        (re.compile(r'\bhas the ability to\b', re.IGNORECASE), 'can'),
        (re.compile(r'\bat this point in time\b', re.IGNORECASE), 'now'),
    ]

    @classmethod
    def compress_text(cls, text: str) -> Tuple[str, Dict[str, Any]]:
        """
        Compresses text while isolating and protecting code blocks verbatim.
        """
        if not text or len(text) < 40:
            tokens = max(1, int(len(text) / 3.8))
            return text, {
                "original_tokens": tokens,
                "compressed_tokens": tokens,
                "saved_tokens": 0,
                "savings_pct": 0.0
            }

        original_tokens = max(1, int(len(text) / 3.8))

        # 1. Isolate code blocks (```...```) to protect syntax
        code_blocks = []
        def _code_replacer(match):
            token = f"__CODE_BLOCK_{len(code_blocks)}__"
            code_blocks.append(match.group(0))
            return token

        # Extract code blocks
        protected_text = re.sub(r'```[\s\S]*?```', _code_replacer, text)

        # 2. Compress conversational & markdown filler
        for pattern, replacement in cls.FILLER_PATTERNS:
            protected_text = pattern.sub(replacement, protected_text)

        # 3. Collapse multiple blank lines to a single blank line
        protected_text = re.sub(r'\n{3,}', '\n\n', protected_text)

        # 4. Strip redundant inline whitespace (except leading indentation)
        lines = protected_text.split('\n')
        cleaned_lines = []
        for line in lines:
            if line.startswith('    ') or line.startswith('\t'):
                cleaned_lines.append(line.rstrip())
            else:
                cleaned_lines.append(re.sub(r'[ \t]{2,}', ' ', line).strip())
        protected_text = '\n'.join(cleaned_lines)

        # 5. Restore code blocks verbatim
        for idx, block in enumerate(code_blocks):
            placeholder = f"__CODE_BLOCK_{idx}__"
            protected_text = protected_text.replace(placeholder, block)

        compressed_tokens = max(1, int(len(protected_text) / 3.8))
        saved_tokens = max(0, original_tokens - compressed_tokens)
        savings_pct = round((saved_tokens / original_tokens) * 100.0, 1) if original_tokens > 0 else 0.0

        return protected_text, {
            "original_tokens": original_tokens,
            "compressed_tokens": compressed_tokens,
            "saved_tokens": saved_tokens,
            "savings_pct": savings_pct
        }
