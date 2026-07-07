#!/usr/bin/env python3
"""Generate docs/index.html from data/cases.json.

Layout follows the Crashfree India design system (CFI_Skill v2.2) to the letter:
section wrapper (max-w-7xl, px-6/10, py-24/32), background rotation
(background -> brand-lite -> brand), section anatomy (eyebrow -> two-line H2 ->
lead -> grid), Montserrat + Geist only, semantic color tokens only.
The docket is split into three sections: PIL & Writs / Suo Motu / Appeals &
References — cases self-sort by case_type.
"""

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
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@500;600;700&family=Geist:wght@400;500;700&display=swap');
:root{
  --brand:#4A35FF; --brand-lite:#F8F7FF; --lavender:#F3F1FF; --lav-text:#C8C0FF;
  --danger:#F10015; --warning:#F57C00; --success:#00AA44;
  --dark:#1a1c1c; --muted:#777589; --border:#EDEEF2; --white:#FFFFFF;
}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:Geist,-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;color:var(--dark);background:var(--white);line-height:1.6;font-size:16px}
h1,h2,h3,h4{font-family:Montserrat,-apple-system,sans-serif}
a{color:var(--brand);text-decoration:none}
a:hover{text-decoration:underline}
.wrap{max-width:1280px;margin:0 auto;padding:0 24px}
@media(min-width:768px){.wrap{padding:0 40px}}
section{border-top:1px solid var(--border)}
.sect{padding:96px 0}
@media(min-width:1024px){.sect{padding:128px 0}}
.eyebrow{display:inline-flex;align-items:center;gap:8px;font-family:Montserrat;font-size:11px;font-weight:500;letter-spacing:.25em;color:var(--brand);text-transform:uppercase}
.h2{margin-top:24px;max-width:900px;font-size:clamp(32px,4.2vw,48px);font-weight:700;line-height:1.05;letter-spacing:-.01em}
.h2 .accent{color:var(--brand)}
.lead{margin-top:24px;max-width:760px;font-size:16px;color:var(--muted)}
@media(min-width:640px){.lead{font-size:18px}}

