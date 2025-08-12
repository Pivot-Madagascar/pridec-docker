from datetime import datetime
from dateutil.relativedelta import relativedelta

def create_period(n_months=6):
    """
    create string of periods for pe_query

    Args:
        n_months(int)          number of months in the past to get. Default = 6
        
    Returns:
        string of period query formatted for DHIS2 API
    """
     
    today = datetime.today()

    periods = [
        (today - relativedelta(months=i)).strftime("%Y%m")
        for i in range(n_months)
    ]
    periods = periods[::-1]
    period_string = f"pe:{';'.join(periods)}"

    return period_string