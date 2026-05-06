# Changelog

모든 주요 변경 사항은 이 파일에 기록됩니다.  
형식은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/)를 따릅니다.

---

## [2.0.3] — 2026-04-27

### 추가 (Added)
- **fly.io 실제 배포 완료**: `https://echoes-terminal.fly.dev` 라이브. Tokyo(nrt) 리전, 256MB 공유 VM, auto-stop/start.
- **GitHub Actions `FLY_API_TOKEN` 시크릿 등록**: 태그 푸시 시 `deploy-fly.yml` 자동 배포 활성화.
- **동적 CI 배지** (`README.md`): 정적 "Tests: 779 passing" 배지 대신 GitHub Actions 실시간 상태 배지 추가.
- 버전 배지 v2.0.1 → v2.0.3, `pyproject.toml` / `constants.py` 버전 동기화.

---

## [2.0.2] — 2026-04-27

### 추가 (Added)
- **fly.io 배포 설정** (`fly.toml`): Tokyo(nrt) 리전, 256MB 공유 VM, auto-stop/start (무료 티어 최적화). Play in Browser URL: `https://echoes-terminal.fly.dev`
- **GitHub Actions 배포 워크플로우** (`.github/workflows/deploy-fly.yml`): 버전 태그 푸시 또는 수동 트리거 시 fly.io 자동 배포. `FLY_API_TOKEN` 시크릿 필요.
- `README.md`: "Play in Browser" 배지 + 플레이 방법 3가지 (브라우저/터미널/로컬 웹서버) 안내.

### 변경 (Changed)
- `pyproject.toml`: 버전 `2.0.0` → `2.0.1`, 의존성에 FastAPI / uvicorn / jinja2 / python-multipart 추가 (웹 UI 출시 이후 누락 반영).
- `.github/workflows/tests.yml` / `release.yml`: `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: "true"` 환경 변수 추가 (Node.js 20 → 24 전환 대응, GitHub Actions 2026-06-02 강제 적용 예정).

---

## [2.0.1] — 2026-04-24

### 추가 (Added)
- **GIF 트레일러** (`assets/trailer.gif`): 20초 루프 애니메이션 — 로비(CRACKER 선택) → 부팅 → 전투(수사 조서 → `cat log` → `analyze 무역` → 정답 성공 → NODE CLEARED 배지). 800×500, 82프레임, 196 KB.
- **트레일러 생성 스크립트** (`scripts/make_trailer_gif.py`): Playwright headless + Pillow — CSS 애니메이션 타임라인을 프레임별 시킹 후 PNG 캡처 → GIF 합성.
- `README.md`: 상단에 트레일러 GIF 삽입, 테스트 배지 749 → 779 갱신.
- **데모 HTML** (`assets/demo_preview.html`): 트레일러 소스. 800×500 셀프-컨테인드 CSS 애니메이션 (외부 의존 없음).

---

## [2.0.0] — 2026-04-21

### 추가 (Added)
- **FastAPI + htmx 웹 UI** (`web/` 패키지 신규):
  - `web/adapters.py` — `ConsoleBridge` (thread-local 프록시), `WebGameSession` (큐 기반 I/O), `install_patches()` (`builtins.input` + `PromptBase.ask` 패치). 게임 엔진 코드 수정 없음.
  - `web/session.py` — `SessionStore` (인메모리, TTL 1시간), 세션 생성·조회·만료 정리.
  - `web/app.py` — FastAPI 앱. 로비 페이지(`GET /`), 게임 페이지(`GET /game`), API 엔드포인트 8종. lifespan 태스크로 5분마다 세션 만료 정리.
  - `web/templates/base.html` — 공통 레이아웃 (htmx CDN 포함).
  - `web/templates/lobby.html` — 클래스 선택·어센션 슬라이더·게임 시작 버튼. htmx form 전송.
  - `web/templates/game.html` — 터미널 출력 영역 + 커맨드 입력 + 300ms htmx 폴링. 게임 종료 감지 및 입력 비활성화.
  - `web/static/style.css` — Design Token CSS 변수 (`assets/tokens.json` 기반). 터미널 스타일 UI.
