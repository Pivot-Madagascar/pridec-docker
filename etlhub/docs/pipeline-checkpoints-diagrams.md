# Contrôle des checkpoints : diagrammes

Ce document rassemble en schémas tout ce qu'etlhub contrôle (conception cible, révisée le 2026-10-12).
Le workflow (3 phases, commandes `pridec`, ordre des étapes) suit la **documentation de référence** (`pivot_forecast.sh`), qui fait foi ;
ce document n'ajoute que la couche de contrôle d'etlhub par-dessus (verrou, checkpoints, cycles, confirmations).
Les règles sont résumées dans [pipeline-checkpoints-guide.md](pipeline-checkpoints-guide.md),
et la conception complète est dans [pipeline-checkpoints.md](pipeline-checkpoints.md).

| # | Diagramme | Question |
|---|---|---|
| 1 | Le parcours complet | Quelles étapes, quels items, et les 9 runs de forecast en détail ? |
| 2 | Un run de forecast | Comment un couple va-t-il de l'ouverture à `post_forecast` ? |
| 3 | Le contrôle d'un lancement | Que vérifie le serveur avant d'accepter un job ? |
| 4 | Les fichiers d'entrée | Que se passe-t-il quand on téléverse ou supprime `config.json` ou `external_data.csv` ? |
| 5 | La vie d'un item | Comment passe-t-on de `pending` à `success`, et comment en revient-on ? |
| 6 | La vie d'un run et d'un cycle | Quand s'ouvrent-ils et quand se ferment-ils ? |

| Règle | Contenu |
|---|---|
| R1 | Tout item est obligatoire ; `config.json` est un item par maladie ; `external_data.csv` est un item par niveau (fkt, csb). Les deux se téléversent depuis l'interface. |
| R2 | Un item exige que ses prérequis soient en `success`. |
| R3 | Un seul job à la fois. Le verrou n'expire jamais (`DELETE /pipeline/lock`). |
| R4 | Une étape n'est valide que si tous ses items sont en `success` et que la précédente est valide. |
| R5 | Défaire ce qui était validé exige `confirm=true`. |
| R6 | Un seul run de forecast ouvert à la fois. |

---

## 1. Le parcours complet d'un cycle

Légende :
- **Vert** : un item, avec un statut en base.
- **Jaune** : une décision humaine (item).
- **Violet** : un run de forecast, résumé ici ; son détail est dans le diagramme 2.
- **Flèche pleine** : prérequis contrôlé par le serveur (R2).
- **Flèche double** : passage d'une étape à la suivante (R4).

Chaque case de run indique les fichiers d'entrée qu'elle utilise ; les uploads eux-mêmes sont détaillés dans le diagramme 2.

```mermaid
flowchart TB
    START(["Premier lancement du mois<br/>ouvre le cycle (YYYYMM)"])

    subgraph S1["① data_import · 5 items"]
        direction LR
        gee["import_gee"] --> ba1["build_analytics"]
        pcom["import_pivot_com"] --> chk
        pcsb["import_pivot_csb"] --> chk
        chk{"approve_imports<br/>(décision : cas COM &lt; 100,<br/>cas CSB &lt; limite)"} --> ba1
    end

    subgraph S2["② forecast · 9 runs, un seul ouvert à la fois (R6) · 71 items"]
        direction TB
        subgraph SADJ["ADJ · OU_LEVEL 6"]
            direction LR
            r1["run ADJ/Malaria<br/>pridec_historic_ADJMalaria<br/>config_malaria.json · external_data/fkt<br/>7 items"]
            r2["run ADJ/Diarrhea<br/>pridec_historic_ADJDiarrhea<br/>config_diarrhea.json · external_data/fkt<br/>7 items"]
            r3["run ADJ/Respinf<br/>pridec_historic_ADJRespinf<br/>config_respiratory.json · external_data/fkt<br/>7 items"]
        end
        subgraph SCOM["COM · OU_LEVEL 6"]
            direction LR
            r4["run COM/Malaria<br/>pridec_historic_COMMalaria<br/>config_malaria.json · external_data/fkt<br/>7 items"]
            r5["run COM/Diarrhea<br/>pridec_historic_COMDiarrhea<br/>config_diarrhea.json · external_data/fkt<br/>7 items"]
            r6["run COM/Respinf<br/>pridec_historic_COMRespinf<br/>config_respiratory.json · external_data/fkt<br/>7 items"]
        end
        subgraph SCSB["CSB · OU_LEVEL 5 · ALERT_NAME CSB&lt;maladie&gt;Vigilance"]
            direction LR
            r7["run CSB/Malaria<br/>pridec_historic_CSBMalaria<br/>config_malaria.json · external_data/csb<br/>8 items"]
            r8["run CSB/Diarrhea<br/>pridec_historic_CSBDiarrhea<br/>config_diarrhea.json · external_data/csb<br/>8 items"]
            r9["run CSB/Respinf<br/>pridec_historic_CSBRespinf<br/>config_respiratory.json · external_data/csb<br/>8 items"]
        end
        SADJ ~~~ SCOM ~~~ SCSB
    end

    subgraph S3["③ system_update · 2 items"]
        direction LR
        ba2["build_analytics"] --> key["update_key"]
    end

    END(["3 étapes valides<br/>cycle fermé jusqu'au mois suivant<br/>application PRIDE-C à jour"])

    START --> S1
    S1 ==>|"étape ① valide (R4)"| S2
    S2 ==>|"9 post_forecast en success (R4)"| S3
    S3 ==> END

    classDef item fill:#e8f5e9,stroke:#2e7d32,color:#1b5e20
    classDef human fill:#fff8e1,stroke:#f9a825,color:#6d4c00
    classDef run fill:#ede7f6,stroke:#5e35b1,color:#311b92
    classDef edge fill:#e3f2fd,stroke:#1565c0,color:#0d47a1
    class gee,pcom,pcsb,ba1,ba2,key item
    class chk human
    class r1,r2,r3,r4,r5,r6,r7,r8,r9 run
    class START,END edge
```

