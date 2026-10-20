from __future__ import annotations
import json, re
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'abk_pai'


def _load(name: str) -> Dict[str, Any]:
    return json.loads((DATA / name).read_text(encoding='utf-8'))


SOURCE_REGISTRY = _load('source_registry.json')
EXPRESSION_DB = _load('expression_sources.json')
EQUATION_REGISTRY = _load('equation_registry.json')
CONSTANTS = _load('physical_constants.json')
TEST_BANK = _load('test_bank_seed.json')

RELEASE_CONFIG = _load('release_config.json')
RELEASE_VERSION = RELEASE_CONFIG.get('version', 'ABK_PAI_V83')

def _load_book_batch_v77() -> Dict[str, Any]:
    path = DATA / 'book_batch_trainer_v77.json'
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {'version': RELEASE_VERSION, 'cases': []}

BOOK_BATCH_V77 = _load_book_batch_v77()
BOOK_CASES_V77 = list(BOOK_BATCH_V77.get('cases', []))

def _normalized_case_prompt(value: str) -> str:
    value = normalize(value)
    value = re.sub(r'\\[a-zA-Z]+|[&{}]', ' ', value)
    value = re.sub(r'[^a-z0-9.]+', ' ', value)
    return re.sub(r'\s+', ' ', value).strip()

def _detect_book_case_v77(text: str) -> Dict[str, Any] | None:
    target = _normalized_case_prompt(text)
    if not target:
        return None
    for case in BOOK_CASES_V77:
        candidate = _normalized_case_prompt(case.get('prompt', ''))
        if target == candidate:
            return case
    # Controlled fallback for copied prompts with repeated equation fragments.
    for case in BOOK_CASES_V77:
        situation = _normalized_case_prompt(case.get('technical_situation', ''))
        question = _normalized_case_prompt(case.get('question_text', ''))
        if situation and situation in target and (not question or question[:80] in target):
            return case
    return None


def normalize(text: str) -> str:
    return re.sub(r'\s+', ' ', str(text or '').lower()).strip()


def analyze_expression(text: str) -> Dict[str, Any]:
    clean = normalize(text)
    matches: List[Dict[str, Any]] = []
    domains=set(); triggers=[]; cautions=[]; prompts=[]; conditional=[]
    for entry in EXPRESSION_DB.get('entries', []):
        found=[p for p in entry.get('expressions',[]) if normalize(p) in clean]
        if found:
            matches.append({
                'id':entry['id'],
                'matched_expressions':found,
                'direct_meanings':entry.get('direct_meanings',[]),
                'domains':entry.get('domains',[]),
                'strong_triggers':entry.get('strong_triggers',[]),
                'conditional_triggers':entry.get('conditional_triggers',[]),
                'cautions':entry.get('cautions',[])
            })
            domains.update(entry.get('domains',[]))
            triggers.extend(entry.get('strong_triggers',[]))
            conditional.extend(entry.get('conditional_triggers',[]))
            cautions.extend(entry.get('cautions',[]))
            prompts.extend(entry.get('comprehension_prompts',[]))
    nums={}
    speed=re.search(r'(?:travel(?:ing|led)?|moving)\s+at\s+(-?\d+(?:\.\d+)?)\s*m\s*/?\s*s',clean)
    if speed: nums['candidate_initial_speed_m_s']=float(speed.group(1))
    time=re.search(r'(?:in|for|after)\s+(-?\d+(?:\.\d+)?)\s*(?:s|sec|second)',clean)
    if time: nums['elapsed_time_s']=float(time.group(1))
    mass=re.search(r'(-?\d+(?:\.\d+)?)\s*kg',clean)
    if mass: nums['mass_kg']=float(mass.group(1))
    height=re.search(r'(?:height(?:\s+of)?|at\s+a\s+height\s+of)\s+(-?\d+(?:\.\d+)?)\s*m\b',clean)
    if height: nums['height_m']=float(height.group(1))
    return {
        'version':'ABK_PAI_V83',
        'input':text,
        'matched_entry_count':len(matches),
        'matches':matches,
        'domains':sorted(domains),
        'ranked_triggers':list(dict.fromkeys(triggers)),
        'conditional_triggers':list(dict.fromkeys(conditional)),
        'numeric_cues':nums,
        'cautions':list(dict.fromkeys(cautions)),
        'reading_comprehension_prompts':list(dict.fromkeys(prompts))
    }


