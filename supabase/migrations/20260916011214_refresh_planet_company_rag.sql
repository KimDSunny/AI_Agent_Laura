-- PLANET 회사 세계관과 2026-09-14 주간 계획을 반영한 RAG 문서 개편

update public.documents
set title = 'PLANET 회사 소개서.md', source_type = 'text', visibility_team = null
where title = '회사 소개서.pdf';

update public.documents
set visibility_team = null
where title = '2026 프로젝트 현황.md';

insert into public.documents (title, source_type, visibility_team)
select '2026-09-14 팀별 주간 계획.md', 'text', null
where not exists (
  select 1 from public.documents where title = '2026-09-14 팀별 주간 계획.md'
);

delete from public.document_sections
where document_id in (
  select id from public.documents
  where title in (
    'PLANET 회사 소개서.md',
    'PLANET 조직도와 담당 업무.md',
    '2026 프로젝트 현황.md',
    '2026-09-14 팀별 주간 계획.md'
  )
);

insert into public.document_sections (document_id, section_title, content, metadata)
select id, section_title, content, metadata
from public.documents
cross join lateral (
  values
    (
      '회사 개요와 사업',
      $$PLANET은 서울 성수에 본사를 둔 B2B SaaS 회사입니다. 신입사원이 입사 전 준비부터 첫 업무 수행까지 빠르게 적응하도록 돕는 Employee Experience OS를 만듭니다. 주요 고객은 임직원 50~500명 규모의 국내 성장 기업이며, 기업용 SaaS 구독료와 초기 도입 컨설팅 비용이 주요 수익원입니다. 대표는 윤지호이고 본사는 서울특별시 성동구 성수이로 88 PLANET 캠퍼스입니다.$$,
      '{"topic":"company"}'::jsonb
    ),
    (
      '미션·비전과 제품',
      $$PLANET의 미션은 누구나 입사 첫날부터 회사의 맥락을 이해하고 자신 있게 일하게 하는 것입니다. 비전은 사람과 조직의 적응 과정을 가장 신뢰받는 AI 업무 경험으로 바꾸는 것입니다. 제품군은 온보딩 AI Agent Laura, 온보딩 운영 허브 Orbit, 익명·집계 기반 People Analytics Compass로 구성됩니다.$$,
      '{"topic":"company"}'::jsonb
    ),
    (
      '연혁 · 2012–2026',
      $$2012년 협업 소프트웨어 스튜디오 PLANET을 설립했습니다. 2015년 첫 기업용 프로젝트 협업 서비스를 출시했고 2018년 엔터프라이즈 제품·개발 조직을 확대했습니다. 2021년 Employee Experience 플랫폼으로 전환했으며 2024년 AI Agent 사업부와 Laura 연구 개발을 시작했습니다. 2025년 디자인 파트너 5개사를 확보했고 2026년 Laura v1.0 고객사 파일럿과 Orbit 연동 프로젝트를 진행하고 있습니다.$$,
      '{"topic":"history"}'::jsonb
    )
) as sections(section_title, content, metadata)
where title = 'PLANET 회사 소개서.md';

