# NCS RAG Chatbot — 아키텍처 마이그레이션 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** FastAPI 단일 서버를 Spring Boot API Gateway + Python AI Server 멀티 서버 아키텍처로 마이그레이션하고, Oracle/PGVector DB 분리, Redis 프롬프트 관리, Arize Phoenix 모니터링을 순차적으로 구축한다.

**Architecture:** Spring Boot(8080)가 모든 외부 API의 단일 진입점으로 PDF CRUD(Oracle)와 채팅 프록시(Python 위임)를 담당한다. Python FastAPI(8000)는 순수 AI 추론과 PGVector 벡터 검색만 담당하며 외부에 노출되지 않는다. Document Registry 패턴으로 Oracle(메타데이터/doc_id)과 PGVector(임베딩/doc_id ref)를 연결한다.

**Tech Stack:**
- Spring Boot 4.0.2 / Java 17 / MVC / MyBatis / RestClient / spring-data-redis
- Python 3.10+ / FastAPI / LangChain / langchain-postgres / redis-py / arize-phoenix
- Oracle DB (ojdbc11) / PostgreSQL+pgvector / Redis / Arize Phoenix (Docker)

---

## Phase 의존 관계

```
Phase 1 → Phase 2 → Phase 4   (메인 흐름, 순차 진행)
Phase 3 ──────────────────────  (Phase 1 완료 후 독립 진행 가능)
Phase 5 ──────────────────────  (Phase 2 완료 후 진행)
```

---

# Phase 1: Spring MVC 기반 구조 + Oracle 연동

> 목표: Spring Boot에서 Oracle DB를 통해 PDF 문서 메타데이터를 CRUD한다.
> AI 기능은 이 단계에서 다루지 않는다.

---

## Task 1.1: pom.xml 의존성 추가 및 application.properties 설정

**Files:**
- Modify: `backend/pom.xml`
- Modify: `backend/src/main/resources/application.properties`

**Step 1: pom.xml에 파일 업로드 의존성 추가**

`backend/pom.xml`의 `<dependencies>` 안에 추가:

```xml
<!-- 파일 업로드 지원 (MultipartFile) - webmvc에 포함되어 있으나 명시적 설정을 위해 -->
<dependency>
    <groupId>commons-fileupload</groupId>
    <artifactId>commons-fileupload</artifactId>
    <version>1.5</version>
</dependency>
```

**Step 2: application.properties 설정**

`backend/src/main/resources/application.properties`를 아래로 교체:

```properties
spring.application.name=backend
server.port=8080

# Oracle DataSource
spring.datasource.url=jdbc:oracle:thin:@localhost:1521:xe
spring.datasource.username=system
spring.datasource.password=oracle
spring.datasource.driver-class-name=oracle.jdbc.OracleDriver

# MyBatis
mybatis.mapper-locations=classpath:mapper/*.xml
mybatis.type-aliases-package=com.ncs.backend.model
mybatis.configuration.map-underscore-to-camel-case=true

# 파일 업로드 크기 제한
spring.servlet.multipart.max-file-size=50MB
spring.servlet.multipart.max-request-size=50MB

# PDF 저장 경로 (Spring과 Python이 공유하는 로컬 경로)
app.upload-dir=./uploads

# Python AI 서버 URL
app.python-server-url=http://localhost:8000

# CORS
app.cors.allowed-origins=http://localhost:5173
```

**Step 3: uploads 디렉토리 생성**

```bash
mkdir -p backend/uploads
echo "uploads/" >> .gitignore
```

**Step 4: 서버 기동 확인**

```bash
cd backend
./mvnw spring-boot:run
```

Expected: `Started BackendApplication` 로그 출력, `http://localhost:8080/actuator/health` 접근 가능

**Step 5: Commit**

```bash
git add backend/pom.xml backend/src/main/resources/application.properties .gitignore
git commit -m "feat(spring): Oracle DataSource 및 기본 설정 추가"
```

---

## Task 1.2: Oracle DDL 실행

**Files:**
- Create: `backend/src/main/resources/sql/schema.sql`

**Step 1: DDL 파일 작성**

`backend/src/main/resources/sql/schema.sql`:

```sql
-- 문서 레지스트리 (Document Registry)
-- Spring이 PDF 업로드 시 이 테이블에 먼저 INSERT하고 doc_id를 발급한다
-- Python은 이 doc_id를 PGVector에 함께 저장하여 연결한다
CREATE TABLE documents (
    doc_id        VARCHAR2(36)  PRIMARY KEY,
    filename      VARCHAR2(255) NOT NULL,
    main_category VARCHAR2(100),
    sub_category  VARCHAR2(100),
    page_count    NUMBER        DEFAULT 0,
    upload_date   DATE          DEFAULT SYSDATE,
    status        VARCHAR2(20)  DEFAULT 'PENDING'
    -- status 값: PENDING(업로드됨) | INDEXED(벡터화 완료) | FAILED(벡터화 실패)
);

-- NCS 카테고리 마스터 데이터
CREATE TABLE ncs_categories (
    main_category VARCHAR2(100) NOT NULL,
    sub_category  VARCHAR2(100) NOT NULL,
    CONSTRAINT pk_ncs_cat PRIMARY KEY (main_category, sub_category)
);

-- 카테고리 초기 데이터
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
```

**Step 2: Oracle SQL Developer 또는 sqlplus로 DDL 실행**

```bash
# sqlplus 사용 예시
sqlplus system/oracle@localhost:1521/xe @backend/src/main/resources/sql/schema.sql
```

**Step 3: 테이블 생성 확인**

```sql
SELECT table_name FROM user_tables WHERE table_name IN ('DOCUMENTS', 'NCS_CATEGORIES');
SELECT * FROM ncs_categories;
```

Expected: 두 테이블 존재, ncs_categories에 9개 행

**Step 4: Commit**

```bash
git add backend/src/main/resources/sql/schema.sql
git commit -m "feat(db): Oracle DDL 작성 (documents, ncs_categories)"
```

---

## Task 1.3: Model 클래스 생성

**Files:**
- Create: `backend/src/main/java/com/ncs/backend/model/Document.java`
- Create: `backend/src/main/java/com/ncs/backend/model/Category.java`

**Step 1: Document 모델 작성**

`backend/src/main/java/com/ncs/backend/model/Document.java`:

```java
package com.ncs.backend.model;

import lombok.Data;
import java.util.Date;

@Data
public class Document {
    private String docId;
    private String filename;
    private String mainCategory;
    private String subCategory;
    private int pageCount;
    private Date uploadDate;
    private String status;  // PENDING | INDEXED | FAILED
}
```

**Step 2: Category 모델 작성**

`backend/src/main/java/com/ncs/backend/model/Category.java`:

```java
package com.ncs.backend.model;

import lombok.Data;

@Data
public class Category {
    private String mainCategory;
    private String subCategory;
}
```

**Step 3: Commit**

```bash
git add backend/src/main/java/com/ncs/backend/model/
git commit -m "feat(spring): Document, Category 모델 클래스 추가"
```

---

## Task 1.4: DocumentMapper 구현 (MyBatis)

