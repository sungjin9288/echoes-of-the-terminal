# CLAUDE.md — Echoes of the Terminal

## 1. 프로젝트 개요

**Echoes of the Terminal**은 Python으로 작성된 터미널 기반 텍스트 로그 추리 roguelike 게임이다.
플레이어는 수사 조서에서 논리적 결함을 찾아 키워드를 `analyze` 명령으로 제출하며, trace level(0-100%)을 관리하면서 7개 노드를 돌파한다.

---

## 2. Tech Stack

| 항목 | 버전 / 내용 |
|---|---|
| **Python** | 3.12 (최소 3.11+) |
| **rich** | `>=13.0.0` (prod), `==14.3.3` (dev) |
| **pytest** | `==9.0.2` |
| **주요 stdlib** | `json`, `dataclasses`, `enum`, `random`, `threading`, `time`, `pathlib`, `hashlib`, `re` |

의존성 설치:
```bash
pip install -r requirements.txt          # 프로덕션
pip install -r requirements-dev.txt      # 테스트 포함
```

---

## 3. 디렉토리 구조

```
Echoes of the Terminal/
├── main.py                  # 게임 루프 엔진 (1831줄)
├── ui_renderer.py           # Rich 터미널 UI 렌더링 (713줄)
├── progression_system.py    # 세이브/퍼크/캠페인/어센션 (544줄)
├── combat_commands.py       # 전투 커맨드 핸들러 + 페널티 계산 (279줄)
├── artifact_system.py       # 15종 아티팩트 시스템 (258줄)
├── data_loader.py           # JSON 데이터 로딩 & 검증 (231줄)
├── daily_challenge.py       # 일일 도전 시스템 (219줄)
├── ending_system.py         # 5종 엔딩 판정 (205줄)
├── diver_class.py           # 3종 다이버 클래스 (194줄)
├── achievement_system.py    # 100종 업적 시스템 (908줄)
├── mutator_system.py        # Glitch 마스킹 텍스트 변형 (128줄)
├── route_map.py             # 노드 타입 라우팅 (94줄)
├── boss_phase_pack_tools.py # ASC20 보스 툴 (89줄)
├── combat_timer.py          # 전투 타이머 캡슐화 (70줄)
├── constants.py             # 전역 상수 단일 출처 (37줄)
│
├── scenarios.json           # 152개 시나리오 데이터 (Pack 01-06)
├── boss_phase_pack.json     # ASC20 보스 페이즈 오버라이드
├── argos_taunts.json        # ARGOS AI 다이얼로그
├── save_data.json           # 플레이어 세이브 데이터 (런타임 생성)
│
├── tests/                   # pytest 테스트 (8파일, 109케이스)
│   ├── test_achievement_system.py
│   ├── test_artifact_effects.py
│   ├── test_ascension_runtime.py
│   ├── test_boss_phase_pack.py
│   ├── test_boss_phase_pack_tools.py
│   ├── test_campaign_progression.py
│   ├── test_penalty_calculation.py
│   └── test_run_game_session.py
│
├── scripts/                 # 유틸리티 스크립트
├── requirements.txt
├── requirements-dev.txt
└── README.md                # 한국어 게임 가이드
```

---

## 4. 빌드 & 실행 명령어

```bash
# 게임 실행
python main.py

# 전체 테스트
pytest tests/ -v

# 특정 파일만 테스트
pytest tests/test_run_game_session.py -v

# 테스트 이름으로 필터링
pytest -k "test_apply_ascension" -v

# 테스트 목록만 확인 (실행 없이)
pytest --collect-only
```

---

## 5. 코딩 규칙 (DO / DON'T)

### Rich 사용 패턴

**DO:**
```python
# ui_renderer.py 에 정의된 전역 Console 싱글턴을 재사용
from ui_renderer import console

console.print(Panel(content, title="TITLE", border_style="green"))
console.print(Text("경고", style="bold red"))

# 탐정 로그처럼 [ ] 괄호를 보존해야 하는 텍스트는 markup/highlight 비활성화
console.print(log_text, markup=False, highlight=False)
```