- **Dockerfile** — `python:3.12-slim` 기반 단일 워커 uvicorn 컨테이너.
- **의존성 추가** (`requirements.txt` / `requirements-dev.txt`): `fastapi`, `uvicorn[standard]`, `jinja2`, `python-multipart`, `httpx`(dev).

### 아키텍처
```
[브라우저 htmx]  ──HTTP──>  [FastAPI web/app.py]
                                  │
                           [WebGameSession thread]
                                  │
                           [기존 run_loops.py 등 — 수정 없음]
                           (ConsoleBridge → 세션 Console)
                           (builtins.input → 세션 Queue)
```

### 실행
```bash
# 터미널 버전 (기존)
python main.py

# 웹 버전 (신규)
uvicorn web.app:app --reload
# → http://localhost:8000
```

### 테스트
- `tests/test_web_session.py` 신규 (30케이스): 로비·게임페이지·폴링·커맨드·세션 스토어·WebGameSession 단위.
- 749 → **779 케이스**.

### 변경 (Changed)
- `pyproject.toml` / `constants.py`: 버전 `1.16.0` → `2.0.0`.
- `README.md`: 버전 배지 v2.0.0 갱신.

---

## [1.16.0] — 2026-04-20

### 추가 (Added)
- **itch.io 배포 인프라**:
  - `scripts/itch_upload.sh` — butler CLI 3-플랫폼 업로드 자동화 스크립트 (linux/windows/mac 채널). `ITCH_USER` 환경 변수 + 버전 자동 추출.
  - `docs/ITCH_PAGE.md` — itch.io 게임 페이지 설명문 (한국어·영어). 게임 소개·특징·명령어·시스템 요구사항·업로드 체크리스트 포함.
- **PyInstaller 빌드 개선** (`echoes.spec`):
  - `datas`에 `locale/`·`packs/` 디렉터리 추가 — i18n 언어 파일과 DLC 팩 JSON을 단일 실행 파일에 번들링.
- **GitHub Actions 수정** (`.github/workflows/release.yml`):
  - `pyinstaller_name` → `exe_name`으로 명칭 정리. spec 출력파일 `EchoesOfTheTerminal`과 일치.
  - Rename 스텝 추가: 플랫폼별로 `echoes-linux` / `echoes-windows.exe` / `echoes-macos`로 재명명.
  - `update_existing_release: true` 추가 — 수동 생성 릴리즈에 바이너리 자동 첨부 지원.

### 변경 (Changed)
- `pyproject.toml` / `constants.py`: 버전 `1.15.0` → `1.16.0`.

### 배포 방법
```bash
# 1. GitHub Actions가 자동으로 3-플랫폼 바이너리 빌드 (v* 태그 push 시)
# 2. dist-artifacts/ 에 바이너리 배치 후:
ITCH_USER=<your_username> ./scripts/itch_upload.sh v1.16.0
```

---

## [1.15.0] — 2026-04-20

### 추가 (Added)
- **비주얼 아이덴티티 에셋** (`assets/` 디렉터리):
  - `assets/logo.svg` — 게임 로고타입 SVG (560×200). Green neon TERMINAL 타이틀 + RGB glitch pseudo-element + 블링킹 커서 + scanline 오버레이.
  - `assets/logo_final.html` — 로고 애니메이션 프로토타입 (Preview MCP 렌더링 기준).
  - `assets/banner_preview.html` — itch.io 배너 HTML (630×500). 그리드 배경·vignette·코너 데코·feature 태그·`analyze [keyword]` 프롬프트.
  - `assets/tokens.json` — 디자인 토큰 v1.15. 색상 12종 / 타이포그래피 / 간격 / 효과(glow·scanline) / border_radius.
  - `assets/screenshots/` — 게임 스크린샷 보관 디렉터리.
