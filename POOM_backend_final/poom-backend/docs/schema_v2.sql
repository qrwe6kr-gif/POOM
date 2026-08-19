-- =====================================================================
-- POOM DB 스키마 v2 (팀 초안 수정판)
-- 팀 초안의 테이블·컬럼 네이밍(projects, worker_id, sent_at 등)을 유지하되,
-- 원장 무결성·다이제스트 구조·시간대 처리의 결함을 수정하였다.
-- 변경 사유는 각 위치에 주석으로 명시한다.
-- =====================================================================

-- 1. 사용자
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    timezone VARCHAR(50) NOT NULL DEFAULT 'Asia/Seoul',
    preferred_language VARCHAR(10) NOT NULL DEFAULT 'ko',

    -- [추가] Timezone Status 엔진의 데이터 원천.
    -- timezone만으로는 '근무 중/수면 중/근무 시작 예정' 판정이 불가능하다.
    work_start  SMALLINT NOT NULL DEFAULT 9,
    work_end    SMALLINT NOT NULL DEFAULT 18,
    sleep_start SMALLINT NOT NULL DEFAULT 23,
    sleep_end   SMALLINT NOT NULL DEFAULT 7,

    -- [수정] simulated_last_active_at → 용도 분리.
    -- last_active_at: 실제 접속 기록(프레즌스). demo_now: 데모 모드의 '가상 현재 시각'.
    -- 상태 판정·무응답 경과·다이제스트 트리거가 전부 '현재 시각' 기반이므로,
    -- 시각 하나를 옮기면 전 시스템이 일관되게 시간 이동한다 (검증된 방식).
    last_active_at TIMESTAMPTZ,
    demo_now       TIMESTAMPTZ,

    -- [제거] credit_balance INT DEFAULT 100
    -- 잔액 컬럼과 거래 테이블이 공존하면 진실이 둘이 되어 반드시 어긋난다.
    -- 잔액은 아래 user_balances 뷰(거래 합산)로만 읽는다. 초기 100c는
    -- 가입 시 SIGNUP_BONUS 거래 1행을 넣는 것으로 지급한다.
    created_at TIMESTAMPTZ DEFAULT now()
);

-- [분리] primary_skill/needed_skill 단일 컬럼 → 테이블.
-- 확정 기획이 "주특기 1개 이상"이므로 단일 컬럼은 요구사항 위반이다.
-- MVP에서 1인 1스킬만 쓸 경우 각 테이블에 1행만 넣으면 된다.
CREATE TABLE user_skills (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id),
    skill VARCHAR(100) NOT NULL,               -- e.g., 'Backend', 'UI/UX Design'
    level VARCHAR(20) NOT NULL DEFAULT 'junior',
    portfolio_url VARCHAR(300) NOT NULL DEFAULT ''
);
CREATE INDEX idx_skills_skill ON user_skills(skill);

CREATE TABLE user_needs (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id),
    skill VARCHAR(100) NOT NULL,
    note VARCHAR(300) NOT NULL DEFAULT ''
);

-- 2. 협업(프로젝트)
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    requester_id INT NOT NULL REFERENCES users(id),
    worker_id    INT NOT NULL REFERENCES users(id),
    title VARCHAR(200) NOT NULL,
    -- [수정] DEFAULT 100 제거 — 견적은 '건당 확정 합의값'이므로 기본값이 있으면 안 된다.
    agreed_credits INT NOT NULL CHECK (agreed_credits > 0),
    deadline TIMESTAMPTZ,                       -- 협업방 헤더에 표시되는 마감일
    -- [수정] 시작 상태는 MATCHED. 흐름: MATCHED → IN_PROGRESS(수락 = HOLD 발생)
    --        → COMPLETED(양측 확인 = RELEASE) / CANCELLED(REFUND).
    --        초안에는 취소 상태가 없어 환불 경로가 표현 불가였다.
    status VARCHAR(30) NOT NULL DEFAULT 'MATCHED',
    requester_completed BOOLEAN NOT NULL DEFAULT FALSE,
    worker_completed    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_projects_requester ON projects(requester_id);
CREATE INDEX idx_projects_worker    ON projects(worker_id);

