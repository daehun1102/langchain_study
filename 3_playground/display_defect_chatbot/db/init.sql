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

-- 테스트결과 (TestResultAgent)
CREATE TABLE IF NOT EXISTS test_results (
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

-- ── Mock 데이터 ────────────────────────────────────────────────

INSERT INTO products VALUES
  ('LOT-A001', 'SDC-OLED-55A', '55inch', '2025-06-01'),
  ('LOT-A002', 'SDC-OLED-55A', '55inch', '2025-06-15'),
  ('LOT-A003', 'SDC-OLED-55A', '55inch', '2025-06-28'),
  ('LOT-B001', 'SDC-QLED-65B', '65inch', '2025-07-01'),
  ('LOT-B002', 'SDC-QLED-65B', '65inch', '2025-07-20'),
  ('LOT-C001', 'SDC-OLED-27C', '27inch', '2025-08-01'),
  ('LOT-C002', 'SDC-OLED-27C', '27inch', '2025-08-18'),
  ('LOT-D001', 'SDC-AMOLED-32D', '32inch', '2025-09-05'),
  ('LOT-D002', 'SDC-AMOLED-32D', '32inch', '2025-09-20')
ON CONFLICT DO NOTHING;

INSERT INTO defect_cases (product_id, company, defect_type, description) VALUES
  ('LOT-A001', 'A사', 'Dead Pixel',     '화면 좌측 상단 영역 픽셀 소등 불량 10개'),
  ('LOT-A002', 'B사', 'Hot Pixel',      '화면 중앙부 흰 점 불량 5개'),
  ('LOT-A003', 'C사', 'Line Defect',    '화면 하단 수평선 1줄 상시 점등 불량'),
  ('LOT-B001', 'A사', 'Cluster Defect', '우측 하단 군집 불량 50x50px'),
  ('LOT-B002', 'D사', 'Mura Defect',    '전면 밝기 불균일 - 중앙부 밝고 주변부 어두운 현상'),
  ('LOT-C001', 'B사', 'Burn-in',        '장시간 정지화면 표시 후 잔상 발생'),
  ('LOT-C002', 'C사', 'Color Shift',    'sRGB 기준 녹색 채널 색좌표 이탈 (Δu''v'' > 0.01)'),
  ('LOT-D001', 'E사', 'Touch Defect',   '우측 하단 터치 미감지 영역 20x30mm'),
  ('LOT-D002', 'A사', 'Dark Spot',      '화면 중앙 암점 불량 직경 3mm 이상 2개')
ON CONFLICT DO NOTHING;

INSERT INTO process_history (product_id, process_step, equipment_id, operator_id, result, measured_at) VALUES
  -- LOT-A001 (Dead Pixel: Etch-Gate FAIL)
  ('LOT-A001', 'CVD-Gate',         'EQ-CVD-01', 'OP-100', 'PASS', '2025-06-01 08:00:00'),
  ('LOT-A001', 'Photo-Gate',       'EQ-PHT-02', 'OP-101', 'PASS', '2025-06-01 10:00:00'),
  ('LOT-A001', 'Etch-Gate',        'EQ-ETH-01', 'OP-102', 'FAIL', '2025-06-01 12:00:00'),
  ('LOT-A001', 'CVD-Active',       'EQ-CVD-01', 'OP-100', 'WARN', '2025-06-01 14:00:00'),
  ('LOT-A001', 'Ion-Implant',      'EQ-ION-01', 'OP-103', 'PASS', '2025-06-01 16:00:00'),
  -- LOT-A002 (Hot Pixel: Cell-Align FAIL)
  ('LOT-A002', 'CVD-Gate',         'EQ-CVD-02', 'OP-100', 'PASS', '2025-06-15 08:00:00'),
  ('LOT-A002', 'Photo-Gate',       'EQ-PHT-02', 'OP-101', 'PASS', '2025-06-15 10:00:00'),
  ('LOT-A002', 'Etch-Gate',        'EQ-ETH-02', 'OP-102', 'PASS', '2025-06-15 12:00:00'),
  ('LOT-A002', 'Cell-Align',       'EQ-ALN-01', 'OP-104', 'FAIL', '2025-06-15 14:00:00'),
  -- LOT-A003 (Line Defect: Photo-Active WARN → Etch-SD FAIL)
  ('LOT-A003', 'CVD-Gate',         'EQ-CVD-01', 'OP-100', 'PASS', '2025-06-28 08:00:00'),
  ('LOT-A003', 'Photo-Gate',       'EQ-PHT-01', 'OP-101', 'PASS', '2025-06-28 10:00:00'),
  ('LOT-A003', 'Etch-Gate',        'EQ-ETH-01', 'OP-102', 'PASS', '2025-06-28 12:00:00'),
  ('LOT-A003', 'CVD-Active',       'EQ-CVD-02', 'OP-100', 'WARN', '2025-06-28 14:00:00'),
  ('LOT-A003', 'Etch-SD',          'EQ-ETH-02', 'OP-105', 'FAIL', '2025-06-28 16:00:00'),
  ('LOT-A003', 'Final-Inspection', 'EQ-INS-01', 'OP-106', 'FAIL', '2025-06-29 09:00:00'),
  -- LOT-B001 (Cluster Defect: Photo-Gate WARN)
  ('LOT-B001', 'CVD-Gate',         'EQ-CVD-03', 'OP-100', 'PASS', '2025-07-01 08:00:00'),
  ('LOT-B001', 'Photo-Gate',       'EQ-PHT-01', 'OP-101', 'WARN', '2025-07-01 09:00:00'),
  ('LOT-B001', 'Etch-Gate',        'EQ-ETH-03', 'OP-102', 'PASS', '2025-07-01 11:00:00'),
  -- LOT-B002 (Mura Defect: Photo-Active FAIL)
  ('LOT-B002', 'CVD-Gate',         'EQ-CVD-03', 'OP-100', 'PASS', '2025-07-20 08:00:00'),
  ('LOT-B002', 'Photo-Gate',       'EQ-PHT-02', 'OP-101', 'PASS', '2025-07-20 10:00:00'),
  ('LOT-B002', 'Photo-Active',     'EQ-PHT-03', 'OP-104', 'FAIL', '2025-07-20 13:00:00'),
  ('LOT-B002', 'Etch-SD',          'EQ-ETH-02', 'OP-105', 'WARN', '2025-07-20 15:00:00'),
  -- LOT-C001 (Burn-in: OLED-Depo FAIL)
  ('LOT-C001', 'CVD-Gate',         'EQ-CVD-01', 'OP-100', 'PASS', '2025-08-01 08:00:00'),
  ('LOT-C001', 'Photo-Gate',       'EQ-PHT-01', 'OP-101', 'PASS', '2025-08-01 10:00:00'),
  ('LOT-C001', 'Etch-Gate',        'EQ-ETH-01', 'OP-102', 'PASS', '2025-08-01 12:00:00'),
  ('LOT-C001', 'OLED-Depo',        'EQ-OLT-01', 'OP-107', 'FAIL', '2025-08-02 08:00:00'),
  ('LOT-C001', 'Encap',            'EQ-ENC-01', 'OP-108', 'WARN', '2025-08-02 11:00:00'),
  -- LOT-C002 (Color Shift: Color-Filter FAIL)
  ('LOT-C002', 'CVD-Gate',         'EQ-CVD-02', 'OP-100', 'PASS', '2025-08-18 08:00:00'),
  ('LOT-C002', 'OLED-Depo',        'EQ-OLT-01', 'OP-107', 'WARN', '2025-08-19 08:00:00'),
  ('LOT-C002', 'Color-Filter',     'EQ-CFT-01', 'OP-109', 'FAIL', '2025-08-19 13:00:00'),
  -- LOT-D001 (Touch Defect: Touch-Pattern FAIL)
  ('LOT-D001', 'CVD-Gate',         'EQ-CVD-01', 'OP-100', 'PASS', '2025-09-05 08:00:00'),
  ('LOT-D001', 'OLED-Depo',        'EQ-OLT-02', 'OP-107', 'PASS', '2025-09-06 08:00:00'),
  ('LOT-D001', 'Touch-Pattern',    'EQ-TCH-01', 'OP-110', 'FAIL', '2025-09-06 14:00:00'),
  ('LOT-D001', 'Encap',            'EQ-ENC-01', 'OP-108', 'PASS', '2025-09-07 09:00:00'),
  -- LOT-D002 (Dark Spot: OLED-Depo FAIL)
  ('LOT-D002', 'CVD-Gate',         'EQ-CVD-02', 'OP-100', 'PASS', '2025-09-20 08:00:00'),
  ('LOT-D002', 'OLED-Depo',        'EQ-OLT-01', 'OP-107', 'FAIL', '2025-09-21 08:00:00'),
  ('LOT-D002', 'Dark-Current-Test','EQ-DCT-01', 'OP-111', 'WARN', '2025-09-21 14:00:00');

INSERT INTO return_history (product_id, return_reason, return_date, quantity, severity) VALUES
  ('LOT-A001', '픽셀 소등 불량 - TFT 불량 의심',          '2025-07-10', 50,  'HIGH'),
  ('LOT-A001', '화면 얼룩 - 공정 불량',                   '2025-07-15', 20,  'MEDIUM'),
  ('LOT-A002', '백라이트 불균일 - 셀 갭 불량',            '2025-07-20', 30,  'LOW'),
  ('LOT-A003', '수평 라인 상시 점등 - Etch-SD 공정 이상', '2025-08-01', 45,  'MEDIUM'),
  ('LOT-B001', '군집 픽셀 불량 - 마스크 오염 의심',       '2025-08-05', 80,  'HIGH'),
  ('LOT-B002', '화면 밝기 불균일 - Mura 불량',            '2025-08-25', 60,  'HIGH'),
  ('LOT-C001', '잔상 발생 - OLED 소자 열화',              '2025-09-10', 35,  'HIGH'),
  ('LOT-C002', '색감 이상 - 녹색 채널 색좌표 이탈',       '2025-09-22', 25,  'MEDIUM'),
  ('LOT-D001', '터치 미감지 - Touch 패턴 단선',           '2025-10-08', 40,  'HIGH'),
  ('LOT-D002', '암점 불량 - OLED 증착 이상',              '2025-10-18', 15,  'MEDIUM');

INSERT INTO test_results (product_id, test_type, result, measured_value, spec_min, spec_max, tested_at) VALUES
  -- LOT-A001
  ('LOT-A001', 'Vth-Uniformity',   'FAIL', 2.8,        1.0,       2.5,       '2025-06-02 09:00:00'),
  ('LOT-A001', 'Ion/Ioff-Ratio',   'PASS', 1200000,    1000000,   NULL,      '2025-06-02 09:30:00'),
  ('LOT-A001', 'Mobility',         'WARN', 0.45,       0.5,       1.5,       '2025-06-02 10:00:00'),
  -- LOT-A002
  ('LOT-A002', 'Cell-Gap',         'FAIL', 3.8,        4.0,       4.5,       '2025-06-16 09:00:00'),
  ('LOT-A002', 'Vth-Uniformity',   'PASS', 1.8,        1.0,       2.5,       '2025-06-16 09:30:00'),
  ('LOT-A002', 'Ion/Ioff-Ratio',   'PASS', 1050000,    1000000,   NULL,      '2025-06-16 10:00:00'),
  -- LOT-A003
  ('LOT-A003', 'Vth-Uniformity',   'PASS', 2.1,        1.0,       2.5,       '2025-06-29 09:00:00'),
  ('LOT-A003', 'Mobility',         'FAIL', 0.38,       0.5,       1.5,       '2025-06-29 09:30:00'),
  ('LOT-A003', 'CD-Uniformity',    'WARN', 98.5,       99.0,      101.0,     '2025-06-29 10:00:00'),
  -- LOT-B001
  ('LOT-B001', 'Particle-Count',   'FAIL', 18,         0,         10,        '2025-07-02 08:00:00'),
  ('LOT-B001', 'CD-Uniformity',    'WARN', 98.2,       99.0,      101.0,     '2025-07-02 08:30:00'),
  ('LOT-B001', 'Vth-Uniformity',   'PASS', 2.0,        1.0,       2.5,       '2025-07-02 09:00:00'),
  -- LOT-B002
  ('LOT-B002', 'Particle-Count',   'WARN', 12,         0,         10,        '2025-07-21 08:00:00'),
  ('LOT-B002', 'CD-Uniformity',    'FAIL', 97.1,       99.0,      101.0,     '2025-07-21 08:30:00'),
  ('LOT-B002', 'Ion/Ioff-Ratio',   'PASS', 1100000,    1000000,   NULL,      '2025-07-21 09:00:00'),
  -- LOT-C001
  ('LOT-C001', 'OLED-Luminance',   'FAIL', 380.0,      400.0,     500.0,     '2025-08-03 09:00:00'),
  ('LOT-C001', 'Color-Coordinate', 'PASS', 0.003,      0.0,       0.01,      '2025-08-03 09:30:00'),
  ('LOT-C001', 'Leakage-Current',  'WARN', 0.08,       0.0,       0.05,      '2025-08-03 10:00:00'),
  -- LOT-C002
  ('LOT-C002', 'Color-Coordinate', 'FAIL', 0.015,      0.0,       0.01,      '2025-08-20 09:00:00'),
  ('LOT-C002', 'OLED-Luminance',   'WARN', 395.0,      400.0,     500.0,     '2025-08-20 09:30:00'),
  ('LOT-C002', 'Cell-Gap',         'PASS', 4.2,        4.0,       4.5,       '2025-08-20 10:00:00'),
  -- LOT-D001
  ('LOT-D001', 'Touch-Sensitivity','FAIL', 1.2,        2.0,       5.0,       '2025-09-07 09:00:00'),
  ('LOT-D001', 'Vth-Uniformity',   'PASS', 2.0,        1.0,       2.5,       '2025-09-07 09:30:00'),
  ('LOT-D001', 'Mobility',         'PASS', 0.85,       0.5,       1.5,       '2025-09-07 10:00:00'),
  -- LOT-D002
  ('LOT-D002', 'Dark-Current',     'FAIL', 0.12,       0.0,       0.05,      '2025-09-22 09:00:00'),
  ('LOT-D002', 'OLED-Luminance',   'WARN', 392.0,      400.0,     500.0,     '2025-09-22 09:30:00'),
  ('LOT-D002', 'Ion/Ioff-Ratio',   'PASS', 1080000,    1000000,   NULL,      '2025-09-22 10:00:00');
