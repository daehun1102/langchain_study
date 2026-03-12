# tests/test_agent_registry.py
from ai_server.agents.registry import AgentKey, AGENT_NODE_MAP


def test_agent_key_values():
    """AgentKey 값이 기존 API contract 문자열과 동일한지 검증"""
    assert AgentKey.PROCESS_HISTORY == "process_history"
    assert AgentKey.RETURN_HISTORY  == "return_history"
    assert AgentKey.TEST_HISTORY    == "test_history"
    assert AgentKey.LONG_TERM       == "long_term"


def test_agent_key_is_str():
    """StrEnum이므로 isinstance(key, str) == True — JSON 직렬화 호환"""
    for key in AgentKey:
        assert isinstance(key, str), f"{key} is not a str"


def test_agent_node_map_covers_all_keys():
    """AGENT_NODE_MAP이 모든 AgentKey를 커버하는지 검증"""
    assert set(AGENT_NODE_MAP.keys()) == set(AgentKey)


def test_agent_node_map_node_names():
    """노드 이름이 기존 규칙({key}_node)을 따르는지 검증"""
    for key, node_name in AGENT_NODE_MAP.items():
        assert node_name == f"{key}_node", f"{key} → {node_name} 형식 불일치"


def test_graph_uses_agent_key_registry():
    """graph._NODE_MAP이 AgentKey를 키로 사용하고, ALL_AGENTS가 AgentKey 리스트인지 검증"""
    from ai_server.agents import graph
    from ai_server.agents.registry import AgentKey

    # _NODE_MAP의 모든 키가 AgentKey 인스턴스인지 확인
    for key in graph._NODE_MAP:
        assert isinstance(key, AgentKey), f"_NODE_MAP key {key!r} is not AgentKey"

    # ALL_AGENTS의 모든 원소가 AgentKey 인스턴스인지 확인
    for agent in graph.ALL_AGENTS:
        assert isinstance(agent, AgentKey), f"ALL_AGENTS entry {agent!r} is not AgentKey"