/* hero */
.hero{position:relative;border-top:none;padding:96px 0 64px;overflow:hidden}
@media(min-width:1024px){.hero{padding:128px 0 64px}}
.hero .glow{position:absolute;inset:0;z-index:-1;background:radial-gradient(circle at 18% 18%,rgba(74,53,255,.12),transparent 60%)}
.hero h1{margin-top:24px;max-width:920px;font-size:clamp(40px,6vw,64px);font-weight:700;line-height:1.02;letter-spacing:-.01em}
.hero h1 .accent{color:var(--brand)}
.hero .meta{margin-top:16px;font-size:14px;color:var(--muted)}
.cta-row{margin-top:32px;display:flex;flex-wrap:wrap;gap:12px}
.btn{display:inline-flex;align-items:center;gap:8px;height:48px;padding:0 28px;border-radius:9999px;font-family:Geist;font-size:16px;cursor:pointer;transition:.15s;text-decoration:none}
.btn:hover{text-decoration:none}
.btn-primary{background:var(--brand);color:#fff;border:none;box-shadow:0 10px 24px rgba(74,53,255,.3)}
.btn-primary:hover{background:rgba(74,53,255,.9)}
.btn-secondary{background:var(--white);color:var(--dark);border:1px solid var(--border)}
.btn-secondary:hover{border-color:rgba(74,53,255,.4)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:16px;margin-top:48px}
.stat{border:1px solid var(--border);border-radius:16px;background:var(--white);padding:24px}
.stat .num{font-family:Montserrat;font-size:36px;font-weight:700;color:var(--brand);line-height:1}
.stat .num.watch{color:var(--warning)}
.stat .lbl{margin-top:8px;font-size:14px;color:var(--muted)}

/* filters */
.filters{margin-top:48px;display:flex;flex-wrap:wrap;gap:12px;align-items:center}
.fbtn{font-family:Montserrat;font-size:12px;font-weight:600;letter-spacing:.05em;min-height:44px;padding:0 20px;border:1px solid var(--border);background:var(--white);color:var(--muted);border-radius:9999px;cursor:pointer;transition:.15s}
.fbtn:hover{border-color:rgba(74,53,255,.4);color:var(--brand)}
.fbtn.active{background:var(--brand);border-color:var(--brand);color:#fff}
.search{flex:1;min-width:240px;max-width:380px;min-height:44px;border:1px solid var(--border);border-radius:9999px;padding:0 20px;font-size:16px;font-family:inherit;color:var(--dark);outline:none;background:var(--white)}
.search:focus{border-color:rgba(74,53,255,.5)}
.tchips{margin-top:16px;display:flex;flex-wrap:wrap;gap:8px}
.tchip{font-size:12px;min-height:32px;border:1px solid var(--border);background:var(--white);color:var(--muted);border-radius:9999px;padding:4px 16px;cursor:pointer;transition:.15s}
.tchip:hover{border-color:rgba(74,53,255,.4)}
.tchip.active{background:rgba(74,53,255,.1);border-color:rgba(74,53,255,.25);color:var(--brand);font-weight:500}
.fnote{margin-top:16px;font-size:13px;color:var(--muted)}

/* docket group sections */
.group-top{display:flex;align-items:flex-end;justify-content:space-between;gap:24px;flex-wrap:wrap}
.gcount{text-align:right}
.gcount .num{font-family:Montserrat;font-size:clamp(60px,7vw,96px);font-weight:700;color:var(--brand);line-height:.9}
.gcount .lbl{font-size:14px;color:var(--muted);margin-top:4px}
.case-list{margin-top:48px}
.case{border:1px solid var(--border);border-radius:16px;background:var(--white);padding:24px;margin-bottom:20px;transition:.15s}
.case:hover{border-color:rgba(74,53,255,.4);box-shadow:0 8px 24px rgba(74,53,255,.05)}
.case-head{display:flex;flex-wrap:wrap;gap:12px;align-items:center}
.case h3{font-size:20px;font-weight:600;line-height:1.4;flex:1 1 340px}
.chip-type{font-family:Montserrat;font-size:10.5px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;border-radius:9999px;padding:6px 14px;background:rgba(74,53,255,.1);border:1px solid rgba(74,53,255,.25);color:var(--brand);white-space:nowrap}
.badge{font-family:Montserrat;font-size:10.5px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;border-radius:9999px;padding:6px 14px;white-space:nowrap}
.badge.pending{background:rgba(74,53,255,.1);color:var(--brand);border:1px solid rgba(74,53,255,.25)}
.badge.monitoring{background:rgba(245,124,0,.1);color:var(--warning);border:1px solid rgba(245,124,0,.3)}
.badge.disposed{background:var(--brand-lite);color:var(--muted);border:1px solid var(--border)}
.badge.new{background:rgba(0,170,68,.1);color:var(--success);border:1px solid rgba(0,170,68,.3)}
.case .meta{width:100%;margin-top:4px;font-size:14px;color:var(--muted)}
.case .meta b{color:var(--dark);font-weight:500}
.case .why{margin-top:16px;font-size:15px;color:var(--muted);max-width:900px}
.case .latest{margin-top:16px;border-left:3px solid var(--brand);background:var(--brand-lite);border-radius:0 12px 12px 0;padding:12px 16px;font-size:14px}
.case .latest b{font-family:Montserrat;font-size:11px;font-weight:700;letter-spacing:.15em;color:var(--brand);display:block;margin-bottom:4px}
.themes{margin-top:16px;display:flex;flex-wrap:wrap;gap:8px}
.theme{font-size:12px;border:1px solid var(--border);background:var(--white);color:var(--muted);border-radius:9999px;padding:4px 12px}
.toggle{margin-top:16px;font-family:Montserrat;font-size:12px;font-weight:600;letter-spacing:.08em;color:var(--brand);background:none;border:none;cursor:pointer;padding:8px 0;min-height:44px}
.timeline{display:none;margin-top:16px;border-top:1px solid var(--border);padding-top:16px}
.timeline.open{display:block}
.trow{display:flex;gap:16px;padding:8px 0;font-size:14px}
.trow .dot{flex:0 0 8px;height:8px;border-radius:50%;background:var(--border);margin-top:8px}
.trow.major .dot{background:var(--brand)}
.trow .tdate{flex:0 0 96px;color:var(--muted);font-variant-numeric:tabular-nums}
.trow.major .tdate{color:var(--dark);font-weight:500}
.trow .tbody{flex:1}
.trow .tbody .gist{color:var(--dark)}
.trow .tbody a{font-size:13px;white-space:nowrap}
.tmore{font-size:13px;color:var(--muted);padding:8px 0 0 120px;font-style:italic}
.gempty{margin-top:48px;padding:32px 0;color:var(--muted);font-size:15px}
.bg-lite{background:var(--brand-lite)}
.bg-lite .case,.bg-lite .stat{background:var(--white)}

/* precedent feed — brand section */
.notable{background:var(--brand)}
.notable .eyebrow{color:var(--lav-text)}
.notable .h2{color:#fff}
.notable .h2 .accent{color:var(--lav-text)}
.notable .lead{color:rgba(255,255,255,.75)}
.njgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:20px;margin-top:48px}
.nj{border:1px solid rgba(255,255,255,.1);background:rgba(255,255,255,.04);border-radius:20px;padding:24px}
.nj .njdate{font-family:Montserrat;font-size:11px;font-weight:700;letter-spacing:.15em;color:var(--lav-text)}
.nj h4{color:#fff;font-size:16px;font-weight:600;margin-top:8px;line-height:1.4}
.nj p{color:rgba(255,255,255,.72);font-size:14px;margin-top:8px}
.nj a{color:var(--lav-text);font-size:13px;display:inline-block;margin-top:12px}

/* watchlist */
.wgrid{margin-top:48px;display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px}
.wcard{border:1px solid var(--border);border-radius:16px;background:var(--white);padding:24px}
.wcard .wc-cases{font-family:Montserrat;font-size:14px;font-weight:600;line-height:1.5}
.wcard .wc-why{margin-top:8px;font-size:13px;color:var(--muted)}
footer{border-top:1px solid var(--border);padding:48px 0 64px;font-size:14px;color:var(--muted)}
footer .brand{font-family:Montserrat;font-weight:700;color:var(--dark)}
footer p{max-width:820px;margin-top:8px}
</style>
</head>
<body>

<section class="hero">
  <div class="glow" aria-hidden="true"></div>
  <div class="wrap">
    <span class="eyebrow">Litigation Tracker · Supreme Court of India</span>
    <h1>Road safety in the<br><span class="accent">Supreme Court of India.</span></h1>
    <p class="lead">Every systemic road-safety case before the Supreme Court — public interest litigation, suo motu matters and appeals that produced nationwide directions — tracked order by order, alongside the judgments that set precedent for crash victims.</p>
    <p class="meta">Last refreshed <b id="last-refresh"></b> · Source: Indian Kanoon (Supreme Court judgments + daily orders) · Refreshes automatically every Tuesday</p>
    <div class="cta-row">
      <a class="btn btn-primary" href="#docket">Browse the docket <span aria-hidden="true">↓</span></a>
      <a class="btn btn-secondary" href="#precedents">Precedent judgments</a>
    </div>
    <div class="stats" id="stats"></div>
  </div>
</section>

<section class="sect bg-lite" id="docket">
  <div class="wrap">
    <span class="eyebrow">The Docket · 01</span>
    <h2 class="h2">Public interest litigation<br><span class="accent">that built road-safety law.</span></h2>
    <p class="lead">Original-jurisdiction petitions — Article 32 writs where citizens, doctors and NGOs moved the Court and the Court kept the file open until systems changed.</p>
    <div class="filters">
      <button class="fbtn active" data-status="all">All cases</button>
      <button class="fbtn" data-status="pending">Pending</button>
      <button class="fbtn" data-status="monitoring">Compliance monitoring</button>
      <button class="fbtn" data-status="disposed">Disposed</button>
      <input class="search" id="search" type="search" placeholder="Search cases, numbers, orders…">
    </div>
    <div class="tchips" id="theme-chips"></div>
    <p class="fnote">Filters and search apply across all three docket sections below.</p>
    <div class="group-top" style="margin-top:48px"><div></div><div class="gcount"><div class="num" id="count-pil"></div><div class="lbl">petitions</div></div></div>
    <div class="case-list" id="list-pil"></div>
  </div>
</section>

<section class="sect" id="suo-motu">
  <div class="wrap">
    <div class="group-top">
      <div style="max-width:760px">
        <span class="eyebrow">The Docket · 02</span>
        <h2 class="h2">When the Court acts<br><span class="accent">on its own motion.</span></h2>
        <p class="lead">Suo motu writ petitions — no petitioner, no filing. The Court read the news, registered a case and summoned the state. The rarest and fastest-moving instrument on this docket.</p>
      </div>
      <div class="gcount"><div class="num" id="count-suo"></div><div class="lbl">suo motu matters</div></div>
    </div>
    <div class="case-list" id="list-suo"></div>
  </div>
</section>

<section class="sect bg-lite" id="appeals">
  <div class="wrap">
    <div class="group-top">
      <div style="max-width:760px">
        <span class="eyebrow">The Docket · 03</span>
        <h2 class="h2">Appeals that ended<br><span class="accent">as nationwide directions.</span></h2>
        <p class="lead">Appellate matters — individual disputes the Court used to fix the system: Constitution Bench references, appeals with directions binding every state, tribunal and insurer.</p>
      </div>
      <div class="gcount"><div class="num" id="count-app"></div><div class="lbl">appeals &amp; references</div></div>
    </div>
    <div class="case-list" id="list-app"></div>
  </div>
</section>

<section class="sect notable" id="precedents">
  <div class="wrap">
    <span class="eyebrow">Precedent Feed</span>
    <h2 class="h2">Judgments that set the rules<br><span class="accent">for every crash victim.</span></h2>
    <p class="lead">Not systemic monitoring cases — the rulings every Motor Accident Claims Tribunal, insurer and claimant lawyer works from: compensation method, insurer liability, licence law and sentencing.</p>
    <div class="njgrid" id="nj-grid"></div>
  </div>
</section>

<section class="sect" id="watchlist">
  <div class="wrap">
    <span class="eyebrow">Watchlist</span>
    <h2 class="h2">Reviewed and set aside<br><span class="accent">— for now.</span></h2>
    <p class="lead">Matters that surfaced in the weekly sweep but sit outside the inclusion rule. They stay on watch; a systemic turn moves them onto the docket.</p>
    <div class="wgrid" id="watch-grid"></div>
  </div>
</section>

<footer>
  <div class="wrap">
    <span class="brand">Crashfree India</span> · Supreme Court Road Safety Litigation Tracker
    <p>Order gists are working summaries prepared for advocacy tracking, not legal advice. Full text of every order is linked to Indian Kanoon. Case discovery runs weekly across judgments and daily orders; newly filed systemic matters are flagged automatically. Inclusion rule: systemic relief in — individual compensation appeals out, unless they set precedent (those join the precedent feed).</p>
  </div>
</footer>

<script id="data" type="application/json">__DATA__</script>
<script>
const DB = JSON.parse(document.getElementById('data').textContent);
const $ = s => document.querySelector(s);
const fmt = d => d ? new Date(d+'T00:00:00').toLocaleDateString('en-IN',{day:'numeric',month:'short',year:'numeric'}) : '—';

// classification
const isSuo = c => /suo motu/i.test(c.case_type||'');
const isPil = c => !isSuo(c) && /pil|writ|implementation/i.test(c.case_type||'');
const typeChip = c => {
  const t = c.case_type||'';
  if (/suo motu/i.test(t)) return 'Suo Motu';
  if (/pil/i.test(t)) return 'PIL';
  if (/constitution bench|reference/i.test(t)) return 'Reference';
  if (/slp/i.test(t)) return 'SLP';
  if (/appeal/i.test(t)) return 'Appeal';
  return 'Writ';
};

// hero stats
const live = DB.cases.filter(c=>c.status==='pending').length;
const mon  = DB.cases.filter(c=>c.status==='monitoring').length;
const disp = DB.cases.filter(c=>c.status==='disposed').length;
const orders = DB.cases.reduce((n,c)=>n+c.order_count,0);
$('#last-refresh').textContent = fmt(DB.meta.built);
$('#stats').innerHTML = [
  [DB.cases.length,'systemic cases tracked',''],
  [live,'pending before the Court',''],
  [mon,'under compliance monitoring','watch'],
  [disp,'disposed with directions',''],
  [orders,'orders indexed',''],
  [DB.notable_judgments.length,'precedent judgments','']
].map(([n,l,c])=>`<div class="stat"><div class="num ${c}">${n}</div><div class="lbl">${l}</div></div>`).join('');

// theme chips
const themes = [...new Set(DB.cases.flatMap(c=>c.themes||[]))].sort();
$('#theme-chips').innerHTML = themes.map(t=>`<button class="tchip" data-theme="${t}">${t}</button>`).join('');

let fStatus='all', fTheme=null, fText='';
const statusLabel = s => s==='pending'?'Pending':s==='monitoring'?'Monitoring':'Disposed';

function matches(c){
  if(fStatus!=='all' && c.status!==fStatus) return false;
  if(fTheme && !(c.themes||[]).includes(fTheme)) return false;
  if(fText){
    const hay=(c.title+' '+c.case_number+' '+(c.why_it_matters||'')+' '+(c.latest_development||'')+' '
      +c.orders.map(o=>o.gist).join(' ')).toLowerCase();
    if(!hay.includes(fText)) return false;
  }
  return true;
}

function renderCase(c, newSet){
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
      <span class="chip-type">${typeChip(c)}</span>
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
}

function render(){
  const newSet = new Set(DB.new_this_refresh||[]);
  const bySort = (a,b)=>(b.latest_order||'').localeCompare(a.latest_order||'');
  const groups = [
    {list:'#list-pil',  count:'#count-pil', section:'#docket',   cases: DB.cases.filter(isPil).filter(matches).sort(bySort)},
    {list:'#list-suo',  count:'#count-suo', section:'#suo-motu', cases: DB.cases.filter(isSuo).filter(matches).sort(bySort)},
    {list:'#list-app',  count:'#count-app', section:'#appeals',  cases: DB.cases.filter(c=>!isPil(c)&&!isSuo(c)).filter(matches).sort(bySort)},
  ];
  for(const g of groups){
    $(g.count).textContent = g.cases.length;
    $(g.list).innerHTML = g.cases.length
      ? g.cases.map(c=>renderCase(c,newSet)).join('')
      : '<div class="gempty">No cases in this section match the current filters.</div>';
  }
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
document.getElementById('search').addEventListener('input',e=>{fText=e.target.value.trim().toLowerCase();render();});

// precedent feed (newest first)
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
