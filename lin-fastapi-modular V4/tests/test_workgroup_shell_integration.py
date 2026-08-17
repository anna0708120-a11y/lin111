from pathlib import Path


ROOT = Path(__file__).parents[1]
FRONTEND = (ROOT / "app/web/frontend.py").read_text()
SPACES = (ROOT / "app/web/spaces_routes.py").read_text()
LIFE_VIEW = (ROOT / "static/js/life_view.js").read_text()
RENDER = (ROOT / "render.yaml").read_text()


def test_workgroup_is_a_lin_shell_page_with_legacy_spaces_links_redirected():
    assert 'id="pg-workgroup"' in FRONTEND
    assert "location.assign('/spaces')" not in FRONTEND
    assert "stab('workgroup')" in FRONTEND
    assert 'id="tb-workgroup"' in FRONTEND
    assert 'src="/spaces/embed"' in FRONTEND
    assert '@router.get("/spaces")' in SPACES
    assert 'RedirectResponse("/?view=workgroup", status_code=307)' in SPACES


def test_embedded_dwell_keeps_six_cards_and_uses_existing_workgroup_api():
    assert SPACES.count("grid.appendChild(rot(card(") == 6
    assert "workgroup-chat" in SPACES
    assert "fetch('/workgroup/messages')" in FRONTEND
    assert "method:'POST'" in FRONTEND
    assert "parent.location.assign('/?view=diary')" in SPACES
    assert "parent.location.assign('/agent-settings')" in SPACES


def test_life_tab_uses_existing_read_only_life_endpoints():
    assert 'id="pg-life"' in FRONTEND
    assert '/static/js/life_view.js' in FRONTEND
    assert "/life/state" in LIFE_VIEW
    assert "/life/context" in LIFE_VIEW
    assert "/life/events?limit=50" in LIFE_VIEW


def test_render_contract_declares_required_persistence_and_hermes_settings_env():
    for key in ("SUPABASE_URL", "SUPABASE_KEY", "HERMES_MANAGEMENT_URL", "HERMES_MANAGEMENT_TOKEN"):
        assert f"- key: {key}" in RENDER