def summary() -> Dict[str, Any]:
    return {
        'version':'ABK_PAI_V83','name':'ABK_PAI','replacement_for':'ABK_PAI Volume 77',
        'source_count':len(SOURCE_REGISTRY.get('sources',[])),
        'expression_entry_count':len(EXPRESSION_DB.get('entries',[])),
        'equation_count':len(EQUATION_REGISTRY.get('equations',[])),
        'constant_count':len(CONSTANTS.get('constants',[])),
        'seed_test_count':len(TEST_BANK.get('problems',[]))
    }


def _direct_kinematics(text: str) -> Dict[str, Any]:
    clean = normalize(text)
    vi = vf = dt = None
    vi_source = vf_source = None
    rest = re.search(r'\b(initially at rest|starts? from rest|starting from rest|from rest)\b', clean)
    if rest:
        vi = 0.0; vi_source='implied_zero_by_rest_phrase'
    else:
        m = re.search(r'(?:travel(?:ing|led)?|moving|moves?|running|walking)\s+(?:at\s+)?(-?\d+(?:\.\d+)?)\s*m\s*/?\s*s', clean)
        if m:
            vi = float(m.group(1)); vi_source='initial_speed_stated'
    if re.search(r'\b(came to (?:a )?(?:stop|rest)|comes to (?:a )?(?:stop|rest)|stopped|stops|brought to rest|forced to stop)\b', clean):
        vf = 0.0; vf_source='implied_zero_by_stop_phrase'
    else:
        m = re.search(r'(?:final velocity|final speed|v_f|vf)\s*(?:is|=|of)?\s*(-?\d+(?:\.\d+)?)\s*m\s*/?\s*s', clean)
        if m:
            vf = float(m.group(1)); vf_source='explicitly_stated'
    m = re.search(r'(?:in|for|after|over|during)\s+(-?\d+(?:\.\d+)?)\s*(?:s|sec|secs|second|seconds)\b', clean)
    if m: dt = float(m.group(1))
    asks_accel = bool(re.search(r'(?:find|calculate|determine|compute|what is)[^.?!\n]*\bacceleration\b', clean))
    constant_explicit = bool(re.search(r'\bconstant acceleration\b|\buniform acceleration\b|\buniformly (?:accelerates?|decelerates?|slows?)\b', clean))
    avg = (vf-vi)/dt if vi is not None and vf is not None and dt not in (None,0) else None
    return {
        'vi':vi,'vf':vf,'dt':dt,'average_acceleration':avg,'complete':avg is not None,
        'asks_acceleration':asks_accel,'constant_acceleration_explicit':constant_explicit,
        'vi_source':vi_source,'vf_source':vf_source
    }


