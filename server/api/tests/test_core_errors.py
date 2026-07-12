from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.errors import (
    AppError,
    DependencyError,
    NotFoundError,
    QuotaError,
    ValidationError,
    register_error_handlers,
)


def test_status_codes():
    assert NotFoundError("nope").status_code == 404
    assert ValidationError("bad").status_code == 422
    assert DependencyError("upstream down").status_code == 502
    assert QuotaError("quota hit").status_code == 429
    assert AppError("generic").status_code == 500


def _build_app() -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/boom/{kind}")
    def boom(kind: str):
        errors = {
            "notfound": NotFoundError,
            "validation": ValidationError,
            "dependency": DependencyError,
            "quota": QuotaError,
        }
        raise errors[kind](f"{kind} happened")

    return app


def test_not_found_envelope():
    client = TestClient(_build_app())
    resp = client.get("/boom/notfound")
    assert resp.status_code == 404
    assert resp.json() == {"error": {"code": "NotFoundError", "message": "notfound happened"}}


def test_quota_envelope():
    client = TestClient(_build_app())
    resp = client.get("/boom/quota")
    assert resp.status_code == 429
    assert resp.json()["error"]["code"] == "QuotaError"
