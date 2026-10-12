# Contrôle des checkpoints : diagrammes

Ce document rassemble en schémas tout ce qu'etlhub contrôle (conception cible, 2026-10-09).
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
| R1 | Tout item est obligatoire ; `config.json` est un item par maladie ; `external_data.csv` est facultatif, ce n'est pas un item. |
| R2 | Un item exige que ses prérequis soient en `success`. |
| R3 | Un seul job à la fois. Le verrou n'expire jamais (`DELETE /pipeline/lock`). |
| R4 | Une étape n'est valide que si tous ses items sont en `success` et que la précédente est valide. |
| R5 | Défaire ce qui était validé exige `confirm=true`. |
| R6 | Un seul run de forecast ouvert à la fois. |

---

## 1. Le parcours complet d'un cycle

Légende :
- **Vert** : un item, avec un statut en base.
- **Violet** : un run de forecast, résumé ici ; son détail est dans le diagramme 2.
- **Flèche pleine** : prérequis contrôlé par le serveur (R2).
- **Flèche double** : passage d'une étape à la suivante (R4).

Chaque case de run indique les fichiers d'entrée qu'elle utilise ; les uploads eux-mêmes sont détaillés dans le diagramme 2.

```mermaid
flowchart TB
    START(["Premier lancement du mois<br/>ouvre le cycle = forecast_start (YYYYMM)"])

    subgraph S1["① data_import"]
        direction LR
        gee["import_gee"] --> ba1["build_analytics"]
        pcom["import_pivot_com"] --> ba1
        pcsb["import_pivot_csb"] --> ba1
    end

    subgraph S2["② forecast · 9 runs, un seul ouvert à la fois (R6)"]
        direction TB
        subgraph SADJ["ADJ · OU_LEVEL 6"]
            direction LR
            r1["run ADJ/Malaria<br/>pridec_historic_ADJMalaria<br/>config/Malaria · external_data fkt<br/>7 items"]
            r2["run ADJ/Diarrhea<br/>pridec_historic_ADJDiarrhea<br/>config/Diarrhea · external_data fkt<br/>7 items"]
            r3["run ADJ/Respinf<br/>pridec_historic_ADJRespinf<br/>config/Respinf · external_data fkt<br/>7 items"]
        end
        subgraph SCOM["COM · OU_LEVEL 6"]
            direction LR
            r4["run COM/Malaria<br/>pridec_historic_COMMalaria<br/>config/Malaria · external_data fkt<br/>7 items"]
            r5["run COM/Diarrhea<br/>pridec_historic_COMDiarrhea<br/>config/Diarrhea · external_data fkt<br/>7 items"]
            r6["run COM/Respinf<br/>pridec_historic_COMRespinf<br/>config/Respinf · external_data fkt<br/>7 items"]
        end
        subgraph SCSB["CSB · OU_LEVEL 5 · ALERT_NAME CSB&lt;maladie&gt;Vigilance"]
            direction LR
            r7["run CSB/Malaria<br/>pridec_historic_CSBMalaria<br/>config/Malaria · external_data csb<br/>8 items"]
            r8["run CSB/Diarrhea<br/>pridec_historic_CSBDiarrhea<br/>config/Diarrhea · external_data csb<br/>8 items"]
            r9["run CSB/Respinf<br/>pridec_historic_CSBRespinf<br/>config/Respinf · external_data csb<br/>8 items"]
        end
        SADJ ~~~ SCOM ~~~ SCSB
    end

    subgraph S3["③ system_update · ordre imposé"]
        direction LR
        ba2["build_analytics"] --> alerts["calc_csb_alerts"] --> ba3["build_analytics<br/>(after alerts)"] --> key["update_key"]
    end

    END(["3 étapes valides<br/>cycle fermé jusqu'au mois suivant"])

    START --> S1
    S1 ==>|"étape ① valide (R4)"| S2
    S2 ==>|"9 post_forecast en success (R4)"| S3
    S3 ==> END

    classDef item fill:#e8f5e9,stroke:#2e7d32,color:#1b5e20
    classDef run fill:#ede7f6,stroke:#5e35b1,color:#311b92
    classDef edge fill:#e3f2fd,stroke:#1565c0,color:#0d47a1
    class gee,pcom,pcsb,ba1,ba2,alerts,ba3,key item
    class r1,r2,r3,r4,r5,r6,r7,r8,r9 run
    class START,END edge
```

