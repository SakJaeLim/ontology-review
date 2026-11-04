# 온톨로지 확장 후보 검토

2026년 11월 3일 확인. 별 수는 같은 날 GitHub API에서 수집한 시점의 값이며 계속 변한다. 전체 29개 저장소의 메타데이터를 비교하고, 아래 핵심 후보는 공식 README와 지정한 소스까지 살펴봤다. 모든 제품을 설치해 비교한 벤치마크는 아니다.

지금 프로젝트에는 **근거를 추적하는 검토 도구를 중심에 두고, 편집기와 검색 엔진을 각각 연결하는 방식**이 적합하다. NVIDIA와 Microsoft 프로젝트는 가져올 부분이 분명하지만, 서로 다른 데이터 모델을 같은 온톨로지 엔진으로 취급하면 원문이나 승인 의미가 손실될 수 있다.

## 우선 검토할 후보

| 프로젝트 | 별 | 활용할 부분 | 이번 판단 |
| --- | ---: | --- | --- |
| [Microsoft Ontology Playground](https://github.com/microsoft/Ontology-Playground) | 2,998 | 개체와 관계 편집, 산업별 예제, 원본 RDF 보존 | 편집 화면 후보 1순위. 사용자 계정에 포크 완료 |
| [NVIDIA Auto Ontology](https://github.com/NVIDIA/auto-ontology) | 1,127 | 업무 용어와 DB 컬럼 연결, 데이터 사전, SQL 의미 계층 | 공공 데이터 사전 연계 후보 1순위. 읽기 전용 교환 형식부터 연결 |
| [Microsoft OG-RAG](https://github.com/microsoft/ograg2) | 155 | 온톨로지의 관련 사실을 묶는 검색 | 기존 포크를 활용할 연구 비교군. 운영 서비스 도입과 구분 |
| [Microsoft GraphRAG](https://github.com/microsoft/graphrag) | 36,537 | 문서 집합의 관계와 공동체 요약 검색 | 넓은 범위의 질문 비교군. 재색인 비용과 근거 정확도를 함께 측정 |
| [LightRAG](https://github.com/HKUDS/LightRAG) | 40,497 | 그래프와 벡터 검색, 증분 삽입과 삭제 | 첫 검색 실험 후보. 작은 문서 집합에서 기존 검색과 비교 |
| [Graphiti](https://github.com/getzep/graphiti) | 32,464 | 시간에 따른 관계와 에피소드 출처 | 실제 유효 시점과 관측 시점을 나누는 설계 참고 |
| [Open Ontologies](https://github.com/fabio-rovai/open-ontologies) | 2,785 | 변경 계획, 추론 결과의 증명서와 별도 검사기 | 다음 심층 검증 후보. 공식 성능과 증명 범위 주장은 아직 재현하지 않음 |
| [OntoRipple](https://github.com/oeg-upm/OntoRipple) | 12 | 온톨로지 변경 영향 분석 | 기존 포크 유지. 우리 도구의 보수적인 파일 단위 영향 판단과 비교 |
| [Graphify](https://github.com/Graphify-Labs/graphify) | 141,413 | 코드와 문서를 관계 지도로 탐색 | 저장소 이해와 개발 문서 지도에 유용. 표준 온톨로지 검증기의 대체재로 보지 않음 |

별 수는 사용자층을 가늠할 때 참고했다. 현재의 SHACL 검사에는 별 367개의 [pySHACL](https://github.com/RDFLib/pySHACL)이 이미 직접적인 역할을 한다. 별 순서대로 제품을 결합할 이유는 없다.

## Microsoft에서 가져올 것

Ontology Playground는 React 기반의 정적 편집기다. Cytoscape로 관계를 표시하며, RDF 원본과 화면에 보이는 그래프를 따로 관리한다. 지원하지 않는 RDF 내용을 화면에서 생략하더라도 원본을 보존하려는 구조가 이 프로젝트와 잘 맞는다. [공식 설명](https://github.com/microsoft/Ontology-Playground/blob/7bf7acb427424ce68f917fa26f484fb06ca42051/README.md), [RDF 교환 범위](https://github.com/microsoft/Ontology-Playground/blob/7bf7acb427424ce68f917fa26f484fb06ca42051/docs/rdf-export-profiles.md).

다만 현재 편집기는 RDF/XML을 다루며 Turtle을 직접 지원하지 않는다. 포함된 SHACL 문장은 보존하지만 실행하지 않는다. 따라서 우리 `.ttl` 규칙을 그대로 넣어 검사까지 맡기는 방식은 맞지 않는다. 원본 보관, 편집용 그래프 변환, SHACL 검사 결과를 분리해야 한다.

실제 `ontologyValidation.ts`를 Node 24.22.1에서 실행했다. 다음 네 경우를 확인했다.

- 영문 개체명과 문자열 식별자가 있는 정상 입력은 통과했다.
- `공공데이터`라는 개체명은 Fabric IQ 이름 제한 때문에 거부됐다.
- 존재하지 않는 개체를 가리키는 관계를 거부했다.
- 생성 결과의 중복 속성명을 거부했다.

이름 검사는 ASCII 문자와 숫자, 하이픈, 밑줄 및 길이 조건을 사용한다. 한국어 사용을 위해서는 표시명과 안정적인 식별자를 따로 유지하는 연결 모델이 필요하다. 이 실행은 검증 함수 네 사례만 확인한 것이며, 앱 전체와 RDF 왕복 변환을 검증한 것은 아니다. [실행한 소스](https://github.com/microsoft/Ontology-Playground/blob/7bf7acb427424ce68f917fa26f484fb06ca42051/src/lib/ontologyValidation.ts).

포크: [SakJaeLim/Ontology-Playground](https://github.com/SakJaeLim/Ontology-Playground). 현재는 원본을 포크한 상태이며 사용자 기능을 추가한 완성품으로 소개하지 않는다.

## NVIDIA에서 가져올 것

Auto Ontology의 교환 모델은 물리 데이터 계층과 업무 의미 계층을 나눈다. 데이터베이스, 스키마, 테이블, 컬럼을 담고, 업무 용어가 어떤 컬럼을 나타내는지 연결한다. 공공기관의 데이터 정의서와 업무 용어를 묶는 어댑터를 만들 때 활용도가 높다. [교환 모델 소스](https://github.com/NVIDIA/auto-ontology/blob/fb496d406acfd34db0af3c5d188080097779021f/auto_ontology/server/model_interchange/schemas.py).

원본 Pydantic 모델을 직접 실행해 네 가지를 확인했다. 숫자 `1`과 문자열 `"1"`이 JSON 왕복 후 구별되고, 한글 용어가 유지된다. `include_ontology` 옵션은 OSSIE 형식에서는 허용되고 Auto Ontology 형식에서는 거부된다. YAML 가져오기, 서버, SQL 실행, 모델 추론은 실행하지 않았다.

첫 연결은 전체 서버를 붙이기보다 내보낸 교환 문서를 읽는 어댑터로 잡는 편이 낫다. 용어와 컬럼을 원본 식별자로 추적하고, 우리 검토 도구의 승인 기록은 따로 유지한다. 원본 스키마의 `sql_column_is`처럼 실제 필드명을 계약으로 확인해야 하며, 의미를 추측해 이름을 바꾸지 않는다.

현재 공식 README에는 외부 기여를 받지 않는다고 명시돼 있다. 따라서 당장은 사용자 포크에서 연결 코드를 개발하고, 원본 프로젝트에 PR을 받아줄 것처럼 계획하지 않는다. 전체 실행은 PostgreSQL과 모델 서비스 설정이 필요한 별도 단계다. [공식 README](https://github.com/NVIDIA/auto-ontology/blob/fb496d406acfd34db0af3c5d188080097779021f/README.md).

평가 저장소의 현재 이름은 [NVIDIA/auto-ontology-eval](https://github.com/NVIDIA/auto-ontology-eval)이다. `ontology-sql-eval` 주소는 이 이름으로 연결됐다. 별 22개이며 SQL 평가 체계를 참고할 후보로 분류했다. 이번에는 메타데이터만 확인했다.

## 다른 인기 프로젝트의 위치

[Semantica](https://github.com/semantica-agi/semantica)는 14,406개, [Cognee](https://github.com/topoteretes/cognee)는 33,019개, [Utopia](https://github.com/deeplethe/utopia)는 8,664개의 별을 받았다. 온톨로지나 기억 그래프를 넓게 다루지만 현재의 작은 오프라인 검사기에 모두 넣으면 설치와 상태 관리가 커진다. 별도 비교 실험 대상으로 남겼다. Semantica는 이전 조사에서 살핀 후보이고, 이번에는 메타데이터와 README 일부를 다시 확인했다.

Cognee의 저장소 라이선스와 운영용 부가 제품의 조건은 구분해야 한다. README가 설명하는 모든 배포 기능을 같은 Apache 라이선스로 쓸 수 있다고 가정하지 않았다. Utopia의 성능 수치와 Open Ontologies의 증명 관련 수치는 원저자의 주장으로 남겼으며, 우리 검증 결과에 포함하지 않았다.

Graphify는 특히 별이 많지만 코드 분석과 자료 탐색에 강점이 있다. README는 코드 전용 분석과 문서 등 혼합 입력의 모델 사용 조건을 구분한다. 우리 프로젝트에서는 소스와 문서의 탐색 지도를 만드는 보조 도구로 먼저 검토할 수 있다. 온톨로지의 제약 검사나 승인 변경 추적을 대신한다고 볼 근거는 확보하지 못했다.

[Protégé](https://github.com/protegeproject/protege), [Apache Jena](https://github.com/apache/jena), [RDFLib](https://github.com/RDFLib/rdflib)는 표준 생태계의 후보로 함께 목록에 남겼다. Protégé의 API 라이선스 값은 `NOASSERTION`이므로 실제 배포물을 재사용하기 전에 파일별 조건을 다시 확인해야 한다.

## 실제 적용한 디자인

현재 결과물은 하나의 HTML로 열리는 오프라인 보고서다. 그래서 전체 React 앱으로 바꾸지 않고, 작은 디자인 자원만 포함했다.

| 선택지 | 장점 | 이번 결정 |
| --- | --- | --- |
| shadcn/ui와 Radix 기반 화면 | 구성요소와 접근성 생태계가 풍부함 | 네이티브 앱 통합 단계에서 검토. 보고서 하나를 위해 빌드 체계를 늘리지 않음 |
| Open Props와 Lucide 일부 포함 | 작은 파일로 일관된 간격, 색상, 아이콘 사용 가능 | 적용 |
| Tabler 전체 템플릿 | 업무 화면을 빠르게 구성 가능 | 현재 두 주장 검토 화면에는 구성요소가 과다함 |
| React Flow, G6, Cytoscape | 관계 탐색과 그래프 편집에 유용함 | 실제 관계 탐색 기능을 만들 때 비교. 장식용 그래프는 추가하지 않음 |

[Open Props](https://github.com/argyleink/open-props)의 회색 계열과 간격 토큰, [Lucide](https://github.com/lucide-icons/lucide)의 문서와 검색 SVG를 고정 커밋에서 가져왔다. 큰 홍보 영역과 세리프 숫자를 줄이고, 원문 인용 비교와 검토 상태에 공간을 배정했다. 파란색은 선택 위치에, 초록과 황색은 상태 구분에 쓴다. 해시 등 긴 기술 정보는 펼쳐볼 수 있게 두었다.

외부 폰트와 CDN 요청 없이 작동한다. MIT, ISC 및 Lucide에 포함된 Feather MIT 고지를 저장소와 내보낸 HTML 모두에 넣었다. 디자인 라이브러리의 제작자나 Microsoft, NVIDIA가 이 프로젝트를 후원하거나 검증했다고 표현하지 않는다.

## 다음 개발 순서

1. NVIDIA 교환 문서와 Microsoft 편집기 JSON을 읽는 어댑터 계약을 먼저 만든다. 원본 바이트, 식별자, 가져온 시점과 변환 손실을 기록하고, 승인 상태는 자동으로 가져오지 않는다.
2. 편집기의 변경을 초안으로 받는다. 한국어 표시명, 관계 삭제, 알 수 없는 RDF 문장, 원본 보존을 작은 합성 예제로 확인한다. SHACL 검사와 사용자 검토를 통과한 결과만 새 검토 상태로 기록한다.
3. 같은 문서 집합과 질문으로 일반 검색, OG-RAG, LightRAG를 비교한다. 근거 인용의 정확성, 변경 후 오래된 답변 비율, 실행 시간과 비용을 측정한다. GraphRAG는 여러 문서를 묶는 질문에 대한 추가 비교군이다.
4. Open Ontologies와 OntoRipple을 각각 독립 실행해 변경 영향 결과를 비교한다. 승인 이력과 추론 증명서를 서로 대체하지 않는다.

이번에 끝낸 것은 저장소 조사, 핵심 검증 모듈의 제한된 실행, Microsoft 편집기 포크, 검토 화면 개선이다. NVIDIA나 Microsoft 엔진 전체가 현재 LLM Wiki에 통합된 상태는 아니다.

## 재현 자료

- `ontology-ecosystem-repositories.csv`: 29개 저장소의 조회 시점, 별, 라이선스 API 값, 검토 깊이와 결정.
- `ontology-ecosystem-evidence.json`: 고정 커밋, 가져온 파일의 SHA-256, 모듈 실행 결과. 토큰과 비공개 자료 없음.
- 화면과 테스트의 최종 결과는 저장소 `extensions/evidence-review/VERIFICATION.md`에 별도로 기록한다.

pstack에서 적용한 판단 기준은 **전제를 먼저 점검하기**, **변경의 영향을 명시적으로 모델링하기**, **실행한 증거로 확인하기**, **검증 가능한 단위로 나누기**다. 조사와 화면 구현은 파일 소유권을 나눴고, 원문 검증과 승인 로직은 이번 디자인 작업에서 변경하지 않았다.
