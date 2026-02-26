-- db/schema.sql
-- Oracle LMS DB 스키마 — NCS 직원 관리 시스템
-- 이미 실행된 환경에서도 재실행 가능 (idempotent)

-- ============================================================
-- 시퀀스 (없으면 생성)
-- ============================================================
BEGIN
    EXECUTE IMMEDIATE 'CREATE SEQUENCE SEQ_HISTORY_ID START WITH 1 INCREMENT BY 1 NOCACHE';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/
BEGIN
    EXECUTE IMMEDIATE 'CREATE SEQUENCE SEQ_SUBMISSION_ID START WITH 1 INCREMENT BY 1 NOCACHE';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/
BEGIN
    EXECUTE IMMEDIATE 'CREATE SEQUENCE SEQ_RESULT_ID START WITH 1 INCREMENT BY 1 NOCACHE';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

-- ============================================================
-- TB_EMPLOYEE : 직원 기본정보 (없으면 생성)
-- ============================================================
BEGIN
    EXECUTE IMMEDIATE '
        CREATE TABLE TB_EMPLOYEE (
            EMPLOYEE_ID  VARCHAR2(20)  NOT NULL,
            NAME         VARCHAR2(50)  NOT NULL,
            DEPARTMENT   VARCHAR2(100) NOT NULL,
            POSITION     VARCHAR2(50),
            JOIN_DATE    DATE          NOT NULL,
            EMAIL        VARCHAR2(100),
            CREATED_AT   DATE          DEFAULT SYSDATE NOT NULL,
            CONSTRAINT PK_EMPLOYEE       PRIMARY KEY (EMPLOYEE_ID),
            CONSTRAINT UQ_EMPLOYEE_EMAIL UNIQUE (EMAIL)
        )';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

-- ============================================================
-- TB_EDUCATION_HISTORY : 교육 이수 내역 (없으면 생성)
-- ============================================================
BEGIN
    EXECUTE IMMEDIATE '
        CREATE TABLE TB_EDUCATION_HISTORY (
            HISTORY_ID      NUMBER        NOT NULL,
            EMPLOYEE_ID     VARCHAR2(20)  NOT NULL,
            COURSE_NAME     VARCHAR2(200) NOT NULL,
            NCS_CODE        VARCHAR2(50),
            START_DATE      DATE,
            COMPLETION_DATE DATE,
            STATUS          VARCHAR2(20)  NOT NULL,
            SCORE           NUMBER(5,2),
            CREATED_AT      DATE          DEFAULT SYSDATE NOT NULL,
            CONSTRAINT PK_EDUCATION_HISTORY PRIMARY KEY (HISTORY_ID),
            CONSTRAINT FK_EDU_EMPLOYEE      FOREIGN KEY (EMPLOYEE_ID) REFERENCES TB_EMPLOYEE(EMPLOYEE_ID),
            CONSTRAINT CK_EDU_STATUS        CHECK (STATUS IN (''완료'', ''진행중'', ''미이수''))
        )';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

-- ============================================================
-- TB_ASSIGNMENT_SUBMISSION : 과제 제출
-- FILE_PATH 컬럼 → CONTENT CLOB 으로 변경
-- ============================================================
BEGIN
    EXECUTE IMMEDIATE '
        CREATE TABLE TB_ASSIGNMENT_SUBMISSION (
            SUBMISSION_ID   NUMBER        NOT NULL,
            EMPLOYEE_ID     VARCHAR2(20)  NOT NULL,
            COURSE_NAME     VARCHAR2(200) NOT NULL,
            ASSIGNMENT_NAME VARCHAR2(200) NOT NULL,
            SUBMIT_DATE     DATE,
            STATUS          VARCHAR2(20)  NOT NULL,
            CONTENT         CLOB,
            CREATED_AT      DATE          DEFAULT SYSDATE NOT NULL,
            CONSTRAINT PK_ASSIGNMENT_SUBMISSION PRIMARY KEY (SUBMISSION_ID),
            CONSTRAINT FK_SUBMIT_EMPLOYEE       FOREIGN KEY (EMPLOYEE_ID) REFERENCES TB_EMPLOYEE(EMPLOYEE_ID),
            CONSTRAINT CK_SUBMIT_STATUS         CHECK (STATUS IN (''제출'', ''미제출'', ''반려''))
        )';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/
-- 기존 테이블에 CONTENT 컬럼이 없으면 추가
BEGIN
    EXECUTE IMMEDIATE 'ALTER TABLE TB_ASSIGNMENT_SUBMISSION ADD (CONTENT CLOB)';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/
-- 기존 FILE_PATH 컬럼이 있으면 제거
BEGIN
    EXECUTE IMMEDIATE 'ALTER TABLE TB_ASSIGNMENT_SUBMISSION DROP COLUMN FILE_PATH';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

-- ============================================================
-- TB_GRADING_RESULT : 채점 결과 (없으면 생성)
-- ============================================================
BEGIN
    EXECUTE IMMEDIATE '
        CREATE TABLE TB_GRADING_RESULT (
            RESULT_ID     NUMBER        NOT NULL,
            SUBMISSION_ID NUMBER        NOT NULL,
            EMPLOYEE_ID   VARCHAR2(20)  NOT NULL,
            GRADER_ID     VARCHAR2(20)  NOT NULL,
            SCORE         NUMBER(5,2),
            PASS_YN       CHAR(1)       NOT NULL,
            FEEDBACK      VARCHAR2(4000),
            GRADED_DATE   DATE,
            CREATED_AT    DATE          DEFAULT SYSDATE NOT NULL,
            CONSTRAINT PK_GRADING_RESULT   PRIMARY KEY (RESULT_ID),
            CONSTRAINT FK_GRADE_SUBMISSION FOREIGN KEY (SUBMISSION_ID) REFERENCES TB_ASSIGNMENT_SUBMISSION(SUBMISSION_ID),
            CONSTRAINT FK_GRADE_EMPLOYEE   FOREIGN KEY (EMPLOYEE_ID)   REFERENCES TB_EMPLOYEE(EMPLOYEE_ID),
            CONSTRAINT FK_GRADE_GRADER     FOREIGN KEY (GRADER_ID)     REFERENCES TB_EMPLOYEE(EMPLOYEE_ID),
            CONSTRAINT CK_PASS_YN          CHECK (PASS_YN IN (''Y'', ''N''))
        )';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/