-- 3. 채팅 메시지
-- [주의] 시차가 제품 본체인 서비스에서 naive TIMESTAMP는 치명적이다 → 전 컬럼 TIMESTAMPTZ.
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(id),
    sender_id  INT NOT NULL REFERENCES users(id),
    content TEXT NOT NULL,
    sent_at TIMESTAMPTZ DEFAULT now(),
    read_at TIMESTAMPTZ                          -- [추가] 미읽음 표시·릴레이 판정 재료
);
CREATE INDEX idx_messages_project ON messages(project_id, id);

-- 4. AI Relay 다이제스트
CREATE TABLE ai_relay_digests (
    id SERIAL PRIMARY KEY,
    project_id   INT NOT NULL REFERENCES projects(id),
    recipient_id INT NOT NULL REFERENCES users(id),
    language VARCHAR(10) NOT NULL DEFAULT 'ko',
    trigger_type VARCHAR(10) NOT NULL DEFAULT 'auto',   -- auto | manual

    -- [추가·필수] 어느 메시지까지 요약했는지. 이 값이 없으면
    -- ① 접속할 때마다 전체 대화를 재요약(비용 폭발) ② 중복 생성 방지 불가.
    covers_to_message_id INT NOT NULL REFERENCES messages(id),

    -- [수정] 6개 TEXT 컬럼 → JSONB 단일 payload.
    -- TEXT로 평탄화하면 항목별 근거(source_ids)가 사라져
    -- "AI가 결정을 지어내면?"에 대한 방어(원문 점프 검증)가 불가능해진다.
    -- payload 형식: { "summary": [...], "decisions": [{"text","source_ids","verified"}], ... }
    payload JSONB NOT NULL,

    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_digest_lookup ON ai_relay_digests(project_id, recipient_id, id DESC);

-- 5. 크레딧 원장
-- [교체] from/to + status('ESCROWED'→'TRANSFERRED') 구조의 문제:
--   ① 거래 행을 UPDATE로 변조 — 원장은 append-only여야 감사·분쟁 대응이 된다.
--   ② 이중 정산을 막는 제약이 없다.
-- 에스크로의 상태 변화는 갱신이 아니라 '새 행'으로 표현한다:
--   HOLD(잠금, 의뢰자 -N) → RELEASE(지급, 작업자 +N) 또는 REFUND(반환, 의뢰자 +N).
CREATE TABLE credit_transactions (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id),   -- 이 거래가 반영되는 계정
    amount  INT NOT NULL,                        -- 부호 있는 값 (HOLD는 음수)
    tx_type VARCHAR(20) NOT NULL,                -- SIGNUP_BONUS | TOPUP | HOLD | RELEASE | REFUND
    project_id INT REFERENCES projects(id),
    created_at TIMESTAMPTZ DEFAULT now(),
    -- 프로젝트당 HOLD/RELEASE/REFUND 각 1회 — 이중 지급을 DB 수준에서 차단
    CONSTRAINT uq_tx_project_type UNIQUE (project_id, tx_type)
);
CREATE INDEX idx_tx_user ON credit_transactions(user_id);

-- 잔액 뷰 — 애플리케이션은 반드시 이 뷰(또는 동일 합산)로만 잔액을 읽는다.
CREATE VIEW user_balances AS
    SELECT u.id AS user_id, COALESCE(SUM(t.amount), 0)::INT AS balance
    FROM users u LEFT JOIN credit_transactions t ON t.user_id = u.id
    GROUP BY u.id;

-- 6. [추가] 상호 평가 — 확정 기획의 핵심 기능(간단한 상호 평가)이 초안에 누락됨.
--    양측 제출 시 동시 공개(보복 평가 방지)는 애플리케이션에서 처리.
CREATE TABLE reviews (
    id SERIAL PRIMARY KEY,
    project_id  INT NOT NULL REFERENCES projects(id),
    reviewer_id INT NOT NULL REFERENCES users(id),
    diligence     INT NOT NULL CHECK (diligence BETWEEN 1 AND 5),
    quality       INT NOT NULL CHECK (quality BETWEEN 1 AND 5),
    communication INT NOT NULL CHECK (communication BETWEEN 1 AND 5),
    comment VARCHAR(300) NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT uq_review_once UNIQUE (project_id, reviewer_id)
);

-- 운영 메모
-- 1) HOLD 시 잔액 검사와 INSERT는 한 트랜잭션에서 수행하고, 동시성 대비로
--    의뢰자 기준 SELECT ... FOR UPDATE 패턴을 쓸 것.
-- 2) Supabase Auth 도입 시 users.id(SERIAL)는 auth.users(UUID)와 매핑 테이블로 연결.
