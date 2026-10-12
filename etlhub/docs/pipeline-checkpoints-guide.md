# Suivi du pipeline : guide rapide

Ce guide explique en bref comment etlhub suit et contrôle le pipeline mensuel.
- La conception complète est dans [pipeline-checkpoints.md](pipeline-checkpoints.md).
- Les schémas sont dans [pipeline-checkpoints-diagrams.md](pipeline-checkpoints-diagrams.md).

## En une phrase

etlhub enregistre, pour chaque mois, ce qui a **vraiment réussi**. Il **refuse** tout ce qui sort de l'ordre prévu,
n'exécute **qu'un seul job à la fois**, traite **un seul forecast (source × maladie) à la fois**, et demande une
**confirmation** avant de défaire ce qui était validé.

## Le cycle

Un **cycle** est le run complet du pipeline, **une fois par mois**. Il est désigné par son `forecast_start` (`YYYYMM`).
- Il s'ouvre au premier lancement, avec le mois en cours.
- Au **changement de mois**, un nouveau cycle commence automatiquement : l'ancien reste inachevé s'il n'était pas fini,
  et son run ouvert est abandonné.
- Une fois les 3 étapes valides, il est **fermé** : le mois ne peut plus tourner une seconde fois.

| # | Étape | Ce qu'il faut réussir | Ordre |
|---|---|---|---|
| ① | `data_import` | `import_gee`, `import_pivot_com`, `import_pivot_csb`, puis `build_analytics` | 3 imports libres, `build_analytics` après |
| ② | `forecast` | **9 runs**, un par couple source × maladie (ADJ, COM, CSB × Malaria, Diarrhea, Respinf) | Runs libres entre eux, un seul ouvert à la fois |
| ③ | `system_update` | `build_analytics` → `calc_csb_alerts` → `build_analytics` (après alertes) → `update_key` | Imposé |

### Un run de forecast

On l'ouvre avec `POST /pipeline/runs` `{"source": "CSB", "disease": "Malaria"}`. L'ouverture **vide `input/` et `output/`**
et fixe le contexte du run :

| Couple | `DISEASE_CODE` | `OU_LEVEL` | `ALERT_NAME` |
|---|---|---|---|
| ADJ/x | `pridec_historic_ADJ<x>` | 6 | — |
| COM/x | `pridec_historic_COM<x>` | 6 | — |
| CSB/x | `pridec_historic_CSB<x>` | 5 | `CSB<x>Vigilance` |

Ce contexte est réécrit dans la config dynamique à chaque job du run : il n'y a rien à changer dans la page Admin.

Items d'un run, avec leurs prérequis :

```
config/<maladie> ┐  (upload, un par maladie)
fetch_disease    ├─→ validate_inputs ─→ forecast ─→ [calc_orgunit_alerts, CSB seulement] ─→ approve ─→ post_forecast
fetch_climate    │
fetch_geojson    ┘
```

- **`config.json` : un par maladie.** On le téléverse dans le premier run de la maladie ; il est remis automatiquement
  dans `input/` pour ses 2 autres runs. Soit 3 uploads par cycle.
- **`external_data.csv` : facultatif, un par niveau** (fokontany pour ADJ et COM, CSB pour CSB). Ce n'est pas un item ;
  le run indique `external_data: uploaded | none`, et le fichier est remis dans `input/` pour les autres runs du même niveau.
- Remplacer un fichier **déjà utilisé** demande `confirm=true` et ne remet à zéro **que le run ouvert** ; les runs déjà
  calculés avec l'ancien fichier gardent leur `success` et sont listés dans `impact.stale_runs`.
- `approve` est une décision : `POST /pipeline/runs/current/approve` avec `{"decision": "approve"}`, ou `"reject"` pour
  refaire le forecast.
- Le run se **ferme** quand `post_forecast` réussit. On peut aussi l'**abandonner** (`DELETE /pipeline/runs/current`) :
  rien n'est publié, et ses items repassent en `pending`.

## Les règles