> **Quand se font les uploads ?** Il n'y a pas d'étape d'upload : les fichiers se téléversent **pendant les runs**,
> un par un. `config/<maladie>` est téléversé dans le **premier run ouvert de cette maladie** (ADJ, COM ou CSB, peu importe),
> puis remis automatiquement dans `input/` pour ses 2 autres runs. Même principe pour `external_data.csv`, facultatif,
> **par niveau** : téléversé dans le premier run du niveau (fokontany : ADJ ou COM ; CSB), puis remis aux autres runs de ce niveau.
> Soit, sur un cycle, 3 uploads de `config.json` à 3 moments différents, et au plus 2 de `external_data.csv`.

### Les 9 runs

| # | Run | `DISEASE_CODE` | `OU_LEVEL` | `ALERT_NAME` | `config.json` | `external_data.csv` | Items du run |
|---|---|---|---|---|---|---|---|
| 1 | `ADJ/Malaria` | `pridec_historic_ADJMalaria` | 6 (fokontany) | — | `config/Malaria` | fkt | 7 |
| 2 | `ADJ/Diarrhea` | `pridec_historic_ADJDiarrhea` | 6 | — | `config/Diarrhea` | fkt | 7 |
| 3 | `ADJ/Respinf` | `pridec_historic_ADJRespinf` | 6 | — | `config/Respinf` | fkt | 7 |
| 4 | `COM/Malaria` | `pridec_historic_COMMalaria` | 6 | — | `config/Malaria` | fkt | 7 |
| 5 | `COM/Diarrhea` | `pridec_historic_COMDiarrhea` | 6 | — | `config/Diarrhea` | fkt | 7 |
| 6 | `COM/Respinf` | `pridec_historic_COMRespinf` | 6 | — | `config/Respinf` | fkt | 7 |
| 7 | `CSB/Malaria` | `pridec_historic_CSBMalaria` | 5 (CSB) | `CSBMalariaVigilance` | `config/Malaria` | csb | 8 |
| 8 | `CSB/Diarrhea` | `pridec_historic_CSBDiarrhea` | 5 | `CSBDiarrheaVigilance` | `config/Diarrhea` | csb | 8 |
| 9 | `CSB/Respinf` | `pridec_historic_CSBRespinf` | 5 | `CSBRespinfVigilance` | `config/Respinf` | csb | 8 |

Au total, l'étape ② compte 69 items : 3 `config/<maladie>` + 6 × 7 + 3 × 8.
Uploads par cycle : 3 `config.json` (obligatoires) et au plus 2 `external_data.csv` (facultatifs).

---

## 2. Un run de forecast

Le même modèle pour les 9 couples. Les flèches sont des prérequis contrôlés (R2).

Légende : **vert** = item ; **bleu** = upload (item) ; **gris pointillé** = upload facultatif ; **jaune** = décision humaine ;
**rouge** = `calc_orgunit_alerts`, présent dans le parcours mais pas encore implémenté (501).
Ce que chaque job lit et écrit :