> **Quand se font les uploads ?** Il n'y a pas d'étape d'upload : les fichiers se téléversent depuis l'interface **pendant les runs**,
> un par un, et ils sont **tous obligatoires**. `config.json` est téléversé dans le **premier run ouvert de la maladie** (ADJ, COM ou CSB, peu importe),
> puis remis automatiquement dans `input/` pour ses 2 autres runs ; le serveur y écrit `forecast_start`, comme le fait `jq` dans `pivot_forecast.sh`.
> Même principe pour `external_data.csv`, **par niveau** : téléversé dans le premier run du niveau (fokontany : ADJ ou COM ; CSB), puis remis aux autres runs de ce niveau.
> Soit, sur un cycle, 3 uploads de `config.json` et 2 de `external_data.csv`. Les fichiers de `forecast_assets/` du dépôt servent de modèles.

> **`build_analytics`** doit passer par l'API etlhub. Lancé à la main depuis l'interface DHIS2, etlhub ne le voit pas et l'étape ① reste non valide.

### Les 9 runs

| # | Run | `DISEASE_CODE` | `OU_LEVEL` | `ALERT_NAME` | Item config (fichier attendu) | Item external_data | Items du run |
|---|---|---|---|---|---|---|---|
| 1 | `ADJ/Malaria` | `pridec_historic_ADJMalaria` | 6 (fokontany) | — | `config/Malaria` (`config_malaria.json`) | `external_data/fkt` | 7 |
| 2 | `ADJ/Diarrhea` | `pridec_historic_ADJDiarrhea` | 6 | — | `config/Diarrhea` (`config_diarrhea.json`) | `external_data/fkt` | 7 |
| 3 | `ADJ/Respinf` | `pridec_historic_ADJRespinf` | 6 | — | `config/Respinf` (`config_respiratory.json`) | `external_data/fkt` | 7 |
| 4 | `COM/Malaria` | `pridec_historic_COMMalaria` | 6 | — | `config/Malaria` (`config_malaria.json`) | `external_data/fkt` | 7 |
| 5 | `COM/Diarrhea` | `pridec_historic_COMDiarrhea` | 6 | — | `config/Diarrhea` (`config_diarrhea.json`) | `external_data/fkt` | 7 |
| 6 | `COM/Respinf` | `pridec_historic_COMRespinf` | 6 | — | `config/Respinf` (`config_respiratory.json`) | `external_data/fkt` | 7 |
| 7 | `CSB/Malaria` | `pridec_historic_CSBMalaria` | 5 (CSB) | `CSBMalariaVigilance` | `config/Malaria` (`config_malaria.json`) | `external_data/csb` | 8 |
| 8 | `CSB/Diarrhea` | `pridec_historic_CSBDiarrhea` | 5 | `CSBDiarrheaVigilance` | `config/Diarrhea` (`config_diarrhea.json`) | `external_data/csb` | 8 |
| 9 | `CSB/Respinf` | `pridec_historic_CSBRespinf` | 5 | `CSBRespinfVigilance` | `config/Respinf` (`config_respiratory.json`) | `external_data/csb` | 8 |

