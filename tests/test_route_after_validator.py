from app.service.agent.routing import route_after_validator


def test_first_fail_rewrites_matching_tutor_node():
    st = {
        "response_kind": "explanation",
        "validator_ok": False,
        "rewrite_count": 0,
        "tutor_node": "tutor_standard",
    }
    assert route_after_validator(st) == "rewrite_standard"
    st["tutor_node"] = "tutor_adaptive"
    assert route_after_validator(st) == "rewrite_adaptive"


def test_second_fail_done():
    st = {
        "response_kind": "explanation",
        "validator_ok": False,
        "rewrite_count": 1,
        "tutor_node": "tutor_adaptive",
        "draft_answer": "RAG là ...",
    }
    assert route_after_validator(st) == "done"
