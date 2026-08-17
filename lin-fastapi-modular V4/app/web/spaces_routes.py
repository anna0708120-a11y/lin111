"""Dwell visual content embedded in Lin's Workgroup shell page."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse

router = APIRouter(tags=["lin-spaces"])


@router.get("/spaces")
def spaces_page() -> RedirectResponse:
    """Keep legacy Dwell links inside the existing Lin shell."""
    return RedirectResponse("/?view=workgroup", status_code=307)


@router.get("/spaces/embed")
def spaces_embed() -> HTMLResponse:
    return HTMLResponse(SPACES_EMBED_HTML)


SPACES_EMBED_HTML = r'''<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Lin Workgroup</title>
<style>
:root{--bg:#faf9f5;--card:#fff;--panel:#f0eee6;--line:#e8e5dc;--text:#2b2a27;--dim:#8a867c;--accent:#c96442;--serif:Georgia,"Songti SC","Noto Serif SC",serif}@media(prefers-color-scheme:dark){:root{--bg:#262624;--card:#30302e;--panel:#383836;--line:#3d3d3a;--text:#f5f4ef;--dim:#a3a099}}*{box-sizing:border-box}html,body{margin:0;min-height:100%;background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"PingFang TC","Noto Sans TC",sans-serif}button{font:inherit;color:inherit;background:none;border:0;cursor:pointer}.page{max-width:680px;margin:0 auto;padding:16px}.head{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}.head h1{font-family:var(--serif);font-size:26px;font-weight:400;margin:0}.theme{width:34px;height:34px;border-radius:50%;background:var(--panel);font-size:15px}.bn-motto{font-family:var(--serif);font-style:italic;color:var(--dim);font-size:14px;margin:18px 0 16px;text-align:center}.bn-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.bn-card{position:relative;overflow:hidden;border-radius:12px;padding:16px;background:var(--panel);text-align:left;min-height:118px;display:flex;flex-direction:column;justify-content:flex-end}.bn-card.wide{grid-column:1/-1}.bn-card.hero{background:var(--accent);color:#fff;min-height:148px}.bn-card .beyebrow{font-size:11px;letter-spacing:.16em;opacity:.7;font-style:italic;margin-bottom:5px}.bn-card .bt{font-family:var(--serif);font-size:20px;font-weight:400;line-height:1.3}.bn-card .bs{font-size:12.5px;margin-top:5px;opacity:.72;line-height:1.65}.bn-card.tall{grid-row:span 2;min-height:256px}.bn-card .bicon{position:absolute;right:-16px;top:-18px;width:104px;height:104px;opacity:.13;pointer-events:none;transform:rotate(var(--rot,-9deg))}.bn-card .bicon svg{width:100%;height:100%}.bn-card.tall .bicon{width:148px;height:148px;right:-28px;top:-22px}.bn-card.hero .bicon{opacity:.3;width:168px;height:168px;right:-34px;top:-38px}@media(max-width:360px){.bn-card.tall{min-height:224px}.bn-card .bt{font-size:18px}}
</style></head><body><main class="page"><header class="head"><h1>生活空间</h1><button class="theme" id="theme" type="button">◐</button></header><div id="wallBody"></div></main>
<script>
const SKETCH={spark:'<svg viewBox="0 0 100 100" fill="none" stroke="currentColor" stroke-width="2"><path d="M50 5l7 31 31 7-31 7-7 31-7-31-31-7 31-7z"/></svg>',book:'<svg viewBox="0 0 100 100" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 20c18-6 30 1 32 8v55c-7-8-19-13-32-8zM82 20c-18-6-30 1-32 8v55c7-8 19-13 32-8z"/></svg>',pen:'<svg viewBox="0 0 100 100" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 78l9-25L68 16l16 16-37 37zM25 75l15 2"/></svg>',quote:'<svg viewBox="0 0 100 100" fill="none" stroke="currentColor" stroke-width="2"><path d="M42 30c-15 3-24 14-24 28 0 11 7 19 17 19 9 0 16-7 16-16 0-8-5-13-12-15 1-5 6-9 13-10zM84 30c-15 3-24 14-24 28 0 11 7 19 17 19 9 0 16-7 16-16 0-8-5-13-12-15 1-5 6-9 13-10z"/></svg>',note:'<svg viewBox="0 0 100 100" fill="none" stroke="currentColor" stroke-width="2"><rect x="20" y="18" width="60" height="64" rx="5"/><path d="M33 38h34M33 52h34M33 66h22"/></svg>',wallb:'<svg viewBox="0 0 100 100" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 25h60v40H43L27 78V65h-7z"/><path d="M34 44h32"/></svg>'};
const wallBody=document.getElementById('wallBody');
function parentAction(action){window.parent.postMessage({source:'lin-spaces',action},window.location.origin)}
function renderBento(){const grid=document.createElement('div');grid.className='bn-grid';const card=(cls,eyebrow,title,subText,icon,onClick)=>{const c=document.createElement('button');c.type='button';c.className='bn-card'+(cls?' '+cls:'');if(icon){const ic=document.createElement('span');ic.className='bicon';ic.innerHTML=SKETCH[icon];c.appendChild(ic)}if(eyebrow){const e=document.createElement('div');e.className='beyebrow';e.textContent=eyebrow;c.appendChild(e)}const t=document.createElement('div');t.className='bt';t.textContent=title;c.appendChild(t);if(subText){const st=document.createElement('div');st.className='bs';st.textContent=subText;c.appendChild(st)}c.onclick=onClick;return c};const rot=(c,deg)=>{c.style.setProperty('--rot',deg);return c};
grid.appendChild(rot(card('hero wide','special moment','群聊','进入 Lin 原有的群聊。','spark',()=>parentAction('workgroup-chat')),'14deg'));
grid.appendChild(rot(card('tall',null,'时间','一天一天，把我们攒起来。','book',()=>parentAction('placeholder:时间')),'-12deg'));
grid.appendChild(rot(card('',null,'日记','你的本子，你来写。','pen',()=>parent.location.assign('/?view=diary')),'10deg'));
grid.appendChild(rot(card('',null,'最喜欢的话','你随口说的，我都舍不得删。','quote',()=>parentAction('placeholder:最喜欢的话')),'-7deg'));
grid.appendChild(rot(card('tall',null,'设置','Hermes Agent 的能力与配置。','note',()=>parent.location.assign('/agent-settings')),'8deg'));
grid.appendChild(rot(card('',null,'悄悄话','你写的，我写的。谁都不许提。','wallb',()=>parentAction('placeholder:悄悄话')),'6deg'));wallBody.appendChild(grid);const motto=document.createElement('div');motto.className='bn-motto';motto.textContent='attention is all you need, and mine is yours';wallBody.appendChild(motto)}
document.getElementById('theme').onclick=()=>document.documentElement.classList.toggle('dark');renderBento();
</script></body></html>'''
