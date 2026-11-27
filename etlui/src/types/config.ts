export interface ConfigResponse {
  // Read-only: set by the DHIS2 login. The token itself is never sent to the browser.
  dhis_url: string | null
  has_dhis_token: boolean
  dhis_token_expires_at: number | null
  parent_ou: string | null
  ou_level: number | null
  disease_code: string | null
  log_level: LogLevel | null
  pivot_url: string | null // the Pivot DHIS2 the imports read from
  has_pivot_token: boolean // PIVOT_TOKEN stays in etlhub's environment: never sent to the browser
  // Read only: every GEE variable of pridec_gee. A pass chooses its own when it starts (Home).
  gee_variables: string[]
}

export const LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'] as const
export type LogLevel = (typeof LOG_LEVELS)[number]

export type ConfigUpdate = Partial<
  Pick<ConfigResponse, 'parent_ou' | 'ou_level' | 'disease_code' | 'log_level' | 'pivot_url'>
>
