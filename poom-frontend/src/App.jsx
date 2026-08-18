import { useEffect, useMemo, useRef, useState } from 'react'
import axios from 'axios'
import {
  ArrowLeft,
  Check,
  CheckCircle2,
  ChevronRight,
  Circle,
  Clock3,
  Globe2,
  Languages,
  LayoutTemplate,
  MessageCircle,
  MoonStar,
  RotateCcw,
  Send,
  Sparkles,
  SunMedium,
  UserRound,
  WandSparkles,
} from 'lucide-react'

const API_BASE = 'http://localhost:8000/api'

const COPY = {
  ko: {
    summary: 'Alex가 아기 사자의 수면 시간 동안 랜딩페이지 메인 화면의 구체적인 제작 조건을 전달했습니다.',
    decisions: '모바일 390px 화면을 우선 설계하고, 메인 컬러는 파란색(#2563eb)으로 적용하기로 했습니다.',
    pending: 'CTA 버튼 형태와 카드 대비 수준에 대한 최종 디자인 판단이 필요합니다.',
    question: '브랜드 인상과 접근성을 고려할 때 CTA 버튼을 라운드형과 사각형 중 어떤 형태로 제작할까요?',
    actions: ['모바일 메인 화면 1차 시안 제작', '디자인 의도와 함께 내일 오전까지 전달'],
    reply: '전달해 주신 요구사항을 확인했습니다. 모바일 390px 화면을 우선 설계하고 접근성 대비도 함께 점검하겠습니다. CTA는 전체 인상과 자연스럽게 연결되는 라운드형으로 먼저 제안드리겠습니다.',
  },
  en: {
    summary: 'The landing page main screen request has been delivered.',
    decisions: 'The mobile screen comes first, with blue (#2563eb) as the primary color.',
    pending: 'The button shape—rounded or square—is still undecided.',
    question: 'Should the buttons use rounded corners or a square shape?',
    actions: ['Create the mobile main screen draft', 'Deliver the first draft by tomorrow morning'],
    reply: 'I reviewed the requirements and will start with the mobile screen. I recommend rounded buttons so they feel consistent with the overall design.',
  },
}

const REQUESTS = [
  ['안녕하세요. 이번 랜딩페이지는 처음 방문한 사용자가 POOM이 어떤 문제를 해결하는지 바로 이해하는 것이 가장 중요합니다. 메인 화면에서 핵심 가치와 주요 CTA가 자연스럽게 이어지도록 1차 시안을 부탁드려요.', '어제 13:00 PDT'],
  ['우선 모바일 화면부터 작업해 주시면 좋겠습니다. 390px 기준으로 헤드라인, 서비스 요약, CTA 순서가 명확하게 보이도록 정보 위계를 잡아 주시고, 실제 사용 시 버튼을 누르기 불편하지 않은지도 함께 봐주세요.', '어제 13:18 PDT'],
  ['메인 컬러는 파란색(#2563eb)으로 정리했습니다. 화면 전체를 파란색으로 채우기보다는 버튼과 꼭 강조해야 하는 정보에만 사용하고, 배경과 카드는 차분하게 구성해 주시면 좋겠습니다.', '어제 13:42 PDT'],
  ['버튼 형태는 아직 최종 결정하지 못했습니다. 라운드형과 각진 형태 중 POOM의 신뢰감 있고 부드러운 인상에 더 잘 맞는 방향을 디자이너 관점에서 제안해 주시면 시안 검토에 도움이 될 것 같아요.', '어제 14:20 PDT'],
  ['내일 오전에 팀 내부 리뷰를 진행할 예정입니다. 가능하다면 모바일 1차 시안과 함께 주요 레이아웃을 그렇게 구성한 이유를 짧게 정리해서 보내 주세요. 검토 후 피드백을 한 번에 전달드리겠습니다.', '어제 15:10 PDT'],
]

const createRequestMessages = () =>
  REQUESTS.map(([text, time], index) => ({
    id: index + 1,
    sender: 'alex',
    name: 'Alex · Project Lead',
    text,
    time,
    unread: true,
  }))

