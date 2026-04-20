"""게임 전역 상수 모음 — 단일 진실 공급원(SSOT).

mutator_system.py 와 main.py 두 곳에 중복 하드코딩되어 있던
TIME_LIMIT_SECONDS 등 모든 게임 상수를 이 파일에서 중앙 관리한다.
"""

# ── 버전 정보 ─────────────────────────────────────────────────────────────────
VERSION: str = "1.13.0"
BUILD_DATE: str = "2026-04-20"

# ── 타임 프레셔 ───────────────────────────────────────────────────────────────
TIME_LIMIT_DEFAULT: int = 30    # 기본 입력 제한 시간 (초)
TIME_LIMIT_EXTENDED: int = 40   # time_extension 특성 보유 시 제한 시간 (초)
TIMEOUT_PENALTY: int = 10       # 시간 초과 1회당 추적도 상승량 (%)

# ── 게임 진행 ─────────────────────────────────────────────────────────────────
MAX_NODES_PER_RUN: int = 7      # 런당 일반 노드 수 (보스 노드 1개 별도 추가)
TRACE_MAX: int = 100            # 추적도 상한 (%)

# ── 보상 공식 계수 ─────────────────────────────────────────────────────────────
REWARD_PER_EASY: int = 10        # Easy 노드 정답 시 기본 보상 (조각)
REWARD_PER_HARD: int = 15        # Hard 노드 정답 시 보상 (조각)
REWARD_PER_NIGHTMARE: int = 30   # NIGHTMARE 노드 정답 시 보상 (조각)
VICTORY_BONUS: int = 30          # 전 노드 클리어(승리) 추가 보상 (조각)
DEATH_MULTIPLIER: float = 0.6    # 사망 시 보상 지급 비율 (40% 손실)

# ── 루트 맵 ───────────────────────────────────────────────────────────────────
REST_HEAL_AMOUNT: int = 20        # REST 노드 통과 시 추적도 감소량 (%)
ELITE_PENALTY_MULT: float = 1.5   # ELITE 노드 페널티 배율 (보상도 동일 배율 상승)
MID_SHOP_TRACE_HEAL: int = 25     # 중간 상점 추적도 회복 아이템 효과 (%)
MID_SHOP_TRACE_COST: int = 15     # 중간 상점 추적도 회복 아이템 비용 (조각)
MID_SHOP_BUFFER_COST: int = 25    # 중간 상점 오답 면역 아이템 비용 (조각)

# ── 캠페인 ────────────────────────────────────────────────────────────────────
CAMPAIGN_VICTORY_BONUS: int = 20    # 승리 런에 추가되는 캠페인 포인트 보너스
DAILY_REWARD_MULTIPLIER: float = 1.5  # 데일리 챌린지 보상 배율

# ── CRACKER 클래스 속공 보너스 ─────────────────────────────────────────────────
CRACKER_SPEED_BONUS_THRESHOLD: int = 50   # 속공 보너스 발동 최소 추적도 (%)
CRACKER_SPEED_BONUS_TIME: float = 1.0     # 속공 판정 시간 (초)
CRACKER_SPEED_BONUS_AMOUNT: int = 3       # 속공 보너스 추적도 감소량 (%)
