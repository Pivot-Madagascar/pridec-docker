# Pipeline checkpoints : l'essentiel

etlhub note ce qui a **vraiment réussi** dans le pipeline du mois, et **refuse** ce qui sort des règles
(conception cible, révisée le 2026-10-12 ; le code suit encore la version du 2026-10-09).
Le workflow lui-même suit la documentation de référence (`pivot_forecast.sh`), qui fait foi.
Plus de détails : [guide](pipeline-checkpoints-guide.md) · [diagrammes](pipeline-checkpoints-diagrams.md) · [conception](pipeline-checkpoints.md).

## Le cycle

- **1 cycle = le pipeline complet, 1 fois par mois**, nommé par le mois (ex. `202610`).
- Il **s'ouvre** au premier lancement du mois.
- Au **changement de mois**, un nouveau cycle commence tout seul. L'ancien, s'il n'est pas fini, reste inachevé
  (on le garde dans l'historique) et son run ouvert est abandonné.
- Il **se ferme** quand les 3 étapes sont validées : l'application PRIDE-C est à jour. Le même mois ne peut pas tourner deux fois.

## Les 3 étapes

| Étape | À réussir | Ordre |
|---|---|---|
| ① `data_import` | `import_gee`, `import_pivot_com`, `import_pivot_csb`, la décision `approve_imports` (cas COM < 100, cas CSB < limite), puis `build_analytics` | Imports libres, `approve_imports` après les imports pivot, `build_analytics` en dernier |
| ② `forecast` | **9 runs** : ADJ, COM, CSB × Malaria, Diarrhea, Respinf | Runs dans l'ordre voulu, **un seul ouvert à la fois** |
| ③ `system_update` | `build_analytics` → `update_key` | Imposé |

`build_analytics` doit passer par l'API etlhub : lancé depuis DHIS2, il n'est pas vu et l'étape ① reste non valide.

## Un run de forecast (étape ②)

1. **Ouvrir** le run d'un couple (`POST /pipeline/runs`). Le serveur vide `input/` et `output/`, remet les fichiers déjà
   téléversés, puis fixe tout seul `DISEASE_CODE`, `OU_LEVEL` (6 pour ADJ/COM, 5 pour CSB) et `ALERT_NAME` (CSB).
2. **Fichiers**, depuis l'interface, **tous obligatoires** :
   - `config.json` : **1 par maladie** (`config_malaria.json`, `config_diarrhea.json`, `config_respiratory.json`).
     On le téléverse au premier run de la maladie ; les 2 autres runs le reçoivent automatiquement.
     Le serveur y écrit `forecast_start`.
   - `external_data.csv` : **1 par niveau** (fokontany ou CSB), même principe. Un fichier du mauvais niveau est refusé (422).
   - Les fichiers de `forecast_assets/` servent de modèles.
3. **Jobs** : `fetch_disease`, `fetch_climate`, `fetch_geojson` → `validate_inputs` → `forecast`
   → `calc_orgunit_alerts` (CSB seulement).
4. **Décider** : lire le rapport, puis `approve` (ou `reject` pour refaire le forecast).
5. **Publier** : `post_forecast`. Le run se **ferme** et un autre couple peut s'ouvrir.

On peut **abandonner** un run à tout moment : rien n'est publié, et ses étapes repartent à zéro.

## Les règles

| | Règle | Si elle n'est pas respectée |
|---|---|---|
| **R1** | Tout est obligatoire, `external_data.csv` compris. | L'étape ne se valide pas. |
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

## Mode test

Le bouton **« Mode test » (test = OUI)** d'etlui bascule etlhub en mode test (`PUT /pipeline/mode` `{"dry_run": true | false}`).
- Ce mode passe `DRYRUN=True` à `import_gee` (import partiel rapide) et à `post_forecast` (rien n'est écrit dans PRIDE-C).
  À ne pas confondre avec l'option `DRYRUN` de chaque commande `pridec`, dont l'effet varie selon la commande.
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

- **Le code n'applique pas encore la révision du 2026-10-12** : voir l'état en tête de [pipeline-checkpoints.md](pipeline-checkpoints.md).
- **Interface** (etlui) : branchée depuis le 2026-10-09 ; elle n'a pas été testée contre un vrai etlhub, seulement avec une API simulée. Le tableau de bord d'etlui n'a plus de bouton « reset output » (`DELETE /output/reset` reste disponible dans l'API).
- Un cycle qui n'est pas fini à la fin du mois reste inachevé : rien ne le termine à sa place.
- `DELETE /output/reset` et la ligne de commande (`./pridec`) échappent à ces contrôles.
- Points ouverts : valeur de `forecast_start`, limite CSB d'`approve_imports`, nature de `calc_orgunit_alerts`,
  colonnes qui distinguent fkt et csb, config du mode test ([diagrammes](pipeline-checkpoints-diagrams.md#points-ouverts)).
