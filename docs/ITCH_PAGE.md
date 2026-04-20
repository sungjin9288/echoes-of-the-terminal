# Echoes of the Terminal — itch.io 페이지 설명문

> 이 파일은 itch.io 게임 페이지에 붙여넣을 설명 텍스트입니다.  
> 한국어(기본) + 영어 순서로 제공합니다.  
> itch.io > Edit Game > Description 에 HTML 또는 마크다운으로 입력하세요.

---

## 메타데이터

| 항목 | 값 |
|---|---|
| 게임 이름 | Echoes of the Terminal |
| 장르 | Roguelike, Text Adventure, Puzzle |
| 플랫폼 | Windows / macOS / Linux |
| 가격 | Pay What You Want (기본 무료) |
| 분류 태그 | roguelike, terminal, text-based, mystery, hacking, korean |
| 배너 파일 | `assets/banner_preview.html` 스크린샷 (630×500) |
| 스크린샷 | `assets/screenshots/` 5장 |

---

## 🇰🇷 한국어 설명

### 게임 소개

```
터미널에 침투하라.
수사 조서를 분석하고, 모순을 찾아라.
하지만 당신이 찾기 전에 — 시스템이 먼저 당신을 찾는다.
```

**Echoes of the Terminal**은 텍스트 로그를 분석해 논리적 결함을 찾아내는 터미널 기반 추리 roguelike입니다.

수사 조서, 기밀 문서, AI 심문 기록... 모든 로그에는 반드시 모순이 숨어 있습니다.  
`analyze [키워드]` 명령으로 결함을 찌르면 노드를 돌파합니다.  
틀리면 추적도(Trace)가 오르고, 100%에 도달하면 **SYSTEM SHUTDOWN**.

---

### 핵심 특징

🔍 **텍스트 추리** — 290개 이상의 수사 조서 시나리오. 사이버범죄·미래법정·양자강도·생체공학 테마.  
⚡ **roguelike 구조** — 런마다 달라지는 7-노드 루트. NORMAL / ELITE / REST / SHOP / MYSTERY.  
🕶️ **3종 다이버 클래스** — ANALYST(힌트형)·GHOST(생존형)·CRACKER(속공형). 각자 고유 액티브 스킬.  
🎲 **Ascension 20단계** — 클리어할수록 가혹해지는 난이도. ASC 20에선 보스 3페이즈 + 가짜 키워드.  
🏆 **118종 업적** — 런 스타일, 극한 목표, 수집 기반.  
📈 **런 히스토리·리더보드** — 개인 최고기록 + 로컬 리더보드 내보내기/가져오기(SHA-256 서명).  
📅 **데일리 챌린지** — 날짜 고정 시드. 보상 ×1.5. 연속 달성 streak 업적.  
🌐 **한국어·영어 지원**.  

---

### 플레이 방법

```
pip install -r requirements.txt
python main.py
```

또는 플랫폼별 단일 실행 파일을 다운로드해 바로 실행하세요 (설치 불필요).

---

### 명령어 목록

| 명령어 | 설명 |
|--------|------|
| `cat log` | 현재 수사 조서 출력 |
| `analyze [키워드]` | 모순 키워드 공격 |
| `ls` | 노드 정보 확인 |
| `skill` | 액티브 스킬 발동 (런당 1회) |
| `help` | 전체 명령어 보기 |

---

### 시스템 요구사항

- **Python**: 3.11 이상 (소스 실행 시)
- **단일 실행 파일**: 별도 설치 불필요
- **OS**: Windows 10+ / macOS 12+ / Ubuntu 20.04+
- **터미널**: 256색 지원 권장 (Windows Terminal, iTerm2, GNOME Terminal)

---

## 🇺🇸 English Description

### About the Game

```
Infiltrate the terminal.
Analyze the investigation logs. Find the contradiction.
But before you do — the system is already tracking you.
```

**Echoes of the Terminal** is a terminal-based mystery roguelike where you analyze text logs to find logical flaws.

Investigation reports, classified documents, AI interrogation transcripts — every log hides a contradiction.  
Use `analyze [keyword]` to strike the flaw and breach the node.  
Wrong answer? Your Trace level rises. Hit 100%? **SYSTEM SHUTDOWN**.

---

### Key Features

🔍 **Text Investigation** — 290+ hand-crafted investigation scenarios across cybercrime, future courts, quantum heists, and biomech asylum themes.  
⚡ **Roguelike Structure** — 7-node routes that change every run. NORMAL / ELITE / REST / SHOP / MYSTERY node types.  
🕶️ **3 Diver Classes** — ANALYST (hint-based) · GHOST (survival-focused) · CRACKER (speed-offense). Each with a unique active skill.  
🎲 **Ascension 20 Levels** — Each victory unlocks a harsher difficulty. ASC 20 features 3-phase boss, fake keywords, and command restrictions.  
🏆 **118 Achievements** — Run-style, extreme challenge, and collection-based achievements.  
📈 **Run History & Leaderboard** — Personal records + local leaderboard export/import with SHA-256 signature verification.  
📅 **Daily Challenge** — Date-seeded map. 1.5× reward multiplier. Streak achievements (3/7/30 days).  
🌐 **Korean & English supported**.

---

### How to Play

```
pip install -r requirements.txt
python main.py
```

Or download the pre-built executable for your platform — no installation needed.

---

### Command Reference

| Command | Description |
|---------|-------------|
| `cat log` | Display the current investigation log |
| `analyze [keyword]` | Attack the logical flaw |
| `ls` | Show current node info |
| `skill` | Activate class skill (once per run) |
| `help` | List all commands |

---

### System Requirements

- **Python**: 3.11+ (source run)
- **Standalone binary**: No installation required
- **OS**: Windows 10+ / macOS 12+ / Ubuntu 20.04+
- **Terminal**: 256-color support recommended (Windows Terminal, iTerm2, GNOME Terminal)

---

## itch.io 업로드 체크리스트

- [ ] 배너 이미지 업로드 (630×500 — `assets/banner_preview.html` 스크린샷)
- [ ] 스크린샷 5장 업로드 (`assets/screenshots/` — lobby/combat/boss/records/ending)
- [ ] Windows 바이너리 업로드 (`echoes-windows.exe` → `windows` 채널)
- [ ] macOS 바이너리 업로드 (`echoes-macos` → `mac` 채널)
- [ ] Linux 바이너리 업로드 (`echoes-linux` → `linux` 채널)
- [ ] 가격: Pay What You Want (기본 $0)
- [ ] 태그: roguelike, terminal, text-based, mystery, hacking, korean
- [ ] 장르: Puzzle, Role Playing
- [ ] 커뮤니티: Allow comments