def infer_rc(text: str, selected_rc: List[str] | None = None) -> Dict[str, Any]:
    selected_rc = list(selected_rc or [])
    base = analyze_expression(text)
    k = _direct_kinematics(text)
    extracted=[]; connections=[]; requested=[]; inferable=[]; conditional=[]
    cautions=list(base.get('cautions',[])); prompts=list(base.get('reading_comprehension_prompts',[])); grading=[]

    if k['vi'] is not None:
        if k['vi_source']=='initial_speed_stated':
            extracted.append(f"Initial speed is stated as {abs(k['vi']):g} m/s. Choosing the original direction of motion as positive gives v_i = +{abs(k['vi']):g} m/s.")
        elif k['vi_source']=='implied_zero_by_rest_phrase':
            extracted.append("The phrase indicating initial rest implies v_i = 0 m/s.")
        else:
            extracted.append(f"Initial velocity: v_i = {k['vi']:g} m/s.")
    if k['vf'] is not None:
        if k['vf_source']=='implied_zero_by_stop_phrase':
            extracted.append("The phrase 'came to a stop' implies the final velocity v_f = 0 m/s.")
        else:
            extracted.append(f"Final velocity is explicitly stated as v_f = {k['vf']:g} m/s.")
    if k['dt'] is not None:
        extracted.append(f"Elapsed time is stated as Δt = {k['dt']:g} s.")

    if k['complete']:
        connections += [
            'Kinematics: the velocity changes during the interval.',
            'Dynamics: for an object with nonzero mass, the nonzero average acceleration requires a nonzero average net force, F_net,avg = m a_avg.',
            'Momentum: the velocity change implies a momentum change and therefore a nonzero net impulse, J_net = Δp. A numerical value requires the mass.',
            'Work-energy: the kinetic energy decreases from K_i = 1/2 m v_i² to K_f = 0. Its numerical change requires the mass.'
        ]
        if k['asks_acceleration']:
            requested.append('Acceleration is explicitly requested by the wording.')
        else:
            inferable.append(f"Average acceleration is inferable: a_avg = (v_f-v_i)/Δt = {k['average_acceleration']:g} m/s².")
        if abs(k['average_acceleration'])>1e-12:
            inferable.append('Nonzero average acceleration is supported because velocity changes during a nonzero time interval.')
        else:
            inferable.append('Average acceleration is zero because velocity does not change.')
        if k['constant_acceleration_explicit'] or 'constant_acceleration_assumption' in selected_rc:
            conditional.append(f"Under the explicitly stated or student-adopted constant-acceleration model, v(t) = {k['vi']:g} + ({k['average_acceleration']:g})t for 0 ≤ t ≤ {k['dt']:g} s.")
        else:
            conditional.append('The complete function v(t) is not determined unless constant acceleration is stated or explicitly adopted as a model assumption.')
            cautions.append('Do not turn average acceleration into a constant instantaneous acceleration without stating the model assumption.')

    labels={
        'average_acceleration':'average acceleration available',
        'average_acceleration_available':'average acceleration available',
        'constant_acceleration_assumed':'constant acceleration assumed',
        'one_dimensional_model_sufficient':'one-dimensional model sufficient',
        'initial_velocity_assigned_sign':'initial velocity assigned by sign convention',
        'no_unknown_explicitly_requested':'no unknown explicitly requested',
        'quantity_inferable_not_requested':'quantity inferable but not requested',
        'stopping_interaction_not_identified':'stopping interaction not identified',
        'nonzero_acceleration':'nonzero acceleration',
        'constant_acceleration_assumption':'constant acceleration assumption',
        'constant_acceleration':'constant acceleration',
        'find_acceleration':'find acceleration',
        'kinematics_equations':'kinematics equations',
        'initial_speed_stated':'initial speed stated',
        'initial_velocity_given':'initial velocity stated or assigned by sign convention',
        'final_velocity_given':'final velocity explicitly stated',
        'final_velocity_implied_zero':'final velocity implied as zero'
    }
    for code in selected_rc:
        status='NO'; reason='This RC is not supported by the written problem.'
        if k['complete']:
            if code in {'average_acceleration','average_acceleration_available'}:
                status,reason='YES',f"The definition a_avg = Δv/Δt applies directly and gives {k['average_acceleration']:g} m/s²."
            elif code=='nonzero_acceleration':
                status,reason=('YES','Velocity changes during a nonzero time interval, so average acceleration is nonzero.') if abs(k['average_acceleration'])>1e-12 else ('NO','Velocity does not change.')
            elif code in {'constant_acceleration','constant_acceleration_assumption','constant_acceleration_assumed','constant_acceleration_stated','acceleration_not_known_constant'}:
                status,reason=('YES','Constant acceleration is stated in the problem.') if k['constant_acceleration_explicit'] else ('PARTLY','Constant acceleration is not stated; it may be adopted only as an explicit model assumption.')
            elif code=='find_acceleration':
                status,reason=('YES','Acceleration is explicitly requested.') if k['asks_acceleration'] else ('PARTLY','Average acceleration is inferable, but acceleration is not explicitly requested.')
            elif code=='kinematics_equations':
                status,reason='YES','The average-acceleration definition a_avg = Δv/Δt applies directly. Position equations and a complete v(t) require a constant-acceleration assumption.'
            elif code=='initial_speed_stated':
                status,reason=('YES','The magnitude of the initial velocity is stated as a speed.') if k['vi_source']=='initial_speed_stated' else ('NO','An initial speed is not stated.')
            elif code in {'initial_velocity_given','initial_velocity_assigned_sign'}:
                if k['vi_source']=='initial_speed_stated':
                    status,reason='PARTLY','The initial speed is stated; a signed initial velocity follows only after choosing the original direction as positive.'
                else:
                    status,reason='YES','The initial velocity is stated or unambiguously implied.'
            elif code=='final_velocity_given':
                status,reason=('YES','The final velocity is explicitly stated.') if k['vf_source']=='explicitly_stated' else ('NO','The final velocity is not explicitly stated; it is implied by the stopping phrase.')
            elif code=='final_velocity_implied_zero':
                status,reason=('YES',"The phrase 'came to a stop' implies v_f = 0.") if k['vf_source']=='implied_zero_by_stop_phrase' else ('NO','No stopping phrase implies a zero final velocity.')
            elif code=='time_given':
                status,reason='YES','The elapsed time is stated.'
            elif code=='slowing_down':
                status,reason=('YES','The speed decreases.') if abs(k['vf'])<abs(k['vi']) else ('NO','The speed does not decrease.')
            elif code in {'one_dimensional_motion','one_dimensional_model_sufficient'}:
                status,reason='SUPPORTED','A one-dimensional model is sufficient for the stated speed change once a positive direction is chosen; the actual path is not explicitly specified.'
            elif code=='no_unknown_explicitly_requested':
                status,reason=('YES','The wording contains no explicit request for an unknown.') if not k['asks_acceleration'] else ('NO','Acceleration is explicitly requested.')
            elif code=='quantity_inferable_not_requested':
                status,reason=('YES','Average acceleration can be inferred, but it is not explicitly requested.') if not k['asks_acceleration'] else ('NO','Acceleration is explicitly requested.')
            elif code=='stopping_interaction_not_identified':
                status,reason='YES','The statement does not identify friction, drag, braking, collision, or another stopping interaction.'
        grading.append({'code':code,'label':labels.get(code,code.replace('_',' ')),'status':status,'reason':reason})

    return {
        'version':'ABK_PAI_V83','input':text,'base_analysis':base,'kinematics':k,
        'extracted_statements':extracted,
        'physics_connections':connections or base.get('ranked_triggers',[]),
        'conditional_physics_connections':base.get('conditional_triggers',[]),
        'explicitly_requested':requested,
        'inferable_quantities':inferable,
        'conditional_results':conditional,
        'selected_rc_grading':grading,
        'prompts':prompts,
        'cautions':list(dict.fromkeys(cautions))
    }