insert into public.document_sections (document_id, section_title, content, metadata)
select id, section_title, content, metadata
from public.documents
cross join lateral (
  values
    ('조직 운영 체계', $$PLANET은 대표 윤지호 아래 기획팀, 개발팀, 디자인팀, 마케팅팀, 인사팀의 5개 기능 조직으로 운영합니다. 제품 의사결정은 기획·개발·디자인이 참여하는 주간 Product Council에서 진행하며 고객 출시와 정책 변경은 마케팅팀과 인사팀까지 검토합니다.$$,'{"topic":"organization"}'::jsonb),
    ('기획팀', $$기획팀 리드는 김서윤입니다. 제품 전략, 고객 요구사항, 로드맵, 지표 설계와 프로젝트 우선순위를 담당합니다. 현재 Laura v1.0 파일럿 범위와 성공 지표 확정, Orbit 요구사항 정리를 책임집니다.$$,'{"topic":"organization","team":"기획팀"}'::jsonb),
    ('개발팀', $$개발팀 리드는 박도현입니다. 프런트엔드, 백엔드, AI Agent, 데이터베이스, 인프라와 보안 운영을 담당합니다. 현재 Laura Agent의 RAG 정확도, Google Calendar Tool Calling과 서비스 안정성을 책임집니다.$$,'{"topic":"organization","team":"개발팀"}'::jsonb),
    ('디자인팀', $$디자인팀 리드는 이나경입니다. UX 리서치, 제품 UI, 디자인 시스템과 브랜드 경험을 담당합니다. 현재 Laura 승인 흐름과 온보딩 관리자 화면 사용성 개선을 책임집니다.$$,'{"topic":"organization","team":"디자인팀"}'::jsonb),
    ('마케팅팀', $$마케팅팀 리드는 최민준입니다. 시장 조사, 브랜드, 콘텐츠, 고객 커뮤니케이션과 출시 캠페인을 담당합니다. 현재 Laura 파일럿 고객 온보딩 자료와 10월 베타 캠페인을 준비합니다.$$,'{"topic":"organization","team":"마케팅팀"}'::jsonb),
    ('인사팀', $$인사팀 리드는 정유진입니다. 채용, 입사 절차, 조직문화, 평가·보상, 복지와 사내 정책을 담당합니다. 현재 PLANET 내부 온보딩 표준화와 Laura용 인사 문서 검수를 책임집니다.$$,'{"topic":"organization","team":"인사팀"}'::jsonb)
) as sections(section_title, content, metadata)
where title = 'PLANET 조직도와 담당 업무.md';

insert into public.document_sections (document_id, section_title, content, metadata)
select id, section_title, content, metadata
from public.documents
cross join lateral (
  values
    ('Laura Onboarding Agent v1.0', $$Laura는 신입사원의 회사 이해, 온보딩 진행과 일정 등록을 하나의 대화에서 처리하는 AI Agent 프로젝트입니다. 2026년 9월 현재 사내 QA와 디자인 파트너 5개사 파일럿을 준비하고 있습니다. 9월 25일까지 RAG 답변 정확도 평가와 Calendar 승인 흐름을 안정화하고 9월 28일 파일럿, 11월 2일 v1.0 정식 출시를 목표로 합니다. 성공 기준은 근거 있는 답변 비율 95% 이상과 반복 문의 30% 감소입니다. 개발팀 박도현과 기획팀 김서윤이 주관합니다.$$,'{"topic":"projects","project":"Laura"}'::jsonb),
    ('Orbit Workspace Admin', $$Orbit은 입사자의 계정 발급, 필수 문서, 교육, 체크리스트와 결재 상태를 한 화면에서 관리하는 프로젝트입니다. 현재 핵심 화면 프로토타입과 HRIS·SSO 연동 요구사항을 정의하고 있습니다. 10월 9일까지 관리자 프로토타입 사용성 테스트를 마치고 12월 디자인 파트너 대상 비공개 베타를 진행합니다. 목표는 입사 준비 업무 처리 시간을 40% 단축하는 것입니다. 기획팀 김서윤과 디자인팀 이나경이 주관합니다.$$,'{"topic":"projects","project":"Orbit"}'::jsonb),
    ('Compass People Analytics', $$Compass는 온보딩 이탈 구간과 반복 질문을 익명·집계 데이터로 분석하는 프로젝트입니다. 현재 문제 정의와 개인정보 영향 검토 단계입니다. 10월 16일까지 지표 사전과 데이터 최소 수집 원칙을 확정하고 12월 내부 분석 프로토타입을 검증합니다. 개인 평가에는 사용하지 않고 팀 단위 개선 인사이트만 제공하는 것이 원칙입니다. 기획팀 김서윤과 인사팀 정유진이 주관합니다.$$,'{"topic":"projects","project":"Compass"}'::jsonb)
) as sections(section_title, content, metadata)
where title = '2026 프로젝트 현황.md';

