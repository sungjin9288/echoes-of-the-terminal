# Echoes of the Terminal - Current Game Settings Book

기준일: 2026-03-05  
기준 소스: `main.py`, `constants.py`, `progression_system.py`, `diver_class.py`, `artifact_system.py`, `route_map.py`, `mutator_system.py`, `data_loader.py`

## 1. 게임 루프 개요
- 로비 메뉴
  - `1`: 게임 시작 (클래스 선택 후 런 시작)
  - `2`: 상점 (영구 특성 구매)
  - `3`: 종료
- 런 구조
  - 기본 포지션: 총 8개
  - 일반 구간: 7포지션 (`MAX_NODES_PER_RUN=7`)
  - 마지막 1포지션: 보스 고정
- 시나리오 선택
  - 일반/엘리트 노드: `scenarios.json`의 `is_boss != True` 중 셔플 후 최대 7개
  - 보스 노드: `is_boss == True` 중 1개 랜덤

## 2. 핵심 수치 (상수)
- 제한 시간
  - 기본: 30초
  - `time_extension` 특성 보유 시: 40초
- 타임아웃 패널티: +10% (`TIMEOUT_PENALTY`)
- 추적도 최대치: 100% (`TRACE_MAX`)
- 휴식 노드 기본 회복: 20%
- 엘리트 기본 페널티 배율: x1.5

## 3. 전투 명령어
- `help`: 명령어 목록
- `ls`: 현재 노드 정보
- `cat log`: 원본 로그 재출력
- `analyze [키워드]`: 정답 시 노드 클리어
- `clear`: 전투 화면 리렌더
- `skill`: 클래스 액티브 스킬 (런당 1회)

## 4. 전투 판정 규칙
- `analyze` 정답/오답은 소문자 정규화 후 비교
- 오답 시 추적도 상승 계산식
  - `base_penalty * penalty_multiplier * elite_mult * cracker_mult * memory_echo_mult`
  - 최솟값 1 보장
  - 보스 노드는 Ascension 보스 배율(`boss_penalty_mult`) 추가 적용
  - Ascension 18+에서는 보스 페이즈가 올라갈수록 추가 배율(`boss_phase_penalty_step`)이 누적됨
  - 보스 노드에서 `null_protocol` 보유 시 최종 페널티 상한 40 적용
- 타임아웃
  - 시간 초과 시 즉시 경고 메시지 출력
  - 패널티(+timeout_penalty)는 노드당 1회만 적용
- 사망 처리 우선순위 (추적도 100 이상)
  1. `backtrack_protocol` 퍼크 (런당 1회, 추적도 50으로 복구)
  2. `phantom_core` 아티팩트 (런당 1회, 추적도 75로 복구)
  3. 사망 확정 (`shutdown`)

## 5. 난이도/변주 시스템
- Easy: 변주 없음
- Hard: 단어 2~3개 글리치 치환
- NIGHTMARE:
  - 단어 5~7개 글리치 치환
  - 가짜 의심 키워드 노이즈 헤더 주입
- `glitch_filter` 퍼크 보유 시 `glitch_word_count=1` 강제 적용
- `noise_filter` 아티팩트 보유 시 NIGHTMARE 노이즈 헤더 제거

## 6. 노드 타입과 경로 분기
- 노드 타입: `NORMAL`, `REST`, `SHOP`, `ELITE`, `BOSS`
- 분기 생성 가중치 (`build_route_choices`)
  - NORMAL 50
  - REST 20
  - SHOP 15
  - ELITE 15
- 경로 선택
  - 시작 포지션(0)은 NORMAL 고정
  - 포지션 0~5 클리어 후 다음 경로 A/B 선택
  - 포지션 7은 BOSS 고정

## 7. 중간 상점 (SHOP 노드)
- 아이템 1: 추적도 제거제
  - 효과: 추적도 즉시 -25%
  - 비용: 데이터 조각 15
- 아이템 2: 오답 면역 쉴드
  - 효과: 다음 오답 1회 페널티 무시
  - 비용: 데이터 조각 25

## 8. 메타 상점 (로비)
- 구매 가능 영구 특성
  1. `penalty_reduction` (50)
  2. `time_extension` (30)
  3. `glitch_filter` (20)
  4. `backtrack_protocol` (80)
  5. `lexical_assist` (60)

## 9. 보상 공식
- 노드 난이도별 기본 보상
  - Easy: 10
  - Hard: 15
  - NIGHTMARE: 30
- 승리 보너스: +30
- 사망 시: 기본 보상 * 0.6 (소수점 버림)
- 실제 정산 시 `run_game_session`에서 반환한 클리어 난이도 목록 기반으로 계산

## 9-1. 100시간 캠페인 클리어 조건
- 목표 시간: 100시간
- 캠페인 클리어 조건 (모두 충족)
  - 캠페인 포인트 `60,000` 이상
  - 누적 승리 `450`회 이상
  - 클래스별 승리 `120`회 이상
    - ANALYST 120+
    - GHOST 120+
    - CRACKER 120+
