import { ref } from 'vue'

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

export function useDemoMode(messages, isLoading, pendingApproval) {
  async function simulateResponse(text) {
    await sleep(800)

    const lotMatch = text.match(/LOT[-_]?\d+/i)

    if (lotMatch) {
      const lotId = lotMatch[0].toUpperCase()

      messages.value.push({
        role: 'assistant',
        content: `${lotId}의 공정 이력을 조회합니다.`,
        agentName: 'Supervisor',
        timestamp: Date.now(),
      })

      await sleep(600)

      messages.value.push({
        role: 'tool',
        content: `[${lotId} 공정 이력]\n` +
          `1. Photo — 2025-01-15 09:30 — Loss: 0.12% — NORMAL\n` +
          `2. Etch — 2025-01-15 11:45 — Loss: 0.08% — NORMAL\n` +
          `3. Deposition — 2025-01-15 14:20 — Loss: 0.15% — NORMAL\n` +
          `4. Photo — 2025-01-16 09:00 — Loss: 0.45% — ABNORMAL\n` +
          `5. Etch — 2025-01-16 11:30 — Loss: 0.11% — NORMAL`,
        toolName: 'get_lot_history',
        timestamp: Date.now(),
      })

      await sleep(500)

      messages.value.push({
        role: 'assistant',
        content: `${lotId}의 공정 이력을 분석한 결과, **4번째 Photo 공정**에서 비정상(ABNORMAL) 상태가 감지되었습니다.\nLoss율이 0.45%로 기준치를 초과합니다. Photo 에이전트를 통해 상세 검사를 진행하겠습니다.`,
        agentName: 'Supervisor',
        toolCalls: [
          {
            id: 'demo-tc-1',
            name: 'inspect_pattern',
            args: { lot_id: lotId, step: 4, process: 'Photo', check_type: 'alignment' },
          },
        ],
        timestamp: Date.now(),
      })

      pendingApproval.value = {
        toolCalls: [
          {
            id: 'demo-tc-1',
            name: 'inspect_pattern',
            args: { lot_id: lotId, step: 4, process: 'Photo', check_type: 'alignment' },
          },
        ],
      }
      isLoading.value = false
    } else {
      messages.value.push({
        role: 'assistant',
        content: generateDemoResponse(text),
        agentName: 'Supervisor',
        timestamp: Date.now(),
      })
      isLoading.value = false
    }
  }

  async function simulateToolResult() {
    await sleep(1000)

    messages.value.push({
      role: 'tool',
      content: '패턴 검사 결과:\n' +
        '- Alignment Error: 0.023μm (기준: ±0.05μm)\n' +
        '- CD (Critical Dimension): 목표 대비 +3.2nm 편차\n' +
        '- Overlay: X: 0.8nm, Y: 1.2nm\n' +
        '- 판정: REVIEW REQUIRED',
      toolName: 'inspect_pattern',
      timestamp: Date.now(),
    })

    await sleep(500)

    messages.value.push({
      role: 'assistant',
      content: '패턴 검사 결과, **CD(Critical Dimension) 편차가 +3.2nm**으로 확인되었습니다.\n\n' +
        '정상 범위(±2nm) 를 벗어나므로 **리워크(rework)** 를 권장합니다.\n' +
        'Overlay 수치는 양호하나, Photo 장비의 노광 조건 재점검이 필요합니다.',
      agentName: 'Photo Agent',
      timestamp: Date.now(),
    })

    isLoading.value = false
  }

  function generateDemoResponse(text) {
    const responses = [
      '반도체 공정 품질 관리를 도와드리겠습니다. LOT ID를 입력해주시면 해당 LOT의 공정 이력을 조회하고 분석해드립니다.\n\n예시: `LOT-2024001`',
      '안녕하세요! 저는 반도체 FAB 공정 품질 관리 에이전트입니다.\n\n다음과 같은 작업을 수행할 수 있습니다:\n- **Photo 공정**: 패턴 검사, CD 측정\n- **Etch 공정**: 식각 프로파일 검사, 깊이 측정\n- **Deposition 공정**: 막 두께 및 균일도 검사\n- **이력 조회**: LOT별 공정 이력 추적\n\nLOT ID를 입력하면 시작됩니다.',
      '해당 질문에 대해 답변드리겠습니다. 더 정확한 분석을 위해 LOT ID를 알려주시면 공정 데이터를 기반으로 상세한 답변을 드릴 수 있습니다.',
    ]
    return responses[Math.floor(Math.random() * responses.length)]
  }

  return {
    simulateResponse,
    simulateToolResult,
  }
}