insert into public.document_sections (document_id, section_title, content, metadata)
select id, section_title, content, metadata
from public.documents
cross join lateral (
  values
    ('기획팀 · 2026-09-14~18', $$기획팀의 이번 주 목표는 Laura 파일럿 범위와 측정 기준 확정입니다. 고객 시나리오 20개의 우선순위를 정하고 RAG 정확도 평가표를 작성하며 Orbit 요구사항 인터뷰 3건을 진행합니다. 김서윤이 최종 범위를 승인하고 한지민이 인터뷰와 요구사항 문서를 담당합니다. 금요일 Product Council의 파일럿 범위와 성공 지표 승인이 완료 조건입니다.$$,'{"topic":"weekly_plan","team":"기획팀","week":"2026-09-14"}'::jsonb),
    ('개발팀 · 2026-09-14~18', $$개발팀의 이번 주 목표는 Laura RAG와 Calendar Tool Calling의 파일럿 안정성 확보입니다. 회사 문서 청크와 임베딩 갱신, 문서에 없는 질문 거절 테스트, 일정 승인 후 Google Calendar 등록 회귀 테스트와 오류 로그 정리를 진행합니다. 박도현이 릴리스를 책임지고 이준호가 RAG, 최아린이 Agent Tool을 담당합니다. 핵심 회귀 테스트 전부 통과, 치명적 오류 0건과 스테이징 배포 완료가 완료 조건입니다.$$,'{"topic":"weekly_plan","team":"개발팀","week":"2026-09-14"}'::jsonb),
    ('디자인팀 · 2026-09-14~18', $$디자인팀의 이번 주 목표는 Laura 대화와 승인 경험의 사용성 개선안 확정입니다. 일정 승인 카드 상태 설계, 팀 채팅과 AI 채팅 구분 검토, 관리자 화면 프로토타입 1차 제작을 진행합니다. 이나경이 디자인 리뷰를 진행하고 오세진이 프로토타입을 제작합니다. 목요일 사용성 테스트 5명 완료와 금요일 개발 전달 문서 게시가 완료 조건입니다.$$,'{"topic":"weekly_plan","team":"디자인팀","week":"2026-09-14"}'::jsonb),
    ('마케팅팀 · 2026-09-14~18', $$마케팅팀의 이번 주 목표는 Laura 고객 파일럿 커뮤니케이션 패키지 완성입니다. 제품 소개서, 파일럿 안내 메일, FAQ 15개와 10월 베타 캠페인 콘텐츠 캘린더를 작성합니다. 최민준이 메시지를 승인하고 강예원이 콘텐츠 제작을 담당합니다. 금요일까지 영업·기획 검토를 반영한 최종 패키지 배포가 완료 조건입니다.$$,'{"topic":"weekly_plan","team":"마케팅팀","week":"2026-09-14"}'::jsonb),
    ('인사팀 · 2026-09-14~18', $$인사팀의 이번 주 목표는 내부 온보딩 문서와 Laura 답변 근거의 정확성 검수입니다. 조직도·복지·휴가 문서 최신화, 신규 입사자 체크리스트 검토와 개인정보 취급 문구 법무 확인 요청을 진행합니다. 정유진이 정책을 승인하고 문채원이 문서 검수와 체크리스트 반영을 담당합니다. 목요일 핵심 사내 문서 승인과 금요일 신규 입사자용 체크리스트 게시가 완료 조건입니다.$$,'{"topic":"weekly_plan","team":"인사팀","week":"2026-09-14"}'::jsonb)
) as sections(section_title, content, metadata)
where title = '2026-09-14 팀별 주간 계획.md';
