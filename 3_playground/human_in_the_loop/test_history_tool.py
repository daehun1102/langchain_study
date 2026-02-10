from src.semiconductor.tool import generate_random_process_history

def test_history_tool():
    print("--- 공정 이력 생성 도구 테스트 ---")
    
    for i in range(3):
        print(f"\n[테스트 케이스 {i+1}]")
        lot_id = f"TEST_LOT_{i}"
        history = generate_random_process_history(lot_id)
        print(history)
        
        # 검증 로직
        if "ABNORMAL" not in history:
            print("ERROR: ABNORMAL 상태가 없음")
        if history.count("ABNORMAL") > 1:
            print("ERROR: ABNORMAL 상태가 1개 초과임")
            
        valid_steps = ["Photo", "Etch", "Deposition"]
        lines = history.split("\n")[1:] # 첫 줄은 헤더
        for line in lines:
            if not any(step in line for step in valid_steps):
                print(f"ERROR: 유효하지 않은 공정 스텝 발견: {line}")

if __name__ == "__main__":
    test_history_tool()
