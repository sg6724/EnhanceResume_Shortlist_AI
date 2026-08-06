from __future__ import annotations

from app.integrations.jobs import apify


def test_split_urls_accepts_newlines_and_commas():
    assert apify.split_urls("https://a.test/jobs, https://b.test/careers\nhttps://a.test/jobs") == [
        "https://a.test/jobs",
        "https://b.test/careers",
    ]


def test_normalize_linkedin_like_item():
    item = {
        "jobId": "123",
        "jobTitle": "Machine Learning Engineer",
        "companyName": "Acme",
        "jobLocation": "Remote",
        "jobUrl": "https://linkedin.com/jobs/view/123",
        "jobDescription": "We need Python, PyTorch, model evaluation, and production ML experience.",
    }

    result = apify._normalize_item(item, "linkedin")

    assert result is not None
    assert result["source"] == "linkedin"
    assert result["company"] == "Acme"
    assert result["title"] == "Machine Learning Engineer"
    assert result["url"] == "https://linkedin.com/jobs/view/123"
    assert result["external_id"] == "123"
    assert result["content_hash"]
