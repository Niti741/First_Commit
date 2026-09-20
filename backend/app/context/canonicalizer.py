import hashlib
import re


class Canonicalizer:
    @staticmethod
    def canonicalize_text(text: str) -> str:
        """
        Canonicalizes text for stable prefix caching:
        - Normalizes Windows \r\n to \n
        - Strips trailing whitespace from each line
        - Collapses multiple redundant blank lines into maximum two
        - Strips leading and trailing blank lines
        """
        if not text:
            return ""
        # Normalize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # Strip trailing space on each line
        lines = [re.sub(r"[ \t]+$", "", line) for line in text.split("\n")]
        # Remove consecutive blank lines
        cleaned_lines = []
        consecutive_blank = 0
        for line in lines:
            if not line.strip():
                consecutive_blank += 1
                if consecutive_blank <= 1:
                    cleaned_lines.append("")
            else:
                consecutive_blank = 0
                cleaned_lines.append(line)
        return "\n".join(cleaned_lines).strip()

    @staticmethod
    def compute_prefix_hash(prefix_text: str) -> str:
        """Computes SHA-256 hash of the canonicalized prefix."""
        canonical = Canonicalizer.canonicalize_text(prefix_text)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