**Files:**
- Create: `backend/src/main/java/com/ncs/backend/mapper/DocumentMapper.java`
- Create: `backend/src/main/resources/mapper/DocumentMapper.xml`

**Step 1: DocumentMapper 인터페이스 작성**

`backend/src/main/java/com/ncs/backend/mapper/DocumentMapper.java`:

```java
package com.ncs.backend.mapper;

import com.ncs.backend.model.Document;
import org.apache.ibatis.annotations.Mapper;
import java.util.List;

@Mapper
public interface DocumentMapper {
    void insert(Document document);
    List<Document> findAll();
    Document findById(String docId);
    void updateStatus(String docId, String status);
    void delete(String docId);
    List<String> findDocIdsByCategory(String mainCategory, String subCategory);
}
```

**Step 2: DocumentMapper XML 작성**

`backend/src/main/resources/mapper/DocumentMapper.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN"
        "http://mybatis.org/dtd/mybatis-3-mapper.dtd">
<mapper namespace="com.ncs.backend.mapper.DocumentMapper">

    <resultMap id="documentResultMap" type="Document">
        <id property="docId" column="DOC_ID"/>
        <result property="filename" column="FILENAME"/>
        <result property="mainCategory" column="MAIN_CATEGORY"/>
        <result property="subCategory" column="SUB_CATEGORY"/>
        <result property="pageCount" column="PAGE_COUNT"/>
        <result property="uploadDate" column="UPLOAD_DATE"/>
        <result property="status" column="STATUS"/>
    </resultMap>

    <insert id="insert" parameterType="Document">
        INSERT INTO documents (doc_id, filename, main_category, sub_category, page_count, status)
        VALUES (#{docId}, #{filename}, #{mainCategory}, #{subCategory}, #{pageCount}, #{status})
    </insert>

    <select id="findAll" resultMap="documentResultMap">
        SELECT * FROM documents ORDER BY upload_date DESC
    </select>

    <select id="findById" parameterType="String" resultMap="documentResultMap">
        SELECT * FROM documents WHERE doc_id = #{docId}
    </select>

    <update id="updateStatus">
        UPDATE documents SET status = #{param2} WHERE doc_id = #{param1}
    </update>

    <delete id="delete" parameterType="String">
        DELETE FROM documents WHERE doc_id = #{docId}
    </delete>

    <select id="findDocIdsByCategory" resultType="String">
        SELECT doc_id FROM documents
        <where>
            status = 'INDEXED'
            <if test="mainCategory != null and mainCategory != ''">
                AND main_category = #{mainCategory}
            </if>
            <if test="subCategory != null and subCategory != ''">
                AND sub_category = #{subCategory}
            </if>
        </where>
    </select>

</mapper>
```

**Step 3: Commit**

```bash
git add backend/src/main/java/com/ncs/backend/mapper/DocumentMapper.java
git add backend/src/main/resources/mapper/DocumentMapper.xml
git commit -m "feat(spring): DocumentMapper MyBatis 구현"
```

---

## Task 1.5: CategoryMapper 구현 (MyBatis)

**Files:**
- Create: `backend/src/main/java/com/ncs/backend/mapper/CategoryMapper.java`
- Create: `backend/src/main/resources/mapper/CategoryMapper.xml`

**Step 1: CategoryMapper 인터페이스 작성**

`backend/src/main/java/com/ncs/backend/mapper/CategoryMapper.java`:

```java
package com.ncs.backend.mapper;

import com.ncs.backend.model.Category;
import org.apache.ibatis.annotations.Mapper;
import java.util.List;
import java.util.Map;

@Mapper
public interface CategoryMapper {
    List<Category> findAll();
}
```

**Step 2: CategoryMapper XML 작성**

`backend/src/main/resources/mapper/CategoryMapper.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN"
        "http://mybatis.org/dtd/mybatis-3-mapper.dtd">
<mapper namespace="com.ncs.backend.mapper.CategoryMapper">

    <select id="findAll" resultType="Category">
        SELECT main_category, sub_category FROM ncs_categories
        ORDER BY main_category, sub_category
    </select>

</mapper>
```

**Step 3: Commit**

```bash
git add backend/src/main/java/com/ncs/backend/mapper/CategoryMapper.java
git add backend/src/main/resources/mapper/CategoryMapper.xml
git commit -m "feat(spring): CategoryMapper MyBatis 구현"
```

---

## Task 1.6: DocumentService 구현

**Files:**
- Create: `backend/src/main/java/com/ncs/backend/service/DocumentService.java`

**Step 1: DocumentService 작성**

`backend/src/main/java/com/ncs/backend/service/DocumentService.java`:

```java
package com.ncs.backend.service;

import com.ncs.backend.mapper.DocumentMapper;
import com.ncs.backend.model.Document;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class DocumentService {

    private final DocumentMapper documentMapper;

    @Value("${app.upload-dir}")
    private String uploadDir;

    public Document upload(MultipartFile file, String mainCategory, String subCategory) throws IOException {
        // 1. doc_id 발급 (UUID)
        String docId = UUID.randomUUID().toString();

        // 2. 파일 저장
        Path uploadPath = Paths.get(uploadDir);
        if (!Files.exists(uploadPath)) {
            Files.createDirectories(uploadPath);
        }
        String filename = file.getOriginalFilename();
        Path filePath = uploadPath.resolve(docId + "_" + filename);
        file.transferTo(filePath);

        // 3. Oracle에 메타데이터 저장 (status: PENDING)
        Document doc = new Document();
        doc.setDocId(docId);
        doc.setFilename(filename);
        doc.setMainCategory(mainCategory);
        doc.setSubCategory(subCategory);
        doc.setStatus("PENDING");
        documentMapper.insert(doc);

        return doc;
    }

    public List<Document> findAll() {
        return documentMapper.findAll();
    }

    public void delete(String docId) {
        documentMapper.delete(docId);
    }

    public void updateStatus(String docId, String status) {
        documentMapper.updateStatus(docId, status);
    }

    public List<String> findDocIdsByCategory(String mainCategory, String subCategory) {
        return documentMapper.findDocIdsByCategory(mainCategory, subCategory);
    }
}
```

**Step 2: Commit**

```bash
git add backend/src/main/java/com/ncs/backend/service/DocumentService.java
git commit -m "feat(spring): DocumentService 구현"
```

---

## Task 1.7: CategoryService 구현

**Files:**
- Create: `backend/src/main/java/com/ncs/backend/service/CategoryService.java`

**Step 1: CategoryService 작성**

`backend/src/main/java/com/ncs/backend/service/CategoryService.java`:

```java
package com.ncs.backend.service;

import com.ncs.backend.mapper.CategoryMapper;
import com.ncs.backend.model.Category;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.*;

@Service
@RequiredArgsConstructor
public class CategoryService {

    private final CategoryMapper categoryMapper;

    // 프론트엔드 기존 형식 유지: { "정보기술개발": ["SW아키텍쳐", ...], ... }
    public Map<String, List<String>> getCategoriesGrouped() {
        List<Category> categories = categoryMapper.findAll();
        Map<String, List<String>> result = new LinkedHashMap<>();
        for (Category c : categories) {
            result.computeIfAbsent(c.getMainCategory(), k -> new ArrayList<>())
                  .add(c.getSubCategory());
        }
        return result;
    }
}
```

