from app.agents.letter_writer import validate_letter

GOOD = ("Backend engineer for Acme",
        "Hi Ada, I build FastAPI services. I shipped X and Y. "
        "I'd like to be considered for the Backend Engineer role at Acme. "
        "My resume is attached — happy to talk.")


def test_valid_letter_passes():
    assert validate_letter(*GOOD) is None


def test_empty_subject_fails():
    assert validate_letter("", GOOD[1]) is not None


def test_banned_phrase_fails():
    assert validate_letter(GOOD[0], "I hope this email finds you well. " + GOOD[1]) is not None


def test_over_220_words_fails():
    assert validate_letter(GOOD[0], "word " * 221) is not None
