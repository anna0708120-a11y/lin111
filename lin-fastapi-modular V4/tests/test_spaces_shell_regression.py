from pathlib import Path


ROOT = Path(__file__).parents[1]
FRONTEND = ROOT / "app/web/frontend.py"
SPACES = ROOT / "app/web/spaces_routes.py"


def test_spaces_has_six_cards_and_preserves_lin_entry_points():
    spaces = SPACES.read_text()
    assert spaces.count("grid.appendChild(rot(card(") == 6
    assert "location.assign('/?view=time')" in spaces
    assert "location.assign('/?view=diary')" in spaces
    assert "location.assign('/?view=favorites')" in spaces
    assert "location.assign('/?view=whispers')" in spaces
    assert "location.assign('/agent-settings')" in spaces


def test_lin_shell_has_all_bottom_tabs_and_matching_pages():
    frontend = FRONTEND.read_text()
    for tab in ("monitor", "chat", "memory", "life", "mine"):
        assert f'id="tb-{tab}"' in frontend
        assert f'id="pg-{tab}"' in frontend
    assert 'id="tb-workgroup"' in frontend
    assert "location.assign('/spaces')" in frontend


def test_frontend_has_no_external_google_font_import_and_stab_guards_missing_pages():
    frontend = FRONTEND.read_text()
    assert "fonts.googleapis.com" not in frontend
    stab_start = frontend.index("function stab(tab){")
    stab_end = frontend.index("// 页面加载时如果是Mine tab", stab_start)
    stab = frontend[stab_start:stab_end]
    assert "if(!pg)return;" in stab