- **README.md 리뉴얼**:
  - 상단 로고 SVG 임베드 (`<img src="assets/logo.svg">`).
  - 배지 5종: Python 버전 / MIT License / Tests passing / Coverage / Version.
  - 스크린샷 갤러리 섹션 (2×2 그리드).
  - 비주얼 에셋 파일 목록 섹션.
  - 수치 갱신: 시나리오 290개·업적 118종·테스트 749+케이스.

### 변경 (Changed)
- `pyproject.toml` / `constants.py`: 버전 `1.14.0` → `1.15.0`.

### 개발 도구
- `assets/logo_preview.html` — 초기 3개 변형(Classic Terminal / Glitch / Bracket Frame) 비교용 프로토타입.
- `.claude/launch.json` — Preview MCP용 Python HTTP 서버 설정 (port 7788, `assets/` serving).

---

## [1.14.0] — 2026-04-20

### 추가 (Added)
- **리더보드 내보내기/가져오기** (`progression_system.export_leaderboard` / `import_leaderboard`):
  - `export_leaderboard(save_data, path)` — SHA-256 서명된 JSON 파일로 리더보드 저장.
  - `import_leaderboard(path, save_data)` — 서명 검증 후 기존 리더보드와 병합, `LEADERBOARD_MAX` 상한 유지.
  - 병합 로직: 기존 + 임포트 항목 합산 → 점수 내림차순 → (score, date, class_key) 중복 제거 → Top 10 → 순위 재계산.
  - `LeaderboardImportError` 예외: 파일 없음 / JSON 파싱 실패 / 포맷 불일치 / 서명 불일치 시 발생.
- **로비 메뉴 `[a]` / `[b]`**: 리더보드 내보내기 / 가져오기 메뉴 항목 추가.
  - 내보내기(`a`): 파일 경로 입력(기본값 `leaderboard_export.json`) → 저장.
  - 가져오기(`b`): 파일 경로 입력 → 검증 & 병합 → 세이브 즉시 반영.
- **i18n 키 추가** (`locale/ko.json`, `locale/en.json`): `lb.export.*` / `lb.import.*` / `lobby.menu.lb_export` / `lobby.menu.lb_import`.

### 테스트
- `tests/test_leaderboard_io.py` 신규 (31케이스):
  - `TestComputeSignature` (5): 결정성·변조 탐지·빈 보드·순서 민감·hex 형식.
  - `TestExportLeaderboard` (8): 파일 생성·포맷·내용·서명·빈 보드·디렉터리 자동 생성·OSError.
  - `TestImportLeaderboard` (13): 정상 경로·항목 반영·서명 불일치·포맷 오류·파일 없음·JSON 오류·리스트 아님·병합·정렬·중복 제거·상한·순위 재계산·반환 통계.
  - `TestRoundTrip` (4): 항목 보존·변조 탐지·점수 정렬·자기 임포트 중복 없음.
- 718 → **749 케이스**.

---

## [1.13.0] — 2026-04-20

### 추가 (Added)
- **일일 도전 결과 히스토리 바 차트** (`ui_renderer.render_daily_history`): 기존 텍스트 테이블에서 점수 비례 바 차트 포함 테이블로 강화.
  - 최신 14개 항목을 최신순(최신→과거)으로 표시.
  - 각 행: 날짜 · WIN/FAIL · `█░` 점수 바(승리=green, 패배=red) · 점수 · 등급(S/A/B/C/D) · 오답 수.
  - 최고 점수 기준 상대 비율로 바 길이 결정.
- **기록 화면 데일리 히스토리 자동 표시**: `render_records_screen`이 `daily_state["history"]`가 있을 때 바 차트 테이블을 DAILY CHALLENGE 요약 패널 직후에 출력.
- **데일리 streak 업적 3종** (`achievement_data.py`):
  - `daily_streak_3` — "3일 연속": 데일리 챌린지를 3일 연속으로 완료.
  - `daily_streak_7` — "일주일의 집착": 7일 연속 완료.
  - `daily_streak_30` — "한 달의 습관": 30일 연속 완료.
