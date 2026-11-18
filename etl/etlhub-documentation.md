# etlhub specific documentation

Some functions within this image are specifically for use by the ETLHub front end. They are documented here. They are not available via the standard cli task router, but only for access via the ETLHUB.

## Importing Pivot data

Scripts: `import_pivot_COM_etlhub.py`, `import_pivot_CSB_etlhub.py`

These scripts fetch community (COM) and clinic (CSB) case counts from the Pivot DHIS2 instance and checks each dataElement for likely data problems. It saves the data and the check result for each dataElement as JSON files in `inputs/temp_fetch/`. **Nothing is imported into PRIDE-C.** The steps for users approvin these data based on the flags and then posting the data will be written within the elthub.

## Configuration

Set these environment variables, either in the shell or in a `.env` file in the folder you run the script from:

| Variable | Description |
|---|---|
| `PIVOT_URL` | URL of the Pivot DHIS2 instance to read from |
| `PIVOT_TOKEN` | Personal access token for the Pivot instance |

Fetch settings are passed in the `__main__` block:

| Argument | Applies to | Default in script | Meaning |
|---|---|---|---|
| `prior_months` | COM and CSB | `8` | Months before today to start the period range. The range stops before the current month. |
| `parent_ou` | COM only | `"VtP4BdCeXIo"` | orgUnit id(s) whose level-6 (fokontany) descendants are fetched. Separate several ids with commas. |

CSB data always covers the 21 Ifanadiana CSBs, which are hard-coded in the package.

## Usage

```bash
python import_pivot_COM_etlhub.py
```

The console shows one line per dataElement:

```
pridec_historic_COMMalaria: <n> rows, ok
pridec_historic_CSBRespinf: <n> rows, FLAGGED
```

Package progress and warnings go to Python `logging`. Configure logging, e.g. `logging.basicConfig(level=logging.INFO)`, if you want to see them.

## Output

All files go to `inputs/temp_fetch/`. The folder is created if it doesn't exist. Each dataElement gets two files:

| File | Contents |
|---|---|
| `<dataElement>_fetched.json` | The fetched data. This is formatted to be directly imported into DHIS2, by being saved under 'dataValues' |
| `<dataElement>_flags.json` | The result of the value check |

The dataElements are:

| Source | dataElement | Check threshold |
|---|---|---|
| COM | `pridec_historic_COMMalaria`, `pridec_historic_COMRespinf`, `pridec_historic_COMDiarrhea` | 100 cases per fokontany per month |
| CSB | `pridec_historic_CSBMalaria`, `pridec_historic_CSBRespinf`, `pridec_historic_CSBDiarrhea` | 500 cases per CSB per month |

### `<dataElement>_fetched.json`

A list of records, one per orgUnit and period, ready to post to DHIS2 `dataValues`:

```json
[ "dataValues":
  {
    "period": "202601",
    "orgUnit": "<orgUnit id>",
    "value": 5,
    "dataElement": "pridec_historic_COMMalaria",
    "categoryOptionCombo": "pridec_COC_u5"
  }
]
```

How values are built:
- **COM:** where a dataElement has several source dx ids, they are summed. Source rows with a blank or non-numeric value are ignored. Total consultations are used to tell missing data from zeroes:
  - a fokontany-month that reported consultations but has no disease value gets `0`;
  - one with no consultations is omitted.
- **CSB:** values are summed by orgUnit and period. Rows with a missing value are dropped, and no zeroes are filled in.

If nothing is left after this, the file contains an empty list `[]`.

### `<dataElement>_flags.json`

The result of `check_import_value`:

```json
{
  "text": "numNA: 0 | minimum value: 0 | maximum value: 36 | negative values: 0 | number of values: 279",
  "flagged": false,
  "error": null
}
```

| Field | Meaning |
|---|---|
| `text` | Summary statistics. |
| `flagged` | `true` if the check found a problem |
| `error` | Description of the problem if flagged; `null` otherwise |

The check flags data when any of these is true:
- it is empty;
- it has missing (NA) values;
- it has negative values;
- any value is above the threshold.

A flagged example:

```json
{
  "text": null,
  "flagged": true,
  "error": "Potential errors in data to be imported: 1 orgUnits exceed case threshold of 500. numNA: 0 | minimum value: 9999 | maximum value: 9999 | negative values: 0"
}
```

## Behaviour to be aware of

- **Flagged data is still saved.** A failed check doesn't stop the fetch or skip the file. Anything downstream that should hold back flagged data must read `flagged` from the `_flags.json` file.
- **Files are overwritten on each run** and never deleted. If a dataElement is later removed from the package, its old files stay in the folder until someone deletes them.
- **Failures stop the script.** If a request to Pivot fails, the script stops with `requests.HTTPError`. An empty `PIVOT_TOKEN` stops it with `ValueError`. The files are only saved after each dataElement is fetch, so if one fails, all will fail.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `ValueError` about authentication | `PIVOT_TOKEN` not set, or `.env` not in the folder you run from |
| `requests.HTTPError` 401 | Token is wrong or expired |
| Files appear somewhere unexpected | The output path is relative to the folder you run from; run from the ETL root or use an absolute path |
| Every element flagged with "data is empty" | No data for the period range or orgUnits; check `prior_months` and `parent_ou` |