**Step 2: Commit**

```bash
git add backend/src/main/java/com/ncs/backend/service/CategoryService.java
git commit -m "feat(spring): CategoryService 구현"
```

---

## Task 1.8: DocumentController + CategoryController 구현

**Files:**
- Create: `backend/src/main/java/com/ncs/backend/controller/DocumentController.java`
- Create: `backend/src/main/java/com/ncs/backend/controller/CategoryController.java`
- Create: `backend/src/main/java/com/ncs/backend/config/CorsConfig.java`

**Step 1: CorsConfig 작성**

`backend/src/main/java/com/ncs/backend/config/CorsConfig.java`:

```java
package com.ncs.backend.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
public class CorsConfig implements WebMvcConfigurer {

    @Value("${app.cors.allowed-origins}")
    private String allowedOrigins;

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/api/**")
                .allowedOrigins(allowedOrigins)
                .allowedMethods("GET", "POST", "PUT", "DELETE", "OPTIONS")
                .allowedHeaders("*");
    }
}
```

**Step 2: DocumentController 작성**

`backend/src/main/java/com/ncs/backend/controller/DocumentController.java`:

```java
package com.ncs.backend.controller;

import com.ncs.backend.model.Document;
import com.ncs.backend.service.DocumentService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.List;

@RestController
@RequestMapping("/api/documents")
@RequiredArgsConstructor
public class DocumentController {

    private final DocumentService documentService;

    // PDF 업로드
    @PostMapping
    public ResponseEntity<Document> upload(
            @RequestParam("file") MultipartFile file,
            @RequestParam(value = "mainCategory", required = false) String mainCategory,
            @RequestParam(value = "subCategory", required = false) String subCategory
    ) throws IOException {
        Document doc = documentService.upload(file, mainCategory, subCategory);
        return ResponseEntity.ok(doc);
    }

    // 문서 목록 조회
    @GetMapping
    public ResponseEntity<List<Document>> findAll() {
        return ResponseEntity.ok(documentService.findAll());
    }

    // 문서 삭제
    @DeleteMapping("/{docId}")
    public ResponseEntity<Void> delete(@PathVariable String docId) {
        documentService.delete(docId);
        return ResponseEntity.noContent().build();
    }
}
```

**Step 3: CategoryController 작성**

`backend/src/main/java/com/ncs/backend/controller/CategoryController.java`:

```java
package com.ncs.backend.controller;

import com.ncs.backend.service.CategoryService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
public class CategoryController {

    private final CategoryService categoryService;

    @GetMapping("/categories")
    public ResponseEntity<Map<String, List<String>>> getCategories() {
        return ResponseEntity.ok(categoryService.getCategoriesGrouped());
    }

    @GetMapping("/health")
    public ResponseEntity<Map<String, String>> health() {
        return ResponseEntity.ok(Map.of("status", "ok"));
    }
}
```

**Step 4: Spring 서버 기동 후 수동 테스트**

```bash
cd backend && ./mvnw spring-boot:run
```

```bash
# 카테고리 조회 테스트
curl http://localhost:8080/api/categories

# 헬스 체크
curl http://localhost:8080/api/health

# PDF 업로드 테스트 (실제 PDF 파일로)
curl -X POST http://localhost:8080/api/documents \
  -F "file=@assets/실습\ NCS파일/정보기술개발/SW아키텍쳐/LM2001020101_SW아키텍처수행관리.pdf" \
  -F "mainCategory=정보기술개발" \
  -F "subCategory=SW아키텍쳐"
```

Expected:
- `/api/categories` → `{"정보기술개발": ["SW아키텍쳐", ...], ...}` 형태 JSON
- `/api/health` → `{"status": "ok"}`
- 업로드 → `{"docId": "...", "filename": "...", "status": "PENDING", ...}`

**Step 5: Commit**

```bash
git add backend/src/main/java/com/ncs/backend/controller/
git add backend/src/main/java/com/ncs/backend/config/CorsConfig.java
git commit -m "feat(spring): DocumentController, CategoryController, CorsConfig 구현"
```

---

# Phase 2: Document Registry 패턴 + PGVector 개편

> 목표: PGVector에서 메타데이터 컬럼을 제거하고 doc_id만으로 Oracle과 연결한다.
> Python에 `/internal/ingest`, `/internal/chat` API를 추가하고,
> Spring에서 PDF 업로드 시 Python ingest를 호출한다.

---

## Task 2.1: PGVector 테이블 재초기화 (doc_id 컬럼으로 변경)

**Files:**
- Modify: `src/ingest.py`

**Step 1: ingest.py의 METADATA_COLUMNS 수정**

`src/ingest.py`에서 `METADATA_COLUMNS` 정의를 변경:

```python
# 변경 전
METADATA_COLUMNS = [
    Column("main_category", "VARCHAR", nullable=True),
    Column("sub_category", "VARCHAR", nullable=True),
    Column("source", "VARCHAR", nullable=True),
    Column("page", "INTEGER", nullable=True),
]

# 변경 후 — Oracle doc_id와 연결, 페이지만 유지
METADATA_COLUMNS = [
    Column("doc_id", "VARCHAR", nullable=True),   # Oracle documents.doc_id 참조
    Column("page", "INTEGER", nullable=True),      # 페이지 번호
]
```

**Step 2: collect_pdf_files 제거, 단일 파일 ingest 함수로 전환**

`src/ingest.py` 전체를 아래로 교체:

