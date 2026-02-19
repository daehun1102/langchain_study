-- ============================================================
-- NCS RAG Chatbot - Oracle 21c Schema
-- ============================================================
-- [DBeaver 실행 방법]
--  1. 이 파일을 DBeaver SQL 편집기에서 열기
--  2. Oracle 21c 연결 선택 (우측 상단 연결 드롭다운)
--  3. Ctrl+A (전체 선택)
--  4. Alt+X (스크립트 실행)
-- ※ DBeaver 툴바의 작은 화살표(▼) → "Ignore errors during script execution" 체크
--   → 최초 실행 시 DROP 오류를 무시하고 나머지 구문을 계속 실행합니다.
-- ============================================================


-- ① 기존 테이블 제거
--    (PURGE: 휴지통 없이 즉시 삭제 / EXCEPTION으로 테이블이 없어도 계속 진행)
BEGIN
    BEGIN EXECUTE IMMEDIATE 'DROP TABLE documents PURGE';    EXCEPTION WHEN OTHERS THEN NULL; END;
    BEGIN EXECUTE IMMEDIATE 'DROP TABLE ncs_categories PURGE'; EXCEPTION WHEN OTHERS THEN NULL; END;
END;
/


-- ② 문서 레지스트리 테이블 생성
--    doc_id  : Spring이 UUID로 발급, Python의 PGVector와 연결 키
--    status  : PENDING(업로드됨) | INDEXED(벡터화 완료) | FAILED(벡터화 실패)
CREATE TABLE documents (
    doc_id        VARCHAR2(36)  PRIMARY KEY,
    filename      VARCHAR2(255) NOT NULL,
    main_category VARCHAR2(100),
    sub_category  VARCHAR2(100),
    page_count    NUMBER        DEFAULT 0,
    upload_date   DATE          DEFAULT SYSDATE,
    status        VARCHAR2(20)  DEFAULT 'PENDING'
);


-- ③ NCS 카테고리 마스터 테이블 생성
CREATE TABLE ncs_categories (
    main_category VARCHAR2(100) NOT NULL,
    sub_category  VARCHAR2(100) NOT NULL,
    CONSTRAINT pk_ncs_cat PRIMARY KEY (main_category, sub_category)
);


-- ④ 카테고리 초기 데이터 (9개)
INSERT INTO ncs_categories VALUES ('정보기술개발', 'SW아키텍쳐');
INSERT INTO ncs_categories VALUES ('정보기술개발', '응용SW엔지니어링');
INSERT INTO ncs_categories VALUES ('정보기술개발', '임베디드SW엔지니어링');
INSERT INTO ncs_categories VALUES ('정보기술관리', 'IT테스트');
INSERT INTO ncs_categories VALUES ('정보기술관리', 'IT품질보증');
INSERT INTO ncs_categories VALUES ('정보기술관리', 'IT프로젝트관리');
INSERT INTO ncs_categories VALUES ('직업기초능력', '문제해결능력');
INSERT INTO ncs_categories VALUES ('직업기초능력', '수리능력');
INSERT INTO ncs_categories VALUES ('직업기초능력', '의사소통능력');

COMMIT;


-- ⑤ 확인 쿼리 (실행 후 Results 탭에서 확인)
SELECT table_name
  FROM user_tables
 WHERE table_name IN ('DOCUMENTS', 'NCS_CATEGORIES')
 ORDER BY table_name;

SELECT main_category, sub_category
  FROM ncs_categories
 ORDER BY main_category, sub_category;
