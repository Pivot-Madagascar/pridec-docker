from datetime import date
from dateutil.relativedelta import relativedelta

def create_period_range(start: date, end: date |None = None) -> str:
    """
    create string of periods for pe_query

    Args:
        start (date): beginning of  period range
        end (date): end of period range. Default=last month relative to today         
        
    Returns:
        str: period query formatted for DHIS2 API
             e.g. "pe:202001;202002;202003"
    """
     
    if end is None:
        today = date.today()
        end = today.replace(day=1)

    periods = []

    while(start<end):
        periods.append(f"{start.year}{str(start.month).zfill(2)}")
        start = start +relativedelta(months = 1)

    period_string = f"pe:{';'.join(periods)}"

    return period_string