"""업적 정의 데이터 — 115종 업적 목록 및 파생 상수.

이 파일은 순수 데이터만 포함한다. 평가 로직은 achievement_system.py 참조.
"""

from __future__ import annotations


ACHIEVEMENTS: tuple[dict[str, str], ...] = (
    # ── 탐험 (Exploration) ────────────────────────────────────────────────────
    {
        "id": "first_shutdown",
        "title": "첫 번째 추락",
        "desc": "처음으로 SYSTEM SHUTDOWN을 경험했다.",
    },
    {
        "id": "first_breach",
        "title": "첫 번째 돌파",
        "desc": "처음으로 CORE BREACHED에 성공했다.",
    },
    {
        "id": "runs_10",
        "title": "단골 해커",
        "desc": "총 10회 런을 완료했다 (승패 무관).",
    },
    {
        "id": "runs_50",
        "title": "숙련된 침입자",
        "desc": "총 50회 런을 완료했다.",
    },
    {
        "id": "victories_5",
        "title": "연속 타격",
        "desc": "5회 이상 승리했다.",
    },
    {
        "id": "victories_25",
        "title": "중견 해커",
        "desc": "누적 25회 승리를 달성했다.",
    },
    # ── 완벽 수행 (Perfection) ────────────────────────────────────────────────
    {
        "id": "perfect_infiltration",
        "title": "완전 침묵",
        "desc": "오답과 타임아웃 없이 런을 클리어했다.",
    },
    {
        "id": "zero_trace_win",
        "title": "무결의 침투",
        "desc": "런 종료 시 추적도 0%로 승리했다.",
    },
    {
        "id": "perfect_analyst",
        "title": "순수 분석",
        "desc": "ANALYST로 오답 없이 런을 클리어했다.",
    },
    {
        "id": "no_perk_win",
        "title": "맨손 돌파",
        "desc": "영구 특성 없이 런을 클리어했다.",
    },
    # ── 클래스 (Class) ────────────────────────────────────────────────────────
    {
        "id": "analyst_victory",
        "title": "분석의 끝",
        "desc": "ANALYST로 첫 승리를 달성했다.",
    },
    {
        "id": "ghost_victory",
        "title": "그림자 질주",
        "desc": "GHOST로 첫 승리를 달성했다.",
    },
    {
        "id": "cracker_victory",
        "title": "파열 지점",
        "desc": "CRACKER로 첫 승리를 달성했다.",
    },
    {
        "id": "class_trinity",
        "title": "삼중 잠입",
        "desc": "세 클래스 모두로 최소 1회 승리했다.",
    },
    {
        "id": "analyst_master",
        "title": "알고리즘의 주인",
        "desc": "ANALYST로 5회 이상 승리했다.",
    },
    {
        "id": "ghost_master",
        "title": "그림자 귀신",
        "desc": "GHOST로 5회 이상 승리했다.",
    },
    {
        "id": "cracker_master",
        "title": "균열 전문가",
        "desc": "CRACKER로 5회 이상 승리했다.",
    },
    {
        "id": "triple_master",
        "title": "전천후 침입자",
        "desc": "세 클래스 모두 5회 이상 승리했다.",
    },
    # ── 도전 (Challenge) ──────────────────────────────────────────────────────
    {
        "id": "ascension_5",
        "title": "첫 번째 도전",
        "desc": "Ascension 5 이상에서 승리했다.",
    },
    {
        "id": "ascension_10",
        "title": "고도 상승",
        "desc": "Ascension 10 이상에서 승리했다.",
    },
    {
        "id": "ascension_15",
        "title": "극한의 영역",
        "desc": "Ascension 15 이상에서 승리했다.",
    },
    {
        "id": "ascension_20",
        "title": "심연 돌파",
        "desc": "Ascension 20을 클리어했다.",
    },
    {
        "id": "nightmare_clear",
        "title": "악몽의 생존자",
        "desc": "NIGHTMARE 난이도 노드가 포함된 런을 클리어했다.",
    },
    # ── 수집 (Collection) ─────────────────────────────────────────────────────
    {
        "id": "perk_collector",
        "title": "완비된 장비실",
        "desc": "모든 영구 특성을 해금했다.",
    },
    {
        "id": "endings_3",
        "title": "분기의 목격자",
        "desc": "3종 이상의 엔딩을 해금했다.",
    },
    {
        "id": "endings_8",
        "title": "결말의 수집가",
        "desc": "8종 이상의 엔딩을 해금했다.",
    },
    {
        "id": "all_endings",
        "title": "모든 결말",
        "desc": "11종 엔딩을 모두 해금했다.",
    },
    # ── 캠페인 (Campaign) ─────────────────────────────────────────────────────
    {
        "id": "campaign_clear",
        "title": "터미널의 침묵",
        "desc": "100시간 캠페인을 완전히 클리어했다.",
    },
    {
        "id": "campaign_points_10000",
        "title": "누적된 데이터",
        "desc": "캠페인 포인트 10,000점을 돌파했다.",
    },
    {
        "id": "campaign_points_30000",
        "title": "데이터 수집가",
        "desc": "캠페인 포인트 30,000점을 달성했다.",
    },
    # ── 극한 (Extreme) ────────────────────────────────────────────────────────
    {
        "id": "all_nodes_correct",
        "title": "완벽한 런",
        "desc": "8노드 모두 첫 번째 시도에 정답을 입력해 클리어했다.",
    },
    {
        "id": "ascension_20_perfect",
        "title": "전설적 침투",
        "desc": "Ascension 20에서 오답 없이 클리어했다.",
    },
    # ── 탐험 확장 (Exploration+) ──────────────────────────────────────────────
    {
        "id": "runs_25",
        "title": "단골 침입자",
        "desc": "총 25회 런을 완료했다.",
    },
    {
        "id": "runs_100",
        "title": "베테랑 해커",
        "desc": "총 100회 런을 완료했다.",
    },
    {
        "id": "runs_200",
        "title": "살아있는 전설",
        "desc": "총 200회 런을 완료했다.",
    },
    {
        "id": "victories_50",
        "title": "엘리트 침투자",
        "desc": "누적 50회 승리를 달성했다.",
    },
    {
        "id": "victories_100",
        "title": "시스템의 적",
        "desc": "누적 100회 승리를 달성했다.",
    },
    # ── 완벽 수행 확장 (Perfection+) ─────────────────────────────────────────
    {
        "id": "perfect_ghost",
        "title": "유령의 완전함",
        "desc": "GHOST로 오답 없이 런을 클리어했다.",
    },
    {
        "id": "perfect_cracker",
        "title": "오류 없는 균열",
        "desc": "CRACKER로 오답 없이 런을 클리어했다.",
    },
    {
        "id": "no_skill_win",
        "title": "맨 머리로 돌파",
        "desc": "액티브 스킬을 한 번도 사용하지 않고 런을 클리어했다.",
    },
    # ── 클래스 마스터 확장 (Class+) ───────────────────────────────────────────
    {
        "id": "analyst_10",
        "title": "알고리즘의 신",
        "desc": "ANALYST로 10회 이상 승리했다.",
    },
    {
        "id": "ghost_10",
        "title": "그림자의 전설",
        "desc": "GHOST로 10회 이상 승리했다.",
    },
    {
        "id": "cracker_10",
        "title": "파열의 달인",
        "desc": "CRACKER로 10회 이상 승리했다.",
    },
    {
        "id": "triple_10",
        "title": "완전한 침입자",
        "desc": "세 클래스 모두 10회 이상 승리했다.",
    },
    # ── 도전 확장 (Challenge+) ────────────────────────────────────────────────
    {
        "id": "ascension_3",
        "title": "첫 번째 각성",
        "desc": "Ascension 3 이상에서 승리했다.",
    },
    {
        "id": "ascension_7",
        "title": "시스템 압박",
        "desc": "Ascension 7 이상에서 승리했다.",
    },
    {
        "id": "ascension_12",
        "title": "심화 침투",
        "desc": "Ascension 12 이상에서 승리했다.",
    },
    {
        "id": "ascension_17",
        "title": "극한의 문턱",
        "desc": "Ascension 17 이상에서 승리했다.",
    },
    # ── 수집 확장 (Collection+) ───────────────────────────────────────────────
    {
        "id": "campaign_points_50000",
        "title": "데이터 폭풍",
        "desc": "캠페인 포인트 50,000점을 달성했다.",
    },
    {
        "id": "campaign_points_100000",
        "title": "무한 데이터",
        "desc": "캠페인 포인트 100,000점을 달성했다.",
    },
    # ── 극한 확장 (Extreme+) ──────────────────────────────────────────────────
    {
        "id": "ascension_20_analyst",
        "title": "알고리즘의 끝자락",
        "desc": "ANALYST로 Ascension 20을 클리어했다.",
    },
    {
        "id": "ascension_20_ghost",
        "title": "그림자의 정점",
        "desc": "GHOST로 Ascension 20을 클리어했다.",
    },
    {
        "id": "ascension_20_cracker",
        "title": "균열의 완성",
        "desc": "CRACKER로 Ascension 20을 클리어했다.",
    },
    {
        "id": "asc20_no_perk",
        "title": "맨손의 신",
        "desc": "영구 특성 없이 Ascension 20을 클리어했다.",
    },
    {
        "id": "asc20_trinity",
        "title": "터미널의 지배자",
        "desc": "세 클래스 모두로 Ascension 20을 클리어했다.",
    },
    {
        "id": "analyst_zero_trace",
        "title": "완벽한 분석",
        "desc": "ANALYST로 런 종료 시 추적도 0%로 승리했다.",
    },
    # ── 탐험 추가 (Exploration++) ──────────────────────────────────────────────
    {
        "id": "victories_10",
        "title": "검증된 해커",
        "desc": "누적 10회 승리를 달성했다.",
    },
    # ── 완벽 심화 (Perfection++) ──────────────────────────────────────────────
    {
        "id": "perfect_asc5",
        "title": "각성 속 완벽함",
        "desc": "Ascension 5 이상에서 오답 없이 런을 클리어했다.",
    },
    {
        "id": "perfect_asc10",
        "title": "심화 각성의 완벽함",
        "desc": "Ascension 10 이상에서 오답 없이 런을 클리어했다.",
    },
    {
        "id": "no_skill_asc10",
        "title": "맨주먹의 각성자",
        "desc": "액티브 스킬 미사용으로 Ascension 10 이상에서 승리했다.",
    },
    # ── 클래스 심화 (Class++) ─────────────────────────────────────────────────
    {
        "id": "ghost_no_timeout",
        "title": "소리 없는 유령",
        "desc": "GHOST로 타임아웃 없이 런을 클리어했다.",
    },
    {
        "id": "cracker_nightmare",
        "title": "균열의 악몽",
        "desc": "CRACKER로 NIGHTMARE 노드가 포함된 런을 클리어했다.",
    },
    {
        "id": "analyst_asc15",
        "title": "분석의 극한",
        "desc": "ANALYST로 Ascension 15 이상에서 승리했다.",
    },
    {
        "id": "ghost_asc15",
        "title": "유령의 극한",
        "desc": "GHOST로 Ascension 15 이상에서 승리했다.",
    },
    {
        "id": "cracker_asc15",
        "title": "균열의 극한",
        "desc": "CRACKER로 Ascension 15 이상에서 승리했다.",
    },
    # ── 수집/해금 (Collection++) ──────────────────────────────────────────────
    {
        "id": "endings_1",
        "title": "첫 번째 결말",
        "desc": "첫 번째 엔딩을 해금했다.",
    },
    {
        "id": "perk_first",
        "title": "첫 번째 강화",
        "desc": "첫 번째 영구 특성을 해금했다.",
    },
    {
        "id": "ascension_unlocked_5",
        "title": "각성의 문턱",
        "desc": "Ascension 5까지 해금했다.",
    },
    {
        "id": "ascension_unlocked_10",
        "title": "각성의 중반",
        "desc": "Ascension 10까지 해금했다.",
    },
    {
        "id": "ascension_unlocked_15",
        "title": "각성의 심연",
        "desc": "Ascension 15까지 해금했다.",
    },
    {
        "id": "ascension_unlocked_20",
        "title": "각성의 정점",
        "desc": "Ascension 20까지 완전히 해금했다.",
    },
    # ── 데이터 파편 (Data Fragments) ─────────────────────────────────────────
    {
        "id": "data_fragments_500",
        "title": "데이터 수집가",
        "desc": "데이터 파편을 500개 이상 보유했다.",
    },
    {
        "id": "data_fragments_2000",
        "title": "데이터 군주",
        "desc": "데이터 파편을 2,000개 이상 보유했다.",
    },
    # ── 극한 심화 (Extreme++) ─────────────────────────────────────────────────
    {
        "id": "perfect_analyst_asc10",
        "title": "알고리즘의 완성",
        "desc": "ANALYST로 Ascension 10 이상에서 오답 없이 승리했다.",
    },
    {
        "id": "perfect_ghost_asc10",
        "title": "그림자의 완성",
        "desc": "GHOST로 Ascension 10 이상에서 오답 없이 승리했다.",
    },
    {
        "id": "perfect_cracker_asc10",
        "title": "균열의 완성",
        "desc": "CRACKER로 Ascension 10 이상에서 오답 없이 승리했다.",
    },
    # ── 탐험 최종 (Exploration Final) ────────────────────────────────────────
    {
        "id": "runs_300",
        "title": "침입의 역사",
        "desc": "총 300회 런을 완료했다.",
    },
    {
        "id": "runs_500",
        "title": "불멸의 해커",
        "desc": "총 500회 런을 완료했다.",
    },
    {
        "id": "victories_200",
        "title": "무적의 침투자",
        "desc": "누적 200회 승리를 달성했다.",
    },
    {
        "id": "victories_500",
        "title": "전설의 시작",
        "desc": "누적 500회 승리를 달성했다.",
    },
    # ── 완벽 최종 (Perfection Final) ─────────────────────────────────────────
    {
        "id": "perfect_asc15",
        "title": "각성의 완벽함",
        "desc": "Ascension 15 이상에서 오답 없이 런을 클리어했다.",
    },
    {
        "id": "no_skill_perfect",
        "title": "본능적 침투",
        "desc": "액티브 스킬 미사용으로 오답 없이 런을 클리어했다.",
    },
    {
        "id": "ghost_trace_zero",
        "title": "유령의 궤적",
        "desc": "GHOST로 런 종료 시 추적도 0%로 승리했다.",
    },
    {
        "id": "cracker_trace_zero",
        "title": "균열 없는 균열",
        "desc": "CRACKER로 런 종료 시 추적도 0%로 승리했다.",
    },
    {
        "id": "no_timeout_asc15",
        "title": "시간을 지배하는 자",
        "desc": "Ascension 15 이상에서 타임아웃 없이 승리했다.",
    },
    {
        "id": "survivor",
        "title": "포기를 모르는 자",
        "desc": "3회 이상 오답 입력 후에도 런을 클리어했다.",
    },
    # ── 클래스 최종 (Class Final) ─────────────────────────────────────────────
    {
        "id": "analyst_nightmare",
        "title": "분석의 악몽",
        "desc": "ANALYST로 NIGHTMARE 노드가 포함된 런을 클리어했다.",
    },
    {
        "id": "ghost_nightmare",
        "title": "유령의 악몽",
        "desc": "GHOST로 NIGHTMARE 노드가 포함된 런을 클리어했다.",
    },
    {
        "id": "perfect_analyst_asc20",
        "title": "분석의 신",
        "desc": "ANALYST로 Ascension 20에서 오답 없이 런을 클리어했다.",
    },
    {
        "id": "perfect_ghost_asc20",
        "title": "유령의 신",
        "desc": "GHOST로 Ascension 20에서 오답 없이 런을 클리어했다.",
    },
    {
        "id": "perfect_cracker_asc20",
        "title": "균열의 신",
        "desc": "CRACKER로 Ascension 20에서 오답 없이 런을 클리어했다.",
    },
    {
        "id": "ghost_asc20_no_timeout",
        "title": "유령의 침묵",
        "desc": "GHOST로 Ascension 20에서 타임아웃 없이 승리했다.",
    },
    {
        "id": "no_skill_asc20",
        "title": "각성 속 맨주먹",
        "desc": "Ascension 20에서 액티브 스킬을 사용하지 않고 승리했다.",
    },
    # ── 핸디캡 (Handicap) ────────────────────────────────────────────────────
    {
        "id": "no_skill_no_perk",
        "title": "순수한 침투",
        "desc": "영구 특성과 액티브 스킬 없이 런을 클리어했다.",
    },
    {
        "id": "analyst_no_perk",
        "title": "무장해제된 분석가",
        "desc": "ANALYST로 영구 특성 없이 승리했다.",
    },
    {
        "id": "ghost_no_perk",
        "title": "무장해제된 유령",
        "desc": "GHOST로 영구 특성 없이 승리했다.",
    },
    {
        "id": "cracker_no_perk",
        "title": "무장해제된 균열",
        "desc": "CRACKER로 영구 특성 없이 승리했다.",
    },
    # ── 수집 최종 (Collection Final) ─────────────────────────────────────────
    {
        "id": "data_fragments_5000",
        "title": "데이터 황제",
        "desc": "데이터 파편을 5,000개 이상 보유했다.",
    },
    {
        "id": "data_fragments_10000",
        "title": "데이터 신",
        "desc": "데이터 파편을 10,000개 이상 보유했다.",
    },
    {
        "id": "campaign_points_200000",
        "title": "무한 데이터 군주",
        "desc": "캠페인 포인트 200,000점을 달성했다.",
    },
    {
        "id": "campaign_points_500000",
        "title": "시스템의 붕괴",
        "desc": "캠페인 포인트 500,000점을 달성했다.",
    },
    # ── MYSTERY (미스터리 노드) ───────────────────────────────────────────────
    {
        "id": "mystery_first_engage",
        "title": "첫 번째 도박",
        "desc": "처음으로 MYSTERY 노드에서 이벤트에 개입했다.",
    },
    {
        "id": "mystery_good_5",
        "title": "행운의 다이버",
        "desc": "MYSTERY 노드 개입에서 좋은 결과를 누적 5회 얻었다.",
    },
    {
        "id": "mystery_engaged_20",
        "title": "위험 중독자",
        "desc": "MYSTERY 노드에서 총 20회 이상 개입했다.",
    },
    {
        "id": "mystery_all_good_run",
        "title": "완벽한 직관",
        "desc": "한 런에서 모든 MYSTERY 개입에서 좋은 결과를 얻었다 (최소 2회 이상 개입).",
    },
    {
        "id": "mystery_all_skip_run",
        "title": "신중한 해커",
        "desc": "한 런에서 모든 MYSTERY 노드를 무시했다 (최소 2회 이상 등장).",
    },
    # ── 아티팩트 (Artifact) ───────────────────────────────────────────────────
    {
        "id": "artifact_first_win",
        "title": "첫 번째 강화 장비",
        "desc": "아티팩트를 1종 이상 보유한 채 처음으로 승리했다.",
    },
    {
        "id": "artifact_hoarder",
        "title": "장비 욕심쟁이",
        "desc": "한 런에서 아티팩트 3종 이상을 보유한 채 승리했다.",
    },
    {
        "id": "artifact_zealot",
        "title": "완전 무장 전술가",
        "desc": "한 런에서 아티팩트 5종 이상을 보유한 채 승리했다.",
    },
    # ── 퍼크 (Perk) v9.1 ─────────────────────────────────────────────────────
    {
        "id": "perk_hoarder_5",
        "title": "특성 수집가",
        "desc": "5종 이상의 영구 특성을 보유했다.",
    },
    {
        "id": "perk_hoarder_10",
        "title": "특성 마스터",
        "desc": "10종 이상의 영구 특성을 보유했다.",
    },
    {
        "id": "swift_first_win",
        "title": "신속한 직감",
        "desc": "swift_analysis 퍼크를 보유한 채 처음으로 승리했다.",
    },
    # ── 특수 아티팩트 (v9.4) ─────────────────────────────────────────────────
    {
        "id": "cascade_master",
        "title": "연쇄 해커",
        "desc": "cascade_core 아티팩트를 보유하고 승리했다.",
    },
    {
        "id": "void_hunter",
        "title": "공허 사냥꾼",
        "desc": "void_scanner 보너스를 획득한 채 승리했다.",
    },
    {
        "id": "mystery_rich",
        "title": "운 좋은 침투자",
        "desc": "단일 런 MYSTERY 이벤트로 데이터 조각 300 이상 획득 후 승리했다.",
    },
)

ACHIEVEMENT_INDEX: dict[str, dict[str, str]] = {
    item["id"]: item for item in ACHIEVEMENTS
}

DEFAULT_ACHIEVEMENT_STATE: dict[str, list[str]] = {
    "unlocked": [],
}