L'interface d'upload affiche le fichier attendu pour chaque maladie (en particulier `config_respiratory.json` pour `Respinf`).

Au total, l'étape ② compte 71 items : 3 `config/<maladie>` + 2 `external_data/<niveau>` + 6 × 7 + 3 × 8.
Uploads par cycle : 3 `config.json` et 2 `external_data.csv`, tous obligatoires.

---

## 2. Un run de forecast

Le même modèle pour les 9 couples. Les flèches sont des prérequis contrôlés (R2).

Légende : **vert** = item ; **bleu** = upload (item) ; **jaune** = décision humaine.
Ce que chaque job lit et écrit :

| Item | Lit | Écrit |
|---|---|---|
| `config/<maladie>` (upload, une fois par maladie) | — | `input/config.json`, avec `forecast_start` écrit par le serveur ; conservé et remis pour les autres runs de la maladie |
| `external_data/<niveau>` (upload, une fois par niveau) | — | `input/external_data.csv`, conservé et remis pour les autres runs du même niveau |
| `fetch_disease` | `DISEASE_CODE`, `OU_LEVEL`, `PARENT_OU` | `input/disease_data.json` |
| `fetch_climate` | `OU_LEVEL`, `PARENT_OU` | `input/climate_data.json` |
| `fetch_geojson` | `OU_LEVEL`, `PARENT_OU` | `input/orgUnit_poly.geojson` |
| `validate_inputs` | les fichiers ci-dessus | `input/config_valid.json`, `input_valid.json`, `polygon_valid.geojson` |
| `forecast` | les 3 fichiers `*_valid` | `output/forecast.json`, `output/forecast_report.html` |
| `calc_orgunit_alerts` (CSB) | `ALERT_NAME` | seuils d'alerte (commande CLI `pridec etl calc_orgUnit_alerts`) |
| `approve` | `output/forecast_report.html` (lu par l'utilisateur) | décision |
| `post_forecast` | `output/forecast.json` | DHIS2 (PRIDE-C) |

```mermaid
flowchart LR
    OPEN(["POST /pipeline/runs<br/>source + disease<br/>vide input/ et output/, remet les fichiers déjà téléversés<br/>fixe DISEASE_CODE, OU_LEVEL, ALERT_NAME"])

    cfg["config.json · config/maladie<br/>(upload si 1er run de la maladie,<br/>sinon déjà remis)<br/>forecast_start écrit par le serveur"]
    ext["external_data.csv · external_data/niveau<br/>(upload si 1er run du niveau,<br/>sinon déjà remis)"]
    fd["fetch_disease"]
    fc["fetch_climate"]
    fg["fetch_geojson"]
    val["validate_inputs"]
    fct["forecast"]
    coa["calc_orgunit_alerts<br/>CSB seulement"]
    apr{"approve<br/>(décision)"}
    post["post_forecast"]
    CLOSE(["run fermé<br/>un autre couple peut s'ouvrir"])

    OPEN --> cfg & ext & fd & fc & fg
    cfg --> val
    ext --> val
    fd --> val
    fc --> val
    fg --> val
    val --> fct
    fct -->|"ADJ, COM"| apr
    fct -->|"CSB"| coa --> apr
    apr -->|"approve"| post --> CLOSE
    apr -->|"reject : forecast et suite → pending"| fct

    classDef item fill:#e8f5e9,stroke:#2e7d32,color:#1b5e20
    classDef upload fill:#e3f2fd,stroke:#1565c0,color:#0d47a1
    classDef human fill:#fff8e1,stroke:#f9a825,color:#6d4c00
    class fd,fc,fg,val,fct,coa,post item
    class cfg,ext upload
    class apr human
```

**Abandonner** (`DELETE /pipeline/runs/current`) : le run passe `abandoned`, ses items repassent en `pending`, rien n'est publié.

**Invalidation dans le run** : relancer ou remplacer un item remet en `pending` tout ce qui en dépend
(par exemple, relancer `fetch_climate` remet `validate_inputs`, `forecast`, … en `pending`).

---

## 3. Le contrôle d'un lancement

Ce chemin s'applique à chaque lancement de job : Celery (`/import_*`, `/fetch_*`, `/validate_inputs`, `/build_analytics`,
`/forecast/`), synchrone (`/post_forecast`, `/update_key`), et `/calc_orgunit_alerts`. Tout se passe dans une seule transaction
SQLite (`BEGIN IMMEDIATE`) ; un refus n'écrit rien.