const PHASES = [
  { id: 'brief', label: '요청 전달' },
  { id: 'gap', label: '시차 공백' },
  { id: 'relay', label: 'AI Relay' },
  { id: 'resume', label: '협업 재개' },
]

const SECONDARY_PROJECTS = [
  {
    id: 'onboarding',
    title: '모바일 온보딩 UX 개선',
    description: 'Sofia와 함께 진행 중인 사용자 경험 개선 작업',
    partner: { name: 'Sofia', role: 'UX Writer', city: 'London', time: '14:20', avatar: 'S' },
    status: '피드백 대기',
    lastActive: '1시간 전',
    lastActiveMinutes: 60,
    unread: 2,
    deadline: '8월 21일',
    activeStep: 2,
    workflow: ['요청 정리', '문구 초안', '피드백 확인', '적용 완료'],
    contextNotice: '아기 사자가 자는 동안 Sofia가 오후에 피드백 2개를 남겼습니다.',
    messages: [
      { id: 1, sender: 'babyLion', name: '아기 사자 · Maker', text: '사용자 인터뷰에서 가입 단계가 길고 각 단계의 목적이 불분명하다는 의견이 반복적으로 나왔어요. 현재 흐름을 더 간결하게 줄일 수 있을까요?', time: '13:42' },
      { id: 2, sender: 'partner', name: 'Sofia · UX Writer', text: '필수 정보와 선택 정보를 분리하면 세 단계로 축약할 수 있습니다. 각 단계에는 사용자가 얻는 이점을 먼저 설명하는 방식이 좋겠습니다.', time: '14:08' },
      { id: 3, sender: 'partner', name: 'Sofia · UX Writer', text: '새로운 안내 문구와 단계별 CTA 초안을 정리했습니다. 특히 권한 요청 화면의 거부감을 줄이는 표현을 함께 검토해 주세요.', time: '14:20', unread: true },
    ],
  },
  {
    id: 'payment',
    title: '결제 API 연동 검토',
    description: 'Daniel과 진행 중인 크레딧 결제 연동 작업',
    partner: { name: 'Daniel', role: 'Backend Engineer', city: 'Singapore', time: '21:10', avatar: 'D' },
    status: '검토 중',
    lastActive: '어제',
    lastActiveMinutes: 1440,
    unread: 0,
    deadline: '8월 23일',
    activeStep: 2,
    workflow: ['연동 완료', '응답 문서', '프론트 검토', '배포 준비'],
    contextNotice: 'Daniel이 업무를 마친 뒤 연동 결과를 남겨 아기 사자가 다음 날 확인했습니다.',
    messages: [
      { id: 1, sender: 'partner', name: 'Daniel · Backend Engineer', text: '샌드박스 환경에서 결제 승인, 부분 취소, 전체 환불 시나리오까지 정상적으로 연결했습니다. 멱등성 키 처리도 함께 적용했습니다.', time: '20:46' },
      { id: 2, sender: 'babyLion', name: '아기 사자 · Maker', text: '확인했습니다. 프론트엔드에서는 실패 코드별 안내 문구가 필요하니 에러 응답 구조와 재시도 가능 여부를 한 번 더 검토할게요.', time: '21:02' },
      { id: 3, sender: 'partner', name: 'Daniel · Backend Engineer', text: '주요 실패 코드와 응답 예시를 API 문서에 추가했습니다. 네트워크 타임아웃은 동일한 멱등성 키로 재시도할 수 있습니다.', time: '21:10' },
    ],
  },
  {
    id: 'brand-guide',
    title: '브랜드 가이드 최종 검수',
    description: 'Maya의 확인을 기다리고 있는 브랜드 정리 작업',
    partner: { name: 'Maya', role: 'Brand Designer', city: 'New York', time: '09:30', avatar: 'M' },
    status: '응답 대기',
    lastActive: '4시간 전',
    lastActiveMinutes: 240,
    unread: 0,
    outgoingUnread: 3,
    deadline: '8월 22일',
    activeStep: 2,
    workflow: ['자료 요청', '가이드 전달', '검수 대기', '수정 반영'],
    contextNotice: 'Maya가 업무를 시작하기 전에 아기 사자가 검수 요청 3개를 남겼습니다.',
    messages: [
      { id: 1, sender: 'partner', name: 'Maya · Brand Designer', text: '최종 컬러 조합과 실제 화면에 적용한 예시를 보내주시면 전체 분위기가 자연스러운지 함께 확인해 볼게요.', time: '08:52' },
      { id: 2, sender: 'babyLion', name: '아기 사자 · Maker', text: '딥 네이비를 기본으로 하고 보라와 파랑은 버튼이나 중요한 부분에만 사용했어요. 화면이 너무 어둡거나 강해 보이지 않도록 전체 색감을 조정했습니다.', time: '09:12', unread: true },
      { id: 3, sender: 'babyLion', name: '아기 사자 · Maker', text: '버튼, 상태 표시, 카드 테두리에 적용한 예시도 함께 보내드립니다. 글자가 배경에서 충분히 잘 보이는지도 같이 확인해 봤어요.', time: '09:18', unread: true },
      { id: 4, sender: 'babyLion', name: '아기 사자 · Maker', text: '전체적으로 어색한 부분이나 조금 더 부드럽게 다듬으면 좋을 곳이 있으면 편하게 알려주세요.', time: '09:30', unread: true },
    ],
  },
]

