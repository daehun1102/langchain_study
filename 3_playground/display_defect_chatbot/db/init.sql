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
  ('LOT-B001', 'SDC-QLED-65B', '65inch', '2025-07-01'),
  ('LOT-C001', 'SDC-OLED-27C', '27inch', '2025-08-01')
ON CONFLICT DO NOTHING;

INSERT INTO defect_cases (product_id, company, defect_type, description) VALUES
  ('LOT-A001', 'A사', 'Dead Pixel', '화면 좌측 상단 영역 픽셀 소등 불량 10개'),
  ('LOT-A002', 'B사', 'Hot Pixel', '화면 중앙부 흰 점 불량 5개'),
  ('LOT-B001', 'A사', 'Cluster Defect', '우측 하단 군집 불량 50x50px')
ON CONFLICT DO NOTHING;

INSERT INTO process_history (product_id, process_step, equipment_id, operator_id, result, measured_at) VALUES
  ('LOT-A001', 'CVD-Gate', 'EQ-CVD-01', 'OP-100', 'PASS', '2025-06-01 08:00:00'),
  ('LOT-A001', 'Photo-Gate', 'EQ-PHT-02', 'OP-101', 'PASS', '2025-06-01 10:00:00'),
  ('LOT-A001', 'Etch-Gate', 'EQ-ETH-01', 'OP-102', 'FAIL', '2025-06-01 12:00:00'),
  ('LOT-A001', 'CVD-Active', 'EQ-CVD-01', 'OP-100', 'WARN', '2025-06-01 14:00:00'),
  ('LOT-A001', 'Ion-Implant', 'EQ-ION-01', 'OP-103', 'PASS', '2025-06-01 16:00:00'),
  ('LOT-A002', 'CVD-Gate', 'EQ-CVD-02', 'OP-100', 'PASS', '2025-06-15 08:00:00'),
  ('LOT-A002', 'Cell-Align', 'EQ-ALN-01', 'OP-104', 'FAIL', '2025-06-15 14:00:00'),
  ('LOT-B001', 'Photo-Gate', 'EQ-PHT-01', 'OP-101', 'WARN', '2025-07-01 09:00:00');

INSERT INTO return_history (product_id, return_reason, return_date, quantity, severity) VALUES
  ('LOT-A001', '픽셀 소등 불량 - TFT 불량 의심', '2025-07-10', 50, 'HIGH'),
  ('LOT-A001', '화면 얼룩 - 공정 불량', '2025-07-15', 20, 'MEDIUM'),
  ('LOT-A002', '백라이트 불균일', '2025-07-20', 30, 'LOW'),
  ('LOT-B001', '군집 픽셀 불량 - 마스크 오염 의심', '2025-08-05', 80, 'HIGH');

INSERT INTO test_results (product_id, test_type, result, measured_value, spec_min, spec_max, tested_at) VALUES
  ('LOT-A001', 'Vth-Uniformity', 'FAIL', 2.8, 1.0, 2.5, '2025-06-02 09:00:00'),
  ('LOT-A001', 'Ion/Ioff-Ratio', 'PASS', 1200000, 1000000, NULL, '2025-06-02 09:30:00'),
  ('LOT-A001', 'Mobility', 'WARN', 0.45, 0.5, 1.5, '2025-06-02 10:00:00'),
  ('LOT-A002', 'Cell-Gap', 'FAIL', 3.8, 4.0, 4.5, '2025-06-16 09:00:00'),
  ('LOT-A002', 'Vth-Uniformity', 'PASS', 1.8, 1.0, 2.5, '2025-06-16 09:30:00'),
  ('LOT-B001', 'Particle-Count', 'FAIL', 18, 0, 10, '2025-07-02 08:00:00'),
  ('LOT-B001', 'CD-Uniformity', 'WARN', 98.2, 99.0, 101.0, '2025-07-02 08:30:00');