```python
"""
ingest.py — PDF를 벡터 저장소에 적재하는 모듈

변경 사항:
- 메타데이터 컬럼을 doc_id + page로 단순화 (Oracle과 연결)
- ingest_single_document(): Spring에서 단일 PDF 처리 요청 시 사용
- ingest_all(): 전체 NCS 파일 일괄 처리 (초기 데이터 적재용)
"""

from loader import DocumentLoader
from splitter import DocumentSplitter
from embeddings import EmbeddingModel
from langchain_postgres import PGEngine, PGVectorStore, Column
from sqlalchemy.ext.asyncio import create_async_engine
from dotenv import load_dotenv
import asyncio
import os

load_dotenv()

# PGVector 테이블 스키마: doc_id(Oracle 참조) + page만 저장
METADATA_COLUMNS = [
    Column("doc_id", "VARCHAR", nullable=True),
    Column("page", "INTEGER", nullable=True),
]

TABLE_NAME = "ncs_vectors"
VECTOR_SIZE = 1536  # text-embedding-3-small


async def get_vector_store(pg_engine, embedding_model):
    """PGVectorStore 인스턴스를 반환한다."""
    return await PGVectorStore.create(
        engine=pg_engine,
        table_name=TABLE_NAME,
        embedding_service=embedding_model,
        metadata_columns=["doc_id", "page"],
    )


async def init_table(pg_engine):
    """테이블을 초기화한다 (최초 1회만 실행)."""
    await pg_engine.ainit_vectorstore_table(
        table_name=TABLE_NAME,
        vector_size=VECTOR_SIZE,
        metadata_columns=METADATA_COLUMNS,
        overwrite_existing=True,
    )


async def ingest_single_document(
    doc_id: str,
    file_path: str,
    db_connection: str,
) -> int:
    """단일 PDF 파일을 벡터 저장소에 적재한다. Spring에서 호출하는 엔드포인트용.

    Args:
        doc_id: Oracle documents 테이블의 doc_id (UUID)
        file_path: PDF 파일 경로
        db_connection: PGVector 연결 문자열

    Returns:
        저장된 청크 수
    """
    embedding_model = EmbeddingModel().get_embeddings()
    engine = create_async_engine(db_connection)
    pg_engine = PGEngine.from_engine(engine)
    vector_store = await get_vector_store(pg_engine, embedding_model)

    loader = DocumentLoader(file_path=file_path)
    docs = loader.load()
    splitter = DocumentSplitter()
    splits = splitter.split_documents(docs)

    for doc in splits:
        doc.page_content = doc.page_content.replace("\x00", "")
        doc.metadata["doc_id"] = doc_id
        doc.metadata["page"] = doc.metadata.get("page", 0)

    await vector_store.aadd_documents(splits)
    return len(splits)


if __name__ == "__main__":
    # 테스트용 단일 파일 ingest
    import sys
    if len(sys.argv) < 3:
        print("Usage: python ingest.py <doc_id> <file_path>")
        sys.exit(1)
    doc_id = sys.argv[1]
    file_path = sys.argv[2]
    db = os.getenv("DB_CONNECTION", "postgresql+asyncpg://postgres:1234@localhost:5432/pdf_db")

    async def run():
        n = await ingest_single_document(doc_id, file_path, db)
        print(f"Ingested {n} chunks for doc_id={doc_id}")

    asyncio.run(run())
```

**Step 3: PGVector 테이블 재생성 테스트**

```bash
cd /c/study/langchain_study/3_playground/ncs_rag_chatbot
source venv/Scripts/activate
python src/ingest.py test-uuid-001 "assets/실습 NCS파일/정보기술개발/SW아키텍쳐/LM2001020101_SW아키텍처수행관리.pdf"
```

Expected: `Ingested N chunks for doc_id=test-uuid-001`

**Step 4: Commit**

```bash
git add src/ingest.py
git commit -m "refact(python): PGVector 스키마를 doc_id+page로 단순화"
```

---

## Task 2.2: vector_store.py 수정 (doc_id IN 필터)

**Files:**
- Modify: `src/vector_store.py`

**Step 1: vector_store.py 전체 교체**

```python
"""
vector_store.py — PGVectorStore 관리 모듈

변경 사항:
- metadata_columns: doc_id + page만 사용
- similarity_search_by_doc_ids(): doc_id 목록으로 필터링하여 검색
"""

from langchain_postgres import PGEngine, PGVectorStore
from typing import List, Optional
from langchain_core.documents import Document
from sqlalchemy.ext.asyncio import create_async_engine


class VectorStoreManager:

    TABLE_NAME = "ncs_vectors"

    def __init__(self, engine, vector_store):
        self.pg_engine = engine
        self.vector_store = vector_store

    @classmethod
    async def create(cls, connection_string: str, embedding_model):
        engine = create_async_engine(connection_string)
        pg_engine = PGEngine.from_engine(engine)
        vector_store = await PGVectorStore.create(
            engine=pg_engine,
            table_name=cls.TABLE_NAME,
            embedding_service=embedding_model,
            metadata_columns=["doc_id", "page"],
        )
        return cls(pg_engine, vector_store)

    async def similarity_search_by_doc_ids(
        self,
        query: str,
        doc_ids: List[str],
        k: int = 4,
    ) -> List[Document]:
        """doc_id 목록 내에서만 유사도 검색을 수행한다.

        doc_ids가 비어있으면 전체 검색을 수행한다.
        """
        if doc_ids:
            # PGVectorStore의 $in 필터: doc_id가 목록 중 하나인 문서만 검색
            filter_dict = {"doc_id": {"$in": doc_ids}}
            return await self.vector_store.asimilarity_search(query, k=k, filter=filter_dict)
        else:
            return await self.vector_store.asimilarity_search(query, k=k)

    def get_vector_store(self):
        return self.vector_store
```

**Step 2: 검색 테스트**

```python
# 테스트 스크립트 (별도 실행)
import asyncio
from src.embeddings import EmbeddingModel
from src.vector_store import VectorStoreManager

async def test():
    emb = EmbeddingModel().get_embeddings()
    mgr = await VectorStoreManager.create(
        "postgresql+asyncpg://postgres:1234@localhost:5432/pdf_db", emb
    )
    docs = await mgr.similarity_search_by_doc_ids(
        "SW 아키텍처 수행관리란?",
        doc_ids=["test-uuid-001"],
        k=2,
    )
    for d in docs:
        print(d.metadata, d.page_content[:100])

asyncio.run(test())
```

Expected: doc_id=test-uuid-001의 관련 문서 반환

**Step 3: Commit**

```bash
git add src/vector_store.py
git commit -m "refact(python): VectorStoreManager를 doc_id 기반 필터로 전환"
```

---

## Task 2.3: tool.py 수정 (doc_ids 파라미터)

**Files:**
- Modify: `src/tool.py`

**Step 1: tool.py 전체 교체**

```python
"""
tool.py — LangChain Agent가 사용하는 검색 도구

변경 사항:
- retrieve_context 도구가 doc_ids 파라미터를 받아 Oracle과 연결된 문서만 검색
- doc_ids는 Spring에서 Oracle 조회 후 전달된 UUID 목록
"""

from langchain.tools import tool
from langchain_core.tools import Tool
from typing import List, Optional


class ToolBuilder:

    def __init__(self, vector_store_manager):
        self.vsm = vector_store_manager

    def build_tools(self, doc_ids: Optional[List[str]] = None) -> List[Tool]:
        """doc_ids가 주어지면 해당 문서 내에서만 검색하는 도구를 생성한다."""

        vsm = self.vsm
        _doc_ids = doc_ids or []

        @tool(response_format="content_and_artifact")
        async def retrieve_context(query: str):
            """NCS 문서에서 질의와 관련된 내용을 검색한다.

            Spring에서 카테고리 필터링으로 전달된 doc_ids 범위 내에서만 검색한다.
            doc_ids가 없으면 전체 문서에서 검색한다.
            """
            retrieved_docs = await vsm.similarity_search_by_doc_ids(
                query, doc_ids=_doc_ids, k=4
            )

            serialized = "\n\n".join(
                f"Source: {doc.metadata}\nContent: {doc.page_content}"
                for doc in retrieved_docs
            )

            if not serialized:
                serialized = "관련 문서를 찾을 수 없습니다."

            return serialized, retrieved_docs

        return [retrieve_context]
```

**Step 2: Commit**

```bash
git add src/tool.py
git commit -m "refact(python): ToolBuilder를 doc_ids 기반으로 변경"
```

---