function App() {
  const [screen, setScreen] = useState('home')
  const [selectedProjectId, setSelectedProjectId] = useState('landing')
  const [phase, setPhase] = useState('waiting')
  const [lang, setLang] = useState('ko')
  const [messages, setMessages] = useState(createRequestMessages)
  const [digest, setDigest] = useState(null)
  const [input, setInput] = useState('')
  const [checkedActions, setCheckedActions] = useState([])
  const streamRef = useRef(null)

  const activeStep = useMemo(() => {
    if (phase === 'complete') return 3
    if (['digest', 'draft'].includes(phase)) return 2
    if (['waiting', 'analyzing'].includes(phase)) return 1
    return 0
  }, [phase])

  const selectedSecondaryProject = SECONDARY_PROJECTS.find((project) => project.id === selectedProjectId)

  const openRoom = (projectId) => {
    setSelectedProjectId(projectId)
    setScreen('room')
  }

  useEffect(() => {
    streamRef.current?.scrollTo({ top: streamRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, phase])

  const resetDemo = () => {
    setPhase('waiting')
    setMessages(createRequestMessages())
    setDigest(null)
    setInput('')
    setCheckedActions([])
  }

  const changeLanguage = (nextLang) => {
    setLang(nextLang)
    if (digest) setDigest(COPY[nextLang])
  }

  const generateDigest = async () => {
    setPhase('analyzing')

    try {
      const request = axios.post(
        `${API_BASE}/relay-digest`,
        {
          chat_history: messages.map((message) => message.text).join('\n'),
          target_lang: lang,
        },
        { timeout: 3500 },
      )
      const [response] = await Promise.all([
        request,
        new Promise((resolve) => setTimeout(resolve, 1100)),
      ])
      const data = response?.data?.digest
      setDigest(data ? { ...COPY[lang], ...data, question: data.question || data.key_questions } : COPY[lang])
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 900))
      setDigest(COPY[lang])
    }

    setPhase('digest')
  }

  const applyReply = () => {
    setInput(digest.reply || digest.suggested_reply)
    setPhase('draft')
  }

  const sendReply = () => {
    if (!input.trim()) return
    setMessages((current) => [
      ...current.map((message) => ({ ...message, unread: false })),
      {
        id: Date.now(),
        sender: 'babyLion',
        name: '아기 사자 · Maker',
        text: input.trim(),
        time: '10:17 KST',
      },
    ])
    setInput('')
    setPhase('complete')
  }

  const toggleAction = (index) => {
    setCheckedActions((current) =>
      current.includes(index) ? current.filter((item) => item !== index) : [...current, index],
    )
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-inner">
          <button className="brand" onClick={() => setScreen('home')} aria-label="POOM 홈">
            <span className="brand-mark">P</span>
            <span className="brand-word">POOM</span>
            <span className="brand-dot" />
          </button>

          <div className="project-chip">
            <LayoutTemplate size={14} />
            <span>{screen === 'home' ? '내 협업' : selectedSecondaryProject?.title || '랜딩페이지 UI 제작'}</span>
            {screen === 'room' && <span className="project-chip-status">진행 중</span>}
          </div>

          <div className="top-actions">
            <div className="language-toggle" aria-label="언어 선택">
              <Languages size={15} />
              <button className={lang === 'ko' ? 'active' : ''} onClick={() => changeLanguage('ko')}>KO</button>
              <button className={lang === 'en' ? 'active' : ''} onClick={() => changeLanguage('en')}>EN</button>
            </div>
            {screen === 'room' && (
              <button className="icon-button" onClick={resetDemo} aria-label="새 메시지 상태로 돌아가기" title="새 메시지 상태로 돌아가기">
                <RotateCcw size={17} />
              </button>
            )}
            <div className="avatar" title="아기 사자" aria-label="현재 사용자: 아기 사자">🦁</div>
          </div>
        </div>
      </header>

      {screen === 'home' ? (
        <HomeView
          messages={messages}
          phase={phase}
          onOpenRoom={openRoom}
        />
      ) : selectedProjectId === 'landing' ? (
      <main className="workspace">
        <aside className="sidebar">
          <div className="progress-card">
            <div className="progress-heading">
              <span>현재 작업 흐름</span>
              <span>{Math.round(((activeStep + 1) / PHASES.length) * 100)}%</span>
            </div>
            <div className="progress-track"><span style={{ width: `${((activeStep + 1) / PHASES.length) * 100}%` }} /></div>
            <ol className="phase-list">
              {PHASES.map((item, index) => (
                <li key={item.id} className={index < activeStep ? 'done' : index === activeStep ? 'active' : ''}>
                  <span className="phase-icon">{index < activeStep ? <Check size={12} /> : index + 1}</span>
                  <span>{item.label}</span>
                </li>
              ))}
            </ol>
          </div>

          <div className="people-card">
            <div className="section-title"><UserRound size={15} /> 참여자</div>
            <div className="person-row">
              <div className="mini-avatar violet">A</div>
              <div><strong>Alex</strong><span>San Francisco · 전날 18:15</span></div>
              <span className="status-pill sleep"><MoonStar size={11} /> 업무 종료</span>
            </div>
            <div className="person-row">
              <div className="mini-avatar blue">🦁</div>
              <div><strong>아기 사자</strong><span>Seoul · 10:15</span></div>
              <span className="status-pill online"><Circle size={8} fill="currentColor" /> 온라인</span>
            </div>
            <div className="timezone-note"><Globe2 size={14} /> 서울이 샌프란시스코보다 16시간 빠릅니다.</div>
          </div>

          <div className="demo-control">
            {phase === 'waiting' && (
              <button className="primary-button" onClick={generateDigest}>
                <Sparkles size={16} /> 읽지 않은 메시지 요약하기
              </button>
            )}
            {phase === 'analyzing' && (
              <button className="primary-button" disabled>
                <span className="spinner" /> Relay 분석 중
              </button>
            )}
            {['digest', 'draft'].includes(phase) && (
              <div className="demo-hint"><Sparkles size={15} /> 추천 답변을 적용하거나 직접 내용을 수정할 수 있어요.</div>
            )}
            {phase === 'complete' && (
              <div className="demo-success"><CheckCircle2 size={16} /> 모든 새 메시지를 확인했어요.</div>
            )}
          </div>
        </aside>

        <section className="conversation-panel">
          <div className="panel-header">
            <div className="room-heading">
              <button className="room-back" onClick={() => setScreen('home')} aria-label="협업 목록으로 돌아가기">
                <ArrowLeft size={16} />
              </button>
              <h2>랜딩페이지 UI 제작</h2>
            </div>
            <div className="channel-meta">
              <MessageCircle size={14} />
              {messages.some((message) => message.unread)
                ? `읽지 않음 ${messages.filter((message) => message.unread).length}`
                : `메시지 ${messages.length}`}
            </div>
          </div>

          <div className="message-stream" ref={streamRef}>
            {messages.length === 0 ? (
              <div className="empty-conversation">
                <div className="empty-orbit"><MessageCircle size={28} /></div>
                <span className="soft-badge">ASYNC COLLABORATION</span>
                <h3>아직 도착한 메시지가 없어요.</h3>
                <p>새로운 협업 메시지가 도착하면 이곳에서 바로 확인할 수 있습니다.</p>
              </div>
            ) : (
              <>
                <div className="date-divider"><span>오늘</span></div>
                {[...messages].sort((first, second) => Number(first.id) - Number(second.id)).map((message) => (
                  <article key={message.id} className={`message-row ${message.sender === 'babyLion' ? 'mine' : ''}`}>
                    <div className={`message-avatar ${message.sender === 'babyLion' ? 'blue' : 'violet'}`}>
                      {message.sender === 'babyLion' ? '🦁' : 'A'}
                    </div>
                    <div className="message-body">
                      <div className="message-author"><strong>{message.name}</strong><span>{message.time}</span></div>
                      <div className="message-bubble">{message.text}</div>
                      {message.unread && <span className="unread-label">읽지 않음</span>}
                    </div>
                  </article>
                ))}
                {phase === 'waiting' && (
                  <div className="gap-notice"><MoonStar size={15} /><span>아기 사자가 자는 동안 Alex가 오후에 메시지 5개를 남겼습니다.</span></div>
                )}
                {phase === 'complete' && (
                  <div className="resume-notice"><CheckCircle2 size={15} /><span>AI Relay를 통해 협업이 다시 시작되었습니다.</span></div>
                )}
              </>
            )}
          </div>

          <div className="composer">
            <div className="composer-box">
              <textarea
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault()
                    sendReply()
                  }
                }}
                placeholder="아기 사자로 답변을 작성하세요…"
                disabled={!['digest', 'draft'].includes(phase)}
                aria-label="메시지 입력"
              />
              <button onClick={sendReply} disabled={!input.trim()} aria-label="메시지 전송"><Send size={17} /></button>
            </div>
            <span>Enter로 전송 · Shift + Enter로 줄바꿈</span>
          </div>
        </section>

        <aside className={`relay-panel ${digest ? 'is-active' : ''}`}>
          <div className="relay-heading">
            <div className="relay-title"><span><WandSparkles size={17} /></span><div><p>POOM AI</p><h2>Relay Digest</h2></div></div>
            {phase === 'complete' && <span className="complete-pill"><Check size={12} /> 확인 완료</span>}
          </div>

          {phase === 'analyzing' ? (
            <div className="analysis-state">
              <div className="analysis-glow"><Sparkles size={27} /></div>
              <h3>대화의 맥락을 연결하고 있어요.</h3>
              <p>누적된 5개의 메시지에서 결정사항과 다음 행동을 찾는 중입니다.</p>
              <div className="analysis-bars"><span /><span /><span /></div>
            </div>
          ) : !digest ? (
            <div className="relay-idle">
              <span className="relay-idle-icon"><Sparkles size={18} /></span>
              <h3>요약 대기 중</h3>
              <p>읽지 않은 메시지를 요약하면 이곳에 정리됩니다.</p>
            </div>
          ) : (
            <div className={`digest-content ${phase === 'complete' ? 'compact' : ''}`}>
              <div className="digest-intro">
                <span><Sparkles size={13} /> 5개 메시지 분석 완료</span>
                <p>아기 사자가 놓친 대화의 맥락을 간결하게 정리했어요.</p>
              </div>

              <div className="digest-grid">
                <DigestCard tone="violet" label="진행 상황" icon="01" text={digest.summary} />
                <DigestCard tone="teal" label="결정 사항" icon="02" text={digest.decisions} />
                <DigestCard tone="amber" label="미결정 사항" icon="03" text={digest.pending} />
                <DigestCard tone="blue" label="핵심 질문" icon="04" text={digest.question || digest.key_questions} />
              </div>

              <div className="action-block">
                <div className="block-title"><span>Action items</span><small>{checkedActions.length}/{digest.actions?.length || digest.action_items?.length || 0}</small></div>
                {(digest.actions || digest.action_items || []).map((action, index) => (
                  <button className={`action-row ${checkedActions.includes(index) ? 'checked' : ''}`} key={action} onClick={() => toggleAction(index)}>
                    <span className="check-box">{checkedActions.includes(index) && <Check size={12} />}</span>
                    <span>{action}</span>
                  </button>
                ))}
              </div>

              {phase !== 'complete' && (
                <div className="suggestion-block">
                  <div className="block-title"><span>추천 답변</span><small>톤 완충 적용</small></div>
                  <p>“{digest.reply || digest.suggested_reply}”</p>
                  <button onClick={applyReply}><Sparkles size={14} /> 입력창에 적용 <ChevronRight size={14} /></button>
                </div>
              )}
            </div>
          )}
        </aside>
      </main>
      ) : (
        <SimpleProjectRoom project={selectedSecondaryProject} onBack={() => setScreen('home')} />
      )}
    </div>
  )
}