**DON'T:**
```python
# 각 모듈에서 Console()을 새로 만들지 말 것
console = Console()  # 모듈마다 생성 금지

# print()로 직접 출력 금지 — Rich 포맷이 깨짐
print("어떤 메시지")
```

### JSON 시나리오 구조

`scenarios.json`의 각 시나리오는 다음 스키마를 따른다:

```json
{
  "node_id": 1,
  "theme": "A",
  "difficulty": "Easy",
  "text_log": "【수사 조서 #84-1127-A】\n...",
  "target_keyword": "GPS",
  "penalty_rate": 20,
  "logical_flaw_explanation": "민간용 GPS는 1990년대 이후에...",
  "is_boss": false
}
```

| 필드 | 타입 | 값 |
|---|---|---|
| `node_id` | int | 고유 식별자 (1~) |
| `theme` | str | `"A"~"E"`, `"BOSS_THEME"` |
| `difficulty` | str | `"Easy"` / `"Hard"` / `"NIGHTMARE"` |
| `text_log` | str | 멀티라인 수사 조서 (한국어) |
| `target_keyword` | str | 정답 키워드 |
| `penalty_rate` | int | 오답 시 trace 패널티 % (10-80) |
| `logical_flaw_explanation` | str | 선택적: 논리적 결함 설명 |
| `is_boss` | bool | 선택적: 보스 노드 여부 |

**DON'T:**
- `node_id` 중복 금지 — `data_loader.py`에서 검증됨
- `target_keyword`에 공백이나 특수문자 넣지 말 것 — `mutator_system.py`에서 보호 대상으로 처리됨

### 상수 관리

```python
# constants.py 에서만 숫자 정의, 다른 곳에서는 임포트해서 사용
from constants import BASE_TIME_LIMIT, MAX_TRACE, PENALTY_MULTIPLIER

# DON'T: 매직 넘버 인라인 사용 금지
trace += 30  # 금지
```

### 데이터 흐름 원칙

- **Runtime Dict** (세션 중 불변): Ascension 수정자, 아티팩트 효과 플래그, 클래스 패시브 설정
- **Run State Dict** (세션 중 가변): 현재 trace, 오답 횟수, 타임아웃 이벤트, Cracker 스트릭 카운터
- **Save Data Dict** (영속 JSON): `data_fragments`, `perks`, `campaign`, `achievements`, `daily`, `endings`

세이브 데이터는 `progression_system.py`에서만 읽고 써야 한다. 다른 모듈에서 직접 파일 I/O 금지.

---

## 6. 핵심 설계 원칙

### 게임 루프 (`main.py::run_game_session`)

```
초기화 (Ascension + Perks → runtime modifiers)
    ↓
루트 생성 (NORMAL/SHOP/REST/ELITE 7노드)
    ↓
노드 순회 루프
    ├── SHOP/REST → 특수 노드 처리
    └── NORMAL/ELITE/BOSS → _run_combat_node()
            ↓
        로그 표시 (glitch masking 적용)
            ↓
        타이머 시작 (Rich progress bar)
            ↓
        플레이어 입력 (analyze [keyword])
            ↓
        패널티 계산 파이프라인
            ↓
        trace level 업데이트
            ↓
        사망 체크 (trace >= 100 → SHUTDOWN)
    ↓
정산: 보상 지급 → 엔딩 판정 → 세이브
```

### 패널티 계산 파이프라인

```
base_penalty = scenario.penalty_rate
    × penalty_multiplier (퍼크/클래스: 0.85~1.0)
    + ascension_penalty_flat (레벨당 +0~12%)
    × elite_penalty_mult (ELITE 노드: 1.5×)
    × artifact 감소 (static_dampener: -10%)
    × Cracker 스트릭 보너스 (-5% per correct)
    → 최종 trace 증가량
```

### 시나리오 로딩 (`data_loader.py`)

- PyInstaller 빌드와 개발 환경 모두 지원하는 경로 해석 로직 보유
- 로드 시 `node_id` 중복, 필수 필드 누락 검증 수행
- `scenarios.json`, `boss_phase_pack.json`, `argos_taunts.json` 별도 로더 함수

### 어센션 시스템 (Ascension 0-20)

