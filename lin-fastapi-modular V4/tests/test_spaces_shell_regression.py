from pathlib import Path


ROOT = Path(__file__).parents[1]
FRONTEND = ROOT / "app/web/frontend.py"
SPACES = ROOT / "app/web/spaces_routes.py"


def test_workgroup_bento_has_six_cards_and_preserves_lin_entry_points():
    frontend = FRONTEND.read_text()
    assert frontend.count("grid.appendChild(rot(card(") == 6
    assert "showWorkgroupPlaceholder('时间')" in frontend
    assert "location.assign('/?view=diary')" in frontend
    assert "showWorkgroupPlaceholder('最喜欢的话')" in frontend
    assert "showHermesAgentCard" in frontend
    assert "fetch(AU+'/api/hermes/status')" in frontend
    assert "fetch(AU+'/api/hermes/models')" in frontend
    assert "fetch(AU+'/api/hermes/task'" in frontend
    assert "showWorkgroupPlaceholder('悄悄话')" in frontend
    assert '@router.get("/spaces")' in SPACES.read_text()


def test_lin_shell_has_all_bottom_tabs_and_matching_pages():
    frontend = FRONTEND.read_text()
    for tab in ("monitor", "chat", "memory", "life", "workgroup", "mine"):
        assert f'id="tb-{tab}"' in frontend
        assert f'id="pg-{tab}"' in frontend
    assert "stab('workgroup')" in frontend
    workgroup = frontend[frontend.index('id="pg-workgroup"'):frontend.index('id="pg-mine"')]
    assert "iframe" not in workgroup


def test_frontend_has_no_external_google_font_import_and_stab_guards_missing_pages():
    frontend = FRONTEND.read_text()
    assert "fonts.googleapis.com" not in frontend
    stab_start = frontend.index("function stab(tab){")
    stab_end = frontend.index("// 页面加载时如果是Mine tab", stab_start)
    stab = frontend[stab_start:stab_end]
    assert "if(!pg)return;" in stab
