const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '');
const TEAM_CONVERSATION_ID = 'planet-demo';

async function request(path, options = {}, retrySession = true) {
  let response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  } catch {
    throw new Error('FastAPI 서버에 연결할 수 없습니다. 백엔드가 실행 중인지 확인해 주세요.');
  }

  if (response.status === 401 && retrySession && path !== '/auth/session') {
    await ensureSession();
    return request(path, options, false);
  }

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(data?.detail || `서버 요청에 실패했습니다. (${response.status})`);
  }
  return data;
}

export function ensureSession() {
  return request('/auth/session', { method: 'POST' }, false);
}

export function getProfile() {
  return request('/profile');
}

export function saveProfile({ employeeName, hireDate, team }) {
  return request('/profile', {
    method: 'PUT',
    body: JSON.stringify({ employee_name: employeeName, hire_date: hireDate, team }),
  });
}

export function resetProfile() {
  return request('/profile', { method: 'DELETE' });
}

export async function askLauraStream(
  { message, team, conversationId = TEAM_CONVERSATION_ID },
  onDelta,
  onStatus = () => {},
) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}/chat/stream`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, team, conversation_id: conversationId }),
    });
  } catch {
    throw new Error('FastAPI 서버에 연결할 수 없습니다. 백엔드가 실행 중인지 확인해 주세요.');
  }

  if (response.status === 401) {
    await ensureSession();
    return askLauraStream({ message, team, conversationId }, onDelta, onStatus);
  }
  if (!response.ok || !response.body) {
    const data = await response.json().catch(() => null);
    throw new Error(data?.detail || `서버 요청에 실패했습니다. (${response.status})`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let finalResponse = null;

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
    const events = buffer.split('\n\n');
    buffer = events.pop() || '';

    events.forEach((block) => {
      const event = block.match(/^event: (.+)$/m)?.[1];
      const data = block.match(/^data: (.+)$/m)?.[1];
      if (!event || !data) return;
      const parsed = JSON.parse(data);
      if (event === 'delta') onDelta(parsed.delta);
      if (event === 'status') onStatus(parsed);
      if (event === 'done') finalResponse = parsed;
    });
    if (done) break;
  }

  if (!finalResponse) throw new Error('로라의 답변이 중간에 끊겼습니다.');
  return finalResponse;
}

export function executeAgentAction(actionId) {
  return request(`/actions/${encodeURIComponent(actionId)}/execute`, {
    method: 'POST',
    body: JSON.stringify({ confirmed: true }),
  });
}

export function declineAgentAction(actionId) {
  return request(`/actions/${encodeURIComponent(actionId)}/decline`, {
    method: 'POST',
  });
}

export function getConversation(team, conversationId = TEAM_CONVERSATION_ID) {
  return request(`/conversations/${encodeURIComponent(conversationId)}?team=${encodeURIComponent(team)}`);
}

export function getTeamMessages(team) {
  return request(`/team-chats/${encodeURIComponent(team)}/messages`);
}

export function sendTeamMessage(team, content) {
  return request(`/team-chats/${encodeURIComponent(team)}/messages`, {
    method: 'POST',
    body: JSON.stringify({ content }),
  });
}

export function disconnectGoogleCalendar() {
  return request('/integrations/google-calendar', { method: 'DELETE' });
}
