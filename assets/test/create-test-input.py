# create test data for input
# from wd: python3 assets/test/create-test-input.py
# requires internet connection to pull geojson data , then is saved in `assets/test` folder
# all other test data is simulated here, no true health data is used
from pridec_gee import get_dhis_geojson
import pandas as pd
import numpy as np
import json
import random
import math
from datetime import date
from dateutil.relativedelta import relativedelta
import os
from dotenv import load_dotenv
load_dotenv(override=False)

random.seed(8675309)


# # uses PRIDE-C instance, run once to save in assets/tests
# orgUnit_poly = get_dhis_geojson(parent_ou= "VtP4BdCeXIo",
#                     ou_level="5",
#                     dhis_url = os.getenv('DHIS_URL'),
#                     dhis_token = os.getenv('DHIS_TOKEN'))
# # save to use without internet connection
# with open("assets/test/orgUnit_poly_pridec.geojson", "w", encoding="utf‑8") as f:
#     json.dump(orgUnit_poly, f, ensure_ascii=False)

with open("assets/test/orgUnit_poly_pridec.geojson", 'r') as f:
    orgUnit_poly = json.load(f)


#set periods (202201-202612) and orgUnits for test data, 
#periods are 202201-202612
# OrgUnits correspond to those above
startdate = date(2021,1,1)
enddate = date(2026,12,31)
periods = []
while(startdate<enddate):
    periods.append(f"{startdate.year}{str(startdate.month).zfill(2)}")
    startdate = startdate +relativedelta(months = 1)

orgUnits = list({
    feature["properties"]["orgUnit"]
    for feature in orgUnit_poly["features"]
    if "properties" in feature and "orgUnit" in feature["properties"]
})

# CLIMATE_DATA ---------------------
CLIMATE_ELEMENTS = {
    "pridec_climate_temperatureMean":   (15,  30),  
    'pridec_climate_mndwi':   (0,   1)
}

climate_values = []

all_periods = sorted(periods)
for element, (lo, hi) in CLIMATE_ELEMENTS.items():

    amplitude = (hi - lo) / 2
    baseline = lo + amplitude

    # randomize curve characteristics per variable
    phase_shift = random.uniform(0, 2 * math.pi)
    yearly_cycles = random.uniform(0.8, 1.2)  # ~annual seasonality

    for i, period in enumerate(all_periods):

        # seasonal sinusoid
        seasonal = math.sin(
            (2 * math.pi * yearly_cycles * i / 12) + phase_shift
        )

        for org_unit in orgUnits:

            # small random noise
            noise = random.uniform(-0.15, 0.15) * amplitude

            value = baseline + (seasonal * amplitude) + noise

            # constrain to allowed range
            value = max(lo, min(hi, value))

            climate_values.append({
                "orgUnit": org_unit,
                "period": period,
                "dataElement": element,
                "value": round(value, 3),
            })




climate_json = {"dataValues": climate_values}

# EXTERNAL_DATA -------------------------------------


df = pd.MultiIndex.from_product(
    [periods, orgUnits],
    names=["period", "orgUnit"]
).to_frame(index=False)

# sequential month index
period_index = {p: i for i, p in enumerate(sorted(periods))}
df["month_idx"] = df["period"].map(period_index)

# -----------------------------
# wealth_index
# constant by orgUnit (1-5)
# -----------------------------

wealth_lookup = {
    ou: round(random.uniform(1, 5), 1)
    for ou in orgUnits
}

df["wealth_index"] = df["orgUnit"].map(wealth_lookup)

# -----------------------------
# fete_nationale
# 1 in July and December only
# -----------------------------

df["month"] = df["period"].str[-2:]

df["fete_nationale"] = np.where(
    df["month"].isin(["07", "12"]),
    1,
    0
)

# -----------------------------
# mosquito_net
# declines over time,
# jumps upward in 202310,
# then declines again
# -----------------------------

intervention_period = "202310"
intervention_idx = period_index[intervention_period]

# orgUnit-specific starting values
net_start = {
    ou: random.uniform(70, 95)
    for ou in orgUnits
}

# orgUnit-specific decline rates
decline_rate = {
    ou: random.uniform(0.15, 0.5)
    for ou in orgUnits
}

mosquito_values = []