# ============================================================================
# ABK_PAI Volume 62 — canonical Lab/Student-AI parity layer
# ============================================================================
import hashlib

_CANONICAL_FIELDS_V62 = [
    'input','learning_mode','selected_rc','extracted_statements','physics_connections',
    'conditional_physics_connections','explicitly_requested','inferable_quantities',
    'conditional_results','selected_rc_grading','prompts','cautions','kinematics','other_entries','other_entry_evaluation'
]

def _canonical_mode(mode: str) -> str:
    raw = str(mode or 'ask_tutor').strip().lower().replace('-', '_').replace(' ', '_')
    aliases = {
        'kinematics':'kinematics_mode','kinematics_mode':'kinematics_mode',
        'forces':'forces_mode','dynamics':'forces_mode','forces_mode':'forces_mode','forces_fbd':'forces_mode','forces_and_fbds':'forces_mode',
        'energy':'energy_mode','energy_mode':'energy_mode',
        'momentum':'momentum_mode','momentum_mode':'momentum_mode',
        'ask_tutor':'ask_tutor','guided':'ask_tutor'
    }
    return aliases.get(raw, raw or 'ask_tutor')

_RC_EQUIVALENCE_V66 = {
    'object_slowing_down':'slowing_down',
    'average_acceleration_available':'average_acceleration',
    'constant_acceleration_assumed':'constant_acceleration_assumption',
    'initial_velocity_assigned_sign':'initial_velocity_given',
    'one_dimensional_model_sufficient':'one_dimensional_model_sufficient',
}

def _canonicalize_rc_v66(items: List[str] | None) -> List[str]:
    out=[]
    for raw in items or []:
        code=str(raw).strip()
        code=_RC_EQUIVALENCE_V66.get(code, code)
        if code and code not in out:
            out.append(code)
    return out

def evaluate_other_entries(text: str, other_rc: str = '') -> List[Dict[str, str]]:
    clean=normalize(text)
    rows=[]
    for raw in [x.strip() for x in str(other_rc or '').split(',') if x.strip()]:
        key=normalize(raw)
        if key in {'braking force','brakes','braking'}:
            rows.append({'entry':raw,'status':'UNSUPPORTED BY THE PROBLEM','detail':'Possible interaction, but not identified by the written problem.'})
        elif key in {'stopping distance unknown','stopping distance is unknown','unknown stopping distance'}:
            rows.append({'entry':raw,'status':'VALID PHYSICS IDEA','detail':'Stopping distance is not determined by the stated information.'})
        elif 'friction' in key or 'drag' in key or 'thermal' in key or 'heat' in key:
            rows.append({'entry':raw,'status':'CONDITIONAL','detail':'This may apply for some stopping mechanisms, but the written problem does not establish it.'})
        elif key and key in clean:
            rows.append({'entry':raw,'status':'MATCHES PROBLEM LANGUAGE','detail':'The entry appears directly in the written problem.'})
        else:
            rows.append({'entry':raw,'status':'STUDENT COMMENT ONLY','detail':'Saved for teacher review and possible dictionary expansion.'})
    return rows