## Task 2.4: Python /internal API 구현

**Files:**
- Modify: `src/main.py`

**Step 1: main.py 전체 교체**

```python
"""
main.py — Python FastAPI AI 서버

엔드포인트:
  POST /internal/ingest  — Spring에서 PDF 업로드 후 벡터 저장 요청
  POST /internal/chat    — Spring에서 채팅 요청 (doc_ids 포함)

외부(프론트엔드)에서 직접 호출하지 않는다. Spring만 호출한다.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

from embeddings import EmbeddingModel
from vector_store import VectorStoreManager
from agent import ChatAgent
from tool import ToolBuilder
from ingest import ingest_single_document
from langchain.chat_models import init_chat_model

app = FastAPI(title="NCS RAG AI Server (Internal)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],  # Spring만 허용
    allow_methods=["POST"],
    allow_headers=["*"],
)

DB_CONNECTION = os.getenv(
    "DB_CONNECTION",
    "postgresql+asyncpg://postgres:1234@localhost:5432/pdf_db"
)

vector_store_manager = None


@app.on_event("startup")
async def startup():
    global vector_store_manager
    emb = EmbeddingModel().get_embeddings()
    vector_store_manager = await VectorStoreManager.create(DB_CONNECTION, emb)
    print("VectorStoreManager initialized.")


# ────────────────────────────────────────────
# Request/Response 모델
# ────────────────────────────────────────────

class IngestRequest(BaseModel):
    doc_id: str       # Oracle에서 발급한 UUID
    file_path: str    # PDF 파일 절대 경로


class IngestResponse(BaseModel):
    doc_id: str
    chunks: int
    status: str       # INDEXED | FAILED


class ChatRequest(BaseModel):
    query: str
    doc_ids: Optional[List[str]] = None   # Oracle에서 조회한 doc_id 목록


class SourceInfo(BaseModel):
    content: str
    doc_id: str
    page: int


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceInfo]


# ────────────────────────────────────────────
# Endpoints
# ────────────────────────────────────────────

@app.post("/internal/ingest", response_model=IngestResponse)
async def ingest(req: IngestRequest):
    """Spring에서 PDF 업로드 후 호출. doc_id와 파일 경로를 받아 벡터 저장."""
    try:
        chunks = await ingest_single_document(req.doc_id, req.file_path, DB_CONNECTION)
        return IngestResponse(doc_id=req.doc_id, chunks=chunks, status="INDEXED")
    except Exception as e:
        return IngestResponse(doc_id=req.doc_id, chunks=0, status="FAILED")


@app.post("/internal/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Spring에서 호출. doc_ids 범위 내에서 RAG 검색 후 AI 응답 생성."""
    doc_ids = req.doc_ids or []

    tool_builder = ToolBuilder(vector_store_manager)
    tools = tool_builder.build_tools(doc_ids=doc_ids)

    agent = ChatAgent()
    agent.create_agent(tools)

    last_message = await agent.run(req.query)
    answer = last_message.content if last_message else "응답을 생성할 수 없습니다."

    return ChatResponse(answer=answer, sources=[])


@app.get("/internal/health")
async def health():
    return {"status": "ok"}
```

**Step 2: Python 서버 기동 테스트**

```bash
cd /c/study/langchain_study/3_playground/ncs_rag_chatbot
source venv/Scripts/activate
uvicorn main:app --reload --port 8000
```

**Step 3: /internal/health 확인**

```bash
curl http://localhost:8000/internal/health
```

Expected: `{"status": "ok"}`

**Step 4: /internal/ingest 테스트**

```bash
curl -X POST http://localhost:8000/internal/ingest \
  -H "Content-Type: application/json" \
  -d '{"doc_id": "test-uuid-002", "file_path": "C:/study/langchain_study/3_playground/ncs_rag_chatbot/assets/실습 NCS파일/정보기술개발/SW아키텍쳐/LM2001020101_SW아키텍처수행관리.pdf"}'
```

Expected: `{"doc_id": "test-uuid-002", "chunks": N, "status": "INDEXED"}`

**Step 5: Commit**

```bash
git add src/main.py
git commit -m "feat(python): /internal/ingest, /internal/chat API 구현"
```

---

## Task 2.5: Spring DocumentService에서 Python ingest 호출 연동

**Files:**
- Create: `backend/src/main/java/com/ncs/backend/config/RestClientConfig.java`
- Modify: `backend/src/main/java/com/ncs/backend/service/DocumentService.java`

**Step 1: RestClientConfig 작성**

`backend/src/main/java/com/ncs/backend/config/RestClientConfig.java`:

```java
package com.ncs.backend.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestClient;

@Configuration
public class RestClientConfig {

    @Value("${app.python-server-url}")
    private String pythonServerUrl;

    @Bean
    public RestClient pythonRestClient() {
        return RestClient.builder()
                .baseUrl(pythonServerUrl)
                .defaultHeader("Content-Type", "application/json")
                .build();
    }
}
```

**Step 2: DocumentService에 Python ingest 호출 추가**

`backend/src/main/java/com/ncs/backend/service/DocumentService.java` 수정:

```java
package com.ncs.backend.service;

import com.ncs.backend.mapper.DocumentMapper;
import com.ncs.backend.model.Document;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class DocumentService {

    private final DocumentMapper documentMapper;
    private final RestClient pythonRestClient;

    @Value("${app.upload-dir}")
    private String uploadDir;

    public Document upload(MultipartFile file, String mainCategory, String subCategory) throws IOException {
        // 1. doc_id 발급
        String docId = UUID.randomUUID().toString();

        // 2. 파일 저장
        Path uploadPath = Paths.get(uploadDir).toAbsolutePath();
        if (!Files.exists(uploadPath)) {
            Files.createDirectories(uploadPath);
        }
        String filename = file.getOriginalFilename();
        Path filePath = uploadPath.resolve(docId + "_" + filename);
        file.transferTo(filePath);

        // 3. Oracle에 PENDING 상태로 저장
        Document doc = new Document();
        doc.setDocId(docId);
        doc.setFilename(filename);
        doc.setMainCategory(mainCategory);
        doc.setSubCategory(subCategory);
        doc.setStatus("PENDING");
        documentMapper.insert(doc);

        // 4. Python ingest 호출 (비동기 처리 없이 동기로 호출)
        try {
            Map<String, String> ingestReq = Map.of(
                "doc_id", docId,
                "file_path", filePath.toString()
            );
            Map response = pythonRestClient.post()
                    .uri("/internal/ingest")
                    .body(ingestReq)
                    .retrieve()
                    .body(Map.class);

            String status = (String) response.get("status");
            documentMapper.updateStatus(docId, status);  // INDEXED or FAILED
            doc.setStatus(status);
            log.info("Ingest complete: docId={}, status={}", docId, status);
        } catch (Exception e) {
            log.error("Python ingest failed for docId={}: {}", docId, e.getMessage());
            documentMapper.updateStatus(docId, "FAILED");
            doc.setStatus("FAILED");
        }

        return doc;
    }

    public List<Document> findAll() {
        return documentMapper.findAll();
    }

    public void delete(String docId) {
        documentMapper.delete(docId);
    }

    public void updateStatus(String docId, String status) {
        documentMapper.updateStatus(docId, status);
    }

    public List<String> findDocIdsByCategory(String mainCategory, String subCategory) {
        return documentMapper.findDocIdsByCategory(mainCategory, subCategory);
    }
}
```

