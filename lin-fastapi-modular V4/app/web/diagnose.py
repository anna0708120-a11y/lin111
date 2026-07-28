"""
臨時診斷頁：用於在 iPhone 實機（Safari browser 模式 / standalone PWA 模式）
讀取真實的 viewport / safe-area / .tab-bar 尺寸數值。

這個檔案只做「讀取並顯示」，不修改任何正式頁面的 CSS 或邏輯。
驗證完成後可以直接刪除這個檔案 + routes.py 裡對應的路由。
"""

DIAGNOSE_HTML = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<title>Diagnose</title>
<style>
:root{--safe-top:env(safe-area-inset-top);--safe-bottom:env(safe-area-inset-bottom);}
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:-apple-system,sans-serif;background:#FAF8F5;color:#2C2320;padding:16px;padding-top:calc(16px + var(--safe-top));}
h1{font-size:18px;margin-bottom:4px;}
.hint{font-size:12px;color:#9B8F8A;margin-bottom:16px;}
.row{display:flex;justify-content:space-between;gap:12px;padding:10px 12px;background:#fff;border-radius:8px;margin-bottom:6px;font-size:13px;border:1px solid #E8DDD9;}
.row.warn{background:#FDECEC;border-color:#E8A5A5;}
.row.ok{background:#EAF6EA;border-color:#A5D6A5;}
.label{color:#5a4540;flex-shrink:0;}
.val{font-family:ui-monospace,monospace;font-weight:600;text-align:right;word-break:break-all;}
.section{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:#C9897A;margin:18px 0 8px;font-weight:600;}
.copybox{width:100%;height:180px;margin-top:16px;font-family:ui-monospace,monospace;font-size:11px;padding:10px;border:1px solid #E8DDD9;border-radius:8px;}
button{margin-top:10px;width:100%;padding:12px;background:#C9897A;color:#fff;border:none;border-radius:8px;font-size:14px;font-weight:600;}
.tabbar-fake{display:flex;background:#fff;border-top:1px solid #E8DDD9;position:fixed;bottom:0;left:0;right:0;padding-bottom:var(--safe-bottom);z-index:200;height:56px;}
</style>
</head>
<body>
<h1>Diagnose 診斷頁</h1>
<div class="hint">加入主畫面後從主畫面開啟，並在此頁面比對「Safari 模式」與「standalone 模式」的差異。</div>

<div class="section">運行模式</div>
<div class="row" id="row-standalone"><span class="label">navigator.standalone</span><span class="val" id="v-standalone">-</span></div>
<div class="row" id="row-displaymode"><span class="label">display-mode: standalone (matchMedia)</span><span class="val" id="v-displaymode">-</span></div>

<div class="section">Viewport 真實數值</div>
<div class="row"><span class="label">window.innerWidth</span><span class="val" id="v-iw">-</span></div>
<div class="row"><span class="label">window.innerHeight</span><span class="val" id="v-ih">-</span></div>
<div class="row"><span class="label">visualViewport.height</span><span class="val" id="v-vvh">-</span></div>
<div class="row"><span class="label">document.documentElement.clientHeight</span><span class="val" id="v-dch">-</span></div>

<div class="section">Safe Area</div>
<div class="row"><span class="label">--safe-bottom (computed)</span><span class="val" id="v-safebottom">-</span></div>
<div class="row"><span class="label">--safe-top (computed)</span><span class="val" id="v-safetop">-</span></div>

<div class="section">模擬 .tab-bar（本頁底部灰條，樣式與正式頁一致）</div>
<div class="row"><span class="label">.tabbar-fake top</span><span class="val" id="v-tbtop">-</span></div>
<div class="row"><span class="label">.tabbar-fake bottom</span><span class="val" id="v-tbbottom">-</span></div>
<div class="row"><span class="label">.tabbar-fake height</span><span class="val" id="v-tbheight">-</span></div>
<div class="row" id="row-gap"><span class="label">Gap = innerHeight - tabBar.bottom</span><span class="val" id="v-gap">-</span></div>

<textarea class="copybox" id="copytext" readonly></textarea>
<button onclick="copyResult()">複製全部結果</button>

<div class="tabbar-fake"></div>

<script>
function diagnose(){
  const tb = document.querySelector('.tabbar-fake');
  const rect = tb.getBoundingClientRect();
  const rootStyle = getComputedStyle(document.documentElement);

  const standalone = window.navigator.standalone;
  const displayModeStandalone = window.matchMedia('(display-mode: standalone)').matches;

  document.getElementById('v-standalone').textContent = String(standalone);
  document.getElementById('v-displaymode').textContent = String(displayModeStandalone);
  document.getElementById('row-standalone').className = 'row ' + (standalone ? 'ok' : 'warn');

  document.getElementById('v-iw').textContent = window.innerWidth;
  document.getElementById('v-ih').textContent = window.innerHeight;
  document.getElementById('v-vvh').textContent = window.visualViewport ? window.visualViewport.height : 'N/A';
  document.getElementById('v-dch').textContent = document.documentElement.clientHeight;

  document.getElementById('v-safebottom').textContent = rootStyle.getPropertyValue('--safe-bottom');
  document.getElementById('v-safetop').textContent = rootStyle.getPropertyValue('--safe-top');

  document.getElementById('v-tbtop').textContent = rect.top.toFixed(1);
  document.getElementById('v-tbbottom').textContent = rect.bottom.toFixed(1);
  document.getElementById('v-tbheight').textContent = rect.height.toFixed(1);

  const gap = window.innerHeight - rect.bottom;
  document.getElementById('v-gap').textContent = gap.toFixed(1) + 'px';
  document.getElementById('row-gap').className = 'row ' + (Math.abs(gap) > 2 ? 'warn' : 'ok');

  const summary = [
    '=== Diagnose Result ===',
    'time: ' + new Date().toISOString(),
    'userAgent: ' + navigator.userAgent,
    'navigator.standalone: ' + standalone,
    'matchMedia(display-mode:standalone): ' + displayModeStandalone,
    'innerWidth: ' + window.innerWidth,
    'innerHeight: ' + window.innerHeight,
    'visualViewport.height: ' + (window.visualViewport ? window.visualViewport.height : 'N/A'),
    'documentElement.clientHeight: ' + document.documentElement.clientHeight,
    '--safe-bottom: ' + rootStyle.getPropertyValue('--safe-bottom'),
    '--safe-top: ' + rootStyle.getPropertyValue('--safe-top'),
    'tabBar.top: ' + rect.top.toFixed(1),
    'tabBar.bottom: ' + rect.bottom.toFixed(1),
    'tabBar.height: ' + rect.height.toFixed(1),
    'gap(innerHeight-tabBar.bottom): ' + gap.toFixed(1)
  ].join('\\n');
  document.getElementById('copytext').value = summary;
}

function copyResult(){
  const t = document.getElementById('copytext');
  t.select();
  document.execCommand('copy');
  alert('已複製，請貼給 Kiro');
}

diagnose();
window.addEventListener('resize', diagnose);
window.addEventListener('orientationchange', diagnose);
if (window.visualViewport) window.visualViewport.addEventListener('resize', diagnose);
</script>
</body>
</html>"""
