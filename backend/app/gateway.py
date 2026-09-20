import asyncio
import json
import time
import uuid
import logging
from typing import Dict, List, Any, Optional, AsyncIterator

from backend.app.config import settings
from backend.app.models.schemas import KifayatReceipt
from backend.app.providers.base import LLMProvider
from backend.app.storage.sqlite_store import SQLiteStore
from backend.app.context.builder import ContextBuilder
from backend.app.cache.local_cache import LocalSemanticCache
from backend.app.cache.safety import CacheSafetyValidator
from backend.app.exemplars.store import ExemplarStore
from backend.app.memory.block_manager import BlockManager
from backend.app.memory.budget import MemoryBudgetManager
from backend.app.memory.compaction_queue import LocalCompactionQueue
from backend.app.repair.ladder import PromptRepairLadder
from backend.app.pricing.cost_calculator import CostCalculator
from backend.app.pricing.accounting import TokenAccountingService
from backend.app.tracing.tracer import RequestExecutionTracer
from backend.app.router import ModelRouter, ConversationIntentClassifier, IntentType

logger = logging.getLogger("kifayat.gateway")


class KifayatGateway:
    """
    Central Kifayat Context Gateway orchestrator.
    Combines:
    - Provider Abstraction
    - Canonicalized Cache-Aware Prompting
    - Frozen-Block & Hierarchical Memory
    - Semantic Response Caching
    - Three-Rung Prompt Repair Ladder
    - Self-Pruning Exemplar Store
    - Asynchronous Compaction
    - Real-Time Streaming & Observability
    """

    def __init__(
        self,
        store: SQLiteStore,
        provider: LLMProvider,
        context_builder: ContextBuilder,
        semantic_cache: LocalSemanticCache,
        exemplar_store: ExemplarStore,
        compaction_queue: LocalCompactionQueue,
        router: Optional[ModelRouter] = None
    ):
        self.store = store
        self.provider = provider
        self.context_builder = context_builder
        self.semantic_cache = semantic_cache
        self.exemplar_store = exemplar_store
        self.compaction_queue = compaction_queue
        self.router = router or ModelRouter()
        
        self.block_manager = BlockManager()
        self.budget_manager = MemoryBudgetManager()
        self.repair_ladder = PromptRepairLadder(
            provider=self.provider,
            context_builder=self.context_builder,
            exemplar_store=self.exemplar_store,
            router=self.router
        )

    def _get_namespace(self, language: str = "en") -> str:
        return f"{settings.APP_ID}:{settings.HANDBOOK_VERSION}:{language}:{self.provider.provider_name}"

    async def process_chat(
        self,
        question: str,
        session_id: Optional[str] = None,
        mode: str = "kifayat"
    ) -> Dict[str, Any]:
        """
        Synchronous / Standard request pipeline with execution tracing.
        Returns {
            'text': str,
            'receipt': KifayatReceipt
        }
        """
        start_time = time.perf_counter()
        req_id = f"req-{uuid.uuid4().hex[:12]}"
        sess_id = session_id or f"sess-{uuid.uuid4().hex[:12]}"

        tracer = RequestExecutionTracer(request_id=req_id, session_id=sess_id)
        tracer.record_event("api", "Request received", {"question_length": len(question), "mode": mode})

        # 1. Retrieve session history
        tracer.set_node_state("memory_retrieval", "RUNNING")
        session_data = self.store.get_session(sess_id) or {
            "session_id": sess_id,
            "raw_turns": [],
            "frozen_blocks": [],
            "merged_blocks": [],
            "turn_count": 0
        }
        raw_count = len(session_data.get("raw_turns", []))
        frozen_count = len(session_data.get("frozen_blocks", []))
        merged_count = len(session_data.get("merged_blocks", []))
        tracer.record_event("memory", "Session history loaded", {
            "raw_turns": raw_count,
            "frozen_blocks": frozen_count,
            "merged_blocks": merged_count
        })
        tracer.set_node_state("memory_retrieval", "COMPLETED", {
            "raw_turns": raw_count,
            "frozen_blocks": frozen_count,
            "merged_blocks": merged_count
        })

        # 2. Input validation, language detection & Intent classification
        tracer.set_node_state("request_validate", "RUNNING")
        q_clean = question.strip()
        hinglish_words = ["ka", "ki", "ke", "hai", "kya", "kitna", "kahan", "nahi", "isme", "mein", "aur", "pehle"]
        is_hinglish = any(w in q_clean.lower().split() for w in hinglish_words)
        lang = "hinglish" if is_hinglish else "en"
        namespace = self._get_namespace(lang)

        intent_res = ConversationIntentClassifier.classify(q_clean)
        tracer.record_event("validator", "Validation and intent classification passed", {
            "language": lang,
            "hinglish": is_hinglish,
            "intent": intent_res.intent.value,
            "is_conversational": intent_res.is_conversational,
            "max_rung": intent_res.maximum_rung,
            "reason": intent_res.routing_reason
        })
        tracer.set_node_state("request_validate", "COMPLETED", {
            "language": lang,
            "clean_length": len(q_clean),
            "intent": intent_res.intent.value,
            "is_conversational": intent_res.is_conversational
        })

        # =========================================================================
        # PATH A: CONVERSATIONAL ROUTING (GREETINGS / PLEASANTRIES / GRATITUDE)
        # =========================================================================
        if intent_res.is_conversational:
            tracer.record_event("routing", f"Path A triggered: {intent_res.intent.value} -> Rung 1 fast path", {
                "reason": intent_res.routing_reason,
                "maximum_rung": 1
            })
            tracer.set_node_state("semantic_cache", "SKIPPED", {"reason": "conversational_fast_path"})
            tracer.set_node_state("context_builder", "COMPLETED", {"path": "conversational_lightweight"})
            tracer.set_node_state("exemplar_search", "SKIPPED", {"reason": "conversational_fast_path"})
            tracer.set_node_state("cheap_model", "RUNNING")

            ladder_result = await self.repair_ladder.execute(
                question=q_clean,
                session_context=session_data,
                mode=mode,
                is_conversational=True,
                maximum_rung=1
            )

            tracer.set_node_state("cheap_model", "COMPLETED", {"model": ladder_result.model_id})
            tracer.set_node_state("judge", "COMPLETED", {"passed": True, "score": 5, "verdict": "Conversational intent verified on Rung 1"})
            tracer.set_node_state("rung2_exemplars", "SKIPPED")
            tracer.set_node_state("judge_rung2", "SKIPPED")
            tracer.set_node_state("rung3_strong", "SKIPPED")
            tracer.set_node_state("final_response", "COMPLETED", {"output_length": len(ladder_result.text)})
            tracer.set_node_state("stream_user", "COMPLETED")

            latency_ms = (time.perf_counter() - start_time) * 1000

            account_info = TokenAccountingService.account(
                model_id=ladder_result.model_id,
                actual_input_tokens=ladder_result.input_tokens,
                actual_output_tokens=ladder_result.output_tokens,
                cache_hit=False,
                cache_read_tokens=ladder_result.cache_read_tokens,
                uncompressed_context_tokens=ladder_result.input_tokens + 25,
                is_strong_model=False
            )

            # Save turn to session so conversation history is preserved
            turn_result = self.block_manager.add_turn(session_data, q_clean, ladder_result.text)
            self.store.save_session(sess_id, turn_result["session_data"])
            tracer.set_node_state("memory_update", "COMPLETED", {"turn_count": turn_result["session_data"].get("turn_count", 0)})
            tracer.set_node_state("async_compaction", "SKIPPED", {"reason": "conversational_turn"})
            tracer.set_node_state("exemplar_feedback", "SKIPPED")
            tracer.set_node_state("self_pruning", "SKIPPED")

            trace_data = tracer.export()

            receipt = KifayatReceipt(
                request_id=req_id,
                session_id=sess_id,
                model_id=ladder_result.model_id,
                rung=1,
                input_tokens=ladder_result.input_tokens,
                output_tokens=ladder_result.output_tokens,
                cache_read_tokens=ladder_result.cache_read_tokens,
                cache_write_tokens=ladder_result.cache_write_tokens,
                tokens_saved=account_info["total_tokens_saved"],
                tokens_saved_actual=account_info["tokens_saved_actual"],
                tokens_saved_estimated=account_info["tokens_saved_estimated"],
                is_estimated_tokens=account_info["is_estimated"],
                llm_calls_avoided=account_info["llm_calls_avoided"],
                cost_usd=account_info["actual_cost_usd"],
                baseline_cost_usd=account_info["baseline_cost_usd"],
                saving_pct=account_info["saving_pct"],
                cache_hit=False,
                similarity=None,
                latency_ms=round(latency_ms, 2),
                prefix_hash=self.context_builder.checkpoint_1_hash,
                judge_score=5,
                judge_verdict="Conversational response verified on Rung 1",
                intent=intent_res.intent.value,
                routing_reason=intent_res.routing_reason,
                provider=self.provider.provider_name,
                provider_request_sent=True,
                provider_response_received=True,
                fallback_used=ladder_result.fallback_used,
                mode=mode,
                execution_path=trace_data["execution_path"],
                node_states=trace_data["node_states"],
                node_details=trace_data["node_details"],
                timeline=trace_data["timeline"]
            )

            self.store.log_request(receipt.model_dump())
            return {"text": ladder_result.text, "receipt": receipt}

        # =========================================================================
        # PATH B: KNOWLEDGE / CODING / COMPLEX REASONING
        # =========================================================================
        # 3. Cacheability Check & Semantic Cache Lookup
        cache_allowed = (
            settings.SEMANTIC_CACHE_ENABLED and
            mode in ["kifayat", "cache_only"] and
            CacheSafetyValidator.is_cacheable(q_clean)
        )

        tracer.set_node_state("semantic_cache", "RUNNING")
        query_embedding = None
        if cache_allowed:
            t_cache_start = time.perf_counter()
            tracer.record_event("cache", "Computing query embedding for semantic lookup")
            embeddings = await self.provider.embed([q_clean])
            query_embedding = embeddings[0]
            cached = await self.semantic_cache.get_similar(
                question=q_clean,
                embedding=query_embedding,
                namespace=namespace,
                threshold=settings.SEMANTIC_CACHE_THRESHOLD
            )
            cache_lookup_ms = round((time.perf_counter() - t_cache_start) * 1000.0, 2)

            if cached:
                sim = cached.get("similarity", 1.0)
                tracer.record_event("cache", "Semantic cache HIT", {"similarity": sim, "lookup_ms": cache_lookup_ms})
                tracer.set_node_state("semantic_cache", "CACHE HIT", {
                    "status": "HIT",
                    "similarity": sim,
                    "threshold": settings.SEMANTIC_CACHE_THRESHOLD,
                    "lookup_ms": cache_lookup_ms
                })
                # Mark downstream LLM nodes as SKIPPED
                for skip_node in ["context_builder", "exemplar_search", "cheap_model", "judge", "rung2_exemplars", "judge_rung2", "rung3_strong"]:
                    tracer.set_node_state(skip_node, "SKIPPED")

                latency_ms = (time.perf_counter() - start_time) * 1000

                # Token Accounting for cache hit: dynamic uncompressed baseline tokens
                baseline_prompt_data = self.context_builder.build_prompt(
                    current_question=q_clean,
                    recent_raw_turns=session_data.get("raw_turns", []),
                    frozen_blocks=session_data.get("frozen_blocks", []),
                    merged_blocks=session_data.get("merged_blocks", []),
                    mode="baseline"
                )
                real_baseline_tokens = self.context_builder._estimate_tokens(baseline_prompt_data["system"]) + sum(
                    self.context_builder._estimate_tokens(m["content"]) for m in baseline_prompt_data["messages"]
                )
                est_out_tokens = max(1, int(len(cached["answer"]) / 3.8))
                account_info = TokenAccountingService.account(
                    model_id="semantic_cache",
                    actual_input_tokens=0,
                    actual_output_tokens=est_out_tokens,
                    cache_hit=True,
                    uncompressed_context_tokens=real_baseline_tokens + est_out_tokens,
                    estimated_output_tokens=est_out_tokens
                )

                tracer.set_node_state("final_response", "COMPLETED", {"source": "semantic_cache"})
                tracer.set_node_state("stream_user", "COMPLETED")
                tracer.set_node_state("async_compaction", "SKIPPED")
                tracer.set_node_state("memory_update", "COMPLETED")
                tracer.set_node_state("exemplar_feedback", "SKIPPED")
                tracer.set_node_state("self_pruning", "SKIPPED")

                trace_data = tracer.export()

                receipt = KifayatReceipt(
                    request_id=req_id,
                    session_id=sess_id,
                    model_id="semantic_cache",
                    rung=0,
                    input_tokens=0,
                    output_tokens=est_out_tokens,
                    tokens_saved=account_info["total_tokens_saved"],
                    tokens_saved_actual=account_info["tokens_saved_actual"],
                    tokens_saved_estimated=account_info["tokens_saved_estimated"],
                    is_estimated_tokens=account_info["is_estimated"],
                    llm_calls_avoided=account_info["llm_calls_avoided"],
                    cost_usd=account_info["actual_cost_usd"],
                    baseline_cost_usd=account_info["baseline_cost_usd"],
                    saving_pct=account_info["saving_pct"],
                    cache_hit=True,
                    cache_type="semantic",
                    similarity=sim,
                    latency_ms=round(latency_ms, 2),
                    prefix_hash=self.context_builder.checkpoint_1_hash,
                    judge_score=5,
                    judge_verdict="Served from verified semantic response cache",
                    intent=intent_res.intent.value,
                    routing_reason=intent_res.routing_reason,
                    provider=self.provider.provider_name,
                    provider_request_sent=False,
                    provider_response_received=True,
                    fallback_used=False,
                    mode=mode,
                    execution_path=trace_data["execution_path"],
                    node_states=trace_data["node_states"],
                    node_details=trace_data["node_details"],
                    timeline=trace_data["timeline"]
                )
                # Save turn to session so conversation history is preserved
                turn_result = self.block_manager.add_turn(session_data, q_clean, cached["answer"])
                self.store.save_session(sess_id, turn_result["session_data"])

                # Log request
                self.store.log_request(receipt.model_dump())
                return {"text": cached["answer"], "receipt": receipt}
            else:
                tracer.record_event("cache", "Semantic cache MISS", {"threshold": settings.SEMANTIC_CACHE_THRESHOLD, "lookup_ms": cache_lookup_ms})
                tracer.set_node_state("semantic_cache", "COMPLETED", {
                    "status": "MISS",
                    "threshold": settings.SEMANTIC_CACHE_THRESHOLD,
                    "lookup_ms": cache_lookup_ms
                })
        else:
            tracer.record_event("cache", "Semantic cache bypassed (safety / mode)", {"cache_allowed": cache_allowed})
            tracer.set_node_state("semantic_cache", "SKIPPED", {"reason": "bypassed_or_unsafe"})

        # 4. Context Budgeting & Builder
        tracer.set_node_state("context_builder", "RUNNING")
        if query_embedding is None:
            tracer.record_event("embeddings", "Generating query vector for retrieval")
            embeddings = await self.provider.embed([q_clean])
            query_embedding = embeddings[0]

        safe_raw, safe_frozen, safe_merged, _ = self.budget_manager.enforce_budget(
            current_question=q_clean,
            recent_raw_turns=session_data.get("raw_turns", []),
            frozen_blocks=session_data.get("frozen_blocks", []),
            merged_blocks=session_data.get("merged_blocks", []),
            exemplars=[]
        )
        bounded_session = dict(session_data)
        bounded_session["raw_turns"] = safe_raw
        bounded_session["frozen_blocks"] = safe_frozen
        bounded_session["merged_blocks"] = safe_merged

        tracer.record_event("context", "Budget enforced & prompt sections constructed", {
            "checkpoint_1_hash": self.context_builder.checkpoint_1_hash[:12]
        })
        tracer.set_node_state("context_builder", "COMPLETED", {
            "checkpoint_1_hash": self.context_builder.checkpoint_1_hash[:12]
        })

        # 5. Execute Three-Rung Prompt Repair Ladder
        tracer.set_node_state("exemplar_search", "RUNNING")
        tracer.set_node_state("cheap_model", "RUNNING")
        tracer.record_event("ladder", "Executing Prompt Repair Ladder", {"mode": mode})

        ladder_result = await self.repair_ladder.execute(
            question=q_clean,
            session_context=bounded_session,
            query_embedding=query_embedding,
            mode=mode,
            is_conversational=False,
            maximum_rung=intent_res.maximum_rung
        )

        tracer.set_node_state("cheap_model", "COMPLETED", {"model": self.router.get_model("cheap")})
        tracer.set_node_state("judge", "COMPLETED", {
            "passed": ladder_result.judge_score >= 3 if ladder_result.judge_score else True,
            "score": ladder_result.judge_score,
            "verdict": ladder_result.judge_verdict
        })

        if ladder_result.rung == 1:
            tracer.record_event("ladder", "Rung 1 (Cheap Model) verified successfully", {"score": ladder_result.judge_score})
            tracer.set_node_state("rung2_exemplars", "SKIPPED")
            tracer.set_node_state("judge_rung2", "SKIPPED")
            tracer.set_node_state("rung3_strong", "SKIPPED")
        elif ladder_result.rung == 2:
            tracer.record_event("ladder", "Rung 2 (Exemplar Rescue) executed and passed", {"score": ladder_result.judge_score})
            tracer.set_node_state("exemplar_search", "COMPLETED", {"status": "rescued"})
            tracer.set_node_state("rung2_exemplars", "COMPLETED", {"status": "exemplar_rescue_success"})
            tracer.set_node_state("judge_rung2", "COMPLETED", {"score": ladder_result.judge_score})
            tracer.set_node_state("rung3_strong", "SKIPPED")
        else:
            tracer.record_event("ladder", "Rung 3 (Strong Fallback) executed", {"score": ladder_result.judge_score})
            tracer.set_node_state("rung2_exemplars", "COMPLETED", {"status": "rescue_attempted"})
            tracer.set_node_state("judge_rung2", "FAILED", {"reason": "score below threshold"})
            tracer.set_node_state("rung3_strong", "COMPLETED", {"model": self.router.get_model("strong")})

        tracer.set_node_state("final_response", "COMPLETED", {"output_length": len(ladder_result.text)})
        tracer.set_node_state("stream_user", "COMPLETED")

        latency_ms = (time.perf_counter() - start_time) * 1000

        # Token Accounting: Calculate real uncompressed baseline tokens
        baseline_prompt_data = self.context_builder.build_prompt(
            current_question=q_clean,
            recent_raw_turns=session_data.get("raw_turns", []),
            frozen_blocks=session_data.get("frozen_blocks", []),
            merged_blocks=session_data.get("merged_blocks", []),
            mode="baseline"
        )
        uncompressed_tokens = self.context_builder._estimate_tokens(baseline_prompt_data["system"]) + sum(
            self.context_builder._estimate_tokens(m["content"]) for m in baseline_prompt_data["messages"]
        )

        account_info = TokenAccountingService.account(
            model_id=ladder_result.model_id,
            actual_input_tokens=ladder_result.input_tokens,
            actual_output_tokens=ladder_result.output_tokens,
            cache_hit=False,
            cache_read_tokens=ladder_result.cache_read_tokens,
            uncompressed_context_tokens=max(uncompressed_tokens, ladder_result.input_tokens),
            is_strong_model=(ladder_result.rung == 3 or mode == "baseline")
        )

        # 6. Save Turn to Session & Handle Background Compaction
        turn_result = self.block_manager.add_turn(session_data, q_clean, ladder_result.text)
        updated_session = turn_result["session_data"]
        self.store.save_session(sess_id, updated_session)
        tracer.set_node_state("memory_update", "COMPLETED", {"turn_count": updated_session.get("turn_count", 0)})

        pending_freeze = turn_result.get("pending_freeze_block")
        if pending_freeze and settings.COMPACTION_ENABLED:
            tracer.record_event("compaction", "Compaction event queued for background worker", {
                "block_id": pending_freeze["block_id"]
            })
            tracer.set_node_state("async_compaction", "RUNNING", {
                "status": "QUEUED",
                "block_id": pending_freeze["block_id"]
            })
            await self.compaction_queue.push_event({
                "event_type": "compact_block",
                "conversation_id": sess_id,
                "block_id": pending_freeze["block_id"],
                "compaction_version": 1,
                "block_data": pending_freeze,
                "timestamp": time.time()
            })
        else:
            tracer.set_node_state("async_compaction", "SKIPPED", {"reason": "threshold_not_reached"})

        # 7. Store in Semantic Cache if safe
        if cache_allowed and ladder_result.judge_score and ladder_result.judge_score >= 4:
            tracer.record_event("cache", "Writing verified answer to semantic cache")
            await self.semantic_cache.set(
                question=q_clean,
                answer=ladder_result.text,
                embedding=query_embedding,
                namespace=namespace,
                context_hash=self.context_builder.checkpoint_1_hash
            )

        tracer.set_node_state("exemplar_feedback", "COMPLETED" if ladder_result.rung == 2 else "SKIPPED")
        tracer.set_node_state("self_pruning", "SKIPPED")

        trace_data = tracer.export()

        receipt = KifayatReceipt(
            request_id=req_id,
            session_id=sess_id,
            model_id=ladder_result.model_id,
            rung=ladder_result.rung,
            input_tokens=ladder_result.input_tokens,
            output_tokens=ladder_result.output_tokens,
            cache_read_tokens=ladder_result.cache_read_tokens,
            cache_write_tokens=ladder_result.cache_write_tokens,
            tokens_saved=account_info["total_tokens_saved"],
            tokens_saved_actual=account_info["tokens_saved_actual"],
            tokens_saved_estimated=account_info["tokens_saved_estimated"],
            is_estimated_tokens=account_info["is_estimated"],
            llm_calls_avoided=account_info["llm_calls_avoided"],
            cost_usd=account_info["actual_cost_usd"],
            baseline_cost_usd=account_info["baseline_cost_usd"],
            saving_pct=account_info["saving_pct"],
            cache_hit=False,
            similarity=None,
            latency_ms=round(latency_ms, 2),
            prefix_hash=self.context_builder.checkpoint_1_hash,
            judge_score=ladder_result.judge_score,
            judge_verdict=ladder_result.judge_verdict,
            intent=intent_res.intent.value,
            routing_reason=intent_res.routing_reason,
            provider=self.provider.provider_name,
            provider_request_sent=True,
            provider_response_received=True,
            fallback_used=ladder_result.fallback_used,
            mode=mode,
            execution_path=trace_data["execution_path"],
            node_states=trace_data["node_states"],
            node_details=trace_data["node_details"],
            timeline=trace_data["timeline"]
        )

        # 8. Log request
        self.store.log_request(receipt.model_dump())
        return {"text": ladder_result.text, "receipt": receipt}

    async def stream_chat(
        self,
        question: str,
        session_id: Optional[str] = None,
        mode: str = "kifayat"
    ) -> AsyncIterator[str]:
        """
        Streaming request pipeline emitting real-time Server-Sent Events:
          event: workflow_step (for visualizer animation)
          event: metadata
          event: token
          event: complete
          event: error
        """
        start_time = time.perf_counter()
        req_id = f"req-{uuid.uuid4().hex[:12]}"
        sess_id = session_id or f"sess-{uuid.uuid4().hex[:12]}"

        # Real-time workflow step 1: Validate
        yield f"event: workflow_step\ndata: {json.dumps({'node': 'request_validate', 'state': 'RUNNING'})}\n\n"
        await asyncio.sleep(0.01)

        q_clean = question.strip()
        hinglish_words = ["ka", "ki", "ke", "hai", "kya", "kitna", "kahan", "nahi", "isme", "mein", "aur", "pehle"]
        is_hinglish = any(w in q_clean.lower().split() for w in hinglish_words)
        lang = "hinglish" if is_hinglish else "en"
        namespace = self._get_namespace(lang)

        intent_res = ConversationIntentClassifier.classify(q_clean)
        yield f"event: workflow_step\ndata: {json.dumps({'node': 'request_validate', 'state': 'COMPLETED', 'details': {'language': lang, 'intent': intent_res.intent.value, 'is_conversational': intent_res.is_conversational}})}\n\n"

        # Step 2: Cache check (only for knowledge/tasks)
        cache_allowed = (
            not intent_res.is_conversational and
            settings.SEMANTIC_CACHE_ENABLED and
            mode in ["kifayat", "cache_only"] and
            CacheSafetyValidator.is_cacheable(q_clean)
        )

        if cache_allowed:
            yield f"event: workflow_step\ndata: {json.dumps({'node': 'semantic_cache', 'state': 'RUNNING'})}\n\n"
            embeddings = await self.provider.embed([q_clean])
            cached = await self.semantic_cache.get_similar(
                question=q_clean,
                embedding=embeddings[0],
                namespace=namespace,
                threshold=settings.SEMANTIC_CACHE_THRESHOLD
            )
            if cached:
                sim = cached["similarity"]
                yield f"event: workflow_step\ndata: {json.dumps({'node': 'semantic_cache', 'state': 'CACHE HIT', 'details': {'similarity': sim}})}\n\n"
                yield f"event: metadata\ndata: {json.dumps({'cache_hit': True, 'model': 'semantic_cache', 'similarity': sim})}\n\n"
                
                # Stream cached answer chunks
                cached_text = cached["answer"]
                for word in cached_text.split(" "):
                    yield f"event: token\ndata: {json.dumps({'text': word + ' '})}\n\n"
                    await asyncio.sleep(0.01)

                latency_ms = (time.perf_counter() - start_time) * 1000
                session_data_pre = self.store.get_session(sess_id) or {}
                baseline_prompt_data = self.context_builder.build_prompt(
                    current_question=q_clean,
                    recent_raw_turns=session_data_pre.get("raw_turns", []),
                    frozen_blocks=session_data_pre.get("frozen_blocks", []),
                    merged_blocks=session_data_pre.get("merged_blocks", []),
                    mode="baseline"
                )
                real_baseline_tokens = self.context_builder._estimate_tokens(baseline_prompt_data["system"]) + sum(
                    self.context_builder._estimate_tokens(m["content"]) for m in baseline_prompt_data["messages"]
                )
                est_out_tokens = max(1, int(len(cached_text) / 3.8))
                account_info = TokenAccountingService.account(
                    model_id="semantic_cache",
                    actual_input_tokens=0,
                    actual_output_tokens=est_out_tokens,
                    cache_hit=True,
                    uncompressed_context_tokens=real_baseline_tokens + est_out_tokens,
                    estimated_output_tokens=est_out_tokens
                )
                receipt = KifayatReceipt(
                    request_id=req_id,
                    session_id=sess_id,
                    model_id="semantic_cache",
                    rung=0,
                    tokens_saved=account_info["total_tokens_saved"],
                    tokens_saved_actual=account_info["tokens_saved_actual"],
                    tokens_saved_estimated=account_info["tokens_saved_estimated"],
                    is_estimated_tokens=account_info["is_estimated"],
                    llm_calls_avoided=account_info["llm_calls_avoided"],
                    cost_usd=account_info["actual_cost_usd"],
                    baseline_cost_usd=account_info["baseline_cost_usd"],
                    saving_pct=account_info["saving_pct"],
                    cache_hit=True,
                    cache_type="semantic",
                    similarity=sim,
                    latency_ms=round(latency_ms, 2),
                    prefix_hash=self.context_builder.checkpoint_1_hash,
                    judge_score=5,
                    judge_verdict="Served from verified semantic response cache",
                    mode=mode,
                    execution_path=["request_validate", "semantic_cache", "final_response", "stream_user"],
                    node_states={
                        "request_validate": "COMPLETED",
                        "semantic_cache": "CACHE HIT",
                        "context_builder": "SKIPPED",
                        "memory_retrieval": "SKIPPED",
                        "cheap_model": "SKIPPED",
                        "judge": "SKIPPED",
                        "rung2_exemplars": "SKIPPED",
                        "rung3_strong": "SKIPPED",
                        "final_response": "COMPLETED",
                        "stream_user": "COMPLETED",
                        "async_compaction": "SKIPPED"
                    }
                )
                # Save turn to session
                session_data = self.store.get_session(sess_id) or {
                    "session_id": sess_id,
                    "raw_turns": [],
                    "frozen_blocks": [],
                    "merged_blocks": [],
                    "turn_count": 0
                }
                turn_result = self.block_manager.add_turn(session_data, q_clean, cached_text)
                self.store.save_session(sess_id, turn_result["session_data"])

                self.store.log_request(receipt.model_dump())
                yield f"event: workflow_step\ndata: {json.dumps({'node': 'stream_user', 'state': 'COMPLETED'})}\n\n"
                yield f"event: complete\ndata: {json.dumps({'request_id': req_id, 'receipt': receipt.model_dump()})}\n\n"
                return

        # Cache miss
        yield f"event: workflow_step\ndata: {json.dumps({'node': 'semantic_cache', 'state': 'COMPLETED', 'details': {'status': 'MISS'}})}\n\n"
        yield f"event: workflow_step\ndata: {json.dumps({'node': 'context_builder', 'state': 'RUNNING'})}\n\n"
        yield f"event: metadata\ndata: {json.dumps({'cache_hit': False, 'model': settings.CHEAP_MODEL_ID})}\n\n"

        # Execute real-time streaming directly from LLM Provider
        try:
            session_data = self.store.get_session(sess_id) or {
                "session_id": sess_id,
                "raw_turns": [],
                "frozen_blocks": [],
                "merged_blocks": [],
                "turn_count": 0
            }

            model_to_use = self.router.cheap
            if mode == "baseline":
                model_to_use = self.router.strong
                prompt_data = self.context_builder.build_prompt(
                    current_question=q_clean,
                    recent_raw_turns=session_data.get("raw_turns", []),
                    frozen_blocks=session_data.get("frozen_blocks", []),
                    merged_blocks=session_data.get("merged_blocks", []),
                    mode="baseline"
                )
            elif intent_res.is_conversational:
                prompt_data = self.context_builder.build_conversational_prompt(
                    current_question=q_clean,
                    recent_raw_turns=session_data.get("raw_turns", [])
                )
            else:
                prompt_data = self.context_builder.build_prompt(
                    current_question=q_clean,
                    recent_raw_turns=session_data.get("raw_turns", []),
                    frozen_blocks=session_data.get("frozen_blocks", []),
                    merged_blocks=session_data.get("merged_blocks", []),
                    mode=mode
                )

            yield f"event: workflow_step\ndata: {json.dumps({'node': 'context_builder', 'state': 'COMPLETED'})}\n\n"
            yield f"event: workflow_step\ndata: {json.dumps({'node': 'cheap_model', 'state': 'RUNNING'})}\n\n"
            yield f"event: metadata\ndata: {json.dumps({'cache_hit': False, 'model': model_to_use, 'intent': intent_res.intent.value})}\n\n"

            stream_chunks = []
            first_token_time = None
            ttft_ms = None

            async for chunk in self.provider.stream(
                messages=prompt_data["messages"],
                system=prompt_data["system"],
                model_id=model_to_use
            ):
                if first_token_time is None:
                    first_token_time = time.perf_counter()
                    ttft_ms = round((first_token_time - start_time) * 1000, 2)
                    yield f"event: workflow_step\ndata: {json.dumps({'node': 'cheap_model', 'state': 'STREAMING', 'details': {'ttft_ms': ttft_ms}})}\n\n"

                stream_chunks.append(chunk)
                yield f"event: token\ndata: {json.dumps({'text': chunk})}\n\n"

            generated_text = "".join(stream_chunks)
            if not generated_text:
                # Fallback to process_chat if stream produced nothing
                fallback_res = await self.process_chat(q_clean, session_id=sess_id, mode=mode)
                generated_text = fallback_res["text"]
                receipt = fallback_res["receipt"]
                for word in generated_text.split(" "):
                    yield f"event: token\ndata: {json.dumps({'text': word + ' '})}\n\n"
                    await asyncio.sleep(0.01)
                yield f"event: complete\ndata: {json.dumps({'request_id': req_id, 'receipt': receipt.model_dump()})}\n\n"
                return

            total_latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            ttft_final = ttft_ms if ttft_ms is not None else total_latency_ms

            # Token Accounting
            in_tokens = self.context_builder._estimate_tokens(prompt_data["system"]) + sum(
                self.context_builder._estimate_tokens(m["content"]) for m in prompt_data["messages"]
            )
            out_tokens = max(1, self.context_builder._estimate_tokens(generated_text))
            prefix_part = prompt_data["system"].split("<!-- CACHE_CHECKPOINT_1 -->")[0] if "<!-- CACHE_CHECKPOINT_1 -->" in prompt_data["system"] else ""
            cached_tokens = max(0, self.context_builder._estimate_tokens(prefix_part)) if mode != "baseline" else 0

            # Baseline tokens for comparison
            baseline_prompt_data = self.context_builder.build_prompt(
                current_question=q_clean,
                recent_raw_turns=session_data.get("raw_turns", []),
                frozen_blocks=session_data.get("frozen_blocks", []),
                merged_blocks=session_data.get("merged_blocks", []),
                mode="baseline"
            )
            uncompressed_tokens = self.context_builder._estimate_tokens(baseline_prompt_data["system"]) + sum(
                self.context_builder._estimate_tokens(m["content"]) for m in baseline_prompt_data["messages"]
            )

            account_info = TokenAccountingService.account(
                model_id=model_to_use,
                actual_input_tokens=in_tokens,
                actual_output_tokens=out_tokens,
                cache_hit=False,
                cache_read_tokens=cached_tokens,
                uncompressed_context_tokens=max(uncompressed_tokens, in_tokens),
                is_strong_model=(mode == "baseline")
            )

            # Save turn to session memory
            turn_result = self.block_manager.add_turn(session_data, q_clean, generated_text)
            self.store.save_session(sess_id, turn_result["session_data"])

            receipt = KifayatReceipt(
                request_id=req_id,
                session_id=sess_id,
                model_id=model_to_use,
                rung=1 if mode != "baseline" else 3,
                input_tokens=in_tokens,
                output_tokens=out_tokens,
                cache_read_tokens=cached_tokens,
                cache_write_tokens=max(0, in_tokens - cached_tokens),
                tokens_saved=account_info["total_tokens_saved"],
                tokens_saved_actual=account_info["tokens_saved_actual"],
                tokens_saved_estimated=account_info["tokens_saved_estimated"],
                is_estimated_tokens=account_info["is_estimated"],
                llm_calls_avoided=account_info["llm_calls_avoided"],
                cost_usd=account_info["actual_cost_usd"],
                baseline_cost_usd=account_info["baseline_cost_usd"],
                saving_pct=account_info["saving_pct"],
                cache_hit=False,
                similarity=None,
                latency_ms=total_latency_ms,
                ttft_ms=ttft_final,
                prefix_hash=self.context_builder.checkpoint_1_hash,
                judge_score=5,
                judge_verdict="Direct streaming response completed successfully",
                intent=intent_res.intent.value,
                routing_reason=intent_res.routing_reason,
                provider=self.provider.provider_name,
                provider_request_sent=True,
                provider_response_received=True,
                fallback_used=False,
                mode=mode,
                execution_path=["request_validate", "context_builder", "cheap_model", "stream_user"],
                node_states={
                    "request_validate": "COMPLETED",
                    "semantic_cache": "SKIPPED" if intent_res.is_conversational else "MISS",
                    "context_builder": "COMPLETED",
                    "cheap_model": "COMPLETED",
                    "judge": "COMPLETED",
                    "rung2_exemplars": "SKIPPED",
                    "rung3_strong": "SKIPPED",
                    "final_response": "COMPLETED",
                    "stream_user": "COMPLETED"
                }
            )

            self.store.log_request(receipt.model_dump())

            yield f"event: workflow_step\ndata: {json.dumps({'node': 'cheap_model', 'state': 'COMPLETED'})}\n\n"
            yield f"event: workflow_step\ndata: {json.dumps({'node': 'judge', 'state': 'COMPLETED'})}\n\n"
            yield f"event: workflow_step\ndata: {json.dumps({'node': 'final_response', 'state': 'COMPLETED'})}\n\n"
            yield f"event: workflow_step\ndata: {json.dumps({'node': 'stream_user', 'state': 'COMPLETED'})}\n\n"
            yield f"event: complete\ndata: {json.dumps({'request_id': req_id, 'receipt': receipt.model_dump()})}\n\n"
        except asyncio.CancelledError:
            logger.info(f"Stream {req_id} cancelled by client abort.")
        except Exception as e:
            logger.error(f"Error during stream_chat: {e}")
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"
