-- db/dummy_data.sql
-- Oracle LMS DB 더미 데이터 — 테스트 및 개발 환경용
-- 재실행 안전: DELETE 후 INSERT

-- ============================================================
-- 기존 데이터 삭제 (FK 순서 역순)
-- ============================================================
DELETE FROM TB_GRADING_RESULT;
DELETE FROM TB_ASSIGNMENT_SUBMISSION;
DELETE FROM TB_EDUCATION_HISTORY;
DELETE FROM TB_EMPLOYEE;

-- 시퀀스 초기화
DROP SEQUENCE SEQ_HISTORY_ID;
DROP SEQUENCE SEQ_SUBMISSION_ID;
DROP SEQUENCE SEQ_RESULT_ID;
CREATE SEQUENCE SEQ_HISTORY_ID   START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE SEQ_SUBMISSION_ID START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE SEQ_RESULT_ID    START WITH 1 INCREMENT BY 1 NOCACHE;

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
-- TB_ASSIGNMENT_SUBMISSION (과제 본문 텍스트)
-- ============================================================

-- EMP001 홍길동 / Python 과정 / REST API 설계 및 구현 (우수 제출)
INSERT INTO TB_ASSIGNMENT_SUBMISSION (SUBMISSION_ID, EMPLOYEE_ID, COURSE_NAME, ASSIGNMENT_NAME, SUBMIT_DATE, STATUS, CONTENT, CREATED_AT)
VALUES (SEQ_SUBMISSION_ID.NEXTVAL, 'EMP001', 'Python 기반 소프트웨어 개발', 'REST API 설계 및 구현', DATE '2023-03-25', '제출',
'[과제] REST API 설계 및 구현

1. 설계 개요
FastAPI 프레임워크를 활용하여 직원 교육 이력 조회용 RESTful API를 설계 및 구현하였습니다.
HTTP 메서드별 역할을 명확히 분리하고, 상태 코드를 표준에 맞게 반환하도록 구성하였습니다.

2. 엔드포인트 설계
- GET    /api/v1/employees/{id}/history  : 직원 교육 이력 조회
- POST   /api/v1/employees               : 직원 등록
- PUT    /api/v1/employees/{id}          : 직원 정보 수정
- DELETE /api/v1/employees/{id}          : 직원 삭제

3. 구현 코드 (핵심 부분)
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import Optional
import uvicorn

app = FastAPI(title="직원 이력 API", version="1.0.0")

class EmployeeCreate(BaseModel):
    employee_id: str
    name: str
    department: str
    position: Optional[str] = None

@app.get("/api/v1/employees/{employee_id}/history", status_code=200)
async def get_employee_history(employee_id: str):
    employee = await get_employee_from_db(employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="직원을 찾을 수 없습니다.")
    history = await get_history_from_db(employee_id)
    return {"employee": employee, "history": history}

@app.post("/api/v1/employees", status_code=201)
async def create_employee(emp: EmployeeCreate):
    if await employee_exists(emp.employee_id):
        raise HTTPException(status_code=409, detail="이미 존재하는 사번입니다.")
    await save_employee(emp)
    return {"message": "직원이 등록되었습니다.", "employee_id": emp.employee_id}

4. 예외 처리 전략
- 404 Not Found    : 존재하지 않는 직원 ID 요청 시
- 409 Conflict     : 중복 사번 등록 시도 시
- 422 Unprocessable: 요청 바디 유효성 실패 시
- 500 Internal     : DB 연결 오류 등 서버 내부 오류 시

5. 테스트 결과
- 단위 테스트 12건 모두 통과 (pytest)
- 통합 테스트 5건 모두 통과
- 응답 시간: 평균 45ms (로컬 환경 기준)

6. NCS 능력단위 적용 사항
SW개발 능력단위 "서버프로그램 구현" 기준에 따라
인터페이스 설계, 예외 처리, 테스트 케이스 작성을 모두 수행하였습니다.',
SYSDATE);

