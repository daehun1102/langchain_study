-- ============================================================
-- NCS RAG Chatbot - Oracle DB Schema
-- ============================================================

-- 문서 레지스트리 (Document Registry)
-- Spring이 PDF 업로드 시 이 테이블에 먼저 INSERT하고 doc_id를 발급한다.
-- Python은 이 doc_id를 PGVector에 함께 저장하여 Oracle과 연결한다.
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

-- NCS 카테고리 마스터 데이터
CREATE TABLE ncs_categories (
    main_category VARCHAR2(100) NOT NULL,
    sub_category  VARCHAR2(100) NOT NULL,
    CONSTRAINT pk_ncs_cat PRIMARY KEY (main_category, sub_category)
);

-- 카테고리 초기 데이터 (9개)
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
