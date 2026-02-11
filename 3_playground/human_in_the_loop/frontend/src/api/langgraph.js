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

  // ─── Run 실행 ──────────────────────────────────────────

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

  /** Interrupt 후 resume (Human-in-the-loop) */
  async resumeRun(threadId, { onEvent, onError, onComplete, config = {}, command = null } = {}) {
    return this.streamRun(threadId, null, { onEvent, onError, onComplete, config, command });
  }

  // ─── Human-in-the-loop ─────────────────────────────────

  /** Tool call 승인 — Command resume with approve */
  async approveToolCall(threadId, callbacks = {}) {
    return this.resumeRun(threadId, {
      ...callbacks,
      command: { resume: { type: 'approve' } },
    });
  }

  /** Tool call 거부 — Command resume with reject */
  async rejectToolCall(threadId, reason = '사용자가 거부했습니다.', callbacks = {}) {
    return this.resumeRun(threadId, {
      ...callbacks,
      command: { resume: { type: 'reject', message: reason } },
    });
  }

  /** Tool call 파라미터 수정 후 resume */
  async editToolCall(threadId, newArgs, callbacks = {}) {
    return this.resumeRun(threadId, {
      ...callbacks,
      command: { resume: { type: 'edit', args: newArgs } },
    });
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
