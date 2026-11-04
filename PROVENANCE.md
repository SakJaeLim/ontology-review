# What was built here

Ontology Review is maintained by [Seokje Lim](https://github.com/SakJaeLim). It began as an independently executable Python extension inside an LLM Wiki fork. This repository continues that component as a standalone project.

## Contribution map

| Component | Origin and contribution |
| --- | --- |
| Review state engine | Developed in this project: observed source/rule revisions, exact basis binding, stale-review rejection, SQLite decisions and history. |
| Dictionary adapter | Developed in this project against NVIDIA's published data model: native JSON/YAML import, preserved source, bounded projection and export envelope. |
| Local service and workbench | Developed in this project: shared-origin editor mounting, guarded writes, original/proposal comparison and review controls. |
| Inspection report | Developed in this project using the credited Open Props tokens and Lucide icons. |
| Visual ontology editor | Microsoft Ontology Playground. The author's fork adds a connection client, panel, bound-draft handling and related regression tests. The editor is built separately. |
| LLM Wiki desktop app | nashsu/llm_wiki. It is neither included in this repository nor required at runtime. Its native answer and approval paths are unchanged. |
| NVIDIA inference service | NVIDIA/auto-ontology. The service is not deployed here; this project consumes its dictionary format. |
| factlog and OntoRipple | Research references. A bounded factlog CSV importer exists. OntoRipple is not a runtime dependency. |

## Preserved development history

The source is [SakJaeLim/llm_wiki at a352744](https://github.com/SakJaeLim/llm_wiki/tree/a3527442f440d1521e111a9c7f0328fa66efe248/extensions/evidence-review).

Git subtree split moved only `extensions/evidence-review` to the repository root. The three component commits retain their authors and messages. Their hashes change because their trees and parents change.

| Original feature merge | Extracted commit |
| --- | --- |
| [bd0e2eb](https://github.com/SakJaeLim/llm_wiki/commit/bd0e2eb12e65f84b61892315d73ccd0c059df333) | `0a626ce` |
| [cb19a58](https://github.com/SakJaeLim/llm_wiki/commit/cb19a58801adf61332c9bcd4b4a418e50c61d595) | `cd59264` |
| [a352744](https://github.com/SakJaeLim/llm_wiki/commit/a3527442f440d1521e111a9c7f0328fa66efe248) | `e43d5b4` |

The extraction itself preserves the component tree. Subsequent commits make the documentation, packaging, workflow and visible branding independent. Existing fork snapshots remain available; this repository becomes the maintained home for the component.

## Pinned integrations

- Microsoft editor fork: [40005215fc283e4abf1c5abae0ca0f9053a87cf8](https://github.com/SakJaeLim/Ontology-Playground/commit/40005215fc283e4abf1c5abae0ca0f9053a87cf8).
- NVIDIA model schema: [fb496d406acfd34db0af3c5d188080097779021f](https://github.com/NVIDIA/auto-ontology/tree/fb496d406acfd34db0af3c5d188080097779021f).
- Open Props and Lucide: versions, selected files and license texts in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

This is an independently maintained integration and review tool. No affiliation, endorsement or accepted upstream PR is implied.

## 한국어

직접 개발한 것은 검토 엔진과 데이터 사전 어댑터, 로컬 서버, 검사 화면, 편집기 연결 코드입니다. Microsoft 시각 편집기와 LLM Wiki 데스크톱 앱, NVIDIA 추론 엔진 전체를 개발했다는 의미가 아닙니다.

기존 확장 폴더의 커밋 3개를 분리해 이력을 유지했습니다. 원본 라이선스와 외부 자원 고지도 남겨 두었습니다. 독립 저장소는 이 도구의 역할과 기여를 쉽게 찾도록 하기 위한 것이며, 원본 프로젝트의 기여 승인과는 별개입니다.
