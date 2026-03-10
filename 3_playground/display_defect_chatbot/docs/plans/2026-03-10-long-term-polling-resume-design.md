# Design: 장기 이력 폴링 재개 (세션 복원 시)

## 배경

사용자가 장기 이력(long_term) 에이전트가 PENDING 상태일 때 화면을 이탈하면 폴링이 끊긴다.
세션 복원 시 자동으로 폴링을 재개해야 한다.

## 핵심 제약

- **세션 간 명확한 구분**: 폴링은 반드시 현재 로드된 세션의 taskId에만 동작해야 한다.
  - 다른 세션 복원 시 기존 폴링 즉시 중단
  - pollTimer는 항상 단 하나만 존재
- 변경 파일: `frontend/src/composables/useDefectChat.js` 단일 파일

## 접근법: A + C 조합

- **A**: `longTermTaskId`를 localStorage에 저장 → 세션 복원 시 taskId를 알 수 있음
- **C**: 복원 직후 즉시 1회 status 체크 → 이미 완료된 경우 즉시 처리, 여전히 PENDING이면 인터벌 시작

## 변경 설계

### 1. state 추가

```js
const longTermTaskId = ref(null)
```

### 2. runAgents() — taskId 저장

```js
if (data.longTermTaskId) {
  longTermTaskId.value = data.longTermTaskId  // ← 신규
  pollBgStatus(data.longTermTaskId)
}
```

### 3. saveCurrentSession() — taskId 포함

```js
const record = {
  ...
  longTermTaskId: longTermTaskId.value,  // ← 신규
  longTermStatus: longTermStatus.value,
  longTermResult: longTermResult.value,
}
```

### 4. loadSession() — taskId 복원 + 세션 구분 후 폴링 재개

```js
function loadSession(session) {
  // 다른 세션 로드 시 기존 폴링 즉시 중단 (세션 구분 핵심)
  if (pollTimer.value) { clearInterval(pollTimer.value); pollTimer.value = null }

  activeSessionId.value = session.id
  sessionId.value = session.id
  form.productId = session.productId
  form.defectDescription = session.defectDescription
  selectedHypothesis.value = session.hypothesis
  chatMessages.value = session.chatMessages || []
  Object.assign(agentResults, session.agentResults)
  if (session.enabledAgents) Object.assign(enabledAgents, session.enabledAgents)
  longTermTaskId.value = session.longTermTaskId || null   // ← 신규
  longTermStatus.value = session.longTermStatus || 'PENDING'
  longTermResult.value = session.longTermResult || null
  step.value = 'result'

  // PENDING + taskId 있으면 즉시 체크 후 필요 시 인터벌 (C)
  if (longTermTaskId.value && longTermStatus.value === 'PENDING') {
    resumePollBgStatus(longTermTaskId.value)
  }
}
```

### 5. resumePollBgStatus() 신규 함수

역할:
- long_term 메시지 카드가 없으면 loading 카드 추가 (UI 복원)
- 즉시 1회 `checkAndHandleBgStatus()` 호출
- 여전히 PENDING이면 `pollBgStatus()` 인터벌 시작

```js
async function resumePollBgStatus(taskId) {
  // 메시지 카드 없으면 loading 추가
  const hasCard = chatMessages.value.some(m => m.agentKey === 'long_term')
  if (!hasCard) {
    chatMessages.value.push({ id: uuidv4(), agentKey: 'long_term', status: 'loading', result: null })
  }
  // 즉시 1회 체크 (이미 완료됐을 수도 있으므로)
  await checkAndHandleBgStatus(taskId)
  // 아직 PENDING이면 인터벌
  if (longTermStatus.value === 'PENDING') {
    pollBgStatus(taskId)
  }
}
```

### 6. checkAndHandleBgStatus() 공통 처리 함수 추출

`pollBgStatus()` 내부 로직을 분리해 재사용:

```js
async function checkAndHandleBgStatus(taskId) {
  const data = await getBgStatus(taskId)
  longTermStatus.value = data.status

  if (data.status === 'COMPLETED' || data.status === 'FAILED') {
    if (pollTimer.value) { clearInterval(pollTimer.value); pollTimer.value = null }
    longTermResult.value = data.resultText

    if (data.status === 'COMPLETED') {
      const response = await callAgent({
        sessionId: sessionId.value,
        action: 'resume_long_term',
        longTermResult: data.resultText || '',
      })
      const r = { suspectRows: [], analysis: data.resultText || '' }
      agentResults['long_term'] = r
      _updateMessage('long_term', 'done', r)
      finalActionPlan.value = response.finalActionPlan || ''
    } else {
      _updateMessage('long_term', 'error', null)
    }
    saveCurrentSession()
  }
}
```

### 7. pollBgStatus() 리팩터 — checkAndHandleBgStatus 재사용

```js
function pollBgStatus(taskId) {
  pollTimer.value = setInterval(async () => {
    try {
      await checkAndHandleBgStatus(taskId)
    } catch (e) {
      clearInterval(pollTimer.value); pollTimer.value = null
    }
  }, 3000)
}
```

### 8. newAnalysis() — longTermTaskId 초기화

```js
function newAnalysis() {
  if (pollTimer.value) { clearInterval(pollTimer.value); pollTimer.value = null }
  longTermTaskId.value = null   // ← 신규
  ...
}
```

## 세션 구분 보장 흐름

```
[세션 A 로드] loadSession(A)
  → clearInterval(pollTimer)  ← 이전 세션(B 등) 폴링 즉시 중단
  → sessionId = A.id
  → A.longTermTaskId가 PENDING → resumePollBgStatus(A_taskId)
    → checkAndHandleBgStatus(A_taskId)  ← A 세션의 task만 체크
    → pollBgStatus(A_taskId) 인터벌 시작
      → callAgent({ sessionId: A.id, ... })  ← A 세션 그래프 resume
```

## 변경 범위

- `frontend/src/composables/useDefectChat.js` 만 수정
- 신규 함수 2개: `resumePollBgStatus`, `checkAndHandleBgStatus`
- 기존 `pollBgStatus` 로직 위임으로 단순화
