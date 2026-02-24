-- db/dummy_data.sql
-- Oracle LMS DB 더미 데이터 — 테스트 및 개발 환경용

-- ============================================================
-- TB_EMPLOYEE (10명)
-- ============================================================
INSERT INTO TB_EMPLOYEE VALUES ('EMP001', '홍길동', '소프트웨어개발팀', '선임개발자',   DATE '2020-03-02', 'hong@company.com',  SYSDATE);
INSERT INTO TB_EMPLOYEE VALUES ('EMP002', '김철수', '소프트웨어개발팀', '주임개발자',   DATE '2021-07-01', 'kim@company.com',   SYSDATE);
INSERT INTO TB_EMPLOYEE VALUES ('EMP003', '이영희', 'QA팀',           '선임QA',      DATE '2019-01-15', 'lee@company.com',   SYSDATE);
INSERT INTO TB_EMPLOYEE VALUES ('EMP004', '박민수', '데이터분석팀',    '주임분석가',   DATE '2022-04-11', 'park@company.com',  SYSDATE);
INSERT INTO TB_EMPLOYEE VALUES ('EMP005', '최지연', '인프라팀',        '클라우드엔지니어', DATE '2020-09-07', 'choi@company.com', SYSDATE);
INSERT INTO TB_EMPLOYEE VALUES ('EMP006', '정수현', '소프트웨어개발팀', '사원',        DATE '2024-02-19', 'jung@company.com',  SYSDATE);
INSERT INTO TB_EMPLOYEE VALUES ('EMP007', '강동원', 'QA팀',           '주임QA',      DATE '2021-11-03', 'kang@company.com',  SYSDATE);
INSERT INTO TB_EMPLOYEE VALUES ('EMP008', '윤서연', '데이터분석팀',    '선임분석가',   DATE '2018-06-25', 'yoon@company.com',  SYSDATE);
INSERT INTO TB_EMPLOYEE VALUES ('EMP009', '조현우', '인프라팀',        '사원',        DATE '2023-08-14', 'cho@company.com',   SYSDATE);
INSERT INTO TB_EMPLOYEE VALUES ('EMP010', '한미래', 'HR팀',           '채점관리자',   DATE '2017-03-20', 'han@company.com',   SYSDATE);

-- ============================================================
-- TB_EDUCATION_HISTORY
-- ============================================================
-- EMP001 홍길동
INSERT INTO TB_EDUCATION_HISTORY VALUES (SEQ_HISTORY_ID.NEXTVAL, 'EMP001', 'Python 기반 소프트웨어 개발', 'SW-20-01', DATE '2023-03-01', DATE '2023-03-31', '완료',   95.0, SYSDATE);
INSERT INTO TB_EDUCATION_HISTORY VALUES (SEQ_HISTORY_ID.NEXTVAL, 'EMP001', 'Java 엔터프라이즈 개발',     'SW-20-02', DATE '2023-06-01', DATE '2023-06-30', '완료',   88.5, SYSDATE);
INSERT INTO TB_EDUCATION_HISTORY VALUES (SEQ_HISTORY_ID.NEXTVAL, 'EMP001', '클라우드 서비스 운용',       'IT-CL-01', DATE '2024-01-10', NULL,             '진행중', NULL, SYSDATE);
-- EMP002 김철수
INSERT INTO TB_EDUCATION_HISTORY VALUES (SEQ_HISTORY_ID.NEXTVAL, 'EMP002', 'Python 기반 소프트웨어 개발', 'SW-20-01', DATE '2023-03-01', DATE '2023-03-31', '완료',   78.0, SYSDATE);
INSERT INTO TB_EDUCATION_HISTORY VALUES (SEQ_HISTORY_ID.NEXTVAL, 'EMP002', '데이터베이스 설계 및 구축',  'DB-15-01', DATE '2023-09-01', DATE '2023-09-30', '완료',   82.0, SYSDATE);
INSERT INTO TB_EDUCATION_HISTORY VALUES (SEQ_HISTORY_ID.NEXTVAL, 'EMP002', 'UI/UX 설계',               'UX-10-01', DATE '2024-02-01', NULL,             '미이수', NULL, SYSDATE);
-- EMP003 이영희
INSERT INTO TB_EDUCATION_HISTORY VALUES (SEQ_HISTORY_ID.NEXTVAL, 'EMP003', '소프트웨어 테스트 설계',    'QA-20-01', DATE '2022-05-01', DATE '2022-05-31', '완료',   92.0, SYSDATE);
INSERT INTO TB_EDUCATION_HISTORY VALUES (SEQ_HISTORY_ID.NEXTVAL, 'EMP003', '테스트 자동화 구현',        'QA-20-02', DATE '2023-10-01', DATE '2023-10-31', '완료',   90.5, SYSDATE);
-- EMP004 박민수
INSERT INTO TB_EDUCATION_HISTORY VALUES (SEQ_HISTORY_ID.NEXTVAL, 'EMP004', '빅데이터 분석',             'DA-25-01', DATE '2023-04-01', DATE '2023-04-30', '완료',   85.0, SYSDATE);
INSERT INTO TB_EDUCATION_HISTORY VALUES (SEQ_HISTORY_ID.NEXTVAL, 'EMP004', '머신러닝 모델 개발',        'DA-25-02', DATE '2024-01-01', NULL,             '진행중', NULL, SYSDATE);
-- EMP006 정수현 (신입)
INSERT INTO TB_EDUCATION_HISTORY VALUES (SEQ_HISTORY_ID.NEXTVAL, 'EMP006', 'Python 기반 소프트웨어 개발', 'SW-20-01', DATE '2024-03-01', NULL,             '진행중', NULL, SYSDATE);

