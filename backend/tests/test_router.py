import pytest
from backend.app.router import ModelRouter


def test_model_router_roles():
    router = ModelRouter(
        cheap_model_id="test-cheap-model",
        strong_model_id="test-strong-model",
        judge_model_id="test-judge-model"
    )
    assert router.get_model("cheap") == "test-cheap-model"
    assert router.get_model("strong") == "test-strong-model"
    assert router.get_model("judge") == "test-judge-model"
    assert router.cheap == "test-cheap-model"
    assert router.strong == "test-strong-model"
    assert router.judge == "test-judge-model"


def test_model_router_invalid_role():
    router = ModelRouter()
    with pytest.raises(ValueError) as exc:
        router.get_model("unknown")
    assert "Unknown model role 'unknown'" in str(exc.value)


def test_conversation_intent_classifier():
    from backend.app.router import ConversationIntentClassifier, IntentType

    # Standalone conversational
    g_res = ConversationIntentClassifier.classify("hello")
    assert g_res.intent == IntentType.GREETING
    assert g_res.is_conversational is True
    assert g_res.maximum_rung == 1

    c_res = ConversationIntentClassifier.classify("how are you?")
    assert c_res.intent == IntentType.CASUAL_CONVERSATION
    assert c_res.is_conversational is True
    assert c_res.maximum_rung == 1

    t_res = ConversationIntentClassifier.classify("thanks a lot")
    assert t_res.intent == IntentType.GRATITUDE
    assert t_res.is_conversational is True
    assert t_res.maximum_rung == 1

    f_res = ConversationIntentClassifier.classify("bye milte hain")
    assert f_res.intent == IntentType.FAREWELL
    assert f_res.is_conversational is True
    assert f_res.maximum_rung == 1

    # Handbook query with embedded greeting
    embed_res = ConversationIntentClassifier.classify("hello, what documents are required for hostel admission?")
    assert embed_res.intent == IntentType.HANDBOOK_QUERY
    assert embed_res.is_conversational is False
    assert embed_res.maximum_rung == 3

    # Coding query
    code_res = ConversationIntentClassifier.classify("write a python function for binary search")
    assert code_res.intent == IntentType.CODING
    assert code_res.is_conversational is False
    assert code_res.maximum_rung == 3
