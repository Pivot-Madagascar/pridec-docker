"""ImportSettings through etl/scripts/config.py: under etlhub its getters read the login and the pass (script_config.py)."""


class ScriptImportSettings:
    def read(self) -> dict:
        from etl.scripts import config  # at call time: the getters are read (and patched in tests) on the module

        values = {"dhis_url": config.get_dhis_url(), "dhis_token": config.get_dhis_token(),
                  "parent_ou": config.get_parent_ou()}
        config.check_envvars(required_vars={"DHIS_TOKEN": values["dhis_token"], "DHIS_URL": values["dhis_url"],
                                            "PARENT_OU": values["parent_ou"]})
        return {**values, "gee_variables": config.get_gee_variables()}