**Step 3: 전체 흐름 통합 테스트**

Python 서버와 Spring 서버 모두 기동 후:

```bash
# PDF 업로드 → Oracle 저장 → Python ingest 자동 호출
curl -X POST http://localhost:8080/api/documents \
  -F "file=@assets/실습\ NCS파일/정보기술개발/SW아키텍쳐/LM2001020101_SW아키텍처수행관리.pdf" \
  -F "mainCategory=정보기술개발" \
  -F "subCategory=SW아키텍쳐"
```

Expected:
- Oracle documents 테이블에 행 추가됨 (status=INDEXED)
- PGVector에 해당 doc_id의 청크들 저장됨

**Step 4: Commit**

```bash
git add backend/src/main/java/com/ncs/backend/config/RestClientConfig.java
git add backend/src/main/java/com/ncs/backend/service/DocumentService.java
git commit -m "feat(spring): PDF 업로드 시 Python ingest 자동 호출 연동"
```

---

# Phase 3: Redis 프롬프트 DB화

> 목표: Agent의 시스템 프롬프트를 코드에서 분리하여 Redis에 저장/관리한다.
> Spring에서 프롬프트를 CRUD하고, Python에서 Redis로부터 로드한다.

---

## Task 3.1: Spring Redis 의존성 추가

**Files:**
- Modify: `backend/pom.xml`

**Step 1: pom.xml에 Redis 의존성 추가**

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-redis</artifactId>
</dependency>
```

**Step 2: application.properties에 Redis 설정 추가**

```properties
# Redis
spring.data.redis.host=localhost
spring.data.redis.port=6379
```

**Step 3: Redis 서버 기동 확인**

```bash
# Redis가 설치되어 있지 않다면 Docker로 실행
docker run -d -p 6379:6379 --name redis redis:latest

# 연결 테스트
redis-cli ping
```

Expected: `PONG`

**Step 4: Commit**

```bash
git add backend/pom.xml backend/src/main/resources/application.properties
git commit -m "feat(spring): spring-data-redis 의존성 및 Redis 설정 추가"
```

---

## Task 3.2: PromptService + PromptController 구현 (Spring)

**Files:**
- Create: `backend/src/main/java/com/ncs/backend/service/PromptService.java`
- Create: `backend/src/main/java/com/ncs/backend/controller/PromptController.java`

**Step 1: PromptService 작성**

`backend/src/main/java/com/ncs/backend/service/PromptService.java`:

```java
package com.ncs.backend.service;

import lombok.RequiredArgsConstructor;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class PromptService {

    // 모든 프롬프트는 "prompt:" 접두사로 Redis에 저장
    private static final String PREFIX = "prompt:";

    private final StringRedisTemplate redisTemplate;

    public String get(String key) {
        return redisTemplate.opsForValue().get(PREFIX + key);
    }

    public void set(String key, String value) {
        redisTemplate.opsForValue().set(PREFIX + key, value);
    }

    public void delete(String key) {
        redisTemplate.delete(PREFIX + key);
    }

    public Map<String, String> getAll() {
        Set<String> keys = redisTemplate.keys(PREFIX + "*");
        if (keys == null || keys.isEmpty()) return Map.of();
        return keys.stream().collect(Collectors.toMap(
            k -> k.substring(PREFIX.length()),
            k -> {
                String v = redisTemplate.opsForValue().get(k);
                return v != null ? v : "";
            }
        ));
    }
}
```

**Step 2: PromptController 작성**

`backend/src/main/java/com/ncs/backend/controller/PromptController.java`:

```java
package com.ncs.backend.controller;

import com.ncs.backend.service.PromptService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/prompts")
@RequiredArgsConstructor
public class PromptController {

    private final PromptService promptService;

    // 전체 프롬프트 목록 조회
    @GetMapping
    public ResponseEntity<Map<String, String>> getAll() {
        return ResponseEntity.ok(promptService.getAll());
    }

    // 특정 프롬프트 조회
    @GetMapping("/{key}")
    public ResponseEntity<Map<String, String>> get(@PathVariable String key) {
        String value = promptService.get(key);
        if (value == null) return ResponseEntity.notFound().build();
        return ResponseEntity.ok(Map.of("key", key, "value", value));
    }

    // 프롬프트 저장/수정
    @PutMapping("/{key}")
    public ResponseEntity<Void> set(@PathVariable String key, @RequestBody Map<String, String> body) {
        promptService.set(key, body.get("value"));
        return ResponseEntity.ok().build();
    }

    // 프롬프트 삭제
    @DeleteMapping("/{key}")
    public ResponseEntity<Void> delete(@PathVariable String key) {
        promptService.delete(key);
        return ResponseEntity.noContent().build();
    }
}
```

**Step 3: 초기 프롬프트 데이터 저장**

Spring 서버 기동 후:

```bash
# agent_system_prompt 저장
curl -X PUT http://localhost:8080/api/prompts/agent_system_prompt \
  -H "Content-Type: application/json" \
  -d '{"value": "너는 NCS(국가직무능력표준) 문서에서 정보를 검색하여 답변해주는 친절한 AI 어시스턴트야.\n사용자의 질의에 retrieve_context 도구를 적극적으로 사용해서 답변해줘.\n답변에 관련 내용의 출처(파일명, 페이지)를 언급해줘."}'

# 저장 확인
curl http://localhost:8080/api/prompts/agent_system_prompt
```

**Step 4: Commit**

```bash
git add backend/src/main/java/com/ncs/backend/service/PromptService.java
git add backend/src/main/java/com/ncs/backend/controller/PromptController.java
git commit -m "feat(spring): Redis 기반 PromptService, PromptController 구현"
```

---

## Task 3.3: Python prompt_loader.py 구현 + agent.py 수정

**Files:**
- Create: `src/prompt_loader.py`
- Modify: `src/agent.py`

**Step 1: prompt_loader.py 작성**

`src/prompt_loader.py`:

```python
"""
prompt_loader.py — Redis에서 프롬프트 템플릿을 로드하는 모듈

Spring의 PromptService가 저장한 "prompt:<key>" 형식의 키를 읽는다.
Redis 연결 실패 시 fallback 기본값을 반환한다.
"""

import os
import redis

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
PREFIX = "prompt:"

# 연결 실패 시 사용하는 기본 프롬프트
FALLBACK_PROMPTS = {
    "agent_system_prompt": (
        "너는 NCS(국가직무능력표준) 문서에서 정보를 검색하여 답변해주는 친절한 AI 어시스턴트야.\n"
        "사용자의 질의에 retrieve_context 도구를 적극적으로 사용해서 답변해줘.\n"
        "답변에 관련 내용의 출처(파일명, 페이지)를 언급해줘."
    ),
}