function HomeView({ messages, phase, onOpenRoom }) {
  const unreadCount = messages.filter((message) => message.unread).length
  const latestMessage = messages.at(-1)
  const projects = [
    {
      id: 'landing',
      title: '랜딩페이지 UI 제작',
      description: 'Alex와 아기 사자가 함께 진행 중인 협업방',
      partner: { name: 'Alex', avatar: 'A' },
      status: '진행 중',
      lastActive: '3시간 전',
      lastActiveMinutes: 180,
      unread: unreadCount,
      latestMessage,
      isRelayProject: true,
      isComplete: phase === 'complete',
    },
    ...SECONDARY_PROJECTS.map((project) => ({
      ...project,
      latestMessage: project.messages.at(-1),
    })),
  ].sort((first, second) => first.lastActiveMinutes - second.lastActiveMinutes)

  return (
    <main className="home-view">
      <div className="home-heading">
        <div>
          <p>내 협업</p>
          <h1>진행 중인 작업</h1>
        </div>
        <span>4개의 작업</span>
      </div>

      <div className="project-list">
        {projects.map((project) => (
          <HomeProjectCard project={project} onOpenRoom={onOpenRoom} key={project.id} />
        ))}
      </div>
    </main>
  )
}

function HomeProjectCard({ project, onOpenRoom }) {
  const latest = project.latestMessage
  const partnerTone = project.id === 'payment' ? 'teal' : 'violet'
  const statusTone = project.outgoingUnread ? 'amber' : project.id === 'payment' ? 'blue' : ''

  return (
    <button className="project-room-card" onClick={() => onOpenRoom(project.id)}>
      <div className="project-card-top">
        <span className={`active-project-pill ${statusTone}`}>{project.status}</span>
        <span className="last-active"><Clock3 size={13} /> {project.lastActive}</span>
      </div>
      <h2>{project.title}</h2>
      <p className="project-description">{project.description}</p>
      <div className="last-message">
        <span>{latest?.sender === 'babyLion' ? '아기 사자' : project.partner.name}</span>
        <p>{latest?.text || '새로운 메시지가 없습니다.'}</p>
      </div>
      <div className="project-card-footer">
        <div className="participant-stack" aria-label={`참여자 ${project.partner.name}와 아기 사자`}>
          <span className={partnerTone}>{project.partner.avatar}</span>
          <span className="blue">🦁</span>
        </div>
        <div className="project-card-status">
          {project.unread > 0 && <span className="unread-count">읽지 않음 {project.unread}</span>}
          {project.outgoingUnread > 0 && <span className="waiting-count">상대방 미확인 {project.outgoingUnread}</span>}
          {project.isComplete && <span className="caught-up"><Check size={12} /> 모두 확인</span>}
          {!project.unread && !project.outgoingUnread && !project.isComplete && <span className="caught-up"><Check size={12} /> 모두 확인</span>}
          <ChevronRight size={18} />
        </div>
      </div>
    </button>
  )
}