for _, row in df.iterrows():

    ou = row["orgUnit"]
    idx = row["month_idx"]

    start = net_start[ou]
    decline = decline_rate[ou]

    # before intervention
    if idx < intervention_idx:
        value = start - (idx * decline)

    # after intervention
    else:
        rebound = 35
        value = (
            start
            - (intervention_idx * decline)
            + rebound
            - ((idx - intervention_idx) * decline)
        )

    # small noise
    value += random.uniform(-2, 2)

    # constrain to sensible range
    value = max(0, min(100, value))

    mosquito_values.append(round(value, 1))

df["mosquito_net"] = mosquito_values

# -----------------------------
# cleanup
# -----------------------------

external_data = df.drop(columns=["month_idx", "month"])

external_data.head()


# DISEASE_DATA ---------------------

#make this a function of the above variables (not space because that is so complicated)

climate_df = (
    pd.DataFrame(climate_values)
    .pivot_table(
        index=["period", "orgUnit"],
        columns="dataElement",
        values="value"
    )
    .reset_index()
)

# flatten column names
climate_df.columns.name = None

# merge with main dataframe
df = external_data.merge(climate_df, on=["period", "orgUnit"], how="left")

# -----------------------------------
# Generate malaria cases
# -----------------------------------

# standardize predictors
temp_scaled = (
    (df["pridec_climate_temperatureMean"] - df["pridec_climate_temperatureMean"].mean())
    / df["pridec_climate_temperatureMean"].std()
)

mndwi_scaled = (
    (df["pridec_climate_mndwi"] - df["pridec_climate_mndwi"].mean())
    / df["pridec_climate_mndwi"].std()
)

wealth_scaled = (
    (df["wealth_index"] - df["wealth_index"].mean())
    / df["wealth_index"].std()
)

net_scaled = (
    (df["mosquito_net"] - df["mosquito_net"].mean())
    / df["mosquito_net"].std()
)

# -----------------------------------
# Linear predictor
# -----------------------------------

linear_predictor = (
    2.5
    + (0.5 * temp_scaled)
    + (0.7 * mndwi_scaled)
    - (0.4 * wealth_scaled)
    - (0.6 * net_scaled)
)

# -----------------------------------
# Convert to lognormal counts
# -----------------------------------

# lognormal mean
expected_cases = np.exp(linear_predictor)

# add stochasticity
malaria_cases = np.random.lognormal(
    mean=np.log(expected_cases),
    sigma=0.35
)

# convert to integer counts
df["malaria_cases"] = np.round(malaria_cases).astype(int)

# optional minimum
df["malaria_cases"] = df["malaria_cases"].clip(lower=0)

malaria_json = {
    "dataValues": (
        df[["orgUnit", "period", "malaria_cases"]]
        .assign(dataElement="pridec_historical_CSBMalaria")
        .rename(columns={"malaria_cases": "value"})
        .to_dict(orient="records")
    )
}

#save data inputs

with open("assets/test/inputs/disease_data.json", "w") as f:
    json.dump(malaria_json, f, indent=2)

with open("assets/test/inputs/climate_data.json", "w") as f:
    json.dump(climate_json, f, indent=2)

external_data.to_csv("assets/test/inputs/external_data.csv", index = False)

with open("assets/test/inputs/orgUnit_poly.geojson", "w", encoding="utf‑8") as f:
    json.dump(orgUnit_poly, f, ensure_ascii=False)

config_json = {
  "pred_vars": [
    "pridec_climate_temperatureMean",
    "wealth_index",
    "mosquito_net",
    "pridec_climate_mndwi"
  ],
  "model_weights": [
    {
      "model": "inla",
      "weight": 0.15
    },
    {
      "model": "glm_nb",
      "weight": 0.2
    },
    {
      "model": "ranger",
      "weight": 0.39
    },
    {
      "model": "arimax",
      "weight": 0.05
    },
    {
      "model": "naive",
      "weight": 0.12
    }
  ],
  "quantile_levels": [
    0.05,
    0.5,
    0.95
  ],
  "month_analysis": 60,
  "month_assess": 3,
  "forecast_start": "202601"
}

with open("assets/test/inputs/config.json", "w", encoding="utf‑8") as f:
    json.dump(config_json, f, ensure_ascii=False)