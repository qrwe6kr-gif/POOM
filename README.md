# 🤝 POOM (품) - 시차를 극복하는 AI 릴레이 협업 플랫폼

> **글로벌 원격 근무 환경에서 시차로 인한 커뮤니케이션 공백을 해소하고 끊김 없는 업무 릴레이를 지원하는 협업 솔루션**

---

## 📌 프로젝트 개요 (Overview)
글로벌 분업 환경에서는 시차(Time Zone Difference)로 인해 의사결정이 지연되고 작업 인수인계에 병목 현상이 발생합니다.  
**POOM**은 팀원이 자리를 비운 사이 쌓인 대화를 **POOM AI Relay Digest**를 통해 핵심 위주로 압축 브리핑하고, 다음 작업자가 즉시 업무를 이어받을 수 있도록 액션 아이템과 추천 답변을 제공하여 끊김 없는 업무 흐름을 완성합니다.

---

## ✨ 핵심 기능 (Key Features)

* **AI Relay Digest (4분할 브리핑)**: 부재 중 쌓인 대화를 분석하여 **진행 상황, 결정 사항, 미결정 사항, 핵심 질문**으로 구조화된 요약 제공
* **Smart Action Items**: 대화 내에서 즉시 처리해야 할 업무(To-Do)를 자동 추출 및 인터랙티브 체크리스트 생성
* **One-Click Suggested Reply (협업 재개)**: 컨텍스트를 반영한 최적의 회신 문구를 AI가 자동 제안하여 클릭 한 번으로 인수인계 완료
* **실시간 시차 & 다국어 지원**: 협업 상대방의 현지 시간 및 온/오프라인 상태 시각화, 실시간 다국어(KO / EN) 원클릭 전환 지원

---

## 🛠 기술 스택 (Tech Stack)

| 영역 | 기술 스택 | 주요 역할 |
| :--- | :--- | :--- |
| **Frontend** | React, Vite, Tailwind CSS, Lucide React | 반응형 UI/UX, 실시간 다이제스트 뷰 및 상호작용 구현 |
| **Backend** | Python, FastAPI, Uvicorn, Pydantic | 비동기 API 서버 구축, RESTful 엔드포인트 및 CORS 연동 |
| **AI / NLP** | Prompt Engineering, LLM Pipeline | 대화 컨텍스트 분석, 4분할 브리핑 및 액션 아이템 자동 추출 |

---

## 📂 프로젝트 구조 (Directory Structure)

```text
POOM/
├── POOM_team_package/
│   └── poom-backend/       # FastAPI 백엔드 서버 및 API 엔드포인트
│       ├── app/
│       │   └── main.py     # 백엔드 라우트 및 비즈니스 로직
│       └── requirements.txt
└── poom-frontend/          # React 프론트엔드 애플리케이션
    ├── src/
    │   ├── App.jsx         # 메인 UI 컴포넌트 및 API 통신
    │   └── index.css       # 스타일시트
    └── package.json

```
## 🚀 빠른 시작 (Getting Started)

로컬 환경 구동을 위해 백엔드와 프론트엔드 터미널을 각각 실행합니다.

**1. Backend 실행 (Port 8000)**
```bash
cd POOM_team_package/poom-backend
pip install fastapi uvicorn pydantic
uvicorn app.main:app --reload --port 8000
```
2. Frontend 실행 (Port 5173)
```bash
cd poom-frontend
npm install
npm run dev
```
두 서버 실행 후 브라우저에서 http://localhost:5173/ 로 접속하여 시연을 진행합니다.
