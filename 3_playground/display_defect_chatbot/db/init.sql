-- display_defect_chatbot/db/init.sql

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- 문서 레지스트리
CREATE TABLE IF NOT EXISTS documents (
    doc_id      VARCHAR(100) PRIMARY KEY,
    filename    VARCHAR(255) NOT NULL,
    doc_type    VARCHAR(50),
    status      VARCHAR(20) DEFAULT 'PENDING',
    created_at  TIMESTAMP DEFAULT NOW()
);

-- 제품 마스터
CREATE TABLE IF NOT EXISTS products (
    product_id      VARCHAR(50) PRIMARY KEY,
    model           VARCHAR(100),
    panel_size      VARCHAR(20),
    manufactured_at TIMESTAMP
);

-- 불량 케이스
CREATE TABLE IF NOT EXISTS defect_cases (
    case_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id   VARCHAR(50) REFERENCES products(product_id),
    company      VARCHAR(100),
    defect_type  VARCHAR(100),
    description  TEXT,
    reported_at  TIMESTAMP DEFAULT NOW()
);

-- 공정이력 (ProcessHistoryAgent)
CREATE TABLE IF NOT EXISTS process_history (
    id           BIGSERIAL PRIMARY KEY,
    product_id   VARCHAR(50),
    process_step VARCHAR(100),
    equipment_id VARCHAR(50),
    operator_id  VARCHAR(50),
    result       VARCHAR(20),
    measured_at  TIMESTAMP
);

-- 반송이력 (ReturnHistoryAgent)
CREATE TABLE IF NOT EXISTS return_history (
    id            BIGSERIAL PRIMARY KEY,
    product_id    VARCHAR(50),
    return_reason VARCHAR(200),
    return_date   DATE,
    quantity      INT,
    severity      VARCHAR(20)
);

-- 테스트이력 (TestHistoryAgent)
CREATE TABLE IF NOT EXISTS test_history (
    id              BIGSERIAL PRIMARY KEY,
    product_id      VARCHAR(50),
    test_type       VARCHAR(100),
    result          VARCHAR(20),
    measured_value  DECIMAL,
    spec_min        DECIMAL,
    spec_max        DECIMAL,
    tested_at       TIMESTAMP
);

