# Changelog

모든 주요 변경 사항은 이 파일에 기록됩니다.  
형식은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/)를 따릅니다.

---

## [1.0.1] — 2026-04-17

### 추가 (Added)
- **튜토리얼/온보딩**: 첫 실행 시 7단계 안내 패널 자동 진입. 로비 [6] 메뉴에서 재열람 가능.
- **누적 통계 대시보드**: 기록 화면에 CUMULATIVE STATS 패널 추가 (총 런·승률·평균 trace·최고 어센션·최다 엔딩).
- 세이브 스키마 v2: `tutorial_completed` 필드 추가, v1→v2 자동 마이그레이션 (기존 유저는 튜토리얼 스킵).

### 변경 (Changed)
- `progression_system.py` 에러 경고를 `warnings.warn` → Rich 노란색 `[SAVE]` 패널로 개선.

### 테스트
- 370 → 372 케이스 (튜토리얼 마이그레이션 케이스 추가).

---

## [1.0.0] — 2026-04-17

### 추가 (Added)
- **280개 시나리오** (Pack 01–22) 및 **22개 보스 패키지**
- **115종 업적** 시스템 (탐험·전투·퍼크·클래스·엔딩·어센션 카테고리)
- **28종 아티팩트** 시스템 (런 중 효과 즉시 적용)
- **13종 엔딩** 판정 (승리·사망·캠페인·어센션 등 조건 다양화)
- **18종 MYSTERY 노드** 이벤트 (개입/무시 선택 + 보상/페널티)
- **3종 다이버 클래스** (ANALYST / GHOST / CRACKER) — 패시브·액티브 스킬 포함
- **13종 퍼크** 영구 강화 시스템
- **일일 도전(Daily Challenge)** — 고정 시드 하루 1회, 리더보드 기록
- **어센션 0–20** 난이도 스케일링 (보스 다중 페이즈, 경로 변이, 명령어 제한)
- **100시간 캠페인** 클리어 조건 (포인트·승리·클래스별 달성)
- **세이브 스키마 버저닝** (`schema_version` + `_migrate_save()` 자동 마이그레이션)
- **VERSION 상수** 중앙화 (`constants.py` → 로고 하단 표시)
- `pyproject.toml` PEP 621 메타데이터 및 도구 설정
- CI 멀티플랫폼 매트릭스 (Ubuntu / Windows / macOS × Python 3.11 / 3.12)
- 릴리즈 워크플로 (`release.yml`): 태그 push 시 3플랫폼 PyInstaller 바이너리 빌드

### 변경 (Changed)
- `main.py` 2062줄 → **32줄** (진입점 + re-export 전용 박막 모듈)
  - 런 루프 엔진 → `run_loops.py` (883줄)
  - 로비/상점/클래스 선택 → `lobby.py` (361줄)
  - 전투/미스터리/상점 노드 실행 → `combat_orchestration.py` (490줄)
- `achievement_system.py` 1051줄 → **430줄** (평가 로직만 유지)
  - 115종 업적 데이터 → `achievement_data.py` (622줄) 분리
- `apply_ascension_reward_multiplier` → `progression_system.py` 공개 API로 이동
- `.gitignore` 보강 (`.venv/`, `.DS_Store`, `.pytest_cache/`, `*.egg-info/` 등)
- 설계 문서 (`ASCENSION_BALANCE_TABLE.md` 등) → `docs/` 하위로 이동

### 수정 (Fixed)
- 테스트 monkeypatch 대상을 `main.*` → `run_loops.*` 로 정정 (모듈 분리 후 경로 드리프트)

### 테스트
- 266 → **364 케이스** (신규 4개 파일):
  - `test_combat_commands.py` — 커맨드 핸들러 정답/오답/사망 경로
  - `test_data_loader.py` — JSON 로딩·검증·PyInstaller 경로 처리
  - `test_diver_class.py` — 3종 클래스 패시브·액티브·스트릭 효과
  - `test_mutator_system.py` — 글리치 마스킹·keyword 보호·한국어 처리
  - `test_campaign_progression.py` — 세이브 마이그레이션 케이스 4개 추가

---

## [0.9.4] — 이전 세션 (요약)

### 추가
- 어센션 20 보스 3페이즈 + 가짜 키워드 + 명령어 제한
- `boss_phase_pack.json` 전용 오버라이드 팩
- MYSTERY 노드 18종 전체 구현
- 일일 도전 시스템 (streak, best_score, history)
- 3종 다이버 클래스 완전 구현

---

*이전 버전(v0.1–v0.9.3)은 비공개 개발 단계로 별도 기록하지 않습니다.*