-- EMP001 홍길동 / Java 과정 / Spring Boot 마이크로서비스 구축 (우수 제출)
INSERT INTO TB_ASSIGNMENT_SUBMISSION (SUBMISSION_ID, EMPLOYEE_ID, COURSE_NAME, ASSIGNMENT_NAME, SUBMIT_DATE, STATUS, CONTENT, CREATED_AT)
VALUES (SEQ_SUBMISSION_ID.NEXTVAL, 'EMP001', 'Java 엔터프라이즈 개발', 'Spring Boot 마이크로서비스 구축', DATE '2023-06-28', '제출',
'[과제] Spring Boot 마이크로서비스 구축

1. 아키텍처 설계
교육 관리 시스템을 3개의 독립 마이크로서비스로 분리하였습니다.
- employee-service  : 직원 정보 관리 (포트 8081)
- education-service : 교육 이력 관리 (포트 8082)
- gateway-service   : API 게이트웨이 + 라우팅 (포트 8080)

2. 서비스 구현 (employee-service 예시)
@SpringBootApplication
@EnableEurekaClient
public class EmployeeServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(EmployeeServiceApplication.class, args);
    }
}

@RestController
@RequestMapping("/employees")
@RequiredArgsConstructor
public class EmployeeController {
    private final EmployeeService employeeService;

    @GetMapping("/{id}")
    public ResponseEntity<EmployeeDTO> getEmployee(@PathVariable String id) {
        return ResponseEntity.ok(employeeService.findById(id));
    }
}

3. 서비스 간 통신
Spring Cloud OpenFeign을 사용하여 서비스 간 HTTP 통신을 구현하였습니다.

@FeignClient(name = "education-service")
public interface EducationClient {
    @GetMapping("/educations/{employeeId}")
    List<EducationDTO> getEducationHistory(@PathVariable String employeeId);
}

4. 오류 처리 한계
서비스 간 통신 오류 발생 시 Circuit Breaker 패턴이 미적용되어
cascade failure 가능성이 있습니다. 향후 Resilience4j 적용 예정입니다.

5. 테스트
- 단위 테스트: 각 서비스별 8건 (총 24건) 통과
- 통합 테스트: Testcontainers 활용, 4건 통과
- 서비스 간 통신 오류 시나리오 테스트: 미완성

6. NCS 능력단위 적용 사항
SW개발 능력단위 "통합 구현" 기준에 따라
인터페이스 설계 및 구현을 완료하였으나,
서비스 간 오류 처리 부분은 보완이 필요합니다.',
SYSDATE);

-- EMP002 김철수 / Python 과정 / REST API 설계 및 구현 (보통 수준 제출)
INSERT INTO TB_ASSIGNMENT_SUBMISSION (SUBMISSION_ID, EMPLOYEE_ID, COURSE_NAME, ASSIGNMENT_NAME, SUBMIT_DATE, STATUS, CONTENT, CREATED_AT)
VALUES (SEQ_SUBMISSION_ID.NEXTVAL, 'EMP002', 'Python 기반 소프트웨어 개발', 'REST API 설계 및 구현', DATE '2023-03-29', '제출',
'[과제] REST API 설계 및 구현

1. 구현 내용
Flask를 사용하여 간단한 직원 조회 API를 구현하였습니다.

2. 코드
from flask import Flask, jsonify, request
app = Flask(__name__)

employees = {
    "EMP001": {"name": "홍길동", "dept": "개발팀"},
    "EMP002": {"name": "김철수", "dept": "개발팀"}
}

@app.route("/employee/<emp_id>", methods=["GET"])
def get_employee(emp_id):
    emp = employees.get(emp_id)
    if emp:
        return jsonify(emp)
    return jsonify({"error": "not found"}), 404

@app.route("/employee", methods=["POST"])
def create_employee():
    data = request.json
    employees[data["id"]] = data
    return jsonify({"result": "ok"})

if __name__ == "__main__":
    app.run(debug=True)

3. 미구현 사항
- 인증/인가 처리 미구현 (JWT 토큰 방식 예정)
- 입력값 유효성 검사 미흡
- DB 연동 없이 메모리 딕셔너리만 사용
- 에러 응답 형식 비표준

4. NCS 적용 사항
기본적인 HTTP 메서드 활용과 상태 코드 반환은 구현하였으나
보안 및 데이터 영속성 부분이 NCS SW개발 기준에 미달합니다.',
SYSDATE);