| Item | Lit | Écrit |
|---|---|---|
| `config/<maladie>` (upload, une fois par maladie) | — | `input/config.json` (`forecast_start` = cycle, sinon 422), conservé et remis pour les autres runs de la maladie |
| `external_data.csv` (upload facultatif, une fois par niveau) | — | `input/external_data.csv`, conservé et remis pour les autres runs du même niveau |
| `fetch_disease` | `DISEASE_CODE`, `OU_LEVEL`, `PARENT_OU` | `input/disease_data.json` |
| `fetch_climate` | `OU_LEVEL`, `PARENT_OU` | `input/climate_data.json` |
| `fetch_geojson` | `OU_LEVEL`, `PARENT_OU` | `input/orgUnit_poly.geojson` |
| `validate_inputs` | les fichiers ci-dessus | `input/config_valid.json`, `input_valid.json`, `polygon_valid.geojson` |
| `forecast` | les 3 fichiers `*_valid` | `output/forecast.json`, `output/forecast_report.html` |
| `calc_orgunit_alerts` (CSB) | `ALERT_NAME` | 501 : pas implémenté |
| `approve` | `output/forecast_report.html` (lu par l'utilisateur) | décision |
| `post_forecast` | `output/forecast.json` | DHIS2 (PRIDE-C) |

```mermaid
flowchart LR
    OPEN(["POST /pipeline/runs<br/>source + disease<br/>vide input/ et output/, remet les fichiers déjà téléversés<br/>fixe DISEASE_CODE, OU_LEVEL, ALERT_NAME"])

    cfg["config.json · config/maladie<br/>(upload si 1er run de la maladie,<br/>sinon déjà remis)"]
    ext["external_data.csv<br/>(facultatif, un par niveau)"]
    fd["fetch_disease"]
    fc["fetch_climate"]
    fg["fetch_geojson"]
    val["validate_inputs"]
    fct["forecast"]
    coa["calc_orgunit_alerts<br/>CSB seulement · 501"]
    apr{"approve<br/>(décision)"}
    post["post_forecast"]
    CLOSE(["run fermé<br/>un autre couple peut s'ouvrir"])

    OPEN --> cfg & fd & fc & fg
    OPEN -.-> ext
    cfg --> val
    fd --> val
    fc --> val
    fg --> val
    ext -.->|"lu s'il est présent"| val
    val --> fct
    fct -->|"ADJ, COM"| apr
    fct -->|"CSB"| coa --> apr
    apr -->|"approve"| post --> CLOSE
    apr -->|"reject : forecast et suite → pending"| fct

    classDef item fill:#e8f5e9,stroke:#2e7d32,color:#1b5e20
    classDef upload fill:#e3f2fd,stroke:#1565c0,color:#0d47a1
    classDef optional fill:#f5f5f5,stroke:#9e9e9e,color:#424242,stroke-dasharray:4 3
    classDef human fill:#fff8e1,stroke:#f9a825,color:#6d4c00
    classDef missing fill:#ffebee,stroke:#c62828,color:#b71c1c
    class fd,fc,fg,val,fct,post item
    class cfg upload
    class ext optional
    class apr human
    class coa missing
```

**Abandonner** (`DELETE /pipeline/runs/current`) : le run passe `abandoned`, ses items repassent en `pending`, rien n'est publié.

**Invalidation dans le run** : relancer ou remplacer un item remet en `pending` tout ce qui en dépend
(par exemple, relancer `fetch_climate` remet `validate_inputs`, `forecast`, … en `pending`).

---

## 3. Le contrôle d'un lancement

Ce chemin s'applique à chaque lancement de job : Celery (`/import_*`, `/fetch_*`, `/validate_inputs`, `/build_analytics`,
`/calc_csb_alerts`, `/forecast/`) ou synchrone (`/post_forecast`, `/update_key`). Tout se passe dans une seule transaction
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
    T -- non --> SL["emplacement : le premier lançable pas en success,<br/>sinon le dernier lançable<br/>(build_analytics : 3 emplacements)"]
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

`POST` et `DELETE /input/files/{config|external_data}`.

```mermaid
flowchart TD
    A(["Upload ou suppression<br/>config.json / external_data.csv"]) --> FS{"Upload de config.json :<br/>forecast_start = cycle ?"}
    FS -- non --> E0["422 · forecast_start does not match the cycle"]
    FS -- "oui, ou autre cas" --> L{"Verrou libre ?"}
    L -- non --> E1["409 · one job at a time"]
    L -- oui --> R{"Run ouvert ?"}
    R -- non --> E2["409 · needs an open forecast run"]
    R -- oui --> V{"Fichier déjà utilisé ?<br/>validate_inputs du run en success,<br/>ou forecast réussi d'un run qui le partage"}
    V -- non --> OK
    V -- oui --> CF{"confirm=true ? (R5)"}
    CF -- non --> E3["409 · confirmation_required + impact"]
    CF -- oui --> OK
    OK["Fichier écrit ou supprimé dans input/ et uploads/cycle/<br/>run ouvert seulement : validate_inputs et suite → pending<br/>(les autres runs gardent leur success)"]
    OK --> K{"Quel fichier ?"}
    K -- config.json --> K1["upload : config/maladie → success<br/>suppression : config/maladie → pending"]
    K -- external_data.csv --> K2["run.external_data = uploaded / none<br/>(pas un item, un fichier par niveau)"]

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
    [*] --> Ouvert : premier lancement du mois<br/>cycle = mois courant = forecast_start
    Ouvert --> Ouvert : lancements et runs du mois
    Ouvert --> Inacheve : changement de mois avant la fin<br/>(run ouvert abandonné)
    Inacheve --> [*] : reste dans l'historique ;<br/>le mois suivant a son propre cycle
    Ouvert --> Ferme : les 3 étapes sont valides
    Ferme --> Ferme : tout lancement du même mois → 409 cycle complete
    Ferme --> [*] : premier lancement du mois suivant<br/>ouvre le cycle suivant
```

Limites :
- `calc_orgunit_alerts` répond 501 : les runs CSB, et donc le cycle, ne peuvent pas se terminer tant qu'il n'est pas implémenté.
- Un cycle non terminé à la fin du mois reste inachevé ; un worker tué bloque tout jusqu'à `DELETE /pipeline/lock`.
- **Mode test** (`DRYRUN=true`, `PUT /pipeline/mode`) : mêmes règles et mêmes schémas, mais les checkpoints sont gardés
  dans Redis seulement ; revenir en production les efface (avec `confirm=true` s'il y en a).
- `DELETE /output/reset` et les jobs lancés en ligne de commande échappent à ces contrôles.