- 캠페인 점수 획득 규칙
  - `campaign_gain = final_reward + (승리 시 +20)`
- 런 종료 시마다 `runs`, `points`, `victories`, `class_victories`가 세이브에 누적 저장됨
- 조건 달성 시 `campaign.cleared=True`로 전환되고 진엔딩 알림 출력

## 9-2. Ascension (각성 레벨)
- 범위: `0~20` (기본 해금 0)
- 상세 수치표: `ASCENSION_BALANCE_TABLE.md` 참고 (코드 SSOT: `progression_system.ASCENSION_TABLE`)
- 해금 규칙
  - 현재 해금 레벨 이상에서 `승리`하면 다음 레벨 1단계 해금
  - 예: 해금 3 상태에서 Asc 3 승리 → 해금 4
- 기본 난이도 효과
  - ASC 1+: 오답 기본 페널티 +5
  - ASC 2+: EASY 노드에도 글리치 강제 적용
  - ASC 3+: 제한 시간 -20초 (최소 10초)
  - ASC 4+: 타임아웃 페널티 +4
  - ASC 5+: 런 시작 TRACE 20%
- 상위 레벨(ASC 6~20) 추가 압축 보정
  - 오답 페널티, 타임아웃 패널티, 제한 시간을 단계적으로 추가 강화
- 후반 티어 규칙 (경제/보스 강화)
  - ASC 10~14: 상점가 ×1.15, 런 보상 ×0.95, 보스 오답 페널티 ×1.10
  - ASC 15~19: 상점가 ×1.30, 런 보상 ×0.90, 보스 오답 페널티 ×1.20
  - ASC 20: 상점가 ×1.50, 런 보상 ×0.85, 보스 오답 페널티 ×1.35
- 후반 티어 규칙 (보스 멀티 페이즈)
  - ASC 18~19: 보스 2페이즈 (페이즈당 제한시간 -2초, 페이즈당 보스 페널티 추가 배율 +0.10)
  - ASC 20: 보스 3페이즈 (페이즈당 제한시간 -2초, 페이즈당 보스 페널티 추가 배율 +0.12)
- ASC 20 전용 보스 패턴
  - 보스 진입 시 가짜 키워드 경보 4개 출력 (정답 유도 교란)
  - 보스 2페이즈부터 `cat log` 명령 차단
  - 보스 3페이즈부터 `skill` 명령 차단
  - 차단된 명령 입력 시 TRACE +4 즉시 부과
  - 보스 페이즈별 `text_log`/`target_keyword`는 `boss_phase_pack.json` 오버라이드 데이터팩 우선 적용
- 후반 티어 규칙 (경로 변이)
  - ASC 12~14: NORMAL의 일부가 ELITE로 치환, REST/SHOP 일부 NORMAL 치환, 최소 ELITE 선택지 1개 보장
  - ASC 15~19: 경로 변이 강화, 최소 ELITE 선택지 2개 보장
  - ASC 20: 경로 변이 최대치, 최소 ELITE 선택지 3개 보장
- 저장 필드
  - `campaign.ascension_unlocked`

## 10. 클래스 설정 (현재 구현 기준)
### ANALYST
- 패시브
  - 노드 진입 시 키워드 글자 수 힌트
  - 오답 시 카테고리 힌트(날짜/이름/사건)
- 액티브: 딥 스캔
  - 키워드 첫 두 글자 공개

### GHOST
- 패시브
  - 오답 페널티 x0.8
  - 타임아웃 페널티 6으로 고정
- 액티브: 페이드아웃
  - 현재 추적도 -15%

### CRACKER
- 패시브
  - 클리어 스택(최대 5) 누적, 오답 페널티 최대 25% 감소
  - ELITE 아티팩트 선택지 +1
- 액티브: 브루트 포스
  - 다음 오답 1회 페널티 면역

## 11. 아티팩트 설정 (15종)
### COMMON
1. `static_dampener`: 오답 페널티 x0.9
2. `coolant_pack`: REST 회복 +10
3. `data_shard_x`: 노드 클리어마다 조각 +3
4. `relay_booster`: 타임아웃 페널티 x0.7 (최소 1)
5. `ghost_signal`: 첫 오답 면역 슬롯 선점
6. `echo_cache`: `cat log` 시 타이머 +2초 (노드당 1회)
7. `noise_filter`: NIGHTMARE 노이즈 헤더 제거

### RARE
1. `trace_siphon`: 클리어 시 추적도 -5
2. `dual_core`: ELITE 배율 상한 1.2
3. `quantum_key`: 런당 1회 오답을 정답으로 전환
4. `overclock`: 제한 시간 +5초
5. `memory_echo`: 이미 클리어한 테마에서 오답 페널티 20% 감소