- **업적 총계 115 → 118종** (`achievement_system.py`): streak 평가 블록 추가.

### 변경 (Changed)
- `ui_renderer.py` 상단에 `from daily_challenge import get_performance_grade as _get_daily_grade` 추가 — 바 차트 등급 표시에 사용.

### 테스트
- `tests/test_daily_history.py` 신규 (36케이스):
  - `TestRenderDailyHistoryBarChart` (9): 빈 히스토리·테이블 렌더·비례 바·색상·등급·오답·14개 상한·제목·최신순.
  - `TestDailyStreakAchievements` (10): streak 2/3/7/30/50·중복 방지·필드 누락 방어·메타데이터.
  - `TestRecordsScreenDailyHistory` (3): 히스토리 있을 때 호출·없을 때 미호출·올바른 데이터 전달.
  - `TestNormalizeHistoryRingBuffer` (7): 빈 리스트·비정상 타입·30개 상한·최신 30개 유지·잘못된 항목 스킵·음수 점수 클램프·필드 존재.
  - `TestRecordDailyResult` (7): 첫 플레이·연속 증가·갭 리셋·베스트 점수·히스토리 추가·30개 상한·총 플레이.
- `tests/test_achievement_system.py` — 업적 수 기대값 115 → 118 갱신 (3케이스 수정).
- 682 → **718 케이스**.

---

## [1.12.0] — 2026-04-20

### 추가 (Added)
- **Pack 26 — QUANTUM HEIST** (`packs/pack_26_quantum_heist.json`): 2077년 양자 기술 범죄 테마 5시나리오.
  - node_id 1014~1018 / 테마 `QUANTUM_HEIST_A~E`
  - Easy×2 · Hard×2 · NIGHTMARE×1
  - 키워드: 접근(이중 볼트 동시 인증 불가) · 서명(서명 선행 타임스탬프 역전) · 측정(양자 관측 즉시 경보 발령 — 검찰 무탐지 주장 모순) · 복사(no-cloning theorem 위반) · 양자(양자 얽힘으로 FTL 정보 전송 불가)
- **Pack 27 — BIOMECH ASYLUM** (`packs/pack_27_biomech_asylum.json`): 2077년 생체공학 의료·보안 범죄 테마 5시나리오.
  - node_id 1019~1023 / 테마 `BIOMECH_ASYLUM_A~E`
  - Easy×2 · Hard×2 · NIGHTMARE×1
  - 키워드: 배터리(82일 만에 99% 방전 — 90일 명세 위반) · 수술(동의서 서명일이 수술·퇴원 이틀 후) · 센서(3배 과다계상 펌웨어 결함 이미 패치 적용 후 사건 발생) · 패치(ZeroSkin 취약점 패치 완료 후 침입 시도 + 인증 실패 로그만 존재) · 기억(BCI가 기억 이식 기능 미지원 + 파일 메타데이터에 47일 후 출시 펌웨어 버전)

### 테스트
- `tests/test_new_packs_v12.py` 신규 (26케이스): Pack 26/27 로드·메타데이터·node_id 범위·필드 검증·난이도 분포·키워드 in text_log·팩 간 node_id 충돌 감지·패널티-난이도 매핑 검증.
- 656 → **682 케이스**.

---

## [1.11.0] — 2026-04-19

### 추가 (Added)
- **런 타임라인 (Run Timeline)**: 런 중 발생한 노드별 이벤트를 8가지 유형으로 기록하여 런 완료 후 기록 화면에 트리 형식으로 표시.
  - 이벤트 유형: `correct` ✓ / `wrong` ✗ / `timeout` ⏱ / `artifact` ◆ / `mystery_engage` ? / `mystery_skip` — / `rest` ♥ / `shop` $
  - 각 이벤트는 `{event, node, detail}` 구조로 저장, 세이브 데이터에 영속.
  - 기록 화면 런 히스토리 하단에 최근 런 타임라인 자동 표시.
