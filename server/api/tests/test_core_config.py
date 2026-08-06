from app.core.config import Settings


def _make_settings(**overrides) -> Settings:
    base = dict(
        supabase_url="https://x.supabase.co",
        supabase_service_key="svc-key",
        gemini_api_key="gem-key",
        groq_api_key="groq-key",
        resend_api_key="re-key",
        resend_from="noreply@example.com",
        hunter_api_key="hunter-key",
        apollo_api_key="apollo-key",
        adzuna_app_id="az-id",
        adzuna_api_key="az-key",
        compile_service_url="http://localhost:8001",
    )
    base.update(overrides)
    return Settings(**base)


def test_flat_fields_unchanged():
    s = _make_settings()
    assert s.supabase_url == "https://x.supabase.co"
    assert s.gemini_api_key == "gem-key"
    assert s.apollo_api_key == "apollo-key"
    assert s.groq_api_key == "groq-key"


def test_db_section():
    s = _make_settings()
    assert s.db.supabase_url == "https://x.supabase.co"
    assert s.db.supabase_service_key == "svc-key"


def test_llm_section():
    s = _make_settings()
    assert s.llm.gemini_api_key == "gem-key"
    assert s.llm.groq_api_key == "groq-key"


def test_contacts_section_includes_apollo_and_hunter_and_adzuna():
    s = _make_settings()
    assert s.contacts.apollo_api_key == "apollo-key"
    assert s.contacts.hunter_api_key == "hunter-key"
    assert s.contacts.adzuna_app_id == "az-id"
    assert s.contacts.adzuna_api_key == "az-key"


def test_email_section():
    s = _make_settings()
    assert s.email.resend_api_key == "re-key"
    assert s.email.resend_from == "noreply@example.com"


def test_compile_section():
    s = _make_settings()
    assert s.compile.compile_service_url == "http://localhost:8001"


def test_compile_section_uses_render_hostport_when_default_url_is_unchanged():
    s = _make_settings(compile_service_hostport="gethired-compile:10000")
    assert s.compile.compile_service_url == "http://gethired-compile:10000"


def test_compile_section_explicit_url_overrides_render_hostport():
    s = _make_settings(
        compile_service_url="https://compile.example.com",
        compile_service_hostport="gethired-compile:10000",
    )
    assert s.compile.compile_service_url == "https://compile.example.com"


def test_old_import_path_reexports_same_settings_class():
    from app.config import Settings as OldSettings
    from app.config import settings as old_settings_instance
    from app.core.config import settings as new_settings_instance

    assert OldSettings is Settings
    assert old_settings_instance is new_settings_instance
