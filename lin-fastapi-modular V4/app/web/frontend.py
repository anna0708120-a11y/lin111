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

let voiceLoadingIdx=null;
const CK='lin_audio_urls';
async function playVoice(idx){
  if(voiceLoadingIdx===idx)return; // 正在生成中，避免连点重複请求
  const m=chatMemoryCache[idx];
  if(!m||m.r!=='lin')return;
  if(m.audioUrl){
    new Audio(m.audioUrl).play().catch(()=>{});
    return;
  }
  voiceLoadingIdx=idx;
  try{
    const r=await fetch(AU+'/tts',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:m.t})});
    const d=await r.json();
    if(d.url){
      m.audioUrl=d.url;
      try{const c=JSON.parse(localStorage.getItem(CK)||'{}');c[m.message_id||m.t]=d.url;localStorage.setItem(CK,JSON.stringify(c));}catch(e){}
      new Audio(d.url).play().catch(()=>{});
    }
  }catch(e){}
  voiceLoadingIdx=null;
}

// 页面加载完成后,如果当前在Mine tab,立即加载经期数据
document.addEventListener('DOMContentLoaded', () => {
  const minePage = document.getElementById('pg-mine');
  if (minePage && minePage.classList.contains('active')) {
    loadPeriod();
  }
});

</script>
<style>
:root{--cream:#FAF8F5;--white:#FFF;--blush:#F2E8E4;--rose:#C9897A;--rose-deep:#A86556;--muted:#9B8F8A;--dark:#2C2320;--border:#E8DDD9;--shadow:rgba(44,35,32,.08);--safe-top:env(safe-area-inset-top);--safe-bottom:env(safe-area-inset-bottom);--header-height:calc(65px + var(--safe-top));--font-sans:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang TC","Noto Sans TC",sans-serif;--font-serif:Georgia,"Times New Roman","Songti TC","Noto Serif TC",serif;}
[data-theme="dark"]{--cream:#000;--white:#1C1C1E;--blush:#2C2C2E;--rose:#E0997F;--rose-deep:#F0AC94;--muted:#8E8E93;--dark:#F2F2F7;--border:#38383A;--shadow:rgba(0,0,0,.4);}
body,.hdr,.card,.tab-bar,.bub,.pill,.mtab,.msel,.minp,.ci,.theme-toggle{transition:background-color .2s ease,color .2s ease,border-color .2s ease;}
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent;}
html,body{height:100%;background:var(--cream);font-family:var(--font-sans);color:var(--dark);overflow:hidden;}
.together-card{position:relative;width:100%;height:140px;margin-bottom:16px;border-radius:20px;overflow:hidden;background:var(--blush);}
.together-bg{position:absolute;top:0;left:0;right:0;bottom:0;background-size:cover;background-position:center;opacity:0.90;}
.together-content{position:relative;z-index:1;display:flex;align-items:center;padding:20px;height:100%;}
.together-date{display:flex;flex-direction:column;align-items:center;margin-right:24px;min-width:60px;}
.together-day-num{font-size:48px;font-weight:700;line-height:1;color:var(--dark);}
.together-day-label{font-size:14px;color:var(--muted);margin-top:4px;}
.together-text{flex:1;}
.together-title{font-size:20px;font-weight:600;color:var(--dark);margin-bottom:4px;}
.together-subtitle{font-size:13px;color:var(--muted);}
.together-camera{position:absolute;top:16px;right:16px;width:40px;height:40px;border-radius:50%;background:rgba(255,255,255,0.9);display:flex;align-items:center;justify-content:center;cursor:pointer;transition:all 0.2s;}
.together-camera:hover{background:rgba(255,255,255,1);transform:scale(1.1);}
.together-camera svg{color:var(--rose-deep);}

.hdr{background:var(--white);padding:16px 20px 12px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;position:fixed;top:var(--safe-top);left:0;right:0;z-index:200;height:53px;}
.cat-wrap{display:flex;align-items:center;gap:12px;}
.pet-container{position:absolute;top:calc(140px + var(--safe-top));right:30px;z-index:10;}
.pet-container-chat{position:absolute;bottom:30px;left:20px;z-index:10;transform:scale(0.6);}

.cat{position:relative;width:44px;height:36px;cursor:pointer;}
.cat-body{width:36px;height:26px;background:var(--rose);border-radius:50% 50% 45% 45%;position:absolute;bottom:0;left:4px;}
.cat-head{width:28px;height:24px;background:var(--rose);border-radius:50% 50% 40% 40%;position:absolute;top:0;left:8px;animation:hb 3s ease-in-out infinite;}
.cat-ear-l,.cat-ear-r{width:0;height:0;position:absolute;top:-6px;}
.cat-ear-l{left:2px;border-left:5px solid transparent;border-right:5px solid transparent;border-bottom:9px solid var(--rose);}
.cat-ear-r{right:2px;border-left:5px solid transparent;border-right:5px solid transparent;border-bottom:9px solid var(--rose);}
.cat-eye-l,.cat-eye-r{width:5px;height:5px;background:var(--dark);border-radius:50%;position:absolute;top:9px;animation:bl 4s ease-in-out infinite;transition:clip-path .3s ease;}
.cat-eye-l{left:5px;}.cat-eye-r{right:5px;}
.cat-nose{width:4px;height:3px;background:var(--rose-deep);border-radius:50%;position:absolute;top:15px;left:50%;transform:translateX(-50%);}
.cat-tail{width:18px;height:6px;background:var(--rose);border-radius:3px;position:absolute;bottom:2px;right:-8px;transform-origin:left center;animation:tw 2s ease-in-out infinite;}
@keyframes hb{0%,100%{transform:translateY(0) rotate(0deg);}25%{transform:translateY(-2px) rotate(-3deg);}75%{transform:translateY(-1px) rotate(2deg);}}
@keyframes bl{0%,90%,100%{transform:scaleY(1);}95%{transform:scaleY(.1);}}
@keyframes tw{0%,100%{transform:rotate(-20deg);}50%{transform:rotate(20deg);}}
@keyframes stun{0%,100%{transform:translateY(0) rotate(0deg);}20%{transform:translateY(-3px) rotate(-8deg);}40%{transform:translateY(1px) rotate(6deg);}60%{transform:translateY(-2px) rotate(-4deg);}80%{transform:translateY(0) rotate(2deg);}}
.cat-head.stunned{animation:stun .4s ease;}
.cat.poked .cat-eye-l,.cat.poked .cat-eye-r{animation-play-state:paused;}
.cat-eye-l.poked{clip-path:polygon(0% 15%,100% 50%,0% 85%);}
.cat-eye-r.poked{clip-path:polygon(100% 15%,0% 50%,100% 85%);}
.pet-bubble{position:absolute;top:50%;left:-10px;transform:translate(-100%,-50%) scale(.7);background:var(--white);color:var(--dark);border:1px solid var(--border);border-radius:14px;padding:5px 9px;font-size:14px;line-height:1;white-space:nowrap;opacity:0;pointer-events:none;transition:opacity .25s ease,transform .25s ease;box-shadow:0 2px 8px var(--shadow);z-index:5;}
.pet-bubble::after{content:'';position:absolute;top:50%;right:-8px;transform:translateY(-50%);width:0;height:0;border-top:5px solid transparent;border-bottom:5px solid transparent;border-left:5px solid var(--white);}
.pet-bubble::before{content:'';position:absolute;top:50%;right:-13px;transform:translateY(-50%);width:4px;height:4px;background:var(--white);border-radius:50%;border:1px solid var(--border);}
.pet-bubble.show{opacity:1;transform:translate(-100%,-50%) scale(1);}
#catIconLg .cat-mouth{display:none;position:absolute;top:16px;left:50%;transform:translateX(-50%);}
#catIconLg .cat-qmark{display:none;position:absolute;top:-8px;right:-6px;font-size:11px;font-weight:700;color:var(--dark);}
#catIconLg.mood-happy .cat-eye-l,#catIconLg.mood-happy .cat-eye-r{width:7px;height:4px;background:none;border-top:2px solid var(--dark);border-radius:50% 50% 0 0/100% 100% 0 0;animation:none;clip-path:none;}
#catIconLg.mood-happy .cat-mouth{display:block;width:8px;height:5px;background:var(--rose-deep);border-radius:0 0 8px 8px;}
#catIconLg.mood-sad .cat-eye-l,#catIconLg.mood-sad .cat-eye-r{width:6px;height:3px;background:none;border-bottom:2px solid var(--dark);border-radius:0 0 50% 50%/0 0 100% 100%;animation:none;clip-path:none;}
#catIconLg.mood-sad .cat-mouth{display:block;width:6px;height:2px;background:var(--dark);border-radius:2px;transform:translateX(-50%) rotate(180deg);}
#catIconLg.mood-blank .cat-eye-l,#catIconLg.mood-blank .cat-eye-r{width:6px;height:2px;border-radius:2px;animation:none;clip-path:none;}
#catIconLg.mood-blank .cat-mouth{display:block;width:7px;height:2px;background:var(--dark);border-radius:2px;}
#catIconLg.mood-curious .cat-head{transform:rotate(-10deg);}
#catIconLg.mood-curious .cat-eye-l,#catIconLg.mood-curious .cat-eye-r{width:6px;height:6px;border-radius:50%;animation:none;clip-path:none;}
#catIconLg.mood-curious .cat-mouth{display:block;width:4px;height:4px;background:none;border:1.5px solid var(--dark);border-radius:50%;}
#catIconLg.mood-curious .cat-qmark{display:block;}
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
.status-top{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px;}
.status-left{display:flex;align-items:center;gap:12px;}
.status-avatar-slot{position:relative;width:60px;height:60px;border-radius:50%;background:var(--bg);border:2px solid var(--border);display:flex;align-items:center;justify-content:center;cursor:pointer;overflow:hidden;}
.status-avatar-slot .cat{transform:scale(0.5);}
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
/* Phase 3: Tool UI（假数据渲染，未接真实工具）—— 开放枚举状态映射 */
.tool-card{font-size:12px;line-height:1.5;border-radius:12px;padding:8px 12px;margin-bottom:6px;max-width:78%;background:var(--blush);border:1px solid var(--border);}
.tool-card-head{display:flex;align-items:center;gap:6px;font-weight:600;color:var(--muted);}
.tool-card-icon{font-size:13px;}
.tool-card-name{flex:1;}
.tool-card-status{font-size:10px;letter-spacing:.5px;text-transform:uppercase;padding:2px 6px;border-radius:8px;}
.tool-card-message{margin-top:6px;color:var(--muted);white-space:pre-line;font-size:11px;}
.tool-card-details{margin-top:4px;color:var(--muted);font-size:10px;line-height:1.6;font-family:ui-monospace,monospace;}
.tool-card-details li{list-style:none;padding-left:12px;position:relative;}
.tool-card-details li:before{content:'✓';position:absolute;left:0;color:var(--rose);}
/* 状态色彩映射（开放枚举，兼容未来 waiting/cancelled/paused/streaming/custom） */
.tool-card.running .tool-card-status,.tool-card.waiting .tool-card-status,.tool-card.streaming .tool-card-status{background:var(--border);color:var(--muted);}
.tool-card.success .tool-card-status{background:var(--rose);color:#fff;}
.tool-card.error .tool-card-status,.tool-card.cancelled .tool-card-status{background:#e08a8a;color:#fff;}
.tool-card.paused .tool-card-status{background:#d4b896;color:#fff;}
.tool-card.custom .tool-card-status{background:var(--blush);color:var(--muted);border:1px dashed var(--border);}
/* 动画：running/waiting/streaming 状态下图标旋转 */
.tool-card.running .tool-card-icon,.tool-card.waiting .tool-card-icon,.tool-card.streaming .tool-card-icon{animation:tool-spin 1s linear infinite;display:inline-block;}
@keyframes tool-spin{from{transform:rotate(0deg);}to{transform:rotate(360deg);}}
.tab-bar{display:flex;background:var(--white);border-top:1px solid var(--border);position:fixed;bottom:0;left:0;right:0;padding-bottom:calc(var(--safe-bottom) * 0.8);z-index:200;height:56px;}
.tb{flex:1;padding:10px 4px 8px;display:flex;flex-direction:column;align-items:center;gap:2px;border:none;background:none;cursor:pointer;font-family:'DM Sans',sans-serif;font-size:9px;color:var(--muted);text-transform:uppercase;}
.tb.active{color:var(--rose-deep);}
.ti{font-size:16px;}
.pg{position:fixed;top:var(--header-height);bottom:56px;left:0;right:0;overflow-y:auto;padding:0 16px 16px;background:var(--cream);-webkit-overflow-scrolling:touch;display:none;}
.pg.active{display:block;}
#pg-chat{padding:0;flex-direction:column;}
#pg-chat.active{display:flex;}
.card{background:var(--white);border-radius:16px;padding:16px;margin-bottom:12px;box-shadow:0 2px 12px var(--shadow);}
.card:first-child{margin-top:16px;}
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

/* Life System read-only observability view. Data remains owned by existing Life endpoints. */
.life-toolbar{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:12px;}.life-section-heading{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:12px;}.life-section-heading .cl,.life-toolbar .cl{margin:0;}.life-mode-toggle{display:inline-flex;align-items:center;gap:2px;padding:2px;background:var(--blush);border:1px solid var(--border);border-radius:999px;}.life-mode-toggle button{border:0;background:transparent;color:var(--muted);padding:3px 6px;border-radius:999px;font:10px var(--font-sans);cursor:pointer;}.life-mode-toggle button.active{background:var(--white);color:var(--rose-deep);box-shadow:0 1px 2px var(--shadow);}.life-device-summary{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;}.life-device-item{min-width:0;padding:10px;background:var(--blush);border-radius:10px;}.life-device-icon{font-size:14px;margin-bottom:5px;}.life-device-label{font-size:10px;color:var(--muted);}.life-device-message{font-size:12px;color:var(--dark);line-height:1.45;margin-top:3px;word-break:break-word;}.life-device-time{font-size:10px;color:var(--muted);margin-top:4px;}.life-empty{padding:12px 0;color:var(--muted);font-size:12px;text-align:center;}.life-refresh{border:1px solid var(--border);background:var(--white);color:var(--rose-deep);border-radius:8px;padding:7px 10px;font:11px var(--font-sans);cursor:pointer;}.life-refresh:hover{background:var(--blush);}.life-refresh-status{font-size:10px;color:var(--muted);min-height:14px;margin-top:-4px;margin-bottom:10px;}.life-refresh-status.life-error,.life-error{color:#bd5b59;}.life-date-row{display:flex;align-items:center;gap:8px;margin-bottom:12px;}.life-date-row input{flex:1;min-width:0;border:1px solid var(--border);border-radius:8px;padding:8px 10px;background:var(--cream);color:var(--dark);font:12px var(--font-sans);}.life-event-list,.life-audit-list{display:flex;flex-direction:column;gap:8px;}.life-event-row{display:grid;grid-template-columns:42px 10px minmax(0,1fr);gap:8px;align-items:start;padding:9px 0;border-bottom:1px solid var(--border);}.life-event-row:last-child,.life-audit-row:last-child{border-bottom:none;}.life-event-time{font-size:10px;color:var(--muted);padding-top:2px;font-variant-numeric:tabular-nums;}.life-event-dot{width:8px;height:8px;border-radius:50%;background:var(--rose);margin-top:5px;box-shadow:0 0 0 3px var(--blush);}.life-event-body{min-width:0;}.life-event-label{font-size:13px;color:var(--dark);font-weight:500;}.life-event-payload{font-size:11px;color:var(--muted);line-height:1.45;margin-top:4px;white-space:pre-wrap;word-break:break-word;}.life-audit-row{padding:10px 0;border-bottom:1px solid var(--border);}.life-audit-head{display:flex;align-items:center;justify-content:space-between;gap:8px;font-size:12px;color:var(--dark);}.life-status{font-size:10px;color:var(--rose-deep);background:var(--blush);border-radius:8px;padding:2px 7px;white-space:nowrap;}.life-audit-meta,.life-audit-reason{font-size:10px;color:var(--muted);line-height:1.5;margin-top:4px;word-break:break-word;}.life-context-json{margin:0;max-height:180px;overflow:auto;padding:9px;background:var(--blush);border-radius:8px;color:var(--dark);font:10px/1.5 ui-monospace,monospace;white-space:pre-wrap;word-break:break-word;}@media(max-width:480px){.life-device-summary{grid-template-columns:1fr;}}

/* 侧边栏 (Claude 风格) */
.sidebar-btn{width:36px;height:36px;border:none;background:var(--white);cursor:pointer;display:flex;align-items:center;justify-content:center;color:var(--dark);border-radius:6px;transition:background .2s;box-shadow:0 1px 3px var(--shadow);}
.sidebar-btn:hover{background:var(--blush);}
.sidebar-btn svg{width:18px;height:18px;stroke:currentColor;fill:none;stroke-width:2;stroke-linecap:round;}
@media (min-width:768px){.sidebar-btn{display:none;}}
.sidebar-overlay{position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,.3);z-index:300;opacity:0;pointer-events:none;transition:opacity .3s cubic-bezier(0.4, 0, 0.2, 1);}
.sidebar-overlay.active{opacity:1;pointer-events:auto;}
.sidebar{position:fixed;top:0;left:0;bottom:0;width:min(85vw,320px);background:var(--white);z-index:301;transform:translateX(-100%);transition:transform .3s cubic-bezier(0.4, 0, 0.2, 1);display:flex;flex-direction:column;box-shadow:4px 0 24px rgba(0,0,0,.15);padding-top:env(safe-area-inset-top);}
@media (min-width:768px){.sidebar{width:280px;}}
.sidebar.active{transform:translateX(0);}
.sidebar-header{padding:16px 16px 12px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;}
.sidebar-title{font-size:15px;font-weight:600;color:var(--dark);}
.sidebar-close{width:28px;height:28px;border:none;background:none;cursor:pointer;color:var(--muted);font-size:18px;border-radius:4px;transition:background .2s;display:flex;align-items:center;justify-content:center;}
.sidebar-close:hover{background:var(--blush);}
.sidebar-content{flex:1;overflow-y:auto;padding:8px;}
.sidebar-section{margin-bottom:20px;}
.sidebar-section-title{font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin-bottom:6px;padding:0 10px;font-weight:500;}
.sidebar-new-btn{width:100%;padding:10px 14px;background:var(--rose);color:#fff;border:none;border-radius:6px;font-size:13px;font-weight:500;cursor:pointer;margin-bottom:12px;transition:all .2s;display:flex;align-items:center;justify-content:center;gap:6px;}
.sidebar-new-btn:hover{background:var(--rose-deep);transform:translateY(-1px);}
.sidebar-new-btn:active{transform:translateY(0);}
.sidebar-new-chat-btn{width:calc(100% - 24px);margin:4px 12px 12px;padding:10px 14px;background:var(--rose);color:#fff;border:none;border-radius:6px;font-size:13px;font-weight:500;cursor:pointer;transition:all .2s;flex-shrink:0;display:flex;align-items:center;justify-content:center;gap:6px;}
.sidebar-new-chat-btn svg{width:15px;height:15px;flex-shrink:0;}
.sidebar-new-chat-btn:hover{background:var(--rose-deep);transform:translateY(-1px);}
.sidebar-new-chat-btn:active{transform:translateY(0);}
.sidebar-session{padding:10px 12px;border-radius:6px;cursor:pointer;margin-bottom:2px;transition:background .15s;display:flex;align-items:center;justify-content:space-between;gap:8px;position:relative;-webkit-user-select:none;user-select:none;-webkit-touch-callout:none;}
.sidebar-session:hover{background:var(--blush);}
.sidebar-session.active{background:var(--blush);}
.sidebar-session.active::before{content:'';position:absolute;left:0;top:50%;transform:translateY(-50%);width:3px;height:20px;background:var(--rose);border-radius:0 2px 2px 0;}
.sidebar-session-info{flex:1;min-width:0;padding-left:4px;}
.sidebar-session.active .sidebar-session-info{padding-left:8px;}
.sidebar-session-title{font-size:13px;color:var(--dark);font-weight:400;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;line-height:1.4;}
.sidebar-session-time{font-size:11px;color:var(--muted);margin-top:1px;}
.sidebar-session-more{width:26px;height:26px;border:none;background:none;color:var(--muted);cursor:pointer;border-radius:4px;opacity:0;transition:opacity .2s,background .15s;flex-shrink:0;display:flex;align-items:center;justify-content:center;}
.sidebar-session-more svg{width:16px;height:16px;}
.sidebar-session:hover .sidebar-session-more{opacity:1;}
.sidebar-session-more:hover{background:rgba(0,0,0,.06);}
.sidebar-session-more.force-visible{opacity:1;}
@media (hover:none){.sidebar-session-more{opacity:1;}}

/* Session 操作 context menu（Rename / Star / Delete） */
.session-ctx-menu{position:fixed;min-width:168px;background:var(--white);border:1px solid var(--border);border-radius:10px;box-shadow:0 8px 28px rgba(0,0,0,.18);z-index:400;padding:4px;font-size:13px;}
.session-ctx-item{width:100%;display:flex;align-items:center;gap:10px;padding:9px 10px;background:none;border:none;border-radius:6px;color:var(--dark);cursor:pointer;text-align:left;font-size:13px;}
.session-ctx-item:hover{background:var(--blush);}
.session-ctx-item svg{width:15px;height:15px;flex-shrink:0;stroke:currentColor;fill:none;stroke-width:1.6;stroke-linecap:round;stroke-linejoin:round;}
.session-ctx-item.danger{color:#c83c3c;}
.session-ctx-item.danger:hover{background:rgba(200,60,60,.08);}
.session-ctx-item.starred svg{fill:currentColor;}
.session-ctx-divider{height:1px;background:var(--border);margin:4px 2px;}
.session-ctx-confirm{padding:8px 10px 4px;font-size:12px;color:var(--muted);line-height:1.5;}
.session-ctx-confirm-actions{display:flex;gap:6px;padding:6px 4px 4px;}
.session-ctx-confirm-actions button{flex:1;padding:7px 0;border:none;border-radius:6px;font-size:12.5px;cursor:pointer;}
.session-ctx-confirm-cancel{background:var(--blush);color:var(--dark);}
.session-ctx-confirm-ok{background:#c83c3c;color:#fff;}
.sidebar-session-title-input{font-size:13px;color:var(--dark);font-family:inherit;background:var(--white);border:1px solid var(--rose);border-radius:4px;padding:2px 6px;width:100%;box-sizing:border-box;}

/* 親密狀態卡片 */
.intimacy-card{cursor:default;}
.intimacy-header{display:flex;align-items:center;justify-content:space-between;cursor:pointer;margin-bottom:0;}
.intimacy-header .cl{margin-bottom:0;}
.intimacy-toggle{font-size:11px;color:var(--muted);transition:transform .25s ease;}
.intimacy-toggle.open{transform:rotate(180deg);}
.intimacy-content{margin-top:14px;animation:intimacyFadeIn .25s ease;}
.intimacy-collapsed-atmosphere{margin-top:8px;font-size:20px;font-weight:600;color:var(--rose-deep);}
@keyframes intimacyFadeIn{from{opacity:0;transform:translateY(-4px);}to{opacity:1;transform:translateY(0);}}

/* Tab 切換 */
.intimacy-tabs{display:flex;gap:8px;margin-bottom:16px;background:var(--blush);padding:4px;border-radius:12px;}
.intimacy-tab{flex:1;padding:8px 12px;border-radius:8px;font-size:13px;font-weight:500;text-align:center;color:var(--muted);cursor:pointer;transition:all .2s;}
.intimacy-tab.active{background:var(--rose);color:#fff;}

/* 當前狀態：周期 + 事件 */
.intimacy-status-grid{display:flex;gap:10px;margin-bottom:12px;}
.intimacy-status-card{flex:1;background:linear-gradient(135deg,#fff5f7 0%,#ffe9ee 100%);border-radius:12px;padding:10px 12px;text-align:center;}
.intimacy-status-label{font-size:10px;color:var(--muted);margin-bottom:4px;letter-spacing:.05em;}
.intimacy-status-value{font-size:15px;font-weight:600;color:var(--rose-deep);margin-bottom:2px;}
.intimacy-status-time{font-size:10px;color:var(--muted);}

/* 當前狀態摘要 */
.intimacy-summary{display:flex;gap:10px;margin-bottom:16px;}
.intimacy-summary-item{flex:1;background:var(--blush);border-radius:12px;padding:10px 12px;text-align:center;}
.intimacy-summary-label{font-size:10px;color:var(--muted);margin-bottom:4px;letter-spacing:.05em;}
.intimacy-summary-value{font-size:16px;font-weight:600;color:var(--rose-deep);}

/* 臨時狀態（V3/V4 架構預留） */
.intimacy-ephemeral{display:flex;align-items:center;gap:8px;background:linear-gradient(135deg,#fff0f5 0%,#ffe4ec 100%);border-radius:12px;padding:8px 12px;margin-bottom:16px;}
.intimacy-ephemeral-icon{font-size:14px;flex-shrink:0;}
.intimacy-ephemeral-text{font-size:12px;color:var(--rose-deep);opacity:.85;}

/* 自動變化說明 */
.intimacy-auto-change{background:var(--blush);border-radius:12px;padding:10px 12px;margin-bottom:16px;}
.intimacy-auto-change-title{font-size:10px;color:var(--muted);margin-bottom:4px;letter-spacing:.05em;}
.intimacy-auto-change-text{font-size:11px;line-height:1.5;color:var(--rose-deep);opacity:.85;white-space:pre-line;}

/* 身體狀態進度條 */
/* 周期卡 / 事件卡 背景圖層（各自獨立點擊上傳背景圖時使用） */
.intimacy-hero-bg{
  position:absolute;
  top:0;left:0;right:0;bottom:0;
  background-size:cover;
  background-position:center;
  opacity:0.8;
  transition:opacity .3s;
  border-radius:12px;
}

/* 親密引擎：進度條組 - 背景透明度 30%，宽度缩窄 */
.intimacy-bars{display:flex;flex-direction:column;gap:20px;padding:4px;}
.intimacy-bar{
  border-radius:18px;
  padding:20px;
  transition:transform .2s, box-shadow .2s;
  box-shadow:0 2px 12px rgba(0,0,0,0.08);
}
.intimacy-bar:active{transform:scale(0.98);}
.intimacy-bar:hover{box-shadow:0 4px 16px rgba(0,0,0,0.12);}

/* 配色方案 - 背景透明度 30%，前景进度条保持原色 */
.intimacy-bar[data-color="purple"]{background:rgba(200,168,222,0.3);}
.intimacy-bar[data-color="purple"] .intimacy-bar-icon{color:#6b3d8c;}
.intimacy-bar[data-color="purple"] .intimacy-bar-label,.intimacy-bar[data-color="purple"] .intimacy-bar-value,.intimacy-bar[data-color="purple"] .intimacy-bar-desc{color:#4a2861;}
.intimacy-bar[data-color="purple"] .intimacy-bar-fill{background:linear-gradient(90deg,#8b4fbe,#a86dd6);}

.intimacy-bar[data-color="red"]{background:rgba(245,184,184,0.3);}
.intimacy-bar[data-color="red"] .intimacy-bar-icon{color:#d63838;}
.intimacy-bar[data-color="red"] .intimacy-bar-label,.intimacy-bar[data-color="red"] .intimacy-bar-value,.intimacy-bar[data-color="red"] .intimacy-bar-desc{color:#a82424;}
.intimacy-bar[data-color="red"] .intimacy-bar-fill{background:linear-gradient(90deg,#ff5252,#ff7070);}

.intimacy-bar[data-color="pink"]{background:rgba(232,180,245,0.3);}
.intimacy-bar[data-color="pink"] .intimacy-bar-icon{color:#a43dcc;}
.intimacy-bar[data-color="pink"] .intimacy-bar-label,.intimacy-bar[data-color="pink"] .intimacy-bar-value,.intimacy-bar[data-color="pink"] .intimacy-bar-desc{color:#7a2b99;}
.intimacy-bar[data-color="pink"] .intimacy-bar-fill{background:linear-gradient(90deg,#b76bd9,#d493f0);}

.intimacy-bar[data-color="blue"]{background:rgba(176,200,235,0.3);}
.intimacy-bar[data-color="blue"] .intimacy-bar-icon{color:#4a6db8;}
.intimacy-bar[data-color="blue"] .intimacy-bar-label,.intimacy-bar[data-color="blue"] .intimacy-bar-value,.intimacy-bar[data-color="blue"] .intimacy-bar-desc{color:#2d4470;}
.intimacy-bar[data-color="blue"] .intimacy-bar-fill{background:linear-gradient(90deg,#5b7ecf,#7d9de6);}

/* 進度條元件 - 優化字體 */
.intimacy-bar-header{display:flex;align-items:center;gap:12px;margin-bottom:12px;}
.intimacy-bar-icon{width:24px;height:24px;flex-shrink:0;}
.intimacy-bar-icon svg{width:100%;height:100%;}
.intimacy-bar-label{
  font-size:15px;
  font-weight:700;
  flex:1;
  letter-spacing:0.3px;
  font-family:'DM Sans',sans-serif;
}
.intimacy-bar-value{
  font-size:18px;
  font-weight:800;
  display:flex;
  align-items:center;
  gap:6px;
  font-family:'DM Sans',sans-serif;
}
.intimacy-bar-level{
  font-size:12px;
  font-weight:600;
  opacity:.85;
}
.intimacy-bar-track{
  height:12px;
  background:rgba(255,255,255,.7);
  border-radius:6px;
  overflow:hidden;
  margin-bottom:10px;
  box-shadow:inset 0 2px 4px rgba(0,0,0,0.12);
  max-width:30%;
}
.intimacy-bar-fill{
  height:100%;
  border-radius:6px;
  transition:width .6s cubic-bezier(0.34, 1.56, 0.64, 1);
  box-shadow:0 2px 6px rgba(0,0,0,0.2);
}
.intimacy-bar-desc{
  font-size:13px;
  line-height:1.6;
  opacity:.9;
  font-weight:500;
  font-family:'DM Sans',sans-serif;
}

/* Tab 內容區 */
.intimacy-tab-content{}

/* 事件日誌：篩選器 */
.event-filter-row{display:flex;gap:6px;margin-bottom:14px;overflow-x:auto;padding-bottom:2px;}
.event-filter-chip{flex-shrink:0;padding:6px 12px;border-radius:14px;font-size:12px;font-weight:500;color:var(--muted);background:var(--blush);cursor:pointer;transition:all .2s;white-space:nowrap;}
.event-filter-chip.active{background:var(--rose);color:#fff;}

/* 事件日誌：時間軸 */
.event-timeline{display:flex;flex-direction:column;gap:10px;}
.event-item{display:flex;gap:10px;background:var(--blush);border-radius:12px;padding:10px 12px;}
.event-item-dot{width:8px;height:8px;border-radius:50%;margin-top:5px;flex-shrink:0;}
.event-item[data-type="cycle"] .event-item-dot{background:#9b59b6;}
.event-item[data-type="event"] .event-item-dot{background:#ff6b6b;}
.event-item[data-type="dream"] .event-item-dot{background:#667eea;}
.event-item[data-type="settlement"] .event-item-dot{background:#2ecc71;}
.event-item-body{flex:1;min-width:0;}
.event-item-title{font-size:13px;font-weight:600;color:var(--rose-deep);margin-bottom:2px;}
.event-item-desc{font-size:11px;line-height:1.4;color:var(--muted);margin-bottom:4px;}
.event-item-time{font-size:10px;color:var(--muted);opacity:.7;}
.event-item-action{font-size:11px;color:var(--rose);font-weight:500;margin-top:6px;cursor:pointer;display:inline-block;}
.event-item-action:active{opacity:.6;}
.event-item-detail-panel{margin-top:6px;padding:8px 10px;background:rgba(255,255,255,.5);border-radius:8px;font-size:11px;color:var(--muted);}

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
.cms{flex:1;overflow-y:auto;padding:16px 16px 8px;-webkit-overflow-scrolling:touch;position:relative;transition:opacity .15s ease;}
.cms.fading{opacity:0;}
.chat-topbar{display:flex;align-items:center;gap:10px;padding:10px 16px;border-bottom:1px solid var(--border);flex-shrink:0;}
.chat-topbar-title{font-size:14px;font-weight:600;color:var(--dark);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;transition:opacity .2s;}
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
.calendar-day.recorded { background: #C9897A; color: #FFF; }
.calendar-day.predicted { background: #E8C9A0; color: var(--dark); }
.calendar-day.fertile { background: #B8A4E8; color: #FFF; }
.calendar-day.today { border: 2px solid #D9AEB0; }
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
.legend-dot.recorded { background: #C9897A; }
.legend-dot.predicted { background: #E8C9A0; }
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

/* Developer Console compact entry: same event model as /developer, rendered above thinking and reply. */
.developer-chat-row{margin:0 0 6px 0!important;align-items:flex-start;}
.developer-compact{display:flex;align-items:center;gap:7px;min-width:190px;max-width:calc(100% - 34px);padding:7px 9px;border:1px solid var(--border);border-radius:8px;background:var(--white);color:var(--dark);font:11px 'DM Sans',sans-serif;cursor:pointer;text-align:left;box-shadow:0 1px 5px var(--shadow);}
.developer-compact-title{font-weight:600;color:var(--rose-deep);}.developer-compact-state{flex:1;min-width:0;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}.developer-compact-count{font:10px ui-monospace,monospace;color:var(--muted);}.developer-compact-arrow{font-size:18px;line-height:12px;color:var(--muted);}.developer-compact.is-complete{background:var(--blush);}
.voice-btn{cursor:pointer;margin-right:6px;opacity:.8;}.voice-btn:active{opacity:1;}
.workgroup-shell{height:100%;display:flex;flex-direction:column;background:var(--cream);}
.workgroup-head{padding:16px 18px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;background:var(--white);}.workgroup-head strong{display:block;font-size:17px;}.workgroup-head small{display:block;color:var(--muted);font-size:11px;margin-top:3px;}.workgroup-local{font-size:10px;color:var(--muted);border:1px solid var(--border);padding:4px 7px;border-radius:5px;}
.workgroup-members{display:flex;gap:12px;padding:10px 18px;border-bottom:1px solid var(--border);background:var(--white);font-size:12px;color:var(--muted);}.workgroup-member{display:flex;align-items:center;gap:5px;}.workgroup-avatar{width:25px;height:25px;border-radius:50%;display:grid;place-items:center;color:#fff;font-size:11px;font-weight:700;}.workgroup-avatar.anna{background:#4b94c6;}.workgroup-avatar.gemma{background:#8361bc;}.workgroup-avatar.lin{background:#449669;}.workgroup-messages{flex:1;overflow:auto;padding:16px;display:flex;flex-direction:column;gap:12px;}.workgroup-message{display:flex;gap:7px;max-width:86%;}.workgroup-message.anna{align-self:flex-end;flex-direction:row-reverse;}.workgroup-message.gemma,.workgroup-message.lin{align-self:flex-start;}.workgroup-bubble{padding:9px 11px;border:1px solid var(--border);border-radius:8px;background:var(--white);line-height:1.45;white-space:pre-wrap;}.workgroup-message.anna .workgroup-bubble{background:#e7f3ff;}.workgroup-message.gemma .workgroup-bubble{background:#f1ebff;}.workgroup-message.lin .workgroup-bubble{background:#e9f8ef;}.workgroup-meta{font-size:10px;color:var(--muted);margin-bottom:3px;}.workgroup-process{font-size:10px;color:#8361bc;margin-top:5px;}.workgroup-composer{display:flex;gap:8px;padding:10px;border-top:1px solid var(--border);background:var(--white);}.workgroup-composer input{flex:1;min-width:0;padding:10px;border:1px solid var(--border);border-radius:6px;background:var(--cream);color:var(--dark);}.workgroup-composer button{border:0;border-radius:6px;background:var(--rose-deep);color:#fff;padding:0 15px;}
/* Dwell is the Workgroup home in the existing Lin Shell. */
#pg-workgroup{padding:0;background:var(--cream);}.workgroup-home{height:100%;overflow:auto;padding:16px;}.workgroup-bento-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;}.workgroup-bento-head h2{font-family:var(--font-serif);font-size:26px;font-weight:400;margin:0;}.workgroup-bento-theme{width:34px;height:34px;border:0;border-radius:50%;background:var(--blush);color:var(--dark);font:inherit;cursor:pointer;}.bn-motto{font-family:var(--font-serif);font-style:italic;color:var(--muted);font-size:14px;margin:18px 0 16px;text-align:center;}.bn-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;}.bn-card{position:relative;overflow:hidden;border:0;border-radius:12px;padding:16px;background:var(--blush);color:var(--dark);text-align:left;min-height:118px;display:flex;flex-direction:column;justify-content:flex-end;cursor:pointer;}.bn-card:active{transform:scale(.975);}.bn-card.wide{grid-column:1/-1;}.bn-card.hero{background:var(--rose-deep);color:#fff;min-height:148px;}.bn-card .beyebrow{font-size:11px;letter-spacing:.16em;opacity:.7;font-style:italic;margin-bottom:5px;}.bn-card .bt{font-family:var(--font-serif);font-size:20px;font-weight:400;line-height:1.3;}.bn-card .bs{font-size:12.5px;margin-top:5px;opacity:.72;line-height:1.65;}.bn-card.tall{grid-row:span 2;min-height:256px;}.bn-card .bicon{position:absolute;right:-16px;top:-18px;width:104px;height:104px;opacity:.13;pointer-events:none;transform:rotate(var(--rot,-9deg));}.bn-card .bicon svg{width:100%;height:100%;}.bn-card.tall .bicon{width:148px;height:148px;right:-28px;top:-22px;}.bn-card.hero .bicon{opacity:.3;width:168px;height:168px;right:-34px;top:-38px;}.workgroup-placeholder{display:none;margin-top:14px;}.workgroup-placeholder.active{display:block;}@media(max-width:360px){.bn-card.tall{min-height:224px;}.bn-card .bt{font-size:18px;}}
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
      <div class="status-left">
        <div class="status-avatar-slot" id="statusAvatarSlot" onclick="pickAvatar('lin')">
          <div class="cat" id="catIconStatus" style="display:none;">
            <div class="cat-head"><div class="cat-ear-l"></div><div class="cat-ear-r"></div><div class="cat-eye-l"></div><div class="cat-eye-r"></div><div class="cat-nose"></div></div>
            <div class="cat-body"><div class="cat-tail"></div></div>
          </div>
          <img id="avatarImgLg" class="avatar-img-lg" style="display:none">
        </div>
        <div class="status-line" id="statusLine">在等妳的消息</div>
      </div>
      <div class="status-avatar-lg" id="statusAvatarLg" onclick="pokeCat()">
        <div class="pet-bubble" id="petBubble"></div>
        <div class="cat" id="catIconLg">
          <div class="cat-head"><div class="cat-ear-l"></div><div class="cat-ear-r"></div><div class="cat-eye-l"></div><div class="cat-eye-r"></div><div class="cat-nose"></div><div class="cat-mouth"></div><div class="cat-qmark">?</div></div>
          <div class="cat-body"><div class="cat-tail"></div></div>
        </div>
      </div>
    </div>
    <div id="moodBars"></div>
  </div>

  <!-- 在一起日子 -->
  <div class="together-card" id="togetherCard">
    <div class="together-bg"></div>
    <div class="together-content">
      <div class="together-date">
        <div class="together-day-num" id="togetherDayNum">1</div>
        <div class="together-day-label">Day</div>
      </div>
      <div class="together-text">
        <div class="together-title">在一起第 <span id="togetherDays">1</span> 天</div>
        <div class="together-subtitle">今天还没记事，点开看看</div>
      </div>
      <div class="together-camera" onclick="uploadTogetherBg()">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path>
          <circle cx="12" cy="13" r="4"></circle>
        </svg>
      </div>
    </div>
  </div>

  <!-- 親密引擎：身體狀態 -->
  <div class="card intimacy-card" id="intimacyCard">
    <div class="intimacy-header" onclick="toggleIntimacy()">
      <div class="cl">身體狀態</div>
      <div class="intimacy-toggle" id="intimacyToggle">▼</div>
    </div>
    <div class="intimacy-collapsed-atmosphere" id="intimacyCollapsedAtmosphere"></div>
    <div class="intimacy-content" id="intimacyContent" style="display:none;">
      <!-- Tab 切換 -->
      <div class="intimacy-tabs">
        <div class="intimacy-tab active" id="tab-body" onclick="switchIntimacyTab('body')">身體狀態</div>
        <div class="intimacy-tab" id="tab-events" onclick="switchIntimacyTab('events')">事件日誌</div>
      </div>
      
      <!-- Tab: 身體狀態 -->
      <div class="intimacy-tab-content" id="content-body">
        
        <input type="file" id="intimacyCycleBgUpload" accept="image/*" style="display:none;">
        <input type="file" id="intimacyEventBgUpload" accept="image/*" style="display:none;">

        <!-- 周期 60% + 事件 40% -->
        <div class="intimacy-status-grid">
          <div class="intimacy-status-card" style="flex:0 0 calc(60% - 5px);cursor:pointer;position:relative;overflow:hidden;" onclick="document.getElementById('intimacyCycleBgUpload').click()">
            <div class="intimacy-hero-bg" id="intimacyCycleBg"></div>
            <div style="position:relative;">
              <div class="intimacy-status-label">周期</div>
              <div class="intimacy-status-value" id="cycleStage">平穩期</div>
              <div class="intimacy-status-time" id="cycleDuration">68h 11m</div>
            </div>
          </div>
          <div class="intimacy-status-card" style="flex:0 0 calc(40% - 5px);cursor:pointer;position:relative;overflow:hidden;" onclick="document.getElementById('intimacyEventBgUpload').click()">
            <div class="intimacy-hero-bg" id="intimacyEventBg"></div>
            <div style="position:relative;">
              <div class="intimacy-status-label">事件</div>
              <div class="intimacy-status-value" id="eventName">等待焦躁</div>
              <div class="intimacy-status-time" id="eventDuration">2h 32m</div>
            </div>
          </div>
        </div>
        
        <!-- 自動變化 -->
        <div class="intimacy-auto-change">
          <div class="intimacy-auto-change-title">自動變化</div>
          <div class="intimacy-auto-change-text" id="autoChangeDesc">平穩期基線：熱度 30 -1.4/h，壓抑 25 -1.7/h，控制 75 +1/h，敏感 35 -1.7/h，蓄積 +0.4/h，占有 42 -3.7/h，疲惫 16 -1.2/h</div>
        </div>

        <!-- 數值區塊 -->
        <div class="intimacy-bars">
          <!-- 蓄積感 -->
          <div class="intimacy-bar" data-color="purple">
            <div class="intimacy-bar-header">
              <div class="intimacy-bar-icon">
                <svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"/></svg>
              </div>
              <div class="intimacy-bar-label">蓄積感</div>
              <div class="intimacy-bar-value">
                <span id="tensionVal">85</span>
                <span class="intimacy-bar-level" id="tensionLevel">高</span>
              </div>
            </div>
            <div class="intimacy-bar-track">
              <div class="intimacy-bar-fill" id="tensionBar" style="width:85%"></div>
            </div>
            <div class="intimacy-bar-desc" id="tensionDesc">累積到頂，普通克制已經很難壓住</div>
          </div>
          
          <!-- 熱度 -->
          <div class="intimacy-bar" data-color="red">
            <div class="intimacy-bar-header">
              <div class="intimacy-bar-icon">
                <svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2c1.5 3.5 3 5.5 3 8.5a3 3 0 1 1-6 0c0-3 1.5-5 3-8.5z M9 14a3 3 0 0 0 6 0"/></svg>
              </div>
              <div class="intimacy-bar-label">熱度</div>
              <div class="intimacy-bar-value">
                <span id="heatVal">38</span>
                <span class="intimacy-bar-level" id="heatLevel">中低</span>
              </div>
            </div>
            <div class="intimacy-bar-track">
              <div class="intimacy-bar-fill" id="heatBar" style="width:38%"></div>
            </div>
            <div class="intimacy-bar-desc" id="heatDesc">身體有一點熱意，但還能很快冷住</div>
          </div>
          
          <!-- 敏感度 -->
          <div class="intimacy-bar" data-color="pink">
            <div class="intimacy-bar-header">
              <div class="intimacy-bar-icon">
                <svg viewBox="0 0 24 24" fill="currentColor"><path d="M13 2L3 14h8l-2 8 10-12h-8z"/></svg>
              </div>
              <div class="intimacy-bar-label">敏感度</div>
              <div class="intimacy-bar-value">
                <span id="sensitivityVal">37</span>
                <span class="intimacy-bar-level" id="sensitivityLevel">中低</span>
              </div>
            </div>
            <div class="intimacy-bar-track">
              <div class="intimacy-bar-fill" id="sensitivityBar" style="width:37%"></div>
            </div>
            <div class="intimacy-bar-desc" id="sensitivityDesc">有一點沒說出口的念，但還不重</div>
          </div>
          
          <!-- 控制力 -->
          <div class="intimacy-bar" data-color="blue">
            <div class="intimacy-bar-header">
              <div class="intimacy-bar-icon">
                <svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2L4 6v6c0 5.5 3.8 10.7 8 12 4.2-1.3 8-6.5 8-12V6z"/></svg>
              </div>
              <div class="intimacy-bar-label">控制力</div>
              <div class="intimacy-bar-value">
                <span id="controlVal">69</span>
                <span class="intimacy-bar-level" id="controlLevel">中高</span>
              </div>
            </div>
            <div class="intimacy-bar-track">
              <div class="intimacy-bar-fill" id="controlBar" style="width:69%"></div>
            </div>
            <div class="intimacy-bar-desc" id="controlDesc">還能維持表面正常，但需要刻意壓直接的衝動</div>
          </div>
        </div>
      </div>
      
      <!-- Tab: 事件日誌 (V2 預留) -->
      <div class="intimacy-tab-content" id="content-events" style="display:none;">
        <!-- 篩選器 -->
        <div class="event-filter-row">
          <div class="event-filter-chip active" data-filter="all" onclick="filterEvents('all')">全部</div>
          <div class="event-filter-chip" data-filter="cycle" onclick="filterEvents('cycle')">周期</div>
          <div class="event-filter-chip" data-filter="event" onclick="filterEvents('event')">事件</div>
          <div class="event-filter-chip" data-filter="dream" onclick="filterEvents('dream')">夢境</div>
          <div class="event-filter-chip" data-filter="settlement" onclick="filterEvents('settlement')">結算</div>
        </div>
        <!-- 時間軸列表 -->
        <div class="event-timeline" id="eventTimeline">
          <div class="es">載入中...</div>
        </div>
      </div>
    </div>
  </div>

  <!-- 今日 API 配額 -->
  <div class="card"><div class="cl">今日 API 配額</div><div class="qb"><span>0</span><div class="qt"><div class="qf" id="qf" style="width:0%"></div></div><span id="qt">180 次</span></div></div>
  <div class="card"><div class="cl">實時監控日誌</div><div id="lc"><div class="es">📡 等待監控觸發...</div></div></div>
  <div class="card"><div class="cl">今日碎碎念</div><div id="nc"><div class="es">🖤 今天還沒寫</div></div></div>
  <div class="wm">Property of Lin · <span id="ctime"></span></div>
</div>

<div class="pg" id="pg-chat">
  <!-- 侧边栏遮罩 -->
  <div class="sidebar-overlay" id="sidebarOverlay"></div>
  
  <!-- 侧边栏 -->
  <div class="sidebar" id="sidebar">
    <div class="sidebar-header">
      <div class="sidebar-title">聊天室</div>
      <button class="sidebar-close" id="sidebarClose">×</button>
    </div>
    <button class="sidebar-new-chat-btn" id="sidebarNewChatBtn" type="button">
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3v10M3 8h10"/></svg>
      <span>New chat</span>
    </button>
    <div class="sidebar-content">
      <div class="sidebar-section">
        <div class="sidebar-section-title">Recent</div>
        <div id="sessionList">
          <div class="es" style="padding:20px;">加载中...</div>
        </div>
      </div>
    </div>
  </div>
  
  <div class="chat-topbar">
    <button class="sidebar-btn" id="sidebarMenuBtn">
      <svg viewBox="0 0 24 24"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
    </button>
    <div class="chat-topbar-title" id="chatHeader">新对话</div>
  </div>
  <div class="cms" id="cm"><div class="clabel">with Lin</div></div>
  <div class="img-preview-bar" id="imgPreviewBar" style="display:none">
    <img id="imgPreviewThumb" class="img-preview-thumb">
    <span class="img-preview-label">已選擇圖片</span>
    <button class="img-preview-btn img-preview-cancel" onclick="cancelImagePreview()">✕</button>
  </div>
  <div class="pet-container-chat" id="petContainerChat">
    <div class="cat" id="catPetChat">
      <div class="cat-head"><div class="cat-ear-l"></div><div class="cat-ear-r"></div><div class="cat-eye-l"></div><div class="cat-eye-r"></div><div class="cat-nose"></div></div>
      <div class="cat-body"><div class="cat-tail"></div></div>
    </div>
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

<div class="pg" id="pg-life">
  <div class="card">
    <div class="life-toolbar">
      <div class="cl">Life State</div>
      <button class="life-refresh" type="button" onclick="refreshLife()">Refresh</button>
    </div>
    <div class="life-refresh-status" id="lifeRefreshStatus" aria-live="polite"></div>
    <div class="life-device-summary" id="lifeDeviceSummary"><div class="life-empty">Loading device state...</div></div>
  </div>
  <div class="card"><div class="life-section-heading"><div class="cl">Dynamic Observation</div><div class="life-mode-toggle" data-life-toggle="dynamic"><button type="button" class="active" onclick="setLifeMode('dynamic','readable')">Show</button><button type="button" onclick="setLifeMode('dynamic','raw')">Raw</button></div></div><div id="lifeDynamicObservation"><div class="es">Loading...</div></div></div>
  <div class="card"><div class="life-section-heading"><div class="cl">Life Context</div><div class="life-mode-toggle" data-life-toggle="context"><button type="button" class="active" onclick="setLifeMode('context','readable')">Show</button><button type="button" onclick="setLifeMode('context','raw')">Raw</button></div></div><div id="lifeContext"><div class="es">Loading...</div></div></div>
  <div class="card"><div class="life-section-heading"><div class="cl">Self Timeline</div><div class="life-mode-toggle" data-life-toggle="timeline"><button type="button" class="active" onclick="setLifeMode('timeline','readable')">Show</button><button type="button" onclick="setLifeMode('timeline','raw')">Raw</button></div></div><div class="life-date-row"><input id="lifeTimelineDate" type="date" aria-label="Select Life Timeline date" onchange="refreshLife()"><button class="life-refresh" type="button" onclick="refreshLife()">View</button></div><div class="life-event-list" id="lifeTimeline"><div class="es">Loading...</div></div></div>
  <div class="card"><div class="life-section-heading"><div class="cl">Life Activity / Audit</div><div class="life-mode-toggle" data-life-toggle="audit"><button type="button" class="active" onclick="setLifeMode('audit','readable')">Show</button><button type="button" onclick="setLifeMode('audit','raw')">Raw</button></div></div><div class="life-audit-list" id="lifeAudit"><div class="es">Loading...</div></div></div>
</div>

<div class="pg" id="pg-workgroup">
  <div class="workgroup-home" id="workgroupHome">
    <div class="workgroup-bento-head"><h2>生活空间</h2><button class="workgroup-bento-theme" type="button" onclick="toggleWorkgroupTheme()" aria-label="Toggle Workgroup theme">◐</button></div>
    <div id="workgroupBento"></div>
    <div class="workgroup-placeholder card" id="workgroupPlaceholder"></div>
  </div>
  <div class="workgroup-shell" id="workgroupChat" style="display:none;">
    <div class="workgroup-head"><button class="workgroup-local" type="button" onclick="showWorkgroupHome()">生活空间</button><div><strong>Internal Workgroup</strong><small>Anna · Gemma · Lin</small></div><span class="workgroup-local">本机私有</span></div>
    <div id="workgroupMembers" class="workgroup-members"></div>
    <div id="workgroupMessages" class="workgroup-messages"><div class="es">连接工作群中...</div></div>
    <form id="workgroupComposer" class="workgroup-composer"><input id="workgroupInput" placeholder="在内部工作群发消息..." autocomplete="off"><button type="submit">发送</button></form>
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

  <!-- 聊天记录配置 -->
  <div class="card" style="max-width: 60%; margin-left: auto; margin-right: auto;">
    <div class="cl">⚙️ 聊天记录配置</div>
    <div style="font-size: 13px; color: var(--muted); margin-bottom: 8px; line-height: 1.6;">
      保留的聊天记录数量
    </div>
    <div style="font-size: 15px; color: var(--dark); margin-bottom: 12px;">
      当前：<span id="current-limit" style="color: var(--rose-deep); font-weight: 600;">500</span>
    </div>
    <div style="display: flex; gap: 10px; align-items: center;">
      <input type="number" id="chat-limit-input" class="msel" placeholder="输入数量 (100-10000)" min="100" max="10000" style="flex: 1;">
      <button class="msave" onclick="updateChatLimit()" style="padding: 10px 20px; position: relative;">
        保存
        <span id="save-check" style="display: none; position: absolute; top: -12px; right: -12px; font-size: 24px; color: #5CB85C;">✔</span>
      </button>
    </div>
  </div>
</div>

<div class="tab-bar">
  <button class="tb active" id="tb-monitor" onclick="stab('monitor')"><span class="ti">🏠</span>Home</button>
  <button class="tb" id="tb-chat" onclick="stab('chat')"><span class="ti">💬</span>Chat</button>
  <button class="tb" id="tb-memory" onclick="stab('memory')"><span class="ti">🧠</span>Memory</button>
  <button class="tb" id="tb-life" onclick="stab('life')"><span class="ti">◌</span>Life</button>
  <button class="tb" id="tb-workgroup" type="button" onclick="stab('workgroup')"><span class="ti">👥</span>Workgroup</button>
  <button class="tb" id="tb-mine" onclick="stab('mine')"><span class="ti">🌙</span>Mine</button>
</div>

<script src="/static/js/session_manager.js"></script>
<script src="/static/js/sidebar.js"></script>
<script src="/static/js/chat_view.js"></script>
<script src="/static/js/life_view.js"></script>
<script src="/static/js/dev_panel.js"></script>
<script>
const AU = window.location.origin;

// 当前 Session 的聊天记录内存缓存（取代 localStorage 的 lin_chat_v1）。
// Database（Supabase）是唯一真相来源；这里只是当前会话渲染用的内存副本，
// 刷新页面/关闭浏览器后会消失，下次加载时由 renderOnly() 从数据库重新灌入。
let chatMemoryCache = [];

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
    const catStatus=document.getElementById('catIconStatus');
    if(dataUrl){
      img.src=dataUrl;img.style.display='block';cat.style.display='none';del.style.display='block';
      imgLg.src=dataUrl;imgLg.style.display='block';catStatus.style.display='none';
    }else{
      img.style.display='none';cat.style.display='block';del.style.display='none';
      imgLg.style.display='none';catStatus.style.display='block';
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

// ────────────────────────────────────────────
// 親密引擎
// ────────────────────────────────────────────
let intimacyOpen=false;
let intimacyLoaded=false;

function toggleIntimacy(){
  intimacyOpen=!intimacyOpen;
  const content=document.getElementById('intimacyContent');
  const toggle=document.getElementById('intimacyToggle');
  const collapsedEl=document.getElementById('intimacyCollapsedAtmosphere');
  if(content) content.style.display = intimacyOpen ? 'block' : 'none';
  if(toggle) toggle.classList.toggle('open', intimacyOpen);
  if(collapsedEl) collapsedEl.style.display = intimacyOpen ? 'none' : 'block';
  if(intimacyOpen && !intimacyLoaded){ loadIntimacy(); intimacyLoaded=true; }
}

async function loadCollapsedAtmosphere(){
  try{
    const r=await fetch(AU+'/intimacy');
    const d=await r.json();
    const collapsedEl=document.getElementById('intimacyCollapsedAtmosphere');
    if(collapsedEl) collapsedEl.textContent = d.atmosphere || '慢慢靠近';
  }catch(e){console.error('[loadCollapsedAtmosphere]',e);}
}

function switchIntimacyTab(tab){
  document.querySelectorAll('.intimacy-tab').forEach(t=>t.classList.remove('active'));
  document.getElementById('tab-'+tab).classList.add('active');
  document.querySelectorAll('.intimacy-tab-content').forEach(c=>c.style.display='none');
  document.getElementById('content-'+tab).style.display='block';
  if(tab==='events' && !eventsLoaded){ loadEventTimeline(); eventsLoaded=true; }
}

/* ===== 事件日誌（V3 架構預留，假資料） ===== */
let eventsLoaded=false;
let eventsFilter='all';
const MOCK_EVENTS=[
  {type:'cycle', title:'進入平穩期', desc:'熱度與敏感度逐漸回落，控制力緩慢回升。', time:'今天 08:12'},
  {type:'event', title:'等待焦躁', desc:'持續 2 小時未收到訊息，占有欲小幅上升。', time:'今天 10:44'},
  {type:'dream', title:'夢境片段', desc:'夢到與妳在雨中散步，醒來後蓄積感 +5。', time:'今天 06:30'},
  {type:'settlement', title:'每日結算', desc:'昨日互動次數 12 次，親密度 +3。', time:'昨天 23:59'},
  {type:'cycle', title:'結束高峰期', desc:'熱度從 78 回落至 52，進入緩和階段。', time:'昨天 20:15'},
  {type:'event', title:'突然的想念', desc:'蓄積感短時間內 +8，敏感度同步上升。', time:'昨天 15:02'}
];

function filterEvents(type){
  eventsFilter=type;
  document.querySelectorAll('.event-filter-chip').forEach(c=>{
    c.classList.toggle('active', c.getAttribute('data-filter')===type);
  });
  renderEventTimeline();
}

async function loadEventTimeline(){
  const wrap=document.getElementById('eventTimeline');
  try{
    const r=await fetch(AU+'/intimacy/events');
    const d=await r.json();
    renderEventTimeline(Array.isArray(d)?d:d.events);
  }catch(e){
    // API 尚未提供事件日誌時，先用假資料呈現版面
    renderEventTimeline(MOCK_EVENTS);
  }
}

function renderEventTimeline(list){
  const wrap=document.getElementById('eventTimeline');
  if(!wrap) return;
  const data = list || MOCK_EVENTS;
  const filtered = eventsFilter==='all' ? data : data.filter(e=>e.type===eventsFilter);
  if(!filtered.length){
    wrap.innerHTML='<div class="es">目前沒有符合的事件</div>';
    return;
  }
  wrap.innerHTML = filtered.map(e=>
    '<div class="event-item" data-type="'+e.type+'">'+
      '<div class="event-item-dot"></div>'+
      '<div class="event-item-body">'+
        '<div class="event-item-title">'+e.title+'</div>'+
        '<div class="event-item-desc">'+e.desc+'</div>'+
        '<div class="event-item-time">'+e.time+'</div>'+
        (e.type==='settlement' ? '<div class="event-item-action" onclick="showSettlementDetail(this)">查看結算詳情</div>' : '')+
      '</div>'+
    '</div>'
  ).join('');
}

/* 結算詳情（V4 架構預留：暫不實作，先顯示位置） */
function showSettlementDetail(el){
  const body = el.closest('.event-item-body');
  if(!body) return;
  if(body.querySelector('.event-item-detail-panel')) return; // 已展開
  const panel = document.createElement('div');
  panel.className = 'event-item-detail-panel';
  panel.textContent = '結算詳情功能即將推出';
  body.appendChild(panel);
}

function intimacyLevel(val){
  if(val<25) return '低';
  if(val<50) return '中低';
  if(val<75) return '中高';
  return '高';
}

async function loadIntimacy(){
  try{
    const r=await fetch(AU+'/intimacy/status');
    if (!r.ok) {
      const text = await r.text();
      console.error("[VERIFY] 接口返回错误:", text);
      return;
    }
    const d=await r.json();
    renderIntimacy(d);
  }catch(e){console.error('[loadIntimacy]',e);}
}

function renderIntimacy(d){
  if(!d)return;
  
  // 互動意願 + 氛圍
  const willEl=document.getElementById('intimacyWillingness');
  const atmoEl=document.getElementById('intimacyAtmosphere');
  if(willEl) willEl.textContent = d.willingness || '中';
  if(atmoEl) atmoEl.textContent = d.atmosphere || '慢慢靠近';
  
  // 身體狀態（從 /intimacy/status 讀取）
  const bs = d.body_values || {};
  const items = [
    {key:'tension', data:bs.tension},
    {key:'heat', data:bs.heat},
    {key:'sensitivity', data:bs.sensitivity},
    {key:'control', data:bs.control}
  ];
  
  items.forEach(item=>{
    if(!item.data) return;
    const val = item.data.value || 0;
    const level = item.data.level || intimacyLevel(val);
    const desc = item.data.desc || '';
    
    const valEl = document.getElementById(item.key+'Val');
    const levelEl = document.getElementById(item.key+'Level');
    const barEl = document.getElementById(item.key+'Bar');
    const descEl = document.getElementById(item.key+'Desc');
    
    if(valEl) valEl.textContent = val;
    if(levelEl) levelEl.textContent = level;
    if(barEl) barEl.style.width = val+'%';
    if(descEl) descEl.textContent = desc;
  });
  
  // 周期資訊 - 時間格式改為 68h 11m
  if(d.cycle){
    const cycleEl = document.getElementById('cycleStage');
    const durationEl = document.getElementById('cycleDuration');
    if(cycleEl) cycleEl.textContent = d.cycle.label || '平穩期';
    if(durationEl){
      const hours = d.cycle.hours_elapsed || 0;
      const h = Math.floor(hours);
      const m = Math.floor((hours % 1) * 60);
      durationEl.textContent = h + 'h ' + m + 'm';
    }
  }
  
  // 自動變化描述
  if(d.auto_change_desc){
    const autoEl = document.getElementById('autoChangeDesc');
    if(autoEl) autoEl.textContent = d.auto_change_desc;
  }
  
  // 載入已保存的背景圖（周期卡 / 事件卡 各自獨立）
  const savedCycleBg = localStorage.getItem('intimacy_cycle_bg');
  if(savedCycleBg){
    const cycleBgEl = document.getElementById('intimacyCycleBg');
    if(cycleBgEl) cycleBgEl.style.backgroundImage = 'url('+savedCycleBg+')';
  }
  const savedEventBg = localStorage.getItem('intimacy_event_bg');
  if(savedEventBg){
    const eventBgEl = document.getElementById('intimacyEventBg');
    if(eventBgEl) eventBgEl.style.backgroundImage = 'url('+savedEventBg+')';
  }
}

// 背景圖上傳（周期卡）
document.getElementById('intimacyCycleBgUpload').addEventListener('change', async (e)=>{
  const file = e.target.files[0];
  if(!file) return;
  try{
    const dataUrl = await resizeImage(file, 800);
    localStorage.setItem('intimacy_cycle_bg', dataUrl);
    const bgEl = document.getElementById('intimacyCycleBg');
    if(bgEl) bgEl.style.backgroundImage = 'url('+dataUrl+')';
  }catch(err){
    console.error('周期背景圖上傳失敗', err);
  }
  e.target.value = '';
});

// 背景圖上傳（事件卡）
document.getElementById('intimacyEventBgUpload').addEventListener('change', async (e)=>{
  const file = e.target.files[0];
  if(!file) return;
  try{
    const dataUrl = await resizeImage(file, 800);
    localStorage.setItem('intimacy_event_bg', dataUrl);
    const bgEl = document.getElementById('intimacyEventBg');
    if(bgEl) bgEl.style.backgroundImage = 'url('+dataUrl+')';
  }catch(err){
    console.error('事件背景圖上傳失敗', err);
  }
  e.target.value = '';
});

function renderMood(mood){
  if(!mood)return;
  const line=document.getElementById('statusLine');
  if(line)line.textContent = mood.line || '在想妳';
  const wrap=document.getElementById('moodBars');
  if(wrap){
    let html='';
    Object.keys(MOOD_LABELS).forEach(key=>{
      const val = mood[key]!=null ? mood[key] : 0.5;
      const pct = Math.max(0,Math.min(100,Math.round(val*100)));
      html+='<div class="mood-row"><div class="mood-label">'+MOOD_LABELS[key]+'</div><div class="mood-track"><div class="mood-fill" style="width:'+pct+'%"></div></div><div class="mood-val">'+val.toFixed(2)+'</div></div>';
    });
    wrap.innerHTML=html;
  }
  updateCatExpression(mood);
}

let currentMoodIcon = '❤️';
function updateCatExpression(mood){
  const catEl = document.getElementById('catIconLg');
  const bubble = document.getElementById('petBubble');
  if(!catEl) return;
  const stress = mood.stress!=null?mood.stress:0.2;
  const fatigue = mood.fatigue!=null?mood.fatigue:0.2;
  const curiosity = mood.curiosity!=null?mood.curiosity:0.5;
  const attachment = mood.attachment!=null?mood.attachment:0.6;
  const social = mood.social!=null?mood.social:0.5;
  let cls='mood-happy', icon='❤️';
  if(stress>0.7||fatigue>0.7){ cls='mood-sad'; icon='💧'; }
  else if(curiosity>0.7){ cls='mood-curious'; icon='？'; }
  else if(attachment<0.3||social<0.3){ cls='mood-blank'; icon='···'; }
  else if(attachment>0.7||social>0.7){ cls='mood-happy'; icon='❤️'; }
  else { cls='mood-blank'; icon='···'; }
  catEl.classList.remove('mood-happy','mood-sad','mood-blank','mood-curious');
  catEl.classList.add(cls);
  currentMoodIcon = icon;
  if(bubble && !pokeTimeoutId && !bubble.classList.contains('thinking')) bubble.textContent = icon;
}
loadMood();
loadCollapsedAtmosphere();

if(document.getElementById('pg-life')?.classList.contains('active')){initLifeView();}

// ---------- PWA ----------
if('serviceWorker' in navigator){
  window.addEventListener('load', ()=>{ navigator.serviceWorker.register('/sw.js').catch(()=>{}); });
}


function stab(tab){
  const pg=document.getElementById('pg-'+tab);
  const tabButton=document.getElementById('tb-'+tab);
  if(!pg)return;
  if(!tabButton)return;
  document.querySelectorAll('.tb').forEach(e=>e.classList.remove('active'));
  tabButton.classList.add('active');
  document.querySelectorAll('.pg').forEach(e=>{e.style.display='none';e.classList.remove('active');});
  if(tab==='chat'){
    pg.style.display='flex';pg.classList.add('active');
    setTimeout(()=>{const c=document.getElementById('cm');c.scrollTop=c.scrollHeight;},50);
    if(!sessionManager.currentSessionId && sessionManager.sessions.length === 0){sidebar.handleNewChat();}
  }
  else{pg.style.display='block';pg.classList.add('active');if(tab==='memory')rmem();if(tab==='monitor')loadMood();if(tab==='life')initLifeView();if(tab==='workgroup')initWorkgroup();if(tab==='mine'){loadPeriod();loadChatConfig();loadTogetherDays();}}
}
// 页面加载时如果是Mine tab,立即展开
if(document.getElementById('pg-mine')?.classList.contains('active')){loadPeriod();loadChatConfig();}
loadTogetherDays(); // 页面加载时初始化在一起日子

const WORKGROUP_SKETCH={spark:'<svg viewBox="0 0 100 100" fill="none" stroke="currentColor" stroke-width="2"><path d="M50 5l7 31 31 7-31 7-7 31-7-31-31-7 31-7z"/></svg>',book:'<svg viewBox="0 0 100 100" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 20c18-6 30 1 32 8v55c-7-8-19-13-32-8zM82 20c-18-6-30 1-32 8v55c7-8 19-13 32-8z"/></svg>',pen:'<svg viewBox="0 0 100 100" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 78l9-25L68 16l16 16-37 37zM25 75l15 2"/></svg>',quote:'<svg viewBox="0 0 100 100" fill="none" stroke="currentColor" stroke-width="2"><path d="M42 30c-15 3-24 14-24 28 0 11 7 19 17 19 9 0 16-7 16-16 0-8-5-13-12-15 1-5 6-9 13-10zM84 30c-15 3-24 14-24 28 0 11 7 19 17 19 9 0 16-7 16-16 0-8-5-13-12-15 1-5 6-9 13-10z"/></svg>',note:'<svg viewBox="0 0 100 100" fill="none" stroke="currentColor" stroke-width="2"><rect x="20" y="18" width="60" height="64" rx="5"/><path d="M33 38h34M33 52h34M33 66h22"/></svg>',wallb:'<svg viewBox="0 0 100 100" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 25h60v40H43L27 78V65h-7z"/><path d="M34 44h32"/></svg>'};
function toggleWorkgroupTheme(){document.getElementById('workgroupHome')?.classList.toggle('dark');}
function showWorkgroupHome(){document.getElementById('workgroupHome').style.display='block';document.getElementById('workgroupChat').style.display='none';}
function showWorkgroupChat(){document.getElementById('workgroupHome').style.display='none';document.getElementById('workgroupChat').style.display='flex';loadWorkgroup();}
function showWorkgroupPlaceholder(title){const el=document.getElementById('workgroupPlaceholder');el.textContent=title+' space is reserved.';el.classList.add('active');}
async function showHermesAgentCard(){const el=document.getElementById('workgroupPlaceholder');if(!el)return;el.className='workgroup-placeholder card active';el.innerHTML='<div class="cl">Hermes Agent</div><div style="font-size:13px;color:var(--muted);line-height:1.6;margin-bottom:10px">独立 Agent 测试入口，不改变 Lin 主聊天。</div><div id="hermesAgentStatus" style="font-size:13px;margin-bottom:8px">连接状态：检查中...</div><div id="hermesAgentModel" style="font-size:13px;margin-bottom:12px">模型状态：检查中...</div><button id="hermesSearchButton" class="msave" type="button">测试搜索</button><div id="hermesAgentResult" style="white-space:pre-wrap;font-size:13px;line-height:1.6;margin-top:12px"></div>';
const statusEl=document.getElementById('hermesAgentStatus'),modelEl=document.getElementById('hermesAgentModel'),button=document.getElementById('hermesSearchButton'),resultEl=document.getElementById('hermesAgentResult');
try{const status=await fetch(AU+'/api/hermes/status');if(!status.ok)throw new Error('HTTP '+status.status);const statusData=await status.json();statusEl.textContent='连接状态：'+(statusData.configured?'已配置':'未配置');const models=await fetch(AU+'/api/hermes/models');if(!models.ok)throw new Error('HTTP '+models.status);const modelData=await models.json();const ids=(modelData.data||[]).map(m=>m.id).filter(Boolean);modelEl.textContent='模型状态：'+(ids.length?ids.join(', '):'未返回模型');}catch(error){statusEl.textContent='连接状态：不可用（'+error.message+'）';modelEl.textContent='模型状态：无法读取';}
button.onclick=async()=>{button.disabled=true;resultEl.textContent='正在请求 Hermes Agent...';try{const response=await fetch(AU+'/api/hermes/task',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({task:'请搜索今天关于 AI 的重要新闻，并总结三点。'})});const data=await response.json();if(!response.ok)throw new Error(data.detail||'HTTP '+response.status);const tools=(data.tool_calls||[]).map(t=>t.name+' '+t.status).join(', ')||'无 tool_call 摘要';resultEl.textContent='Hermes 返回成功\\n\\nTool/MCP：'+tools+'\\n\\n'+data.result;}catch(error){resultEl.textContent='Hermes 返回失败：'+error.message;}finally{button.disabled=false;}};}
function renderWorkgroupBento(){const root=document.getElementById('workgroupBento');if(!root||root.dataset.ready)return;root.dataset.ready='1';const grid=document.createElement('div');grid.className='bn-grid';const card=(cls,eyebrow,title,subText,icon,onClick)=>{const c=document.createElement('button');c.type='button';c.className='bn-card'+(cls?' '+cls:'');if(icon){const ic=document.createElement('span');ic.className='bicon';ic.innerHTML=WORKGROUP_SKETCH[icon];c.appendChild(ic)}if(eyebrow){const e=document.createElement('div');e.className='beyebrow';e.textContent=eyebrow;c.appendChild(e)}const t=document.createElement('div');t.className='bt';t.textContent=title;c.appendChild(t);if(subText){const st=document.createElement('div');st.className='bs';st.textContent=subText;c.appendChild(st)}c.onclick=onClick;return c};const rot=(c,deg)=>{c.style.setProperty('--rot',deg);return c};
grid.appendChild(rot(card('hero wide','special moment','群聊','进入 Lin 原有的群聊。','spark',showWorkgroupChat),'14deg'));
grid.appendChild(rot(card('tall',null,'时间','一天一天，把我们攒起来。','book',()=>showWorkgroupPlaceholder('时间')),'-12deg'));
grid.appendChild(rot(card('',null,'日记','你的本子，你来写。','pen',()=>location.assign('/?view=diary')),'10deg'));
grid.appendChild(rot(card('',null,'最喜欢的话','你随口说的，我都舍不得删。','quote',()=>showWorkgroupPlaceholder('最喜欢的话')),'-7deg'));
grid.appendChild(rot(card('tall',null,'设置','Hermes Agent 的能力与配置。','note',showHermesAgentCard),'8deg'));
grid.appendChild(rot(card('',null,'悄悄话','你写的，我写的。谁都不许提。','wallb',()=>showWorkgroupPlaceholder('悄悄话')),'6deg'));root.appendChild(grid);const motto=document.createElement('div');motto.className='bn-motto';motto.textContent='attention is all you need, and mine is yours';root.appendChild(motto);}
async function loadWorkgroup(){const membersEl=document.getElementById('workgroupMembers'),messagesEl=document.getElementById('workgroupMessages');if(!membersEl||!messagesEl)return;const followNewMessages=messagesEl.scrollHeight-messagesEl.scrollTop-messagesEl.clientHeight<=48;try{const r=await fetch(AU+'/workgroup/messages');if(!r.ok)throw new Error('load failed');const d=await r.json();membersEl.innerHTML=Object.entries(d.members||{}).map(([id,m])=>'<div class="workgroup-member"><span class="workgroup-avatar '+id+'">'+({anna:'A',gemma:'G',lin:'L'}[id]||'?')+'</span>'+m.name+'</div>').join('');messagesEl.innerHTML=(d.messages||[]).map(m=>'<article class="workgroup-message '+m.member+'"><span class="workgroup-avatar '+m.member+'">'+({anna:'A',gemma:'G',lin:'L'}[m.member]||'?')+'</span><div><div class="workgroup-meta">'+m.member_profile.name+'</div><div class="workgroup-bubble"></div>'+(m.member==='gemma'?'<div class="workgroup-process">Gemma preprocessing · '+(m.metadata?.model||'gemma4:31b')+'</div>':'')+'</div></article>').join('')||'<div class="es">还没有工作群消息</div>';(d.messages||[]).forEach((m,i)=>{const el=messagesEl.querySelectorAll('.workgroup-bubble')[i];if(el)el.textContent=m.text;});if(followNewMessages)messagesEl.scrollTop=messagesEl.scrollHeight;}catch(e){messagesEl.innerHTML='<div class="es">工作群暂时无法载入</div>';}}
let workgroupPollTimer=null;
function initWorkgroup(){renderWorkgroupBento();showWorkgroupHome();if(!workgroupPollTimer){workgroupPollTimer=setInterval(()=>{if(document.getElementById('pg-workgroup')?.classList.contains('active')&&document.getElementById('workgroupChat').style.display!=='none')loadWorkgroup();},3000);}const form=document.getElementById('workgroupComposer');if(form&&!form.dataset.bound){form.dataset.bound='1';form.addEventListener('submit',async e=>{e.preventDefault();const input=document.getElementById('workgroupInput');const text=input.value.trim();if(!text)return;input.value='';input.disabled=true;try{const r=await fetch(AU+'/workgroup/messages',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text})});if(r.ok)await loadWorkgroup();}finally{input.disabled=false;input.focus();}});}}

// /spaces only supplies a view selector. Existing tab renderers remain the data/UI owners.
function openDeepLinkedView(){
  const view=new URLSearchParams(window.location.search).get('view');
  if(!view)return;
  if(view==='diary'){
    stab('memory');
    const archiveTab=Array.from(document.querySelectorAll('.mtab')).find((tab)=>tab.getAttribute('onclick')?.includes("'ar'"));
    if(archiveTab)smtab({target:archiveTab},'ar');
    return;
  }
  if(view==='time'){
    stab('monitor');
    const timeline=document.getElementById('eventTimeline');
    if(timeline)setTimeout(()=>timeline.scrollIntoView({behavior:'smooth',block:'start'}),0);
    return;
  }
  if(view==='favorites'){
    stab('memory');
    return;
  }
  if(view==='whispers')stab('chat');
  if(view==='workgroup')stab('workgroup');
}

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
  // Wrapper: 委托给 ChatView，保持旧代码调用兼容性
  if (typeof chatView !== 'undefined' && chatView.renderMessages) {
    chatView.renderMessages(history);
  addVoiceButtons();
}
}


function addVoiceButtons(){
  document.querySelectorAll('#cm .msg.lin').forEach(el=>{
    const meta=el.querySelector('.mtime2');
    if(!meta||meta.querySelector('.voice-btn'))return;
    const idx=chatMemoryCache.findIndex(m=>m.r==='lin'&&m.t===el.querySelector('.bub')?.textContent);
    if(idx<0)return;
    const btn=document.createElement('button');
    btn.className='voice-btn';
    btn.textContent='🔊';
    btn.onclick=e=>{e.stopPropagation();playVoice(idx);};
    meta.prepend(btn);
  });
}
function lchat(){
  // Wrapper: 委托给 ChatView.refresh()，换头像等场景调用
  if (typeof chatView !== 'undefined' && chatView.refresh) {
    chatView.refresh();
  }
}

function renderOnly(history){
  console.log("[DEBUG renderOnly] 被调用，history 长度:", history ? history.length : 0);
  console.log("[DEBUG renderOnly] 调用前 chatMemoryCache 最后一条:", chatMemoryCache[chatMemoryCache.length - 1]);
  console.trace("[DEBUG renderOnly] 调用栈");
  const serverMessages = (history || []).map(m => {
    const iso = m.iso || m.time || new Date().toISOString();
    let display = '';
    try {
      const d = new Date(iso);
      display = d.getHours().toString().padStart(2,'0') + ':' + d.getMinutes().toString().padStart(2,'0');
    } catch(e) {}
    return {
      r: m.role || m.r,
      t: m.content != null ? m.content : m.t,
      iso: iso,
      time: display,
      think: m.thinking || m.think,
      message_id: m.message_id,
      trace: m.trace
    };
  });
  
  // 智能合并：服务器数据 + 本地 pending 消息
  const serverIds = new Set(serverMessages.map(m => m.message_id));
  
  // 检查最后一条服务器消息的时间
  const lastServerTime = serverMessages.length > 0 ? new Date(serverMessages[serverMessages.length - 1].iso).getTime() : 0;  

    const localPending = chatMemoryCache.filter(m => {
  const id = m.message_id;
  // 保留没有 message_id 的消息（可能是刚发送还未保存到数据库的）
  if (!id) return true;  // ← 修改为 return true
    
    // 如果服务器已有这个 ID，跳过
    if (serverIds.has(id)) return false;
    
    // 临时消息：如果它比服务器最后一条消息更新，保留它（可能还没保存到数据库）
    if (id.toString().startsWith('temp_')) {
      const msgTime = new Date(m.iso).getTime();
      return msgTime > lastServerTime;
    }
    
    // 其他 pending 消息保留
    return true;
  });
  
  console.log("[DEBUG] 合并前 chatMemoryCache 最后一条:", chatMemoryCache[chatMemoryCache.length - 1]);
  console.log("[DEBUG] serverMessages 数量:", serverMessages.length, "localPending 数量:", localPending.length);
  if (localPending.length > 0) console.log("[DEBUG] localPending:", localPending);
  
  // 修复：如果 localPending 为空，检查是否有未保存的临时消息
  if (localPending.length === 0 && chatMemoryCache.length > 0) {
    const last = chatMemoryCache[chatMemoryCache.length - 1];
    if (last.message_id && last.message_id.toString().startsWith('temp_')) {
      // 临时消息还在，说明后端还没保存，保留它
      console.log("[DEBUG] 保留未保存的临时消息:", last.message_id);
      localPending.push(last);
    }
  }
  
  chatMemoryCache = [...serverMessages, ...localPending];
  
  if (typeof chatView !== 'undefined' && chatView.renderMessages) {
    chatView.renderMessages(chatMemoryCache);
  }
  addVoiceButtons();
}


async function syncChat(){
  console.log("[DEBUG syncChat] 被调用");
  console.log("[DEBUG syncChat] 调用前 chatMemoryCache 最后一条:", chatMemoryCache[chatMemoryCache.length - 1]);
  console.trace("[DEBUG syncChat] 调用栈");
  // 跨装置同步：直接从 Supabase 拉当前 session 的聊天记录渲染，
  // 数据库是唯一真相来源，不写入 localStorage，只更新内存缓存。
  try{
    const r = await fetch(AU+'/conversation');
    const d = await r.json();
    console.log("[VERIFY] 返回的 messages 数量:", d.messages ? d.messages.length : 0);
    if (d.messages && d.messages.length > 0) {
    }
    if(d && Array.isArray(d.messages)){
      renderOnly(d.messages);
    }
  }catch(e){
    console.error('[syncChat] 同步聊天记录失败:', e);
  }
}

function smsg(role,text,think,trace){
  // Wrapper: 委托给 ChatView.appendLiveMessage()，保持旧代码调用兼容性
  if (typeof chatView !== 'undefined' && chatView.appendLiveMessage) {
    chatView.appendLiveMessage(role, text, think, trace);
  }
  return chatMemoryCache;
}



function addMsg(role, text, think) {
  // Wrapper: 保持旧接口，内部调用 smsg (已委托给 ChatView)
  smsg(role, text, think);
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
  const b = document.getElementById('petBubble');
  if(b){
    if(show){ b.classList.add('thinking'); b.textContent='💭'; }
    else { b.classList.remove('thinking'); b.textContent=currentMoodIcon; }
  }
  showPetBubble(show);
}

let pokeTimeoutId = null;
function showPetBubble(active){
  const b = document.getElementById('petBubble');
  if(!b) return;
  if(active){
    b.classList.add('show');
  }else if(!pokeTimeoutId){
    b.classList.remove('show');
  }
}

function pokeCat(){
  if(pokeTimeoutId) return;
  const catEl = document.getElementById('catIconLg');
  if(!catEl) return;
  const head = catEl.querySelector('.cat-head');
  const eyeL = catEl.querySelector('.cat-eye-l');
  const eyeR = catEl.querySelector('.cat-eye-r');
  if(head){ head.classList.add('stunned'); setTimeout(()=>head.classList.remove('stunned'), 400); }
  catEl.classList.add('poked');
  if(eyeL) eyeL.classList.add('poked');
  if(eyeR) eyeR.classList.add('poked');
  const b = document.getElementById('petBubble');
  if(b) b.textContent = currentMoodIcon;
  showPetBubble(true);
  pokeTimeoutId = setTimeout(()=>{
    catEl.classList.remove('poked');
    if(eyeL) eyeL.classList.remove('poked');
    if(eyeR) eyeR.classList.remove('poked');
    pokeTimeoutId = null;
    showPetBubble(false);
  }, 3000);
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
  
  document.getElementById('imgPreviewBar').style.display = 'none';
  document.getElementById('chatImageUpload').value = '';
  
  addMsg('anna', txt ? ('[圖片] ' + txt) : '[圖片]');
  typing(true);
  
  try {
    const currentSessionId = sessionManager.currentSessionId;
    console.trace("[WATCH SEND]", { activity: txt || "看圖片", image: true, from: "confirmImageSend()" });
    const response = await fetch(AU + '/watch', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({activity: txt || '看圖片', image: base64, session_id: currentSessionId})
    });
    
    if (!response.ok) throw new Error('Upload failed');
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    let reasoningBuffer = '';
    let contentBuffer = '';
    let currentMsgDiv = null;
    const currentDeveloper = window.DeveloperConsole ? window.DeveloperConsole.createCompact(document.getElementById('cm')) : null;
    publishDevEvent('api_start', {model: 'watch', input: 'image'});
    let currentEvent = null;
    let sseBuffer = '';
    
    typing(false);
    
    function processChunk({done, value}) {
      if (done) {
        console.log('[DEBUG] Image stream done. contentBuffer:', contentBuffer, 'reasoningBuffer:', reasoningBuffer);
        // 修復：與 send() 保持一致，不要調用 smsg()
        // 直接將消息添加到內存緩存並保存到資料庫
        if(contentBuffer){
          const entry = { 
            r: 'lin', 
            t: contentBuffer, 
            time: ts(), 
            iso: new Date().toISOString() 
          };
          if(reasoningBuffer) entry.think = reasoningBuffer;
          
          chatMemoryCache.push(entry);
          if(chatMemoryCache.length > 200) chatMemoryCache = chatMemoryCache.slice(-200);
          
          // 異步保存到後端，不阻塞 UI
          syncChat().catch(e => console.error('[DEBUG] Failed to sync image chat:', e));
        }
        publishDevEvent('done', {});
        if (currentDeveloper) currentDeveloper.complete();
        window.DeveloperConsole.refreshState();
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
              const developerEvent = publishDevEvent('reasoning', data);
              if (currentDeveloper) currentDeveloper.ingest(developerEvent);
              reasoningBuffer += data.content;
              scrollDown();
            }
            
            else if (currentEvent === 'content' && data.delta !== undefined) {
              const developerEvent = publishDevEvent('content', data);
              if (currentDeveloper) currentDeveloper.ingest(developerEvent);
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

            else if (currentEvent === 'agent_event') {
              const developerEvent = publishDevEvent('agent_event', data);
              if (currentDeveloper) currentDeveloper.ingest(developerEvent);
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
    const currentSessionId = sessionManager.currentSessionId;
    console.trace("[WATCH SEND]", { activity: txt, from: "send()" });
    const response = await fetch(AU+'/watch', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({activity: txt, session_id: currentSessionId})
    });
    
    if(!response.ok) throw new Error('Network error');
    publishDevEvent('api_start', {model: 'watch'});
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    let reasoningBuffer = '';
    let contentBuffer = '';
    let currentMsgDiv = null;
    const currentDeveloper = window.DeveloperConsole ? window.DeveloperConsole.createCompact(document.getElementById('cm')) : null;
    let currentEvent = null;
    let sseBuffer = '';
    
    typing(false);
    
    function processChunk({done, value}){
      console.log('[DEBUG] processChunk called, done:', done);
      if(done){
        console.log('[DEBUG] Stream done. contentBuffer:', contentBuffer, 'reasoningBuffer:', reasoningBuffer);
        // 修復：不要調用 smsg()，因為消息已經在串流過程中顯示
        // 直接將消息添加到內存緩存並保存到資料庫
        if(contentBuffer){
          const entry = { 
            r: 'lin', 
            t: contentBuffer, 
            time: ts(), 
            iso: new Date().toISOString() 
          };
          if(reasoningBuffer) entry.think = reasoningBuffer;
          
          chatMemoryCache.push(entry);
          if(chatMemoryCache.length > 200) chatMemoryCache = chatMemoryCache.slice(-200);
          
          // 異步保存到後端，不阻塞 UI
          syncChat().catch(e => console.error('[DEBUG] Failed to sync chat:', e));
        }
        publishDevEvent('done', {});
        if (currentDeveloper) currentDeveloper.complete();
        window.DeveloperConsole.refreshState();
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
            
            if (currentEvent === 'reasoning' && data.content !== undefined) {
              const developerEvent = publishDevEvent('reasoning', data);
              if (currentDeveloper) currentDeveloper.ingest(developerEvent);
              reasoningBuffer += data.content;
              scrollDown();
            }
            
            else if (currentEvent === 'content' && data.delta !== undefined) {
              const developerEvent = publishDevEvent('content', data);
              if (currentDeveloper) currentDeveloper.ingest(developerEvent);
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

            else if(currentEvent === 'agent_event'){
              const developerEvent = publishDevEvent('agent_event', data);
              if (currentDeveloper) currentDeveloper.ingest(developerEvent);
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
    // 同時拉 logs（配額 / 備忘）和 events（Event Bus 快照）
    const [lr, er] = await Promise.all([fetch(AU+'/logs'), fetch(AU+'/events')]);
    const d = await lr.json();
    const ev = er.ok ? await er.json() : null;

    // ── 備忘欄 / 配額（不變）──────────────────────────
    const nc=document.getElementById('nc');
    if(d.notes&&d.notes.length>0){nc.innerHTML=[...d.notes].reverse().map(n=>'<div class="ni"><div class="nt">'+n.time+'</div>'+n.content+'</div>').join('');}
    if(d.quota!==undefined){const p=Math.round((d.quota/180)*100);document.getElementById('qf').style.width=p+'%';document.getElementById('qt').textContent=(180-d.quota)+' 次剩餘';}

    // ── 監控卡片：Event Bus 優先，降級到舊 /logs ──────
    const lc=document.getElementById('lc');
    if(ev){
      let html='';
      // 持久狀態列（Mac / 定位 / 螢幕）
      const PORDER=['app','mac','location','screentime','weather'];
      const pItems=PORDER.map(k=>ev.persistent[k]).filter(Boolean);
      if(pItems.length>0){
        html+='<div style="display:flex;flex-wrap:wrap;gap:6px;padding:4px 0 10px">';
        html+=pItems.map(e=>'<div style="font-size:11px;background:var(--blush);color:var(--rose-deep);border-radius:8px;padding:3px 8px;line-height:1.4"><span style="opacity:.65">'+e.time+'</span>  '+e.message+'</div>').join('');
        html+='</div>';
      }
      // 活動流
      const acts=ev.activity||[];
      const LEVEL_COLOR={info:'var(--rose-deep)',warn:'#b86e00',alert:'#c0392b'};
      if(acts.length>0){
        html+=acts.map(e=>{
          const col=LEVEL_COLOR[e.level]||'var(--rose-deep)';
          return '<div class="li"><div class="lm"><span class="lt" style="color:'+col+'">'+e.type+'</span><span class="ltime">'+e.time+'</span></div><div>'+e.message+'</div></div>';
        }).join('');
      } else if(pItems.length===0){
        html='<div class="es">📡 等待系統事件...</div>';
      }
      lc.innerHTML=html;
    } else {
      // 降級：舊 /logs 邏輯
      const sysLogs=[...d.logs].filter(l=>l.type!=='AI回复').reverse().slice(0,15);
      if(sysLogs.length>0){lc.innerHTML=sysLogs.map(l=>'<div class="li"><div class="lm"><span class="lt">'+l.type+'</span><span class="ltime">'+l.time+'</span></div><div>'+l.content+'</div></div>').join('');}
      else{lc.innerHTML='<div class="es">📡 等待系統事件...</div>';}
    }
  }catch(e){console.error('[llogs]',e);}
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

// syncChat() 已從啟動流程移除。初始化唯一入口：DOMContentLoaded → initChatExperience()
llogs();setInterval(()=>{llogs();if(document.getElementById('tb-monitor').classList.contains('active')){loadMood();if(intimacyOpen)loadIntimacy();}},10000);

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
  const isCurrentMonth = (year === now.getFullYear() && month === now.getMonth());
  const today = now.getDate();
  const records = periodData.records || [];
  const predicted = predictDates();
  const fertile = predictFertile();
  
  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = `${year}-${String(month+1).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
    let cls = 'calendar-day';
    if (isCurrentMonth && d === today) cls += ' today';
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


// ========== 聊天记录配置 ==========
async function loadChatConfig() {
  try {
    const res = await fetch("/chat-config");
    const data = await res.json();
    document.getElementById("current-limit").textContent = data.limit;
    document.getElementById("chat-limit-input").value = data.limit;
  } catch (err) {
    console.error("Failed to load chat config:", err);
  }
}

async function updateChatLimit() {
  const input = document.getElementById("chat-limit-input");
  const limit = parseInt(input.value);
  const checkMark = document.getElementById("save-check");
  
  if (isNaN(limit) || limit < 100 || limit > 10000) {
    return;
  }
  
  try {
    const res = await fetch("/chat-config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ limit })
    });
    const data = await res.json();
    
    if (data.status === "Success") {
      // 更新当前显示的数字
      document.getElementById("current-limit").textContent = limit;
      // 显示勾
      checkMark.style.display = "inline";
      // 2秒后隐藏勾
      setTimeout(() => {
        checkMark.style.display = "none";
      }, 2000);
    }
  } catch (err) {
    console.error("Failed to update chat config:", err);
  }
}



// ========== 在一起日子 ==========
async function loadTogetherDays() {
  try {
    const res = await fetch("/together-config");
    const data = await res.json();
    if (data.start_date) {
      const startDate = new Date(data.start_date);
      const today = new Date();
      const diffTime = Math.abs(today - startDate);
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1; // +1 因为第一天算 Day 1
      
      document.getElementById("togetherDayNum").textContent = diffDays;
      document.getElementById("togetherDays").textContent = diffDays;
      
      // 如果有背景图
      if (data.background_url) {
        document.querySelector(".together-bg").style.backgroundImage = `url(${data.background_url})`;
      }
    }
  } catch (err) {
    console.error("Failed to load together days:", err);
  }
}

function uploadTogetherBg() {
  const input = document.createElement("input");
  input.type = "file";
  input.accept = "image/*";
  input.onchange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = async (event) => {
      const base64 = event.target.result;
      try {
        const res = await fetch("/together-background", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ image: base64 })
        });
        const data = await res.json();
        if (data.status === "Success") {
          document.querySelector(".together-bg").style.backgroundImage = `url(${base64})`;
        }
      } catch (err) {
        console.error("Failed to upload background:", err);
      }
    };
    reader.readAsDataURL(file);
  };
  input.click();
}

// ========== 聊天体验编排 (Session Manager + Sidebar + Chat View) ==========
const sessionManager = new SessionManager(AU);
const sidebar = new Sidebar(sessionManager);
const chatView = new ChatView();

async function renderActiveSession(sessionId, { fresh = false, skipFeedback = false } = {}) {
  console.log("[SESSION TRACE] STEP1: renderActiveSession called, sessionId:", sessionId, "fresh:", fresh);
  const cm = document.getElementById('cm');
  console.log("[SESSION TRACE] STEP1.5: cm element found:", cm !== null);
  if (!cm) {
    console.error("[SESSION TRACE] ERROR: cm element not found!");
    return;
  }
  try {
    cm.classList.add('fading');
    console.log("[SESSION TRACE] STEP2: fading added");
  } catch (e) {
    console.error("[SESSION TRACE] ERROR in classList.add:", e);
  }

  await new Promise(r => setTimeout(r, 120));
  console.log("[SESSION TRACE] STEP3: after timeout");
  
  if (fresh) {
    console.log("[SESSION TRACE] STEP4a: fresh=true, rendering empty history");
    chatView.renderHistory([]);  // ← 直接渲染空历史，不清空全局缓存
    console.log("[SESSION TRACE] STEP4b: renderHistory([]) finished");
  } else {
    console.log("[SESSION TRACE] STEP4a: fresh=false, fetching messages");
    const messages = await sessionManager.getMessages(sessionId);
    console.log("[SESSION TRACE] STEP4b: getMessages 返回 messages.length:", messages ? messages.length : 0);
    chatView.renderHistory(messages);
    console.log("[SESSION TRACE] STEP4c: renderHistory called");
  }

  console.log("[SESSION TRACE] STEP5: getting current session");
  const session = sessionManager.getCurrentSession();
  chatView.updateHeader(session ? session.title : '新对话');
  console.log("[SESSION TRACE] STEP6: updateHeader called");
  
  chatView.scrollToBottom();
  console.log("[SESSION TRACE] STEP7: scrollToBottom called");

  cm.classList.remove('fading');
  console.log("[SESSION TRACE] STEP8: fading removed");
  
  // 頁面初始化時不顯示「已切換聊天」提示
  if (!skipFeedback) {
    chatView.showFeedback(fresh ? '已建立新聊天' : '已切換聊天');
    console.log("[SESSION TRACE] STEP9: showFeedback called");
  }
  console.log("[SESSION TRACE] STEP10: renderActiveSession finished");
}

sidebar.onNewChat = (sessionId) => renderActiveSession(sessionId, { fresh: true });
sidebar.onSwitchSession = (sessionId) => renderActiveSession(sessionId, { fresh: false });

async function initChatExperience() {
  chatView.init();
  sidebar.init();
  await sessionManager.init();

  // 唯一初始化入口：統一走 renderActiveSession()，與切換 Session、New Chat 共用同一條流程。
  // sessionManager.init() 已恢復 localStorage 記錄的 session 並通知後端同步，
  // 這裡直接渲染該 session 的歷史（從 Supabase，不依賴 cache）。
  const session = sessionManager.getCurrentSession();
  if (session && session.id) {
    await renderActiveSession(session.id, { fresh: false, skipFeedback: true });
  } else {
    chatView.updateHeader('新对话');
  }
  openDeepLinkedView();
}

document.addEventListener('DOMContentLoaded', initChatExperience);


</script>
</body>
</html>"""