- **`render_run_timeline(entry)`** — ui_renderer.py에 신규 함수. Rich Tree로 이벤트 아이콘·노드번호·상세정보 렌더.

### 변경 (Changed)
- **세이브 스키마 v2 → v3**: 기존 `run_history` 엔트리에 `timeline: []` 필드 자동 추가 (마이그레이션).
  - `_migrate_v2_to_v3()` 추가, `_CURRENT_SCHEMA_VERSION = 3`.
  - `_make_run_record` / `add_run_to_history`에 `timeline` 파라미터 추가.
- `run_state` 초기화에 `"timeline": []` 추가 — 런 전체에 걸쳐 이벤트를 축적.
- `_build_run_stats()`에 `timeline` 필드 포함, lobby.py의 `add_run_to_history` 호출에 전달.
- `run_state["current_node"]` 필드 추가 — 노드 루프 진입 시 갱신, 하위 핸들러(wrong/timeout/artifact 이벤트)에서 참조.

### 테스트
- `tests/test_run_timeline.py` 신규 (19케이스): `_make_run_record` timeline 필드·`add_run_to_history` 영속·v2→v3 마이그레이션·UI 렌더링.
- `tests/test_campaign_progression.py` — 스키마 버전 기대값 3으로 갱신 (3케이스 수정).
- `tests/test_save_slots.py` — `schema_version == 3` 갱신 (1케이스 수정).
- 637 → **656 케이스**.

---

## [1.10.0] — 2026-04-19

### 추가 (Added)
- **업적 진행률 표시 (Achievement Progress)**: 미해금 업적 중 누적 카운터 계열 45종에 대해 `current/target` + 유니코드 진행바(`[▓▓▓▓▓▓▓░░░]`)를 기록 화면(`[5]`)에 표시.
  - 추적 대상: `runs_N`·`victories_N`·`campaign_points_N`·클래스별 승리(`analyst_master`·`triple_master` 등)·`ascension_unlocked_N`·`endings_N`·`data_fragments_N`·`perk_hoarder_N`·MYSTERY 누적.
  - 진행률 비율 내림차순 상위 5개를 "진행 중" 섹션에 노출 — 해금 임박 업적을 한눈에 파악.
  - 이벤트 트리거형(`first_shutdown`·`perfect_infiltration` 등 70종)은 진행률 없이 기존 unlocked/locked 표기 유지.

### 신규 모듈
- `achievement_progress.py` (약 200줄): `compute_achievement_progress`, `get_locked_progress_entries`, `format_progress_bar`.
- `PROGRESS_SPECS` 명세 테이블로 업적 ID ↔ 세이브 필드 매핑 중앙화.

### 수정 (Changed)
- `ui_renderer.render_records_screen` — `achievement_progress: list | None` 파라미터 추가. ACHIEVEMENTS 패널 하단에 진행률 블록 렌더.
- `lobby.py` 기록 메뉴 — `get_locked_progress_entries(save_data, top_n=5)` 호출 후 UI로 전달.

### 테스트
- `tests/test_achievement_progress.py` 신규 (31케이스): 진행바 포맷·진행률 계산·손상된 save_data 방어·정렬·UI 렌더 통합.
- 606 → **637 케이스**.

---

## [1.9.0] — 2026-04-19

### 추가 (Added)
- **Pack 24 — DYSTOPIAN COURT** (`packs/pack_24_dystopian_court.json`): 2076년 AI 법정 테마 5시나리오.
  - node_id 1004~1008 / 테마 `DYSTOPIAN_COURT_A~E`
  - Easy×2 · Hard×2 · NIGHTMARE×1
  - 주요 결함: AI 판사 타임스탬프 모순, 홀로그램 서버 점검 중 목격, 블록체인 해시 변조 불가, 신경 인터페이스 비호환, 양자 백업 미인증
