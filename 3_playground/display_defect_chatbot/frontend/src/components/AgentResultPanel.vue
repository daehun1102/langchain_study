<template>
  <div class="result-view">
    <div class="hypothesis-badge">선택된 가설: {{ hypothesis }}</div>

    <!-- 서브에이전트 결과 그리드 -->
    <div class="agent-grid">
      <div class="agent-card">
        <h3>⚙️ 공정이력</h3>
        <table v-if="result.processHistory.length">
          <tr v-for="(r, i) in result.processHistory" :key="i">
            <td>{{ r.process_step }}</td>
            <td :class="r.result">{{ r.result }}</td>
            <td>{{ r.equipment_id }}</td>
          </tr>
        </table>
        <p v-else class="empty">데이터 없음</p>
      </div>

      <div class="agent-card">
        <h3>↩️ 반송이력</h3>
        <table v-if="result.returnHistory.length">
          <tr v-for="(r, i) in result.returnHistory" :key="i">
            <td>{{ r.return_reason }}</td>
            <td :class="r.severity?.toLowerCase()">{{ r.severity }}</td>
            <td>{{ r.quantity }}건</td>
          </tr>
        </table>
        <p v-else class="empty">데이터 없음</p>
      </div>

      <div class="agent-card">
        <h3>🧪 테스트결과</h3>
        <table v-if="result.testResults.length">
          <tr v-for="(r, i) in result.testResults" :key="i">
            <td>{{ r.test_type }}</td>
            <td :class="r.result">{{ r.result }}</td>
            <td>{{ r.measured_value }}</td>
          </tr>
        </table>
        <p v-else class="empty">데이터 없음</p>
      </div>

      <div class="agent-card long-term">
        <h3>📊 장기이력 분석 <span class="badge" :class="result.longTermStatus">{{ result.longTermStatus }}</span></h3>
        <pre v-if="result.longTermResult">{{ result.longTermResult }}</pre>
        <p v-else class="empty">백그라운드 분석 진행 중...</p>
      </div>
    </div>

    <!-- 최종 조치안 -->
    <div class="action-plan">
      <h3>📋 최종 조치 방안</h3>
      <div v-html="renderedPlan" class="plan-content"></div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps(['result', 'hypothesis'])
const renderedPlan = computed(() => marked(props.result.actionPlan || ''))
</script>

<style scoped>
.result-view { display: flex; flex-direction: column; gap: 24px; }
.hypothesis-badge { background: #1e3a5f; border: 1px solid #3b82f6; border-radius: 8px; padding: 10px 16px; color: #93c5fd; font-size: 0.9rem; }
.agent-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.agent-card { background: #1a1d27; border: 1px solid #2a2d3a; border-radius: 10px; padding: 16px; }
.agent-card h3 { color: #60a5fa; font-size: 0.9rem; margin-bottom: 12px; }
.long-term { grid-column: 1 / -1; }
table { width: 100%; border-collapse: collapse; font-size: 0.8rem; }
td { padding: 4px 8px; border-bottom: 1px solid #1e2130; }
.FAIL, .fail { color: #f87171; }
.PASS, .pass { color: #4ade80; }
.WARN, .warn, .medium { color: #fbbf24; }
.HIGH, .high { color: #f87171; }
.LOW, .low { color: #4ade80; }
.empty { color: #4b5563; font-size: 0.85rem; }
pre { font-size: 0.8rem; white-space: pre-wrap; color: #d1d5db; }
.badge { font-size: 0.7rem; padding: 2px 8px; border-radius: 4px; margin-left: 8px; }
.badge.PENDING { background: #374151; }
.badge.COMPLETED { background: #065f46; color: #6ee7b7; }
.badge.FAILED { background: #7f1d1d; color: #fca5a5; }
.action-plan { background: #1a1d27; border: 1px solid #2a2d3a; border-radius: 10px; padding: 20px; }
.action-plan h3 { color: #60a5fa; margin-bottom: 16px; }
.plan-content { color: #d1d5db; line-height: 1.7; }
</style>
