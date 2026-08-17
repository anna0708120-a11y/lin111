from pathlib import Path


ROOT = Path(__file__).parents[1]
FRONTEND = (ROOT / "app/web/frontend.py").read_text()
SPACES = (ROOT / "app/web/spaces_routes.py").read_text()
LIFE_VIEW = (ROOT / "static/js/life_view.js").read_text()
RENDER = (ROOT / "render.yaml").read_text()


def test_workgroup_is_a_lin_shell_page_with_legacy_spaces_links_redirected():
    assert 'id="pg-workgroup"' in FRONTEND
    assert 'id="workgroupHome"' in FRONTEND
    assert 'id="workgroupChat"' in FRONTEND
    assert "location.assign('/spaces')" not in FRONTEND
    assert "stab('workgroup')" in FRONTEND
    assert 'id="tb-workgroup"' in FRONTEND
    assert "iframe" not in FRONTEND[FRONTEND.index('id=\"pg-workgroup\"'):FRONTEND.index('id=\"pg-mine\"')]
    assert '@router.get("/spaces")' in SPACES
    assert 'RedirectResponse("/?view=workgroup", status_code=307)' in SPACES
    assert "/spaces/embed" not in SPACES


def test_dwell_bento_is_directly_rendered_in_workgroup_home_and_opens_native_chat():
    assert FRONTEND.count("grid.appendChild(rot(card(") == 6
    assert "showWorkgroupChat" in FRONTEND
    assert "fetch(AU+'/workgroup/messages')" in FRONTEND
    assert "id=\"workgroupMembers\"" in FRONTEND
    assert "id=\"workgroupMessages\"" in FRONTEND
    assert "id=\"workgroupComposer\"" in FRONTEND
    assert "location.assign('/?view=diary')" in FRONTEND
    assert "location.assign('/agent-settings')" in FRONTEND


def test_life_tab_uses_existing_read_only_life_endpoints():
    assert 'id="pg-life"' in FRONTEND
    assert '/static/js/life_view.js' in FRONTEND
    assert "/life/state" in LIFE_VIEW
    assert "/life/context" in LIFE_VIEW
    assert "/life/events?limit=50" in LIFE_VIEW


def test_render_contract_declares_required_persistence_and_hermes_settings_env():
    for key in ("SUPABASE_URL", "SUPABASE_KEY", "HERMES_MANAGEMENT_URL", "HERMES_MANAGEMENT_TOKEN"):
        assert f"- key: {key}" in RENDER
