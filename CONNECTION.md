# Connect the live editor

[한국어 사용 흐름](#한국어-사용-흐름) / English

The standalone Python service mounts a separately built Microsoft Ontology Playground fork. Both pages share the same loopback origin. LLM Wiki and NVIDIA inference services are not required.

Requirements: Python 3.11+, Git, npm, and Node.js 20.19+ within the 20.x line or Node.js 22.12+. This follows the pinned editor's Vite engine range, `^20.19.0 || >=22.12.0`; the recorded Windows build used Node 24. Build commands need network access. The running synthetic workflow needs no API key.

The commands below start inside your `ontology-review` checkout. Build the editor once. The pinned commit includes the connection panel; the upstream Microsoft demo does not include this fork's integration.

## Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install .

git clone https://github.com/SakJaeLim/Ontology-Playground.git ../ontology-playground
git -C ../ontology-playground checkout 40005215fc283e4abf1c5abae0ca0f9053a87cf8
Push-Location ../ontology-playground
npm ci --ignore-scripts
$env:VITE_BASE_PATH = '/editor/'
$env:VITE_EVIDENCE_REVIEW = 'true'
npm run build
Remove-Item Env:VITE_BASE_PATH
Remove-Item Env:VITE_EVIDENCE_REVIEW
Pop-Location

New-Item -ItemType Directory review-workspace
.venv\Scripts\python -m evidence_wiki serve review-workspace --editor-dist ../ontology-playground/build --port 8770
```

## macOS and Linux

```sh
python3 -m venv .venv
.venv/bin/python -m pip install .

git clone https://github.com/SakJaeLim/Ontology-Playground.git ../ontology-playground
git -C ../ontology-playground checkout 40005215fc283e4abf1c5abae0ca0f9053a87cf8
(
  cd ../ontology-playground
  npm ci --ignore-scripts
  VITE_BASE_PATH=/editor/ VITE_EVIDENCE_REVIEW=true npm run build
)

mkdir review-workspace
.venv/bin/python -m evidence_wiki serve review-workspace --editor-dist ../ontology-playground/build --port 8770
```

If the editor already exists, use another checkout directory and update the paths. Confirm that its build succeeded before starting the service. If 8770 is busy, choose another port, such as 8771, and open that port.

## Try the connected workflow

Open **http://127.0.0.1:8770/**.

1. Choose **합성 예제 불러오기**, or import a native Auto Ontology JSON/YAML file.
2. Open **2 편집기**, then explicitly choose **작업 공간 불러오기** in the Designer. This replaces the current editor draft.
3. Edit an entity or property description and choose **검토로 보내기**.
4. Open **검토 화면** in its separate tab. Compare original and proposal, enter a reviewer label and record a decision.
5. Edit again, return to the review tab and refresh. The current definition requires review; the earlier decision stays in history.
6. Choose **원본과 편집본 내보내기** to download the source and separate proposal.

Use an empty directory for a new workspace. Restart with the same directory to retain its history. Only one server process may write to a workspace; concurrent CLI writers are unsupported.

## Input and editing contract

The adapter follows NVIDIA's `AutoOntologyModelDocument` at commit `fb496d406acfd34db0af3c5d188080097779021f`. A term's `represents` values identify tables; column attributes use `column_id`; primary-key lists contain column names.

- Maximum dictionary size: 1 MiB. Maximum reviewable definitions: 200.
- JSON and safe YAML are accepted. Duplicate keys, aliases, explicit tags and non-finite values are rejected.
- Ontology name/description and bound entity/property descriptions can change.
- Structural changes, including renaming and reordering bound properties, are rejected. The adapter does not guess identity.
- Reimporting an identical source preserves the proposal. A changed source starts a new projection.
- Foreign keys, joins, SQL attributes, samples and zones remain in the original input. They are not converted into guessed relationships.
- Export is an envelope containing exact original text, its hash, the proposal and bindings. It is not a replacement NVIDIA model for automatic reimport.

## Review and local access

A decision is bound to the inspected basis. A new generation conservatively requires review again; even unrelated definitions can be affected. Earlier decisions remain in SQLite.

The source and proposal extracts are representations of the submitted data, not independent factual evidence. SHACL checks description shape and length, not truth. Reviewer names are local labels, not authenticated identities.

The service binds to `127.0.0.1`. Reads require its session cookie; writes also check the exact host, origin, CSRF token and workspace revision. It does not expose arbitrary local paths, SQL execution or remote fetches. This is a local single-user service, not an internet deployment.

## 한국어 사용 흐름

위에서 운영체제에 맞는 명령을 실행하세요. 이미 Python 가상환경과 편집기를 준비했다면, 같은 작업 폴더와 `build` 경로로 마지막 서버 명령만 다시 실행하면 됩니다.

작업 화면에서 합성 예제를 불러온 뒤 편집기로 이동합니다. **작업 공간 불러오기**로 연결된 초안을 열고, 개체 또는 속성 설명을 수정한 다음 **검토로 보내기**를 누릅니다. **검토 화면**은 별도 탭으로 열립니다. 원문과 제안문을 확인하고 검토자 이름을 적어 승인하거나 반려하세요.

저장만으로 승인되지는 않습니다. 승인한 내용을 다시 바꾸면 이전 기록을 남긴 채 재검토 대상으로 표시합니다. 다른 탭에서 먼저 저장했으면 오래된 화면의 저장은 거부되고 수정 내용은 화면에 남습니다. 새 내용을 불러오기 전에 필요한 초안은 별도로 보관하세요.

현재는 설명 편집을 지원합니다. 이름, 자료형, 순서, 관계와 구조 변경은 저장할 수 없습니다. 화면에 옮기지 않은 정보도 원본과 내보내기 파일에 보존됩니다. 검토자가 확인하는 것은 제출된 원문과 수정안이며, 업무적 의미의 타당성은 직접 판단해야 합니다.

## Verify the result

See [standalone verification](STANDALONE_VERIFICATION.md) for current platform checks and [the original connection record](CONNECTION_VERIFICATION.md) for the earlier browser and security checks.
