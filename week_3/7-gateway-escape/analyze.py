#!/usr/bin/env python3
"""Find the "totally unguarded" window in a decrypted CSI log.

For every sample, compute the variance of the subcarrier amplitudes. Motion in
the room spreads the amplitudes out (high variance); an empty room gives a flat
channel (variance near 0). Report every quiet run and the quietest 30 s slot.

usage: analyze.py log_055.csv [--window 30] [--thresh 0.3]
"""
import argparse
import csv
import datetime
import statistics as st


def utc(ms):
    return datetime.datetime.fromtimestamp(ms / 1000, datetime.UTC).strftime("%Y-%m-%d %H:%M:%S")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--window", type=float, default=30, help="window length in seconds")
    ap.add_argument("--thresh", type=float, default=0.3, help="quiet = variance < thresh * median")
    args = ap.parse_args()

    ts, var = [], []
    with open(args.csv) as f:
        rows = csv.reader(f)
        next(rows)
        for row in rows:
            amps = [float(x) for x in row[3].strip("[]").split(",")]
            ts.append(int(row[0]))
            var.append(st.pvariance(amps))

    period_ms = ts[1] - ts[0]
    med = st.median(var)
    print(f"{len(var)} samples, {period_ms} ms apart, {utc(ts[0])} -> {utc(ts[-1])} UTC")
    print(f"variance: min {min(var):.4f}  median {med:.2f}  max {max(var):.2f}\n")

    # Contiguous runs below the threshold (ignore blips shorter than 2 s)
    runs, start = [], None
    for i, v in enumerate(var + [float("inf")]):
        if v < args.thresh * med:
            if start is None:
                start = i
        elif start is not None:
            if (i - start) * period_ms >= 2000:
                runs.append((start, i))
            start = None

    print("quiet runs (sorted by mean variance):")
    print(f"  {'start UTC':19}  {'end UTC':19}  {'length':>7}  {'mean var':>9}")
    for a, b in sorted(runs, key=lambda r: st.fmean(var[r[0]:r[1]])):
        length = (b - a) * period_ms / 1000
        print(f"  {utc(ts[a])}  {utc(ts[b - 1])}  {length:6.0f}s  {st.fmean(var[a:b]):9.4f}")

    # Quietest sliding window of the requested length
    k = int(args.window * 1000 / period_ms)
    s = sum(var[:k])
    best_sum, best_i = s, 0
    for i in range(k, len(var)):
        s += var[i] - var[i - k]
        if s < best_sum:
            best_sum, best_i = s, i - k + 1
    epoch = ts[best_i] // 1000
    print(f"\nquietest {args.window:.0f}s window: {utc(ts[best_i])} UTC "
          f"(mean var {best_sum / k:.4f})")
    print(f"epoch to write: {epoch}  (try {epoch + 1} to land safely inside)")


if __name__ == "__main__":
    main()
