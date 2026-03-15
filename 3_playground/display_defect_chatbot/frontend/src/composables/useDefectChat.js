// frontend/src/composables/useDefectChat.js
// 이 파일은 조합(composition)만 담당합니다.
// 각 기능의 구현은 아래 파일들을 참조하세요:
//   - useUserEmail.js     : 이메일 설정
//   - useChatMessages.js  : 채팅 메시지 배열
//   - useAnalysisFlow.js  : 분析 흐름, 에이전트, 폴링
//   - useSessionManager.js: 세션 CRUD, 저장/불러오기
import { useUserEmail }      from './useUserEmail.js'
import { useChatMessages }   from './useChatMessages.js'
import { useAnalysisFlow, AGENT_CONFIG } from './useAnalysisFlow.js'
import { useSessionManager } from './useSessionManager.js'

export { AGENT_CONFIG }

export function useDefectChat() {
  const email    = useUserEmail()
  const chat     = useChatMessages()
  const analysis = useAnalysisFlow(chat, email)
  const session  = useSessionManager(analysis, chat)

  // polling 완료 시 자동 저장 콜백 주입
  analysis._setSaveCallback(session.saveCurrentSession)

  // Auto-save 래퍼: 원본 useDefectChat.js의 saveCurrentSession 호출 시점 재현
  // startAnalysis: (1) 즉시 카드 생성, (2) API 완료 후 hypotheses 저장
  const startAnalysis = async () => {
    await session.saveCurrentSession()
    await analysis.startAnalysis()
    await session.saveCurrentSession()
  }

  const selectHypothesis = async (h) => {
    await analysis.selectHypothesis(h)
    await session.saveCurrentSession()
  }

  const goBackToHypotheses = async () => {
    await analysis.goBackToHypotheses()
    await session.saveCurrentSession()
  }

  const runAgents = async () => {
    await analysis.runAgents()
    await session.saveCurrentSession()
  }

  // _updateMessage는 내부 전용이므로 루트 반환값에서 제외한다.
  // eslint-disable-next-line no-unused-vars
  const { _updateMessage, ...chatPublic } = chat

  return {
    ...email,
    ...chatPublic,
    ...analysis,
    ...session,
    // auto-save 래퍼로 덮어쓰기
    startAnalysis,
    selectHypothesis,
    goBackToHypotheses,
    runAgents,
    reset: session.newAnalysis,  // 하위 호환 alias
  }
}