-- ============================================================
-- TB_ASSIGNMENT_SUBMISSION
-- ============================================================
INSERT INTO TB_ASSIGNMENT_SUBMISSION VALUES (SEQ_SUBMISSION_ID.NEXTVAL, 'EMP001', 'Python 기반 소프트웨어 개발', 'REST API 설계 및 구현',         DATE '2023-03-25', '제출',  '/uploads/EMP001/python_api.zip',  SYSDATE);
INSERT INTO TB_ASSIGNMENT_SUBMISSION VALUES (SEQ_SUBMISSION_ID.NEXTVAL, 'EMP001', 'Java 엔터프라이즈 개발',     'Spring Boot 마이크로서비스 구축', DATE '2023-06-28', '제출',  '/uploads/EMP001/spring_msa.zip',  SYSDATE);
INSERT INTO TB_ASSIGNMENT_SUBMISSION VALUES (SEQ_SUBMISSION_ID.NEXTVAL, 'EMP002', 'Python 기반 소프트웨어 개발', 'REST API 설계 및 구현',         DATE '2023-03-29', '제출',  '/uploads/EMP002/python_api.zip',  SYSDATE);
INSERT INTO TB_ASSIGNMENT_SUBMISSION VALUES (SEQ_SUBMISSION_ID.NEXTVAL, 'EMP002', 'UI/UX 설계',               'UI 프로토타입 제작',             NULL,             '미제출', NULL,                              SYSDATE);
INSERT INTO TB_ASSIGNMENT_SUBMISSION VALUES (SEQ_SUBMISSION_ID.NEXTVAL, 'EMP003', '소프트웨어 테스트 설계',    '테스트 케이스 시나리오 작성',    DATE '2022-05-28', '제출',  '/uploads/EMP003/test_case.xlsx',  SYSDATE);
INSERT INTO TB_ASSIGNMENT_SUBMISSION VALUES (SEQ_SUBMISSION_ID.NEXTVAL, 'EMP003', '테스트 자동화 구현',        'Selenium 자동화 스크립트',       DATE '2023-10-29', '제출',  '/uploads/EMP003/selenium_test.zip', SYSDATE);
INSERT INTO TB_ASSIGNMENT_SUBMISSION VALUES (SEQ_SUBMISSION_ID.NEXTVAL, 'EMP006', 'Python 기반 소프트웨어 개발', 'REST API 설계 및 구현',         NULL,             '미제출', NULL,                              SYSDATE);

-- ============================================================
-- TB_GRADING_RESULT
-- ============================================================
INSERT INTO TB_GRADING_RESULT VALUES (SEQ_RESULT_ID.NEXTVAL, 1, 'EMP001', 'EMP010', 96.0, 'Y', 'REST API 설계가 우수하며 코드 품질이 높습니다. 예외 처리 로직이 특히 잘 구현되었습니다.',  DATE '2023-03-30', SYSDATE);
INSERT INTO TB_GRADING_RESULT VALUES (SEQ_RESULT_ID.NEXTVAL, 2, 'EMP001', 'EMP010', 87.0, 'Y', 'MSA 구조 설계는 양호하나 서비스 간 통신 오류 처리 부분 보완 필요.',                      DATE '2023-06-30', SYSDATE);
INSERT INTO TB_GRADING_RESULT VALUES (SEQ_RESULT_ID.NEXTVAL, 3, 'EMP002', 'EMP010', 72.0, 'Y', 'API 기본 기능은 구현되었으나 인증/인가 처리가 미흡합니다.',                               DATE '2023-03-31', SYSDATE);
INSERT INTO TB_GRADING_RESULT VALUES (SEQ_RESULT_ID.NEXTVAL, 5, 'EMP003', 'EMP010', 93.0, 'Y', '테스트 케이스가 체계적으로 잘 작성되었습니다. 경계값 테스트 케이스 추가 권장.',             DATE '2022-05-31', SYSDATE);
INSERT INTO TB_GRADING_RESULT VALUES (SEQ_RESULT_ID.NEXTVAL, 6, 'EMP003', 'EMP010', 91.0, 'Y', 'Selenium 스크립트 품질 우수. Page Object 패턴 적용이 돋보입니다.',                       DATE '2023-10-31', SYSDATE);

COMMIT;
