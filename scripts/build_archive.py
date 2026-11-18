"""Rebuild the checked-in pilot from USGS annual report table transcriptions."""

import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

from build_usgs import DAY, make_rows, summarize, write_csv


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "data" / "archive"
PILOT = ROOT / "data" / "pilot"


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main():
    extracted = {}
    months = {}
    for path in sorted(ARCHIVE.glob("WY*_extracted.csv")):
        for row in read_csv(path):
            station = row["station_id"]
            when = date.fromisoformat(row["date"])
            station_days = extracted.setdefault(station, {})
            if when in station_days:
                raise ValueError(f"Duplicate archive row {station} / {when}")
            values = tuple(Decimal(row[name]) for name in (
                "Q_cfs_extracted", "SSC_mgL_extracted", "SSL_short_ton_day_extracted"
            ))
            if any(not value.is_finite() or value < 0 for value in values):
                raise ValueError(f"Invalid archive value {station} / {when}")
            station_days[when] = values
            months.setdefault((station, row["date"][:7]), []).append(values)

    review = {}
    for row in read_csv(ARCHIVE / "monthly_totals.csv"):
        station, month = row["station_id"], row["month"]
        key = (station, month)
        if key in review:
            raise ValueError(f"Duplicate monthly total {key}")
        expected_q = Decimal(row["Q_cfs_sum"])
        expected_load = Decimal(row["SSL_short_tons"])
        month_values = months[key]
        actual_q = sum(v[0] for v in month_values)
        actual_load = sum(v[2] for v in month_values)
        review[key] = {
            "station_id": station, "month": month,
            "Q_cfs_sum_extracted": actual_q, "Q_cfs_sum_published": expected_q,
            "Q_month_total_matches": int(actual_q == expected_q),
            "SSL_short_tons_extracted": actual_load, "SSL_short_tons_published": expected_load,
            "SSL_month_total_matches": int(actual_load == expected_load),
        }
    if set(review) != set(months):
        raise ValueError("Daily archives and monthly total keys differ")

    all_rows, coverage = [], []
    for station, station_days in sorted(extracted.items()):
        start, end = min(station_days), max(station_days)
        if len(station_days) != (end - start) // DAY + 1:
            raise ValueError(f"Calendar missing dates for {station}")
        series = {"Q_cfs": {}, "SSC_mgL": {}, "SSL_short_ton_day": {}}
        for when, (q, ssc, load) in station_days.items():
            check = review[station, when.isoformat()[:7]]
            series["SSC_mgL"][when] = (float(ssc), [])
            if check["Q_month_total_matches"]:
                series["Q_cfs"][when] = (float(q), [])
            if check["SSL_month_total_matches"]:
                series["SSL_short_ton_day"][when] = (float(load), [])
        rows = make_rows(station, start, end, series)
        for row in rows:
            check = review[station, row["date"][:7]]
            row["Q_month_total_matches"] = check["Q_month_total_matches"]
            row["SSL_month_total_matches"] = check["SSL_month_total_matches"]
            row["source_report"] = f"USGS IA-{row['water_year_us'] % 100:02d}-1"
        all_rows.extend(rows)
        coverage.append(summarize(station, rows))
    PILOT.mkdir(exist_ok=True)
    write_csv(PILOT / "daily.csv", all_rows)
    write_csv(PILOT / "coverage.csv", coverage)
    write_csv(PILOT / "monthly_qc.csv", [review[key] for key in sorted(review)])


if __name__ == "__main__":
    main()
