export interface ConfigResponse {
  // Read-only: set by the DHIS2 login. The token itself is never sent to the browser.
  dhis_url: string | null
  has_dhis_token: boolean
  dhis_token_expires_at: number | null
  parent_ou: string | null
  ou_level: number | null
  disease_code: string | null
}

export type ConfigUpdate = Partial<Pick<ConfigResponse, 'parent_ou' | 'ou_level' | 'disease_code'>>