```mermaid
flowchart TD
    A(["Lancement d'un job"]) --> L{"Verrou libre ? (R3)"}
    L -- non --> E1["409 · one job at a time<br/>(jamais d'expiration : DELETE /pipeline/lock)"]
    L -- oui --> C{"Quel cycle ?"}
    C -- "cycle du mois en cours" --> C1["cycle du mois<br/>(un run ouvert d'un mois précédent est abandonné)"]
    C -- "nouveau mois (l'ancien cycle, fini ou non, reste tel quel)" --> C2["nouveau cycle = mois courant"]
    C -- "dernier fini ce mois-ci" --> E2["409 · cycle complete"]
    C1 --> T
    C2 --> T
    T{"Job d'un run ?<br/>(fetch_*, validate_inputs, forecast,<br/>calc_orgunit_alerts, post_forecast)"}
    T -- oui --> R{"Run ouvert ? (R6)"}
    R -- non --> E3["409 · needs an open forecast run"]
    R -- oui --> RI["item = couple du run : job"]
    T -- non --> SL["emplacement : le premier lançable pas en success,<br/>sinon le dernier lançable<br/>(build_analytics : 2 emplacements)"]
    RI --> P
    SL --> P
    P{"Étape accessible (R4)<br/>et prérequis en success (R2) ?"}
    P -- non --> E4["409 · needs … first"]
    P -- oui --> S{"Item déjà en success ?"}
    S -- non --> OK
    S -- oui --> CF{"confirm=true ? (R5)"}
    CF -- non --> E5["409 · confirmation_required<br/>+ impact (rien n'est écrit)"]
    CF -- oui --> OK
    OK["Dépendants du run → pending<br/>verrou pris · item → running<br/>job d'un run : contexte écrit dans la config dynamique"]
    OK --> J["Le job s'exécute"]
    J --> FIN{"Fin du job"}
    FIN -- succès --> SUC["item → success · verrou rendu<br/>post_forecast : run fermé"]
    FIN -- échec --> ERR["item → error · verrou rendu"]

    classDef refuse fill:#ffebee,stroke:#c62828,color:#b71c1c
    classDef accept fill:#e8f5e9,stroke:#2e7d32,color:#1b5e20
    class E1,E2,E3,E4,E5 refuse
    class OK,SUC accept
```

**Ouvrir un run** (`POST /pipeline/runs`) suit les mêmes premières vérifications (verrou, cycle), puis :
étape ② accessible, aucun run ouvert (sinon 409), et `confirm=true` si le couple a déjà un run fermé dans le cycle.

---

## 4. Les fichiers d'entrée

`POST` et `DELETE /input/files/{config|external_data}`, depuis l'interface.

```mermaid
flowchart TD
    A(["Upload ou suppression<br/>config.json / external_data.csv"]) --> L{"Verrou libre ?"}
    L -- non --> E1["409 · one job at a time"]
    L -- oui --> R{"Run ouvert ?"}
    R -- non --> E2["409 · needs an open forecast run"]
    R -- oui --> LV{"Upload de external_data.csv :<br/>fichier conforme au niveau du run ?"}
    LV -- non --> E0["422 · file does not match the run level"]
    LV -- "oui, ou autre cas" --> V{"Fichier déjà utilisé ?<br/>validate_inputs du run en success,<br/>ou forecast réussi d'un run qui le partage"}
    V -- non --> OK
    V -- oui --> CF{"confirm=true ? (R5)"}
    CF -- non --> E3["409 · confirmation_required + impact"]
    CF -- oui --> OK
    OK["Upload de config.json : forecast_start écrit par le serveur<br/>Fichier écrit ou supprimé dans input/ et uploads/cycle/<br/>run ouvert seulement : validate_inputs et suite → pending<br/>(les autres runs gardent leur success)"]
    OK --> K{"Quel fichier ?"}
    K -- config.json --> K1["upload : config/maladie → success<br/>suppression : config/maladie → pending"]
    K -- external_data.csv --> K2["upload : external_data/niveau → success<br/>suppression : external_data/niveau → pending"]

    classDef refuse fill:#ffebee,stroke:#c62828,color:#b71c1c
    class E0,E1,E2,E3 refuse
```

