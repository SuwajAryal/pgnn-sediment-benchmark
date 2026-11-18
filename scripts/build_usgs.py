"""Build a daily SSC/discharge dataset from USGS Water Data APIs (Python 3.10+)."""

import argparse
import csv
from datetime import date, datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
from statistics import mean
from urllib.error import URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


API = "https://api.waterdata.usgs.gov/ogcapi/v1/collections/daily/items"
SITES = {
    "01491000": ("Choptank River near Greensboro, MD", "1980-10-01", "1991-09-29"),
    "05465500": ("Iowa River at Wapello, IA", "1978-04-01", "2006-09-30"),
    "05389500": ("Mississippi River at McGregor, IA", "1975-07-01", "2004-09-30"),
}
PARAMETERS = {"00060": "Q_cfs", "80154": "SSC_mgL", "80155": "SSL_short_ton_day"}
DAY = timedelta(days=1)


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        if rows:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


def fetch(site, code, start, end, cache):
    url = API + "?" + urlencode({
        "monitoring_location_id": "USGS-" + site,
        "parameter_code": code, "statistic_id": "00003", "f": "json",
        "datetime": f"{start}/{end}", "limit": 20000,
    })
    key = os.environ.get("USGS_API_KEY")
    headers = {"Accept": "application/geo+json", "User-Agent": "pgnn-ssc-research/1.0"}
    if key:
        headers["X-Api-Key"] = key
    records = []
    visited = set()
    request_url = url
    while request_url:
        if urlsplit(request_url).netloc != "api.waterdata.usgs.gov" or request_url in visited:
            raise ValueError("Unexpected USGS pagination link")
        visited.add(request_url)
        with urlopen(Request(request_url, headers=headers), timeout=60) as response:
            page = json.load(response)
        records.extend(page["features"])
        request_url = next((x["href"] for x in page.get("links", []) if x["rel"] == "next"), None)
    cache.write_text(json.dumps({
        "query": url,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "features": records,
    }, ensure_ascii=False), encoding="utf-8")
    return records


def accepted_values(features, site, code):
    by_date = {}
    for feature in features:
        p = feature["properties"]
        if (p["monitoring_location_id"], p["parameter_code"], p["statistic_id"]) != (
                "USGS-" + site, code, "00003"):
            raise ValueError(f"Unexpected series for {site} / {code}")
        approval = p.get("approval_status", p.get("approvals_status", []))
        statuses = [approval] if isinstance(approval, str) else approval or []
        if not any(str(item).casefold() == "approved" for item in statuses):
            continue
        try:
            value = float(p["value"])
        except (TypeError, ValueError):
            continue
        if not math.isfinite(value) or value < 0:
            continue
        when = date.fromisoformat(p["time"][:10])
        qualifier = p.get("qualifier") or []
        if isinstance(qualifier, str):
            qualifier = [qualifier]
        if when in by_date:
            previous_value, previous_qualifier = by_date[when]
            if previous_value != value:
                raise ValueError(f"Conflicting approved values at {site} / {code} / {when}")
            qualifier = previous_qualifier + qualifier
        by_date[when] = (value, sorted(set(qualifier)))
    return by_date


def scale(value, factor):
    return None if value is None else value * factor


def make_rows(site, start, end, series):
    q_values = series["Q_cfs"]
    ssc_values = series["SSC_mgL"]
    rows = []
    for offset in range((end - start).days + 1):
        when = start + offset * DAY
        row = {
            "station_id": site, "date": when.isoformat(),
            "water_year_us": when.year + int(when.month >= 10),
        }
        for name, values in series.items():
            value, qualifiers = values.get(when, (None, []))
            row[name] = value
            row[name + "_qualifiers"] = "|".join(qualifiers)
        q = row["Q_m3s"] = scale(row["Q_cfs"], 0.028316846592)
        row["SSL_metric_t_day"] = scale(row["SSL_short_ton_day"], 0.90718474)
        for lag in (1, 2, 3):
            past = when - lag * DAY
            row[f"Q_lag{lag}"] = scale(q_values.get(past, (None, []))[0], 0.028316846592)
            if lag <= 2:
                row[f"SSC_lag{lag}_mgL"] = ssc_values.get(past, (None, []))[0]
        prior_q = row["Q_lag1"]
        row["dQ"] = q - prior_q if q is not None and prior_q is not None else None
        trailing_q = [q_values.get(when - step * DAY, (None, []))[0] for step in range(7)]
        row["Q_max_7d"] = row["Q_ratio"] = row["HI_proxy"] = None
        if all(item is not None for item in trailing_q):
            max_q = row["Q_max_7d"] = max(trailing_q) * 0.028316846592
            avg_q = mean(trailing_q)
            if avg_q > 0:
                row["Q_ratio"] = row["Q_cfs"] / avg_q
                row["HI_proxy"] = row["dQ"] / max_q
        row["paired"] = int(q is not None and row["SSC_mgL"] is not None)
        rows.append(row)
    return rows


def summarize(site, rows):
    paired = [row for row in rows if row["paired"]]
    return {
        "station_id": site, "start": rows[0]["date"], "end": rows[-1]["date"],
        "calendar_days": len(rows), "q_days": sum(r["Q_cfs"] is not None for r in rows),
        "ssc_days": sum(r["SSC_mgL"] is not None for r in rows), "paired_days": len(paired),
        "paired_pct": round(100 * len(paired) / len(rows), 2),
        "paired_with_ssc_lag1": sum(r["SSC_lag1_mgL"] is not None for r in paired),
        "paired_with_both_ssc_lags": sum(
            r["SSC_lag1_mgL"] is not None and r["SSC_lag2_mgL"] is not None for r in paired),
        "paired_water_years": len({r["water_year_us"] for r in paired}),
        "reported_load_days": sum(r["SSL_short_ton_day"] is not None for r in rows),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=Path("usgs_daily"), type=Path)
    parser.add_argument("--station", action="append", choices=SITES)
    parser.add_argument("--common-window", action="store_true",
                        help="Restrict all stations to October 1980–September 1991")
    parser.add_argument("--use-cache", action="store_true",
                        help="Reuse raw responses matching the requested station and dates")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    raw = args.output / "raw"
    raw.mkdir(exist_ok=True)
    coverage = []
    for site in dict.fromkeys(args.station or SITES):
        _, first, last = SITES[site]
        if args.common_window:
            first, last = "1980-10-01", "1991-09-29"
        start, end = date.fromisoformat(first), date.fromisoformat(last)
        series = {}
        for code, field in PARAMETERS.items():
            cache = raw / f"{site}_{code}_{start}_{end}.json"
            try:
                features = (json.loads(cache.read_text(encoding="utf-8"))["features"]
                            if args.use_cache and cache.exists()
                            else fetch(site, code, start, end, cache))
            except (URLError, TimeoutError) as error:
                raise SystemExit(
                    f"USGS request failed for {site} / {code}: {error}. "
                    "Rerun with --use-cache to keep completed downloads."
                ) from error
            series[field] = accepted_values(features, site, code)
        rows = make_rows(site, start, end, series)
        write_csv(args.output / f"{site}_daily.csv", rows)
        coverage.append(summarize(site, rows))
        write_csv(args.output / "coverage.csv", coverage)
        print(f"{site} {SITES[site][0]} | {coverage[-1]['paired_days']} paired days")
    if any(item["paired_days"] == 0 for item in coverage):
        raise SystemExit("At least one station has zero approved Q–SSC pairs. Inspect raw series.")


if __name__ == "__main__":
    main()