-- EMP002 김철수 / UI/UX 설계 / UI 프로토타입 제작 (미제출)
INSERT INTO TB_ASSIGNMENT_SUBMISSION (SUBMISSION_ID, EMPLOYEE_ID, COURSE_NAME, ASSIGNMENT_NAME, SUBMIT_DATE, STATUS, CONTENT, CREATED_AT)
VALUES (SEQ_SUBMISSION_ID.NEXTVAL, 'EMP002', 'UI/UX 설계', 'UI 프로토타입 제작', NULL, '미제출', NULL, SYSDATE);

-- EMP003 이영희 / 소프트웨어 테스트 설계 / 테스트 케이스 시나리오 작성 (우수 제출)
INSERT INTO TB_ASSIGNMENT_SUBMISSION (SUBMISSION_ID, EMPLOYEE_ID, COURSE_NAME, ASSIGNMENT_NAME, SUBMIT_DATE, STATUS, CONTENT, CREATED_AT)
VALUES (SEQ_SUBMISSION_ID.NEXTVAL, 'EMP003', '소프트웨어 테스트 설계', '테스트 케이스 시나리오 작성', DATE '2022-05-28', '제출',
'[과제] 테스트 케이스 시나리오 작성

1. 테스트 대상
직원 교육 이력 조회 API (GET /api/v1/employees/{id}/history)

2. 테스트 케이스 목록

[TC-001] 정상 조회 — 유효한 사번으로 이력 조회
  - 입력: employee_id = "EMP001"
  - 기대 결과: 200 OK, 교육 이력 목록 반환
  - 결과: PASS

[TC-002] 존재하지 않는 사번 조회
  - 입력: employee_id = "EMP999"
  - 기대 결과: 404 Not Found, 오류 메시지 반환
  - 결과: PASS

[TC-003] 빈 사번 입력
  - 입력: employee_id = ""
  - 기대 결과: 400 Bad Request
  - 결과: PASS

[TC-004] 교육 이력 없는 직원 조회
  - 입력: employee_id = "EMP010"
  - 기대 결과: 200 OK, 빈 배열 반환
  - 결과: PASS

[TC-005] 특수문자 포함 사번 (SQL Injection 시도)
  - 입력: employee_id = "EMP001'' OR 1=1 --"
  - 기대 결과: 400 Bad Request 또는 404 Not Found
  - 결과: PASS (Prepared Statement로 방어됨)

[TC-006] 이름으로 조회 (한글)
  - 입력: identifier = "홍길동"
  - 기대 결과: 200 OK, 해당 직원 이력 반환
  - 결과: PASS

[TC-007] 경계값 — 가장 오래된 이력 포함 여부
  - 입력: employee_id = "EMP001"
  - 기대 결과: 전체 이력 반환 (날짜순 정렬 확인)
  - 결과: PASS

[TC-008] 동시 다수 요청 (100 concurrent)
  - 기대 결과: 모든 요청 200 OK, 응답시간 500ms 이내
  - 결과: PASS (평균 180ms)

3. 결함 발견 사항
- 이름 중복 시 첫 번째 직원만 반환하는 동작 확인
  → 중복 이름 처리 정책 명문화 필요 (결함 등록: BUG-2022-011)

4. NCS 능력단위 적용 사항
QA 능력단위 "테스트 케이스 설계" 기준에 따라
동등 분할, 경계값 분석, 오류 추측 기법을 모두 적용하였습니다.
경계값 테스트와 보안 테스트 케이스를 추가로 보강할 예정입니다.',
SYSDATE);

