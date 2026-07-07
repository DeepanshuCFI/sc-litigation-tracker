#!/usr/bin/env python3
"""Generate dashboard/index.html from data/cases.json (self-contained, CFI design system)."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / "data" / "cases.json").read_text())

TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Road Safety in the Supreme Court — Crashfree India</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@500;600;700&display=swap');
:root{
  --brand:#4A35FF; --brand-lite:#F3F1FF; --brand-soft:#F8F7FF;
  --danger:#F10015; --warning:#F57C00; --success:#00AA44;
  --dark:#1a1c1c; --muted:#777589; --border:#EDEEF2; --white:#FFFFFF;
}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:Geist,-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;color:var(--dark);background:var(--white);line-height:1.6}
h1,h2,h3,h4,.heading{font-family:Montserrat,-apple-system,sans-serif}
.wrap{max-width:1280px;margin:0 auto;padding:0 24px}
@media(min-width:768px){.wrap{padding:0 40px}}
section{border-top:1px solid var(--border)}
.eyebrow{display:inline-flex;align-items:center;gap:8px;font-family:Montserrat;font-size:11px;font-weight:500;letter-spacing:.25em;color:var(--brand);text-transform:uppercase}
a{color:var(--brand);text-decoration:none}
a:hover{text-decoration:underline}

/* hero */
.hero{position:relative;padding:64px 0 48px;background:radial-gradient(circle at 18% 18%,rgba(74,53,255,.10),transparent 60%)}
.hero h1{font-size:clamp(34px,5vw,56px);font-weight:700;line-height:1.05;letter-spacing:-.01em;max-width:900px;margin-top:20px}
.hero h1 .accent{color:var(--brand)}
.hero p.lead{margin-top:20px;max-width:760px;font-size:17px;color:var(--muted)}
.hero .updated{margin-top:14px;font-size:13px;color:var(--muted)}

/* stat strip */
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:16px;margin:40px 0 56px}
.stat{border:1px solid var(--border);border-radius:16px;background:var(--white);padding:20px}
.stat .num{font-family:Montserrat;font-size:36px;font-weight:700;color:var(--brand);line-height:1}
.stat .num.live{color:var(--warning)}
.stat .lbl{margin-top:8px;font-size:13px;color:var(--muted)}

/* filters */
.filters{padding:24px 0;display:flex;flex-wrap:wrap;gap:12px;align-items:center}
.fbtn{font-family:Montserrat;font-size:12px;font-weight:600;letter-spacing:.05em;border:1px solid var(--border);background:var(--white);color:var(--muted);border-radius:9999px;padding:9px 18px;cursor:pointer;transition:.15s}
.fbtn:hover{border-color:rgba(74,53,255,.4);color:var(--brand)}
.fbtn.active{background:var(--brand);border-color:var(--brand);color:#fff}
.search{flex:1;min-width:220px;max-width:360px;border:1px solid var(--border);border-radius:9999px;padding:10px 18px;font-size:14px;font-family:inherit;color:var(--dark);outline:none}
.search:focus{border-color:rgba(74,53,255,.5)}
.tchip{font-size:12px;border:1px solid var(--border);background:var(--white);color:var(--muted);border-radius:9999px;padding:6px 14px;cursor:pointer;transition:.15s}
.tchip:hover{border-color:rgba(74,53,255,.4)}
.tchip.active{background:var(--brand-lite);border-color:rgba(74,53,255,.25);color:var(--brand);font-weight:500}

/* case cards */
.cases{padding:8px 0 72px;background:var(--white)}
.case{border:1px solid var(--border);border-radius:16px;background:var(--white);padding:26px;margin-bottom:20px;transition:.15s}
.case:hover{border-color:rgba(74,53,255,.4);box-shadow:0 8px 24px rgba(74,53,255,.05)}
.case-head{display:flex;flex-wrap:wrap;gap:10px 14px;align-items:center}
.case h3{font-size:19px;font-weight:600;line-height:1.35;flex:1 1 340px}
.badge{font-family:Montserrat;font-size:10.5px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;border-radius:9999px;padding:5px 13px;white-space:nowrap}
.badge.pending{background:rgba(74,53,255,.10);color:var(--brand);border:1px solid rgba(74,53,255,.25)}
.badge.monitoring{background:rgba(245,124,0,.10);color:var(--warning);border:1px solid rgba(245,124,0,.3)}
.badge.disposed{background:var(--brand-soft);color:var(--muted);border:1px solid var(--border)}
.badge.new{background:rgba(0,170,68,.10);color:var(--success);border:1px solid rgba(0,170,68,.3)}
.case .meta{width:100%;margin-top:2px;font-size:13px;color:var(--muted)}
.case .meta b{color:var(--dark);font-weight:500}
.case .why{margin-top:14px;font-size:14.5px;color:var(--muted);max-width:900px}
.case .latest{margin-top:14px;border-left:3px solid var(--brand);background:var(--brand-soft);border-radius:0 12px 12px 0;padding:12px 16px;font-size:14px}
.case .latest b{font-family:Montserrat;font-size:11px;font-weight:700;letter-spacing:.15em;color:var(--brand);display:block;margin-bottom:4px}
.themes{margin-top:14px;display:flex;flex-wrap:wrap;gap:8px}
.theme{font-size:11.5px;border:1px solid var(--border);background:var(--white);color:var(--muted);border-radius:9999px;padding:4px 12px}
.toggle{margin-top:16px;font-family:Montserrat;font-size:12px;font-weight:600;letter-spacing:.08em;color:var(--brand);background:none;border:none;cursor:pointer;padding:0}
.timeline{display:none;margin-top:18px;border-top:1px solid var(--border);padding-top:16px}
.timeline.open{display:block}
.trow{display:flex;gap:14px;padding:7px 0;font-size:13.5px}
.trow .dot{flex:0 0 8px;height:8px;border-radius:50%;background:var(--border);margin-top:7px}
.trow.major .dot{background:var(--brand)}
.trow .tdate{flex:0 0 92px;color:var(--muted);font-variant-numeric:tabular-nums}
.trow.major .tdate{color:var(--dark);font-weight:500}
.trow .tbody{flex:1}
.trow .tbody .gist{color:var(--dark)}
.trow .tbody a{font-size:12.5px;white-space:nowrap}
.tmore{font-size:12.5px;color:var(--muted);padding:6px 0 0 114px;font-style:italic}
.empty{padding:48px 0;text-align:center;color:var(--muted)}

/* notable judgments — brand section */
.notable{background:var(--brand);padding:64px 0 72px}
.notable .eyebrow{color:#C8C0FF}
.notable h2{color:#fff;font-size:clamp(26px,3.4vw,38px);font-weight:700;line-height:1.1;margin-top:16px}
.notable h2 .accent{color:#C8C0FF}
.notable p.lead{color:rgba(255,255,255,.75);margin-top:14px;max-width:720px;font-size:15px}
.njgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:20px;margin-top:36px}
.nj{border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.04);border-radius:20px;padding:24px}
.nj .njdate{font-family:Montserrat;font-size:11px;font-weight:700;letter-spacing:.15em;color:#C8C0FF}
.nj h4{color:#fff;font-size:15.5px;font-weight:600;margin-top:8px;line-height:1.4}
.nj p{color:rgba(255,255,255,.72);font-size:13.5px;margin-top:8px}
.nj a{color:#C8C0FF;font-size:12.5px;display:inline-block;margin-top:10px}

/* watchlist + footer */
.watch{background:var(--brand-soft);padding:56px 0 64px}
.watch h2{font-size:clamp(24px,3vw,32px);font-weight:700;margin-top:16px}
.watch h2 .accent{color:var(--brand)}
.wgrid{margin-top:28px;display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px}
.wcard{border:1px solid var(--border);border-radius:16px;background:var(--white);padding:20px}
.wcard .wc-cases{font-family:Montserrat;font-size:13.5px;font-weight:600;line-height:1.5}
.wcard .wc-why{margin-top:8px;font-size:13px;color:var(--muted)}
footer{border-top:1px solid var(--border);padding:36px 0 48px;font-size:13px;color:var(--muted)}
footer .brand{font-family:Montserrat;font-weight:700;color:var(--dark)}
footer p{max-width:820px;margin-top:6px}
</style>
</head>
<body>

<div class="hero">
  <div class="wrap">
    <span class="eyebrow">Litigation Tracker · Supreme Court</span>
    <h1>Road safety in the<br><span class="accent">Supreme Court of India.</span></h1>
    <p class="lead">Every systemic road-safety case before the Supreme Court — PILs, suo motu matters and appeals that produced nationwide directions — tracked order by order, alongside the judgments that set precedent for crash victims. High Courts follow in phase 2.</p>
    <p class="updated">Last refreshed <b id="last-refresh"></b> · Source: Indian Kanoon (Supreme Court judgments + daily orders)</p>
    <div class="stats" id="stats"></div>
  </div>
</div>

<section class="cases">
  <div class="wrap">
    <div class="filters">
      <button class="fbtn active" data-status="all">All cases</button>
      <button class="fbtn" data-status="pending">Pending</button>
      <button class="fbtn" data-status="monitoring">Compliance monitoring</button>
      <button class="fbtn" data-status="disposed">Disposed</button>
      <input class="search" id="search" type="search" placeholder="Search cases, numbers, orders…">
    </div>
    <div class="filters" id="theme-chips" style="padding-top:0"></div>
    <div id="case-list"></div>
  </div>
</section>

<section class="notable">
  <div class="wrap">
    <span class="eyebrow">Precedent Feed</span>
    <h2>Judgments that set the rules<br><span class="accent">for every crash victim.</span></h2>
    <p class="lead">Not systemic monitoring cases — but the rulings every MACT, insurer and claimant lawyer works from.</p>
    <div class="njgrid" id="nj-grid"></div>
  </div>
</section>

<section class="watch">
  <div class="wrap">
    <span class="eyebrow">Watchlist</span>
    <h2>Reviewed and set aside<br><span class="accent">— for now.</span></h2>
    <div class="wgrid" id="watch-grid"></div>
  </div>
</section>

<footer>
  <div class="wrap">
    <span class="brand">Crashfree India</span> · Supreme Court Road Safety Litigation Tracker
    <p>Order gists are working summaries prepared for advocacy tracking, not legal advice. Full text of every order is linked to Indian Kanoon. Case discovery runs weekly across judgments and daily orders; newly filed systemic matters are flagged automatically.</p>
  </div>
</footer>

<script id="data" type="application/json">__DATA__</script>
<script>
const DB = JSON.parse(document.getElementById('data').textContent);
const $ = s => document.querySelector(s);
const fmt = d => d ? new Date(d+'T00:00:00').toLocaleDateString('en-IN',{day:'numeric',month:'short',year:'numeric'}) : '—';

// stats
const live = DB.cases.filter(c=>c.status==='pending').length;
const mon  = DB.cases.filter(c=>c.status==='monitoring').length;
const disp = DB.cases.filter(c=>c.status==='disposed').length;
const orders = DB.cases.reduce((n,c)=>n+c.order_count,0);
$('#last-refresh').textContent = fmt(DB.meta.built);
$('#stats').innerHTML = [
  [DB.cases.length,'systemic cases tracked',''],
  [live,'pending before the Court','live'],
  [mon,'under compliance monitoring','live'],
  [disp,'disposed with directions',''],
  [orders,'orders indexed',''],
  [DB.notable_judgments.length,'precedent judgments','']
].map(([n,l,c])=>`<div class="stat"><div class="num ${c}">${n}</div><div class="lbl">${l}</div></div>`).join('');

// theme chips
const themes = [...new Set(DB.cases.flatMap(c=>c.themes||[]))].sort();
$('#theme-chips').innerHTML = themes.map(t=>`<button class="tchip" data-theme="${t}">${t}</button>`).join('');

let fStatus='all', fTheme=null, fText='';
function statusLabel(s){return s==='pending'?'Pending':s==='monitoring'?'Monitoring':'Disposed';}

function render(){
  const newSet = new Set(DB.new_this_refresh||[]);
  const list = DB.cases.filter(c=>{
    if(fStatus!=='all' && c.status!==fStatus) return false;
    if(fTheme && !(c.themes||[]).includes(fTheme)) return false;
    if(fText){
      const hay=(c.title+' '+c.case_number+' '+(c.why_it_matters||'')+' '+(c.latest_development||'')+' '
        +c.orders.map(o=>o.gist).join(' ')).toLowerCase();
      if(!hay.includes(fText)) return false;
    }
    return true;
  }).sort((a,b)=>(b.latest_order||'').localeCompare(a.latest_order||''));

  $('#case-list').innerHTML = list.length ? list.map(c=>{
    const majors=c.orders.filter(o=>o.significance==='major');
    const routine=c.orders.length-majors.length;
    const rows=c.orders.slice().reverse().map(o=>`
      <div class="trow ${o.significance==='major'?'major':''}">
        <div class="dot"></div>
        <div class="tdate">${fmt(o.date)}</div>
        <div class="tbody">${o.gist?`<span class="gist">${o.gist}</span> `:''}<a href="${o.link}" target="_blank" rel="noopener">Read order ↗</a></div>
      </div>`).join('');
    return `<div class="case" data-id="${c.id}">
      <div class="case-head">
        <h3>${c.title}</h3>
        ${newSet.has(c.id)?'<span class="badge new">New</span>':''}
        <span class="badge ${c.status}">${statusLabel(c.status)}</span>
        <div class="meta"><b>${c.case_number}</b> · ${c.case_type} · filed ${c.filed_year} · ${c.order_count} orders on record (${fmt(c.first_order)} → ${fmt(c.latest_order)})</div>
      </div>
      <p class="why">${c.why_it_matters||''}</p>
      ${c.latest_development?`<div class="latest"><b>Latest development</b>${c.latest_development}</div>`:''}
      <div class="themes">${(c.themes||[]).map(t=>`<span class="theme">${t}</span>`).join('')}</div>
      <button class="toggle" data-toggle="${c.id}">Show order timeline (${c.order_count}) ▾</button>
      <div class="timeline" id="tl-${c.id}">${rows}${routine>0?`<div class="tmore">${majors.length} orders summarised above are marked significant; the remaining ${routine} are procedural (listings, extensions, exemptions).</div>`:''}</div>
    </div>`;
  }).join('') : '<div class="empty">No cases match the current filters.</div>';

  document.querySelectorAll('[data-toggle]').forEach(b=>b.addEventListener('click',()=>{
    const tl=document.getElementById('tl-'+b.dataset.toggle);
    tl.classList.toggle('open');
    b.textContent=b.textContent.includes('▾')?b.textContent.replace('Show','Hide').replace('▾','▴'):b.textContent.replace('Hide','Show').replace('▴','▾');
  }));
}

document.querySelectorAll('.fbtn').forEach(b=>b.addEventListener('click',()=>{
  document.querySelectorAll('.fbtn').forEach(x=>x.classList.remove('active'));
  b.classList.add('active'); fStatus=b.dataset.status; render();
}));
document.querySelectorAll('.tchip').forEach(b=>b.addEventListener('click',()=>{
  const on=b.classList.contains('active');
  document.querySelectorAll('.tchip').forEach(x=>x.classList.remove('active'));
  fTheme=on?null:b.dataset.theme; if(!on)b.classList.add('active'); render();
}));
$('#search').addEventListener('input',e=>{fText=e.target.value.trim().toLowerCase();render();});

// notable judgments
$('#nj-grid').innerHTML = DB.notable_judgments.map(j=>`
  <div class="nj"><div class="njdate">${fmt(j.date)}</div><h4>${j.title}</h4><p>${j.gist}</p>
  <a href="${j.link}" target="_blank" rel="noopener">Read judgment ↗</a></div>`).join('');

// watchlist
$('#watch-grid').innerHTML = DB.borderline_excluded.map(w=>`
  <div class="wcard"><div class="wc-cases">${w.cases.join('<br>')}</div><div class="wc-why">${w.why}</div></div>`).join('');

render();
</script>
</body>
</html>
"""


def main() -> None:
    payload = json.dumps(DATA, ensure_ascii=False).replace("</", "<\\/")
    html = TEMPLATE.replace("__DATA__", payload)
    out = ROOT / "docs" / "index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(html)
    print(f"wrote {out} ({len(html)//1024} KB)")


if __name__ == "__main__":
    main()
