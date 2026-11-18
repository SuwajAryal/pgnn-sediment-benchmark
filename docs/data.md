# Data provenance and quality checks

## Source and study window

The pilot uses U.S. Geological Survey daily tables for discharge, suspended sediment concentration (SSC), and suspended sediment discharge (reported load). It includes 1 October 1984 through 30 September 1987 for McGregor and Wapello. Station identifiers are strings with leading zeros.

- U.S. Geological Survey, *Water Resources Data, Iowa, Water Year 1985*, Water Data Report IA-85-1. [Report](https://pubs.usgs.gov/wdr/1985/ia-85-1/report.pdf)
- U.S. Geological Survey, *Water Resources Data, Iowa, Water Year 1986*, Water Data Report IA-86-1. [Report](https://pubs.usgs.gov/wdr/1986/ia-86-1/report.pdf)
- U.S. Geological Survey, *Water Resources Data, Iowa, Water Year 1987*, Water Data Report IA-87-1. [Report](https://pubs.usgs.gov/wdr/1987/ia-87-1/report.pdf)

The repository records the numeric transcription under `data/archive`. The build checks for unique station dates, continuous station calendars, finite nonnegative values, and complete matching monthly keys. Discharge and reported load are summed independently and compared with the printed totals. A discrepancy withholds the relevant series for that station-month in the screened data. The other series remain available when their own checks pass. The raw extraction remains available for reconciliation with digital archive data.

The SSC series has no published monthly totals. Its annual extrema match the reports for each station-year, including the six maximum dates listed below. This is an aggregate transcription check. The source page scans were unavailable for a cell-by-cell check, and individual errors can survive these checks. Use the digital USGS records for the journal dataset and compare them with the archived pilot where dates overlap.

| Station | US water year | Minimum SSC (mg/L) | Maximum SSC (mg/L) | Maximum date |
|---|---:|---:|---:|---|
| McGregor | 1985 | 3 | 409 | 1985-02-24 |
| McGregor | 1986 | 1 | 2350 | 1986-03-19 |
| McGregor | 1987 | 2 | 193 | 1987-05-27 |
| Wapello | 1985 | 4 | 1670 | 1985-02-24 |
| Wapello | 1986 | 6 | 2120 | 1986-07-09 |
| Wapello | 1987 | 17 | 3700 | 1987-05-22 |

## Screened daily fields

| Fields | Meaning |
|---|---|
| `station_id`, `date`, `water_year_us` | USGS gauge number, local observation date (ISO 8601), and water year ending in September. |
| `Q_cfs`, `Q_m3s` | Daily discharge in ft³/s and m³/s. Conversion factor 0.028316846592. |
| `SSC_mgL` | Agency-published daily SSC in mg/L. Historical USGS daily series may include record computation between sediment samples. |
| `SSL_short_ton_day`, `SSL_metric_t_day` | Agency-published sediment discharge in US short tons/day and metric tonnes/day. Conversion factor 0.90718474. |
| Fields ending in `_qualifiers` | Qualifiers when available from the digital API. Archive transcriptions leave these blank. A blank is not a qualifier assertion. |
| `Q_lag1` to `Q_lag3`, `SSC_lag1_mgL`, `SSC_lag2_mgL` | Prior calendar day values in the matching units, calculated within each station. Missing prior data stays blank. |
| `dQ`, `Q_max_7d`, `Q_ratio`, `HI_proxy` | Daily Q difference in m³/s, seven-day maximum Q in m³/s, current Q divided by seven-day mean Q, and dQ divided by seven-day maximum Q. The window includes the current day and requires seven available Q values. |
| `paired` | 1 when that date has both screened Q and SSC. |
| `Q_month_total_matches`, `SSL_month_total_matches`, `source_report` | Archive reconciliation for each series and citation key for the source report. |

## Data for the PGNN

The comparative study still needs multi-year approved records and concurrent catchment-area rainfall and temperature. Reproducing the original Yang term also needs station-specific channel slope, width, depth, and a defensible grain-size parameter. Keep the source and units of each covariate in the data inventory. This archive dataset supports development of ingestion and validation. Complete the data inventory before fitting models or drawing conclusions about high-flow performance.

The live download uses USGS parameter codes 00060 (Q), 80154 (SSC), and 80155 (reported load), with daily mean statistic 00003. Raw API responses and query dates are saved under the chosen output directory. Approval status and qualifiers remain traceable to each raw response. [Daily API schema](https://api.waterdata.usgs.gov/ogcapi/v1/collections/daily/schema?f=html)

## Reuse

USGS-produced data are in the U.S. public domain under its stated policy. Acknowledge USGS and cite the original annual reports or the station-level digital records as appropriate. Record retrieval dates and preserve third-party rights notices if additional products are added. Obtain any applicable redistribution permission for the separate DHM workbook before adding it. [USGS copyrights and credits](https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits)
