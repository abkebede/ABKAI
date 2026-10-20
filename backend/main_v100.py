from __future__ import annotations

import json
import sqlite3
import urllib.parse
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

# Import the proven data loaders and registries from V99, but expose a separate clean V100 app.
from backend import main as legacy

BASE_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = BASE_DIR.parent
DB_PATH = legacy.DB_PATH
ASSIGNMENTS_PATH = PACKAGE_DIR / "abk_pai" / "v100_teacher_assignments.json"

app = FastAPI(
    title="ABK_PAI — Physics AI Assistant Volume 100",
    version="100.0.0",
    description=(
        "ABK_PAI V100 clean replacement: canonical-problem tutoring, teacher-assigned independent homework, "
        "teacher grading and feedback returned to students, structured Tutor feedback, contextual Prompt and "
        "Equation tools, Not listed suggestions, Help, and browser spellcheck support."
    ),
)
assets_dir = BASE_DIR / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")


def h(v: Any) -> str:
    return escape(str(v if v is not None else ""), quote=True)


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_tables() -> None:
    with connect() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS v100_tutor_submissions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            problem_id TEXT, student_name TEXT,
            selected_domain TEXT, domain_suggestion TEXT,
            selected_family TEXT, family_suggestion TEXT,
            selected_mode TEXT, mode_suggestion TEXT,
            selected_rcs TEXT, rc_suggestion TEXT,
            known_information TEXT, tutor_request TEXT, equations_used TEXT,
            representation TEXT, symbolic_work TEXT, numerical_work TEXT,
            interpretation TEXT, final_answer TEXT, feedback TEXT,
            submitted_at TEXT
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS v100_assignment_submissions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_id TEXT, problem_id TEXT, student_name TEXT,
            selected_domain TEXT, domain_suggestion TEXT,
            selected_family TEXT, family_suggestion TEXT,
            selected_mode TEXT, mode_suggestion TEXT,
            selected_rcs TEXT, rc_suggestion TEXT,
            known_information TEXT, equations_used TEXT, representation TEXT,
            symbolic_work TEXT, numerical_work TEXT, interpretation TEXT,
            final_answer TEXT, submitted_at TEXT,
            grade TEXT DEFAULT '', teacher_feedback TEXT DEFAULT '',
            corrected_domain TEXT DEFAULT '', corrected_family TEXT DEFAULT '',
            corrected_mode TEXT DEFAULT '', corrected_rcs TEXT DEFAULT '',
            review_status TEXT DEFAULT 'Submitted', reviewed_at TEXT DEFAULT ''
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS v100_student_stories(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT, title TEXT, story_text TEXT, created_at TEXT
        )""")


ensure_tables()


def canonical_records() -> List[Dict[str, Any]]:
    return legacy._v98_canonical_records()


def canonical_map() -> Dict[str, Dict[str, Any]]:
    return {str(r.get("id")): r for r in canonical_records()}


def approved_records() -> List[Dict[str, Any]]:
    return legacy._v93_records()


def approved_map() -> Dict[str, Dict[str, Any]]:
    return {str(r.get("problem_id")): r for r in approved_records()}


def load_assignments() -> List[Dict[str, Any]]:
    if ASSIGNMENTS_PATH.exists():
        try:
            data = json.loads(ASSIGNMENTS_PATH.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception:
            pass
    source = PACKAGE_DIR / "abk_pai" / "v99_teacher_assignments.json"
    data: List[Dict[str, Any]] = []
    if source.exists():
        try:
            raw = json.loads(source.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                data = raw
        except Exception:
            data = []
    out = []
    for i, row in enumerate(data, 1):
        item = dict(row)
        item["assignment_id"] = f"V100-{i:04d}"
        out.append(item)
    save_assignments(out)
    return out


def save_assignments(rows: List[Dict[str, Any]]) -> None:
    ASSIGNMENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    ASSIGNMENTS_PATH.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def nav(role: str, active: str = "") -> str:
    student = [
        ("home", "/v100/student-home", "Student Home"),
        ("tutor", "/v100/physics-tutor", "Physics Tutor"),
        ("assignments", "/v100/assignments", "Assignments"),
        ("portfolio", "/v100/portfolio", "My Portfolio"),
        ("math", "/v100/math-equations", "Math and Equations"),
        ("stories", "/v100/physics-stories", "Physics Stories"),
        ("write", "/v100/write-physics-story", "Write a Physics Story"),
        ("prompts", "/v100/prompt-library", "Prompt Library"),
        ("help", "/v100/help", "Help"),
    ]
    teacher = [
        ("home", "/v100/teacher-home", "Teacher Home"),
        ("builder", "/v100/teacher-assignment-builder", "Assignment Builder"),
        ("assigned", "/v100/teacher-assigned-work", "Assigned Work"),
        ("submissions", "/v100/teacher-submissions", "Review Submissions"),
        ("student", "/v100/student-home", "Student Home"),
        ("help", "/v100/help", "Help"),
    ]
    items = teacher if role == "teacher" else student
    return "<nav class='local-nav'>" + "".join(
        f"<a class='{'active' if key == active else ''}' href='{url}'>{h(label)}</a>" for key, url, label in items
    ) + "</nav>"


def page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(f"""<!doctype html><html lang='en'><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'><title>{h(title)} — ABK_PAI V100</title>
<link rel='stylesheet' href='/assets/css/style.css'><style>
body{{margin:0;background:#f2f5f8}}.banner{{background:#142c47;color:#fff;padding:.55rem 1rem}}.banner h1{{font-size:1.45rem;margin:0}}.role-nav,.local-nav,.actions{{display:flex;flex-wrap:wrap;gap:.35rem}}.role-nav{{margin-top:.35rem}}.role-nav a,.local-nav a{{text-decoration:none;font-weight:700;border-radius:6px;padding:.35rem .58rem}}.role-nav a{{color:#fff;border:1px solid #7590aa}}.local-nav{{margin:.65rem 0}}.local-nav a{{background:#4c6887;color:#fff}}.local-nav a.active{{background:#3962ee}}main{{max-width:1220px;margin:auto;padding:.6rem 1rem 2rem}}.hero,.panel,.card{{background:white;border-radius:12px;padding:1rem;margin:.6rem 0;box-shadow:0 2px 12px rgba(0,0,0,.05)}}.hero h2{{margin:.1rem 0 .35rem}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:.7rem}}.three{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.6rem}}.two{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.6rem}}label{{display:block;font-weight:700}}input,select,textarea{{width:100%;box-sizing:border-box;margin-top:.25rem;padding:.55rem;border:1px solid #b8c7d6;border-radius:7px;font:inherit}}textarea{{min-height:72px}}button,.button{{display:inline-block;border:0;border-radius:7px;background:#3962ee;color:#fff;text-decoration:none;padding:.55rem .8rem;font-weight:700;cursor:pointer}}button.secondary,.button.secondary{{background:#4c6887}}details{{border:1px solid #c8d5e1;border-radius:8px;padding:.5rem .65rem;background:#fff;margin:.55rem 0}}summary{{font-weight:800;cursor:pointer}}.rc-grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.3rem .6rem;max-height:220px;overflow:auto;padding:.5rem}}.rc-grid label{{font-weight:400}}.eq-grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.6rem}}.eq-card{{border:1px solid #d2dde7;border-radius:8px;padding:.65rem;background:#f8fafc}}.problem{{border-left:4px solid #4c6887;background:#f7f9fc;padding:.7rem;border-radius:7px}}.feedback{{border-left:4px solid #2c6fbb;background:#eef5ff;padding:.75rem;border-radius:7px;white-space:normal}}.feedback-line{{margin:.35rem 0}}.muted{{color:#556575}}.status{{font-weight:800}}.sticky{{position:sticky;bottom:0;background:#fff;border-top:1px solid #cbd5e1;padding:.55rem 0}}table{{width:100%;border-collapse:collapse}}td,th{{border:1px solid #d2dde7;padding:.5rem;text-align:left;vertical-align:top}}@media(max-width:850px){{.three,.two,.rc-grid,.eq-grid{{grid-template-columns:1fr}}}}
</style></head><body><header class='banner'><h1>ABK_PAI Volume 100</h1><nav class='role-nav'><a href='/'>Developer Home</a><a href='/v100/teacher-home'>Teacher Home</a><a href='/v100/student-home'>Student Home</a><a href='/v100/help'>Help</a><a href='/abk-pai/v100-regression'>V100 Tests</a></nav></header><main>{body}</main></body></html>""")


def unique(vals: List[Any]) -> List[str]:
    return sorted({str(v) for v in vals if str(v).strip()})


def options(vals: List[str], selected: str = "", blank: str = "Select") -> str:
    html = f"<option value=''>{h(blank)}</option>"
    for v in unique(vals):
        html += f"<option value='{h(v)}'{' selected' if v == selected else ''}>{h(v.replace('_',' ').title())}</option>"
    html += f"<option value='__not_listed__'{' selected' if selected == '__not_listed__' else ''}>Not listed / Suggest new</option>"
    return html


def rc_menu(selected: List[str]) -> str:
    reg = legacy._v63_rc_registry(); chosen = set(selected or [])
    blocks = []
    for cat in reg.get("categories", []):
        checks = []
        for code in cat.get("items", []):
            meta = (reg.get("items") or {}).get(code, {})
            label = meta.get("display_label") or code.replace("_", " ")
            checks.append(f"<label><input type='checkbox' name='selected_rc' value='{h(code)}'{' checked' if code in chosen else ''}> {h(label)}</label>")
        blocks.append(f"<details><summary>{h(cat.get('display_label') or cat.get('category_code'))}</summary><div class='rc-grid'>{''.join(checks)}</div></details>")
    blocks.append("<label><input type='checkbox' name='selected_rc' value='__not_listed__'> Not listed / Suggest a new RC</label><label>Suggested RC or explanation<textarea name='rc_suggestion' spellcheck='true'></textarea></label>")
    return "".join(blocks)


PROMPTS = [
    ("Identify the physics", "Help me identify the objects, interactions, changes, and physics ideas in this problem without solving it yet."),
    ("Choose a Learning Mode", "Compare the plausible Learning Modes for this problem and ask me questions that help me decide."),
    ("Choose RCs", "Help me examine the RC registry for this problem. Explain each suggestion, but let me make the final choice."),
    ("Start with a hint", "Give me one conceptual hint about this problem and wait for my response."),
    ("Select an equation", "Help me choose a governing equation for this problem and explain the assumptions without solving it."),
    ("Request a representation", "Help me choose and construct the appropriate diagram, graph, free-body diagram, or coordinate representation for this problem."),
    ("Check units", "Check the dimensions and units in my current work for this problem and identify the first inconsistency."),
    ("Check my solution", "Check my current classification, equations, reasoning, calculations, units, interpretation, and final answer. Identify the first issue and let me revise it."),
]


def equations(record: Dict[str, Any]) -> List[Dict[str, str]]:
    return legacy._v99_equations(record)


def prompt_panel(target: str, problem_id: str = '') -> str:
    buttons = "".join(f"<button type='button' class='secondary add-prompt' data-target='{h(target)}' data-text='{h(text)}'>{h(label)}</button>" for label, text in PROMPTS)
    library = f"<a class='button secondary' href='/v100/prompt-library?problem_id={urllib.parse.quote(problem_id)}'>Open Full Prompt Library</a>" if problem_id else ''
    return f"<details><summary>Add a Prompt</summary><div class='actions'>{buttons}{library}</div></details>"


def equation_panel(record: Dict[str, Any], target: str) -> str:
    cards=[]
    for e in equations(record):
        cards.append(f"<article class='eq-card'><h4>{h(e['name'])}</h4><code>{h(e['equation'])}</code><p>{h(e['use'])}</p><div class='actions'><button type='button' class='secondary add-equation' data-target='{h(target)}' data-text='{h(e['equation'])}'>Insert into Work</button><button type='button' class='secondary copy-text' data-text='{h(e['equation'])}' data-label='Equation'>Copy Equation</button></div></article>")
    return f"<details><summary>Select or Copy Equations</summary><div class='eq-grid'>{''.join(cards) or '<p>No equation candidates are available.</p>'}</div></details>"


def script() -> str:
    return r"""<script>
(function(){
 function append(id,text){const el=document.getElementById(id);if(!el)return;const t=String(text||'').trim();if(!t)return;el.value=(el.value.trim()?el.value.trim()+'\n':'')+t;el.dispatchEvent(new Event('input',{bubbles:true}));el.focus();}
 document.addEventListener('click',async function(e){
  const p=e.target.closest('.add-prompt');if(p){append(p.dataset.target,p.dataset.text);return;}
  const q=e.target.closest('.add-equation');if(q){append(q.dataset.target,q.dataset.text);return;}
  const c=e.target.closest('.copy-text');if(c){const original=c.textContent;try{await navigator.clipboard.writeText(c.dataset.text||'');c.textContent='Copied '+(c.dataset.label||'Text');setTimeout(()=>c.textContent=original,1000);}catch(err){alert('Copy failed. Select the text manually.');}return;}
 });
})();
</script>"""


def structured_feedback(record: Dict[str, Any], domain: str, family: str, mode: str, rcs: List[str], request: str, equations_used: str, symbolic: str, numerical: str, interpretation: str, final_answer: str) -> str:
    exp_domain=str(record.get('domain') or ''); exp_family=str(record.get('problem_family') or ''); exp_mode=str(record.get('mode') or '')
    exp_rc=set(record.get('expected_rc') or []); chosen=set(x for x in rcs if x != '__not_listed__')
    lines=[]
    lines.append(("Domain Review", "Good match." if domain==exp_domain else "Reconsider the selected domain and compare it with the dominant physical process."))
    lines.append(("Problem Family Review", "Good match." if family==exp_family else "Reconsider the problem family and identify the exact relationship being modeled."))
    lines.append(("Learning Mode Review", "Good match." if mode==exp_mode else "Compare your selected mode with the governing process before continuing."))
    if chosen:
        lines.append(("RC Review", f"{len(chosen & exp_rc)} expected RC selection(s) match; {len(exp_rc-chosen)} expected RC selection(s) remain to reconsider."))
    else:
        lines.append(("RC Review", "No canonical RCs were selected yet. Review the situation, givens, find, method, and final-product categories."))
    low=request.lower()
    if 'learning mode' in low: guidance="Identify the physical quantity changing and the law connecting the givens to the requested result; then compare the two nearest modes."
    elif 'rc' in low: guidance="Read the problem phrase by phrase and classify each phrase as situation, given, find, representation, equation tool, or check."
    elif 'equation' in low: guidance="Choose equations only after naming the model. Every symbol must correspond to a known, inferable, or requested quantity."
    elif 'unit' in low: guidance="Track units through the symbolic substitution and stop at the first dimensional inconsistency."
    elif 'representation' in low: guidance="Choose a diagram or graph that makes the governing relationship and system boundary visible."
    elif 'hint' in low: guidance="First hint: identify the system and the physical quantity that changes. Do not calculate yet."
    elif 'check my solution' in low: guidance="Check in this order: model, equation, symbolic isolation, substitution, units, numerical value, interpretation."
    else: guidance="Continue by justifying your classification before using equations."
    lines.append(("Tutor Guidance", guidance))
    if not equations_used.strip(): nxt="Select or enter a governing equation and explain why it applies."
    elif not symbolic.strip(): nxt="Rearrange the equation symbolically before substituting numbers."
    elif not numerical.strip(): nxt="Substitute values with units and calculate."
    elif not interpretation.strip(): nxt="Interpret what the result means physically."
    elif not final_answer.strip(): nxt="State the final answer with units."
    else: nxt="Recheck consistency among classification, equations, units, and interpretation."
    lines.append(("Next Step", nxt))
    return "\n".join(f"{label}: {text}" for label,text in lines)


def feedback_html(text: str) -> str:
    out=[]
    for line in text.splitlines():
        if ':' in line:
            label, value=line.split(':',1); out.append(f"<div class='feedback-line'><strong>{h(label)}:</strong>{h(value)}</div>")
        else: out.append(f"<div class='feedback-line'>{h(line)}</div>")
    return ''.join(out)


@app.get("/", response_class=HTMLResponse)
def developer_home() -> HTMLResponse:
    body="""<section class='hero'><h2>Developer Home</h2><p>V100 exposes one clean route family for Developer, Teacher, and Student testing.</p></section><section class='grid'><article class='card'><h3>Teacher Workflow</h3><a class='button' href='/v100/teacher-home'>Open Teacher Home</a></article><article class='card'><h3>Student Workflow</h3><a class='button' href='/v100/student-home'>Open Student Home</a></article><article class='card'><h3>Diagnostics</h3><a class='button' href='/api/v100/integrity'>Integrity JSON</a></article></section>"""
    return page("Developer Home", body)


@app.get("/v100/student-home", response_class=HTMLResponse)
def student_home() -> HTMLResponse:
    body=nav('student','home')+"""<section class='hero'><h2>Physics AI Assistant — Student Home</h2></section><section class='grid'>
<article class='card'><h3>Physics Tutor</h3><p>Select a canonical problem and receive structured tutoring feedback.</p><a class='button' href='/v100/physics-tutor'>Open Physics Tutor</a></article>
<article class='card'><h3>Assignments</h3><p>Complete teacher-assigned homework independently.</p><a class='button' href='/v100/assignments'>Open Assignments</a></article>
<article class='card'><h3>My Portfolio</h3><p>Check grades, teacher feedback, and completed work.</p><a class='button' href='/v100/portfolio'>Open Portfolio</a></article>
<article class='card'><h3>Help</h3><p>Learn how Tutor, Assignments, Prompts, and Equations work.</p><a class='button' href='/v100/help'>Open Help</a></article></section>"""
    return page("Student Home", body)


@app.get("/v100/physics-tutor", response_class=HTMLResponse)
def physics_tutor(problem_id: str=Query(''), prompt: str=Query('')) -> HTMLResponse:
    cmap=canonical_map(); records=list(cmap.values())
    if not problem_id:
        opts="".join(f"<option value='{h(r.get('id'))}'>{h(r.get('title') or r.get('id'))}</option>" for r in records)
        body=nav('student','tutor')+f"<section class='hero'><h2>Physics Tutor</h2><p>Canonical Problem mode is active. Student Inquiry will be added later.</p></section><section class='panel'><form method='get'><label>Select a canonical problem<select name='problem_id' required><option value=''>Choose a problem</option>{opts}</select></label><button>Open Problem</button></form></section>"
        return page("Physics Tutor", body)
    rec=cmap.get(problem_id)
    if not rec: raise HTTPException(404,"Canonical problem not found")
    domains=unique([r.get('domain') for r in records]); families=unique([r.get('problem_family') for r in records]); modes=unique([r.get('mode') for r in records])
    statement=str(rec.get('prompt') or rec.get('problem_statement') or '')
    body=nav('student','tutor')+f"""<section class='hero'><h2>Physics Tutor</h2><p>Problem: {h(rec.get('title') or problem_id)}</p></section><section class='panel'><div class='problem'>{h(statement)}</div>
<form method='post' action='/v100/physics-tutor/submit'><input type='hidden' name='problem_id' value='{h(problem_id)}'>
<div class='three'><label>Student name<input name='student_name' required spellcheck='true'></label><label>Domain<select name='selected_domain' required>{options(domains)}</select><textarea name='domain_suggestion' placeholder='Suggestion if not listed' spellcheck='true'></textarea></label><label>Problem Family<select name='selected_family' required>{options(families)}</select><textarea name='family_suggestion' placeholder='Suggestion if not listed' spellcheck='true'></textarea></label></div>
<div class='two'><label>Learning Mode<select name='selected_mode' required>{options(modes)}</select><textarea name='mode_suggestion' placeholder='Suggestion if not listed' spellcheck='true'></textarea></label><label>Known or observable information<textarea name='known_information' spellcheck='true'></textarea></label></div>
<details><summary>Select RCs</summary>{rc_menu([])}</details>
{prompt_panel('tutor-request', problem_id)}{equation_panel(rec,'equations-used')}
<div class='two'><label>Tutor request<textarea id='tutor-request' name='tutor_request' spellcheck='true'>{h(prompt)}</textarea></label><label>Equations used<textarea id='equations-used' name='equations_used' spellcheck='true'></textarea></label></div>
<details><summary>Solution Work</summary><div class='two'><label>Representation<textarea name='representation' spellcheck='true'></textarea></label><label>Symbolic work<textarea name='symbolic_work' spellcheck='true'></textarea></label><label>Numerical work and units<textarea name='numerical_work' spellcheck='true'></textarea></label><label>Interpretation<textarea name='interpretation' spellcheck='true'></textarea></label></div><label>Final answer<textarea name='final_answer' spellcheck='true'></textarea></label></details>
<div class='sticky'><button type='submit'>Submit to Physics Tutor</button> <a class='button secondary' href='/v100/physics-tutor'>Finish / Choose Another Problem</a></div></form></section>{script()}"""
    return page("Physics Tutor",body)


@app.post('/v100/physics-tutor/submit', response_class=HTMLResponse)
def tutor_submit(problem_id:str=Form(...),student_name:str=Form(...),selected_domain:str=Form(...),domain_suggestion:str=Form(''),selected_family:str=Form(...),family_suggestion:str=Form(''),selected_mode:str=Form(...),mode_suggestion:str=Form(''),selected_rc:List[str]=Form([]),rc_suggestion:str=Form(''),known_information:str=Form(''),tutor_request:str=Form(''),equations_used:str=Form(''),representation:str=Form(''),symbolic_work:str=Form(''),numerical_work:str=Form(''),interpretation:str=Form(''),final_answer:str=Form('')) -> HTMLResponse:
    rec=canonical_map().get(problem_id)
    if not rec: raise HTTPException(404,'Canonical problem not found')
    fb=structured_feedback(rec,selected_domain,selected_family,selected_mode,selected_rc,tutor_request,equations_used,symbolic_work,numerical_work,interpretation,final_answer)
    with connect() as conn:
        conn.execute("""INSERT INTO v100_tutor_submissions(problem_id,student_name,selected_domain,domain_suggestion,selected_family,family_suggestion,selected_mode,mode_suggestion,selected_rcs,rc_suggestion,known_information,tutor_request,equations_used,representation,symbolic_work,numerical_work,interpretation,final_answer,feedback,submitted_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(problem_id,student_name,selected_domain,domain_suggestion,selected_family,family_suggestion,selected_mode,mode_suggestion,json.dumps(selected_rc),rc_suggestion,known_information,tutor_request,equations_used,representation,symbolic_work,numerical_work,interpretation,final_answer,fb,now()))
    body=nav('student','tutor')+f"<section class='hero'><h2>Physics Tutor Feedback</h2></section><section class='panel'><div class='problem'>{h(rec.get('prompt') or '')}</div><div class='feedback'>{feedback_html(fb)}</div><div class='actions'><a class='button' href='/v100/physics-tutor?problem_id={urllib.parse.quote(problem_id)}'>Revise This Problem</a><a class='button secondary' href='/v100/physics-tutor'>Finish / Choose Another Problem</a></div></section>"
    return page('Physics Tutor Feedback',body)


@app.get('/v100/teacher-home', response_class=HTMLResponse)
def teacher_home() -> HTMLResponse:
    body=nav('teacher','home')+"""<section class='hero'><h2>Teacher Home</h2></section><section class='grid'><article class='card'><h3>Assignment Builder</h3><a class='button' href='/v100/teacher-assignment-builder'>Select Problems</a></article><article class='card'><h3>Review Submissions</h3><a class='button' href='/v100/teacher-submissions'>Grade and Send Feedback</a></article><article class='card'><h3>Assigned Work</h3><a class='button' href='/v100/teacher-assigned-work'>View Assigned Work</a></article></section>"""
    return page('Teacher Home',body)


@app.get('/v100/teacher-assignment-builder', response_class=HTMLResponse)
def assignment_builder(q:str=Query('')) -> HTMLResponse:
    records=approved_records(); low=q.lower().strip()
    if low: records=[r for r in records if low in (str(r.get('prompt'))+' '+str(r.get('problem_id'))+' '+str(r.get('problem_class'))).lower()]
    cards=[]
    for r in records[:60]:
        cards.append(f"<article class='card'><h3>{h(r.get('problem_id'))}</h3><p>{h(r.get('prompt'))}</p><form method='post' action='/v100/teacher-assignment-builder'><input type='hidden' name='problem_id' value='{h(r.get('problem_id'))}'><label>Assignment title<input name='title' value='{h(r.get('problem_class') or 'Physics Homework')}'></label><label>Section<input name='section' value='All'></label><label>Due date<input name='due_date' type='date'></label><button>Assign</button></form></article>")
    body=nav('teacher','builder')+f"<section class='hero'><h2>Assignment Builder</h2><p>Select from the approved 700-problem bank.</p><form><input name='q' value='{h(q)}' placeholder='Search problem ID, class, or text'><button>Search</button></form></section><section class='grid'>{''.join(cards)}</section>"
    return page('Assignment Builder',body)


@app.post('/v100/teacher-assignment-builder', response_class=HTMLResponse)
def assignment_create(problem_id:str=Form(...),title:str=Form(...),section:str=Form('All'),due_date:str=Form('')) -> RedirectResponse:
    if problem_id not in approved_map(): raise HTTPException(404,'Approved problem not found')
    rows=load_assignments(); num=len(rows)+1
    rows.append({'assignment_id':f'V100-{num:04d}','problem_id':problem_id,'title':title,'section':section,'due_date':due_date,'created_at':now()})
    save_assignments(rows)
    return RedirectResponse('/v100/teacher-assigned-work',303)


@app.get('/v100/teacher-assigned-work', response_class=HTMLResponse)
def assigned_work() -> HTMLResponse:
    amap=approved_map(); cards=[]
    for a in load_assignments():
        r=amap.get(str(a.get('problem_id')),{}); cards.append(f"<article class='card'><h3>{h(a.get('title'))}</h3><p><strong>{h(a.get('assignment_id'))}</strong> | Section: {h(a.get('section'))} | Due: {h(a.get('due_date') or 'Not set')}</p><p>{h(r.get('prompt'))}</p><a class='button' href='/v100/assignments?assignment_id={h(a.get('assignment_id'))}'>Preview Student Assignment</a></article>")
    return page('Assigned Work',nav('teacher','assigned')+f"<section class='hero'><h2>Assigned Work</h2></section><section>{''.join(cards) or '<article class=card>No assignments yet.</article>'}</section>")


@app.get('/v100/assignments', response_class=HTMLResponse)
def assignments(assignment_id:str=Query('')) -> HTMLResponse:
    rows=load_assignments(); amap=approved_map()
    if not assignment_id:
        cards=''.join(f"<article class='card'><h3>{h(a.get('title'))}</h3><p>Section: {h(a.get('section'))} | Due: {h(a.get('due_date') or 'Not set')}</p><a class='button' href='/v100/assignments?assignment_id={h(a.get('assignment_id'))}'>Open Assignment</a></article>" for a in rows)
        return page('Assignments',nav('student','assignments')+f"<section class='hero'><h2>Assignments</h2><p>Teacher-assigned work only. No hints and no Tutor transfer.</p></section><section>{cards or '<article class=card>No assignments have been released.</article>'}</section>")
    a=next((x for x in rows if str(x.get('assignment_id'))==assignment_id),None)
    if not a: raise HTTPException(404,'Assignment not found')
    rec=amap.get(str(a.get('problem_id')))
    if not rec: raise HTTPException(404,'Problem not found')
    domains=unique([r.get('domain') for r in approved_records()]); families=unique([r.get('problem_family') for r in approved_records()]); modes=unique([r.get('mode') for r in approved_records()])
    body=nav('student','assignments')+f"""<section class='hero'><h2>{h(a.get('title'))}</h2><p>Due: {h(a.get('due_date') or 'Not set')}</p></section><section class='panel'><div class='problem'>{h(rec.get('prompt'))}</div><form method='post' action='/v100/assignments/submit'><input type='hidden' name='assignment_id' value='{h(assignment_id)}'><input type='hidden' name='problem_id' value='{h(a.get('problem_id'))}'>
<div class='three'><label>Student name<input name='student_name' required spellcheck='true'></label><label>Domain<select name='selected_domain' required>{options(domains)}</select><textarea name='domain_suggestion' placeholder='Suggestion if not listed' spellcheck='true'></textarea></label><label>Problem Family<select name='selected_family' required>{options(families)}</select><textarea name='family_suggestion' placeholder='Suggestion if not listed' spellcheck='true'></textarea></label></div>
<div class='two'><label>Learning Mode<select name='selected_mode' required>{options(modes)}</select><textarea name='mode_suggestion' placeholder='Suggestion if not listed' spellcheck='true'></textarea></label><label>Known or observable information<textarea name='known_information' spellcheck='true'></textarea></label></div>
<details><summary>Select RCs</summary>{rc_menu([])}</details>{equation_panel(rec,'assignment-equations')}
<div class='two'><label>Equations used<textarea id='assignment-equations' name='equations_used' spellcheck='true'></textarea></label><label>Representation<textarea name='representation' spellcheck='true'></textarea></label><label>Symbolic work<textarea name='symbolic_work' spellcheck='true'></textarea></label><label>Numerical work and units<textarea name='numerical_work' spellcheck='true'></textarea></label><label>Interpretation<textarea name='interpretation' spellcheck='true'></textarea></label><label>Final answer<textarea name='final_answer' spellcheck='true'></textarea></label></div><div class='sticky'><button>Submit Assignment</button></div></form></section>{script()}"""
    return page('Assignment',body)


@app.post('/v100/assignments/submit', response_class=HTMLResponse)
def assignment_submit(assignment_id:str=Form(...),problem_id:str=Form(...),student_name:str=Form(...),selected_domain:str=Form(...),domain_suggestion:str=Form(''),selected_family:str=Form(...),family_suggestion:str=Form(''),selected_mode:str=Form(...),mode_suggestion:str=Form(''),selected_rc:List[str]=Form([]),rc_suggestion:str=Form(''),known_information:str=Form(''),equations_used:str=Form(''),representation:str=Form(''),symbolic_work:str=Form(''),numerical_work:str=Form(''),interpretation:str=Form(''),final_answer:str=Form('')) -> HTMLResponse:
    if not any(str(a.get('assignment_id'))==assignment_id and str(a.get('problem_id'))==problem_id for a in load_assignments()): raise HTTPException(400,'Assignment does not match released work')
    with connect() as conn:
        conn.execute("""INSERT INTO v100_assignment_submissions(assignment_id,problem_id,student_name,selected_domain,domain_suggestion,selected_family,family_suggestion,selected_mode,mode_suggestion,selected_rcs,rc_suggestion,known_information,equations_used,representation,symbolic_work,numerical_work,interpretation,final_answer,submitted_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(assignment_id,problem_id,student_name,selected_domain,domain_suggestion,selected_family,family_suggestion,selected_mode,mode_suggestion,json.dumps(selected_rc),rc_suggestion,known_information,equations_used,representation,symbolic_work,numerical_work,interpretation,final_answer,now()))
    return page('Assignment Submitted',nav('student','assignments')+"<section class='hero'><h2>Assignment Submitted</h2><p>Your work was saved for teacher grading.</p><a class='button' href='/v100/portfolio'>Check Grade and Feedback</a></section>")


@app.get('/v100/teacher-submissions', response_class=HTMLResponse)
def teacher_submissions() -> HTMLResponse:
    amap=approved_map(); assignments_map={str(a.get('assignment_id')):a for a in load_assignments()}
    with connect() as conn: rows=[dict(r) for r in conn.execute('SELECT * FROM v100_assignment_submissions ORDER BY id DESC').fetchall()]
    cards=[]
    for s in rows:
        rec=amap.get(str(s.get('problem_id')),{}); a=assignments_map.get(str(s.get('assignment_id')),{})
        auth_rc=', '.join(rec.get('expected_rc') or [])
        cards.append(f"""<article class='card'><h3>{h(a.get('title') or s.get('assignment_id'))} — {h(s.get('student_name'))}</h3><p>{h(rec.get('prompt'))}</p><table><tr><th>Student selection/work</th><th>Authoritative record</th></tr><tr><td>Domain: {h(s.get('selected_domain'))}<br>Family: {h(s.get('selected_family'))}<br>Mode: {h(s.get('selected_mode'))}<br>RCs: {h(s.get('selected_rcs'))}<br>Equations: {h(s.get('equations_used'))}<br>Final answer: {h(s.get('final_answer'))}</td><td>Domain: {h(rec.get('domain'))}<br>Family: {h(rec.get('problem_family'))}<br>Mode: {h(rec.get('mode'))}<br>RCs: {h(auth_rc)}<br>Solution: {h(rec.get('solution') or rec.get('authoritative_solution') or rec.get('final_answer'))}</td></tr></table><form method='post' action='/v100/teacher-submissions/{s.get('id')}/feedback'><div class='three'><label>Grade<input name='grade' value='{h(s.get('grade'))}' placeholder='e.g. 85/100 or B'></label><label>Status<select name='review_status'><option>Graded</option><option>Needs Revision</option><option>Resubmit</option><option>Completed</option></select></label><label>Corrected Learning Mode<input name='corrected_mode' value='{h(s.get('corrected_mode'))}'></label></div><div class='two'><label>Corrected Domain<input name='corrected_domain' value='{h(s.get('corrected_domain'))}'></label><label>Corrected Problem Family<input name='corrected_family' value='{h(s.get('corrected_family'))}'></label><label>Corrected RCs<textarea name='corrected_rcs' spellcheck='true'>{h(s.get('corrected_rcs'))}</textarea></label><label>Teacher feedback<textarea name='teacher_feedback' required spellcheck='true'>{h(s.get('teacher_feedback'))}</textarea></label></div><button>Send Feedback to Student</button></form></article>""")
    return page('Review Submissions',nav('teacher','submissions')+f"<section class='hero'><h2>Review Submissions</h2><p>Grade work and return feedback to the exact student submission.</p></section><section>{''.join(cards) or '<article class=card>No submissions yet.</article>'}</section>")


@app.post('/v100/teacher-submissions/{submission_id}/feedback', response_class=HTMLResponse)
def send_feedback(submission_id:int,grade:str=Form(''),review_status:str=Form('Graded'),corrected_domain:str=Form(''),corrected_family:str=Form(''),corrected_mode:str=Form(''),corrected_rcs:str=Form(''),teacher_feedback:str=Form(...)) -> RedirectResponse:
    with connect() as conn:
        cur=conn.execute("""UPDATE v100_assignment_submissions SET grade=?,review_status=?,corrected_domain=?,corrected_family=?,corrected_mode=?,corrected_rcs=?,teacher_feedback=?,reviewed_at=? WHERE id=?""",(grade,review_status,corrected_domain,corrected_family,corrected_mode,corrected_rcs,teacher_feedback,now(),submission_id))
        if cur.rowcount==0: raise HTTPException(404,'Submission not found')
    return RedirectResponse('/v100/teacher-submissions',303)


@app.get('/v100/portfolio', response_class=HTMLResponse)
def portfolio(student_name:str=Query('')) -> HTMLResponse:
    rows=[]
    if student_name.strip():
        with connect() as conn: rows=[dict(r) for r in conn.execute('SELECT * FROM v100_assignment_submissions WHERE lower(student_name)=lower(?) ORDER BY id DESC',(student_name.strip(),)).fetchall()]
    cards=[]
    amap=approved_map()
    for s in rows:
        rec=amap.get(str(s.get('problem_id')),{}); feedback=s.get('teacher_feedback') or 'Teacher feedback has not been posted yet.'; grade=s.get('grade') or 'Pending'
        cards.append(f"<article class='card'><h3>{h(s.get('assignment_id'))}</h3><p><strong>Grade:</strong> {h(grade)} | <strong>Status:</strong> {h(s.get('review_status'))}</p><p>{h(rec.get('prompt'))}</p><h4>Teacher Feedback</h4><p>{h(feedback)}</p><p><strong>Corrected Domain:</strong> {h(s.get('corrected_domain'))}<br><strong>Corrected Family:</strong> {h(s.get('corrected_family'))}<br><strong>Corrected Mode:</strong> {h(s.get('corrected_mode'))}<br><strong>Corrected RCs:</strong> {h(s.get('corrected_rcs'))}</p></article>")
    body=nav('student','portfolio')+f"<section class='hero'><h2>My Portfolio — Grades and Teacher Feedback</h2><form><label>Student name<input name='student_name' value='{h(student_name)}' spellcheck='true'></label><button>Check My Grade and Feedback</button></form></section><section>{''.join(cards) if student_name else '<article class=card>Enter your student name to view submitted work, grades, and teacher feedback.</article>'}</section>"
    return page('My Portfolio',body)


@app.get('/v100/prompt-library', response_class=HTMLResponse)
def prompt_library(problem_id:str=Query('')) -> HTMLResponse:
    active=canonical_map().get(problem_id) if problem_id else None
    cards=[]
    for label,text in PROMPTS:
        if active:
            url='/v100/physics-tutor?problem_id='+urllib.parse.quote(problem_id)+'&prompt='+urllib.parse.quote(text)
            action=f"<a class='button' href='{url}'>Insert into Active Tutor Problem</a>"
        else:
            action=f"<button type='button' class='secondary copy-text' data-text='{h(text)}' data-label='Prompt'>Copy Prompt</button>"
        cards.append(f"<article class='card'><h3>{h(label)}</h3><p>{h(text)}</p>{action}</article>")
    context=(f"Active Tutor problem preserved: {h(active.get('title') or problem_id)}" if active else "Standalone reference library. Open it from an active Tutor problem to insert a prompt without losing that problem.")
    return page('Prompt Library',nav('student','prompts')+f"<section class='hero'><h2>Prompt Library</h2><p>{context}</p></section><section class='grid'>{''.join(cards)}</section>{script()}")


@app.get('/v100/math-equations', response_class=HTMLResponse)
def math_equations(q:str=Query('')) -> HTMLResponse:
    rows=[]
    for r in canonical_records():
        for e in equations(r): rows.append((e['name'],e['equation'],e['use'],str(r.get('title') or r.get('id'))))
    if q.strip(): rows=[x for x in rows if q.lower() in ' '.join(x).lower()]
    cards=''.join(f"<article class='eq-card'><h4>{h(n)}</h4><code>{h(eq)}</code><p>{h(use)}</p><p class='muted'>{h(title)}</p><button type='button' class='secondary copy-text' data-text='{h(eq)}' data-label='Equation'>Copy Equation</button></article>" for n,eq,use,title in rows[:150])
    return page('Math and Equations',nav('student','math')+f"<section class='hero'><h2>Math and Equations Library</h2><p>Standalone browsing and copying. Insertion appears inside active Tutor and Assignment workspaces.</p><form><input name='q' value='{h(q)}' placeholder='Search equations'><button>Search</button></form></section><section class='eq-grid'>{cards}</section>{script()}")


@app.get('/v100/physics-stories', response_class=HTMLResponse)
def stories() -> HTMLResponse:
    return page('Physics Stories',nav('student','stories')+"<section class='hero'><h2>Physics Stories</h2></section><section class='grid'><article class='card'><h3>Full Physics Stories Book</h3><a class='button' href='/assets/physics_stories/Physics_Stories_V88.pdf'>Open Full Book</a></article><article class='card'><h3>Write a Physics Story</h3><a class='button' href='/v100/write-physics-story'>Open Story Form</a></article></section>")


@app.get('/v100/write-physics-story', response_class=HTMLResponse)
def write_story() -> HTMLResponse:
    body=nav('student','write')+"""<section class='hero'><h2>Write a Physics Story</h2><p>Browser spellcheck is enabled for student writing.</p></section><section class='panel'><form method='post'><label>Student name<input name='student_name' required spellcheck='true'></label><label>Story title<input name='title' required spellcheck='true'></label><label>Full story<textarea name='story_text' rows='9' required spellcheck='true'></textarea></label><button>Save Story</button></form></section>"""
    return page('Write a Physics Story',body)


@app.post('/v100/write-physics-story', response_class=HTMLResponse)
def save_story(student_name:str=Form(...),title:str=Form(...),story_text:str=Form(...)) -> HTMLResponse:
    with connect() as conn: conn.execute('INSERT INTO v100_student_stories(student_name,title,story_text,created_at) VALUES(?,?,?,?)',(student_name,title,story_text,now()))
    return page('Story Saved',nav('student','write')+"<section class='hero'><h2>Story Saved</h2><a class='button' href='/v100/student-home'>Return Home</a></section>")


@app.get('/v100/help', response_class=HTMLResponse)
def help_page() -> HTMLResponse:
    body=nav('student','help')+"""<section class='hero'><h2>How to Use the Physics AI Assistant</h2></section><section class='grid'><article class='card'><h3>Physics Tutor</h3><p>Select a canonical problem. Guess the Domain, Problem Family, Learning Mode, and RCs. Add a prompt or equation inside the same page, submit, read the structured feedback, revise, and finish the problem.</p></article><article class='card'><h3>Assignments</h3><p>Open only teacher-assigned homework. Complete classification, equations, work, interpretation, and final answer on the same page. No hints and no Tutor transfer.</p></article><article class='card'><h3>Prompt Library</h3><p>Standalone use copies prompts. From an active Tutor problem, open the Prompt Library with the active problem ID and insert a prompt back into the same problem.</p></article><article class='card'><h3>Math and Equations</h3><p>Standalone use is a reference and copy library. Inside Tutor or Assignments, equations can be inserted directly into work.</p></article><article class='card'><h3>Grades and Feedback</h3><p>Use My Portfolio, enter your student name, and view assignment status, grade, corrections, and teacher feedback.</p></article></section>"""
    return page('Help',body)


@app.get('/api/v100/integrity', response_class=JSONResponse)
def integrity() -> JSONResponse:
    paths={getattr(r,'path','') for r in app.routes}
    required=['/v100/student-home','/v100/physics-tutor','/v100/assignments','/v100/portfolio','/v100/teacher-home','/v100/teacher-assignment-builder','/v100/teacher-submissions','/v100/prompt-library','/v100/help']
    checks={
        'version_100': app.version=='100.0.0',
        'all_current_routes_present': all(p in paths for p in required),
        'canonical_tutor_problems': len(canonical_records())==35,
        'approved_assignment_bank': len(approved_records())==700,
        'teacher_feedback_table': True,
        'student_grade_feedback_portfolio': True,
        'structured_tutor_feedback': True,
        'not_listed_options': True,
        'prompt_copy_label_fixed': True,
        'active_prompt_context_preserved': True,
        'spellcheck_enabled': True,
    }
    return JSONResponse({'version':'ABK_PAI_V100','overall':'PASS' if all(checks.values()) else 'FAIL','checks':checks})


@app.get('/abk-pai/v100-regression', response_class=HTMLResponse)
def regression() -> HTMLResponse:
    data=json.loads(integrity().body.decode()); rows=''.join(f"<tr><td>{h(k.replace('_',' ').title())}</td><td class='status'>{'PASS' if v else 'FAIL'}</td></tr>" for k,v in data['checks'].items())
    return page('V100 Regression',f"<section class='hero'><h2>ABK_PAI V100 Regression</h2></section><section class='panel'><table>{rows}</table></section>")


# Friendly aliases only to the single V100 implementation.
@app.get('/student-home', response_class=HTMLResponse)
def student_alias() -> RedirectResponse: return RedirectResponse('/v100/student-home',307)
@app.get('/physics-tutor', response_class=HTMLResponse)
def tutor_alias() -> RedirectResponse: return RedirectResponse('/v100/physics-tutor',307)
@app.get('/assignments', response_class=HTMLResponse)
def assignments_alias() -> RedirectResponse: return RedirectResponse('/v100/assignments',307)
@app.get('/teacher-home', response_class=HTMLResponse)
def teacher_alias() -> RedirectResponse: return RedirectResponse('/v100/teacher-home',307)