def get_prompt(key: str) -> str:
    """Redis에서 프롬프트를 가져온다. 실패 시 fallback을 반환한다."""
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        value = r.get(PREFIX + key)
        if value:
            return value
    except Exception as e:
        print(f"[prompt_loader] Redis 연결 실패, fallback 사용: {e}")

    return FALLBACK_PROMPTS.get(key, "")
```

**Step 2: agent.py 수정 — 하드코딩 프롬프트를 Redis 로드로 교체**

`src/agent.py`:

```python
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from prompt_loader import get_prompt
from typing import List
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


class ChatAgent:

    def __init__(self, model_name: str = "gpt-4o-mini", system_prompt: str = None):
        self.model = init_chat_model(model_name)
        # system_prompt가 명시적으로 전달되면 사용, 없으면 Redis에서 로드
        if system_prompt is not None:
            self.system_prompt = system_prompt
        else:
            self.system_prompt = get_prompt("agent_system_prompt")

    def create_agent(self, tools: List):
        self.agent = create_agent(self.model, tools, system_prompt=self.system_prompt)

    async def run(self, query: str):
        if not hasattr(self, 'agent'):
            raise ValueError("Agent has not been created. Call create_agent() first.")

        last_message = None
        async for event in self.agent.astream(
            {"messages": [{"role": "user", "content": query}]},
            stream_mode="values",
        ):
            event["messages"][-1].pretty_print()
            last_message = event["messages"][-1]

        return last_message
```

**Step 3: Redis에서 프롬프트 로드 테스트**

```bash
source venv/Scripts/activate
python -c "
import sys; sys.path.insert(0, 'src')
from prompt_loader import get_prompt
print(get_prompt('agent_system_prompt'))
"
```

Expected: Redis에서 저장한 프롬프트 텍스트 출력 (또는 fallback 텍스트)

**Step 4: Commit**

```bash
git add src/prompt_loader.py src/agent.py
git commit -m "feat(python): Redis 기반 프롬프트 로더 구현, agent.py 연동"
```

---

# Phase 4: Spring API Gateway + ChatController

> 목표: Spring이 프론트엔드의 채팅 요청을 받아 Python AI 서버로 프록시한다.
> 기존 FastAPI server.py의 /api/chat, /api/categories를 Spring으로 이전한다.

---

## Task 4.1: DTO 클래스 작성

**Files:**
- Create: `backend/src/main/java/com/ncs/backend/dto/ChatRequest.java`
- Create: `backend/src/main/java/com/ncs/backend/dto/ChatResponse.java`
- Create: `backend/src/main/java/com/ncs/backend/dto/InternalChatRequest.java`

**Step 1: ChatRequest 작성**

`backend/src/main/java/com/ncs/backend/dto/ChatRequest.java`:

```java
package com.ncs.backend.dto;

import lombok.Data;

@Data
public class ChatRequest {
    private String query;
    private String mainCategory;
    private String subCategory;
}
```

**Step 2: InternalChatRequest 작성 (Python 전달용)**

`backend/src/main/java/com/ncs/backend/dto/InternalChatRequest.java`:

```java
package com.ncs.backend.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import java.util.List;

@Data
@AllArgsConstructor
public class InternalChatRequest {
    private String query;
    private List<String> docIds;
}
```

**Step 3: ChatResponse 작성**

`backend/src/main/java/com/ncs/backend/dto/ChatResponse.java`:

```java
package com.ncs.backend.dto;

import lombok.Data;
import java.util.List;
import java.util.Map;

@Data
public class ChatResponse {
    private String answer;
    private List<Map<String, Object>> sources;
}
```

**Step 4: Commit**

```bash
git add backend/src/main/java/com/ncs/backend/dto/
git commit -m "feat(spring): Chat DTO 클래스 추가"
```

---

## Task 4.2: ChatService + ChatController 구현

**Files:**
- Create: `backend/src/main/java/com/ncs/backend/service/ChatService.java`
- Create: `backend/src/main/java/com/ncs/backend/controller/ChatController.java`

**Step 1: ChatService 작성**

`backend/src/main/java/com/ncs/backend/service/ChatService.java`:

```java
package com.ncs.backend.service;

import com.ncs.backend.dto.ChatRequest;
import com.ncs.backend.dto.ChatResponse;
import com.ncs.backend.dto.InternalChatRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class ChatService {

    private final DocumentService documentService;
    private final RestClient pythonRestClient;

    public ChatResponse chat(ChatRequest req) {
        // 1. Oracle에서 카테고리 조건에 맞는 doc_id 목록 조회
        List<String> docIds = documentService.findDocIdsByCategory(
            req.getMainCategory(), req.getSubCategory()
        );
        log.info("Chat request: query={}, docIds={}", req.getQuery(), docIds);

        // 2. Python AI 서버에 query + doc_ids 전달
        InternalChatRequest internalReq = new InternalChatRequest(req.getQuery(), docIds);
        ChatResponse response = pythonRestClient.post()
                .uri("/internal/chat")
                .body(internalReq)
                .retrieve()
                .body(ChatResponse.class);

        return response;
    }
}
```

**Step 2: ChatController 작성**

`backend/src/main/java/com/ncs/backend/controller/ChatController.java`:

```java
package com.ncs.backend.controller;

import com.ncs.backend.dto.ChatRequest;
import com.ncs.backend.dto.ChatResponse;
import com.ncs.backend.service.ChatService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
public class ChatController {

    private final ChatService chatService;

    @PostMapping("/chat")
    public ResponseEntity<ChatResponse> chat(@RequestBody ChatRequest req) {
        ChatResponse response = chatService.chat(req);
        return ResponseEntity.ok(response);
    }
}
```

**Step 3: 전체 채팅 흐름 테스트**

Spring + Python 서버 모두 기동 후:

```bash
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "SW 아키텍처 수행관리의 핵심은 무엇인가요?", "mainCategory": "정보기술개발", "subCategory": "SW아키텍쳐"}'
```

Expected: `{"answer": "...", "sources": [...]}`

**Step 4: Commit**

```bash
git add backend/src/main/java/com/ncs/backend/service/ChatService.java
git add backend/src/main/java/com/ncs/backend/controller/ChatController.java
git commit -m "feat(spring): ChatService, ChatController 구현 (Python 프록시)"
```

---

## Task 4.3: 프론트엔드 API 주소 Spring으로 전환

**Files:**
- Modify: `frontend/src/api/ncsApi.js`

**Step 1: ncsApi.js 현재 내용 확인 후 BASE_URL 변경**

`frontend/src/api/ncsApi.js`에서 API base URL을 Spring 서버로 변경:

```javascript
// 변경 전
const BASE_URL = 'http://localhost:8000'

// 변경 후
const BASE_URL = 'http://localhost:8080'
```

**Step 2: 프론트엔드 동작 확인**

```bash
cd frontend && npm run dev
```

브라우저에서 `http://localhost:5173` 접속 후:
- 카테고리 목록 정상 로드 확인
- 채팅 질의 전송 후 응답 수신 확인

**Step 3: server.py에서 /api 엔드포인트 제거**

`server.py`에서 Spring으로 이전된 엔드포인트 제거:

