#!/usr/bin/env python3
"""
Promo Finder CLI.

    python run.py --input data                      # full run, default model
    python run.py --input data --no-llm             # code only, no network
    python run.py --input data --episodes 1,24,31   # develop on a few
    python run.py --input data --model qwen/qwen3.8-27b
    python run.py --input data --provider gemini --model gemini-2.5-flash-lite
"""
import sys
import argparse

from promo.pipeline import run


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Find promo clips in microdrama screenplays.")
    ap.add_argument("--input", default="data", help="folder of screenplay .txt files")
    ap.add_argument("--out", default="outputs", help="output folder")
    ap.add_argument("--provider", default=None, help="groq | openai | gemini | anthropic | openrouter")
    ap.add_argument("--model", default=None, help="model id for that provider")
    ap.add_argument("--no-llm", action="store_true", help="code-only scoring, no API calls")
    ap.add_argument("--no-cache", action="store_true", help="ignore the response cache")
    ap.add_argument("--no-gate", action="store_true", help="skip the cold-viewer gate")
    ap.add_argument("--no-flagship", action="store_true", help="skip the cross-episode promo")
    ap.add_argument("--episodes", default=None, help="comma-separated episode numbers")
    ap.add_argument("--max-calls", type=int, default=400, help="hard cap on API calls")
    ap.add_argument("--top-k", type=int, default=4, help="candidate windows per episode")
    ap.add_argument("--per-episode", type=int, default=1, help="promos kept per episode")
    args = ap.parse_args(argv)

    episodes = None
    if args.episodes:
        episodes = [int(x) for x in args.episodes.replace(" ", "").split(",") if x]

    try:
        run(
            args.input,
            args.out,
            provider=args.provider,
            model=args.model,
            use_llm=not args.no_llm,
            use_cache=not args.no_cache,
            episodes=episodes,
            max_calls=args.max_calls,
            top_k=args.top_k,
            promos_per_episode=args.per_episode,
            run_gate=not args.no_gate,
            run_flagship=not args.no_flagship,
        )
    except RuntimeError as exc:
        print(f"\nSTOPPED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
