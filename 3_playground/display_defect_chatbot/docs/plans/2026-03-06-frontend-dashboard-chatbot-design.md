# Frontend Redesign: Dashboard + Chatbot UI

Date: 2026-03-06

## Overview

Split-layout dashboard 형태로 전면 재설계.
- 왼쪽: 분석 이력 CRD 패널 (로컬스토리지 영속)
- 오른쪽: 기존 단계 흐름 + 에이전트 결과 챗봇 스트림

## Layout

```
┌─────────────────┬────────────────────────────────────┐
│  LeftPanel      │  RightPanel                        │
│  (280px 고정)   │  (flex: 1)                         │
│                 │                                    │
│  분석 이력      │  [상단] 단계별 흐름                │
│  세션 카드 목록 │  InputView / HypothesisSelector    │
│                 │  / AgentSelector                   │
│  [+ 새 분석]    │  [하단] ChatStream                 │
│                 │  에이전트 결과 말풍선 스트림        │
└─────────────────┴────────────────────────────────────┘
```

## Components

### 신규 컴포넌트
- `LeftPanel.vue`: 분석 이력 목록 + CRD 조작
- `ChatStream.vue`: 에이전트 결과를 말풍선 형태로 순차 표시

### 기존 컴포넌트 (재사용)
- `InputView.vue`: 불량 입력 폼 (스타일 소폭 조정)
- `HypothesisSelector.vue`: 가설 선택
- `AgentSelector.vue`: 에이전트 ON/OFF 토글
- AG Grid: ChatStream 내 의심 데이터 테이블 재사용

### 수정 컴포넌트
- `App.vue`: flex row 레이아웃으로 변경, LeftPanel + RightPanel 구성
- `useDefectChat.js`: sessions 상태 + 로컬스토리지 동기화 추가

## Left Panel — CRD 상세

### Create
- 에이전트 실행 완료 시 자동으로 세션 저장
- 세션 데이터: `{ id, productId, defectDescription, hypothesis, timestamp, agentResults }`

### Read
- 세션 카드 목록 표시: productId, defectDescription 앞 30자, 실행 에이전트 아이콘, 날짜
- 카드 클릭 시 해당 세션 결과를 ChatStream에 복원

### Delete
- 카드 우측 🗑 버튼으로 해당 세션 삭제
- `localStorage` 에서도 동기화 삭제

## Right Panel — ChatStream 상세

### 메시지 흐름
1. 에이전트 실행 시작 → 로딩 말풍선 즉시 추가 (spinner)
2. 결과 수신 → 로딩 말풍선을 결과 카드로 교체
3. 모든 에이전트 완료 → 세션 자동 저장 → 왼쪽 이력에 카드 추가

### 메시지 구조
```js
{
  agentKey: 'process_history' | 'return_history' | 'test_result' | 'long_term',
  status: 'loading' | 'done' | 'error',
  result: null | { analysis: string, suspectRows: [] }
}
```

### 말풍선 UI
- 에이전트 아이콘 + 이름 헤더
- 로딩 중: spinner + "분석 중..." 텍스트
- 완료: 분석 텍스트 + AG Grid 테이블 (suspectRows 있을 때)
- 에러: 빨간 테두리 + 에러 메시지

## State Management

### useDefectChat.js 추가 상태
```js
const sessions = ref([])         // 세션 이력 배열
const activeSessionId = ref(null) // 현재 선택된 세션 ID
const chatMessages = ref([])      // 현재 ChatStream 메시지 배열
```

### 로컬스토리지 동기화
```js
// 초기화 시 로드
const saved = localStorage.getItem('defect_sessions')
if (saved) sessions.value = JSON.parse(saved)

// 세션 변경 시 저장 (watch)
watch(sessions, (val) => {
  localStorage.setItem('defect_sessions', JSON.stringify(val))
}, { deep: true })
```

## Design Tokens (다크 테마 유지)

기존 다크 테마 색상 체계 유지:
- 배경: `#0f1117`
- 패널: `#1a1d27`
- 테두리: `#2a2d3a`
- 강조: `#60a5fa` (파란계열)
- 성공: `#4ade80`, 실패: `#f87171`, 경고: `#fbbf24`

## Out of Scope

- 백엔드 API 변경 없음
- 다른 기기 간 세션 공유 없음 (로컬스토리지 한정)
- 실시간 스트리밍 (SSE/WebSocket) 없음 — 기존 폴링 방식 유지
