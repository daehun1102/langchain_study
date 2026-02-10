from langchain.tools import tool


@tool
def search_code(query: str, repo: str = "main") -> str:
    """깃허브 리포지토리에서 코드를 검색합니다."""
    return f"'{query}'와 일치하는 코드를 {repo}에서 찾았습니다: src/auth.py의 인증 미들웨어"


@tool
def search_issues(query: str) -> str:
    """깃허브 이슈와 풀 리퀘스트를 검색합니다."""
    return f"'{query}'와 일치하는 이슈 3개를 찾았습니다: #142 (API 인증 문서), #89 (OAuth 플로우), #203 (토큰 갱신)"


@tool
def search_prs(query: str) -> str:
    """깃허브 이슈와 풀 리퀘스트를 검색합니다."""
    return f"PR #156 JWT 인증 추가, PR #178 OAuth 스코프 업데이트"


@tool
def search_notion(query: str) -> str:
    """노션 워크스페이스에서 문서를 검색합니다."""
    return f"문서를 찾았습니다: 'API 인증 가이드' - OAuth2 플로우, API 키, JWT 토큰을 다룹니다"


@tool
def get_page(page_id: str) -> str:
    """특정 노션 페이지를 ID로 가져옵니다."""
    return f"페이지 내용: 단계별 인증 설정 지침"


@tool
def search_slack(query: str) -> str:
    """슬랙 메시지와 스레드를 검색합니다."""
    return f"#engineering에서 논의를 찾았습니다: 'API 인증을 위해 Bearer 토큰을 사용하세요, 갱신 플로우는 문서를 참조하세요'"


@tool
def get_thread(thread_id: str) -> str:
    """특정 슬랙 스레드를 ID로 가져옵니다."""
    return f"스레드에서 API 키 순환을 위한 모범 사례를 논의했습니다"
