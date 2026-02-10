/**
 * LangGraph API Client
 *
 * LangGraph Server 와 통신하는 클라이언트.
 * 기본 포트: 2024 (langgraph dev 기본값)
 */

const BASE_URL = import.meta.env.VITE_LANGGRAPH_API_URL || '';

class LangGraphClient {
  constructor(baseUrl = BASE_URL) {
    this.baseUrl = baseUrl;
    this.graphId = 'agent';
  }

  async _fetch(path, options = {}) {
    const url = `${this.baseUrl}${path}`;
    const res = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!res.ok) {
      const body = await res.text();
      throw new Error(`LangGraph API error ${res.status}: ${body}`);
    }

    return res;
  }

  async _json(path, options = {}) {
    const res = await this._fetch(path, options);
    return res.json();
  }

  // ─── Thread 관리 ───────────────────────────────────────

  /** 새 Thread 생성 */
  async createThread() {
    return this._json('/threads', { method: 'POST', body: JSON.stringify({}) });
  }

  /** Thread 상태 조회 */
  async getThreadState(threadId) {
    return this._json(`/threads/${threadId}/state`);
  }

  /** Thread 상태 업데이트 (Human-in-the-loop 응답 등) */
  async updateThreadState(threadId, values, asNode = null) {
    const body = { values };
    if (asNode) body.as_node = asNode;
    return this._json(`/threads/${threadId}/state`, {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  // ─── Run 실행 ──────────────────────────────────────────

  /** Run 생성 (비동기) */
  async createRun(threadId, input, config = {}) {
    return this._json(`/threads/${threadId}/runs`, {
      method: 'POST',
      body: JSON.stringify({
        assistant_id: this.graphId,
        input,
        config,
      }),
    });
  }

  /** Run 스트리밍 — SSE 로 이벤트를 받아 콜백 호출 */
  async streamRun(threadId, input, { onEvent, onError, onComplete, config = {}, command = null } = {}) {
    const url = `${this.baseUrl}/threads/${threadId}/runs/stream`;
    const body = {
      assistant_id: this.graphId,
      input,
      config,
      stream_mode: ['updates'],
    };
    if (command) body.command = command;

    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`Stream error ${res.status}: ${text}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        let eventType = null;
        for (const line of lines) {
          if (line.startsWith('event:')) {
            eventType = line.slice(6).trim();
          } else if (line.startsWith('data:') && eventType) {
            try {
              const data = JSON.parse(line.slice(5).trim());
              onEvent?.({ event: eventType, data });
            } catch {
              // non-JSON data line, skip
            }
            eventType = null;
          }
        }
      }

      onComplete?.();
    } catch (err) {
      onError?.(err);
    }
  }

  /** Interrupt 후 resume (Human-in-the-loop approve) */
  async resumeRun(threadId, { onEvent, onError, onComplete, config = {}, command = null } = {}) {
    return this.streamRun(threadId, null, { onEvent, onError, onComplete, config, command });
  }

  // ─── Human-in-the-loop ─────────────────────────────────

  /** Tool call 승인 — Command resume */
  async approveToolCall(threadId, { onEvent, onError, onComplete, config = {} } = {}) {
    return this.resumeRun(threadId, {
      onEvent,
      onError,
      onComplete,
      config,
      command: { resume: true },
    });
  }

  /** Tool call 거부 — state 에 reject 메시지 추가 후 resume */
  async rejectToolCall(threadId, reason = '사용자가 거부했습니다.') {
    // ToolMessage 로 reject 응답을 보냄
    await this.updateThreadState(threadId, {
      messages: [{
        role: 'tool',
        content: `REJECTED: ${reason}`,
        tool_call_id: '__reject__',
      }],
    });
  }

  /** Tool call 파라미터 수정 후 resume */
  async editToolCall(threadId, toolCallId, newArgs) {
    const state = await this.getThreadState(threadId);
    // 마지막 AI 메시지의 tool_calls 에서 해당 ID 찾아 수정
    const messages = state.values?.messages || [];
    const lastAiMsg = [...messages].reverse().find(m => m.role === 'assistant' && m.tool_calls?.length);

    if (lastAiMsg) {
      const tc = lastAiMsg.tool_calls.find(tc => tc.id === toolCallId);
      if (tc) {
        tc.args = newArgs;
      }
      await this.updateThreadState(threadId, { messages: [lastAiMsg] });
    }
  }

  // ─── 유틸리티 ──────────────────────────────────────────

  /** 서버 상태 확인 */
  async healthCheck() {
    try {
      await this._fetch('/ok');
      return true;
    } catch {
      return false;
    }
  }

  /** Assistants 목록 */
  async listAssistants() {
    return this._json('/assistants/search', {
      method: 'POST',
      body: JSON.stringify({}),
    });
  }
}

export const client = new LangGraphClient();
export default LangGraphClient;
