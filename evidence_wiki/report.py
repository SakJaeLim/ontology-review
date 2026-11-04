import json
from html import escape
from importlib.resources import files
from pathlib import Path


def _browser_values(value):
    if type(value) is int and abs(value) > 2**53 - 1:
        return str(value)
    if isinstance(value, dict):
        return {key: _browser_values(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_browser_values(item) for item in value]
    return value


def render_report(report: dict, destination: Path, *, language: str = "ko") -> None:
    """Write offline HTML, encoding unsafe JavaScript integers as decimal strings."""
    if language not in {"ko", "en"}:
        raise ValueError("language must be 'ko' or 'en'")
    if not isinstance(report, dict):
        raise TypeError("report must be a dictionary")
    data = json.dumps(_browser_values(report), ensure_ascii=False, allow_nan=False)
    # JSON is inert data, but HTML's parser still recognizes closing script tags.
    for character, replacement in (("&", "\\u0026"), ("<", "\\u003c"), (">", "\\u003e"),
                              ("\u2028", "\\u2028"), ("\u2029", "\\u2029")):
        data = data.replace(character, replacement)
    design = files("evidence_wiki").joinpath("design")
    document = _HTML.replace("__LANGUAGE__", language)
    for placeholder, resource in (("__DESIGN_TOKENS__", "open-props.css"),
                                  ("__WORKBENCH_STYLE__", "workbench.css"),
                                  ("__FILES_ICON__", "files.svg"),
                                  ("__SEARCH_ICON__", "search.svg")):
        document = document.replace(placeholder, design.joinpath(resource).read_text(encoding="utf-8"))
    notices = "\n\n".join(design.joinpath(name).read_text(encoding="utf-8")
                          for name in ("LICENSE.open-props", "LICENSE.lucide"))
    document = document.replace("__THIRD_PARTY_NOTICES__", escape(notices))
    document = document.replace("__REPORT_DATA__", data)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(document, encoding="utf-8")


_HTML = r'''<!doctype html>
<html lang="__LANGUAGE__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>Evidence review</title>
<style>
__DESIGN_TOKENS__
__WORKBENCH_STYLE__
</style>
</head>
<body>
<header class="report-header"><div class="shell">
<div class="masthead"><div class="identity"><span class="identity-icon" aria-hidden="true">__FILES_ICON__</span><div><p class="brand">ONTOLOGY REVIEW</p><h1 id="hero-title"></h1></div></div><nav class="languages" aria-label="Language"><button id="lang-ko" lang="ko">한국어</button><button id="lang-en" lang="en">English</button></nav></div>
<div class="report-meta" id="hero-meta"></div>
</div></header>
<main class="shell workspace">
<section aria-labelledby="record-title"><div class="section-line"><h2 id="record-title" data-i18n="records"></h2><p class="muted" data-i18n="recordHint"></p></div><div class="stages" id="stages"></div><p class="stage-description" id="stage-description"></p></section>
<div class="metrics" id="metrics"></div>
<section aria-labelledby="inspect-title"><div class="section-line"><h2 id="inspect-title" data-i18n="inspect"></h2><p id="result-count" class="muted" role="status"></p></div>
<div class="toolbar"><label class="search-field"><span class="field-label" data-i18n="searchLabel"></span><span class="search-input"><span class="search-icon" aria-hidden="true">__SEARCH_ICON__</span><input type="search" id="search" autocomplete="off"></span></label><label class="filter-field"><span class="field-label" data-i18n="filterLabel"></span><select id="filter"></select></label></div>
<div class="inspector"><nav class="claim-list" id="claims" aria-label="Claims"></nav><article class="detail" id="detail" aria-live="polite"></article></div></section>
<div class="bottom"><section class="bottom-card"><h3 data-i18n="affectedPages"></h3><div id="affected-pages"></div></section><section class="bottom-card"><h3 data-i18n="limitations"></h3><div id="limitations"></div></section></div>
<footer class="footer"><span>ONTOLOGY REVIEW</span><span data-i18n="footer"></span></footer>
</main>
<noscript>This report needs JavaScript to display its embedded inspection data. It does not contact a server.</noscript>
<template id="third-party-notices"><pre>__THIRD_PARTY_NOTICES__</pre></template>
<script id="report-data" type="application/json">__REPORT_DATA__</script>
<script>
'use strict';
const report = JSON.parse(document.getElementById('report-data').textContent);
const stages = Array.isArray(report.stages) ? report.stages : [{id:'inspection',inspection:report}];
const dictionary = {
  ko: {
    title:'근거 검토',
    records:'실행 기록',recordHint:'버튼을 누르면 저장된 검사 결과를 불러옵니다.',snapshot:'검사 시점',synthetic:'합성 데이터 데모',single:'현재 검사 기록',
    claims:'등록된 주장',eligible:'재사용 가능',attention:'확인 필요',affectedPages:'영향받은 위키 페이지',inspect:'주장과 근거 살펴보기',
    searchLabel:'주장 검색',searchPlaceholder:'제목, 내용 또는 출처 경로 검색',filterLabel:'현재 재사용 상태',all:'전체',blocked:'재사용 보류',unreviewed:'미검토',
    reviewState:'검토 상태',eligibility:'현재 재사용 상태',approved:'승인',rejected:'반려',needs_review:'재검토 필요',
    evidence:'근거 문서',expected:'주장에 등록된 인용문',actual:'현재 파일의 해당 줄',lines:'줄',subject:'대상',predicate:'속성',value:'주장 값',
    rules:'규칙 검사',ruleNote:'규칙 통과는 사실 여부를 보증하지 않습니다.',conforms:'규칙 통과',violates:'규칙 위반',not_checked:'검사하지 않음',focus:'검사한 대상 수',
    history:'검토 이력',historyNote:'과거 결정은 보존됩니다. 현재 재사용 가능 여부는 위의 상태를 확인하세요.',noDecisions:'기록된 검토가 없습니다.',
    noEvidence:'연결된 근거가 없습니다.',noRules:'연결된 규칙이 없습니다.',noPages:'해당 페이지가 없습니다.',empty:'조건에 맞는 주장이 없습니다.',
    limitations:'이 결과의 범위',native:'이 확장은 별도 검사 도구입니다. LLM Wiki의 기본 승인과 답변 동작을 차단하지 않습니다.',
    snapshotNote:'이 화면은 저장된 검사 결과입니다. 파일 변경을 실시간으로 감시하지 않습니다.',syntheticNote:'데모의 문서, 규칙과 검토자는 모두 합성 예제입니다.',
    footer:'오프라인 보고서. 데이터는 이 파일 안에만 있습니다.',metadata:'버전과 검사 정보',revision:'관측된 버전',digest:'파일 해시',availability:'파일 접근 상태',basis:'검토 기준',
    approve:'승인',accept:'승인',reject:'반려',actor:'검토자',decision:'검토 기록',unknown:'확인되지 않음',present:'있음',available:'접근 가능',missing:'없음',unsafe:'안전하지 않은 경로',
    unreadable:'읽을 수 없음',too_large:'크기 제한 초과',unstable:'검사 중 파일 변경',span_missing:'해당 줄 없음',invalid_encoding:'지원하지 않는 문자 인코딩',
    no_review:'기록된 검토가 없습니다.',review_rejected:'검토자가 반려했습니다.',evidence_unbound:'주장에 연결된 근거가 없습니다.',rules_unbound:'연결된 규칙이 없습니다.',
    evidence_mismatch:'기록된 인용문과 현재 파일 내용이 다릅니다.',evidence_span_missing:'인용한 줄이 현재 파일에 없습니다.',evidence_invalid_encoding:'근거 문서의 문자 인코딩을 읽을 수 없습니다.',
    evidence_missing:'근거 문서가 없습니다.',evidence_unsafe:'근거 문서가 허용된 경로 밖에 있거나 링크를 사용합니다.',evidence_unreadable:'근거 문서를 읽을 수 없습니다.',evidence_too_large:'근거 문서가 크기 제한을 넘었습니다.',evidence_unstable:'검사 중 근거 문서가 변경되었습니다.',
    rule_violates:'주장이 현재 규칙을 통과하지 못했습니다.',rule_not_checked:'규칙 검사를 완료하지 못했습니다.',rule_missing:'규칙 파일이 없습니다.',rule_unsafe:'규칙 파일 경로가 안전하지 않습니다.',rule_unreadable:'규칙 파일을 읽을 수 없습니다.',rule_too_large:'규칙 파일이 크기 제한을 넘었습니다.',rule_unstable:'검사 중 규칙 파일이 변경되었습니다.',
    matches:'인용 일치',match:'인용 일치',ok:'일치',quote_match:'인용 일치',mismatch:'인용 불일치',quote_mismatch:'인용 불일치',changed:'변경됨',unavailable:'접근 불가',
    source_changed:'근거 문서가 변경되었습니다.',evidence_changed:'근거 문서가 변경되었습니다.',rule_changed:'규칙이 변경되었습니다.',rules_changed:'규칙이 변경되었습니다.',
    basis_changed:'승인 당시의 검토 기준과 현재 기준이 다릅니다.',stale_basis:'승인 당시의 검토 기준과 현재 기준이 다릅니다.',
    no_approval:'현재 기준의 승인이 없습니다.',rule_violation:'현재 규칙을 통과하지 못했습니다.',legacy_unbound:'버전에 연결되지 않은 기존 기록입니다.',
    conservative:'파일 일부만 바뀌어도 해당 파일에 연결된 주장은 다시 검토해야 합니다. 의미상의 영향 범위를 추론하지는 않습니다.',
    ruleScope:'SHACL 검사는 지원하는 로컬 속성 제약만 확인합니다. 통과한 주장이 사실임을 보증하지 않습니다.',
    observationScope:'검사한 시점의 버전만 추적합니다. 두 검사 사이에 파일을 수정했다가 되돌린 경우는 감지할 수 없습니다.',
    reviewerScope:'검토자 이름은 로컬 입력값입니다. 검토자의 신원을 인증하거나 기록 위변조를 방지하는 시스템은 아닙니다.',
    count:'건 표시',pageDependencies:'이 주장이 연결된 위키 페이지',source:'출처',review:'검토',affected:'영향받은 페이지 수'
  },
  en: {
    title:'Evidence review',
    records:'Execution records',recordHint:'Each button opens a saved inspection result.',snapshot:'Observed at',synthetic:'Synthetic demo',single:'Inspection snapshot',
    claims:'Registered claims',eligible:'Eligible for reuse',attention:'Needs attention',affectedPages:'Affected wiki pages',inspect:'Inspect claims and evidence',
    searchLabel:'Search claims',searchPlaceholder:'Search a title, value, or source path',filterLabel:'Current reuse eligibility',all:'All claims',blocked:'Reuse blocked',unreviewed:'Unreviewed',
    reviewState:'Review state',eligibility:'Current reuse eligibility',approved:'Approved',rejected:'Rejected',needs_review:'Needs review',
    evidence:'Source evidence',expected:'Quote recorded as evidence',actual:'Current lines in the file',lines:'Lines',subject:'Subject',predicate:'Property',value:'Claim value',
    rules:'Rule validation',ruleNote:'Passing a rule does not establish factual truth.',conforms:'Conforms',violates:'Violates',not_checked:'Not checked',focus:'Focus nodes checked',
    history:'Decision history',historyNote:'Earlier decisions remain in the record. Check the status above for current reuse eligibility.',noDecisions:'No recorded decisions.',
    noEvidence:'No linked evidence.',noRules:'No linked rules.',noPages:'No pages in this list.',empty:'No claims match these filters.',
    limitations:'Scope of this result',native:'This extension is a separate inspector. It does not block native LLM Wiki approvals or answers.',
    snapshotNote:'This is a saved inspection result. It does not monitor file changes in real time.',syntheticNote:'The demo documents, rules, and reviewers are synthetic examples.',
    footer:'Offline report. All data stays in this file.',metadata:'Versions and inspection details',revision:'Observed revision',digest:'File digest',availability:'File availability',basis:'Review basis',
    approve:'Approved',accept:'Approved',reject:'Rejected',actor:'Reviewer',decision:'Decision',unknown:'Unknown',present:'Present',available:'Available',missing:'Missing',unsafe:'Unsafe path',
    unreadable:'Unreadable',too_large:'Exceeds size limit',unstable:'Changed during inspection',span_missing:'Lines missing',invalid_encoding:'Unsupported encoding',
    no_review:'No decision is recorded.',review_rejected:'The reviewer rejected the claim.',evidence_unbound:'The claim has no bound evidence.',rules_unbound:'No rules are bound to the claim.',
    evidence_mismatch:'The recorded quote differs from the current file.',evidence_span_missing:'The quoted lines are missing from the current file.',evidence_invalid_encoding:'The evidence text encoding could not be read.',
    evidence_missing:'The evidence file is missing.',evidence_unsafe:'The evidence path is outside the allowed workspace or uses a link.',evidence_unreadable:'The evidence file could not be read.',evidence_too_large:'The evidence file exceeds the size limit.',evidence_unstable:'The evidence file changed during inspection.',
    rule_violates:'The claim does not conform to the current rule.',rule_not_checked:'The rule check could not be completed.',rule_missing:'The rule file is missing.',rule_unsafe:'The rule path is unsafe.',rule_unreadable:'The rule file could not be read.',rule_too_large:'The rule file exceeds the size limit.',rule_unstable:'The rule file changed during inspection.',
    matches:'Quote matches',match:'Quote matches',ok:'Matches',quote_match:'Quote matches',mismatch:'Quote mismatch',quote_mismatch:'Quote mismatch',changed:'Changed',unavailable:'Unavailable',
    source_changed:'The source document changed.',evidence_changed:'The source document changed.',rule_changed:'The rule changed.',rules_changed:'The rules changed.',
    basis_changed:'The current review basis differs from the approved basis.',stale_basis:'The current review basis differs from the approved basis.',
    no_approval:'No approval exists for the current basis.',rule_violation:'The claim does not conform to the current rule.',legacy_unbound:'This legacy record is not bound to a source revision.',
    conservative:'Any file change requires another review of all claims bound to that file. The inspector does not infer semantic impact.',
    ruleScope:'SHACL validation checks a supported set of local property constraints. Conformance does not establish factual truth.',
    observationScope:'Only observed revisions are tracked. Edits made and reverted between inspections cannot be detected.',
    reviewerScope:'Reviewer names are local assertions. This workspace does not authenticate reviewers or prevent record tampering.',
    count:'shown',pageDependencies:'Wiki pages linked to this claim',source:'Source',review:'Review',affected:'Affected pages'
  }
};
const limitationKeys = {
  'This is an offline sidecar. It does not enforce decisions in the upstream wiki or factlog engine.':'native',
  'Full-file changes require re-review. This is conservative dependency checking, not semantic impact analysis.':'conservative',
  'SHACL conformance checks a small local property-constraint profile. It does not prove a claim is true.':'ruleScope',
  'Only observed revisions are tracked. Edits made and reverted between inspections cannot be detected.':'observationScope',
  'Reviewer names are local assertions. The workspace is not an authenticated or tamper-proof audit system.':'reviewerScope',
  'This report is a captured snapshot. Reinspect the workspace before using an approval.':'snapshotNote'
};
let language = document.documentElement.lang, stageIndex = 0, selectedId = null;
const $ = id => document.getElementById(id);
const values = value => Array.isArray(value) ? value : [];
const display = value => value === null || value === undefined ? t('unknown') : typeof value === 'object' ? JSON.stringify(value,null,2) : String(value);
const t = key => Object.prototype.hasOwnProperty.call(dictionary[language],key) ? dictionary[language][key] : key;
function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = display(text);
  if (className) element.className = className;
  return element;
}
function tone(status) {
  if (['eligible','conforms','approved','approve','accept','matches','match','ok','quote_match','available','present'].includes(status)) return 'good';
  if (['violates','rejected','reject','unsafe','missing','unavailable','unreadable'].includes(status)) return 'bad';
  return 'warning';
}
function badge(status) { return node('span',t(status || 'unknown'),'badge '+tone(status)); }
function timestamp(value) {
  const time = node('time',display(value).replace(/\.\d+(?=Z$|\+00:00$)/,'').replace('T',' ').replace(/(?:Z|\+00:00)$/,' UTC'));
  if (typeof value === 'string') {time.dateTime=value;time.title=value;}
  return time;
}
function inspection() { return stages[stageIndex]?.inspection || {}; }
function section(parent, title) {
  const part = node('section',undefined,'section'); part.append(node('h3',t(title))); parent.append(part); return part;
}
function metadata(parent, item, fields) {
  const details = node('details',undefined,'details-meta'); details.append(node('summary',t('metadata')));
  const list = node('dl'); fields.forEach(key => {list.append(node('dt',t(key)),node('dd',key==='availability'?t(item[key]||'unknown'):item[key],'mono'));}); details.append(list); parent.append(details);
}
function pageList(parent, pages) {
  if (!values(pages).length) {parent.append(node('p',t('noPages'),'muted'));return;}
  const list = node('div',undefined,'page-list'); pages.forEach(page => list.append(node('span',page,'page-chip'))); parent.append(list);
}
function renderDetail(claim) {
  const panel = $('detail'); panel.replaceChildren();
  if (!claim) {panel.append(node('p',t('empty'),'empty'));return;}
  const head = node('div',undefined,'detail-head'); head.append(node('p',claim.id,'claim-id'),node('h2',claim.title || claim.id));
  const pair = node('div',undefined,'status-pair');
  [['reviewState',claim.review_state],['eligibility',claim.eligibility]].forEach(([label,status]) => {const item=node('div',undefined,'status-item');item.append(node('span',t(label)),badge(status));pair.append(item);});
  head.append(pair);
  if (values(claim.reason_codes).length) {const reasons=node('div',undefined,'reasons');claim.reason_codes.forEach(reason=>reasons.append(node('p',t(reason))));head.append(reasons);}
  panel.append(head); const body=node('div',undefined,'detail-body'); panel.append(body);
  const fact=node('div',undefined,'fact-row');
  [['subject',claim.subject],['predicate',claim.predicate],['value',claim.value]].forEach(([key,value])=>{const field=node('p',t(key));field.append(node('strong',value));fact.append(field);});body.append(fact);
  const evidence=section(body,'evidence');
  if (!values(claim.evidence).length) evidence.append(node('p',t('noEvidence'),'note'));
  values(claim.evidence).forEach(item=>{
    const card=node('div',undefined,'evidence-card'), top=node('div',undefined,'card-top');
    top.append(node('span',display(item.path)+'  '+t('lines')+' '+display(item.start_line)+'–'+display(item.end_line),'path'),badge(item.status));card.append(top);
    const quotes=node('div',undefined,'quote-grid'+(item.expected_text!==item.actual_text?' quote-mismatch':''));
    [['expected',item.expected_text],['actual',item.actual_text]].forEach(([label,text])=>{const quote=node('div',undefined,'quote');quote.append(node('p',t(label),'quote-label'),node('pre',text));quotes.append(quote);});card.append(quotes);
    metadata(card,item,['availability','revision','digest']); evidence.append(card);
  });
  const rules=section(body,'rules');rules.append(node('p',t('ruleNote'),'note'));
  if (!values(claim.rules).length) rules.append(node('p',t('noRules'),'muted'));
  values(claim.rules).forEach(item=>{
    const card=node('div',undefined,'rule-card'),top=node('div',undefined,'card-top');top.append(node('span',item.path,'path'),badge(item.status));card.append(top);
    const content=node('div',undefined,'rule-body');content.append(node('p',t('focus')+': '+display(item.focus_count),'muted'));values(item.messages).forEach(message=>content.append(node('p',message)));card.append(content);metadata(card,item,['availability','revision','digest']);rules.append(card);
  });
  const history=section(body,'history');history.append(node('p',t('historyNote'),'note'));const timeline=node('div',undefined,'timeline');timeline.style.marginTop='16px';history.append(timeline);
  if (!values(claim.decisions).length) timeline.append(node('p',t('noDecisions'),'muted'));
  values(claim.decisions).forEach(decision=>{
    const event=node('div',undefined,'event'),when=node('p',undefined,'event-time');when.append(timestamp(decision.recorded_at));event.append(node('p',t(decision.action)+' / '+display(decision.actor),'event-title'),when);
    const details=node('details');details.append(node('summary',t('basis')),node('pre',decision.basis));event.append(details);timeline.append(event);
  });
  pageList(section(body,'pageDependencies'),claim.wiki_pages);
  metadata(body,claim,['basis']);
}
function renderClaims() {
  const query=$('search').value.toLocaleLowerCase(),filter=$('filter').value;
  const all=values(inspection().claims),claims=all.filter(claim=>(filter==='all'||claim.eligibility===filter)&&[claim.id,claim.title,claim.subject,claim.predicate,claim.value,...values(claim.evidence).map(item=>item.path)].some(value=>display(value).toLocaleLowerCase().includes(query)));
  if (!claims.some(claim=>claim.id===selectedId)) selectedId=claims[0]?.id ?? null;
  $('claims').replaceChildren();$('result-count').textContent=claims.length+' / '+all.length+' '+t('count');
  if (!claims.length) $('claims').append(node('p',t('empty'),'empty'));
  claims.forEach(claim=>{const button=node('button',undefined,'claim-button');button.type='button';button.setAttribute('aria-pressed',String(claim.id===selectedId));button.dataset.claimId=claim.id;
    button.append(node('span',claim.id,'claim-id'),node('span',claim.title||claim.id,'claim-name'),badge(claim.eligibility),node('span',display(claim.predicate)+': '+display(claim.value),'claim-meta'));
    button.addEventListener('click',()=>{selectedId=claim.id;renderClaims();});$('claims').append(button);
  });renderDetail(claims.find(claim=>claim.id===selectedId));
}
function render() {
  document.documentElement.lang=language;document.title=t('title');
  document.querySelectorAll('[data-i18n]').forEach(element=>{element.textContent=t(element.dataset.i18n);});$('hero-title').textContent=t('title');
  ['ko','en'].forEach(code=>$('lang-'+code).setAttribute('aria-pressed',String(language===code)));
  const current=inspection(),observed=node('span',t('snapshot')+' ','observed');observed.append(timestamp(current.observed_at));$('hero-meta').replaceChildren(node('span',current.workspace_name||report.title||'Evidence review','workspace-name'),observed);
  if (report.demo) $('hero-meta').append(node('span',t('synthetic'),'meta-pill demo-pill'));
  $('stages').replaceChildren();stages.forEach((stage,index)=>{const button=node('button',undefined,'stage');button.type='button';button.dataset.stageId=stage.id;button.setAttribute('aria-pressed',String(index===stageIndex));
    button.append(node('span',String(index+1).padStart(2,'0'),'stage-number'),node('span',stage['label_'+language]||t('single'),'stage-title'));
    button.addEventListener('click',()=>{stageIndex=index;render();});$('stages').append(button);
  });$('stage-description').textContent=stages[stageIndex]?.['description_'+language]||t('snapshotNote');
  const claims=values(current.claims),eligible=claims.filter(claim=>claim.eligibility==='eligible').length;
  $('metrics').replaceChildren();[['claims',claims.length,''],['eligible',eligible,'good'],['attention',claims.length-eligible,'warning'],['affected',values(current.affected_pages).length,'']].forEach(([label,count,tone])=>{const item=node('div',undefined,'metric '+tone);item.append(node('strong',count),node('span',t(label)));$('metrics').append(item);});
  $('search').placeholder=t('searchPlaceholder');const filter=$('filter').value||'all';$('filter').replaceChildren();['all','eligible','blocked','unreviewed'].forEach(status=>{const option=node('option',t(status));option.value=status;$('filter').append(option);});$('filter').value=filter;
  $('claims').setAttribute('aria-label',t('claims'));$('affected-pages').replaceChildren();pageList($('affected-pages'),current.affected_pages);
  const limitations=[t('native'),t('snapshotNote'),...(report.demo?[t('syntheticNote')]:[]),...values(current.limitations).map(text=>t(Object.prototype.hasOwnProperty.call(limitationKeys,text)?limitationKeys[text]:text))];
  $('limitations').replaceChildren();[...new Set(limitations)].forEach(text=>$('limitations').append(node('p',text)));
  renderClaims();
}
['ko','en'].forEach(code=>$('lang-'+code).addEventListener('click',()=>{language=code;render();}));
$('search').addEventListener('input',renderClaims);$('filter').addEventListener('change',renderClaims);render();
</script>
</body>
</html>
'''