-- EMP003 이영희 / 테스트 자동화 구현 / Selenium 자동화 스크립트 (우수 제출)
INSERT INTO TB_ASSIGNMENT_SUBMISSION (SUBMISSION_ID, EMPLOYEE_ID, COURSE_NAME, ASSIGNMENT_NAME, SUBMIT_DATE, STATUS, CONTENT, CREATED_AT)
VALUES (SEQ_SUBMISSION_ID.NEXTVAL, 'EMP003', '테스트 자동화 구현', 'Selenium 자동화 스크립트', DATE '2023-10-29', '제출',
'[과제] Selenium 자동화 스크립트 구현

1. 구현 개요
교육 관리 시스템 웹 UI의 주요 기능을 Selenium WebDriver와
Page Object Model(POM) 패턴을 적용하여 자동화하였습니다.

2. 디렉토리 구조
tests/
  pages/
    login_page.py      # 로그인 페이지 POM
    employee_page.py   # 직원 조회 페이지 POM
    history_page.py    # 이력 조회 페이지 POM
  tests/
    test_login.py
    test_employee_search.py
    test_history_view.py
  conftest.py

3. Page Object 구현 예시
# pages/employee_page.py
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class EmployeePage:
    SEARCH_INPUT = (By.ID, "employee-search")
    SEARCH_BUTTON = (By.ID, "btn-search")
    RESULT_TABLE  = (By.CSS_SELECTOR, "table.employee-list")

    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)

    def search_employee(self, identifier: str):
        field = self.wait.until(EC.element_to_be_clickable(self.SEARCH_INPUT))
        field.clear()
        field.send_keys(identifier)
        self.driver.find_element(*self.SEARCH_BUTTON).click()

    def get_result_rows(self):
        table = self.wait.until(EC.visibility_of_element_located(self.RESULT_TABLE))
        return table.find_elements(By.TAG_NAME, "tr")[1:]  # 헤더 제외

4. 테스트 케이스
# tests/test_employee_search.py
import pytest
from pages.employee_page import EmployeePage

class TestEmployeeSearch:
    def test_search_by_employee_id(self, driver, base_url):
        driver.get(f"{base_url}/employees")
        page = EmployeePage(driver)
        page.search_employee("EMP001")
        rows = page.get_result_rows()
        assert len(rows) >= 1
        assert "홍길동" in rows[0].text

    def test_search_no_result(self, driver, base_url):
        driver.get(f"{base_url}/employees")
        page = EmployeePage(driver)
        page.search_employee("EMP999")
        rows = page.get_result_rows()
        assert len(rows) == 0

5. 실행 결과
- 총 18개 테스트 케이스, 18건 통과
- CI/CD 파이프라인 연동 완료 (GitHub Actions)
- 크로스 브라우저 테스트: Chrome, Firefox 모두 통과

6. NCS 능력단위 적용 사항
QA 능력단위 "테스트 자동화" 기준에 따라
Page Object 패턴으로 유지보수성을 확보하였으며
CI 파이프라인 통합까지 완료하였습니다.',
SYSDATE);

-- EMP006 정수현 / Python 과정 / REST API 설계 및 구현 (미제출 — 신입)
INSERT INTO TB_ASSIGNMENT_SUBMISSION (SUBMISSION_ID, EMPLOYEE_ID, COURSE_NAME, ASSIGNMENT_NAME, SUBMIT_DATE, STATUS, CONTENT, CREATED_AT)
VALUES (SEQ_SUBMISSION_ID.NEXTVAL, 'EMP006', 'Python 기반 소프트웨어 개발', 'REST API 설계 및 구현', NULL, '미제출', NULL, SYSDATE);

-- ============================================================
-- TB_GRADING_RESULT (AI 채점 결과)
-- GRADER_ID = 'EMP010' (채점관리자 한미래 — AI 채점 결과 등록 담당)
-- ============================================================

-- EMP001 / REST API (SUBMISSION_ID=1)
INSERT INTO TB_GRADING_RESULT VALUES (
    SEQ_RESULT_ID.NEXTVAL, 1, 'EMP001', 'EMP010', 96.0, 'Y',
    'NCS SW개발 능력단위 "서버프로그램 구현" 기준 평가 결과:
[우수] HTTP 메서드 및 상태 코드 표준 준수 (GET/POST/PUT/DELETE, 200/201/404/409)
[우수] 예외 처리 전략이 구체적이며 NCS 요구사항을 충족함
[우수] 단위/통합 테스트 모두 수행하여 품질 검증 완료
[개선 권고] 인증(Authentication) 처리 방식 명시 필요 — JWT 또는 OAuth2 적용 권장
종합: NCS 서버프로그램 구현 능력단위 수준 4 기준을 충족하며 우수한 구현입니다.',
    DATE '2023-03-30', SYSDATE);

