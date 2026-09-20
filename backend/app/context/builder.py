import os
from typing import List, Dict, Any, Optional
from backend.app.config import settings
from backend.app.context.canonicalizer import Canonicalizer
from backend.app.context.squeezer import PromptSqueezer


class ContextBuilder:
    """
    Unified ContextBuilder for Kifayat Gateway.
    Strictly enforces cache-friendly prompt ordering:
    SYSTEM:
      [1] System instructions
      [2] Canonicalized handbook
      <!-- CACHE_CHECKPOINT_1 -->
      [3] Frozen conversation summaries (Levels 1 & 2)
      <!-- CACHE_CHECKPOINT_2 -->
    MESSAGES:
      [4] Recent raw turns
      <!-- CACHE_CHECKPOINT_3 -->
      [5] Dynamic context & metadata
      [6] Current user question
      [7] Retrieved exemplars (if Rung 2)
    """

    SYSTEM_INSTRUCTIONS = (
        "You are Kifayat AI, a highly capable, versatile, empathetic, and intelligent AI assistant (like ChatGPT or Gemini).\n"
        "Your objective is to provide clear, insightful, accurate, and direct responses across all topics:\n"
        "- Conversational & Emotional: Respond warmly, empathetically, and naturally to greetings, personal questions, or emotional check-ins. Be human, supportive, and kind.\n"
        "- Programming & Technical: Provide clean, idiomatic, fully functional code blocks with clear explanations. Avoid verbose fluff.\n"
        "- Interactive Canvas: When asked to build interactive web apps, tools, or games, produce a complete, standalone, responsive HTML page with inline <style> and <script> ready to run in a browser sandbox.\n"
        "- Knowledge & Reasoning: Explain complex concepts simply and thoroughly. When addressing campus or academic queries, adhere strictly to institutional facts.\n"
        "- Languages: Seamlessly converse in English, Hinglish, Hindi, or any language the user initiates.\n"
        "- Persona: Helpful, intelligent, authentic, and direct. Never mention internal infrastructure details, routing rungs, repair ladders, caches, or prompt tokens in your conversations."
    )

    def __init__(self, handbook_path: Optional[str] = None):
        self.handbook_path = handbook_path or settings.HANDBOOK_PATH
        self._raw_handbook = self._load_handbook()
        self.canonical_handbook = Canonicalizer.canonicalize_text(self._raw_handbook)
        self.canonical_instructions = Canonicalizer.canonicalize_text(self.SYSTEM_INSTRUCTIONS)
        
        # Checkpoint 1 prefix (System instructions + Knowledge Base) is static and immutable
        self.checkpoint_1_text = (
            "[STABLE SYSTEM CONTEXT]\n"
            f"{self.canonical_instructions}\n\n"
            "[KIFAYAT AI KNOWLEDGE & CORE PRINCIPLES]\n"
            f"=== OPERATING GUIDELINES ===\n{self.canonical_handbook}\n<!-- CACHE_CHECKPOINT_1 -->"
        )
        self.lightweight_instructions = (
            "[STABLE SYSTEM CONTEXT]\n"
            f"{self.canonical_instructions}\n<!-- CACHE_CHECKPOINT_1 -->"
        )
        self.checkpoint_1_hash = Canonicalizer.compute_prefix_hash(self.checkpoint_1_text)

    def _load_handbook(self) -> str:
        if os.path.exists(self.handbook_path):
            with open(self.handbook_path, "r", encoding="utf-8") as f:
                return f.read()
        return "Kifayat AI General Knowledge Base."

    def _estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        # Standard token approximation: ~4 characters per token
        return max(1, int(len(text) / 3.8))

    def build_prompt(
        self,
        current_question: str,
        recent_raw_turns: Optional[List[Dict[str, str]]] = None,
        frozen_blocks: Optional[List[Dict[str, Any]]] = None,
        merged_blocks: Optional[List[Dict[str, Any]]] = None,
        exemplars: Optional[List[Dict[str, Any]]] = None,
        dynamic_context: Optional[str] = None,
        mode: str = "kifayat"
    ) -> Dict[str, Any]:
        """
        Builds the prompt according to the gateway mode and cache checkpoints.
        Returns:
            system_prompt: str
            messages: List[Dict[str, str]]
            prefix_hash: str
            checkpoint_markers: Dict[str, str]
            metadata: Dict[str, Any] (with estimated token breakdown)
        """
        recent_raw = recent_raw_turns or []
        frozen = frozen_blocks or []
        merged = merged_blocks or []
        ex_list = exemplars or []

        if mode == "baseline":
            # Baseline: Uncached raw history concatenation without frozen blocks or checkpoints
            # Simulates an unoptimized, bloated LLM prompt without prefix caching, without prompt squeezing, and with full history
            full_system = (
                "[UNOPTIMIZED BASELINE SYSTEM CONTEXT]\n"
                f"{self.SYSTEM_INSTRUCTIONS}\n\n"
                "[UNOPTIMIZED KNOWLEDGE BASE & DETAILED OPERATING GUIDELINES]\n"
                "You are an AI assistant operating without cache acceleration or prompt compression. "
                "You must analyze the entire conversation history and complete instructions before formulating a response. "
                "Provide direct, complete, accurate, and comprehensive assistance across all technical and general inquiries.\n\n"
                f"{self._raw_handbook}"
            )
            msgs = []
            for b in (merged + frozen):
                msgs.append({"role": "user", "content": f"Historical interaction: {b.get('summary', '')}"})
            for turn in recent_raw:
                if "user" in turn and "assistant" in turn:
                    msgs.append({"role": "user", "content": turn["user"]})
                    msgs.append({"role": "assistant", "content": turn["assistant"]})
                elif "content" in turn:
                    msgs.append({"role": turn.get("role", "user"), "content": turn["content"]})
            msgs.append({"role": "user", "content": f"[USER INQUIRY]\n{current_question}\nPlease provide a detailed and complete response."})
            return {
                "system": full_system,
                "messages": msgs,
                "prefix_hash": Canonicalizer.compute_prefix_hash(full_system),
                "checkpoint_markers": {},
                "metadata": {
                    "context_tokens_est": self._estimate_tokens(full_system),
                    "memory_tokens_est": 0,
                    "retrieval_tokens_est": 0,
                    "exemplar_tokens_est": 0,
                    "dynamic_tokens_est": self._estimate_tokens(current_question),
                    "is_estimated": True
                }
            }

        elif mode == "naive":
            # Naive: Rolling plain text summary without immutable block separation
            summary_text = "\n".join([f"Summary: {b.get('summary', '')}" for b in frozen + merged])
            full_system = f"[STABLE SYSTEM CONTEXT]\n{self.canonical_instructions}\n\n[KIFAYAT AI KNOWLEDGE & CORE PRINCIPLES]\n=== OPERATING GUIDELINES ===\n{self.canonical_handbook}\n\n[FROZEN MEMORY]\nContext:\n{summary_text}"
            msgs = []
            for turn in recent_raw:
                if "user" in turn and "assistant" in turn:
                    msgs.append({"role": "user", "content": turn["user"]})
                    msgs.append({"role": "assistant", "content": turn["assistant"]})
                elif "content" in turn:
                    msgs.append({"role": turn.get("role", "user"), "content": turn["content"]})
            msgs.append({"role": "user", "content": f"[CURRENT QUESTION]\n{current_question}"})
            return {
                "system": full_system,
                "messages": msgs,
                "prefix_hash": Canonicalizer.compute_prefix_hash(full_system),
                "checkpoint_markers": {},
                "metadata": {
                    "context_tokens_est": self._estimate_tokens(full_system),
                    "memory_tokens_est": self._estimate_tokens(summary_text),
                    "retrieval_tokens_est": 0,
                    "exemplar_tokens_est": 0,
                    "dynamic_tokens_est": self._estimate_tokens(current_question),
                    "is_estimated": True
                }
            }

        # Kifayat and Cache-Only Mode: Cache-aware structured prompt
        # Select appropriate checkpoint 1 prefix: only inject the full handbook if handbook/campus topics are relevant
        include_handbook = any(
            w in current_question.lower() for w in [
                "hostel", "fee", "fees", "mess", "attendance", "placement", "curfew", "scholarship",
                "admission", "campus", "college", "kit", "kifayat institute", "semester", "cgpa",
                "grade", "faculty", "exam", "course", "handbook"
            ]
        )
        c1_prefix = self.checkpoint_1_text if include_handbook else self.lightweight_instructions
        system_parts = [c1_prefix]

        # [3] Checkpoint 2: Frozen Conversation Summaries (Ordered deterministically)
        memory_str = ""
        if merged or frozen:
            memory_section = ["[FROZEN MEMORY]\n=== CONVERSATION MEMORY (FROZEN BLOCKS) ==="]
            for m in merged:
                memory_section.append(f"[Overview L{m.get('level', 1)}]: {m.get('summary', '')}")
            for b in frozen:
                memory_section.append(f"[Block #{b.get('block_id', 0)} (Turns {b.get('start_turn', 0)}-{b.get('end_turn', 0)})]: {b.get('summary', '')}")
            memory_section.append("<!-- CACHE_CHECKPOINT_2 -->")
            memory_str = "\n".join(memory_section)
            system_parts.append(memory_str)

        system_prompt = "\n\n".join(system_parts)
        checkpoint_2_hash = Canonicalizer.compute_prefix_hash(system_prompt)

        # [4] Recent raw turns
        messages = []
        for turn in recent_raw:
            if "user" in turn and "assistant" in turn:
                messages.append({"role": "user", "content": turn["user"]})
                messages.append({"role": "assistant", "content": turn["assistant"]})
            elif "content" in turn:
                messages.append({"role": turn.get("role", "user"), "content": turn["content"]})

        # [5] Dynamic context / Retrieved Context
        dynamic_prefix = ""
        if dynamic_context:
            dynamic_prefix += f"[RETRIEVED CONTEXT]\n[Session Context: {dynamic_context}]\n"

        # [6] Current Question + [7] Retrieved Exemplars (Positioned after stable history)
        final_user_content = dynamic_prefix
        exemplar_str = ""
        if ex_list:
            exemplar_str += "[EXAMPLES]\n=== REFERENCE EXAMPLES (EXEMPLARS) ===\n"
            for i, ex in enumerate(ex_list, 1):
                exemplar_str += f"Example {i}:\nQ: {ex.get('question', '')}\nA: {ex.get('answer', '')}\n\n"
            exemplar_str += "=== RELEVANT EXAMPLES ===\n"
            final_user_content += exemplar_str

        final_user_content += f"[USER INQUIRY]\n{current_question}"

        # Dynamic Token Squeezer (protects code, prunes redundant scaffolding & filler)
        squeezed_content, squeeze_stats = PromptSqueezer.compress_text(final_user_content)
        messages.append({"role": "user", "content": squeezed_content})

        token_metadata = {
            "context_tokens_est": self._estimate_tokens(self.checkpoint_1_text),
            "memory_tokens_est": self._estimate_tokens(memory_str),
            "retrieval_tokens_est": self._estimate_tokens(dynamic_context or ""),
            "exemplar_tokens_est": self._estimate_tokens(exemplar_str),
            "dynamic_tokens_est": self._estimate_tokens(current_question),
            "compression_saved_tokens": squeeze_stats["saved_tokens"],
            "compression_savings_pct": squeeze_stats["savings_pct"],
            "total_tokens_est": self._estimate_tokens(system_prompt) + sum(self._estimate_tokens(m["content"]) for m in messages),
            "is_estimated": True
        }

        return {
            "system": system_prompt,
            "messages": messages,
            "prefix_hash": checkpoint_2_hash,
            "checkpoint_markers": {
                "checkpoint_1_hash": self.checkpoint_1_hash,
                "checkpoint_2_hash": checkpoint_2_hash
            },
            "metadata": token_metadata
        }

    def build_conversational_prompt(
        self,
        current_question: str,
        recent_raw_turns: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Lightweight conversational prompt without handbook or frozen-block injection.
        Used exclusively for Path A (greetings, pleasantries, small talk, gratitude).
        """
        system_prompt = (
            "You are Kifayat AI, a helpful, polite, empathetic, and intelligent AI assistant.\n"
            "Respond naturally, warmly, and concisely to greetings, emotional check-ins, and conversational remarks.\n"
            "Never output robotic gateway explanations or technical diagnostics in casual conversation.\n"
            "Support English and Hinglish seamlessly. Be direct, genuinely supportive, and friendly."
        )
        messages = []
        recent_raw = recent_raw_turns or []
        for turn in recent_raw[-4:]:
            if "user" in turn and "assistant" in turn:
                messages.append({"role": "user", "content": turn["user"]})
                messages.append({"role": "assistant", "content": turn["assistant"]})
            elif "content" in turn:
                messages.append({"role": turn.get("role", "user"), "content": turn["content"]})

        messages.append({"role": "user", "content": current_question})

        prefix_hash = Canonicalizer.compute_prefix_hash(system_prompt)
        token_metadata = {
            "context_tokens_est": self._estimate_tokens(system_prompt),
            "memory_tokens_est": sum(self._estimate_tokens(m["content"]) for m in messages[:-1]),
            "retrieval_tokens_est": 0,
            "exemplar_tokens_est": 0,
            "dynamic_tokens_est": self._estimate_tokens(current_question),
            "compression_saved_tokens": 0,
            "compression_savings_pct": 0.0,
            "total_tokens_est": self._estimate_tokens(system_prompt) + sum(self._estimate_tokens(m["content"]) for m in messages),
            "is_estimated": True
        }
        return {
            "system": system_prompt,
            "messages": messages,
            "prefix_hash": prefix_hash,
            "checkpoint_markers": {"conversational_hash": prefix_hash},
            "metadata": token_metadata
        }