- **Pack 25 — NEON UNDERGROUND** (`packs/pack_25_neon_underground.json`): 사이버펑크 지하경제 테마 5시나리오.
  - node_id 1009~1013 / 테마 `NEON_UNDERGROUND_A~E`
  - Easy×2 · Hard×2 · NIGHTMARE×1
  - 주요 결함: 데이터 수신 전 전송 완료, 리콜 카메라 영상 신뢰 불가, 폐기된 암호화 프로토콜, 위성 차단 구역 업링크, 존재 불가 블록체인 블록 번호
- 총 시나리오 수: 280 + 3(Pack 23) + 5(Pack 24) + 5(Pack 25) = **293개**

### 테스트
- `tests/test_new_packs.py` 신규 (23케이스): 팩 로드·메타데이터·node_id 범위·필드 검증·난이도 분포·팩 간 충돌 감지.
- 583 → **606 케이스**.

---

## [1.8.0] — 2026-04-19

### 추가 (Added)
- **다이버 프로필 카드 (Diver Profile Card)**: 플레이어 전체 진행도를 집약한 프로필 패널. 기록 화면(`[5]`) 최상단에 표시.
  - **칭호 시스템**: 승률·어센션 기반 자동 부여 (데이터 다이버 / 성장 / 숙련 / 전설 / 도전자 / 전문가 / 마스터 7등급)
  - **주력 클래스**: 가장 많이 플레이한 클래스 자동 도출
  - 총 런 수·승률·평균 추적도·최고 어센션·최다 엔딩·리더보드 최고 점수·해금 업적 수·캠페인 클리어 여부 한눈에 표시
- `progression_system.py`: `get_diver_profile()` 공개 API. `_compute_diver_title()` / `_compute_signature_class()` 내부 헬퍼.
- `ui_renderer.py`: `render_diver_profile(profile)` — 황금색 테두리 Rich Panel. `render_records_screen()`에 `diver_profile=` 파라미터 추가.
- `lobby.py`: 기록 화면 `[5]` 진입 시 프로필 자동 계산·표시.

### 테스트
- `tests/test_diver_profile.py` 신규 (25케이스): 칭호 계산·주력 클래스·get_diver_profile 전체 필드·UI render.
- 558 → **583 케이스**.

---

## [1.7.0] — 2026-04-18

### 추가 (Added)
- **로컬 리더보드 (Local Score Leaderboard)**: 런 종료마다 점수를 계산해 전체 Top-10 리더보드를 유지.
  - 점수 공식: `보상 + (100 - 추적도) × 2 + 정답 × 10 + 어센션 × 30 + 승리 보너스 200`
  - 순위권 진입 시 정산 화면에 `🏆 LOCAL LEADERBOARD #N 진입!` 알림 표시.
- `progression_system.py`: `calculate_run_score()` / `update_leaderboard()` / `get_leaderboard()` 공개 API. `LEADERBOARD_MAX = 10` 상수. `DEFAULT_SAVE_DATA`에 `leaderboard` 필드 추가, 손상된 값은 빈 리스트로 자동 교정.
- `ui_renderer.py`: `render_leaderboard(entries, new_rank=None)` — 점수 내림차순 Rich 테이블, 신규 순위 항목 ★ 강조. `render_records_screen()`에 `leaderboard=` 파라미터 추가.
- `lobby.py`: 런 종료 시 `update_leaderboard()` 자동 호출. 순위권 진입 시 알림 패널 표시. 기록 화면(`[5]`)에 리더보드 테이블 표시.

### 테스트
- `tests/test_leaderboard.py` 신규 (23케이스): 점수 계산 공식·삽입·Top-10 제한·순위 재계산·세이브 정규화·UI render.
- 535 → **558 케이스**.