| Règle | Contenu |
|---|---|
| R1 | Tout item est obligatoire (`external_data.csv` n'est pas un item ; `config.json` est un item par maladie). |
| R2 | Un item ne démarre que si ses prérequis sont en `success`. |
| R3 | Un seul job à la fois. **Le verrou n'expire jamais.** |
| R4 | Une étape ne vaut que si la précédente vaut. Sinon, les suivantes sont bloquées, mais leurs `success` sont conservés. |
| R5 | Défaire ce qui était validé exige `confirm=true` : relancer un `success`, remplacer un fichier déjà utilisé, rouvrir un couple fermé. |
| R6 | Un seul run de forecast ouvert à la fois. |

Un refus répond **409** (422 pour un `config.json` dont le `forecast_start` n'est pas le cycle) et n'écrit rien.
Tous les messages sont en anglais :

```json
{"message": "build_analytics needs data_import/import_gee in success first"}
{"message": "fetch_climate needs an open forecast run (POST /pipeline/runs)"}
{"message": "Run CSB/Malaria is open: finish or abandon it first"}
{"message": "import_gee (import_gee_ab12cd34) is running since 2026-10-09T14:02:11: one job at a time"}
{"message": "Cycle 202610 is complete: the next cycle starts next month"}
```

## Statuts d'un item

| Statut | Signification |
|---|---|
| `pending` | jamais lancé, ou remis à zéro (pas de ligne en base) |
| `running` | lancé, pas encore terminé |
| `success` | réussi : compte pour valider l'étape |
| `error` | échec : se relance sans confirmation |

**Dans un run**, relancer ou remplacer un item remet en `pending` **tout ce qui en dépend** dans le run.
Par exemple, relancer `fetch_climate` remet `validate_inputs` et `forecast` en `pending`.

## Confirmation (R5)

Sans `confirm=true`, le serveur décrit l'impact au lieu d'agir :

```json
{
  "code": "confirmation_required",
  "message": "COM/Respinf:fetch_climate is already in success: resend with confirm=true to relaunch it",
  "impact": {
    "item": "COM/Respinf:fetch_climate",
    "step": "forecast",
    "current_step": "forecast",
    "reset_items": ["COM/Respinf:validate_inputs", "COM/Respinf:forecast"],
    "blocked_steps": ["system_update"],
    "kept_items": {"system_update": 0}
  }
}
```

etlui affiche ce constat, demande l'approbation, puis renvoie la même requête avec `?confirm=true`.
Le paramètre existe sur toutes les routes de lancement, sur `POST` et `DELETE /input/files/{name}` et sur `POST /pipeline/runs`.

## Mode test (DRYRUN)

Le bouton **« Mode test » (test = OUI)** d'etlui correspond à **`DRYRUN=true`**.
- On bascule avec `PUT /pipeline/mode` `{"dry_run": true | false}`. Le serveur écrit `DRYRUN` dans la config dynamique,
  que les scripts ETL lisent : en test, ils n'écrivent rien dans DHIS2. Le `.env` ne donne que la valeur de départ.
- En test, les checkpoints, runs et verrou sont gardés **dans Redis seulement**, jamais dans `logs/etlhub.db`.
  Les données de production ne sont ni visibles ni modifiées. Le cycle reste le mois réel ; les mêmes règles s'appliquent.
- **Revenir en production** (`dry_run: false`) efface ce qui est dans Redis. S'il y a des données de test,
  il faut `confirm=true` (409 `confirmation_required` sinon, avec le run ouvert et les items réussis dans `impact`).
- La bascule est refusée pendant qu'un job tourne.
- `GET /pipeline/checkpoints` indique le mode (`dry_run`).

## Les endpoints du suivi

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/pipeline/checkpoints?cycle=YYYYMM` | État du cycle : `current_step`, `cycle_state`, `run`, `lock`, étapes (`done`, `accessible`) et items (`status`, `launchable`) |
| POST | `/pipeline/runs` | Ouvre le run d'un couple |
| DELETE | `/pipeline/runs/current` | Abandonne le run ouvert |
| POST | `/pipeline/runs/current/approve` | `{"decision": "approve" \| "reject"}` |
| PUT | `/pipeline/mode` | `{"dry_run": true \| false}` : mode test ou production (`confirm=true` pour quitter le test avec des données) |
| DELETE | `/pipeline/lock` | Libère le verrou d'un job dont le worker a été tué ; l'item `running` passe en `error` |
| POST | `/calc_orgunit_alerts` | **501** : pas encore implémenté (voir les limites) |

Toutes ces routes exigent une session etlui.

## Limites connues

- **`calc_orgunit_alerts` n'existe pas encore** (aucun script). Sa route répond 501 : **les runs CSB, et donc le cycle,
  ne peuvent pas se terminer** tant qu'il n'est pas implémenté.
- **Un worker tué bloque tout** jusqu'à `DELETE /pipeline/lock`.
- **Un cycle non terminé à la fin du mois reste inachevé** : le mois suivant repart de zéro.
- **Mode test** : `build_analytics` ignore `DRYRUN` et relance quand même l'analytics DHIS2.
- `DELETE /output/reset` et les jobs lancés en ligne de commande (`./pridec`) échappent à ces contrôles.
- **etlui** est branché (2026-10-09), mais n'a été vérifié qu'avec une API simulée. le tableau de bord d'etlui n'a plus de bouton « reset output » (`DELETE /output/reset` reste disponible dans l'API).

## Où est le code

| Fichier | Contenu |
|---|---|
| `domain/pipeline.py` | Étapes, items, prérequis, règles (code pur, sans I/O) |
| `infrastructure/checkpoint_store.py` | Tables `checkpoints`, `pipeline_lock`, `forecast_runs` (`logs/etlhub.db`), contexte du run, vidage de `input/` et `output/` |
| `api/routers/pipeline_router.py` | Routes du suivi et des runs |
| `infrastructure/tasks.py` | Prise du verrou au lancement, résultat en fin de job |
| `tests/infrastructure/test_checkpoint_store.py`, `tests/api/test_pipeline_router.py` | Tests |

**Ajouter un nouveau type de job ?** Ajoute-le dans `domain/pipeline.py` : dans `PIPELINE`, et dans `RUN_TASKS` s'il
appartient à un run. Sinon, son lancement échoue.
