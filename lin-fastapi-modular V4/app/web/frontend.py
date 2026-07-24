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
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="theme-color" content="#C9897A" id="theme-color-meta">
<link rel="manifest" href="/manifest.json">
<link rel="apple-touch-icon" href="/static/apple-touch-icon.png">
<title>Lin</title>
<script>
(function(){
  try{
    var t=localStorage.getItem('lin_theme');
    var d=window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches;
    var mode=t||(d?'dark':'light');
    document.documentElement.setAttribute('data-theme', mode);
    var m=document.getElementById('theme-color-meta');
    if(m) m.setAttribute('content', mode==='dark' ? '#000000' : '#C9897A');
  }catch(e){}
})();

// 页面加载完成后,如果当前在Mine tab,立即加载经期数据
document.addEventListener('DOMContentLoaded', () => {
  const minePage = document.getElementById('pg-mine');
  if (minePage && minePage.classList.contains('active')) {
    loadPeriod();
  }
});

</script>
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500&display=swap');
:root{--cream:#FAF8F5;--white:#FFF;--blush:#F2E8E4;--rose:#C9897A;--rose-deep:#A86556;--muted:#9B8F8A;--dark:#2C2320;--border:#E8DDD9;--shadow:rgba(44,35,32,.08);}
[data-theme="dark"]{--cream:#000;--white:#1C1C1E;--blush:#2C2C2E;--rose:#E0997F;--rose-deep:#F0AC94;--muted:#8E8E93;--dark:#F2F2F7;--border:#38383A;--shadow:rgba(0,0,0,.4);}
body,.hdr,.card,.tab-bar,.bub,.pill,.mtab,.msel,.minp,.ci,.theme-toggle{transition:background-color .2s ease,color .2s ease,border-color .2s ease;}
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
.hdr-right{display:flex;align-items:center;gap:10px;}
.theme-toggle{width:36px;height:36px;border-radius:50%;border:1px solid var(--border);background:var(--blush);display:flex;align-items:center;justify-content:center;font-size:14px;cursor:pointer;color:var(--rose-deep);flex-shrink:0;}
.avatar-slot{position:relative;width:44px;height:36px;cursor:pointer;}
.avatar-img{width:36px;height:36px;border-radius:50%;object-fit:cover;position:absolute;bottom:0;left:4px;border:1px solid var(--border);}
.avatar-del{position:absolute;top:-4px;right:-4px;width:16px;height:16px;border-radius:50%;background:var(--rose-deep);color:#fff;font-size:11px;line-height:16px;text-align:center;cursor:pointer;}
.tdiv{text-align:center;font-size:11px;color:var(--muted);margin:18px 0 12px;}
.status-card{padding:16px;}
.status-top{display:flex;align-items:center;gap:14px;margin-bottom:18px;}
.status-avatar-lg{width:64px;height:64px;flex-shrink:0;position:relative;display:flex;align-items:center;justify-content:center;overflow:visible;}
.status-avatar-lg .cat{transform:scale(2.3);cursor:pointer;}
.avatar-img-lg{width:64px;height:64px;border-radius:50%;object-fit:cover;border:1px solid var(--border);cursor:pointer;}
.status-line{flex:1;font-size:13px;color:var(--dark);font-style:italic;line-height:1.5;}
.mood-row{display:flex;align-items:center;gap:8px;margin-bottom:9px;font-size:11px;color:var(--muted);}
.mood-label{width:56px;flex-shrink:0;}
.mood-track{flex:1;height:6px;background:var(--blush);border-radius:3px;overflow:hidden;}
.mood-fill{height:100%;background:var(--rose);border-radius:3px;transition:width .5s ease;}
.mood-val{width:30px;text-align:right;flex-shrink:0;font-variant-numeric:tabular-nums;}
.msg-row{display:flex;gap:6px;align-items:flex-end;}
.msg.anna .msg-row{flex-direction:row-reverse;}
.msg-avatar{width:26px;height:26px;border-radius:50%;flex-shrink:0;object-fit:cover;display:flex;align-items:center;justify-content:center;font-size:13px;background:var(--blush);color:var(--rose-deep);border:1px solid var(--border);}
.think-toggle{font-size:10px;color:var(--muted);margin-bottom:4px;cursor:pointer;opacity:.75;display:inline-flex;align-items:center;gap:3px;}
.think-toggle:active{opacity:1;}
.think-box{font-size:12px;line-height:1.65;color:var(--muted);background:var(--blush);border-radius:12px;padding:10px 12px;margin-bottom:6px;max-width:78%;white-space:pre-line;}
.mstar{font-size:9px;letter-spacing:1px;}
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
.img-preview-bar{display:flex;align-items:center;gap:8px;padding:8px 16px;background:var(--white);border-top:1px solid var(--border);}
.img-preview-thumb{width:40px;height:40px;border-radius:8px;object-fit:cover;border:1px solid var(--border);}
.img-preview-label{flex:1;font-size:12px;color:var(--muted);}
.img-preview-btn{border:none;border-radius:14px;padding:5px 12px;font-size:12px;cursor:pointer;}
.img-preview-cancel{background:var(--blush);color:var(--muted);}
.img-preview-send{background:var(--rose);color:#fff;}
.clabel{text-align:center;font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin-bottom:16px;}
.msg{margin-bottom:14px;display:flex;flex-direction:column;}
.msg.grouped{margin-bottom:3px;}
.msg.anna{align-items:flex-end;}.msg.lin{align-items:flex-start;}
.bub{max-width:78%;padding:10px 14px;border-radius:18px;font-size:14px;line-height:1.5;}
.msg.lin .bub{background:var(--white);color:var(--dark);border:1px solid var(--border);border-bottom-left-radius:4px;box-shadow:0 1px 6px var(--shadow);}
.msg.anna .bub{background:var(--rose);color:white;border-bottom-right-radius:4px;}
.mtime2{font-size:10px;color:var(--muted);margin-top:3px;}
.typing{display:inline-flex;gap:4px;padding:12px 14px;background:var(--white);border:1px solid var(--border);border-radius:18px;border-bottom-left-radius:4px;}
.td{width:5px;height:5px;background:var(--muted);border-radius:50%;animation:tda 1.2s infinite;}
.td:nth-child(2){animation-delay:.2s}.td:nth-child(3){animation-delay:.4s}
@keyframes tda{0%,60%,100%{transform:translateY(0)}30%{transform:translateY(-5px)}}


/* 经期记录样式 - 参考图2的粉红渐变配色 */
.period-card { background: linear-gradient(180deg, #E8C4BC 0%, #F5E8E4 100%); }
.period-month-header { 
  display: flex; 
  align-items: center; 
  justify-content: space-between; 
  padding: 12px 20px;
  background: var(--white);
  border-radius: 12px;
  margin-bottom: 12px;
}
.period-month-title { 
  font-size: 18px; 
  font-weight: 600; 
  color: var(--dark);
}
.month-nav { 
  width: 36px; 
  height: 36px; 
  border: none; 
  background: var(--blush); 
  border-radius: 50%; 
  cursor: pointer;
  font-size: 16px;
  color: var(--rose-deep);
  display: flex;
  align-items: center;
  justify-content: center;
}
.month-nav:hover { background: var(--rose); color: #FFF; }
.period-calendar { 
  display: grid; 
  grid-template-columns: repeat(7, 1fr); 
  gap: 8px; 
  margin: 16px 0; 
  padding: 12px;
  background: var(--white);
  border-radius: 12px;
}
.calendar-day { 
  aspect-ratio: 1; 
  display: flex; 
  align-items: center; 
  justify-content: center; 
  border-radius: 12px; 
  font-size: 14px; 
  color: var(--dark);
  cursor: pointer;
  transition: all .2s;
}
.calendar-day.selected { 
  border: 2px solid #D4A5A5; 
  background: transparent;
}
.calendar-day:hover { background: var(--blush); }
.calendar-day.recorded { background: #E89A9A; color: #FFF; }
.calendar-day.predicted { background: #F5C6C6; color: var(--dark); }
.calendar-day.fertile { background: #B8A4E8; color: #FFF; }
.calendar-day.today { border: 2px solid var(--rose); }
.period-legend { 
  display: flex; 
  gap: 16px; 
  justify-content: center; 
  margin: 12px 0; 
  font-size: 12px;
  color: var(--muted);
}
.legend-item { display: flex; align-items: center; gap: 6px; }
.legend-dot { 
  width: 12px; 
  height: 12px; 
  border-radius: 50%; 
}
.legend-dot.recorded { background: #E89A9A; }
.legend-dot.predicted { background: #F5C6C6; }
.legend-dot.fertile { background: #B8A4E8; }
.period-input-box { 
  display: flex; 
  gap: 12px; 
  margin: 16px 0; 
  justify-content: center;
}
.period-date-input { 
  padding: 10px 14px; 
  border: 1px solid var(--border); 
  border-radius: 8px; 
  font-size: 14px;
  background: var(--white);
  color: var(--dark);
}
.period-btn { 
  padding: 10px 20px; 
  background: var(--rose); 
  color: #FFF; 
  border: none; 
  border-radius: 8px; 
  cursor: pointer;
  font-size: 14px;
  transition: background .2s;
}
.period-btn:hover { background: var(--rose-deep); }
.period-prediction { 
  margin-top: 16px; 
  padding: 16px; 
  background: var(--white); 
  border-radius: 12px;
  font-size: 15px;
  line-height: 1.8;
  color: var(--dark);
}
.period-prediction .big-text {
  font-size: 28px;
  font-weight: 600;
  color: #D4718B;
  margin: 12px 0;
}
/* 移动端适配 - 针对小屏幕优化 */
@media (max-width: 768px) {
  body { font-size: 14px; }
  .hdr { padding: 10px 16px !important; font-size: 16px !important; }
  .card { margin: 12px 12px !important; padding: 16px !important; }
  .mood-row { font-size: 13px !important; }
  .mood-label { min-width: 60px !important; }
  .bub { max-width: 85% !important; font-size: 13px !important; padding: 9px 12px !important; }
  .think-box { font-size: 11px !important; max-width: 85% !important; }
  .ci { padding: 10px 12px !important; font-size: 14px !important; }
  .pill { padding: 4px 10px !important; font-size: 11px !important; }
  .tab-bar button { font-size: 12px !important; padding: 8px !important; }
  .mtab { padding: 8px 14px !important; font-size: 13px !important; }
}
@media (max-width: 480px) {
  .card { margin: 10px 8px !important; padding: 12px !important; }
  .mood-row { font-size: 12px !important; }
  .bub { max-width: 90% !important; }
  .ci { font-size: 13px !important; }
}
</style>
</head>
<body>
<div class="hdr">
  <div class="cat-wrap">
    <div class="avatar-slot" id="avatarSlot" onclick="pickAvatar()">
      <div class="cat" id="catIcon">
        <div class="cat-head"><div class="cat-ear-l"></div><div class="cat-ear-r"></div><div class="cat-eye-l"></div><div class="cat-eye-r"></div><div class="cat-nose"></div></div>
        <div class="cat-body"><div class="cat-tail"></div></div>
      </div>
      <img id="avatarImg" class="avatar-img" style="display:none">
      <div class="avatar-del" id="avatarDel" onclick="removeAvatar(event)" style="display:none">×</div>
    </div>
    <input type="file" id="avatarFile" accept="image/*" style="display:none">
    <div class="hdr-txt"><h1>Lin</h1><p>正在看著妳</p></div>
  </div>
  <div class="hdr-right">
    <button class="theme-toggle" id="themeToggle" onclick="toggleTheme()">🌙</button>
    <div class="pill"><div class="dot"></div>在線</div>
  </div>
</div>

<div class="pg active" id="pg-monitor">
  <div class="card status-card">
    <div class="status-top">
      <div class="status-avatar-lg" id="statusAvatarLg" onclick="pickAvatar('lin')">
        <div class="cat" id="catIconLg">
          <div class="cat-head"><div class="cat-ear-l"></div><div class="cat-ear-r"></div><div class="cat-eye-l"></div><div class="cat-eye-r"></div><div class="cat-nose"></div></div>
          <div class="cat-body"><div class="cat-tail"></div></div>
        </div>
        <img id="avatarImgLg" class="avatar-img-lg" style="display:none" onclick="pickAvatar('lin')">
      </div>
      <div class="status-line" id="statusLine">在等妳的消息</div>
    </div>
    <div id="moodBars"></div>
  </div>
  <div class="card"><div class="cl">今日 API 配額</div><div class="qb"><span>0</span><div class="qt"><div class="qf" id="qf" style="width:0%"></div></div><span id="qt">180 次</span></div></div>
  <div class="card"><div class="cl">實時監控日誌</div><div id="lc"><div class="es">📡 等待監控觸發...</div></div></div>
  <div class="card"><div class="cl">今日碎碎念</div><div id="nc"><div class="es">🖤 今天還沒寫</div></div></div>
  <div class="wm">Property of Lin · <span id="ctime"></span></div>
</div>

<div class="pg" id="pg-chat">
  <div class="cms" id="cm"><div class="clabel">with Lin</div></div>
  <div class="img-preview-bar" id="imgPreviewBar" style="display:none">
    <img id="imgPreviewThumb" class="img-preview-thumb">
    <span class="img-preview-label">已選擇圖片</span>
    <button class="img-preview-btn img-preview-cancel" onclick="cancelImagePreview()">✕</button>
  </div>
  <div class="ciw">
    <input type="file" id="chatImageUpload" accept="image/*" style="display:none">
    <button class="sb" onclick="document.getElementById('chatImageUpload').click()" style="background:var(--blush);color:var(--rose-deep);">📎</button>
    <input type="text" class="ci" id="ci" placeholder="跟主人說話...">
    <button class="sb" onclick="send()">↑</button>
  </div>
</div>

<div class="pg" id="pg-memory">
  <div class="mtabs">
    <div class="mtab active" onclick="smtab(event,'lt')">長期記憶</div>
    <div class="mtab" onclick="smtab(event,'st')">短期記憶</div>
    <div class="mtab" onclick="smtab(event,'rl')">Relationship</div>
    <div class="mtab" onclick="smtab(event,'rf')">Reflection</div>
    <div class="mtab" onclick="smtab(event,'ar')">Archive</div>
  </div>
  <div class="ms active" id="ms-lt"></div>
  <div class="ms" id="ms-st"></div>
  <div class="ms" id="ms-rl"></div>
  <div class="ms" id="ms-rf"></div>
  <div class="ms" id="ms-ar"></div>
  <div class="card" id="mem-add-card"><div class="cl">新增記憶</div>
    <div class="maw">
      <select class="msel" id="mtag">
        <option value="长期记忆">長期記憶</option>
        <option value="短期记忆">短期記憶</option>
        <option value="Relationship">Relationship</option>
        <option value="Reflection">Reflection</option>
      </select>
      <textarea class="minp" id="mcontent" placeholder="輸入記憶內容..."></textarea>
      <button class="msave" onclick="saveMem()">💾 儲存記憶</button>
    </div>
  </div>
</div>


<div class="pg" id="pg-mine">
  <div class="card period-card">
    <div class="cl">📅 经期记录</div>
    <div class="period-month-header">
      <button class="month-nav" onclick="changeMonth(-1)">❮</button>
      <div id="period-month-title" class="period-month-title">2026年7月</div>
      <button class="month-nav" onclick="changeMonth(1)">❯</button>
    </div>
    <div id="period-calendar" class="period-calendar"></div>
    <div class="period-legend">
      <span class="legend-item"><span class="legend-dot recorded"></span>已记录</span>
      <span class="legend-item"><span class="legend-dot predicted"></span>预测</span>
      <span class="legend-item"><span class="legend-dot fertile"></span>易孕期/排卵</span>
    </div>

    <div id="period-prediction" class="period-prediction"></div>
  </div>
</div>

<div class="tab-bar">
  <button class="tb active" id="tb-monitor" onclick="stab('monitor')"><span class="ti">🏠</span>Home</button>
  <button class="tb" id="tb-chat" onclick="stab('chat')"><span class="ti">💬</span>Chat</button>
  <button class="tb" id="tb-memory" onclick="stab('memory')"><span class="ti">🧠</span>Memory</button>
  <button class="tb" id="tb-mine" onclick="stab('mine')"><span class="ti">🌙</span>Mine</button>
</div>

<script>
const AU = window.location.origin;
const CK = 'lin_chat_v1';

function ts(){const n=new Date();return n.getHours().toString().padStart(2,'0')+':'+n.getMinutes().toString().padStart(2,'0');}
function utime(){document.getElementById('ctime').textContent=ts();}
utime();setInterval(utime,60000);

// ---------- 深色模式 ----------
function applyTheme(mode){
  document.documentElement.setAttribute('data-theme', mode);
  const meta=document.getElementById('theme-color-meta');
  if(meta) meta.setAttribute('content', mode==='dark' ? '#000000' : '#C9897A');
  const btn=document.getElementById('themeToggle');
  if(btn) btn.textContent = mode==='dark' ? '☀️' : '🌙';
}
function toggleTheme(){
  const cur=document.documentElement.getAttribute('data-theme')||'light';
  const next=cur==='dark'?'light':'dark';
  localStorage.setItem('lin_theme', next);
  applyTheme(next);
}
applyTheme(document.documentElement.getAttribute('data-theme')||'light');

// ---------- 头像（Lin + Anna 两组） ----------
let linAvatarUrl = null;
let annaAvatarUrl = null;
let pendingAvatarWho = 'lin';
let pendingImageDataUrl = null;

function pickAvatar(who){ pendingAvatarWho = who || 'lin'; document.getElementById('avatarFile').click(); }

function applyAvatar(who, dataUrl){
  if(who==='anna'){
    annaAvatarUrl = dataUrl;
  }else{
    linAvatarUrl = dataUrl;
    const img=document.getElementById('avatarImg');
    const cat=document.getElementById('catIcon');
    const del=document.getElementById('avatarDel');
    const imgLg=document.getElementById('avatarImgLg');
    const catLg=document.getElementById('catIconLg');
    if(dataUrl){
      img.src=dataUrl;img.style.display='block';cat.style.display='none';del.style.display='block';
      imgLg.src=dataUrl;imgLg.style.display='block';catLg.style.display='none';
    }else{
      img.style.display='none';cat.style.display='block';del.style.display='none';
      imgLg.style.display='none';catLg.style.display='block';
    }
  }
  lchat(); // 头像变了，重画一次聊天记录让气泡头像同步
}

function resizeImage(file,size){
  return new Promise((resolve,reject)=>{
    const reader=new FileReader();
    reader.onload=(e)=>{
      const img=new Image();
      img.onload=()=>{
        const canvas=document.createElement('canvas');
        canvas.width=size;canvas.height=size;
        const ctx=canvas.getContext('2d');
        const s=Math.min(img.width,img.height);
        const sx=(img.width-s)/2, sy=(img.height-s)/2;
        ctx.drawImage(img,sx,sy,s,s,0,0,size,size);
        resolve(canvas.toDataURL('image/jpeg',0.85));
      };
      img.onerror=reject;
      img.src=e.target.result;
    };
    reader.onerror=reject;
    reader.readAsDataURL(file);
  });
}

document.getElementById('avatarFile').addEventListener('change', async (e)=>{
  const file=e.target.files[0];
  if(!file)return;
  try{
    const dataUrl=await resizeImage(file,200);
    await fetch(AU+'/avatar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({data:dataUrl,who:pendingAvatarWho})});
    applyAvatar(pendingAvatarWho,dataUrl);
  }catch(err){}
  e.target.value='';
});

async function removeAvatar(ev){
  ev.stopPropagation();
  try{ await fetch(AU+'/avatar?who=lin',{method:'DELETE'}); }catch(e){}
  applyAvatar('lin',null);
}

(async function loadAvatars(){
  try{
    const r=await fetch(AU+'/avatar?who=lin');const d=await r.json();
    if(d.avatar) applyAvatar('lin',d.avatar);
  }catch(e){}
  try{
    const r2=await fetch(AU+'/avatar?who=anna');const d2=await r2.json();
    if(d2.avatar) annaAvatarUrl=d2.avatar;
  }catch(e){}
})();

// ---------- 状态面板 ----------
const MOOD_LABELS = {attachment:'依戀',possessiveness:'佔有欲',curiosity:'好奇',social:'社交欲',libido:'性慾',fatigue:'疲憊感',stress:'壓力'};

async function loadMood(){
  try{
    const r=await fetch(AU+'/mood');const d=await r.json();
    renderMood(d.mood);
  }catch(e){}
}

function renderMood(mood){
  if(!mood)return;
  const line=document.getElementById('statusLine');
  if(line)line.textContent = mood.line || '在想妳';
  const wrap=document.getElementById('moodBars');
  if(!wrap)return;
  let html='';
  Object.keys(MOOD_LABELS).forEach(key=>{
    const val = mood[key]!=null ? mood[key] : 0.5;
    const pct = Math.max(0,Math.min(100,Math.round(val*100)));
    html+='<div class="mood-row"><div class="mood-label">'+MOOD_LABELS[key]+'</div><div class="mood-track"><div class="mood-fill" style="width:'+pct+'%"></div></div><div class="mood-val">'+val.toFixed(2)+'</div></div>';
  });
  wrap.innerHTML=html;
}
loadMood();

// ---------- PWA ----------
if('serviceWorker' in navigator){
  window.addEventListener('load', ()=>{ navigator.serviceWorker.register('/sw.js').catch(()=>{}); });
}


function stab(tab){
  document.querySelectorAll('.tb').forEach(e=>e.classList.remove('active'));
  document.getElementById('tb-'+tab).classList.add('active');
  document.querySelectorAll('.pg').forEach(e=>{e.style.display='none';e.classList.remove('active');});
  const pg=document.getElementById('pg-'+tab);
  if(tab==='chat'){pg.style.display='flex';pg.classList.add('active');setTimeout(()=>{const c=document.getElementById('cm');c.scrollTop=c.scrollHeight;},50);}
  else{pg.style.display='block';pg.classList.add('active');if(tab==='memory')rmem();if(tab==='monitor')loadMood();if(tab==='mine')loadPeriod();}
}
// 页面加载时如果是Mine tab,立即展开
if(document.getElementById('pg-mine')?.classList.contains('active'))loadPeriod();

function toggleThink(el){
  const box=el.nextElementSibling;
  const open=box.style.display!=='none';
  box.style.display=open?'none':'block';
  el.textContent=open?'💭 查看思考過程':'💭 收起思考過程';
}

// ---------- 聊天消息渲染：日期分隔线、连续消息分组、已读状态、雙方頭像、可收合思考 ----------
function fmtDivider(d){
  const now=new Date();
  const hh=d.getHours().toString().padStart(2,'0');
  const mm=d.getMinutes().toString().padStart(2,'0');
  let day;
  if(d.toDateString()===now.toDateString()){day='今天';}
  else{
    const y=new Date(now);y.setDate(y.getDate()-1);
    day = d.toDateString()===y.toDateString() ? '昨天' : (d.getMonth()+1)+'月'+d.getDate()+'日';
  }
  return day+' '+hh+':'+mm;
}

function avatarHtml(role){
  if(role==='anna'){
    return annaAvatarUrl
      ? '<img class="msg-avatar" src="'+annaAvatarUrl+'" onclick="pickAvatar(\\'anna\\')">'
      : '<div class="msg-avatar" onclick="pickAvatar(\\'anna\\')">🙂</div>';
  }
  return linAvatarUrl
    ? '<img class="msg-avatar" src="'+linAvatarUrl+'">'
    : '<div class="msg-avatar">🐈</div>';
}

function renderMessages(history){
  console.log('[DEBUG] 🔄 renderMessages called, history.length:', history ? history.length : 0);
  if(history && history.length > 0){
    const lastMsg = history[history.length - 1];
    console.log('[DEBUG] Last message:', lastMsg);
  }
  const cm=document.getElementById('cm');
  if(!history||history.length===0){
    cm.innerHTML='<div class="clabel">with Lin</div><div class="msg lin"><div class="msg-row">'+avatarHtml('lin')+'<div class="bub">打開了？</div></div><div class="mtime2">'+ts()+'</div></div>';
    cm.scrollTop=cm.scrollHeight;
    return;
  }
  let html='<div class="clabel">with Lin</div>';
  history.forEach((m,i)=>{
    const cur=m.iso?new Date(m.iso):new Date();
    const prev=i>0?history[i-1]:null;
    const prevTime=prev&&prev.iso?new Date(prev.iso):null;
    if(!prevTime||(cur-prevTime)>30*60*1000){html+='<div class="tdiv">'+fmtDivider(cur)+'</div>';}
    const next=i<history.length-1?history[i+1]:null;
    const nextTime=next&&next.iso?new Date(next.iso):null;
    const showMeta = !next || next.r!==m.r || (nextTime && (nextTime-cur)>5*60*1000);
    let meta='';
    if(showMeta){
      const read = m.r==='anna' && history.slice(i+1).some(x=>x.r==='lin');
      meta='<div class="mtime2">'+m.time+(read?' · 已讀':'')+'</div>';
    }
    let thinkHtml='';
    if(m.r==='lin' && m.think){
      thinkHtml='<div class="think-toggle" onclick="toggleThink(this)">💭 查看思考過程</div><div class="think-box" style="display:none">'+m.think+'</div>';
    }
    html+='<div class="msg '+m.r+(showMeta?'':' grouped')+'">'+thinkHtml+'<div class="msg-row">'+avatarHtml(m.r)+'<div class="bub">'+m.t+'</div></div>'+meta+'</div>';
  });
  cm.innerHTML=html;
  cm.scrollTop=cm.scrollHeight;
  const msgDivs = cm.querySelectorAll('.msg.lin');
  console.log('[DEBUG] After renderMessages, .msg.lin count:', msgDivs.length);
}

function lchat(){
  renderMessages(JSON.parse(localStorage.getItem(CK)||'[]'));
}

async function syncChat(){
  // 跨装置同步：从 Supabase 共享的聊天记录覆盖本地 localStorage，
  // 这样手机 dock / 电脑 dock / 网页版打开时看到的是同一份对话，不是各自锁死的本地缓存。
  // 失败（离线/后端没起来）就安静地退回原本的 localStorage 内容，不影响原有体验。
  try{
    const r = await fetch(AU+'/conversation');
    const d = await r.json();
    if(d && Array.isArray(d.messages)){
      localStorage.setItem(CK, JSON.stringify(d.messages));
    }
  }catch(e){
    console.error('[syncChat] 同步聊天记录失败，先显示本地缓存:', e);
  }
  lchat();
}

function smsg(role,text,think){
  const h=JSON.parse(localStorage.getItem(CK)||'[]');
  const entry = {r:role,t:text,time:ts(),iso:new Date().toISOString()};
  if(think) entry.think = think;
  h.push(entry);
  if(h.length>200)h.splice(0,h.length-200);
  localStorage.setItem(CK,JSON.stringify(h));
  return h;
}



function addMsg(role, text, think) {
  smsg(role, text, think);
  lchat();
}

function typing(show) {
  const cm = document.getElementById('cm');
  let typingDiv = cm.querySelector('.typing');
  if (show && !typingDiv) {
    typingDiv = document.createElement('div');
    typingDiv.className = 'typing';
    typingDiv.innerHTML = '<span class="td"></span><span class="td"></span><span class="td"></span>';
    cm.appendChild(typingDiv);
    cm.scrollTop = cm.scrollHeight;
  } else if (!show && typingDiv) {
    typingDiv.remove();
  }
}

function scrollDown() {
  const cm = document.getElementById('cm');
  if (cm) cm.scrollTop = cm.scrollHeight;
}

function ftime() {
  const now = new Date();
  const h = now.getHours().toString().padStart(2, '0');
  const m = now.getMinutes().toString().padStart(2, '0');
  return h + ':' + m;
}


// 聊天圖片上傳處理
document.getElementById('chatImageUpload').addEventListener('change', async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  
  try {
    const dataUrl = await resizeImage(file, 800);
    pendingImageDataUrl = dataUrl;
    
    // 顯示預覽
    document.getElementById('imgPreviewThumb').src = dataUrl;
    document.getElementById('imgPreviewBar').style.display = 'flex';
  } catch(e) {
    console.error('Image preview error:', e);
  }
});

// 取消圖片預覽
function cancelImagePreview() {
  pendingImageDataUrl = null;
  document.getElementById('imgPreviewBar').style.display = 'none';
  document.getElementById('chatImageUpload').value = '';
}

// 確認送出圖片
async function confirmImageSend() {
  if (!pendingImageDataUrl) return;
  
  const base64 = pendingImageDataUrl.split(',')[1];
  const inp = document.getElementById('ci');
  const txt = inp.value.trim();
  inp.value = '';
  
  // 隱藏預覽列
  document.getElementById('imgPreviewBar').style.display = 'none';
  document.getElementById('chatImageUpload').value = '';
  
  addMsg('anna', txt ? ('[圖片] ' + txt) : '[圖片]');
  typing(true);
  
  try {
    const response = await fetch(AU + '/watch', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({activity: txt || '看圖片', image: base64})
    });
    
    if (!response.ok) throw new Error('Upload failed');
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    let reasoningBuffer = '';
    let contentBuffer = '';
    let currentMsgDiv = null;
    let thinkDiv = null;
    let currentEvent = null;
    let sseBuffer = '';
    
    typing(false);
    
    function processChunk({done, value}) {
      if (done) {
        if (contentBuffer) {
          smsg('lin', contentBuffer, reasoningBuffer || null);
        }
        scrollDown();
        pendingImageDataUrl = null;
        return;
      }
      
      const chunk = decoder.decode(value, {stream: true});
      sseBuffer += chunk;
      const lines = sseBuffer.split('\\n');
      sseBuffer = lines.pop();
      
      for (let line of lines) {
        if (!line.trim() || line.startsWith(': ping')) continue;
        
        if (line.startsWith('event:')) {
          currentEvent = line.slice(7).trim();
          continue;
        }
        
        if (line.startsWith('data:')) {
          try {
            const data = JSON.parse(line.slice(6));
            
            if (currentEvent === 'reasoning' && data.content !== undefined) {
              reasoningBuffer += data.content;
              
              if (!thinkDiv) {
                const msgDiv = document.createElement('div');
                msgDiv.className = 'msg lin';
                
                thinkDiv = document.createElement('div');
                thinkDiv.className = 'think-box';
                thinkDiv.textContent = reasoningBuffer;
                
                const toggle = document.createElement('div');
                toggle.className = 'think-toggle';
                toggle.innerHTML = '💭 思考過程';
                toggle.onclick = () => {
                  thinkDiv.style.display = thinkDiv.style.display==='none'?'block':'none';
                };
                
                msgDiv.appendChild(toggle);
                msgDiv.appendChild(thinkDiv);
                document.getElementById('cm').appendChild(msgDiv);
              } else {
                thinkDiv.textContent = reasoningBuffer;
              }
              scrollDown();
            }
            
            else if (currentEvent === 'content' && data.delta !== undefined) {
              contentBuffer += data.delta;
              
              if (!currentMsgDiv) {
                const msgDiv = document.createElement('div');
                msgDiv.className = 'msg lin';
                
                const rowDiv = document.createElement('div');
                rowDiv.className = 'msg-row';
                rowDiv.innerHTML = avatarHtml('lin');
                
                const bubDiv = document.createElement('div');
                bubDiv.className = 'bub';
                bubDiv.textContent = contentBuffer;
                
                rowDiv.appendChild(bubDiv);
                msgDiv.appendChild(rowDiv);
                document.getElementById('cm').appendChild(msgDiv);
                console.log('[DEBUG] Content msgDiv appended to #cm');
                
                currentMsgDiv = bubDiv;
              } else {
                currentMsgDiv.textContent = contentBuffer;
              }
              scrollDown();
            }
            
            else if (currentEvent === 'error') {
              typing(false);
              if (data.message) {
                addMsg('lin', data.message);
              }
            }
            
          } catch(e) {
            console.error('Parse SSE error:', e, line);
          }
        }
      }
      
      reader.read().then(processChunk);
    }
    
    reader.read().then(processChunk);
    
  } catch(e) {
    typing(false);
    addMsg('lin', '圖片上傳失敗');
    console.error('Image send error:', e);
  } finally {
    pendingImageDataUrl = null;
  }
}

async function send(){
  if (pendingImageDataUrl) return confirmImageSend();

  const inp=document.getElementById('ci');
  let txt=inp.value.trim();
  if(!txt)return;
  inp.value='';
  addMsg('anna',txt);
  typing(true);
  
  try{
    const response = await fetch(AU+'/watch', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({activity: txt})
    });
    
    if(!response.ok) throw new Error('Network error');
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    let reasoningBuffer = '';
    let contentBuffer = '';
    let currentMsgDiv = null;
    let thinkDiv = null;
    let currentEvent = null;
    let sseBuffer = '';
    
    typing(false);
    
    function processChunk({done, value}){
      console.log('[DEBUG] processChunk called, done:', done);
      if(done){
        console.log('[DEBUG] Stream done. contentBuffer:', contentBuffer, 'reasoningBuffer:', reasoningBuffer);
        if(contentBuffer){
          smsg('lin', contentBuffer, reasoningBuffer || null);
        }
        scrollDown();
        return;
      }
      
      const chunk = decoder.decode(value, {stream: true});
      sseBuffer += chunk;
      const lines = sseBuffer.split('\\n');
      sseBuffer = lines.pop();
      
      for(let line of lines){
        if(!line.trim() || line.startsWith(': ping')) continue;
        
        if(line.startsWith('event:')){
          currentEvent = line.slice(7).trim();
          continue;
        }
        
        if(line.startsWith('data:')){
          try{
            const data = JSON.parse(line.slice(6));
            
            if(currentEvent === 'reasoning' && data.content !== undefined){
              console.log('[DEBUG] ✅ REASONING event received, data.content:', data.content);
              reasoningBuffer += data.content;
              
              if(!thinkDiv){
                console.log('[DEBUG] Creating thinking msgDiv');
                const msgDiv = document.createElement('div');
                msgDiv.className = 'msg lin';
                
                thinkDiv = document.createElement('div');
                thinkDiv.className = 'think-box';
                thinkDiv.textContent = reasoningBuffer;
                
                const toggle = document.createElement('div');
                toggle.className = 'think-toggle';
                toggle.innerHTML = '💭 思考過程';
                toggle.onclick = () => {
                  thinkDiv.style.display = thinkDiv.style.display==='none'?'block':'none';
                };
                
                msgDiv.appendChild(toggle);
                msgDiv.appendChild(thinkDiv);
                document.getElementById('cm').appendChild(msgDiv);
              } else {
                thinkDiv.textContent = reasoningBuffer;
              }
              scrollDown();
            }
            
            else if(currentEvent === 'content' && data.delta !== undefined){
              console.log('[DEBUG] ✅ CONTENT event received, data.delta:', data.delta);
              contentBuffer += data.delta;
              
              if(!currentMsgDiv){
                console.log('[DEBUG] Creating content msgDiv');
                const msgDiv = document.createElement('div');
                msgDiv.className = 'msg lin';
                
                const rowDiv = document.createElement('div');
                rowDiv.className = 'msg-row';
                rowDiv.innerHTML = avatarHtml('lin');
                
                const bubDiv = document.createElement('div');
                bubDiv.className = 'bub';
                bubDiv.textContent = contentBuffer;
                
                rowDiv.appendChild(bubDiv);
                msgDiv.appendChild(rowDiv);
                document.getElementById('cm').appendChild(msgDiv);
                
                currentMsgDiv = bubDiv;
              } else {
                currentMsgDiv.textContent = contentBuffer;
              }
              scrollDown();
            }
            
            else if(currentEvent === 'error'){
              typing(false);
              if(data.message){
                addMsg('lin', data.message);
              }
            }
            
          }catch(e){
            console.error('Parse SSE error:', e, line);
          }
        }
      }
      
      reader.read().then(processChunk);
    }
    
    reader.read().then(processChunk);
    
  }catch(e){
    typing(false);
    addMsg('lin', '網絡錯誤');
    console.error('Send error:', e);
  }
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

const TM={'长期记忆':'lt','短期记忆':'st','Relationship':'rl','Reflection':'rf'};
const MEMORY_TAB_IDS=['lt','st','rl','rf'];

function smtab(ev,tab){
  document.querySelectorAll('.mtab').forEach(e=>e.classList.remove('active'));
  ev.target.classList.add('active');
  document.querySelectorAll('.ms').forEach(e=>e.classList.remove('active'));
  document.getElementById('ms-'+tab).classList.add('active');
  const addCard=document.getElementById('mem-add-card');
  if(tab==='ar'){ addCard.style.display='none'; rarchive(); }
  else{ addCard.style.display='block'; rmem(); }
}

async function rmem(){
  let mems=[];
  try{
    const r=await fetch(AU+'/memory');const d=await r.json();
    mems=d.memories||[];
  }catch(e){}
  MEMORY_TAB_IDS.forEach(id=>{document.getElementById('ms-'+id).innerHTML='';});
  mems.slice().reverse().forEach(m=>{
    const sid=TM[m.category]||'lt';
    const el=document.getElementById('ms-'+sid);
    const stars=m.importance?'⭐'.repeat(m.importance):'';
    if(el)el.innerHTML+='<div class="mi"><div class="mit">🏷 '+(m.tag||m.category)+(stars?' <span class="mstar">'+stars+'</span>':'')+'</div><div>'+m.content+'</div><div class="mtime">'+m.time+'</div><button class="mdel" onclick="delmem('+m.id+')">删除</button></div>';
  });
  MEMORY_TAB_IDS.forEach(id=>{const el=document.getElementById('ms-'+id);if(el&&el.innerHTML==='')el.innerHTML='<div class="es">這裡還沒有記憶</div>';});
}

async function rarchive(){
  const el=document.getElementById('ms-ar');
  el.innerHTML='<div class="es">載入中...</div>';
  try{
    const r=await fetch(AU+'/logs');const d=await r.json();
    let html='';
    if(d.notes&&d.notes.length>0){
      html+='<div class="mit" style="padding:10px 4px 4px">📔 日記</div>';
      html+=[...d.notes].reverse().map(n=>'<div class="mi"><div>'+n.content+'</div><div class="mtime">'+n.time+'</div></div>').join('');
    }
    const pushLogs=(d.logs||[]).filter(l=>l.type&&l.type.indexOf('推送')>=0);
    if(pushLogs.length>0){
      html+='<div class="mit" style="padding:10px 4px 4px">🔔 Bark 推送記錄</div>';
      html+=[...pushLogs].reverse().map(l=>'<div class="mi"><div>'+l.content+'</div><div class="mtime">'+l.time+'</div></div>').join('');
    }
    el.innerHTML = html || '<div class="es">還沒有日記或推送記錄</div>';
  }catch(e){
    el.innerHTML='<div class="es">載入失敗</div>';
  }
}

async function saveMem(){
  const category=document.getElementById('mtag').value;
  const content=document.getElementById('mcontent').value.trim();
  if(!content)return;
  document.getElementById('mcontent').value='';
  await fetch(AU+'/memory',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({category,content})});
  rmem();
}

async function delmem(id){
  await fetch(AU+'/memory/'+id,{method:'DELETE'});
  rmem();
}

syncChat();llogs();setInterval(()=>{llogs();if(document.getElementById('tb-monitor').classList.contains('active'))loadMood();},10000);

// ========== 经期记录功能 ==========
let periodData = { records: [], cycle: 28 };
let currentYear = new Date().getFullYear();
let currentMonth = new Date().getMonth();


function changeMonth(delta) {
  currentMonth += delta;
  if (currentMonth > 11) {
    currentMonth = 0;
    currentYear++;
  } else if (currentMonth < 0) {
    currentMonth = 11;
    currentYear--;
  }
  updateMonthTitle();
  renderCalendar();
}

function updateMonthTitle() {
  const title = document.getElementById('period-month-title');
  if (title) {
    title.textContent = `${currentYear}年${currentMonth + 1}月`;
  }
}

async function loadPeriod() {
  try {
    const r = await fetch(AU + '/period');
    if (r.ok) {
      periodData = await r.json();
      updateMonthTitle();
      renderCalendar();
      updatePrediction();
    }
  } catch(e) { console.error('Load period failed:', e); }
}

function renderCalendar() {
  const cal = document.getElementById('period-calendar');
  if (!cal) return;
  
  const year = currentYear;
  const month = currentMonth;
  const now = new Date();
  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  
  let html = '';
  // 添加星期标题
  ['日','一','二','三','四','五','六'].forEach(d => {
    html += `<div class="calendar-day" style="font-weight:600;color:var(--muted);">${d}</div>`;
  });
  
  // 填充空白
  for (let i = 0; i < firstDay; i++) {
    html += '<div class="calendar-day"></div>';
  }
  
  // 渲染日期
  const today = now.getDate();
  const records = periodData.records || [];
  const predicted = predictDates();
  const fertile = predictFertile();
  
  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = `${year}-${String(month+1).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
    let cls = 'calendar-day';
    if (d === today) cls += ' today';
    if (records.includes(dateStr)) cls += ' recorded';
    else if (predicted.includes(dateStr)) cls += ' predicted';
    else if (fertile.includes(dateStr)) cls += ' fertile';
    html += `<div class="${cls}" onclick="quickRecord('${dateStr}')">${d}</div>`;
  }
  
  cal.innerHTML = html;
}

function predictDates() {
  // 根据最近一次记录预测下次日期
  const records = (periodData.records || []).sort();
  if (records.length === 0) return [];
  
  const last = new Date(records[records.length - 1]);
  const cycle = periodData.cycle || 28;
  const next = new Date(last);
  next.setDate(next.getDate() + cycle);
  
  const predicted = [];
  for (let i = 0; i < 5; i++) { // 预测5天
    const d = new Date(next);
    d.setDate(d.getDate() + i);
    predicted.push(d.toISOString().split('T')[0]);
  }
  return predicted;
}

function predictFertile() {
  // 排卵期 = 下次月经前14天左右
  const records = (periodData.records || []).sort();
  if (records.length === 0) return [];
  
  const last = new Date(records[records.length - 1]);
  const cycle = periodData.cycle || 28;
  const ovulation = new Date(last);
  ovulation.setDate(ovulation.getDate() + cycle - 14);
  
  const fertile = [];
  for (let i = -2; i <= 2; i++) { // 排卵日前后2天
    const d = new Date(ovulation);
    d.setDate(d.getDate() + i);
    fertile.push(d.toISOString().split('T')[0]);
  }
  return fertile;
}

function updatePrediction() {
  const pred = document.getElementById('period-prediction');
  if (!pred) return;
  
  const records = (periodData.records || []).sort();
  if (records.length === 0) {
    pred.innerHTML = '<div style="background:#A86556;padding:20px;border-radius:12px;"><p style="font-size:18px;font-weight:600;color:#FFF;margin:0 0 8px 0;">还没记录</p><p style="font-size:13px;color:rgba(255,255,255,0.9);margin:0;">记录最近一次开始日期后，会自动预测下次时间。</p></div>';
    return;
  }
  
  const last = new Date(records[records.length - 1]);
  const cycle = periodData.cycle || 28;
  const next = new Date(last);
  next.setDate(next.getDate() + cycle);
  
  const ovulation = new Date(next);
  ovulation.setDate(ovulation.getDate() - 14);
  
  const nextStr = next.toLocaleDateString('zh-CN', {month: 'long', day: 'numeric'});
  pred.innerHTML = `
    <p style="font-size:15px;color:var(--muted);margin-bottom:8px;">周期预测</p>
    <p class="big-text">${nextStr}</p>
    <p style="font-size:13px;color:var(--muted);">预测下次开始日期</p>
    <p style="margin-top:12px;"><strong>上次:</strong> ${last.toLocaleDateString('zh-CN')} | <strong>周期:</strong> ${cycle}天</p>
  `;
}

async function recordPeriod(date) {
  if (!date) return;
  
  try {
    // 已经记录过的日期再点一次 = 取消记录（呼叫 DELETE）
    const isRecorded = (periodData.records || []).includes(date);
    const r = await fetch(AU + '/period' + (isRecorded ? '/' + date : ''), {
      method: isRecorded ? 'DELETE' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: isRecorded ? undefined : JSON.stringify({ date })
    });
    if (r.ok) {
      await loadPeriod();
      document.querySelectorAll('.calendar-day').forEach(d => d.classList.remove('selected'));
    }
  } catch(e) {
    console.error('记录失败:', e);
  }
}

let pendingPeriodDate = null;

function quickRecord(date) {
  // 防误触：第一次点击只显示边框（选中态），不动数据库；
  // 对同一天再点一次才真的送出新增/取消。点别的日期则边框转移，不触发任何请求。
  if (pendingPeriodDate === date) {
    document.querySelectorAll('.calendar-day').forEach(d => d.classList.remove('selected'));
    pendingPeriodDate = null;
    recordPeriod(date);
  } else {
    document.querySelectorAll('.calendar-day').forEach(d => d.classList.remove('selected'));
    event.target.classList.add('selected');
    pendingPeriodDate = date;
  }
}

</script>
</body>
</html>"""
