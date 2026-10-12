# Pipeline checkpoints : l'essentiel

etlhub note ce qui a **vraiment réussi** dans le pipeline du mois, et **refuse** ce qui sort des règles.
Plus de détails : [guide](pipeline-checkpoints-guide.md) · [diagrammes](pipeline-checkpoints-diagrams.md) · [conception](pipeline-checkpoints.md).

## Le cycle

- **1 cycle = le pipeline complet, 1 fois par mois**, nommé par son `forecast_start` (ex. `202610`).
- Il **s'ouvre** au premier lancement du mois.
- Au **changement de mois**, un nouveau cycle commence tout seul. L'ancien, s'il n'est pas fini, reste inachevé
  (on le garde dans l'historique) et son run ouvert est abandonné.
- Il **se ferme** quand les 3 étapes sont validées. Le même mois ne peut pas tourner deux fois.

## Les 3 étapes

| Étape | À réussir | Ordre |
|---|---|---|
| ① `data_import` | `import_gee`, `import_pivot_com`, `import_pivot_csb`, puis `build_analytics` | 3 imports libres, `build_analytics` en dernier |
| ② `forecast` | **9 runs** : ADJ, COM, CSB × Malaria, Diarrhea, Respinf | Runs dans l'ordre voulu, **un seul ouvert à la fois** |
| ③ `system_update` | `build_analytics` → `calc_csb_alerts` → `build_analytics` → `update_key` | Imposé |

## Un run de forecast (étape ②)

1. **Ouvrir** le run d'un couple (`POST /pipeline/runs`). Le serveur vide `input/` et `output/`, puis fixe tout seul
   `DISEASE_CODE`, `OU_LEVEL` (6 pour ADJ/COM, 5 pour CSB) et `ALERT_NAME` (CSB).
2. **Fichiers** :
   - `config.json` : **1 par maladie**. On le téléverse au premier run de la maladie ; les 2 autres runs le reçoivent automatiquement.
   - `external_data.csv` : **facultatif, 1 par niveau** (fokontany ou CSB), même principe.
3. **Jobs** : `fetch_disease`, `fetch_climate`, `fetch_geojson` → `validate_inputs` → `forecast`
   → `calc_orgunit_alerts` (CSB seulement).
4. **Décider** : lire le rapport, puis `approve` (ou `reject` pour refaire le forecast).
5. **Publier** : `post_forecast`. Le run se **ferme** et un autre couple peut s'ouvrir.

On peut **abandonner** un run à tout moment : rien n'est publié, et ses étapes repartent à zéro.

## Les règles

| | Règle | Si elle n'est pas respectée |
|---|---|---|
| **R1** | Tout est obligatoire (sauf `external_data.csv`). | L'étape ne se valide pas. |
| **R2** | Une action attend que ses prérequis soient réussis. | Refus 409. |
| **R3** | **Un seul job à la fois.** Le verrou **n'expire jamais**. | Refus 409. Worker planté : `DELETE /pipeline/lock`. |
| **R4** | Une étape ne compte que si la précédente compte. | Étapes suivantes bloquées ; leurs réussites sont gardées et recomptent ensuite. |
| **R5** | **Défaire ce qui a réussi demande une confirmation** : relancer une action réussie, remplacer un fichier déjà utilisé, rouvrir un run terminé. | Refus 409 `confirmation_required` qui décrit l'impact ; on renvoie avec `?confirm=true`. |
| **R6** | **Un seul run de forecast ouvert à la fois.** | Refus 409. |

Bon à savoir :
- Un refus **n'écrit jamais rien**. Les messages sont en anglais.
- Relancer une action **en échec** ne demande pas de confirmation.
- Dans un run, relancer ou remplacer quelque chose **remet à zéro tout ce qui en dépend dans ce run**.
  Les autres runs ne sont pas touchés.
- `config.json` doit avoir `forecast_start` = le cycle (sinon 422). S'il n'en a pas, il est accepté seulement pendant le mois du cycle.

## Mode test

Le bouton **« Mode test » (test = OUI)** d'etlui correspond à **`DRYRUN=true`**.
- On bascule avec `PUT /pipeline/mode` `{"dry_run": true | false}`. Le serveur écrit `DRYRUN` dans la config dynamique,
  que les scripts ETL lisent : en test, ils n'écrivent rien dans DHIS2. Le `.env` ne donne que la valeur de départ.
- En test, les checkpoints, runs et verrou sont gardés **dans Redis seulement**, jamais dans `logs/etlhub.db`.
  Les données de production ne sont ni visibles ni modifiées. Le cycle reste le mois réel ; les mêmes règles s'appliquent.
- **Revenir en production** (`dry_run: false`) efface ce qui est dans Redis. S'il y a des données de test,
  il faut `confirm=true` (409 `confirmation_required` sinon, avec le run ouvert et les items réussis dans `impact`).
- La bascule est refusée pendant qu'un job tourne.
- `GET /pipeline/checkpoints` indique le mode (`dry_run`).

## Statuts

`pending` (pas fait) · `running` (en cours) · `success` (réussi, compte) · `error` (échec, à relancer)

## Où en suis-je ?

`GET /pipeline/checkpoints` renvoie :
- l'étape courante, le run ouvert et le job en cours ;
- pour chaque étape : `done` (validée) et `accessible` (on peut y travailler) ;
- pour chaque action : `status` et `launchable` (lançable maintenant).

## Limites actuelles

- **`calc_orgunit_alerts` n'existe pas encore** (réponse 501) : les runs CSB, donc le cycle, ne peuvent pas se terminer.
- **Interface** (etlui) : branchée depuis le 2026-10-09 ; elle n'a pas été testée contre un vrai etlhub, seulement avec une API simulée. le tableau de bord d'etlui n'a plus de bouton « reset output » (`DELETE /output/reset` reste disponible dans l'API).
- Un cycle qui n'est pas fini à la fin du mois reste inachevé : rien ne le termine à sa place.
- En mode test, `build_analytics` relance quand même l'analytics DHIS2 (il ignore `DRYRUN`).
- `DELETE /output/reset` et la ligne de commande (`./pridec`) échappent à ces contrôles.
