import numpy as np

def check_dhis_value(df):
    this_value = df['value']
    
    err_1 = this_value.isna().sum()
    print(f"numNA: {err_1}")
    
    print("minimum value:", this_value.min())
    print("maximum value:", this_value.max())
    
    err_3 = (this_value < 0).sum()
    print(f"negative values: {err_3}")
    
    if (err_1 + err_3) > 0:
        raise ValueError("Incorrectly formatted data.")