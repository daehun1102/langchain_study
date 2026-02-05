# LangChain Study Repository

## Study Goal
공식 문서의 학습에서 시작해서 실무에 적용할 수 있는 수준까지 정리하는 것을 목표로 합니다.

## Version
* Python: 3.13.x
* LangChain: 1.2.x
* LangGraph: 1.0.x
* LangSmith: 0.6.x  

## Directory Structure
```text
.
├── 1_concepts        # 이론 및 개념 정리
│   ├── langchain
│   ├── langgraph
│   └── langsmith
├── 2_tutorials       # 실습 및 튜토리얼 코드
│   ├── langchain
│   ├── langgraph
│   └── langsmith
├── 3_playground      # 통합 프로젝트 실험 공간
├── .env
├── .gitignore
├── requirements.txt
└── README.md
```

### 01 Concepts
공식 문서의 핵심 개념과 이론적 배경을 정리합니다. Markdown으로 정리합니다.
* **LangChain:** models, messages, tools, structed output...
* **LangGraph:** persistence, checkpoint, conditional edge, multi-agent...
* **LangSmith:** trace, debug, test, playground...

### 02 Tutorials
공식 가이드를 기반으로 한 코드 구현 및 설명입니다. Jupyter Notebook으로 정리합니다.

### 03 Lab
학습된 기술을 실제 서비스 환경(Full-stack)에 이식하는 통합 실험 공간입니다. (예정)
* **AI Engine:** FastAPI 기반의 LangGraph 추론 엔진
* **Service:** Spring Boot 백엔드 연동 및 PostgreSQL 상태 저장
* **Interface:** Vue.js 기반의 대화형 UI



## Tech Stack
실무와 동일한 환경을 구성해서 연습할 예정입니다.

* **Core:** LangChain, LangGraph, LangSmith
* **Backend:** Python (FastAPI), Java (Spring Boot), Mybatis, 
* **Frontend:** Vue.js
* **Database:** PostgreSQL, Redis, Vector Stores
* **Infrastructure:** Docker, AWS


