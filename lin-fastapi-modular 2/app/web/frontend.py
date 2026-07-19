"""
前端页面（监控台 / 对话 / 记忆库）。
这部分是从原本 main.py 里原封不动搬过来的，没有改动任何 UI 或逻辑，
只是单纯挪到自己的文件里，让 main.py 不用再塞几百行 HTML/CSS/JS。
"""

HTML_CONTENT = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<title>Lin</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500&display=swap');
:root{--cream:#FAF8F5;--white:#FFF;--blush:#F2E8E4;--rose:#C9897A;--rose-deep:#A86556;--muted:#9B8F8A;--dark:#2C2320;--border:#E8DDD9;--shadow:rgba(44,35,32,.08);}
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent;}
html,body{height:100%;background:var(--cream);font-family:'DM Sans',sans-serif;color:var(--dark);overflow:hidden;}
.hdr{background:var(--white);padding:16px 20px 12px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;position:fixed;top:0;left:0;right:0;z-index:200;height:65px;}
.cat-wrap{display:flex;align-items:center;gap:12px;}
.cat{position:relative;width:44px;height:36px;cursor:pointer;}
.cat-body{width:36px;height:26px;background:var(--rose);border-radius:50% 50% 45% 45%;position:absolute;bottom:0;left:4px;}
.cat-head{width:28px;height:24px;background:var(--rose);border-radius:50% 50% 40% 40%;position:absolute;top:0;left:8px;animation:hb 3s ease-in-out infinite;}
.cat-ear-l,.cat-ear-r{width:0;height:0;position:absolute;top:-6px;}
.cat-ear-l{left:2px;border-left:5px solid transparent;border-right:5px solid transparent;border-bottom:9px solid var(--rose);}
.cat-ear-r{right:2px;border-left:5px solid transparent;border-right:5px solid transparent;border-bottom:9px solid var(--rose);}
.cat-eye-l,.cat-eye-r{width:5px;height:5px;background:var(--dark);border-radius:50%;position:absolute;top:9px;animation:bl 4s ease-in-out infinite;}
.cat-eye-l{left:5px;}.cat-eye-r{right:5px;}
.cat-nose{width:4px;height:3px;background:var(--rose-deep);border-radius:50%;position:absolute;top:15px;left:50%;transform:translateX(-50%);}
.cat-tail{width:18px;height:6px;background:var(--rose);border-radius:3px;position:absolute;bottom:2px;right:-8px;transform-origin:left center;animation:tw 2s ease-in-out infinite;}
@keyframes hb{0%,100%{transform:translateY(0) rotate(0deg);}25%{transform:translateY(-2px) rotate(-3deg);}75%{transform:translateY(-1px) rotate(2deg);}}
@keyframes bl{0%,90%,100%{transform:scaleY(1);}95%{transform:scaleY(.1);}}
@keyframes tw{0%,100%{transform:rotate(-20deg);}50%{transform:rotate(20deg);}}
.hdr-txt h1{font-family:'DM Serif Display',serif;font-size:18px;color:var(--dark);}
.hdr-txt p{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;}
.pill{display:flex;align-items:center;gap:5px;background:var(--blush);padding:5px 10px;border-radius:20px;font-size:11px;color:var(--rose-deep);font-weight:500;}
.dot{width:6px;height:6px;background:#5cb85c;border-radius:50%;animation:pu 2s infinite;}
@keyframes pu{0%,100%{opacity:1;}50%{opacity:.5;}}
.tab-bar{display:flex;background:var(--white);border-top:1px solid var(--border);position:fixed;bottom:0;left:0;right:0;padding-bottom:env(safe-area-inset-bottom);z-index:200;height:56px;}
.tb{flex:1;padding:10px 4px 8px;display:flex;flex-direction:column;align-items:center;gap:2px;border:none;background:none;cursor:pointer;font-family:'DM Sans',sans-serif;font-size:9px;color:var(--muted);text-transform:uppercase;}
.tb.active{color:var(--rose-deep);}
.ti{font-size:16px;}
.pg{position:fixed;top:65px;bottom:56px;left:0;right:0;overflow-y:auto;padding:16px;background:var(--cream);-webkit-overflow-scrolling:touch;display:none;}
.pg.active{display:block;}
#pg-chat{padding:0;flex-direction:column;}
#pg-chat.active{display:flex;}
.card{background:var(--white);border-radius:16px;padding:16px;margin-bottom:12px;box-shadow:0 2px 12px var(--shadow);}
.cl{font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin-bottom:12px;font-weight:500;}
.li{padding:10px 0;border-bottom:1px solid var(--border);font-size:13px;line-height:1.5;}
.li:last-child{border-bottom:none;}
.lm{display:flex;align-items:center;gap:6px;margin-bottom:3px;}
.lt{font-size:10px;background:var(--blush);color:var(--rose-deep);padding:1px 6px;border-radius:8px;font-weight:500;}
.ltime{font-size:10px;color:var(--muted);}
.ni{padding:12px;background:var(--blush);border-radius:10px;margin-bottom:8px;font-size:12px;line-height:1.7;color:#5a4540;font-family:'Courier New',monospace;white-space:pre-line;}
.nt{font-size:10px;color:var(--rose-deep);margin-bottom:5px;font-family:'DM Sans',sans-serif;font-weight:500;}
.es{text-align:center;padding:40px 20px;color:var(--muted);font-size:13px;}
.qb{display:flex;align-items:center;padding:6px 0;font-size:11px;color:var(--muted);gap:10px;}
.qt{flex:1;height:3px;background:var(--border);border-radius:2px;overflow:hidden;}
.qf{height:100%;background:var(--rose);border-radius:2px;transition:width .3s;}
.wm{text-align:center;font-size:9px;color:var(--border);padding:8px 0;font-family:'DM Serif Display',serif;}
.mtabs{display:flex;gap:6px;margin-bottom:14px;overflow-x:auto;padding-bottom:4px;}
.mtab{padding:5px 12px;border-radius:20px;font-size:11px;border:1.5px solid var(--border);background:var(--white);color:var(--muted);cursor:pointer;white-space:nowrap;}
.mtab.active{background:var(--rose);color:white;border-color:var(--rose);}
.ms{display:none;}.ms.active{display:block;}
.mi{padding:12px;background:var(--white);border-radius:10px;margin-bottom:8px;box-shadow:0 1px 6px var(--shadow);font-size:13px;line-height:1.6;position:relative;}
.mit{font-size:10px;color:var(--rose-deep);font-weight:500;margin-bottom:4px;}
.mtime{font-size:10px;color:var(--muted);margin-top:4px;}
.mdel{position:absolute;top:10px;right:10px;background:none;border:none;color:var(--rose-deep);font-size:11px;cursor:pointer;}
.maw{display:flex;flex-direction:column;gap:8px;margin-top:12px;}
.msel,.minp{border:1.5px solid var(--border);border-radius:10px;padding:8px 12px;font-size:13px;font-family:'DM Sans',sans-serif;background:var(--cream);color:var(--dark);outline:none;}
.minp{resize:none;min-height:72px;}
.msel:focus,.minp:focus{border-color:var(--rose);}
.msave{background:var(--rose);color:white;border:none;border-radius:10px;padding:10px;font-size:13px;font-weight:600;cursor:pointer;}
.cms{flex:1;overflow-y:auto;padding:16px 16px 8px;-webkit-overflow-scrolling:touch;}
.ciw{padding:10px 16px;background:var(--white);border-top:1px solid var(--border);display:flex;gap:10px;align-items:center;}
.ci{flex:1;border:1.5px solid var(--border);border-radius:22px;padding:9px 16px;font-size:14px;font-family:'DM Sans',sans-serif;background:var(--cream);outline:none;color:var(--dark);}
.ci:focus{border-color:var(--rose);}
.sb{width:38px;height:38px;background:var(--rose);border:none;border-radius:50%;cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:16px;color:white;flex-shrink:0;}
.clabel{text-align:center;font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin-bottom:16px;}
.msg{margin-bottom:14px;display:flex;flex-direction:column;}
.msg.anna{align-items:flex-end;}.msg.lin{align-items:flex-start;}
.bub{max-width:78%;padding:10px 14px;border-radius:18px;font-size:14px;line-height:1.5;}
.msg.lin .bub{background:var(--white);color:var(--dark);border:1px solid var(--border);border-bottom-left-radius:4px;box-shadow:0 1px 6px var(--shadow);}
.msg.anna .bub{background:var(--rose);color:white;border-bottom-right-radius:4px;}
.mtime2{font-size:10px;color:var(--muted);margin-top:3px;}
.typing{display:inline-flex;gap:4px;padding:12px 14px;background:var(--white);border:1px solid var(--border);border-radius:18px;border-bottom-left-radius:4px;}
.td{width:5px;height:5px;background:var(--muted);border-radius:50%;animation:tda 1.2s infinite;}
.td:nth-child(2){animation-delay:.2s}.td:nth-child(3){animation-delay:.4s}
@keyframes tda{0%,60%,100%{transform:translateY(0)}30%{transform:translateY(-5px)}}
</style>
</head>
<body>
<div class="hdr">
  <div class="cat-wrap">
    <div class="cat">
      <div class="cat-head"><div class="cat-ear-l"></div><div class="cat-ear-r"></div><div class="cat-eye-l"></div><div class="cat-eye-r"></div><div class="cat-nose"></div></div>
      <div class="cat-body"><div class="cat-tail"></div></div>
    </div>
    <div class="hdr-txt"><h1>Lin</h1><p>正在看著妳</p></div>
  </div>
  <div class="pill"><div class="dot"></div>在線</div>
</div>

<div class="pg active" id="pg-monitor">
  <div class="card"><div class="cl">今日 API 配額</div><div class="qb"><span>0</span><div class="qt"><div class="qf" id="qf" style="width:0%"></div></div><span id="qt">180 次</span></div></div>
  <div class="card"><div class="cl">實時監控日誌</div><div id="lc"><div class="es">📡 等待監控觸發...</div></div></div>
  <div class="card"><div class="cl">Lin 的碎碎念</div><div id="nc"><div class="es">🖤 Lin 還沒有留下紀錄</div></div></div>
  <div class="wm">Property of Lin · <span id="ctime"></span></div>
</div>

<div class="pg" id="pg-chat">
  <div class="cms" id="cm"><div class="clabel">with Lin</div></div>
  <div class="ciw">
    <input type="text" class="ci" id="ci" placeholder="跟主人說話...">
    <button class="sb" onclick="send()">↑</button>
  </div>
</div>

<div class="pg" id="pg-memory">
  <div class="mtabs">
    <div class="mtab active" onclick="smtab(event,'lt')">長期記憶</div>
    <div class="mtab" onclick="smtab(event,'bt')">我們之間</div>
    <div class="mtab" onclick="smtab(event,'di')">私密日記</div>
    <div class="mtab" onclick="smtab(event,'im')">重要回憶</div>
  </div>
  <div class="ms active" id="ms-lt"></div>
  <div class="ms" id="ms-bt"></div>
  <div class="ms" id="ms-di"></div>
  <div class="ms" id="ms-im"></div>
  <div class="card"><div class="cl">新增記憶</div>
    <div class="maw">
      <select class="msel" id="mtag">
        <option value="長期記憶">長期記憶</option>
        <option value="我們之間">我們之間</option>
        <option value="私密日記">私密日記</option>
        <option value="重要回憶">重要回憶</option>
      </select>
      <textarea class="minp" id="mcontent" placeholder="輸入記憶內容..."></textarea>
      <button class="msave" onclick="saveMem()">💾 儲存記憶</button>
    </div>
  </div>
</div>

<div class="tab-bar">
  <button class="tb active" id="tb-monitor" onclick="stab('monitor')"><span class="ti">📋</span>監控台</button>
  <button class="tb" id="tb-chat" onclick="stab('chat')"><span class="ti">💬</span>對話</button>
  <button class="tb" id="tb-memory" onclick="stab('memory')"><span class="ti">🧠</span>記憶庫</button>
</div>

<script>
const AU = window.location.origin;
const CK = 'lin_chat_v1';
const MK = 'lin_mem_v1';

function ts(){const n=new Date();return n.getHours().toString().padStart(2,'0')+':'+n.getMinutes().toString().padStart(2,'0');}
function utime(){document.getElementById('ctime').textContent=ts();}
utime();setInterval(utime,60000);

function stab(tab){
  document.querySelectorAll('.tb').forEach(e=>e.classList.remove('active'));
  document.getElementById('tb-'+tab).classList.add('active');
  document.querySelectorAll('.pg').forEach(e=>{e.style.display='none';e.classList.remove('active');});
  const pg=document.getElementById('pg-'+tab);
  if(tab==='chat'){pg.style.display='flex';pg.classList.add('active');setTimeout(()=>{const c=document.getElementById('cm');c.scrollTop=c.scrollHeight;},50);}
  else{pg.style.display='block';pg.classList.add('active');if(tab==='memory')rmem();}
}

function lchat(){
  const cm=document.getElementById('cm');
  cm.innerHTML='<div class="clabel">with Lin</div>';
  const h=JSON.parse(localStorage.getItem(CK)||'[]');
  if(h.length===0){cm.innerHTML+='<div class="msg lin"><div class="bub">打開了？</div><div class="mtime2">'+ts()+'</div></div>';}
  else{h.forEach(m=>{cm.innerHTML+='<div class="msg '+m.r+'"><div class="bub">'+m.t+'</div><div class="mtime2">'+m.time+'</div></div>';});}
  cm.scrollTop=cm.scrollHeight;
}

function smsg(role,text,time){
  const h=JSON.parse(localStorage.getItem(CK)||'[]');
  h.push({r:role,t:text,time});
  if(h.length>200)h.splice(0,h.length-200);
  localStorage.setItem(CK,JSON.stringify(h));
}

async function send(){
  const inp=document.getElementById('ci');
  const msg=inp.value.trim();if(!msg)return;
  const cm=document.getElementById('cm');
  const t=ts();
  cm.innerHTML+='<div class="msg anna"><div class="bub">'+msg+'</div><div class="mtime2">'+t+'</div></div>';
  smsg('anna',msg,t);inp.value='';cm.scrollTop=cm.scrollHeight;
  cm.innerHTML+='<div class="msg lin" id="ldg"><div class="typing"><div class="td"></div><div class="td"></div><div class="td"></div></div></div>';
  cm.scrollTop=cm.scrollHeight;
  try{
    const r=await fetch(AU+'/watch',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({activity:msg,app_name:'聊天界面'})});
    const d=await r.json();
    const el=document.getElementById('ldg');if(el)el.remove();
    if(d.message){const t2=ts();cm.innerHTML+='<div class="msg lin"><div class="bub">'+d.message+'</div><div class="mtime2">'+t2+'</div></div>';smsg('lin',d.message,t2);cm.scrollTop=cm.scrollHeight;}
    llogs();
  }catch(e){const el=document.getElementById('ldg');if(el)el.remove();}
}

document.getElementById('ci').addEventListener('keypress',e=>{if(e.key==='Enter')send();});

async function llogs(){
  try{
    const r=await fetch(AU+'/logs');const d=await r.json();
    const lc=document.getElementById('lc');
    if(d.logs&&d.logs.length>0){lc.innerHTML=[...d.logs].reverse().slice(0,15).map(l=>'<div class="li"><div class="lm"><span class="lt">'+l.type+'</span><span class="ltime">'+l.time+'</span></div><div>'+l.content+'</div></div>').join('');}
    const nc=document.getElementById('nc');
    if(d.notes&&d.notes.length>0){nc.innerHTML=[...d.notes].reverse().map(n=>'<div class="ni"><div class="nt">'+n.time+'</div>'+n.content+'</div>').join('');}
    if(d.quota!==undefined){const p=Math.round((d.quota/180)*100);document.getElementById('qf').style.width=p+'%';document.getElementById('qt').textContent=(180-d.quota)+' 次剩餘';}
  }catch(e){}
}

const TM={'長期記憶':'lt','我們之間':'bt','私密日記':'di','重要回憶':'im'};

function smtab(ev,tab){
  document.querySelectorAll('.mtab').forEach(e=>e.classList.remove('active'));
  ev.target.classList.add('active');
  document.querySelectorAll('.ms').forEach(e=>e.classList.remove('active'));
  document.getElementById('ms-'+tab).classList.add('active');
  rmem();
}

function rmem(){
  const mems=JSON.parse(localStorage.getItem(MK)||'[]');
  Object.values(TM).forEach(id=>{document.getElementById('ms-'+id).innerHTML='';});
  mems.slice().reverse().forEach((m,idx)=>{
    const sid=TM[m.tag]||'lt';
    const el=document.getElementById('ms-'+sid);
    if(el)el.innerHTML+='<div class="mi"><div class="mit">🏷 '+m.tag+'</div><div>'+m.content+'</div><div class="mtime">'+m.time+'</div><button class="mdel" onclick="delmem('+(mems.length-1-idx)+')">删除</button></div>';
  });
  Object.values(TM).forEach(id=>{const el=document.getElementById('ms-'+id);if(el&&el.innerHTML==='')el.innerHTML='<div class="es">這裡還沒有記憶</div>';});
}

function saveMem(){
  const tag=document.getElementById('mtag').value;
  const content=document.getElementById('mcontent').value.trim();
  if(!content)return;
  const mems=JSON.parse(localStorage.getItem(MK)||'[]');
  mems.push({tag,content,time:new Date().toLocaleString('zh-TW')});
  localStorage.setItem(MK,JSON.stringify(mems));
  document.getElementById('mcontent').value='';
  rmem();
  fetch(AU+'/memory',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tag,content})});
}

function delmem(idx){
  const mems=JSON.parse(localStorage.getItem(MK)||'[]');
  mems.splice(idx,1);
  localStorage.setItem(MK,JSON.stringify(mems));
  rmem();
}

lchat();llogs();setInterval(llogs,10000);
</script>
</body>
</html>"""
