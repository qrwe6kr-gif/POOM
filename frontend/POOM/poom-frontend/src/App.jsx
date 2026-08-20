import { useEffect, useMemo, useRef, useState } from 'react'
import {
  ArrowLeft,
  ArrowRight,
  Check,
  CheckCircle2,
  ChevronRight,
  Circle,
  Clock3,
  Globe2,
  Languages,
  LayoutTemplate,
  MessageCircle,
  Mail,
  MoonStar,
  RotateCcw,
  Send,
  Sparkles,
  SunMedium,
  UserRound,
  WandSparkles,
} from 'lucide-react'
import {
  getProjectDetail,
  getUserStatus,
  getMessages,
  sendMessage,
  getRelayDigest,
  login,
  seedDemo,
  
} from './api/poomApi'

const COPY = {
  ko: {
    summary: 'Alex가 아기 사자의 수면 시간 동안 랜딩페이지 메인 화면의 구체적인 제작 조건을 전달했습니다.',
    decisions: '모바일 화면을 우선 제작하고, 메인 컬러는 파란색(#2563eb)으로 결정했습니다.',
    pending: '버튼 형태(라운드형 또는 사각형)가 아직 결정되지 않았습니다.',
    question: '버튼을 라운드형과 사각형 중 어떤 형태로 제작할지요?',
    actions: ['모바일 메인 화면 시안 제작', '내일 오전까지 초안 전달'],
    reply: '요구사항을 확인했습니다. 모바일 화면을 먼저 제작하겠습니다. 버튼은 전체 디자인과 어울리도록 라운드형을 제안드립니다.',
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

const FALLBACK_ROOM = {
  project_id: 'proj_landing_01',
  project_title: '랜딩페이지 UI 제작',
  workflow: { current_step: 2, progress_percent: 50 },
  participants: [
    { user_id: 'us_user_01', name: 'Alex', role: 'Project Lead', location: 'San Francisco · 전날 18:15', status: 'sleeping', badge: '비근무' },
    { user_id: 'kr_user_01', name: '민준', role: 'Collaborator', location: 'Seoul · 10:15', status: 'working', badge: '업무 가능' },
  ],
  timezone_gap_text: '서울이 샌프란시스코보다 16시간 빠릅니다.',
}

const FALLBACK_ABSENCE_BANNER = {
  show: true,
  text: '민준이 자는 동안 Alex가 메시지 5개를 남겼습니다.',
}

// v2 API 메시지 규격 매핑
const mapApiMessage = (message, currentUserId) => {
  const isMine = message.mine ?? (message.sender_id === currentUserId || message.sender_id === 'kr_user_01')
  return {
    id: message.message_id || message.id || Date.now(),
    sender: isMine ? 'babyLion' : 'alex',
    name: isMine ? '민준 · Collaborator' : 'Alex · Project Lead',
    text: message.body || message.content || message.text || '',
    time: message.created_at ? new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '지금',
    unread: Boolean(message.unread || message.is_unread),
  }
}

// v2 객체 배열(GroundedItem) 및 구버전 호환 파서
const mapApiDigest = (data, fallback) => {
  if (!data?.digest && !data?.grid_cards) return fallback

  const extractText = (field) => {
    if (!field) return ''
    if (typeof field === 'string') return field
    if (Array.isArray(field)) return field.map(item => typeof item === 'string' ? item : item.text).join(' ')
    return ''
  }

  const payload = data.digest || data.grid_cards
  const actionList = data.digest?.action_items || data.action_items || []

  return {
    id: data.digest_id,
    analyzedCount: data.unread_message_count || data.analyzed_count,
    title: data.header_title || `${data.unread_message_count || 5}개 메시지 분석 완료`,
    subtitle: data.header_subtitle || '민준이 놓친 대화의 맥락을 간결하게 정리했어요.',
    summary: extractText(payload.summary || payload.progress_summary),
    decisions: extractText(payload.decisions || payload.decisions_made),
    pending: extractText(payload.pending || payload.pending_items),
    question: extractText(payload.key_questions),
    actions: actionList.map((item, idx) => ({
      id: item.id || `act_${idx + 1}`,
      text: typeof item === 'string' ? item : item.text
    })),
    reply: data.digest?.tone_cushioned_message || data.suggested_reply?.text || fallback.reply,
    replyTag: data.suggested_reply?.tag || '톤 완충 적용',
    workflowProgress: data.workflow_progress ?? 75,
  }
}

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
    contextNotice: '민준이 자는 동안 Sofia가 오후에 피드백 2개를 남겼습니다.',
    messages: [
      { id: 1, sender: 'babyLion', name: '민준 · Maker', text: '사용자 인터뷰에서 가입 단계가 길고 각 단계의 목적이 불분명하다는 의견이 반복적으로 나왔어요. 현재 흐름을 더 간결하게 줄일 수 있을까요?', time: '13:42' },
      { id: 2, sender: 'partner', name: 'Sofia · UX Writer', text: '필수 정보와 선택 정보를 분리하면 세 단계로 축약할 수 있습니다. 각 단계에는 사용자가 얻는 이점을 먼저 설명하는 방식이 좋겠습니다.', time: '14:08' },
      { id: 3, sender: 'partner', name: 'Sofia · UX Writer', text: '새로운 안내 문구와 단계별 CTA 초안을 정리했습니다. 특히 권한 요청 화면의 거부감을 줄이는 표현을 함께 검토해 주세요.', time: '14:20', unread: true },
    ],
  }
]

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(() => Boolean(localStorage.getItem('user_id')))
  const [loginEmail, setLoginEmail] = useState('')
  const [loginError, setLoginError] = useState('')
  const [isLoggingIn, setIsLoggingIn] = useState(false)
  const [screen, setScreen] = useState('home')
  const [selectedProjectId, setSelectedProjectId] = useState('landing')
  const [phase, setPhase] = useState('waiting')
  const [lang, setLang] = useState(() => localStorage.getItem('poom-language') || 'ko')
  const [messages, setMessages] = useState([])
  const [room, setRoom] = useState(FALLBACK_ROOM)
  const [absenceBanner, setAbsenceBanner] = useState(FALLBACK_ABSENCE_BANNER)
  const [digest, setDigest] = useState(null)
  const [input, setInput] = useState('')
  const [checkedActions, setCheckedActions] = useState([])
  const [isSending, setIsSending] = useState(false)
  const streamRef = useRef(null)

  useEffect(() => {
    document.documentElement.lang = lang
    localStorage.setItem('poom-language', lang)
  }, [lang])

  const activeStep = useMemo(() => {
    const currentStep = Number(room.workflow?.current_step || 2)
    return Math.max(0, Math.min(PHASES.length - 1, currentStep - 1))
  }, [room.workflow?.current_step])

  const progressPercent = room.workflow?.progress_percent ?? Math.round(((activeStep + 1) / PHASES.length) * 100)
  const digestActions = digest?.actions || []
  const selectedSecondaryProject = SECONDARY_PROJECTS.find((project) => project.id === selectedProjectId)

  const openRoom = (projectId) => {
    setSelectedProjectId(projectId)
    setScreen('room')
  }

  const handleLogin = async (event) => {
    event.preventDefault()
    const email = loginEmail.trim()
    if (!email || isLoggingIn) return

    setIsLoggingIn(true)
    setLoginError('')
    try {
      const response = await login(email)
      localStorage.setItem('user_id', response.data.user_id)
      setIsAuthenticated(true)
    } catch (error) {
      setLoginError(error.response?.data?.detail || '로그인에 실패했습니다. 이메일을 확인해 주세요.')
    } finally {
      setIsLoggingIn(false)
    }
  }

  useEffect(() => {
    streamRef.current?.scrollTo({ top: streamRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, phase])

  // v2 API 연동: 프로젝트 정보, 상대방 상태, 메시지 목록 일괄 조회
  const loadData = async () => {
    try {
      const [projRes, statusRes, msgRes] = await Promise.allSettled([
        getProjectDetail('proj_landing_01'),
        getUserStatus('us_user_01'),
        getMessages('proj_landing_01')
      ])

      let nextRoom = { ...FALLBACK_ROOM }
      if (projRes.status === 'fulfilled' && projRes.value.data) {
        nextRoom.project_title = projRes.value.data.title
      }

      if (statusRes.status === 'fulfilled' && statusRes.value.data) {
        const s = statusRes.value.data
        nextRoom.participants = [
          {
            user_id: s.user_id,
            name: s.name,
            role: 'Project Lead',
            location: `San Francisco · ${s.local_time}`,
            status: s.status.toLowerCase(),
            badge: s.status_label
          },
          {
            user_id: 'kr_user_01',
            name: '민준',
            role: 'Collaborator',
            location: 'Seoul · 10:15',
            status: 'online',
            badge: '온라인'
          }
        ]
      }
      setRoom(nextRoom)

      if (msgRes.status === 'fulfilled' && msgRes.value.data) {
        const fetchedMsgs = (msgRes.value.data.messages || []).map(m => mapApiMessage(m, 'kr_user_01'))
        setMessages(fetchedMsgs)
        const unreadCount = fetchedMsgs.filter(m => m.sender === 'alex').length
        setAbsenceBanner({
          show: unreadCount > 0,
          text: `민준이 자는 동안 Alex가 메시지 ${unreadCount}개를 남겼습니다.`
        })
      }
    } catch {
      // API 연결 전 Fallback 유지
    }
  }

  useEffect(() => {
    if (!isAuthenticated) return
    loadData()
  }, [isAuthenticated])

  // 데모 리셋 (Seed & 가상 시계 초기화)
  const resetDemo = async () => {
    setPhase('waiting')
    setDigest(null)
    setInput('')
    setCheckedActions([])

    try {
      await seedDemo()
    } catch {
      // Fallback 처리
    }
    await loadData()
  }

  const changeLanguage = (nextLang) => {
    setLang(nextLang)
    if (digest) setDigest(COPY[nextLang])
  }

  // AI Relay 다이제스트 생성 (v2 GET 호출)
  const generateDigest = async () => {
    setPhase('analyzing')

    try {
      const response = await getRelayDigest('proj_landing_01')
      const nextDigest = mapApiDigest(response.data, COPY[lang])
      setDigest(nextDigest)
      setRoom((current) => ({
        ...current,
        workflow: {
          current_step: 3,
          progress_percent: nextDigest.workflowProgress ?? 75,
        },
      }))
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 800))
      setDigest(COPY[lang])
      setRoom((current) => ({ ...current, workflow: { current_step: 3, progress_percent: 75 } }))
    }

    setPhase('digest')
  }

  const applyReply = () => {
    setInput(digest.reply)
    setPhase('draft')
  }

  // 메시지 전송 (v2 POST /messages 호출 시 백엔드에서 다이제스트 is_read: true 처리)
  const sendReply = async () => {
    const replyContent = input.trim()
    if (!replyContent || isSending) return

    const isDigestReply = Boolean(digest) && ['digest', 'draft'].includes(phase)
    setIsSending(true)

    try {
      await sendMessage('proj_landing_01', replyContent)
      await loadData()
      setRoom((current) => ({ ...current, workflow: { current_step: 4, progress_percent: 100 } }))
    } catch {
      setMessages((current) => [
        ...current.map((message) => isDigestReply ? { ...message, unread: false } : message),
        {
          id: Date.now(),
          sender: 'babyLion',
          name: '민준 · Maker',
          text: replyContent,
          time: '지금',
        },
      ])
      if (isDigestReply) setRoom((current) => ({ ...current, workflow: { current_step: 4, progress_percent: 100 } }))
    } finally {
      setInput('')
      setIsSending(false)
    }

    if (isDigestReply) {
      setCheckedActions(digestActions.map((_, index) => index))
      setAbsenceBanner({ show: false, text: '' })
      setPhase('complete')
    }
  }

  const toggleAction = (index) => {
    setCheckedActions((current) =>
      current.includes(index) ? current.filter((item) => item !== index) : [...current, index],
    )
  }

  return (
    !isAuthenticated ? (
      <LoginView
        email={loginEmail}
        error={loginError}
        isLoading={isLoggingIn}
        onEmailChange={setLoginEmail}
        onSubmit={handleLogin}
      />
    ) : (
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
            <span>{screen === 'home' ? '내 협업' : selectedSecondaryProject?.title || room.project_title}</span>
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
            <div className="avatar" title="민준" aria-label="현재 사용자: 민준">🦁</div>
          </div>
        </div>
      </header>

      {screen === 'home' ? (
        <HomeView
          messages={messages}
          phase={phase}
          room={room}
          onOpenRoom={openRoom}
        />
      ) : selectedProjectId === 'landing' ? (
        <main className="workspace">
          <aside className="sidebar">
            <div className="progress-card">
              <div className="progress-heading">
                <span>현재 작업 흐름</span>
                <span>{progressPercent}%</span>
              </div>
              <div className="progress-track"><span style={{ width: `${progressPercent}%` }} /></div>
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
              {(room.participants || []).map((participant) => {
                const isBabyLion = participant.name === '민준' || participant.user_id === 'kr_user_01'
                const statusTone = participant.status === 'online' || participant.status === 'working' ? 'working' : 'sleep'
                return (
                  <div className="person-row" key={participant.user_id || participant.name}>
                    <div className={`mini-avatar ${isBabyLion ? 'blue' : 'violet'}`}>{isBabyLion ? '🦁' : participant.name?.[0]}</div>
                    <div><strong>{participant.name}</strong><span>{participant.location}</span></div>
                    <span className={`status-pill ${statusTone}`}>
                      {statusTone === 'working' ? <SunMedium size={11} /> : <MoonStar size={11} />}
                      {participant.badge}
                    </span>
                  </div>
                )
              })}
              <div className="timezone-note"><Globe2 size={14} /> {room.timezone_gap_text}</div>
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
                <h2>{room.project_title}</h2>
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
                  {messages.map((message) => (
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
                  {phase === 'waiting' && absenceBanner.show && (
                    <div className="gap-notice"><MoonStar size={15} /><span>{absenceBanner.text}</span></div>
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
                  placeholder="민준으로 메시지를 입력하세요…"
                  disabled={phase === 'analyzing' || isSending}
                  aria-label="메시지 입력"
                />
                <button onClick={sendReply} disabled={!input.trim() || phase === 'analyzing' || isSending} aria-label="메시지 전송"><Send size={17} /></button>
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
                  <span><Sparkles size={13} /> {digest.title}</span>
                  <p>{digest.subtitle}</p>
                </div>

                <div className="digest-grid">
                  <DigestCard tone="violet" label="진행 상황" icon="01" text={digest.summary} />
                  <DigestCard tone="teal" label="결정 사항" icon="02" text={digest.decisions} />
                  <DigestCard tone="amber" label="미결정 사항" icon="03" text={digest.pending} />
                  <DigestCard tone="blue" label="핵심 질문" icon="04" text={digest.question} />
                </div>

                <div className="action-block">
                  <div className="block-title"><span>Action items</span><small>{checkedActions.length}/{digestActions.length}</small></div>
                  {digestActions.map((action, index) => (
                    <button className={`action-row ${checkedActions.includes(index) ? 'checked' : ''}`} key={action.id} onClick={() => toggleAction(index)}>
                      <span className="check-box">{checkedActions.includes(index) && <Check size={12} />}</span>
                      <span>{action.text}</span>
                    </button>
                  ))}
                </div>

                {phase !== 'complete' && (
                  <div className="suggestion-block">
                    <div className="block-title"><span>추천 답변</span><small>{digest.replyTag}</small></div>
                    <p>“{digest.reply}”</p>
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
  )
}

function LoginView({ email, error, isLoading, onEmailChange, onSubmit }) {
  return (
    <main className="login-page">
      <div className="login-atmosphere" aria-hidden="true" />
      <section className="login-layout">
        <div className="login-intro">
          <button className="brand login-brand" type="button" aria-label="POOM">
            <span className="brand-mark">P</span>
            <span className="brand-word">POOM</span>
            <span className="brand-dot" />
          </button>
          <div className="login-copy">
            <span className="login-kicker">ASYNC COLLABORATION</span>
            <h1>시차를 넘어,<br /><em>협업의 흐름</em>을 이어가세요.</h1>
            <p>POOM이 잠든 사이 쌓인 메시지를 정리하고, 서로의 다음 순간을 연결해 드립니다.</p>
          </div>
          <div className="login-signal"><span /><span /><span /><small>AI Relay가 협업의 맥락을 지켜보고 있어요.</small></div>
        </div>

        <div className="login-card-wrap">
          <form className="login-card" onSubmit={onSubmit}>
            <div className="login-card-heading">
              <span className="login-icon"><Mail size={18} /></span>
              <p>WELCOME BACK</p>
              <h2>다시 만나요</h2>
              <span>POOM 계정으로 협업을 이어가세요.</span>
            </div>
            <label className="login-label" htmlFor="login-email">이메일 주소</label>
            <div className="login-input-wrap">
              <Mail size={16} aria-hidden="true" />
              <input
                id="login-email"
                type="email"
                value={email}
                onChange={(event) => onEmailChange(event.target.value)}
                placeholder="you@poom.dev"
                autoComplete="email"
                required
              />
            </div>
            {error && <p className="login-error" role="alert">{error}</p>}
            <button className="login-submit" type="submit" disabled={isLoading}>
              {isLoading ? <span className="spinner" /> : <><span>로그인하고 시작하기</span><ArrowRight size={17} /></>}
            </button>
            <p className="login-note">초대받은 이메일로 로그인하면 바로 협업 공간에 입장합니다.</p>
          </form>
          <div className="login-footer"><span>POOM workspace</span><span>SECURE ACCESS</span></div>
        </div>
      </section>
    </main>
  )
}

function HomeView({ messages, phase, room, onOpenRoom }) {
  const unreadCount = messages.filter((message) => message.unread).length
  const latestMessage = messages.at(-1)
  const landingPartner = room.participants?.find((participant) => participant.user_id === 'us_user_01') || { name: 'Alex' }
  const projects = [
    {
      id: 'landing',
      title: room.project_title,
      description: `${landingPartner.name}와 민준이 함께 진행 중인 협업방`,
      partner: { name: landingPartner.name, avatar: landingPartner.name?.[0] || 'A' },
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
        <span>2개의 작업</span>
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
  const partnerTone = 'violet'
  const statusTone = ''

  return (
    <button className="project-room-card" onClick={() => onOpenRoom(project.id)}>
      <div className="project-card-top">
        <span className={`active-project-pill ${statusTone}`}>{project.status}</span>
        <span className="last-active"><Clock3 size={13} /> {project.lastActive}</span>
      </div>
      <h2>{project.title}</h2>
      <p className="project-description">{project.description}</p>
      <div className="last-message">
        <span>{latest?.sender === 'babyLion' ? '민준' : project.partner.name}</span>
        <p>{latest?.text || '새로운 메시지가 없습니다.'}</p>
      </div>
      <div className="project-card-footer">
        <div className="participant-stack" aria-label={`참여자 ${project.partner.name}와 민준`}>
          <span className={partnerTone}>{project.partner.avatar}</span>
          <span className="blue">🦁</span>
        </div>
        <div className="project-card-status">
          {project.unread > 0 && <span className="unread-count">읽지 않음 {project.unread}</span>}
          {project.isComplete && <span className="caught-up"><Check size={12} /> 모두 확인</span>}
          {!project.unread && !project.isComplete && <span className="caught-up"><Check size={12} /> 모두 확인</span>}
          <ChevronRight size={18} />
        </div>
      </div>
    </button>
  )
}

function SimpleProjectRoom({ project, onBack }) {
  const [roomMessages, setRoomMessages] = useState(project.messages)
  const [draft, setDraft] = useState('')

  const handleSend = () => {
    if (!draft.trim()) return
    setRoomMessages((current) => [
      ...current,
      {
        id: Date.now(),
        sender: 'babyLion',
        name: '민준 · Maker',
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
            <div><strong>민준</strong><span>Seoul · 10:15</span></div>
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
          {roomMessages.map((message) => (
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
              <MoonStar size={15} />
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
                  handleSend()
                }
              }}
              placeholder="메시지를 입력하세요…"
              aria-label="메시지 입력"
            />
            <button onClick={handleSend} disabled={!draft.trim()} aria-label="메시지 전송"><Send size={17} /></button>
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