---

## [1.6.0] — 2026-04-18

### 추가 (Added)
- **개인 최고 기록 (Personal Records)**: (클래스, 어센션) 조합별 런 수·승리 수·승률·최저 추적도·최고 보상·최다 정답 영구 저장.
- `progression_system.py`: `update_personal_records()` / `get_personal_records()` 공개 API. `DEFAULT_SAVE_DATA`에 `personal_records` 필드 추가, 손상된 값은 빈 딕셔너리로 자동 교정.
- `ui_renderer.py`: `render_personal_records(records)` — (클래스, 어센션) 오름차순 Rich 테이블. `render_records_screen()`에 `personal_records=` 파라미터 추가.
- `lobby.py`: 런 종료 시 `update_personal_records()` 자동 호출. 기록 화면(`[5]`)에 개인 기록 테이블 표시.

### 테스트
- `tests/test_personal_records.py` 신규 (19케이스): update·get·승리/패배 분기·최고 기록 경신·세이브 정규화·UI render.
- `tests/test_route_map.py` 신규 (34케이스): NodeType 열거형·build_route_choices·레이블/설명/스타일 헬퍼 (파라미터화).
- 482 → **535 케이스**.

---

## [1.5.0] — 2026-04-18

### 추가 (Added)
- **런 기록 히스토리**: 런 종료마다 날짜·클래스·어센션·결과·최종 추적도·보상·정답 수·엔딩 ID를 자동 저장. 최신 20건 유지 (초과 시 오래된 항목 삭제).
- `progression_system.py`: `add_run_to_history()` / `get_run_history()` 공개 API. `RUN_HISTORY_MAX = 20` 상수. `DEFAULT_SAVE_DATA`에 `run_history` 필드 추가, 손상된 값은 빈 리스트로 자동 교정.
- `ui_renderer.py`: `render_run_history(history)` — 최신순 Rich 테이블 (VICTORY 녹색 / SHUTDOWN 빨간색 강조). `render_records_screen()`에 `run_history=` 파라미터 추가.
- `lobby.py`: 런 종료 시 `add_run_to_history()` 자동 호출. 기록 화면(`[5]`)에 히스토리 테이블 표시.

### 테스트
- `tests/test_run_history.py` 신규 (20케이스): add·get·최대 제한·역순·세이브 정규화·UI render.
- 462 → **482 케이스**.

---

## [1.4.0] — 2026-04-18

### 추가 (Added)
- **다국어 지원 기반 구조 (i18n)**: 한국어(`ko`) / 영어(`en`) 2개 언어. 로비 메뉴 `[9] 언어 변경`에서 즉시 전환, 슬롯에 자동 저장.
- `i18n.py`: `t(key, **kwargs)` 번역 함수, `set_language()` / `get_language()` / `reload()` 공개 API. 알 수 없는 키는 폴백 → 한국어 재시도 → 키 자체 반환. `str.format_map` 보간 지원.
- `locale/ko.json` / `locale/en.json`: 74개 UI 키 (로비·정산·슬롯·상점·클래스·어센션·테마·언어 선택 문자열).
- `ui_renderer.py`: `render_lobby()` / `render_settlement_log()` / `render_class_selection()` / `render_shop()` / `render_save_slot_selection()` 번역키 적용.
- `lobby.py`: `select_language()` UI 함수, `[9] 언어 변경` 메뉴, 세이브 로드 시 저장된 언어 자동 복원.
- `progression_system.py`: `DEFAULT_SAVE_DATA`에 `language` 필드 추가, 잘못된 값은 `"ko"` 자동 교정.

### 테스트
- `tests/test_i18n.py` 신규 (25케이스): 언어 전환·폴백·보간·파일 검증·세이브 정규화·UI 연동.
- 437 → **462 케이스**.

---

## [1.3.0] — 2026-04-18