---

## 5. La vie d'un item

```mermaid
stateDiagram-v2
    [*] --> pending
    pending --> running : lancement accepté (verrou, prérequis, run)
    error --> running : relance, sans confirmation
    success --> running : relance avec confirm=true (R5)
    running --> success : job terminé
    running --> error : job en échec, ou DELETE /pipeline/lock
    success --> pending : un prérequis du run est relancé ou remplacé
    success --> pending : rejet du forecast, abandon du run, réouverture du couple
    error --> pending : un prérequis du run est relancé, ou abandon du run
```

L'**étape** n'est pas un état stocké : elle est recalculée à chaque lecture.

```mermaid
flowchart LR
    A["Tous les items de l'étape en success ?"] -- non --> N["étape non valide<br/>étapes suivantes : non accessibles"]
    A -- oui --> B["Étape précédente valide ?"]
    B -- non --> N
    B -- oui --> V["étape valide (done)<br/>étape suivante : accessible"]
```

Entre étapes, rien n'est remis à zéro : si l'étape ① redevient non valide, les `success` de l'étape ② restent
en base et comptent de nouveau dès que l'étape ① est revalidée.

---

## 6. La vie d'un run et d'un cycle

```mermaid
stateDiagram-v2
    [*] --> open : POST /pipeline/runs (aucun autre run ouvert)
    open --> closed : post_forecast en success
    open --> abandoned : DELETE /pipeline/runs/current
    closed --> open : réouverture avec confirm=true (items remis à pending)
    abandoned --> open : réouverture, sans confirmation
```

```mermaid
stateDiagram-v2
    [*] --> Ouvert : premier lancement du mois<br/>cycle = mois courant
    Ouvert --> Ouvert : lancements et runs du mois
    Ouvert --> Inacheve : changement de mois avant la fin<br/>(run ouvert abandonné)
    Inacheve --> [*] : reste dans l'historique ;<br/>le mois suivant a son propre cycle
    Ouvert --> Ferme : les 3 étapes sont valides
    Ferme --> Ferme : tout lancement du même mois → 409 cycle complete
    Ferme --> [*] : premier lancement du mois suivant<br/>ouvre le cycle suivant
```

Limites :
- Un cycle non terminé à la fin du mois reste inachevé ; un worker tué bloque tout jusqu'à `DELETE /pipeline/lock`.
- **Mode test** (`PUT /pipeline/mode`) : mêmes règles et mêmes schémas ; les checkpoints sont gardés dans Redis seulement,
  et revenir en production les efface (avec `confirm=true` s'il y en a). Ce mode passe `DRYRUN=True` à `import_gee`
  (import partiel rapide) et à `post_forecast` (aucune écriture dans PRIDE-C). À ne pas confondre avec l'option `DRYRUN`
  de chaque commande `pridec`, dont l'effet varie d'une commande à l'autre.
- `DELETE /output/reset` et les jobs lancés en ligne de commande échappent à ces contrôles.

---

## Points ouverts

| Point | Question |
|---|---|
| `forecast_start` | Quelle valeur `jq` écrit-il dans `pivot_forecast.sh` (mois courant, mois suivant, dernier mois de données) ? Le serveur doit écrire la même. |
| `approve_imports` | Quelle est la limite pour les cas CSB ? |
| Mode test et `forecast` | Le mode test doit-il utiliser `forecast_assets/test_config.json` (Ranger + Naive) ? |
| `calc_orgunit_alerts` | Job Celery ou synchrone ? Que publie-t-il exactement ? |
| Contrôle de niveau de `external_data` | Quelles colonnes distinguent un fichier fkt d'un fichier csb ? |

## Changements depuis la version du 2026-10-09

- Phase 3 alignée sur la référence : `build_analytics` → `update_key` (`calc_csb_alerts` et le second `build_analytics` retirés).
- `calc_orgunit_alerts` actif dans les runs CSB (plus de 501).
- `external_data.csv` obligatoire, désormais un item par niveau ; l'étape ② passe à 71 items.
- `forecast_start` écrit par le serveur à l'upload de `config.json`, au lieu d'un refus 422.
- Contrôle de niveau à l'upload de `external_data.csv`.
- Fichier de config attendu affiché par maladie (`config_respiratory.json` pour `Respinf`).
- Décision `approve_imports` ajoutée en phase 1 ; `build_analytics` uniquement par l'API.
- Mode test distingué de l'option `DRYRUN` des commandes.
