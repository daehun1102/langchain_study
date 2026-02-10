from langchain.tools import tool

# --- 포토(Photo) 공정 도구 ---
@tool
def inspect_photo_patterns(lot_id: str) -> str:
    """포토 공정의 회로 패턴을 검사합니다."""
    return f"LOT {lot_id} 포토 패턴 검사 결과: 정렬 오차 2nm 확인됨."

@tool
def measure_photo_cd(lot_id: str) -> str:
    """포토 공정의 CD(Critical Dimension)를 측정합니다."""
    return f"LOT {lot_id} CD 측정 결과: 평균 15nm (스펙 내 양호)."

# --- 식각(Etch) 공정 도구 ---
@tool
def inspect_etch_profile(lot_id: str) -> str:
    """식각 단면 프로파일을 검사합니다."""
    return f"LOT {lot_id} 식각 프로파일 검사 결과: 수직도 89.5도 (양호)."

@tool
def measure_etch_depth(lot_id: str) -> str:
    """식각 깊이를 측정합니다."""
    return f"LOT {lot_id} 식각 깊이 측정 결과: 타겟 대비 +1.2% 깊음."

# --- 증착(Deposition) 공정 도구 ---
@tool
def inspect_deposition_thickness(lot_id: str) -> str:
    """증착 막 두께를 측정합니다."""
    return f"LOT {lot_id} 증착 두께 측정 결과: 1025A (타겟 1000A)."

@tool
def check_deposition_uniformity(lot_id: str) -> str:
    """증착 균일도를 검사합니다."""
    return f"LOT {lot_id} 증착 균일도 검사 결과: 98.5% (매우 우수)."

# --- 공정 이력 생성 도구 ---
import random
from datetime import datetime, timedelta

@tool
def generate_random_process_history(lot_id: str) -> str:
    """LOT의 공정 이력을 무작위로 생성합니다."""
    steps = ["Photo", "Etch", "Deposition"] # 사용자가 지정한 3개 공정
    history = []
    current_time = datetime.now() - timedelta(days=5)
    
    # 5~10개의 공정 스텝 생성
    num_steps = random.randint(5, 10)
    
    # 이상 발생 스텝 인덱스를 무작위로 선정 (반드시 1개)
    abnormal_idx = random.randint(0, num_steps - 1)

    for i in range(num_steps):
        step = random.choice(steps)
        duration = timedelta(hours=random.randint(1, 12))
        current_time += duration
        
        if i == abnormal_idx:
            # 이상 발생: Loss를 높게 설정 (예: 20% ~ 50%)
            param_loss = random.uniform(20.0, 50.0)
            status = "ABNORMAL"
        else:
            # 정상: Loss를 낮게 설정 (예: 0.1% ~ 2.0%)
            param_loss = random.uniform(0.1, 2.0)
            status = "NORMAL"
            
        history.append(f"- {current_time.strftime('%Y-%m-%d %H:%M')}: {step} (Loss: {param_loss:.2f}%) [{status}]")
        
    return f"LOT {lot_id} 공정 이력:\n" + "\n".join(history)
