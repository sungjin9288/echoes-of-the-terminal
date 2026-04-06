"""Generate/sync ASC20 boss phase pack template JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from boss_phase_pack_tools import build_boss_phase_pack_template
from data_loader import load_boss_phase_pack, load_scenarios


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="ASC20 보스 페이즈 데이터팩 템플릿을 생성/동기화합니다.",
    )
    parser.add_argument(
        "--scenarios",
        default="scenarios.json",
        help="시나리오 파일 경로 (default: scenarios.json)",
    )
    parser.add_argument(
        "--input-pack",
        default="boss_phase_pack.json",
        help="기존 보스 페이즈 팩 경로 (default: boss_phase_pack.json)",
    )
    parser.add_argument(
        "--output",
        default="boss_phase_pack.template.json",
        help="출력 파일 경로 (default: boss_phase_pack.template.json)",
    )
    parser.add_argument(
        "--phase-count",
        type=int,
        default=3,
        help="최소 페이즈 수 (default: 3)",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    scenarios = load_scenarios(args.scenarios)

    input_path = Path(args.input_pack)
    existing_overrides: dict[int, list[dict[str, str]]] = {}
    if input_path.exists():
        existing_overrides = load_boss_phase_pack(str(input_path))

    template = build_boss_phase_pack_template(
        scenarios=scenarios,
        phase_count=args.phase_count,
        existing_overrides=existing_overrides,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(template, f, ensure_ascii=False, indent=2)

    boss_count = len(template.get("ascension_20_boss_overrides", {}))
    print(
        f"[OK] boss phase template generated: {output_path} "
        f"(bosses={boss_count}, phase_count>={max(1, int(args.phase_count))})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