### EPIC
1. `null_protocol`: 보스 오답 페널티 상한 40
2. `phantom_core`: 사망 시 1회 부활(추적도 75)
3. `argos_fragment`: 노드 진입마다 추적도 -3

### 드랍 규칙
- 중복 아티팩트 미허용
- 희귀도 가중치
  - COMMON 60
  - RARE 30
  - EPIC 10
- ELITE 클리어: 기본 3선택지 (CRACKER는 4)
- BOSS 클리어: 2선택지

## 12. 세이브/데이터 포맷
- 기본 세이브 구조
  - `data_fragments`: int
  - `perks`: 5개 bool
  - `campaign`: 장기 진행도 dict
    - `points`: int
    - `runs`: int
    - `victories`: int
    - `class_victories`: `{ANALYST, GHOST, CRACKER}` int
    - `cleared`: bool
- 리소스 필수 파일
  - `scenarios.json`
  - `argos_taunts.json`
  - `boss_phase_pack.json` (ASC20 보스 페이즈 오버라이드)
- 시나리오 필수 키
  - `node_id`, `theme`, `difficulty`, `text_log`, `target_keyword`, `penalty_rate`

## 13. 현재 데이터셋 통계 (scenarios.json)
- 총 시나리오: 200
- 일반 시나리오: 178 (Easy 89 + Hard 89)
- 보스 시나리오: 22 (NIGHTMARE 전용)
- 난이도 분포
  - Easy: 89 (일반)
  - Hard: 89 (일반)
  - NIGHTMARE: 22 (보스 전용)
- 테마 수: 110
- Pack 01~02: node_id 1~118 (기존)
- Pack 03: node_id 119~128 (ANTARCTIC, RENAISSANCE, FUTURE_COURT, AI_LOG)
- Pack 04: node_id 129~136 (POW_INTERROGATION, ANCIENT_EGYPT, CYBER_TERROR, COLONY_PLANET)
- Pack 05: node_id 137~144 (ASYLUM_JOURNAL, JOSEON_ANNALS, MAFIA_DOCUMENT, SUBMARINE_LOG)
- Pack 06: node_id 145~152 (MEDIEVAL_MONASTERY, COLD_WAR_SPY, DEEP_SEA_BASE, PLAGUE_RECORD)
- Pack 07: node_id 153~160 (SPACE_STATION, VIKING_VOYAGE, PROHIBITION_ERA, ROMAN_LEGION)
- Pack 08: node_id 161~168 (OTTOMAN_COURT, WILD_WEST, ARCTIC_EXPEDITION, CYBER_FUTURE)
- Pack 09: node_id 169~176 (EDO_JAPAN, FRENCH_REVOLUTION, PIRATE_ERA, COLD_LAB)
- Pack 10: node_id 177~184 (TANG_DYNASTY, AMERICAN_REVOLUTION, AZTEC_EMPIRE, INDUSTRIAL_ENGLAND)
- Pack 11: node_id 185~192 (MING_DYNASTY, COLD_WAR_BERLIN, FRENCH_RESISTANCE, OTTOMAN_EXPANSION)
- Pack 12: node_id 193~200 (SPANISH_INQUISITION, MONGOL_EMPIRE, BRITISH_COLONIAL, SOVIET_ERA)

## 14. 구현-설명 차이 메모 (현 시점)
기준일 업데이트: 2026-04-09

이전에 미구현으로 기록된 3개 항목 모두 구현 완료 확인됨.

| 항목 | 상태 | 구현 위치 |
|------|------|-----------|
| ANALYST "HARD 이상 penalty 10% 감소" | ✅ 구현 완료 | `combat_commands.py::calculate_analyze_penalty` — `analyst_hard_penalty_reduction` 플래그 |
| GHOST "REST 회복 +15" | ✅ 구현 완료 | `diver_class.py` → `rest_heal_bonus_class` 런타임 키 → REST 노드 계산 연결 |
| CRACKER "1초 내 정답 시 추적도 -3" | ✅ 구현 완료 | `combat_commands.py::handle_analyze` — `CRACKER_SPEED_BONUS_*` 상수 기반 |

추가 구현 여지가 있는 신규 항목:
- (현재 없음)

## 15. 운영 스크립트
- `scripts/generate_boss_phase_pack_template.py`
  - 용도: `scenarios.json`의 보스 목록 기준으로 `boss_phase_pack` 템플릿을 생성/동기화
  - 특징:
    - 기존 `boss_phase_pack.json` 내용이 있으면 우선 보존
    - 누락된 페이즈는 자동 placeholder로 채움
    - 보스 목록은 현재 시나리오 데이터 기준으로 재정렬/동기화
  - 실행 예시:
    - `python scripts/generate_boss_phase_pack_template.py`
    - `python scripts/generate_boss_phase_pack_template.py --output boss_phase_pack.json --phase-count 3`
