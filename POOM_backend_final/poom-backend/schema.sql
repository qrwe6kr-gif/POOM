-- =====================================================================
-- POOM 백엔드 스키마 (PostgreSQL / Supabase)
-- 로컬 개발은 SQLite(SQLAlchemy가 자동 생성), 배포 시 본 DDL을 실행한다.
-- 원칙: 잔액 컬럼 없음 — 잔액은 credit_transactions 합산 뷰로만 조회한다.
-- =====================================================================

create table if not exists users (
  id           varchar(32) primary key,
  name         varchar(80)  not null,
  email        varchar(120) not null unique,
  country      varchar(40)  not null default '',
  tz           varchar(64)  not null default 'Asia/Seoul',   -- IANA 타임존
  lang         varchar(8)   not null default 'ko',           -- 다이제스트 언어
  work_start   int          not null default 9,
  work_end     int          not null default 18,
  sleep_start  int          not null default 23,
  sleep_end    int          not null default 7,
  is_pro       boolean      not null default false,
  demo_now     timestamptz,          -- 데모 모드: 계정별 가상 '현재 시각'
  last_active_at timestamptz,         -- 마지막 접속(요청) 시각
  created_at   timestamptz
);

create table if not exists user_skills (
  id            serial primary key,
  user_id       varchar(32) not null references users(id),
  role          varchar(40) not null,      -- dev/design/sound/plan/marketing/translate
  level         varchar(20) not null default 'junior',
  portfolio_url varchar(300) not null default ''
);
create index if not exists idx_skills_role on user_skills(role);

create table if not exists user_needs (
  id       serial primary key,
  user_id  varchar(32) not null references users(id),
  role     varchar(40) not null,
  note     varchar(300) not null default ''
);

-- 상태 머신: requested → agreed → completed / cancelled
create table if not exists collabs (
  id                  varchar(32) primary key,
  requester_id        varchar(32) not null references users(id),
  provider_id         varchar(32) not null references users(id),
  title               varchar(160) not null,
  scope               text not null default '',
  credit_amount       int  not null check (credit_amount > 0),  -- 건당 확정 견적
  deadline            timestamptz,
  status              varchar(20) not null default 'requested',
  requester_confirmed boolean not null default false,
  provider_confirmed  boolean not null default false,
  created_at          timestamptz,
  agreed_at           timestamptz,
  completed_at        timestamptz
);
create index if not exists idx_collabs_req on collabs(requester_id);
create index if not exists idx_collabs_prov on collabs(provider_id);

create table if not exists messages (
  id         serial primary key,
  collab_id  varchar(32) not null references collabs(id),
  sender_id  varchar(32) not null references users(id),
  body       text not null,
  created_at timestamptz,
  read_at    timestamptz
);
create index if not exists idx_messages_collab on messages(collab_id, id);

-- append-only 원장. UPDATE/DELETE 금지(정정도 새 행으로).
-- ttype: signup_bonus | topup | hold | release | refund
create table if not exists credit_transactions (
  id         serial primary key,
  user_id    varchar(32) not null references users(id),
  amount     int not null,                      -- 부호 있는 값
  ttype      varchar(20) not null,
  collab_id  varchar(32) references collabs(id),
  created_at timestamptz,
  constraint uq_tx_collab_type unique (collab_id, ttype)  -- 협업당 hold/release/refund 각 1회
);
create index if not exists idx_tx_user on credit_transactions(user_id);

-- 잔액 뷰 — 애플리케이션은 이 뷰(또는 동일한 합산)로만 잔액을 읽는다.
create or replace view user_balances as
  select u.id as user_id, coalesce(sum(t.amount), 0)::int as balance
  from users u left join credit_transactions t on t.user_id = u.id
  group by u.id;

-- AI Relay 다이제스트 — payload는 6필드 JSON,
-- 각 항목은 근거 메시지 id 배열(source_ids)을 반드시 포함한다(환각 게이트).
create table if not exists relay_digests (
  id                   serial primary key,
  collab_id            varchar(32) not null references collabs(id),
  for_user_id          varchar(32) not null references users(id),
  lang                 varchar(8)  not null,
  trigger              varchar(10) not null,      -- auto | manual
  covers_to_message_id int not null,
  payload              jsonb not null,
  is_read              boolean not null default false,  -- 수신자 답변 전송 시 확인 완료
  created_at           timestamptz
);
create index if not exists idx_digest_lookup on relay_digests(collab_id, for_user_id, id desc);

create table if not exists reviews (
  id            serial primary key,
  collab_id     varchar(32) not null references collabs(id),
  reviewer_id   varchar(32) not null references users(id),
  diligence     int not null check (diligence between 1 and 5),
  quality       int not null check (quality between 1 and 5),
  communication int not null check (communication between 1 and 5),
  comment       varchar(300) not null default '',
  created_at    timestamptz,
  constraint uq_review_once unique (collab_id, reviewer_id)
);

-- 운영 메모:
-- 1) hold 시 잔액 검사와 INSERT는 한 트랜잭션에서 수행하고,
--    동시성 대비로 requester 행을 select ... for update 로 잠글 것.
-- 2) Supabase Auth 도입 시 users.id를 auth.users(id)와 매핑하는 프로필 테이블 구조로
--    전환하면 된다(코드 측 교체 지점: app/deps.py 하나).
