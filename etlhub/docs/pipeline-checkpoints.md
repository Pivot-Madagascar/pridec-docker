# Checkpoints du pipeline : conception cible

> **État (2026-10-09)**
>
> - **Implémenté côté etlhub** : parcours cible en **3 étapes**, **runs de forecast** (R6), fichiers d'entrée par run,
>   approbation, invalidation des dépendants dans un run, confirmation des relances (R5), cycle mensuel (`forecast_start`),
>   verrou global sans expiration. Code : `domain/pipeline.py`, `infrastructure/checkpoint_store.py`,
>   `api/routers/pipeline_router.py`. Tests : `tests/infrastructure/test_checkpoint_store.py`, `tests/api/test_pipeline_router.py`.
> - **etlui** : fait (§8, étape 12), vérifié avec une API simulée seulement.
> - **À faire** : le script de `calc_orgunit_alerts` (§6).
>
> Références : le schéma cible du processus (3 phases), et `pivot_workflow.sh`, qui en est la version
> **automatisée** pour un seul `DISEASE_CODE` (ce script n'est pas dans ce repo). etlhub/etlui en est la version **manuelle** :
> l'utilisateur déclenche chaque action et téléverse lui-même ses fichiers ; le serveur fait respecter les règles.

## Règles validées

| Règle | Contenu |
|---|---|
| **R1** | Tout item est obligatoire. Ce qui est facultatif (`external_data.csv`) n'est pas un item. `config.json` est **un item par maladie** (`config/<maladie>`), partagé par ses 3 runs. |
| **R2** | Un item ne peut être lancé que si tous ses **prérequis** sont en `success`. |
| **R3** | Un seul job à la fois (verrou global). **Le verrou n'expire jamais** : seul `DELETE /pipeline/lock` le libère. |
| **R4** | Une étape n'est valide (`done`) que si tous ses items sont en `success` **et** que l'étape précédente est valide. Sinon, les étapes suivantes sont inaccessibles. |
| **R5** | Défaire ce qui était validé (relancer un item en `success`, remplacer un fichier déjà validé, rouvrir un run fermé) exige `confirm=true`, donné après une modale de constat. |
| **R6** | Un seul **run de forecast** ouvert à la fois. Un run traite un couple source × maladie, du premier fetch jusqu'à `post_forecast`. |
| **Cycle** | Un run mensuel désigné par son `forecast_start` (`YYYYMM`) : **toujours le mois calendaire**. Il s'ouvre au premier lancement du mois et se ferme une fois les 3 étapes valides. Au changement de mois, le cycle suivant commence automatiquement ; un cycle inachevé le reste, et son run ouvert est abandonné. |
| **Mode test** | `DRYRUN=true` (bouton « Mode test » d'etlui) : les scripts n'écrivent pas dans DHIS2 et les checkpoints sont gardés **dans Redis seulement**. Revenir en production efface ces données, avec `confirm=true` s'il y en a (§4.10). |

Le serveur fait respecter toutes ces règles : sinon, il répond **409** (422 pour un `config.json` invalide),
et un refus n'écrit rien. **Tous les messages de l'API sont en anglais.**

---

## 1. Le problème, rappelé en une ligne

Avant ce travail, le ✓ de l'UI signifiait « l'API a répondu 202 » et non « le job a fini en `success` ».
Cet état vivait dans des `ref` Vue (`results`, `climateSuccess`…), donc il disparaissait au rechargement
de la page et dans un autre navigateur.

---

## 2. Le parcours cible

| # | Étape | Fréquence | Items | Ordre |
|---|---|---|---|---|
| ① | `data_import` | 1× par mois, avant les forecasts | `import_gee`, `import_pivot_com`, `import_pivot_csb`, puis `build_analytics` | Les 3 imports en ordre libre, `build_analytics` après les 3 |
| ② | `forecast` | 9 runs par mois, un par couple source × maladie | 3 `config/<maladie>` (un upload par maladie, dans le premier run de la maladie) ; par run : 3 `fetch_*`, `validate_inputs`, `forecast`, `calc_orgunit_alerts` (CSB seulement), `approve`, `post_forecast` | Voir §4.2. Runs en ordre libre entre eux, un seul ouvert à la fois (R6) |
| ③ | `system_update` | 1× par mois, après les 9 `post_forecast` | `build_analytics`, `calc_csb_alerts`, `build_analytics_after_alerts`, `update_key` | Imposé |

Sources : `ADJ`, `COM`, `CSB`. Maladies : `Malaria`, `Diarrhea`, `Respinf`
(`etlui/src/stores/forecastConfig.ts`).

Ce qui change par rapport au parcours en 4 étapes du socle :
- `external_upload` n'est plus une étape : les fichiers d'entrée sont téléversés pendant les runs. `config.json` une fois
  par maladie (3 uploads), `external_data.csv` une fois par niveau (2 uploads au plus : fokontany pour ADJ et COM, CSB),
  puis remis automatiquement dans `input/` pour les autres runs qui les partagent ;
- les jobs préparatoires (`fetch_*`, `validate_inputs`) deviennent des items suivis ;
- l'approbation devient un checkpoint obligatoire ;
- `post_forecast` passe dans chaque run (« Forecasts → PRIDE-C ») ;
- `build_analytics` est relancé deux fois dans `system_update` (avant et après `calc_csb_alerts`) ;
- les runs CSB ont un item de plus, `calc_orgunit_alerts` (absent du schéma cible, présent dans `pivot_workflow.sh`).
  Il est distinct de `calc_csb_alerts` de l'étape ③ (comptage mensuel).

---

## 3. Ce qu'on garde de la philosophie « stages » (projet `lang`), et ce qu'on change

| Principe dans `lang` | Ce qu'il devient dans etlhub |
|---|---|
| **Le serveur est la seule source de vérité** ; le client ne fait qu'afficher | ✅ Gardé. Checkpoints et runs vivent dans etlhub (SQLite), pas dans Pinia ni localStorage. |
| **Une seule question : « où en suis-je ? »** | ✅ Gardé. `GET /pipeline/checkpoints` renvoie tout l'état, run ouvert compris. |
| **Progression persistée et reprenable** | ✅ Gardé. Tables sans TTL. |
| **Vocabulaire fermé** | ✅ Gardé : `pending` (absence de ligne), `running`, `success`, `error`. |
| **Le client désigne l'étape, le serveur la vérifie** | ✅ Gardé. Le serveur résout le checkpoint au lancement (§4.4). |
| **Définition du parcours séparée du moteur** | ✅ Gardé. Un module Python déclare items et prérequis. |
| **L'état est un agenda** | ❌ **Changé.** On stocke des faits, on calcule la progression. |
| **Avancer = une action dans la requête** | ❌ **Changé.** On avance quand un job finit, souvent en asynchrone. |

> **On stocke un fait par item (« CSB/Malaria:forecast : success, job X, à telle heure »),
> et on *calcule* l'état à chaque lecture.**
> Une étape est valide quand tous ses items sont en `success` et que la précédente est valide.
> L'étape courante est la première qui ne l'est pas.

---

## 4. Conception

### 4.1 Les tables (`logs/etlhub.db`)

```sql
-- Un fait par item : le dernier statut écrase le précédent.
CREATE TABLE IF NOT EXISTS checkpoints (
    cycle      TEXT NOT NULL,   -- '202610'
    step       TEXT NOT NULL,   -- data_import | forecast | system_update
    item       TEXT NOT NULL,   -- 'import_gee', 'config/Malaria', 'CSB/Malaria:forecast'…
    job_id     TEXT,            -- NULL pour une approbation ; 'upload_config_…' pour un upload
    status     TEXT NOT NULL,   -- running | success | error
    updated_at TEXT NOT NULL,
    PRIMARY KEY (cycle, step, item)
);

-- Contexte des runs de forecast (R6). Ce ne sont pas des checkpoints.
CREATE TABLE IF NOT EXISTS forecast_runs (
    cycle         TEXT NOT NULL,
    couple        TEXT NOT NULL,   -- 'CSB/Malaria'
    state         TEXT NOT NULL,   -- open | closed | abandoned
    disease_code  TEXT NOT NULL,   -- 'pridec_historic_CSBMalaria'
    ou_level      TEXT NOT NULL,   -- '6' (ADJ, COM) | '5' (CSB)
    alert_name    TEXT,            -- 'CSBMalariaVigilance' (CSB seulement)
    external_data TEXT NOT NULL DEFAULT 'none',   -- none | uploaded
    opened_at     TEXT NOT NULL,
    closed_at     TEXT,
    PRIMARY KEY (cycle, couple, opened_at)
);
CREATE UNIQUE INDEX IF NOT EXISTS one_open_run ON forecast_runs(state) WHERE state = 'open';
```

- Un item **sans ligne** est `pending`. Remettre un item en `pending` = supprimer sa ligne.
- La table `pipeline_lock` (verrou global, R3) ne change pas. Un upload prend aussi le verrou :
  c'est pourquoi il porte un `job_id` technique (`upload_config_…`, `delete_external_data_…`).
- Les fichiers téléversés sont aussi conservés dans `<data_dir>/uploads/<cycle>/` (`config_<maladie>.json`,
  `external_data_<fkt|csb>.csv`), puisque `input/` est vidé à chaque run. Un nouveau cycle repart sans fichier.
- Ces tables ne sont **pas** soumises au `RETENTION_DAYS` de `request_log`. L'historique détaillé reste dans `request_log` et `logs/`.

### 4.2 La définition du parcours : des items et leurs prérequis

Une liste ordonnée ne suffit plus (ordre libre ici, imposé là). Chaque item déclare ses prérequis **dans son étape** ;
l'ordre entre étapes est donné par R4. Le code réel est dans `domain/pipeline.py` (`run_context`, `run_items`,
`PIPELINE`, `progress`, `launchable`, `blocking_reason`, `dependents`, `resolve_slot`).

```python
SOURCES = ("ADJ", "COM", "CSB")
DISEASES = ("Malaria", "Diarrhea", "Respinf")
COUPLES = [f"{s}/{d}" for s in SOURCES for d in DISEASES]
OU_LEVEL = {"ADJ": "6", "COM": "6", "CSB": "5"}

def config_item(couple: str) -> str:
    return f"config/{couple.split('/')[1]}"       # un upload par maladie, partagé par ses 3 runs

def run_items(couple: str) -> dict[str, list[str]]:
    c = couple
    items = {
        f"{c}:fetch_disease": [],
        f"{c}:fetch_climate": [],
        f"{c}:fetch_geojson": [],
        f"{c}:validate_inputs": [config_item(c), f"{c}:fetch_disease",
                                 f"{c}:fetch_climate", f"{c}:fetch_geojson"],
        f"{c}:forecast": [f"{c}:validate_inputs"],
    }
    last = f"{c}:forecast"
    if c.startswith("CSB/"):
        items[f"{c}:calc_orgunit_alerts"] = [last]
        last = f"{c}:calc_orgunit_alerts"
    items[f"{c}:approve"] = [last]                # décision humaine
    items[f"{c}:post_forecast"] = [f"{c}:approve"]
    return items

PIPELINE = {   # étape → {item: prérequis}
    "data_import": {
        "import_gee": [], "import_pivot_com": [], "import_pivot_csb": [],
        "build_analytics": ["import_gee", "import_pivot_com", "import_pivot_csb"],
    },
    "forecast": {**{f"config/{d}": [] for d in DISEASES},                  # 3 configs
                 **{k: v for c in COUPLES for k, v in run_items(c).items()}},   # + 66 = 69 items
    "system_update": {
        "build_analytics": [],
        "calc_csb_alerts": ["build_analytics"],
        "build_analytics_after_alerts": ["calc_csb_alerts"],
        "update_key": ["build_analytics_after_alerts"],
    },
}
```

`progress()` est chaîné (R4) et renvoie `done`, `accessible` et, pour chaque item, `launchable`
(étape accessible, prérequis en `success`, et pour l'étape ② : item du run ouvert).

L'étape ② compte **69 items** : 3 `config/<maladie>`, 6 runs ADJ et COM de 7 items, 3 runs CSB de 8 items.
`external_data.csv` n'y figure pas (R1, §4.6).

### 4.3 Les runs de forecast (R6)

Les 9 runs partagent les mêmes fichiers (`input/`, `output/`). Deux runs entremêlés produiraient un forecast sur
les données d'un autre couple. D'où un seul run ouvert à la fois, garanti par l'index `one_open_run`
et vérifié avant l'insertion.

**Ouvrir** : `POST /pipeline/runs` avec `{source, disease}`. Le serveur, dans une seule transaction :
1. vérifie R3 (verrou libre), R4 (étape ② accessible) et R6 (aucun run ouvert, sinon 409
   `Run CSB/Malaria is open: finish or abandon it first`) ;
2. si ce couple a déjà un run fermé dans le cycle, exige `confirm=true` (R5) et remet tous les items du couple en `pending` ;
3. vide `input/` et `output/` (comme `pivot_workflow.sh`) ; si le vidage échoue, le run n'est pas ouvert ;
4. enregistre le run `open` avec son contexte figé (`run_context`).

**Pendant le run** : tout job de l'étape ② est rattaché au run ouvert. Au lancement de chaque job de l'étape ②,
le serveur écrit `DISEASE_CODE` et `OU_LEVEL` du run dans la config dynamique (Redis `app:config:dynamic`),
là où `etl/scripts/config.py` les lit ; `ALERT_NAME` y est écrit pour les runs CSB et effacé sinon.
Si l'écriture échoue, le lancement est refusé et rien n'est écrit. etlui n'envoie rien, et la page Admin ne sert plus
à changer de couple. Un job d'étape ② sans run ouvert → 409.

**Fermer** : automatiquement, quand `post_forecast` du run passe en `success`. Un autre couple peut alors s'ouvrir.

**Abandonner** : `DELETE /pipeline/runs/current` (équivalent du « n » du script). Le run passe `abandoned`,
ses items repassent en `pending`, rien n'est publié. Un couple abandonné se rouvre sans confirmation.

### 4.4 Associer un job à son checkpoint : au lancement

`CeleryTaskLauncher.launch` appelle `start()`, qui écrit l'item en `running` avec le `job_id` du job.
En fin de job, `finish(job_id, status)` retrouve la ligne par la colonne `job_id` (rien n'est ajouté dans `job:{id}`).
Le checkpoint est résolu par `resolve_slot` **au lancement**, puis figé (cycle compris : un job lancé en octobre
et fini en novembre reste dans le cycle d'octobre).

- **Jobs de l'étape ②** : l'item est `{couple du run ouvert}:{nom du job}`.
- **`build_analytics`** a trois emplacements (`data_import:build_analytics`, `system_update:build_analytics`,
  `system_update:build_analytics_after_alerts`). `resolve_slot` choisit, dans l'ordre du parcours, le **premier
  emplacement lançable** (`launchable`) qui n'est pas en `success`. S'il n'y en a aucun, il choisit le dernier
  emplacement lançable en `success`, ce qui déclenche R5.
- Aucun paramètre `?step=` : le contrat d'etlui ne change pas pour les lancements.

### 4.5 Qui écrit les statuts

- **Jobs Celery** : `_update_task_status` (`infrastructure/tasks.py`) appelle `finish()` pour `success` et `error`,
  `task_forecast` compris.
- **Jobs synchrones** : `post_forecast` et `update_key` passent par `PipelineGate.run()` dans `AnalyticsService`,
  `success` après l'exécution, `error` si elle lève une exception.
- **Uploads** : `PipelineGate.change_input()` dans `InputUploadService`, sous le verrou.
- **Approbation** : `PipelineGate.decide()`, écriture directe (`job_id = NULL`).
- **Fermeture du run** : dans `finish()`, quand l'item terminé est un `post_forecast` en `success`.

### 4.6 Les fichiers d'entrée (téléversés manuellement)

L'utilisateur choisit lui-même ses fichiers sur son poste. Le serveur ne copie jamais rien depuis `forecast_assets`.

| Fichier | Statut | Règles |
|---|---|---|
| `config.json` | Item `config/<maladie>`, **obligatoire**, **un par maladie** | Téléversé dans le premier run de la maladie (run ouvert, sinon 409). `forecast_start` = cycle, sinon 422 (absent toléré si le cycle est le mois courant). Remis dans `input/` à l'ouverture des 2 autres runs de la maladie. |
| `external_data.csv` | **Facultatif**, pas un item, **un par niveau** (`fkt` : ADJ et COM ; `csb` : CSB) | Run ouvert, sinon 409. Remis dans `input/` à l'ouverture des autres runs du même niveau. Le run enregistre `external_data = uploaded` ou `none`. |

Remplacer ou supprimer l'un des deux fichiers :
- **tant qu'il n'a servi à rien** (`validate_inputs` du run ouvert pas en `success`, et aucun autre run qui le partage
  n'a son `forecast` en `success`) : libre ;
- **sinon** : exige `confirm=true` (R5). **Seul le run ouvert** repasse en `pending` à partir de `validate_inputs`.
  Les autres runs qui avaient utilisé l'ancien fichier gardent leur `success` (ils sont déjà publiés) ; l'`impact`
  les liste dans `stale_runs`.

Supprimer `config.json` remet `config/<maladie>` en `pending`.

### 4.7 L'approbation

Après `forecast` (et `calc_orgunit_alerts` pour CSB), l'utilisateur lit `output/forecast_report.html`, puis :
- `POST /pipeline/runs/current/approve` avec `{"decision": "approve"}` : `{couple}:approve` → `success`,
  ce qui débloque `post_forecast` ;
- `{"decision": "reject"}` : `forecast` et ses dépendants (`calc_orgunit_alerts`, `approve`) repassent en `pending`.
  L'utilisateur corrige (par exemple un nouveau fichier, avec confirmation) et relance, sans confirmation pour le forecast ;
- ou abandonne le run (§4.3).

### 4.8 Relances, invalidations et confirmations (R5)

**Dans un run ouvert**, tout s'appuie sur les mêmes fichiers. Relancer ou remplacer un item remet donc en `pending`
**tous les items du run qui en dépendent** (fermeture transitive des prérequis, `dependents()`). Sans cela, on pourrait
approuver un forecast calculé sur d'anciennes entrées.

**Entre étapes**, c'est l'inverse : les `success` des étapes suivantes **restent en base** (R4). Ils ne comptent plus
tant que l'étape précédente n'est pas revalidée, puis comptent de nouveau sans rien relancer. Les items des étapes ① et ③
n'invalident pas leurs dépendants (relancer `import_gee` laisse `build_analytics` en `success`).

| Action | Confirmation | Effet |
|---|---|---|
| Relancer un item en `error` ou `pending` | Non | Item → `running` |
| Relancer un item en `success` | `confirm=true` | Item → `running`, ses dépendants du run → `pending` |
| Remplacer ou supprimer un fichier déjà utilisé (§4.6) | `confirm=true` | Run ouvert : `validate_inputs` et dépendants → `pending` ; autres runs : inchangés, listés dans `stale_runs` |
| Rejeter le forecast | Non (c'est la décision elle-même) | `forecast` et dépendants → `pending` |
| Rouvrir un couple déjà fermé | `confirm=true` | Tous les items du couple → `pending`, `input/` et `output/` vidés |
| Relancer un item de l'étape ① pendant l'étape ② | `confirm=true` | Étape ① non valide → étapes ② et ③ inaccessibles, run ouvert bloqué |

Sans `confirm=true`, le serveur répond **sans rien écrire** :

```json
{
  "code": "confirmation_required",
  "message": "CSB/Malaria:forecast is already in success: resend with confirm=true to relaunch it",
  "impact": {
    "item": "CSB/Malaria:forecast",
    "step": "forecast",
    "current_step": "forecast",
    "reset_items": ["CSB/Malaria:calc_orgunit_alerts", "CSB/Malaria:approve"],
    "blocked_steps": ["system_update"],
    "kept_items": {"system_update": 0}
  }
}
```

`reset_items` ne liste que les dépendants qui ont une ligne (les autres sont déjà `pending`).
etlui construit la modale de constat **uniquement** à partir de `impact`, exige la case
« J'ai pris connaissance de l'impact et j'approuve cette mise à jour », puis renvoie la même requête avec `confirm=true`.

### 4.9 La lecture

`GET /pipeline/checkpoints?cycle=202610` :

```json
{
  "cycle": "202610",
  "cycle_state": "open",
  "current_step": "forecast",
  "run": {"cycle": "202610", "couple": "CSB/Malaria", "state": "open", "external_data": "uploaded",
          "disease_code": "pridec_historic_CSBMalaria", "ou_level": "5", "alert_name": "CSBMalariaVigilance",
          "opened_at": "…"},
  "lock": null,
  "steps": [
    {"step": "data_import", "done": true, "accessible": true, "items": [
      {"item": "import_gee", "status": "success", "job_id": "import_gee_ab12cd34", "updated_at": "…", "launchable": true}
    ]},
    {"step": "forecast", "done": false, "accessible": true, "items": [
      {"item": "CSB/Malaria:forecast", "status": "running", "job_id": "forecast_…", "updated_at": "…", "launchable": true}
    ]},
    {"step": "system_update", "done": false, "accessible": false, "items": []}
  ]
}
```

`launchable` ne tient pas compte du verrou : un item en cours reste `launchable` ; `lock` dit qu'un job tourne.
etlui appelle cette route au montage et à chaque `etl_log_complete` ou `job_status_update` reçu sur le WebSocket.
Il ne calcule rien : il affiche les ✓, grise ce qui n'est pas `accessible` ou `launchable`, et affiche le couple
du run ouvert au-dessus des sélecteurs de fichiers.

---

### 4.10 Le mode test (DRYRUN)

Le bouton « Mode test » d'etlui (`test = OUI`) correspond à `DRYRUN=true`, la variable que les scripts ETL lisent
(config dynamique Redis, sinon `.env`, défaut `true`).

- **Bascule** : `PUT /pipeline/mode` `{"dry_run": true | false}`, avec `?confirm`. Le serveur écrit `DRYRUN` dans la
  config dynamique ; le `.env` ne fournit que la valeur de départ. Refusée (409) pendant qu'un job tourne.
- **Stockage en test** : la même logique SQL tourne sur une base SQLite **en mémoire**, sérialisée dans la clé Redis
  `pipeline:dry_run:db` (sous le verrou Redis `pipeline:dry_run:lock`). Rien n'est écrit dans `logs/etlhub.db`, et la
  production n'est ni visible ni modifiée. Les fichiers téléversés en test vont dans `uploads/dry_run/`.
- **Cycle en test** : le mois réel, avec les mêmes règles (R1 à R6).
- **Retour en production** : la clé Redis et `uploads/dry_run/` sont effacés. S'il y a des données de test,
  `confirm=true` est exigé ; sinon 409 `confirmation_required` avec
  `impact = {mode, items_in_success, open_run}`.
- **Limite** : `build_analytics` ignore `DRYRUN` (il relance l'analytics DHIS2 même en test). Les fichiers `input/` et
  `output/` sont partagés entre les deux modes : ouvrir un run de test les vide aussi.

---

## 5. Décisions

| Question | Décision |
|---|---|
| Qu'est-ce qu'un cycle ? | Le run mensuel `forecast_start` (`YYYYMM`), toujours le mois calendaire, ouvert par le serveur au premier lancement, fermé quand les 3 étapes sont valides. Un lancement dans un cycle fermé du même mois → 409 `Cycle 202610 is complete…`. **Changement de mois : bascule automatique** ; le cycle précédent reste inachevé s'il n'était pas fini, son run ouvert est abandonné. |
| Mode test ? | `DRYRUN=true`, basculé par `PUT /pipeline/mode`. Checkpoints en Redis seulement ; retour en production avec confirmation, données de test effacées (§4.10). |
| Bloquer ou indiquer ? | Bloquer, côté serveur (409). Un blocage seulement dans l'UI serait contournable. |
| Ordre des imports ? | Libre ; `build_analytics` après les 3. |
| Fichiers d'entrée ? | Téléversés manuellement. `config.json` obligatoire, **un par maladie** (3 uploads) ; `external_data.csv` facultatif, **un par niveau** (fokontany, CSB). Remis dans `input/` pour les runs qui les partagent. Remplacer un fichier déjà utilisé n'invalide que le run ouvert. |
| Choix du couple ? | À l'ouverture du run. `DISEASE_CODE`, `OU_LEVEL`, `ALERT_NAME` sont injectés par le serveur. |
| Approbation ? | Obligatoire, avant `post_forecast`. Rejet → `forecast` à refaire. |
| Échec et relance ? | Le dernier statut gagne. Défaire un `success` exige une confirmation (R5). Dans un run, invalidation des dépendants ; entre étapes, conservation des `success`. |
| Verrou figé ? | **Il n'expire jamais.** `DELETE /pipeline/lock` le libère ; l'item `running` passe alors en `error`. |
| Langue des messages ? | **Anglais**, pour tous les messages de l'API (409, 422, 501). |
| `calc_orgunit_alerts` ? | L'item existe pour les runs CSB, mais `POST /calc_orgunit_alerts` répond **501** tant qu'aucun script ne l'implémente (§6). |

---

## 6. Limites connues

- **`calc_orgunit_alerts` n'est pas implémenté** : aucun module `etl/scripts`, rien dans `pivot_dhis_tools`, et
  `pivot_workflow.sh` n'est pas dans ce repo. La route répond 501, donc **les 3 runs CSB, l'étape ② et le cycle ne
  peuvent pas se terminer** tant que le script n'existe pas. `ALERT_NAME` est écrit dans la config dynamique, mais aucun
  script ne le lit, et `etl/scripts/config.py` ne le compte pas parmi les clés lues depuis Redis.
- **Correspondance des fichiers** : le serveur ne peut pas vérifier que `config.json` correspond à la maladie du run,
  ni que `external_data.csv` correspond au niveau de la source (fokontany ou CSB), sauf si les fichiers contiennent
  un champ qui le permet.
- **`external_data.csv` absent** : à vérifier dans pridec. Si `validate_inputs` ne reprend pas le défaut de `assets`
  pour le `DISEASE_CODE`, « aucun CSV » signifie « aucune variable externe ». Le message d'etlui doit le dire.
- **Run rouvert** : les forecasts déjà publiés dans PRIDE-C y restent tant que le nouveau `post_forecast` ne les remplace pas.
- **Un run inachevé n'est jamais abandonné automatiquement** ; un cycle inachevé bloque le mois suivant.
- **Un worker tué bloque tout** jusqu'à `DELETE /pipeline/lock` : le verrou n'expire jamais.
- **Contexte du run dans Redis** : la page Admin peut encore modifier `DISEASE_CODE` ou `OU_LEVEL` entre deux jobs ;
  le serveur les réécrit au lancement de chaque job de l'étape ②, mais pas pendant qu'un job tourne.
- **Cycle inachevé** : à la fin du mois, un cycle non terminé reste inachevé ; rien ne le termine à sa place.
- **Mode test** : `build_analytics` ignore `DRYRUN` ; `input/` et `output/` sont communs aux deux modes.
- `DELETE /output/reset` et les jobs lancés en ligne de commande (`./pridec`, `pivot_workflow.sh`) échappent à tous ces contrôles.

---

## 7. Ce qu'on n'ajoute pas

- Ni moteur à états ni librairie de workflow : un dict de prérequis et quelques fonctions pures (`progress`, `launchable`, `dependents`, `resolve_slot`).
- Pas de définition du parcours en base : c'est du code versionné.
- Pas d'état de progression dans Pinia ou localStorage.
- Pas de statut `stale` ou `invalidated` : `done`, `accessible` et `launchable` sont calculés.
- Pas de copie automatique depuis `forecast_assets` : c'est le rôle de la version automatisée (`pivot_workflow.sh`).
- Pas d'expiration du verrou.

---

## 8. Ordre d'implémentation

✅ = fait (socle 2026-10-08 → 09 ; cible 2026-10-09).

1. ✅ `domain/pipeline.py`, `infrastructure/checkpoint_store.py` (`checkpoints`, `pipeline_lock`, `BEGIN IMMEDIATE`).
2. ✅ `CeleryTaskLauncher.launch()` → `start()` ; `_update_task_status` → `finish()`.
3. ✅ `AnalyticsService` et `InputUploadService` passent par `PipelineGate`.
4. ✅ `GET /pipeline/checkpoints`, `DELETE /pipeline/lock`, tests API.
5. ✅ Cycle mensuel, contrôle 422 de `config.json`, `progress()` chaîné (R4), confirmation (R5).
6. ✅ **Définition cible** : `PIPELINE` par prérequis en 3 étapes, `launchable()`, `resolve_slot` pour les
   3 emplacements de `build_analytics`. Expiration du verrou supprimée.
   Migration : les lignes des anciennes étapes ne correspondent à aucun item et sont ignorées ; le cycle en cours
   d'une base de développement repart donc de `data_import`.
7. ✅ **Runs (R6)** : table `forecast_runs`, `POST /pipeline/runs`, `DELETE /pipeline/runs/current`, injection de
   `run_context` (via la config dynamique), vidage de `input/` et `output/`, fermeture par `post_forecast`.
8. ✅ **Fichiers** : `config/<maladie>` comme item (un par maladie), `external_data.csv` par niveau, conservés dans
   `uploads/<cycle>/` et remis dans `input/` à l'ouverture des runs qui les partagent ; remplacement : seul le run ouvert est invalidé.
9. ✅ **Approbation** : `POST /pipeline/runs/current/approve` (approve / reject) ; `post_forecast` exige `approve`.
10. ✅ **Invalidation dans le run** : remise en `pending` des dépendants, et `reset_items` dans `impact`.
11. ✅ **`calc_orgunit_alerts`** : route `POST /calc_orgunit_alerts` en **501** (pas de script) ; l'item existe pour les runs CSB.
12. ✅ **etlui** (`usePipeline`, `ModeToggle` avant l'étape ①, `ForecastRuns`, `ImpactDialog`) : lecture de la route, plus aucun ✓ calculé localement ; choix du couple et ouverture du run ;
    sélecteurs de fichiers sous le couple affiché ; écran d'approbation avec le rapport et l'état du CSV ;
    messages des 409 ; modale de constat sur `confirmation_required` puis renvoi avec `confirm=true`.
13. ✅ **Documentation** : tableau des endpoints, `ARCHITECTURE.md`, `CLAUDE.MD`, `known-issues.md`, guide et diagrammes.
14. ✅ **Bascule de mois automatique** et **mode test** (`PUT /pipeline/mode`, checkpoints en Redis, sortie confirmée).

---

## 9. La phrase à retenir

> **Dans etlhub, on stocke *ce qui s'est passé*
> (un fait par item) et on calcule *où on en est*.**
> Le serveur décide, le client affiche. Une étape ne vaut que si celle d'avant vaut,
> un run à la fois traite un couple de bout en bout, et défaire ce qui était validé
> demande l'accord explicite de l'utilisateur.