function SimpleProjectRoom({ project, onBack }) {
  const [roomMessages, setRoomMessages] = useState(project.messages)
  const [draft, setDraft] = useState('')

  const sendMessage = () => {
    if (!draft.trim()) return
    setRoomMessages((current) => [
      ...current,
      {
        id: Date.now(),
        sender: 'babyLion',
        name: '아기 사자 · Maker',
        text: draft.trim(),
        time: '지금',
      },
    ])
    setDraft('')
  }

  return (
    <main className="simple-workspace">
      <aside className="simple-room-sidebar">
        <div className="simple-project-meta">
          <span className="active-project-pill">{project.status}</span>
          <h2>{project.title}</h2>
          <p>{project.description}</p>
        </div>

        <div className="progress-card simple-workflow">
          <div className="progress-heading">
            <span>현재 작업 흐름</span>
            <span>{Math.round(((project.activeStep + 1) / project.workflow.length) * 100)}%</span>
          </div>
          <div className="progress-track"><span style={{ width: `${((project.activeStep + 1) / project.workflow.length) * 100}%` }} /></div>
          <ol className="phase-list">
            {project.workflow.map((item, index) => (
              <li key={item} className={index < project.activeStep ? 'done' : index === project.activeStep ? 'active' : ''}>
                <span className="phase-icon">{index < project.activeStep ? <Check size={12} /> : index + 1}</span>
                <span>{item}</span>
              </li>
            ))}
          </ol>
        </div>

        <div className="people-card">
          <div className="section-title"><UserRound size={15} /> 참여자</div>
          <div className="person-row">
            <div className="mini-avatar violet">{project.partner.avatar}</div>
            <div><strong>{project.partner.name}</strong><span>{project.partner.city} · {project.partner.time}</span></div>
            <span className="status-pill online"><Circle size={8} fill="currentColor" /> 온라인</span>
          </div>
          <div className="person-row">
            <div className="mini-avatar blue">🦁</div>
            <div><strong>아기 사자</strong><span>Seoul · 10:15</span></div>
            <span className="status-pill working"><SunMedium size={11} /> 근무 중</span>
          </div>
        </div>

        <div className="simple-deadline">
          <span>마감 예정</span>
          <strong>{project.deadline}</strong>
        </div>
      </aside>

      <section className="simple-conversation">
        <div className="panel-header">
          <div className="room-heading">
            <button className="room-back" onClick={onBack} aria-label="협업 목록으로 돌아가기"><ArrowLeft size={16} /></button>
            <h2>{project.title}</h2>
          </div>
          <div className="channel-meta"><MessageCircle size={14} /> 메시지 {roomMessages.length}</div>
        </div>

        <div className="message-stream">
          <div className="date-divider"><span>오늘</span></div>
          {[...roomMessages].sort((first, second) => Number(first.id) - Number(second.id)).map((message) => (
            <article key={message.id} className={`message-row ${message.sender === 'babyLion' ? 'mine' : ''}`}>
              <div className={`message-avatar ${message.sender === 'babyLion' ? 'blue' : 'violet'}`}>
                {message.sender === 'babyLion' ? '🦁' : project.partner.avatar}
              </div>
              <div className="message-body">
                <div className="message-author"><strong>{message.name}</strong><span>{message.time}</span></div>
                <div className="message-bubble">{message.text}</div>
                {message.unread && (
                  <span className="unread-label">{message.sender === 'babyLion' ? '상대방 미확인' : '읽지 않음'}</span>
                )}
              </div>
            </article>
          ))}
          {roomMessages.length === project.messages.length && (
            <div className="gap-notice">
              {project.outgoingUnread ? <Clock3 size={15} /> : <MoonStar size={15} />}
              <span>{project.contextNotice}</span>
            </div>
          )}
        </div>

        <div className="composer">
          <div className="composer-box">
            <textarea
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && !event.shiftKey) {
                  event.preventDefault()
                  sendMessage()
                }
              }}
              placeholder="메시지를 입력하세요…"
              aria-label="메시지 입력"
            />
            <button onClick={sendMessage} disabled={!draft.trim()} aria-label="메시지 전송"><Send size={17} /></button>
          </div>
        </div>
      </section>
    </main>
  )
}

function DigestCard({ tone, label, icon, text }) {
  return (
    <article className={`digest-card ${tone}`}>
      <div><span>{icon}</span><strong>{label}</strong></div>
      <p>{text}</p>
    </article>
  )
}

export default App