```python
# 삭제할 코드:
# @app.get("/api/categories")
# @app.get("/api/health")
# @app.post("/api/chat")
# @app.on_event("startup") 블록 (store, llm 초기화)
# StaticFiles 마운트
```

`server.py`를 아래와 같이 정리:

```python
"""
server.py — 레거시 파일 (비활성화)

모든 API는 Spring Boot(8080)로 이전됨.
Python AI 서버는 src/main.py (포트 8000)에서 실행.
이 파일은 참조용으로만 보관.
"""
# 이 파일은 더 이상 사용하지 않습니다.
# Python AI 서버 실행: uvicorn src.main:app --port 8000
```

**Step 4: Commit**

```bash
git add frontend/src/api/ncsApi.js server.py
git commit -m "feat: 프론트엔드 API 주소를 Spring(8080)으로 전환, server.py 정리"
```

---

# Phase 5: Arize Phoenix 모니터링 구축

> 목표: Python AI 서버의 LangChain Agent 실행을 Arize Phoenix로 트레이싱한다.
> Docker로 Phoenix를 로컬에서 실행하고 OpenTelemetry로 자동 계측한다.

---

## Task 5.1: Arize Phoenix Docker 실행

**Step 1: Phoenix Docker 컨테이너 실행**

```bash
docker run -d \
  --name arize-phoenix \
  -p 6006:6006 \
  -p 4317:4317 \
  arizephoenix/phoenix:latest
```

**Step 2: Phoenix 대시보드 접속 확인**

브라우저에서 `http://localhost:6006` 접속

Expected: Arize Phoenix 대시보드 로드됨

**Step 3: Commit**

```bash
git add .
git commit -m "docs: Arize Phoenix Docker 실행 명령 확인"
```

---

## Task 5.2: Python 트레이싱 패키지 설치

**Step 1: 필요 패키지 설치**

```bash
source venv/Scripts/activate
pip install arize-phoenix-otel opentelemetry-sdk opentelemetry-exporter-otlp openinference-instrumentation-langchain
```

**Step 2: requirements.txt 업데이트**

```bash
pip freeze | grep -E "(arize|opentelemetry|openinference)" >> requirements.txt
```

**Step 3: Commit**

```bash
git add requirements.txt
git commit -m "feat(python): Arize Phoenix OTel 패키지 추가"
```

---

## Task 5.3: tracing.py 구현

**Files:**
- Create: `src/tracing.py`

**Step 1: tracing.py 작성**

`src/tracing.py`:

```python
"""
tracing.py — Arize Phoenix OpenTelemetry 트레이싱 설정

Phoenix가 http://localhost:6006 에서 실행 중이어야 한다.
(docker run -p 6006:6006 -p 4317:4317 arizephoenix/phoenix:latest)

이 모듈을 main.py 시작 시 가장 먼저 import하면
LangChain Agent의 모든 실행이 자동으로 트레이싱된다.
"""

import os
from phoenix.otel import register
from openinference.instrumentation.langchain import LangChainInstrumentor


def setup_tracing():
    """Phoenix 트레이싱을 초기화한다."""
    phoenix_host = os.getenv("PHOENIX_HOST", "localhost")
    phoenix_grpc_port = os.getenv("PHOENIX_GRPC_PORT", "4317")

    endpoint = f"http://{phoenix_host}:{phoenix_grpc_port}"

    try:
        tracer_provider = register(
            project_name="ncs-rag-chatbot",
            endpoint=endpoint,
        )
        LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
        print(f"[tracing] Arize Phoenix 트레이싱 활성화: {endpoint}")
        print(f"[tracing] 대시보드: http://{phoenix_host}:6006")
    except Exception as e:
        print(f"[tracing] Phoenix 연결 실패, 트레이싱 비활성화: {e}")
```

**Step 2: main.py 최상단에 tracing 초기화 추가**

`src/main.py` 최상단 (import 바로 위)에 추가:

```python
# 트레이싱은 가장 먼저 초기화해야 모든 LangChain 호출을 계측할 수 있다
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from tracing import setup_tracing
setup_tracing()

# ... 이후 기존 import들
```

**Step 3: 트레이싱 동작 확인**

Python 서버 재기동 후 채팅 요청 전송:

```bash
uvicorn src.main:app --reload --port 8000
```

```bash
curl -X POST http://localhost:8000/internal/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "IT 테스트 기획의 핵심은?", "doc_ids": []}'
```

브라우저에서 `http://localhost:6006` 확인

Expected:
- `ncs-rag-chatbot` 프로젝트에 트레이스 생성됨
- LangChain Agent 실행 단계별 스팬 확인 가능
- LLM 호출 latency, 토큰 수, retrieve_context 호출 결과 확인

**Step 4: Commit**

```bash
git add src/tracing.py src/main.py
git commit -m "feat(python): Arize Phoenix OTel 트레이싱 구현"
```

---

## Task 5.4: 최종 검증

**전체 시스템 기동 순서:**

```bash
# 1. Oracle DB — 이미 실행 중이어야 함

# 2. PostgreSQL (PGVector) — 이미 실행 중이어야 함

# 3. Redis
docker start redis  # 또는 docker run -d -p 6379:6379 redis

# 4. Arize Phoenix
docker start arize-phoenix  # 또는 위 Task 5.1 명령

# 5. Python AI 서버
cd /c/study/langchain_study/3_playground/ncs_rag_chatbot
source venv/Scripts/activate
uvicorn src.main:app --reload --port 8000

# 6. Spring Boot 서버
cd backend && ./mvnw spring-boot:run

# 7. 프론트엔드 (개발 서버)
cd frontend && npm run dev
```

**검증 체크리스트:**

```
□ http://localhost:5173 — Vue 채팅 UI 로드
□ 카테고리 드롭다운 — Oracle에서 9개 카테고리 표시
□ PDF 업로드 — Oracle에 INDEXED 상태로 저장, PGVector에 벡터 저장
□ 채팅 질의 — 카테고리 필터링 적용된 RAG 응답 수신
□ http://localhost:8080/api/prompts — Redis 프롬프트 목록 조회
□ http://localhost:6006 — Phoenix 대시보드에 트레이스 확인
```

**Step 5: 최종 Commit**

```bash
git add .
git commit -m "feat: Phase 5 완료 - Arize Phoenix 모니터링 구축 및 전체 시스템 검증"
```

---

## 참고: 서버별 포트 정리

| 서버 | 포트 | 용도 |
|------|------|------|
| Spring Boot | 8080 | 외부 API Gateway (프론트엔드가 바라봄) |
| Python FastAPI | 8000 | 내부 AI 서버 (Spring에서만 호출) |
| Oracle DB | 1521 | 관계형 데이터 |
| PostgreSQL (PGVector) | 5432 | 벡터 임베딩 |
| Redis | 6379 | 프롬프트 템플릿 |
| Arize Phoenix (HTTP) | 6006 | 모니터링 대시보드 |
| Arize Phoenix (gRPC) | 4317 | OTel exporter 수신 |
| Vue 개발 서버 | 5173 | 프론트엔드 |
