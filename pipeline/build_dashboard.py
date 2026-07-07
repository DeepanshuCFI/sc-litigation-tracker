#!/usr/bin/env python3
"""Generate docs/index.html from data/cases.json.

Layout follows the Crashfree India design system (CFI_Skill v2.2) to the letter:
section wrapper (max-w-7xl, px-6/10, py-24/32), background rotation
(background -> brand-lite -> brand), section anatomy (eyebrow -> two-line H2 ->
lead -> grid), Montserrat + Geist only, semantic color tokens only (all tints
via color-mix from :root tokens — never hardcode a color below :root).
The docket is split into three sections: PIL & Writs / Suo Motu / Appeals &
References — cases self-sort by case_type.

Settled design decision (Deepanshu, 7 Jul 2026): card radius is 16px — the
real rendering of the spec's `rounded-2xl` class on the Tailwind stack that
crashfreeindia.org uses; the spec prose's "(12px)" is a transcription slip.
Featured panels (brand-section cards) are 24px (`rounded-3xl`).
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
.h2{margin-top:24px;max-width:896px;font-size:clamp(32px,4.2vw,48px);font-weight:700;line-height:1.05;letter-spacing:-.01em}
.h2 .accent{color:var(--brand)}
.lead{margin-top:24px;max-width:768px;font-size:16px;color:var(--muted)}
@media(min-width:640px){.lead{font-size:18px}}

/* hero */
.hero{position:relative;border-top:none;padding:96px 0 64px;overflow:hidden}
@media(min-width:768px){.hero{padding-top:112px}}
@media(min-width:1024px){.hero{padding:128px 0 64px}}
.hero .glow{position:absolute;inset:0;z-index:-1;background:radial-gradient(circle at 18% 18%,color-mix(in srgb,var(--brand) 22%,transparent),transparent 60%)}
.hero h1{margin-top:24px;max-width:920px;font-size:clamp(40px,6vw,64px);font-weight:700;line-height:1.02;letter-spacing:-.01em}
.hero h1 .accent{color:var(--brand)}
.hero .meta{margin-top:16px;font-size:14px;color:var(--muted)}
.cta-row{margin-top:32px;display:flex;flex-wrap:wrap;gap:12px}
.btn{display:inline-flex;align-items:center;gap:8px;height:48px;padding:0 28px;border-radius:9999px;font-family:Geist;font-size:16px;cursor:pointer;transition:.15s;text-decoration:none}
.btn:hover{text-decoration:none}
.btn-primary{background:var(--brand);color:var(--white);border:none;box-shadow:0 10px 24px color-mix(in srgb,var(--brand) 30%,transparent)}
.btn-primary:hover{background:color-mix(in srgb,var(--brand) 90%,transparent)}
.btn-secondary{background:var(--white);color:var(--dark);border:1px solid var(--border)}
.btn-secondary:hover{border-color:color-mix(in srgb,var(--brand) 40%,transparent)}
.btn svg{flex:0 0 auto}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:16px;margin-top:48px}
.stat{border:1px solid var(--border);border-radius:16px;background:var(--white);padding:24px}
.stat .num{font-family:Montserrat;font-size:36px;font-weight:700;color:var(--brand);line-height:1}
.stat .num.watch{color:var(--warning)}
.stat .lbl{margin-top:8px;font-size:14px;color:var(--muted)}

/* filters */
.filters{margin-top:48px;display:flex;flex-wrap:wrap;gap:12px;align-items:center}
.fbtn{font-family:Montserrat;font-size:12px;font-weight:600;letter-spacing:.05em;min-height:44px;padding:0 20px;border:1px solid var(--border);background:var(--white);color:var(--muted);border-radius:9999px;cursor:pointer;transition:.15s}
.fbtn:hover{border-color:color-mix(in srgb,var(--brand) 40%,transparent);color:var(--brand)}
.fbtn.active{background:var(--brand);border-color:var(--brand);color:var(--white)}
.search{flex:1;min-width:240px;max-width:380px;min-height:44px;border:1px solid var(--border);border-radius:9999px;padding:0 20px;font-size:16px;font-family:inherit;color:var(--dark);outline:none;background:var(--white)}
.search:focus{border-color:color-mix(in srgb,var(--brand) 50%,transparent)}
.tchips{margin-top:16px;display:flex;flex-wrap:wrap;gap:8px}
.tchip{display:inline-flex;align-items:center;font-size:12px;min-height:44px;border:1px solid var(--border);background:var(--white);color:var(--muted);border-radius:9999px;padding:0 16px;cursor:pointer;transition:.15s}
.tchip:hover{border-color:color-mix(in srgb,var(--brand) 40%,transparent)}
.tchip.active{background:color-mix(in srgb,var(--brand) 10%,transparent);border-color:color-mix(in srgb,var(--brand) 25%,transparent);color:var(--brand);font-weight:500}
.fnote{margin-top:16px;font-size:13px;color:var(--muted)}

/* docket group sections */
.group-top{display:flex;align-items:flex-end;justify-content:space-between;gap:24px;flex-wrap:wrap}
.gcount{text-align:right}
.gcount .num{font-family:Montserrat;font-size:clamp(60px,7vw,96px);font-weight:700;color:var(--brand);line-height:.9}
.gcount .lbl{font-size:14px;color:var(--muted);margin-top:4px}
.case-list{margin-top:48px}
.case{border:1px solid var(--border);border-radius:16px;background:var(--white);padding:24px;margin-bottom:20px;transition:.15s}
.case:hover{border-color:color-mix(in srgb,var(--brand) 40%,transparent);box-shadow:0 8px 24px color-mix(in srgb,var(--brand) 5%,transparent)}
.case-head{display:flex;flex-wrap:wrap;gap:12px;align-items:center}
.case h3{font-size:20px;font-weight:600;line-height:1.4;flex:1 1 340px}
.chip-type{font-family:Montserrat;font-size:10.5px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;border-radius:9999px;padding:6px 14px;background:color-mix(in srgb,var(--brand) 10%,transparent);border:1px solid color-mix(in srgb,var(--brand) 25%,transparent);color:var(--brand);white-space:nowrap}
.badge{font-family:Montserrat;font-size:10.5px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;border-radius:9999px;padding:6px 14px;white-space:nowrap}
.badge.pending{background:color-mix(in srgb,var(--brand) 10%,transparent);color:var(--brand);border:1px solid color-mix(in srgb,var(--brand) 25%,transparent)}
.badge.monitoring{background:color-mix(in srgb,var(--warning) 10%,transparent);color:var(--warning);border:1px solid color-mix(in srgb,var(--warning) 30%,transparent)}
.badge.disposed{background:var(--brand-lite);color:var(--muted);border:1px solid var(--border)}
.badge.new{background:color-mix(in srgb,var(--success) 10%,transparent);color:var(--success);border:1px solid color-mix(in srgb,var(--success) 30%,transparent)}
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

/* accountability ledger */
.ledger-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:16px;margin-top:48px}
.lstat{border:1px solid var(--border);border-radius:16px;background:var(--white);padding:24px}
.lstat .num{font-family:Montserrat;font-size:44px;font-weight:700;line-height:1;color:var(--brand)}
.lstat.red .num{color:var(--danger)}
.lstat.orange .num{color:var(--warning)}
.lstat.green .num{color:var(--success)}
.lstat .lbl{margin-top:8px;font-size:14px;color:var(--muted)}
.authchart{margin-top:24px;border:1px solid var(--border);border-radius:16px;background:var(--white);padding:24px 28px}
.authchart h4{font-family:Montserrat;font-size:13px;font-weight:600;letter-spacing:.04em;color:var(--dark)}
.authchart .csub{font-size:12.5px;color:var(--muted);margin-top:4px;margin-bottom:20px}
.abar{display:grid;grid-template-columns:minmax(88px,168px) 1fr 28px;align-items:center;gap:14px;margin:11px 0}
.abar .an{font-size:13px;color:var(--dark);text-align:right;line-height:1.3}
.abar .track{height:14px;background:var(--brand-lite);border-radius:9999px;overflow:hidden}
.abar .fill{height:100%;background:var(--brand);border-radius:9999px;min-width:14px}
.abar .av{font-family:Montserrat;font-size:13px;font-weight:600;color:var(--brand);text-align:right}
.ledger-list{margin-top:24px}
.dcard{border:1px solid var(--border);border-radius:16px;background:var(--white);padding:22px 24px;margin-bottom:16px;transition:.15s}
.dcard:hover{border-color:color-mix(in srgb,var(--brand) 40%,transparent);box-shadow:0 8px 24px color-mix(in srgb,var(--brand) 5%,transparent)}
.dcard-head{display:flex;justify-content:space-between;gap:16px;align-items:flex-start;flex-wrap:wrap-reverse}
.dtext{font-size:15px;color:var(--dark);line-height:1.5;max-width:760px;flex:1 1 320px}
.dpill{font-family:Montserrat;font-size:10px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;border-radius:9999px;padding:6px 13px;white-space:nowrap}
.dpill.overdue,.dpill.missed{background:color-mix(in srgb,var(--danger) 9%,transparent);color:var(--danger);border:1px solid color-mix(in srgb,var(--danger) 28%,transparent)}
.dpill.due-soon{background:color-mix(in srgb,var(--warning) 10%,transparent);color:var(--warning);border:1px solid color-mix(in srgb,var(--warning) 30%,transparent)}
.dpill.upcoming{background:color-mix(in srgb,var(--brand) 10%,transparent);color:var(--brand);border:1px solid color-mix(in srgb,var(--brand) 25%,transparent)}
.dpill.complied{background:color-mix(in srgb,var(--success) 10%,transparent);color:var(--success);border:1px solid color-mix(in srgb,var(--success) 30%,transparent)}
.dpill.ongoing{background:var(--brand-lite);color:var(--muted);border:1px solid var(--border)}
.dmeta{margin-top:14px;display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;font-size:13px;color:var(--muted)}
.dmeta b{color:var(--dark);font-weight:500}
.authchip{font-family:Montserrat;font-size:11px;font-weight:600;letter-spacing:.06em;border-radius:9999px;padding:4px 12px;background:color-mix(in srgb,var(--brand) 8%,transparent);border:1px solid color-mix(in srgb,var(--brand) 20%,transparent);color:var(--brand);white-space:nowrap}
.dmeta .dcase{font-style:italic}
.ledger-note{margin-top:20px;font-size:13px;color:var(--muted);max-width:820px;border-left:3px solid var(--border);padding-left:16px;font-style:italic}

/* precedent feed — brand section */
.notable{background:var(--brand)}
.notable .eyebrow{color:var(--lav-text)}
.notable .h2{color:var(--white)}
.notable .h2 .accent{color:var(--lav-text)}
.notable .lead{color:color-mix(in srgb,var(--white) 80%,transparent)}
.njgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:20px;margin-top:48px}
.nj{border:1px solid color-mix(in srgb,var(--white) 10%,transparent);background:color-mix(in srgb,var(--white) 4%,transparent);border-radius:24px;padding:24px}
.nj .njdate{font-family:Montserrat;font-size:11px;font-weight:700;letter-spacing:.15em;color:var(--lav-text)}
.nj h4{color:var(--white);font-size:16px;font-weight:600;margin-top:8px;line-height:1.4}
.nj p{color:color-mix(in srgb,var(--white) 80%,transparent);font-size:14px;margin-top:8px}
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
      <a class="btn btn-primary" href="#ledger">See what's come due
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 5v14"/><path d="m19 12-7 7-7-7"/></svg></a>
      <a class="btn btn-secondary" href="#docket">Browse the docket
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg></a>
    </div>
    <div class="stats" id="stats"></div>
  </div>
</section>

<section class="sect bg-lite" id="ledger">
  <div class="wrap">
    <span class="eyebrow">Accountability Ledger</span>
    <h2 class="h2">What the Court ordered.<br><span class="accent">What's come due.</span></h2>
    <p class="lead">The Supreme Court doesn't just decide road-safety cases — it hands the government dated deadlines. This ledger extracts each direction, names the duty-bearer, and converts the granted time into a calendar date, so the question becomes simple: has the deadline passed?</p>
    <div class="ledger-stats" id="ledger-stats"></div>
    <div class="authchart">
      <h4>Court-ordered obligations, by duty-bearer</h4>
      <div class="csub">Who the Supreme Court is currently holding to a deadline on road safety.</div>
      <div id="auth-bars"></div>
    </div>
    <div class="filters" id="ledger-filters">
      <button class="fbtn active" data-lstatus="all">All directions</button>
      <button class="fbtn" data-lstatus="overdue">Overdue</button>
      <button class="fbtn" data-lstatus="due-soon">Due soon</button>
      <button class="fbtn" data-lstatus="upcoming">Upcoming</button>
      <button class="fbtn" data-lstatus="ongoing">Ongoing</button>
    </div>
    <div class="tchips" id="ledger-auth"></div>
    <div class="ledger-list" id="ledger-list"></div>
    <p class="ledger-note">"Deadline passed" means the date the Court set has gone by with compliance not confirmed on the orders we track — not a finding of government failure. "Non-compliance recorded" is used only where a later order of the Court itself notes the direction was not met (as with the National Road Safety Board). Every direction links to its source order.</p>
  </div>
</section>

<section class="sect" id="docket">
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

<section class="sect bg-lite" id="suo-motu">
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

<section class="sect" id="appeals">
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

// ===== Accountability Ledger =====
const DIRS = DB.directions || [];
const SMETA = {
  overdue:   {label:'Deadline passed',          cls:'overdue',  rank:0},
  missed:    {label:'Non-compliance recorded',  cls:'missed',   rank:0},
  'due-soon':{label:'Due within 90 days',       cls:'due-soon', rank:1},
  upcoming:  {label:'Upcoming',                 cls:'upcoming', rank:2},
  complied:  {label:'Complied',                 cls:'complied', rank:3},
  ongoing:   {label:'Ongoing / recurring',      cls:'ongoing',  rank:4},
};
function dstatus(d){
  if(d.status) return d.status;              // missed / complied / ongoing set explicitly
  if(!d.due) return 'ongoing';
  const midnight = new Date(new Date().toDateString());
  const days = Math.floor((new Date(d.due+'T00:00:00') - midnight)/86400000);
  if(days < 0) return 'overdue';
  if(days <= 90) return 'due-soon';
  return 'upcoming';
}
DIRS.forEach(d => d._st = dstatus(d));

// stat strip
const nOver = DIRS.filter(d=>d._st==='overdue'||d._st==='missed').length;
const nSoon = DIRS.filter(d=>d._st==='due-soon').length;
const nDone = DIRS.filter(d=>d._st==='complied').length;
$('#ledger-stats').innerHTML = [
  [DIRS.length,'directions tracked',''],
  [nOver,'overdue — deadline passed','red'],
  [nSoon,'due within 90 days','orange'],
  [nDone,'confirmed complied','green'],
].map(([n,l,c])=>`<div class="lstat ${c}"><div class="num">${n}</div><div class="lbl">${l}</div></div>`).join('');

// by-authority bar chart (single-hue magnitude)
const authCounts = {};
DIRS.forEach(d=>{authCounts[d.authority]=(authCounts[d.authority]||0)+1;});
const authRows = Object.entries(authCounts).sort((a,b)=>b[1]-a[1]);
const authMax = Math.max(...authRows.map(r=>r[1]),1);
$('#auth-bars').innerHTML = authRows.map(([a,n])=>`
  <div class="abar">
    <div class="an">${a}</div>
    <div class="track"><div class="fill" style="width:${Math.round(n/authMax*100)}%"></div></div>
    <div class="av">${n}</div>
  </div>`).join('');

// authority filter chips
const authList = authRows.map(r=>r[0]);
$('#ledger-auth').innerHTML = authList.map(a=>`<button class="tchip" data-lauth="${a}">${a}</button>`).join('');

let lStatus='all', lAuth=null;
function renderLedger(){
  const inStatusBucket = (st) => lStatus==='all' ? true
    : lStatus==='overdue' ? (st==='overdue'||st==='missed')
    : st===lStatus;
  const rows = DIRS.filter(d=>{
    if(!inStatusBucket(d._st)) return false;
    if(lAuth && d.authority!==lAuth) return false;
    return true;
  }).sort((a,b)=> (SMETA[a._st].rank - SMETA[b._st].rank) || ((a.due||'9999').localeCompare(b.due||'9999')));

  $('#ledger-list').innerHTML = rows.length ? rows.map(d=>{
    const m = SMETA[d._st];
    const due = d.due ? `due <b>${fmt(d.due)}</b>` : '<b>no fixed date</b>';
    const link = d.link ? `<a href="${d.link}" target="_blank" rel="noopener">Read order ↗</a>` : '';
    return `<div class="dcard">
      <div class="dcard-head">
        <div class="dtext">${d.directive}</div>
        <span class="dpill ${m.cls}">${m.label}</span>
      </div>
      <div class="dmeta">
        <span class="authchip">${d.authority}</span>
        <span>Granted <b>${d.granted}</b> · ${due}</span>
        <span class="dcase">${d.case_title}</span>
        ${link}
      </div>
    </div>`;
  }).join('') : '<div class="gempty">No directions match the current filters.</div>';
}
document.querySelectorAll('#ledger-filters .fbtn').forEach(b=>b.addEventListener('click',()=>{
  document.querySelectorAll('#ledger-filters .fbtn').forEach(x=>x.classList.remove('active'));
  b.classList.add('active'); lStatus=b.dataset.lstatus; renderLedger();
}));
document.querySelectorAll('#ledger-auth .tchip').forEach(b=>b.addEventListener('click',()=>{
  const on=b.classList.contains('active');
  document.querySelectorAll('#ledger-auth .tchip').forEach(x=>x.classList.remove('active'));
  lAuth = on ? null : b.dataset.lauth; if(!on) b.classList.add('active'); renderLedger();
}));
renderLedger();

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
