from etl.scripts.import_gee import import_gee
from etl.scripts.import_pivot_COM import import_pivot_com
from etl.scripts.import_pivot_CSB import import_pivot_csb
from etl.scripts.fetch_pridec_climate import fetch_climate
from etl.scripts.fetch_pridec_disease import fetch_disease
from etl.scripts.fetch_pridec_geojson import fetch_geojson
from etl.scripts.build_analytics import build_analytics
from etl.scripts.post_forecast import post_forecast
from etl.scripts.calc_CSB_alerts import calc_csb_alerts
from etl.scripts.update_pridec_key import update_key


class ETLException(Exception):
    pass


def run_import_gee() -> None:
    try:
        import_gee()
    except Exception as e:
        raise ETLException(f"import_gee failed: {e}") from e


def run_import_pivot_com() -> None:
    try:
        import_pivot_com()
    except Exception as e:
        raise ETLException(f"import_pivot_com failed: {e}") from e


def run_import_pivot_csb() -> None:
    try:
        import_pivot_csb()
    except Exception as e:
        raise ETLException(f"import_pivot_csb failed: {e}") from e


def run_fetch_climate() -> None:
    try:
        fetch_climate()
    except Exception as e:
        raise ETLException(f"fetch_climate failed: {e}") from e


def run_fetch_disease() -> None:
    try:
        fetch_disease()
    except Exception as e:
        raise ETLException(f"fetch_disease failed: {e}") from e


def run_fetch_geojson() -> None:
    try:
        fetch_geojson()
    except Exception as e:
        raise ETLException(f"fetch_geojson failed: {e}") from e


def run_build_analytics() -> None:
    try:
        build_analytics()
    except Exception as e:
        raise ETLException(f"build_analytics failed: {e}") from e


def run_post_forecast() -> None:
    try:
        post_forecast()
    except Exception as e:
        raise ETLException(f"post_forecast failed: {e}") from e


def run_calc_csb_alerts() -> None:
    try:
        calc_csb_alerts()
    except Exception as e:
        raise ETLException(f"calc_csb_alerts failed: {e}") from e


def run_update_key() -> None:
    try:
        update_key()
    except Exception as e:
        raise ETLException(f"update_key failed: {e}") from e