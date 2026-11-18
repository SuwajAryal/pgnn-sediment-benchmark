# PGNN suspended sediment benchmark

Daily discharge and suspended sediment concentration data for extending the West Rapti PGNN thesis to U.S. monitoring stations. This repository currently covers dataset preparation.

| USGS station | Station ID | Included archive window |
|---|---|---|
| Mississippi River at McGregor, Iowa | `05389500` | Water years 1985–1987 |
| Iowa River at Wapello, Iowa | `05465500` | Water years 1985–1987 |
| Choptank River near Greensboro, Maryland | `01491000` | Candidate for the digital-data build |

## Start here

- [Screened daily observations](data/pilot/daily.csv)
- [Station coverage](data/pilot/coverage.csv)
- [Monthly table reconciliation](data/pilot/monthly_qc.csv)
- [Data dictionary, source citations, and quality checks](docs/data.md)

Rebuild the archived pilot with Python 3.10 or later. No external libraries are required.

```powershell
python scripts/build_archive.py
```

The live digital-data downloader queries approved USGS daily means for the three candidate stations. A different output directory can hold each build. Append `--use-cache` to resume with completed responses.

```powershell
python scripts/build_usgs.py --common-window --output data/generated/common
python scripts/build_usgs.py --output data/generated/full
```

The live API could not be reached from the environment used to assemble the archives. The exported three-year pilot is available offline. Climate, hydraulic geometry, grain size, and the DHM West Rapti workbook are outside the current data package.
