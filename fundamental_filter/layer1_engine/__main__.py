"""CLI: python -m fundamental_filter.layer1_engine VNM,FPT 2021 2025 [--debug]."""

from .fundamental_engine import DEFAULT_OUTPUT_DIR, analyze_fundamental_universe
import argparse


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the in-memory Fundamental Layer for a current universe."
    )
    parser.add_argument("tickers", help="Comma-separated tickers, for example VNM,FPT")
    parser.add_argument("start_year", type=int)
    parser.add_argument("end_year", type=int)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--sleep-seconds", type=float, default=4.0)
    args = parser.parse_args()
    run = analyze_fundamental_universe(
        args.tickers,
        args.start_year,
        args.end_year,
        debug=args.debug,
        output_dir=args.output_dir,
        sleep_seconds=args.sleep_seconds,
    )
    print(run["results"].to_string(index=False))


if __name__ == "__main__":
    main()
