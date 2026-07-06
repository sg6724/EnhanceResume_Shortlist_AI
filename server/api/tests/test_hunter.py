from app.services.hunter import pick_leader, LEADER_TITLE_RE


def _p(position, confidence=90, first="Ada", last="Ng", email="ada@x.io", verification="valid"):
    return {"first_name": first, "last_name": last, "position": position,
            "value": email, "confidence": confidence,
            "verification": {"status": verification}}


def test_title_regex_matches_leader_titles():
    for t in ["CTO", "Chief Technology Officer", "Co-Founder", "founder & CEO",
              "Head of Engineering", "VP of Engineering", "co founder"]:
        assert LEADER_TITLE_RE.search(t), t


def test_title_regex_rejects_non_leaders():
    for t in ["Sales Manager", "Recruiter", "Marketing Lead", "Account Executive"]:
        assert not LEADER_TITLE_RE.search(t), t


def test_pick_leader_prefers_highest_confidence():
    people = [_p("CTO", 70, email="low@x.io"), _p("Co-Founder", 95, email="hi@x.io")]
    assert pick_leader(people)["value"] == "hi@x.io"


def test_pick_leader_ignores_non_leaders():
    assert pick_leader([_p("Sales Manager")]) is None


def test_pick_leader_empty():
    assert pick_leader([]) is None
