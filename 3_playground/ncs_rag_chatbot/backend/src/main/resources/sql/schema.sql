-- ============================================================
-- NCS RAG Chatbot - Oracle DB Schema
-- DBeaver에서 실행: 전체 선택(Ctrl+A) 후 SQL 실행(Alt+X 또는 Ctrl+Enter)
-- 재실행 시: 상단 DROP 블록이 기존 테이블을 먼저 제거합니다.
-- ============================================================


-- ① 기존 테이블 제거 (재실행 시 사용 / 최초 실행 시 오류 무시)
BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE documents';
EXCEPTION
    WHEN OTHERS THEN NULL;
END;
/

BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE ncs_categories';
EXCEPTION
    WHEN OTHERS THEN NULL;
END;
/


-- ② 테이블 생성

-- 문서 레지스트리 (Document Registry)
-- Spring이 PDF 업로드 시 INSERT하여 doc_id를 발급한다.
-- Python은 이 doc_id를 PGVector에 함께 저장하여 연결한다.
-- status: PENDING(업로드됨) | INDEXED(벡터화 완료) | FAILED(벡터화 실패)
CREATE TABLE documents (
    doc_id        VARCHAR2(36)  PRIMARY KEY,
    filename      VARCHAR2(255) NOT NULL,
    main_category VARCHAR2(100),
    sub_category  VARCHAR2(100),
    page_count    NUMBER        DEFAULT 0,
    upload_date   DATE          DEFAULT SYSDATE,
    status        VARCHAR2(20)  DEFAULT 'PENDING'
);

-- NCS 카테고리 마스터
CREATE TABLE ncs_categories (
    main_category VARCHAR2(100) NOT NULL,
    sub_category  VARCHAR2(100) NOT NULL,
    CONSTRAINT pk_ncs_cat PRIMARY KEY (main_category, sub_category)
);


-- ③ 카테고리 초기 데이터 (9개)
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


-- ④ 확인 쿼리
SELECT table_name FROM user_tables WHERE table_name IN ('DOCUMENTS', 'NCS_CATEGORIES');
SELECT * FROM ncs_categories ORDER BY main_category, sub_category;
