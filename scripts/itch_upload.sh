#!/usr/bin/env bash
# scripts/itch_upload.sh — itch.io butler 업로드 자동화
#
# 사전 요구사항:
#   1. butler CLI 설치: https://itch.io/docs/butler/installing.html
#   2. itch.io 로그인:  butler login
#   3. 환경 변수 설정:  export ITCH_USER=<your_itch_username>
#   4. GitHub Release에서 3개 플랫폼 바이너리 다운로드 후 dist-artifacts/ 에 배치:
#      dist-artifacts/
#        echoes-linux
#        echoes-windows.exe
#        echoes-macos
#
# 사용법:
#   ./scripts/itch_upload.sh [VERSION]
#   ./scripts/itch_upload.sh v1.16.0
#
# itch.io 채널 이름 규칙: linux / windows / mac
#   (itch.io 페이지: https://itch.io/dashboard/game/<ITCH_GAME_ID>/distribute)

set -euo pipefail

# ── 설정 ──────────────────────────────────────────────────────────────────────
ITCH_USER="${ITCH_USER:-sungjin9288}"
ITCH_GAME="echoes-of-the-terminal"
ARTIFACTS_DIR="${ARTIFACTS_DIR:-dist-artifacts}"
VERSION="${1:-}"

# ── 검증 ──────────────────────────────────────────────────────────────────────
if ! command -v butler &>/dev/null; then
  echo "❌  butler 를 찾을 수 없습니다."
  echo "    설치: https://itch.io/docs/butler/installing.html"
  exit 1
fi

if [[ -z "${VERSION}" ]]; then
  # constants.py 에서 버전 자동 추출
  VERSION="v$(grep -m1 'VERSION' constants.py | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')"
fi

echo "🚀  Echoes of the Terminal ${VERSION} → itch.io/${ITCH_USER}/${ITCH_GAME}"
echo "────────────────────────────────────────────────────────"

# ── 플랫폼별 업로드 ────────────────────────────────────────────────────────────
upload() {
  local channel="$1"
  local binary="$2"
  local path="${ARTIFACTS_DIR}/${binary}"

  if [[ ! -f "${path}" ]]; then
    echo "⚠️   ${path} 없음 — ${channel} 채널 건너뜁니다."
    return
  fi

  echo "📦  [${channel}]  ${path}"
  butler push "${path}" \
    "${ITCH_USER}/${ITCH_GAME}:${channel}" \
    --userversion "${VERSION#v}"
  echo "✅  ${channel} 업로드 완료"
}

upload "linux"   "echoes-linux"
upload "windows" "echoes-windows.exe"
upload "mac"     "echoes-macos"

echo "────────────────────────────────────────────────────────"
echo "🎉  모든 플랫폼 업로드 완료!"
echo "    https://itch.io/dashboard/game/${ITCH_GAME}/edit"
