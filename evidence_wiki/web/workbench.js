'use strict';
let state = null;
let csrf = '';
let selected = null;
let busy = false;
const $ = id => document.getElementById(id);
const statuses = {eligible: '재사용 가능', blocked: '재사용 보류', unreviewed: '미검토', approved: '승인', needs_review: '재검토 필요', rejected: '반려'};
function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
}
function message(text, error = false) { $('message').textContent = text; $('message').className = error ? 'error' : ''; }
async function request(path, data) {
  const response = await fetch(path, {credentials: 'same-origin', redirect: 'error', cache: 'no-store', headers: data ? {'Content-Type': 'application/json', 'X-CSRF-Token': csrf} : {}, ...(data ? {method: 'POST', body: JSON.stringify(data)} : {})});
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.message || '요청을 완료하지 못했습니다.');
  return payload;
}
async function perform(action) {
  if (busy) return;
  busy = true;
  document.querySelectorAll('button').forEach(button => button.disabled = true);
  try { await action(); } catch (error) { message(error.message, true); }
  finally { busy = false; document.querySelectorAll('button').forEach(button => button.disabled = false); render(); }
}
function render() {
  if (!state) return;
  const claims = state.inspection?.claims || [];
  $('source-info').hidden = !state.source;
  $('source-info').replaceChildren();
  if (state.source) $('source-info').append(node('strong', state.source.filename), node('code', 'SHA-256 ' + state.source.sha256));
  $('counts').textContent = claims.length ? claims.filter(claim => claim.eligibility === 'eligible').length + ' / ' + claims.length + ' 재사용 가능' : '';
  $('report').hidden = !state.inspection;
  $('export').disabled = busy || !state.ontology;
  $('notices').replaceChildren(...state.notices.map(text => node('li', text)));
  const query = $('search').value.toLocaleLowerCase();
  const shown = claims.filter(claim => [claim.title, claim.value].some(value => String(value).toLocaleLowerCase().includes(query)));
  if (!shown.some(claim => claim.id === selected)) selected = shown[0]?.id || null;
  $('claims').replaceChildren();
  for (const claim of shown) {
    const button = node('button', undefined, 'claim');
    button.type = 'button';
    button.setAttribute('aria-pressed', String(claim.id === selected));
    button.append(node('strong', claim.title), node('span', statuses[claim.eligibility], 'badge ' + claim.eligibility));
    button.addEventListener('click', () => { selected = claim.id; render(); });
    $('claims').append(button);
  }
  renderDetail(shown.find(claim => claim.id === selected));
}
function renderDetail(claim) {
  $('detail').replaceChildren();
  if (!claim) { $('detail').append(node('p', state.ontology ? '조건에 맞는 정의가 없습니다.' : '데이터 사전을 가져오면 검토할 정의가 표시됩니다.', 'muted')); return; }
  const heading = node('div', undefined, 'detail-heading');
  heading.append(node('h3', claim.title), node('span', statuses[claim.review_state], 'badge ' + claim.eligibility));
  $('detail').append(heading, node('p', claim.value || '(설명 없음)', 'definition'));
  const evidence = node('div', undefined, 'evidence');
  for (const [index, item] of claim.evidence.entries()) {
    const side = node('div');
    side.append(node('h3', index === 0 ? '데이터 사전 원문' : '편집기에서 보낸 설명'), node('pre', item.actual_text ?? '근거를 읽지 못했습니다.'));
    const details = node('details'); details.append(node('summary', '근거 위치'), node('pre', item.path + '\n줄 ' + item.start_line + '\nSHA-256 ' + item.digest)); side.append(details); evidence.append(side);
  }
  $('detail').append(evidence);
  const passed = claim.rules.every(rule => rule.status === 'conforms') && claim.evidence.every(item => item.status === 'matches');
  $('detail').append(node('p', passed ? '근거 일치와 설명 형식 검사를 통과했습니다.' : '근거 또는 설명 형식 검사를 통과하지 못했습니다.', 'checks'));
  if (claim.reason_codes.includes('basis_changed')) $('detail').append(node('p', '이전 승인 이후 원본 또는 편집본이 바뀌었습니다. 현재 내용을 다시 검토하세요.', 'checks'));
  const actions = node('div', undefined, 'actions');
  for (const [action, label] of [['accept', '현재 정의 승인'], ['reject', '반려']]) {
    const button = node('button', label, action === 'accept' ? 'primary' : 'quiet');
    button.disabled = busy || (action === 'accept' && !passed);
    button.addEventListener('click', () => perform(async () => {
      const actor = $('actor').value.trim();
      if (!actor) throw new Error('검토 기록에 남길 이름을 입력하세요.');
      state = await request('/api/review', {expectedRevision: state.revision, claimId: claim.id, basis: claim.basis, action, actor});
      message(action === 'accept' ? '현재 근거에 대한 승인을 기록했습니다.' : '반려를 기록했습니다.');
    })); actions.append(button);
  }
  $('detail').append(actions);
  const history = node('section', undefined, 'history'); history.append(node('h3', '검토 이력'));
  if (!claim.decisions.length) history.append(node('p', '아직 검토 기록이 없습니다.', 'muted'));
  else {
    const list = node('ol');
    for (const decision of claim.decisions) {
      const event = node('li', (decision.action === 'accept' ? '승인' : '반려') + ' / ' + decision.actor + ' / ' + decision.recorded_at.replace('T', ' ').replace(/\.\d+\+00:00$/, ' UTC'));
      const details = node('details'); details.append(node('summary', '당시 검토 기준'), node('pre', decision.basis)); event.append(details); list.append(event);
    }
    history.append(list);
  }
  $('detail').append(history);
}
$('search').addEventListener('input', render);
$('refresh').addEventListener('click', () => perform(async () => { state = await request('/api/state'); message('현재 원본과 검토 상태를 다시 확인했습니다.'); }));
$('upload').addEventListener('click', () => perform(async () => {
  const file = $('dictionary-file').files[0];
  if (!file) throw new Error('가져올 JSON 또는 YAML 파일을 선택하세요.');
  if (file.size > 1048576) throw new Error('파일은 1 MiB 이하로 선택하세요.');
  const content = new TextDecoder('utf-8', {fatal: true, ignoreBOM: true}).decode(await file.arrayBuffer());
  state = await request('/api/import', {expectedRevision: state.revision, filename: file.name, content});
  message('원본을 보존하고 검토할 정의를 불러왔습니다. 편집기에서 설명을 다듬을 수 있습니다.');
}));
$('example').addEventListener('click', () => perform(async () => {
  const example = await request('/api/example');
  state = await request('/api/import', {expectedRevision: state.revision, ...example});
  message('가상의 데이터 사전을 불러왔습니다. 실제 기관 자료는 포함하지 않습니다.');
}));
$('export').addEventListener('click', () => perform(async () => {
  const envelope = await request('/api/export');
  const url = URL.createObjectURL(new Blob([JSON.stringify(envelope, null, 2)], {type: 'application/json'}));
  const link = node('a'); link.href = url; link.download = 'ontology-review-export.json'; document.body.append(link); link.click(); link.remove(); URL.revokeObjectURL(url);
  message('원본과 편집본, 연결 정보를 내보냈습니다.');
}));
perform(async () => {
  const session = await request('/api/session');
  if (!session.connected || session.protocol !== 'evidence-connection-v1') throw new Error('지원하는 로컬 연결을 찾지 못했습니다.');
  csrf = session.csrfToken;
  state = await request('/api/state');
});