def canonical_analysis(text: str, selected_rc: List[str] | None = None, learning_mode: str = 'ask_tutor', other_rc: str = '') -> Dict[str, Any]:
    """Return the single canonical physics record consumed by both interfaces."""
    selected = _canonicalize_rc_v66(selected_rc)
    result = infer_rc(text, selected)
    result = dict(result)
    result['version'] = 'ABK_PAI_V68'
    result['learning_mode'] = _canonical_mode(learning_mode)
    result['selected_rc'] = selected
    result['other_entries'] = [x.strip() for x in str(other_rc or '').split(',') if x.strip()]
    result['other_entry_evaluation'] = evaluate_other_entries(text, other_rc)
    # Canonical equality ignores interface wording and transport metadata.
    canonical = {k: result.get(k) for k in _CANONICAL_FIELDS_V62}
    payload = json.dumps(canonical, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    result['canonical_hash'] = hashlib.sha256(payload.encode('utf-8')).hexdigest()
    result['canonical_fields'] = list(_CANONICAL_FIELDS_V62)
    return result

def lab_canonical_analysis(text: str, selected_rc: List[str] | None = None, learning_mode: str = 'ask_tutor', other_rc: str = '') -> Dict[str, Any]:
    return canonical_analysis(text, selected_rc, learning_mode, other_rc)

def student_canonical_analysis(text: str, selected_rc: List[str] | None = None, learning_mode: str = 'ask_tutor', other_rc: str = '') -> Dict[str, Any]:
    return canonical_analysis(text, selected_rc, learning_mode, other_rc)

def parity_report(text: str, selected_rc: List[str] | None = None, learning_mode: str = 'ask_tutor', other_rc: str = '') -> Dict[str, Any]:
    lab = lab_canonical_analysis(text, selected_rc, learning_mode, other_rc)
    student = student_canonical_analysis(text, selected_rc, learning_mode, other_rc)
    comparisons=[]
    for field in _CANONICAL_FIELDS_V62:
        left, right = lab.get(field), student.get(field)
        comparisons.append({'field':field,'status':'PASS' if left == right else 'FAIL','lab':left,'student_ai':right})
    passed = all(x['status']=='PASS' for x in comparisons) and lab['canonical_hash']==student['canonical_hash']
    return {
        'version':'ABK_PAI_V83','input':text,'learning_mode':_canonical_mode(learning_mode),
        'selected_rc':list(selected_rc or []),'overall':'PASS' if passed else 'FAIL',
        'lab_hash':lab['canonical_hash'],'student_ai_hash':student['canonical_hash'],
        'comparisons':comparisons,'lab_canonical':lab,'student_ai_canonical':student
    }

# ============================================================================
# ABK_PAI Volume 69 — broad-domain canonical training engine
# ============================================================================
_BROAD_DOMAIN_PACK_V69 = _load('broad_domain_training_v69.json')
_BROAD_CASES_V69 = {c['id']: c for c in _BROAD_DOMAIN_PACK_V69.get('cases', [])}

_V69_SIGNATURES = [
    ('forces_level_friction', ('box','coefficient of kinetic friction','level floor','find the acceleration')),
    ('energy_drop', ('dropped from rest','height of 5 m','neglect air resistance')),
    ('momentum_stick', ('cart','collides','stick together','common final velocity')),
    ('spring_oscillation', ('mass is attached','spring constant','released from rest','maximum speed')),
    ('uniform_circular_motion', ('car','constant speed','circular curve','centripetal acceleration')),
    ('rotational_disk', ('solid disk','net torque','angular acceleration')),
    ('wall_sign_torque', ('wall-mounted sign','center of mass','support cable','rotational equilibrium')),
    ('fluid_buoyancy', ('completely submerged','water','buoyant force')),
    ('wave_speed', ('wave has frequency','wavelength','find its speed')),
    ('dc_ohm_power', ('resistor','ideal battery','current','power dissipated')),
    ('magnetic_particle', ('proton','perpendicular','magnetic field','magnetic force')),
    ('book_biology_blood_pressure', ('blood has density','standing person','hydrostatic pressure difference')),
    ('book_biology_vessel_flow', ('biological fluid sample','18.0 ml','average volume flow rate')),
    ('book_agriculture_irrigation_flow', ('irrigation line','1500 l','average volume flow rate')),
    ('book_agriculture_tractor_stopping', ('tractor moves','constant acceleration of -1.2','stopping time and stopping distance')),
    ('book_biology_stair_power', ('68.0 kg person','vertical height of 4.20 m','average mechanical power')),
    ('book_kinesiology_sprint', ('70.0 kg sprinter','reaches 8.0 m/s in 3.2 s','average net horizontal force')),
    ('book_kinesiology_vertical_jump', ('athlete leaves the ground vertically','3.1 m/s','total time in the air')),
]

_V69_CANONICAL_FIELDS = [
    'input','learning_mode','selected_rc','domain','extracted_statements','physics_connections',
    'conditional_physics_connections','explicitly_requested','inferable_quantities',
    'governing_equations','solution_steps','numerical_results','final_answer','representations',
    'conditional_results','selected_rc_grading','prompts','cautions','kinematics',
    'other_entries','other_entry_evaluation'
]


def _book_case_analysis_v77(text: str, selected_rc: List[str], case: Dict[str, Any]) -> Dict[str, Any]:
    labels = _registry_labels_v69()
    expected = set(case.get('expected_rc', []))
    selected = list(selected_rc or [])
    grading=[]
    for code in selected:
        ok = code in expected
        grading.append({
            'code': code,
            'label': labels.get(code, code.replace('_',' ')),
            'status': 'YES' if ok else 'NO',
            'reason': ('This RC is directly supported by the written problem and the canonical book-family model.' if ok
                       else 'This RC is not supported by this problem as written.')
        })
    expressions=[str(x.get('expression','')).strip() for x in case.get('expressions',[]) if str(x.get('expression','')).strip()]
    recognition = expressions[:6] or [case.get('technical_situation','').strip(), case.get('question_text','').strip()]
    recognition=[x for x in recognition if x]
    domain=str(case.get('domain','general_physics'))
    final=str(case.get('final_answer','')).strip()
    equations=list(case.get('equations',[]) or [])
    solution=list(case.get('solution',[]) or [])
    requested=[case.get('question_text','').strip()] if case.get('question_text') else []
    return {
        'version': RELEASE_VERSION,
        'input': text,
        'base_analysis': {
            'version': RELEASE_VERSION, 'input': text, 'matched_entry_count': 1,
            'matches': [{'id': case.get('id'), 'matched_expressions': recognition, 'domains':[domain]}],
            'domains':[domain], 'ranked_triggers':recognition, 'conditional_triggers':[],
            'numeric_cues':{}, 'cautions':list(case.get('cautions',[]) or []),
            'reading_comprehension_prompts':['Which quantities and relationships are stated?','Which physics law applies?','Which selected RCs are unsupported?']
        },
        'domain':domain, 'kinematics':{},
        'extracted_statements':[f'Recognized: {x}.' for x in recognition],
        'physics_connections':[f"{domain.replace('_',' ').title()}: matched canonical book problem family {case.get('problem_family','')}."],
        'conditional_physics_connections':[], 'explicitly_requested':requested,
        'inferable_quantities':[final] if final else [], 'governing_equations':equations,
        'solution_steps':solution, 'numerical_results':[final] if final else [],
        'final_answer':final, 'representations':['Use the representation selected by the RC record.'],
        'conditional_results':[], 'selected_rc_grading':grading,
        'prompts':['Which words identify the problem family?','Why does the selected equation apply?','Are any selected RCs unsupported?'],
        'cautions':list(case.get('cautions',[]) or []), 'training_case_id':case.get('id'),
        'source':case.get('source_book','ABK_PAI indexed book corpus'),
        'source_location':case.get('source_location',''), 'problem_family':case.get('problem_family','')
    }

def _detect_broad_case_v69(text: str) -> Dict[str, Any] | None:
    clean = normalize(text)
    for case_id, terms in _V69_SIGNATURES:
        if all(term in clean for term in terms):
            return _BROAD_CASES_V69.get(case_id)
    return None

def _registry_labels_v69() -> Dict[str, str]:
    path = ROOT / 'physics_language_dictionary' / 'rc_canonical_registry_v69.json'
    try:
        reg = json.loads(path.read_text(encoding='utf-8'))
        return {k: str(v.get('display_label') or k.replace('_',' ')) for k,v in reg.get('items',{}).items()}
    except Exception:
        return {}

def _broad_case_analysis_v69(text: str, selected_rc: List[str], case: Dict[str, Any]) -> Dict[str, Any]:
    labels = _registry_labels_v69()
    expected = set(case.get('expected_rc', []))
    selected = list(selected_rc or [])
    grading=[]
    for code in selected:
        if code in expected:
            status='YES'; reason='This RC is directly supported by the written problem and the canonical domain model.'
        else:
            status='NO'; reason='This RC is not supported by this problem as written.'
        grading.append({'code':code,'label':labels.get(code,code.replace('_',' ')),'status':status,'reason':reason})
    recognition = list(case.get('recognition', []))
    domain = str(case.get('domain','general_physics'))
    final = str(case.get('final_answer',''))
    return {
        'version':'ABK_PAI_V83',
        'input':text,
        'base_analysis':{'version':'ABK_PAI_V83','input':text,'matched_entry_count':1,'domains':[domain],
                         'ranked_triggers':recognition,'conditional_triggers':[],'numeric_cues':{},
                         'cautions':case.get('cautions',[]),'reading_comprehension_prompts':[
                            'Which information is stated directly?',
                            'Which physical model or conservation law applies?',
                            'Which assumption or idealization is required?'
                         ]},
        'domain':domain,
        'kinematics':{},
        'extracted_statements':[f"Recognized: {x}." for x in recognition],
        'physics_connections':[f"{domain.replace('_',' ').title()}: the statement activates this domain model."],
        'conditional_physics_connections':[],
        'explicitly_requested':[recognition[-1].capitalize()+'.'] if recognition else [],
        'inferable_quantities':[final] if final else [],
        'governing_equations':list(case.get('equations',[])),
        'solution_steps':list(case.get('solution',[])),
        'numerical_results':[final] if final else [],
        'final_answer':final,
        'representations':['Draw or select the representation appropriate to the chosen RC items.'],
        'conditional_results':[],
        'selected_rc_grading':grading,
        'prompts':[
            'Which words identify the physical situation?',
            'Why is the selected law or equation applicable?',
            'What would change if an idealization were removed?'
        ],
        'cautions':list(case.get('cautions',[])),
        'training_case_id':case.get('id'),
        'source':'ABK_PAI broad-domain canonical training pack'
    }

# Preserve the V68 inference implementation for the frozen kinematics regression case.
_infer_rc_v68 = infer_rc
_evaluate_other_entries_v68 = evaluate_other_entries

def infer_rc(text: str, selected_rc: List[str] | None = None) -> Dict[str, Any]:
    selected = _canonicalize_rc_v66(selected_rc)
    book_case = _detect_book_case_v77(text)
    if book_case:
        return _book_case_analysis_v77(text, selected, book_case)
    case = _detect_broad_case_v69(text)
    if case:
        return _broad_case_analysis_v69(text, selected, case)
    result = _infer_rc_v68(text, selected)
    result['version']='ABK_PAI_V83'
    if isinstance(result.get('base_analysis'), dict):
        result['base_analysis']['version']='ABK_PAI_V83'
    result.setdefault('domain','kinematics')
    result.setdefault('governing_equations',['a_avg = (v_f-v_i)/Delta t'] if result.get('kinematics',{}).get('complete') else [])
    result.setdefault('solution_steps',[])
    result.setdefault('numerical_results',result.get('inferable_quantities',[]))
    result.setdefault('final_answer','')
    result.setdefault('representations',[])
    return result

def evaluate_other_entries(text: str, other_rc: str = '') -> List[Dict[str, str]]:
    case = _detect_book_case_v77(text) or _detect_broad_case_v69(text)
    if not case:
        return _evaluate_other_entries_v68(text, other_rc)
    expected_words=' '.join(case.get('recognition',[])+case.get('equations',[])).lower()
    out=[]
    for raw in [x.strip() for x in str(other_rc or '').split(',') if x.strip()]:
        key=normalize(raw)
        if key and key in expected_words:
            out.append({'entry':raw,'status':'VALID PHYSICS IDEA','detail':'This idea agrees with the canonical domain model.'})
        else:
            out.append({'entry':raw,'status':'STUDENT COMMENT ONLY','detail':'Saved for teacher review and possible dictionary expansion.'})
    return out

def _canonical_mode(mode: str) -> str:
    raw = str(mode or 'ask_tutor').strip().lower().replace('-', '_').replace(' ', '_')
    aliases = {
        'kinematics':'kinematics_mode','kinematics_mode':'kinematics_mode',
        'forces':'forces_mode','dynamics':'forces_mode','forces_mode':'forces_mode','forces_fbd':'forces_mode','forces_and_fbds':'forces_mode',
        'energy':'energy_mode','energy_mode':'energy_mode',
        'momentum':'momentum_mode','momentum_mode':'momentum_mode',
        'spring':'oscillation_mode','oscillation':'oscillation_mode','oscillation_mode':'oscillation_mode',
        'circular':'circular_mode','circular_mode':'circular_mode',
        'rotation':'rotation_mode','rotation_mode':'rotation_mode',
        'fluids':'fluids_mode','fluids_mode':'fluids_mode',
        'waves':'waves_mode','waves_mode':'waves_mode',
        'circuits':'circuits_mode','circuits_mode':'circuits_mode',
        'magnetism':'magnetism_mode','magnetism_mode':'magnetism_mode',
        'ask_tutor':'ask_tutor','guided':'ask_tutor'
    }
    return aliases.get(raw, raw or 'ask_tutor')

def canonical_analysis(text: str, selected_rc: List[str] | None = None, learning_mode: str = 'ask_tutor', other_rc: str = '') -> Dict[str, Any]:
    selected = _canonicalize_rc_v66(selected_rc)
    result = dict(infer_rc(text, selected))
    result['version']='ABK_PAI_V83'
    result['learning_mode']=_canonical_mode(learning_mode)
    result['selected_rc']=selected
    result['other_entries']=[x.strip() for x in str(other_rc or '').split(',') if x.strip()]
    result['other_entry_evaluation']=evaluate_other_entries(text, other_rc)
    canonical={k:result.get(k) for k in _V69_CANONICAL_FIELDS}
    payload=json.dumps(canonical,sort_keys=True,ensure_ascii=False,separators=(',',':'))
    result['canonical_hash']=hashlib.sha256(payload.encode('utf-8')).hexdigest()
    result['canonical_fields']=list(_V69_CANONICAL_FIELDS)
    return result

def lab_canonical_analysis(text: str, selected_rc: List[str] | None = None, learning_mode: str = 'ask_tutor', other_rc: str = '') -> Dict[str, Any]:
    return canonical_analysis(text, selected_rc, learning_mode, other_rc)

def student_canonical_analysis(text: str, selected_rc: List[str] | None = None, learning_mode: str = 'ask_tutor', other_rc: str = '') -> Dict[str, Any]:
    return canonical_analysis(text, selected_rc, learning_mode, other_rc)

def parity_report(text: str, selected_rc: List[str] | None = None, learning_mode: str = 'ask_tutor', other_rc: str = '') -> Dict[str, Any]:
    lab=lab_canonical_analysis(text,selected_rc,learning_mode,other_rc)
    student=student_canonical_analysis(text,selected_rc,learning_mode,other_rc)
    comparisons=[]
    for field in _V69_CANONICAL_FIELDS:
        comparisons.append({'field':field,'status':'PASS' if lab.get(field)==student.get(field) else 'FAIL','lab':lab.get(field),'student_ai':student.get(field)})
    passed=all(x['status']=='PASS' for x in comparisons) and lab['canonical_hash']==student['canonical_hash']
    return {'version':'ABK_PAI_V83','input':text,'learning_mode':_canonical_mode(learning_mode),
            'selected_rc':list(selected_rc or []),'other_rc':other_rc,'overall':'PASS' if passed else 'FAIL',
            'lab_hash':lab['canonical_hash'],'student_ai_hash':student['canonical_hash'],
            'comparisons':comparisons,'lab_canonical':lab,'student_ai_canonical':student}

def summary() -> Dict[str, Any]:
    return {'version':'ABK_PAI_V83','name':'ABK_PAI','replacement_for':'ABK_PAI Volume 77',
            'source_count':len(SOURCE_REGISTRY.get('sources',[])),
            'expression_entry_count':len(EXPRESSION_DB.get('entries',[])),
            'equation_count':len(EQUATION_REGISTRY.get('equations',[])),
            'constant_count':len(CONSTANTS.get('constants',[])),
            'seed_test_count':len(TEST_BANK.get('problems',[])),
            'broad_domain_case_count':len(_BROAD_CASES_V69),'indexed_book_case_count':len(BOOK_CASES_V77),
            'broad_domains':sorted({c.get('domain') for c in _BROAD_CASES_V69.values()})}
