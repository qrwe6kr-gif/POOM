import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Moon, Sun, Sparkles, CheckCircle2, Send, Clock, User, 
  ArrowRight, MessageSquare, CheckSquare, Globe, Play, RotateCcw, Zap
} from 'lucide-react';

const API_BASE = "http://localhost:8000/api";

export default function App() {
  // Step 관리 (1 ~ 8)
  const [step, setStep] = useState(1);
  const [currentRole, setCurrentRole] = useState('minjun'); // 'minjun' | 'alex'
  const [lang, setLang] = useState('ko'); // 'ko' | 'en'
  const [loadingAI, setLoadingAI] = useState(false);
  const [actionAccepted, setActionAccepted] = useState(false);
  const [inputMessage, setInputMessage] = useState('');

  // 8단계 메시지 데이터
  const [messages, setMessages] = useState([]);

  // 다이제스트 데이터 (한국어 / 영어)
  const digestData = {
    ko: {
      summary: "랜딩페이지 메인 화면 제작 요청이 전달되었습니다.",
      decisions: "모바일 화면을 우선 제작하며, 메인 컬러는 파란색(#2563eb)입니다.",
      pending: "버튼 형태가 아직 결정되지 않았습니다.",
      key_questions: "버튼을 라운드형과 사각형 중 어떤 형태로 제작할까요?",
      action_items: ["모바일 메인 화면 시안 제작", "내일 오전까지 초안 전달"],
      suggested_reply: "요구사항을 확인했습니다. 모바일 화면을 먼저 제작하겠습니다. 버튼은 전체적인 디자인과 잘 어울리도록 라운드형을 제안합니다."
    },
    en: {
      summary: "Landing page UI design request has been received.",
      decisions: "Prioritize mobile view first; Primary brand color is set to Blue (#2563eb).",
      pending: "Button shape style is not yet confirmed.",
      key_questions: "Should the buttons be rounded corners or sharp rectangle style?",
      action_items: ["Create Mobile Main Screen draft", "Deliver initial draft by tomorrow morning"],
      suggested_reply: "Requirements confirmed. I will work on the mobile layout first and suggest rounded buttons for better visual harmony."
    }
  };

  const [activeDigest, setActiveDigest] = useState(null);

  // 플로우 초기화
  const handleReset = () => {
    setStep(1);
    setCurrentRole('minjun');
    setMessages([]);
    setActiveDigest(null);
    setActionAccepted(false);
    setInputMessage('');
  };

  // Step 3: 민준의 5대 작업 요청 전송
  const handleSendMinjunRequests = () => {
    setStep(3);
    const minjunMsgs = [
      { id: 1, sender: 'minjun', name: '민준 (개발자)', text: '메인 화면 시안을 만들어 주세요.', time: '23:00' },
      { id: 2, sender: 'minjun', name: '민준 (개발자)', text: '모바일 화면을 먼저 제작해 주세요.', time: '23:02' },
      { id: 3, sender: 'minjun', name: '민준 (개발자)', text: '메인 컬러는 파란색(#2563eb)으로 결정했습니다.', time: '23:05' },
      { id: 4, sender: 'minjun', name: '민준 (개발자)', text: '버튼은 라운드형과 사각형 중 어떤 것이 좋을까요?', time: '23:10' },
      { id: 5, sender: 'minjun', name: '민준 (개발자)', text: '내일 오전까지 초안을 부탁드립니다.', time: '23:15' }
    ];
    setMessages(minjunMsgs);
  };

  // Step 4 & 5 & 6: 3시간 무응답 후 Alex 복귀 및 AI Relay 생성
  const handleSimulateGapAndGenerate = async () => {
    setStep(5);
    setLoadingAI(true);
    setCurrentRole('alex');

    try {
      // 백엔드 OpenAI API 호출 시도
      const res = await axios.post(`${API_BASE}/relay-digest`, {
        chat_history: messages.map(m => m.text).join("\n"),
        target_lang: lang
      });
      setActiveDigest(res.data.digest || digestData[lang]);
    } catch (e) {
      // 백엔드 미구동 시 Fallback 데이터 사용
      setActiveDigest(digestData[lang]);
    } finally {
      setLoadingAI(false);
      setStep(6);
    }
  };

  // 언어 변경 시 다이제스트 번역 전환
  useEffect(() => {
    if (activeDigest) {
      setActiveDigest(digestData[lang]);
    }
  }, [lang]);

  // Step 7: 추천 답변 입력창에 적용
  const handleApplySuggestedReply = () => {
    if (activeDigest) {
      setInputMessage(activeDigest.suggested_reply);
      setStep(7);
    }
  };

  // Step 8: Alex 답변 전송 및 협업 재개
  const handleSendAlexReply = () => {
    if (!inputMessage.trim()) return;
    const alexMsg = {
      id: Date.now(),
      sender: 'alex',
      name: 'Alex (디자이너)',
      text: inputMessage,
      time: '03:52 AM (PST)'
    };
    setMessages(prev => [...prev, alexMsg]);
    setInputMessage('');
    setStep(8);
  };

  return (
    <div className="w-screen h-screen bg-slate-950 text-slate-100 flex flex-col font-sans overflow-hidden">
      
      {/* 1. Header (Navbar) */}
      <header className="h-16 border-b border-slate-800 px-6 flex items-center justify-between bg-slate-900/80 backdrop-blur">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center font-black text-white text-lg">P</div>
            <span className="text-xl font-black text-white tracking-tight">POOM</span>
          </div>
          <span className="text-xs bg-slate-800 text-slate-300 px-3 py-1 rounded-full border border-slate-700 font-medium">
            프로젝트: 랜딩페이지 UI 제작
          </span>
        </div>

        {/* 언어 선택 & 역할 전환 & 리셋 */}
        <div className="flex items-center gap-3">
          {/* 언어 토글 */}
          <div className="flex items-center bg-slate-800 rounded-lg p-0.5 border border-slate-700 text-xs">
            <button 
              onClick={() => setLang('ko')} 
              className={`px-2.5 py-1 rounded-md font-bold transition ${lang === 'ko' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white'}`}
            >
              KO
            </button>
            <button 
              onClick={() => setLang('en')} 
              className={`px-2.5 py-1 rounded-md font-bold transition ${lang === 'en' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white'}`}
            >
              EN
            </button>
          </div>

          {/* 현재 시점 역할 뱃지 */}
          <div className="flex items-center gap-1.5 bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700 text-xs font-semibold">
            <User size={14} className={currentRole === 'minjun' ? 'text-blue-400' : 'text-indigo-400'} />
            <span>현재 관점:</span>
            <span className={currentRole === 'minjun' ? 'text-blue-400 font-bold' : 'text-indigo-400 font-bold'}>
              {currentRole === 'minjun' ? '민준 (한국 개발자)' : 'Alex (미국 디자이너)'}
            </span>
          </div>

          <button 
            onClick={handleReset}
            title="초기화"
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition border border-slate-700"
          >
            <RotateCcw size={15} />
          </button>
        </div>
      </header>

      {/* 2. Main 2-Column Layout */}
      <div className="flex-1 flex overflow-hidden">
        
        {/* [Left Sidebar] Step 1, Step 2, Step 4 데모 컨트롤러 */}
        <aside className="w-84 border-r border-slate-800 bg-slate-900/40 p-5 flex flex-col justify-between overflow-y-auto">
          <div className="space-y-5">
            
            {/* Step 1: 프로젝트 메타 정보 */}
            <div>
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                📌 협업 개요
              </h3>
              <div className="bg-slate-900 border border-slate-800 p-3.5 rounded-xl space-y-2 text-xs">
                <div className="font-bold text-slate-200 text-sm">랜딩페이지 UI 제작</div>
                <div className="text-slate-400">🎯 <strong>작업 목표</strong>: 모바일 메인 화면 시안 제작</div>
                <div className="text-slate-400">📅 <strong>마감일</strong>: 내일 오전 10:00 (KST)</div>
                <div className="pt-2 border-t border-slate-800 flex justify-between text-[11px] text-slate-500">
                  <span>참여자: 민준, Alex</span>
                  <span className="text-emerald-400 font-medium">● 룸 활성화됨</span>
                </div>
              </div>
            </div>

            {/* Step 2: 상대방 타임존 및 업무 가능 상태 */}
            <div>
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                ⏰ 상대방 업무 상태 (Timezone)
              </h3>
              <div className="bg-slate-900 border border-slate-800 p-3.5 rounded-xl space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-300 font-bold">Alex (샌프란시스코, PST)</span>
                  <span className="bg-amber-500/10 text-amber-300 border border-amber-500/30 text-[10px] font-bold px-2 py-0.5 rounded">
                    비근무 시간
                  </span>
                </div>

                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400">
                    <Moon size={22} />
                  </div>
                  <div>
                    <div className="text-lg font-black text-slate-100 tracking-tight">03:45 AM (PST)</div>
                    <div className="text-[11px] text-slate-400 font-medium">다음 근무 시작까지 약 7시간 남음</div>
                  </div>
                </div>

                <div className="text-[11px] bg-slate-950 p-2.5 rounded-lg border border-slate-800 text-slate-400 space-y-1">
                  <div className="flex justify-between">
                    <span>최근 접속:</span>
                    <span className="text-slate-300 font-medium">4시간 전 (자리 비움)</span>
                  </div>
                  <div className="flex justify-between">
                    <span>시차:</span>
                    <span className="text-slate-300 font-medium">16시간 (비동기 협업 모드)</span>
                  </div>
                </div>
              </div>
            </div>

          </div>

          {/* 시연 데모 시나리오 컨트롤러 */}
          <div className="pt-4 border-t border-slate-800 space-y-2">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
              ⚡ 시연 플로우 원클릭 실행
            </span>

            {step < 3 && (
              <button
                onClick={handleSendMinjunRequests}
                className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-2.5 px-3 rounded-xl text-xs flex items-center justify-center gap-2 shadow-lg shadow-blue-600/20 transition"
              >
                <Send size={14} /> Step 3. 민준 작업 요청 전송 (5건)
              </button>
            )}

            {step >= 3 && step < 6 && (
              <button
                onClick={handleSimulateGapAndGenerate}
                disabled={loadingAI}
                className="w-full bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white font-bold py-2.5 px-3 rounded-xl text-xs flex items-center justify-center gap-2 shadow-lg shadow-orange-500/20 transition"
              >
                <Sparkles size={14} /> 
                {loadingAI ? 'AI Relay 분석 생성 중...' : 'Step 4~5. 3시간 경과 & Alex 복귀'}
              </button>
            )}

            {step >= 6 && (
              <div className="bg-emerald-950/40 border border-emerald-800/40 p-2.5 rounded-xl text-center">
                <span className="text-emerald-400 text-xs font-bold flex items-center justify-center gap-1">
                  <CheckCircle2 size={13} /> 8단계 플로우 진행 완료
                </span>
              </div>
            )}
          </div>
        </aside>

        {/* [Right Main Panel] AI Relay Digest & Full Chat Stream */}
        <main className="flex-1 flex flex-col bg-slate-950 overflow-hidden">
          
          {/* Step 6 & 7 & 8: AI Relay Digest Card (상단 배너 카드) */}
          {activeDigest && (
            <section className={`border-b transition-all duration-300 p-5 ${
              step >= 8 ? 'bg-slate-900/60 border-slate-800' : 'bg-slate-900 border-blue-900/40 shadow-2xl'
            }`}>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="p-1 rounded-md bg-blue-600/20 text-blue-400 border border-blue-500/30">
                    <Sparkles size={16} />
                  </div>
                  <h2 className="text-sm font-bold text-slate-100">
                    POOM SyncRelay AI Digest
                    <span className="ml-2 text-xs font-normal text-slate-400">
                      ({lang === 'ko' ? 'Alex를 위한 복귀 맞춤 브리핑' : 'Context briefing for Alex'})
                    </span>
                  </h2>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-[11px] bg-slate-800 text-slate-400 px-2.5 py-0.5 rounded border border-slate-700">
                    부재 중 누적 메시지 5건 분석됨
                  </span>
                  {step >= 8 && (
                    <span className="text-[11px] bg-emerald-950 text-emerald-300 px-2.5 py-0.5 rounded border border-emerald-800 font-semibold">
                      ✓ 확인 및 회신 완료
                    </span>
                  )}
                </div>
              </div>

              {/* 4분할 브리핑 카드 그리드 */}
              <div className="grid grid-cols-4 gap-3 text-xs mb-3">
                <div className="bg-slate-950/70 border border-slate-800/80 p-3 rounded-xl">
                  <span className="text-blue-400 font-bold block mb-1">📌 {lang === 'ko' ? '진행 상황' : 'Summary'}</span>
                  <p className="text-slate-300 leading-relaxed text-[11px]">{activeDigest.summary}</p>
                </div>
                <div className="bg-emerald-950/20 border border-emerald-900/40 p-3 rounded-xl">
                  <span className="text-emerald-400 font-bold block mb-1">✅ {lang === 'ko' ? '결정된 사항' : 'Decisions'}</span>
                  <p className="text-slate-300 leading-relaxed text-[11px]">{activeDigest.decisions}</p>
                </div>
                <div className="bg-amber-950/20 border border-amber-900/40 p-3 rounded-xl">
                  <span className="text-amber-400 font-bold block mb-1">⏳ {lang === 'ko' ? '미결정 사항' : 'Pending'}</span>
                  <p className="text-slate-300 leading-relaxed text-[11px]">{activeDigest.pending}</p>
                </div>
                <div className="bg-rose-950/20 border border-rose-900/40 p-3 rounded-xl">
                  <span className="text-rose-400 font-bold block mb-1">❓ {lang === 'ko' ? '핵심 질문' : 'Key Question'}</span>
                  <p className="text-slate-300 leading-relaxed text-[11px]">{activeDigest.key_questions}</p>
                </div>
              </div>

              {/* Step 7: Action Item 체크 & 추천 답변 바로 적용 바 */}
              <div className="flex items-center justify-between bg-slate-950/90 border border-slate-800 p-2.5 rounded-xl text-xs">
                <div className="flex items-center gap-3">
                  <span className="font-bold text-slate-300 flex items-center gap-1.5">
                    <CheckSquare size={15} className="text-blue-400" /> Action Items:
                  </span>
                  {activeDigest.action_items.map((item, idx) => (
                    <label key={idx} className="flex items-center gap-1.5 text-slate-300 cursor-pointer bg-slate-900 px-2.5 py-1 rounded border border-slate-800 hover:border-slate-700">
                      <input 
                        type="checkbox" 
                        checked={actionAccepted} 
                        onChange={(e) => setActionAccepted(e.target.checked)} 
                        className="rounded accent-blue-600"
                      />
                      <span className={actionAccepted ? 'line-through text-slate-500' : ''}>{item}</span>
                    </label>
                  ))}
                </div>

                {step < 8 && (
                  <button
                    onClick={handleApplySuggestedReply}
                    className="bg-blue-600 hover:bg-blue-500 text-white font-bold px-3.5 py-1.5 rounded-lg text-xs flex items-center gap-1.5 transition shadow"
                  >
                    💬 {lang === 'ko' ? '추천 답변 입력창에 적용' : 'Apply Suggested Reply'}
                  </button>
                )}
              </div>
            </section>
          )}

          {/* Chat Stream (Step 3, 8 누적 대화) */}
          <div className="flex-1 p-6 overflow-y-auto space-y-4">
            {messages.length === 0 && (
              <div className="h-full flex flex-col items-center justify-center text-slate-500 text-xs">
                <MessageSquare size={32} className="mb-2 opacity-40" />
                <p>협업방에 입장했습니다. 좌측 [Step 3. 민준 작업 요청 전송]을 클릭해 협업을 시작하세요.</p>
              </div>
            )}

            {messages.map((m) => {
              const isMinjun = m.sender === 'minjun';
              return (
                <div key={m.id} className={`flex flex-col ${isMinjun ? 'items-start' : 'items-end'}`}>
                  <span className="text-[11px] text-slate-400 mb-1 px-1">{m.name}</span>
                  <div
                    className={`max-w-xl px-4 py-2.5 rounded-2xl text-xs leading-relaxed shadow ${
                      isMinjun 
                        ? 'bg-slate-900 text-slate-200 border border-slate-800 rounded-tl-none' 
                        : 'bg-blue-600 text-white rounded-tr-none font-medium'
                    }`}
                  >
                    {m.text}
                  </div>
                  <span className="text-[10px] text-slate-600 mt-1 px-1">{m.time}</span>
                </div>
              );
            })}
          </div>

          {/* Chat Input Bar (Step 7, 8) */}
          <div className="p-4 border-t border-slate-800 bg-slate-900/80">
            <div className="flex gap-3">
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSendAlexReply()}
                placeholder={
                  currentRole === 'minjun' 
                    ? "민준으로서 작업 요청 및 메시지를 입력하세요..." 
                    : "Alex로서 피드백 또는 수정된 답변을 입력하세요..."
                }
                className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500"
              />
              <button
                onClick={handleSendAlexReply}
                className="bg-blue-600 hover:bg-blue-500 text-white px-5 py-2.5 rounded-xl font-bold text-xs flex items-center gap-1.5 transition"
              >
                <Send size={14} /> 전송
              </button>
            </div>
          </div>

        </main>
      </div>

    </div>
  );
}