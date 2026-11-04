# Diagram generation prompts

These explanatory images were generated with the built-in image generation tool on 2026-11-04. They are illustrations of the documented workflow and architecture, not browser screenshots or customer-deployment evidence. Both contain Korean labels and English subtitles. The existing captured screens and videos remain unchanged.

## Review flow

Output: `assets/review-flow.png`

```text
Create one finished, readable editorial infographic for the GitHub README of a small software project called Ontology Review. Landscape 1600x1000 or a similar wide proportion. This is an explanatory diagram, NOT a screenshot or a claim of a real customer deployment. Elegant flat vector-like visual design, warm off-white background, dark navy typography, teal for reviewed content, amber for changed content, blue for a new review. Large clear Korean typography with short English subtitles. Restrained rounded rectangles, thin arrows, plenty of white space. No gradients, robots, brains, decorative graphs, 3D objects, company logos, watermark, or fake app chrome.

Title exactly: "바뀐 설명은 다시 검토합니다"
Subtitle exactly: "Changed wording needs a new review"

Three equally sized cards from left to right, joined by simple arrows.
Card 1 header: "01  기존 검토" with English subtitle "Reviewed"
Card 1 body: "활성 고객" then "최근 90일 내 구매" and a green status "승인"
Card 2 header: "02  설명 수정" with English subtitle "Edited"
Card 2 body: "활성 고객" then "최근 30일 내 구매" with the number 30 emphasized and an amber status "재검토 필요"
Card 3 header: "03  새 검토" with English subtitle "Review again"
Card 3 body: "원문과 수정안 비교" then "사람이 승인 또는 반려" and a blue status "새 결정 기록"

Below the three cards, use a simple horizontal history strip with a small archive icon and exact text:
"이전 승인은 이력에 남습니다"
"Earlier decisions stay in history."

Footer in readable small type:
"30일과 90일 중 무엇이 맞는지는 사람이 판단합니다."
"A person decides which definition is right."
In the bottom-left margin add "설명용 가상 사례 / Illustrative example".
Do not imply that the tool counts customers or changes a live database. All text must be legible, correctly spelled and fully inside its card.
```

## System architecture

Output: `assets/system-architecture.png`

```text
Create one finished software architecture infographic for the GitHub README of Ontology Review. Landscape 1600x1100 or similar wide proportion. This diagram explains actual implemented roles, NOT a screenshot. Premium editorial technical diagram, flat vector-like, warm off-white background, dark navy type, restrained teal outlines for this project's contribution, light gray for reused external components, thin clear connectors, generous white space. Large readable Korean labels with short English subtitles. No gradients, robots, decorative network clouds, 3D, company logos or watermark.

Title exactly: "무엇을 연결했고, 무엇을 만들었나"
Subtitle exactly: "Ontology Review — components and contributions"

Put all components inside one thin outer boundary labelled "개인 PC에서 실행 / Runs on one local PC".
Inside that boundary make a left-to-right system diagram:

LEFT input card, pale gray:
"NVIDIA 형식의 데이터 사전"
"Dictionary file"
"JSON / YAML"
A single right-pointing arrow to the middle, labelled "가져오기 / Import". It is a local input file, NOT a NVIDIA server.

MIDDLE largest outlined teal container:
"Ontology Review"
"직접 개발한 부분 / Built in this project"
Inside it, three clear stacked rows:
"원본 보관과 수정안 비교"
"Keep source and compare draft"
"검토 기록과 재검토 상태"
"Decisions and re-review status"
"로컬 서버와 검토 화면"
"Local server and review UI"
These rows are components of the same service; do not add arrows suggesting autonomous AI decisions.

RIGHT pale gray editor card:
"Microsoft 편집기"
"Microsoft Ontology Playground"
"기존 설명 편집 / Edit descriptions"
Connect the middle and right with TWO separate clear directional arrows:
middle to right labelled "초안 불러오기 / Load draft"
right to middle labelled "수정안 보내기 / Submit draft"
Do not connect NVIDIA directly to Microsoft.

BOTTOM inside the local PC boundary, connected downward from the middle service, place three small output/storage cards:
"원본과 수정안" / "Local files"
"검토 이력" / "SQLite"
"검사 보고서" / "HTML"
Keep all labels within cards; connectors must not cross any text.

Below the system boundary one short note:
"승인과 반려는 사람이 결정합니다."
"Review decisions are made by a person."
Bottom attribution summary:
"Microsoft: 편집기   NVIDIA: 파일 형식   이 프로젝트: 연결과 검토"
This diagram must NOT show a deployed NVIDIA inference engine, cloud service, LLM, enterprise authentication, automatic DB query, Foundry connector, or autonomous approval.
```