-- EMP001 / Spring Boot MSA (SUBMISSION_ID=2)
INSERT INTO TB_GRADING_RESULT VALUES (
    SEQ_RESULT_ID.NEXTVAL, 2, 'EMP001', 'EMP010', 87.0, 'Y',
    'NCS SW개발 능력단위 "통합 구현" 기준 평가 결과:
[우수] 마이크로서비스 분리 설계(3개 서비스)가 적절하며 책임 분리가 명확함
[우수] Spring Cloud OpenFeign을 활용한 서비스 간 통신 구현
[미흡] Circuit Breaker 패턴 미적용 — cascade failure 위험 존재
[미흡] 서비스 간 통신 오류 시나리오 테스트 미완성
[개선 권고] Resilience4j 적용 및 오류 전파 차단 로직 구현 필요
종합: 기본 MSA 구조는 양호하나 장애 대응 설계 보완이 필요합니다.',
    DATE '2023-06-30', SYSDATE);

-- EMP002 / REST API (SUBMISSION_ID=3)
INSERT INTO TB_GRADING_RESULT VALUES (
    SEQ_RESULT_ID.NEXTVAL, 3, 'EMP002', 'EMP010', 72.0, 'Y',
    'NCS SW개발 능력단위 "서버프로그램 구현" 기준 평가 결과:
[양호] 기본 CRUD HTTP 메서드 및 상태 코드 구현
[미흡] 인증/인가(Authentication/Authorization) 처리 완전 누락
[미흡] 입력값 유효성 검사 부재 — SQL Injection 등 보안 취약점 위험
[미흡] 데이터 영속성 미구현 (메모리 딕셔너리만 사용)
[미흡] 에러 응답 형식이 비표준적 (NCS 인터페이스 설계 기준 불충족)
[개선 권고] DB 연동, JWT 인증 구현, 표준 에러 응답 형식 적용 필요
종합: 기본 기능은 구현되었으나 실무 수준의 보완이 필요합니다.',
    DATE '2023-03-31', SYSDATE);

-- EMP003 / 테스트 케이스 (SUBMISSION_ID=5)
INSERT INTO TB_GRADING_RESULT VALUES (
    SEQ_RESULT_ID.NEXTVAL, 5, 'EMP003', 'EMP010', 93.0, 'Y',
    'NCS QA 능력단위 "테스트 케이스 설계" 기준 평가 결과:
[우수] 동등 분할, 경계값 분석, 오류 추측 기법 모두 적용
[우수] 보안 테스트(SQL Injection) 케이스 포함 — NCS 요구 수준 초과
[우수] 성능 테스트(100 concurrent) 케이스 포함
[우수] 결함 발견 및 BUG 등록 절차 준수
[개선 권고] 경계값 테스트 케이스 추가 확장 권장 (최대값, 최소값, 초과값)
[개선 권고] 테스트 커버리지 측정 도구 활용 권장
종합: NCS 테스트 케이스 설계 능력단위 수준 4 기준을 충족하는 우수한 작업입니다.',
    DATE '2022-05-31', SYSDATE);

-- EMP003 / Selenium (SUBMISSION_ID=6)
INSERT INTO TB_GRADING_RESULT VALUES (
    SEQ_RESULT_ID.NEXTVAL, 6, 'EMP003', 'EMP010', 91.0, 'Y',
    'NCS QA 능력단위 "테스트 자동화" 기준 평가 결과:
[우수] Page Object Model 패턴 적용으로 유지보수성 확보
[우수] CI/CD(GitHub Actions) 파이프라인 통합 완료
[우수] 크로스 브라우저 테스트(Chrome, Firefox) 수행
[우수] 18개 테스트 케이스 100% 통과
[개선 권고] 테스트 실패 시 스크린샷 자동 캡처 기능 추가 권장
[개선 권고] 테스트 실행 보고서(Allure Report 등) 생성 자동화 권장
종합: NCS 테스트 자동화 능력단위 수준 4 기준을 충족하며 CI 연동까지 완성한 우수한 구현입니다.',
    DATE '2023-10-31', SYSDATE);

COMMIT;