-- 백그라운드 작업 추적
CREATE TABLE IF NOT EXISTS background_tasks (
    id           BIGSERIAL PRIMARY KEY,
    task_id      VARCHAR(100) UNIQUE NOT NULL,
    session_id   VARCHAR(100),
    status       VARCHAR(20) DEFAULT 'PENDING',
    result_text  TEXT,
    created_at   TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- 분석 세션 (002_add_chat_sessions + 003_add_step_hypotheses)
CREATE TABLE IF NOT EXISTS chat_sessions (
    id                  TEXT PRIMARY KEY,
    title               TEXT NOT NULL DEFAULT '',
    product_id          TEXT NOT NULL DEFAULT '',
    defect_description  TEXT NOT NULL DEFAULT '',
    hypothesis          TEXT NOT NULL DEFAULT '',
    agent_results       JSONB NOT NULL DEFAULT '{}',
    chat_messages       JSONB NOT NULL DEFAULT '[]',
    enabled_agents      JSONB NOT NULL DEFAULT '{}',
    long_term_task_id   TEXT,
    long_term_status    TEXT NOT NULL DEFAULT 'PENDING',
    long_term_result    TEXT,
    final_action_plan   TEXT NOT NULL DEFAULT '',
    step                TEXT NOT NULL DEFAULT 'input',
    hypotheses          JSONB NOT NULL DEFAULT '[]',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ══════════════════════════════════════════════════════════════════
-- 제품 마스터
-- ══════════════════════════════════════════════════════════════════

INSERT INTO products VALUES
  ('LOT-A001', 'SDC-OLED-55A', '55inch', '2025-10-01'),
  ('LOT-A002', 'SDC-OLED-55A', '55inch', '2025-10-15'),
  ('LOT-A003', 'SDC-OLED-55A', '55inch', '2025-10-28'),
  ('LOT-B001', 'SDC-QLED-65B', '65inch', '2025-11-01'),
  ('LOT-B002', 'SDC-QLED-65B', '65inch', '2025-11-20'),
  ('LOT-C001', 'SDC-OLED-27C', '27inch', '2025-12-01'),
  ('LOT-C002', 'SDC-OLED-27C', '27inch', '2025-12-18'),
  ('LOT-D001', 'SDC-AMOLED-32D', '32inch', '2026-01-05'),
  ('LOT-D002', 'SDC-AMOLED-32D', '32inch', '2026-01-20')
ON CONFLICT DO NOTHING;

-- ══════════════════════════════════════════════════════════════════
-- 불량 케이스
-- ══════════════════════════════════════════════════════════════════

INSERT INTO defect_cases (product_id, company, defect_type, description) VALUES
  ('LOT-A001', 'A사', 'Dead Pixel',     '화면 좌측 상단 영역 픽셀 10개 완전 소등 — TFT Etch 공정 이상 의심'),
  ('LOT-A002', 'B사', 'Hot Pixel',      '화면 중앙부 흰 점 불량 5개 — 셀 정렬 불량 의심'),
  ('LOT-A003', 'C사', 'Line Defect',    '화면 하단 수평선 1줄 상시 점등 — Etch-SD 공정 이상'),
  ('LOT-B001', 'A사', 'Cluster Defect', '우측 하단 군집 불량 50x50px — 마스크 오염 의심'),
  ('LOT-B002', 'D사', 'Mura Defect',    '전면 밝기 불균일 — 중앙 밝고 주변 어두운 현상'),
  ('LOT-C001', 'B사', 'Burn-in',        '장시간 정지화면 후 잔상 발생 — OLED 소자 열화'),
  ('LOT-C002', 'C사', 'Color Shift',    'sRGB 기준 녹색 채널 색좌표 이탈 (Δu''v'' > 0.01)'),
  ('LOT-D001', 'E사', 'Touch Defect',   '우측 하단 터치 미감지 영역 20x30mm — Touch 패턴 단선'),
  ('LOT-D002', 'A사', 'Dark Spot',      '화면 중앙 암점 불량 직경 3mm 이상 2개 — OLED 증착 이상')
ON CONFLICT DO NOTHING;

-- ══════════════════════════════════════════════════════════════════
-- 공정이력
-- ══════════════════════════════════════════════════════════════════

INSERT INTO process_history (product_id, process_step, equipment_id, operator_id, result, measured_at) VALUES

  -- ── LOT-A001 Dead Pixel ─────────────────────────────────────────
  -- 주요 원인: Etch-Gate FAIL → CVD-Active·Ion-Implant WARN 연쇄
  ('LOT-A001', 'CVD-Gate',          'EQ-CVD-01', 'OP-100', 'PASS', '2025-10-01 08:00:00'),
  ('LOT-A001', 'Photo-Gate',        'EQ-PHT-02', 'OP-101', 'PASS', '2025-10-01 09:30:00'),
  ('LOT-A001', 'Etch-Gate',         'EQ-ETH-01', 'OP-102', 'FAIL', '2025-10-01 11:00:00'),
  ('LOT-A001', 'CVD-Active',        'EQ-CVD-01', 'OP-100', 'WARN', '2025-10-01 13:00:00'),
  ('LOT-A001', 'Ion-Implant',       'EQ-ION-01', 'OP-103', 'WARN', '2025-10-01 15:00:00'),
  ('LOT-A001', 'Photo-Active',      'EQ-PHT-01', 'OP-101', 'PASS', '2025-10-02 08:00:00'),
  ('LOT-A001', 'Etch-Active',       'EQ-ETH-02', 'OP-102', 'WARN', '2025-10-02 10:00:00'),
  ('LOT-A001', 'Metal-SD',          'EQ-MET-01', 'OP-104', 'PASS', '2025-10-02 12:00:00'),
  ('LOT-A001', 'Passivation',       'EQ-PAS-01', 'OP-105', 'FAIL', '2025-10-02 14:00:00'),
  ('LOT-A001', 'Final-Inspection',  'EQ-INS-01', 'OP-106', 'FAIL', '2025-10-03 09:00:00'),

  -- ── LOT-A002 Hot Pixel ──────────────────────────────────────────
  -- 주요 원인: Cell-Align FAIL → Photo-Gate·OLED-Depo WARN 연쇄
  ('LOT-A002', 'CVD-Gate',          'EQ-CVD-02', 'OP-100', 'PASS', '2025-10-15 08:00:00'),
  ('LOT-A002', 'Photo-Gate',        'EQ-PHT-02', 'OP-101', 'WARN', '2025-10-15 09:30:00'),
  ('LOT-A002', 'Etch-Gate',         'EQ-ETH-02', 'OP-102', 'PASS', '2025-10-15 11:00:00'),
  ('LOT-A002', 'CVD-Active',        'EQ-CVD-02', 'OP-100', 'PASS', '2025-10-15 13:00:00'),
  ('LOT-A002', 'Ion-Implant',       'EQ-ION-01', 'OP-103', 'PASS', '2025-10-15 15:00:00'),
  ('LOT-A002', 'Cell-Align',        'EQ-ALN-01', 'OP-104', 'FAIL', '2025-10-16 08:00:00'),
  ('LOT-A002', 'Photo-Active',      'EQ-PHT-03', 'OP-101', 'WARN', '2025-10-16 10:00:00'),
  ('LOT-A002', 'OLED-Depo',         'EQ-OLT-01', 'OP-107', 'WARN', '2025-10-17 08:00:00'),
  ('LOT-A002', 'Encap',             'EQ-ENC-01', 'OP-108', 'FAIL', '2025-10-17 12:00:00'),
  ('LOT-A002', 'Final-Inspection',  'EQ-INS-01', 'OP-106', 'FAIL', '2025-10-18 09:00:00'),

  -- ── LOT-A003 Line Defect ────────────────────────────────────────
  -- 주요 원인: Etch-SD FAIL → CVD-Active·Photo-Active WARN
  ('LOT-A003', 'CVD-Gate',          'EQ-CVD-01', 'OP-100', 'PASS', '2025-10-28 08:00:00'),
  ('LOT-A003', 'Photo-Gate',        'EQ-PHT-01', 'OP-101', 'PASS', '2025-10-28 09:30:00'),
  ('LOT-A003', 'Etch-Gate',         'EQ-ETH-01', 'OP-102', 'PASS', '2025-10-28 11:00:00'),
  ('LOT-A003', 'CVD-Active',        'EQ-CVD-02', 'OP-100', 'WARN', '2025-10-28 13:00:00'),
  ('LOT-A003', 'Photo-Active',      'EQ-PHT-01', 'OP-101', 'WARN', '2025-10-29 08:00:00'),
  ('LOT-A003', 'Etch-SD',           'EQ-ETH-02', 'OP-105', 'FAIL', '2025-10-29 10:00:00'),
  ('LOT-A003', 'Passivation',       'EQ-PAS-01', 'OP-105', 'WARN', '2025-10-29 13:00:00'),
  ('LOT-A003', 'OLED-Depo',         'EQ-OLT-01', 'OP-107', 'PASS', '2025-10-30 08:00:00'),
  ('LOT-A003', 'Final-Inspection',  'EQ-INS-01', 'OP-106', 'FAIL', '2025-10-30 14:00:00'),

  -- ── LOT-B001 Cluster Defect ─────────────────────────────────────
  ('LOT-B001', 'CVD-Gate',          'EQ-CVD-03', 'OP-100', 'PASS', '2025-11-01 08:00:00'),
  ('LOT-B001', 'Photo-Gate',        'EQ-PHT-01', 'OP-101', 'WARN', '2025-11-01 09:30:00'),
  ('LOT-B001', 'Etch-Gate',         'EQ-ETH-03', 'OP-102', 'PASS', '2025-11-01 11:00:00'),
  ('LOT-B001', 'CVD-Active',        'EQ-CVD-03', 'OP-100', 'FAIL', '2025-11-02 08:00:00'),
  ('LOT-B001', 'Photo-Active',      'EQ-PHT-02', 'OP-101', 'WARN', '2025-11-02 10:00:00'),
  ('LOT-B001', 'Etch-Active',       'EQ-ETH-03', 'OP-102', 'WARN', '2025-11-02 13:00:00'),
  ('LOT-B001', 'Final-Inspection',  'EQ-INS-01', 'OP-106', 'FAIL', '2025-11-03 09:00:00'),

  -- ── LOT-B002 Mura Defect ────────────────────────────────────────
  ('LOT-B002', 'CVD-Gate',          'EQ-CVD-03', 'OP-100', 'PASS', '2025-11-20 08:00:00'),
  ('LOT-B002', 'Photo-Gate',        'EQ-PHT-02', 'OP-101', 'PASS', '2025-11-20 09:30:00'),
  ('LOT-B002', 'Photo-Active',      'EQ-PHT-03', 'OP-104', 'FAIL', '2025-11-20 13:00:00'),
  ('LOT-B002', 'Etch-SD',           'EQ-ETH-02', 'OP-105', 'WARN', '2025-11-20 15:00:00'),
  ('LOT-B002', 'OLED-Depo',         'EQ-OLT-02', 'OP-107', 'WARN', '2025-11-21 08:00:00'),
  ('LOT-B002', 'Final-Inspection',  'EQ-INS-01', 'OP-106', 'FAIL', '2025-11-22 09:00:00'),

  -- ── LOT-C001 Burn-in ────────────────────────────────────────────
  ('LOT-C001', 'CVD-Gate',          'EQ-CVD-01', 'OP-100', 'PASS', '2025-12-01 08:00:00'),
  ('LOT-C001', 'Photo-Gate',        'EQ-PHT-01', 'OP-101', 'PASS', '2025-12-01 09:30:00'),
  ('LOT-C001', 'Etch-Gate',         'EQ-ETH-01', 'OP-102', 'PASS', '2025-12-01 11:00:00'),
  ('LOT-C001', 'OLED-Depo',         'EQ-OLT-01', 'OP-107', 'FAIL', '2025-12-02 08:00:00'),
  ('LOT-C001', 'Encap',             'EQ-ENC-01', 'OP-108', 'WARN', '2025-12-02 11:00:00'),
  ('LOT-C001', 'Final-Inspection',  'EQ-INS-01', 'OP-106', 'FAIL', '2025-12-03 09:00:00'),

  -- ── LOT-C002 Color Shift ────────────────────────────────────────
  ('LOT-C002', 'CVD-Gate',          'EQ-CVD-02', 'OP-100', 'PASS', '2025-12-18 08:00:00'),
  ('LOT-C002', 'OLED-Depo',         'EQ-OLT-01', 'OP-107', 'WARN', '2025-12-19 08:00:00'),
  ('LOT-C002', 'Color-Filter',      'EQ-CFT-01', 'OP-109', 'FAIL', '2025-12-19 13:00:00'),
  ('LOT-C002', 'Encap',             'EQ-ENC-01', 'OP-108', 'WARN', '2025-12-20 09:00:00'),
  ('LOT-C002', 'Final-Inspection',  'EQ-INS-01', 'OP-106', 'FAIL', '2025-12-20 14:00:00'),

  -- ── LOT-D001 Touch Defect ───────────────────────────────────────
  ('LOT-D001', 'CVD-Gate',          'EQ-CVD-01', 'OP-100', 'PASS', '2026-01-05 08:00:00'),
  ('LOT-D001', 'OLED-Depo',         'EQ-OLT-02', 'OP-107', 'PASS', '2026-01-06 08:00:00'),
  ('LOT-D001', 'Touch-Pattern',     'EQ-TCH-01', 'OP-110', 'FAIL', '2026-01-06 14:00:00'),
  ('LOT-D001', 'Encap',             'EQ-ENC-01', 'OP-108', 'WARN', '2026-01-07 09:00:00'),
  ('LOT-D001', 'Final-Inspection',  'EQ-INS-01', 'OP-106', 'FAIL', '2026-01-08 09:00:00'),

  -- ── LOT-D002 Dark Spot ──────────────────────────────────────────
  ('LOT-D002', 'CVD-Gate',          'EQ-CVD-02', 'OP-100', 'PASS', '2026-01-20 08:00:00'),
  ('LOT-D002', 'OLED-Depo',         'EQ-OLT-01', 'OP-107', 'FAIL', '2026-01-21 08:00:00'),
  ('LOT-D002', 'Dark-Current-Test', 'EQ-DCT-01', 'OP-111', 'WARN', '2026-01-21 14:00:00'),
  ('LOT-D002', 'Encap',             'EQ-ENC-01', 'OP-108', 'WARN', '2026-01-22 09:00:00'),
  ('LOT-D002', 'Final-Inspection',  'EQ-INS-01', 'OP-106', 'FAIL', '2026-01-23 09:00:00');

-- ══════════════════════════════════════════════════════════════════
-- 반송이력
-- ══════════════════════════════════════════════════════════════════

INSERT INTO return_history (product_id, return_reason, return_date, quantity, severity) VALUES

  -- ── LOT-A001: Dead Pixel (6건) ──────────────────────────────────
  ('LOT-A001', '픽셀 소등 불량 — 좌측 상단 TFT 특성 이상 의심',      '2025-11-02', 50, 'HIGH'),
  ('LOT-A001', 'Etch-Gate 공정 이상 — 게이트 선폭 초과',              '2025-11-05', 30, 'HIGH'),
  ('LOT-A001', '화면 암점 확산 — Passivation 막질 불량 의심',         '2025-11-10', 20, 'HIGH'),
  ('LOT-A001', 'CVD-Active 막 두께 불균일 — 이동도 저하',             '2025-11-18', 15, 'MEDIUM'),
  ('LOT-A001', '모듈 조립 후 픽셀 소등 재발 — Ion-Implant 도핑 불량', '2025-11-25', 45, 'HIGH'),
  ('LOT-A001', '시장 반송 — 화면 좌상단 블랙 스팟 군집',              '2025-12-10', 25, 'MEDIUM'),

  -- ── LOT-A002: Hot Pixel (6건) ───────────────────────────────────
  ('LOT-A002', 'Hot Pixel 군집 — Cell-Align 정밀도 불량',             '2025-11-18', 40, 'HIGH'),
  ('LOT-A002', '셀 갭 불균일 — 배향막 공정 이상',                     '2025-11-22', 25, 'MEDIUM'),
  ('LOT-A002', 'OLED 발광 불균일 — Encap 수분 침투 의심',             '2025-11-28', 20, 'HIGH'),
  ('LOT-A002', '화면 중앙 과밝기 — Photo-Gate 노광 조건 편차',        '2025-12-05', 35, 'MEDIUM'),
  ('LOT-A002', '출하 검사 재불량 — Photo-Active WARN 이후 재검사',    '2025-12-15', 30, 'HIGH'),
  ('LOT-A002', '시장 AS — 중앙부 흰 점 불량 고객 클레임',             '2026-01-10', 18, 'MEDIUM'),

  -- ── LOT-A003: Line Defect (5건) ─────────────────────────────────
  ('LOT-A003', '수평 라인 상시 점등 — Etch-SD 단선 의심',             '2025-11-30', 45, 'HIGH'),
  ('LOT-A003', 'S/D 금속 패턴 불량 — 에칭 균일도 저하',              '2025-12-05', 30, 'HIGH'),
  ('LOT-A003', 'CVD-Active 막질 불량 — 이동도 저하 연관성',           '2025-12-10', 20, 'MEDIUM'),
  ('LOT-A003', '라인 불량 반복 발생 — 동일 설비 연속 FAIL',           '2025-12-20', 50, 'HIGH'),
  ('LOT-A003', '고객 반송 — 하단 1줄 상시 점등 현상',                 '2026-01-05', 35, 'MEDIUM'),

  -- ── LOT-B001 (4건) ──────────────────────────────────────────────
  ('LOT-B001', '군집 픽셀 불량 — 마스크 오염 의심',                   '2025-12-05', 80, 'HIGH'),
  ('LOT-B001', 'CVD-Active 이상 — 군집 불량 원인 분석 중',            '2025-12-10', 40, 'HIGH'),
  ('LOT-B001', '파티클 오염 — Photo-Gate 노광 환경 이상',             '2025-12-18', 30, 'MEDIUM'),
  ('LOT-B001', '고객 반송 — 우측 하단 클러스터 불량',                 '2026-01-08', 25, 'HIGH'),

  -- ── LOT-B002 (3건) ──────────────────────────────────────────────
  ('LOT-B002', 'Mura 불량 — Photo-Active 노광 균일도 이상',           '2025-12-25', 60, 'HIGH'),
  ('LOT-B002', '화면 밝기 불균일 — Etch-SD WARN 연관',               '2026-01-03', 35, 'MEDIUM'),
  ('LOT-B002', '시장 반송 — 중앙 밝고 주변 어두운 현상',              '2026-01-20', 45, 'HIGH'),

  -- ── LOT-C001 (3건) ──────────────────────────────────────────────
  ('LOT-C001', '잔상 발생 — OLED 소자 열화 의심',                     '2026-01-10', 35, 'HIGH'),
  ('LOT-C001', 'Encap 수분 침투 — 잔상 가속 요인',                    '2026-01-18', 20, 'HIGH'),
  ('LOT-C001', '고객 클레임 — 정지화면 30분 후 잔상 확인',            '2026-02-01', 50, 'MEDIUM'),

  -- ── LOT-C002 (3건) ──────────────────────────────────────────────
  ('LOT-C002', '색감 이상 — 녹색 채널 색좌표 이탈',                   '2026-01-22', 25, 'MEDIUM'),
  ('LOT-C002', 'Color-Filter 공정 불량 — 파장 편차',                  '2026-02-05', 18, 'HIGH'),
  ('LOT-C002', '시장 AS — 피부색 이상하게 보임 고객 민원',            '2026-02-15', 30, 'MEDIUM'),

  -- ── LOT-D001 (3건) ──────────────────────────────────────────────
  ('LOT-D001', '터치 미감지 — Touch 패턴 단선',                       '2026-02-08', 40, 'HIGH'),
  ('LOT-D001', 'Encap 이후 터치 감도 저하',                           '2026-02-15', 22, 'MEDIUM'),
  ('LOT-D001', '고객 반송 — 우측 하단 터치 불량',                     '2026-02-25', 35, 'HIGH'),

  -- ── LOT-D002 (3건) ──────────────────────────────────────────────
  ('LOT-D002', '암점 불량 — OLED 증착 이상 의심',                     '2026-02-18', 15, 'MEDIUM'),
  ('LOT-D002', 'Dark Current 증가 — 누설전류 관련',                   '2026-02-24', 20, 'HIGH'),
  ('LOT-D002', '고객 반송 — 화면 중앙 암점 2개',                      '2026-03-05', 12, 'MEDIUM');

-- ══════════════════════════════════════════════════════════════════
-- 테스트결과
-- ══════════════════════════════════════════════════════════════════

INSERT INTO test_history (product_id, test_type, result, measured_value, spec_min, spec_max, tested_at) VALUES

  -- ── LOT-A001: Dead Pixel (7건) ──────────────────────────────────
  ('LOT-A001', 'Vth-Uniformity',          'FAIL', 2.85, 1.00, 2.50, '2025-10-03 09:00:00'),
  ('LOT-A001', 'Gate-Leakage-Current',    'FAIL', 1.20, 0.00, 0.50, '2025-10-03 09:30:00'),
  ('LOT-A001', 'Ion/Ioff-Ratio',          'WARN', 920000, 1000000, NULL, '2025-10-03 10:00:00'),
  ('LOT-A001', 'Mobility',               'WARN', 0.44, 0.50, 1.50, '2025-10-03 10:30:00'),
  ('LOT-A001', 'Pixel-Voltage-Uniformity','FAIL', 86.5, 95.0, NULL, '2025-10-03 11:00:00'),
  ('LOT-A001', 'Threshold-Voltage',       'FAIL', 3.20, 1.00, 2.80, '2025-10-03 11:30:00'),
  ('LOT-A001', 'Subthreshold-Swing',      'WARN', 185.0, NULL, 150.0, '2025-10-03 12:00:00'),

  -- ── LOT-A002: Hot Pixel (7건) ───────────────────────────────────
  ('LOT-A002', 'Cell-Gap',               'FAIL', 3.75, 4.00, 4.50, '2025-10-18 09:00:00'),
  ('LOT-A002', 'Alignment-Accuracy',     'FAIL', 2.90, NULL, 1.50, '2025-10-18 09:30:00'),
  ('LOT-A002', 'Pixel-Opening-Ratio',    'FAIL', 41.5, 48.0, NULL, '2025-10-18 10:00:00'),
  ('LOT-A002', 'OLED-Luminance',         'WARN', 382.0, 400.0, 500.0, '2025-10-18 10:30:00'),
  ('LOT-A002', 'Color-Coordinate-G',     'WARN', 0.008, NULL, 0.010, '2025-10-18 11:00:00'),
  ('LOT-A002', 'Vth-Uniformity',         'PASS', 1.80, 1.00, 2.50, '2025-10-18 11:30:00'),
  ('LOT-A002', 'Ion/Ioff-Ratio',         'PASS', 1050000, 1000000, NULL, '2025-10-18 12:00:00'),

  -- ── LOT-A003: Line Defect (6건) ─────────────────────────────────
  ('LOT-A003', 'Vth-Uniformity',         'PASS', 2.10, 1.00, 2.50, '2025-10-30 09:00:00'),
  ('LOT-A003', 'Mobility',              'FAIL', 0.38, 0.50, 1.50, '2025-10-30 09:30:00'),
  ('LOT-A003', 'CD-Uniformity',         'WARN', 98.4, 99.0, 101.0, '2025-10-30 10:00:00'),
  ('LOT-A003', 'Etch-CD-Bias',          'FAIL', 0.42, 0.50, 0.80, '2025-10-30 10:30:00'),
  ('LOT-A003', 'Metal-Resistivity',     'WARN', 28.5, NULL, 25.0, '2025-10-30 11:00:00'),
  ('LOT-A003', 'Contact-Resistance',    'FAIL', 185.0, NULL, 100.0, '2025-10-30 11:30:00'),

  -- ── LOT-B001 (5건) ──────────────────────────────────────────────
  ('LOT-B001', 'Particle-Count',        'FAIL', 18.0, 0.0, 10.0, '2025-11-03 08:00:00'),
  ('LOT-B001', 'CD-Uniformity',         'WARN', 98.1, 99.0, 101.0, '2025-11-03 08:30:00'),
  ('LOT-B001', 'Vth-Uniformity',        'PASS', 2.00, 1.00, 2.50, '2025-11-03 09:00:00'),
  ('LOT-B001', 'Defect-Density',        'FAIL', 0.35, NULL, 0.10, '2025-11-03 09:30:00'),
  ('LOT-B001', 'Gate-Leakage-Current',  'WARN', 0.45, NULL, 0.50, '2025-11-03 10:00:00'),

  -- ── LOT-B002 (5건) ──────────────────────────────────────────────
  ('LOT-B002', 'Particle-Count',        'WARN', 12.0, 0.0, 10.0, '2025-11-22 08:00:00'),
  ('LOT-B002', 'CD-Uniformity',         'FAIL', 97.0, 99.0, 101.0, '2025-11-22 08:30:00'),
  ('LOT-B002', 'Luminance-Uniformity',  'FAIL', 82.0, 90.0, NULL, '2025-11-22 09:00:00'),
  ('LOT-B002', 'Ion/Ioff-Ratio',        'PASS', 1100000, 1000000, NULL, '2025-11-22 09:30:00'),
  ('LOT-B002', 'Photo-Sensitivity',     'WARN', 0.72, 0.80, NULL, '2025-11-22 10:00:00'),

  -- ── LOT-C001 (5건) ──────────────────────────────────────────────
  ('LOT-C001', 'OLED-Luminance',        'FAIL', 375.0, 400.0, 500.0, '2025-12-03 09:00:00'),
  ('LOT-C001', 'Color-Coordinate',      'PASS', 0.003, 0.0, 0.010, '2025-12-03 09:30:00'),
  ('LOT-C001', 'Leakage-Current',       'WARN', 0.082, 0.0, 0.050, '2025-12-03 10:00:00'),
  ('LOT-C001', 'Lifetime-Degradation',  'FAIL', 28.0, NULL, 20.0, '2025-12-03 10:30:00'),
  ('LOT-C001', 'Encap-Moisture-Rate',   'WARN', 0.045, NULL, 0.030, '2025-12-03 11:00:00'),

  -- ── LOT-C002 (5건) ──────────────────────────────────────────────
  ('LOT-C002', 'Color-Coordinate',      'FAIL', 0.015, 0.0, 0.010, '2025-12-20 09:00:00'),
  ('LOT-C002', 'OLED-Luminance',        'WARN', 393.0, 400.0, 500.0, '2025-12-20 09:30:00'),
  ('LOT-C002', 'Cell-Gap',              'PASS', 4.20, 4.00, 4.50, '2025-12-20 10:00:00'),
  ('LOT-C002', 'Color-Gamut-sRGB',      'FAIL', 88.5, 95.0, NULL, '2025-12-20 10:30:00'),
  ('LOT-C002', 'White-Balance-dE',      'WARN', 3.20, NULL, 2.00, '2025-12-20 11:00:00'),

  -- ── LOT-D001 (5건) ──────────────────────────────────────────────
  ('LOT-D001', 'Touch-Sensitivity',     'FAIL', 1.15, 2.00, 5.00, '2026-01-08 09:00:00'),
  ('LOT-D001', 'Touch-Linearity',       'FAIL', 4.80, NULL, 2.00, '2026-01-08 09:30:00'),
  ('LOT-D001', 'Vth-Uniformity',        'PASS', 2.00, 1.00, 2.50, '2026-01-08 10:00:00'),
  ('LOT-D001', 'Mobility',              'PASS', 0.85, 0.50, 1.50, '2026-01-08 10:30:00'),
  ('LOT-D001', 'Pattern-Resistance',    'WARN', 320.0, NULL, 250.0, '2026-01-08 11:00:00'),

  -- ── LOT-D002 (5건) ──────────────────────────────────────────────
  ('LOT-D002', 'Dark-Current',          'FAIL', 0.125, 0.0, 0.050, '2026-01-23 09:00:00'),
  ('LOT-D002', 'OLED-Luminance',        'WARN', 390.0, 400.0, 500.0, '2026-01-23 09:30:00'),
  ('LOT-D002', 'Ion/Ioff-Ratio',        'PASS', 1080000, 1000000, NULL, '2026-01-23 10:00:00'),
  ('LOT-D002', 'Leakage-Current',       'FAIL', 0.095, 0.0, 0.050, '2026-01-23 10:30:00'),
  ('LOT-D002', 'Pixel-Defect-Density',  'WARN', 0.22, NULL, 0.10, '2026-01-23 11:00:00');