| 레벨 | 변경 사항 |
|---|---|
| 0-5 | 패널티 +0~+5% flat |
| 6-11 | 제한시간 단축 + 시작 trace 20% |
| 12-14 | ELITE 노드 빈도 증가 |
| 15-17 | 상점 비용 증가, 보상 감소 |
| 18-19 | 보스 2페이즈 |
| 20 | 보스 3페이즈 + 가짜 키워드 + 명령어 제한 |

### 세이브 데이터 경로

- **Windows**: `%APPDATA%\Echoes of the Terminal\save_data.json`
- **macOS/Linux**: `./save_data.json` (실행 디렉토리)

---

## 7. 테스트 방법

### 테스트 구조

각 테스트 파일은 단일 모듈을 커버하며, Rich UI와 I/O를 `monkeypatch`로 모킹한다.

```python
# 일반 패턴
def test_penalty_with_elite_modifier(monkeypatch) -> None:
    scenario = _scenario(penalty_rate=30)      # 헬퍼로 테스트 데이터 생성
    runtime = {"elite_penalty_mult": 1.5, ...}

    result = main._calculate_analyze_penalty(scenario, runtime, ...)

    assert result == 45   # 30 × 1.5
```

### 모킹 전략

- `monkeypatch.setattr(main, "_run_combat_node", ...)` — 게임 루프 내 전투 노드를 모킹
- `monkeypatch.setattr(builtins, "input", lambda _: "A")` — 유저 입력 항상 "A"로 고정
- Rich `console.print()` 모킹으로 출력 억제

### 테스트 커버리지 영역

| 파일 | 케이스 | 내용 |
|---|---|---|
| `test_achievement_system.py` | 70 | 100종 업적 해금 조건 + 중복 방지 검증 |
| `test_artifact_effects.py` | 7 | 15종 아티팩트 runtime 수정 검증 |
| `test_ascension_runtime.py` | 15 | 패널티 스케일링, 시간 조정, 보스 페이즈 |
| `test_boss_phase_pack.py` | 2 | 보스 페이즈 로딩 |
| `test_boss_phase_pack_tools.py` | 3 | 템플릿 생성 검증 |
| `test_campaign_progression.py` | 7 | 100시간 캠페인 클리어 조건 |
| `test_penalty_calculation.py` | 5 | 멀티플라이어 스태킹 |
| `test_run_game_session.py` | 6 | 게임 루프 통합 테스트 |

---

## 8. 주의사항

### 신규 시나리오 추가 시

1. `scenarios.json`에 추가할 때 `node_id`가 기존 ID와 중복되지 않도록 확인
2. `target_keyword`는 `text_log` 내에 등장해야 하며, 공백 없는 단일 단어여야 함
3. `penalty_rate`는 10~80 범위 권장 (밸런스 기준은 `GAME_SETTINGS_BOOK.md` 참조)

### 신규 아티팩트/퍼크 추가 시

- `artifact_system.py`에 아티팩트 정의 추가
- `main.py`의 `_build_runtime_modifiers()`에 runtime 적용 로직 추가
- `test_artifact_effects.py`에 대응 테스트 케이스 추가 필수

### 신규 엔딩 추가 시

- `ending_system.py`에 판정 로직 추가
- `progression_system.py`의 세이브 데이터 스키마에 엔딩 ID 등록

### `constants.py` 수정 시

- 숫자 하나가 패널티, 보상, 어센션 밸런스 전체에 영향을 줄 수 있음
- 변경 전 `ASCENSION_BALANCE_TABLE.md`와 `GAME_SETTINGS_BOOK.md` 반드시 확인

### 한국어 텍스트 처리

- `text_log`는 한국어 멀티라인 문자열 — Rich `markup=False`로 렌더링해야 `[` `]` 괄호가 깨지지 않음
- `target_keyword`는 영문 또는 한국어 단일 단어만 허용 (mutator가 이 단어를 보호함)

### PyInstaller 빌드 주의

- JSON 데이터 파일 경로는 반드시 `data_loader.py`의 `resource_path()` 함수를 통해 해석
- 직접 `open("scenarios.json")` 형태의 상대 경로 사용 금지