### 추가 (Added)
- **시나리오 팩 DLC 구조**: `packs/` 디렉터리의 `pack_*.json` 파일을 자동 발견·병합.
- `pack_loader.py`: `PackMetadata` / `LoadedPack` 불변 데이터클래스, `load_scenario_pack()` / `discover_packs()` / `load_all_packs()` 공개 API. node_id 중복 감지 포함.
- `data_loader.py`: `load_scenarios_with_packs()` — 기본 시나리오 + 팩 병합 단일 진입점.
- `packs/pack_23_cyber_noir.json`: 팩 23 데모 (사이버 느와르, 3개 시나리오 / node_id 1001~1003).
- `run_loops.py`: 게임 세션 및 데일리 챌린지 진입 시 팩 자동 로드.

### 테스트
- `tests/test_pack_loader.py` 신규 (27케이스): 구조·검증·탐색·병합·중복 감지·smoke 테스트.
- 410 → **437 케이스**.

---

## [1.2.0] — 2026-04-18

### 추가 (Added)
- **색각 이상 대응 테마 시스템 (3종)**: `default` / `colorblind` (청색/황색/주황) / `high_contrast` (굵기·반전만 사용).
- `theme_system.py`: `THEMES`, `THEME_LABEL_MAP`, `VALID_THEMES`, `get_theme_styles` 공개 API.
- `ui_renderer.py`: `_THEME` 모듈 전역 상태, `set_theme()`, `get_current_theme_name()`, `_difficulty_style()`, `_result_style()` — trace·난이도·결과 강조색이 선택된 테마를 따름.
- 로비 메뉴 `[8] 테마 변경` — 게임 중 테마 전환 + 슬롯 자동 저장.
- 세이브 스키마에 `theme` 필드 추가 (없거나 잘못된 값이면 `"default"` 자동 보완).

### 테스트
- `tests/test_theme_system.py` 신규 (17케이스): 테마 구조·스타일 품질·세이브 정규화·UI 연동 검증.
- 393 → **410 케이스**.

---

## [1.1.0] — 2026-04-18

### 추가 (Added)
- **다중 세이브 슬롯 (3슬롯)**: 게임 시작 시 슬롯 선택 화면 표시. 슬롯별 데이터 조각·캠페인 승리 횟수·마지막 저장일 요약.
- `progression_system.py`: `get_slot_info`, `get_all_slots_info`, `load_save_slot`, `save_game_slot`, `migrate_legacy_save` 공개 API.
- 레거시 `save_data.json` 자동 마이그레이션 (슬롯 1으로 1회 복사).
- 로비 메뉴 `[7] 슬롯 변경` — 게임 중 슬롯 전환 가능.
- `ui_renderer.py`: `render_save_slot_selection` 슬롯 선택 테이블.

### 테스트
- `tests/test_save_slots.py` 신규 (16케이스): 경로 클램핑·슬롯 독립성·마이그레이션·왕복 저장 검증.
- `tests/test_e2e_run.py` 업데이트: 새 슬롯 mock 타깃 반영.
- 377 → **393 케이스**.

---

## [1.0.2] — 2026-04-17

### 추가 (Added)
- **E2E 스모크 테스트**: `tests/test_e2e_run.py` (5케이스) — 로비 정산 파이프라인 전체 검증 (승리·패배·lobby 1턴·퍼크 불변·통계 누적).
- **pytest-cov** 도입: `requirements-dev.txt` + CI 70% 커버리지 게이트.

### 변경 (Changed)
- 설계 문서 `GAME_SETTINGS_BOOK.md` → `docs/GAME_SETTINGS_BOOK.md` 이동.
- `dist/sw.js`, `dist/workbox-7b98b334.js` 삭제 (타 프로젝트 오염 파일).
- `CLAUDE.md` 내 문서 참조 경로 `docs/` 기준 갱신.

### 테스트
- 372 → **377 케이스**, 커버리지 **80.9%** (게이트: 70%).

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
