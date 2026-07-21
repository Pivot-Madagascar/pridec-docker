export interface ConfigResponse {
  dhis_url: string | null
  dhis_token: string | null
  parent_ou: string | null
  ou_level: number | null
  disease_code: string | null
}