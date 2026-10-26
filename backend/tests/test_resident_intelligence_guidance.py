from types import SimpleNamespace

from app.analytics.services.intelligence_service import _resident_answer


def issue(issue_id: int, title: str, status: str, logged_date: str = "2026-10-01"):
    return SimpleNamespace(id=issue_id, title=title, status=status, logged_date=logged_date)


def answer(question: str, issues=None, notices=None, score="", published=False):
    return _resident_answer(
        question=question,
        issues=issues or [],
        notices=notices or [],
        score_summary=score,
        score_published=published,
    )


def test_resident_can_get_a_clear_new_issue_reporting_flow():
    summary, related = answer("How do I report a broken gate?")
    assert "open Complaints" in summary
    assert "attach clear photos" in summary
    assert "How do I report a new maintenance issue?" not in summary
    assert "Report a maintenance issue" in related


def test_resident_emergency_guidance_does_not_rely_on_valora():
    summary, _ = answer("There is a fire in the building")
    assert "contact local emergency services" in summary
    assert "do not wait for VALORA" in summary


def test_resident_access_requests_are_referred_to_hoa_not_approved_by_ai():
    summary, _ = answer("I can't see my unit")
    assert "estate administrator" in summary
    assert "I can't approve membership" in summary


def test_resident_can_filter_to_a_specific_request_id():
    summary, _ = answer(
        "What is the status of request #42?",
        issues=[
            issue(42, "Kitchen leak", "In progress"),
            issue(43, "Gate remote", "Resolved"),
        ],
    )
    assert "#42 Kitchen leak" in summary
    assert "#43 Gate remote" not in summary


def test_resident_open_requests_exclude_resolved_records():
    summary, _ = answer(
        "Show my open requests",
        issues=[
            issue(42, "Kitchen leak", "In progress"),
            issue(43, "Gate remote", "Resolved"),
        ],
    )
    assert "#42 Kitchen leak" in summary
    assert "#43 Gate remote" not in summary


def test_resident_is_not_given_an_invented_repair_timeline():
    summary, _ = answer(
        "When will my request be fixed?",
        issues=[issue(42, "Kitchen leak", "In progress")],
    )
    assert "does not have a verified completion estimate" in summary
    assert "must confirm the expected date" in summary
    assert "will be fixed by" not in summary


def test_unpublished_living_score_is_never_fabricated():
    summary, _ = answer("What is my estate's Living Score?")
    assert "not currently published" in summary
    assert "verified score" in summary


def test_published_living_score_is_returned_only_when_explicitly_marked_published():
    summary, _ = answer(
        "What is my estate's Living Score?",
        score="Living Score: 78/100",
        published=True,
    )
    assert summary == "Living Score: 78/100"


def test_notice_answer_is_limited_to_published_notices():
    summary, _ = answer("Any community announcements?", notices=["Pool closed on Friday."])
    assert "Pool closed on Friday." in summary
    summary, _ = answer("Any community announcements?")
    assert "published estate notices" in summary
    assert "does not prove that no offline notice exists" in summary


def test_resident_fallback_describes_supported_capabilities_and_privacy_limits():
    summary, related = answer("Can you help me?")
    assert "your own maintenance-request status" in summary
    assert "private requests from other residents" in summary
    assert "promise a repair date" in summary
    assert "How do I report a new maintenance issue?" in related
