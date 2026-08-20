import api from './client';

// 1. 로그인
export const login = (email) => api.post('/auth/login', { email });

// 2. 프로젝트 방 상세 (헤더/목표/참여자)
export const getProjectDetail = (projectId = 'proj_landing_01') =>
  api.get(`/projects/${projectId}`);

// 3. 사용자 상태 조회 (수면/근무/타임존)
export const getUserStatus = (userId) =>
  api.get(`/users/${userId}/status`);

// 4. 메시지 목록 조회 (폴링)
export const getMessages = (projectId = 'proj_landing_01') =>
  api.get(`/projects/${projectId}/messages`);

// 5. 메시지 전송 (전송 시 백엔드에서 다이제스트 is_read: true 처리)
export const sendMessage = (projectId = 'proj_landing_01', text) =>
  api.post(`/projects/${projectId}/messages`, { body: text });

// 6. 다이제스트 조회 및 지연 평가 생성
export const getRelayDigest = (projectId = 'proj_landing_01') =>
  api.get(`/projects/${projectId}/relay-digest`);

// 7. [데모 시연용] 시드 초기화 및 가상 시간 전진
export const seedDemo = () => api.post('/demo/seed');
export const setDemoTime = (userIds, nowIsoString) =>
  api.post('/demo/time', { user_ids: userIds, now: nowIsoString });