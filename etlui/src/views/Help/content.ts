// Text of the Help page, one entry per language. Static, trusted HTML (<strong> only): rendered with v-html.
// Source: etlhub/docs/decision-design (cycle-passes, pipeline-checkpoints, mode-isolation). Keep both languages in line.
export type Lang = 'en' | 'fr'
type Term = { id: string; term: string; def: string } // id: same anchor (#term-<id>) in both languages

export const HELP: Record<Lang, {
  description: string; howTitle: string; how: string[]; steps: string[]; rules: string; glossaryTitle: string; glossary: Term[]
}> = {
  en: {
    description: 'How the application works, and the words it uses.',
    howTitle: 'How it works',
    how: [
      '<strong>Log in</strong> with your DHIS2 account, then choose the <strong>mode</strong>: Test (nothing is written to DHIS2) or Production (real writes).',
      '<strong>Start a pass</strong>: pick the cycle (the month), then Start, or resume a paused pass of that month.',
      'On <strong>Forecast</strong>, work through the 3 steps in order:',
      'The pass is <strong>complete</strong> when the 3 steps are done. You can pause it and resume it later, or abandon it.',
      'Follow your work in the job toasts, Recent Activity, the <strong>Journal</strong> (history of a pass), <strong>Tracking</strong> (every request) and <strong>Logs</strong>.'
    ],
    steps: [
      '① <strong>Data Import</strong>: import GEE and Pivot data, review and approve it, then Build Analytics.',
      '② <strong>Forecasts</strong>: one run per disease and level. Open it, provide its input files, fetch the data, run the data check and the forecast, read and approve the report, publish it.',
      '③ <strong>System Update</strong>: Build Analytics, then Update Key.'
    ],
    rules: 'etlhub enforces the order: an action stays unavailable, or is refused with a message, until what it needs has succeeded. Only one job runs at a time. Undoing something that already succeeded asks for a confirmation first.',
    glossaryTitle: 'Glossary',
    glossary: [
      { id: 'abandon', term: 'Abandon', def: 'Stops a pass or a run for good. An abandoned pass cannot be resumed; the month can be redone in a new pass. An abandoned run starts again from zero, the pass goes on.' },
      { id: 'approval', term: 'Approval', def: 'Your decision before data is written: in Data Import, which fetched Pivot data elements to post; in a run, approve or reject the forecast report before its publication.' },
      { id: 'confirmation', term: 'Confirmation', def: 'Asked when an action would undo something that succeeded (relaunch it, replace a file already used, start a new pass…). The dialog shows what will be lost.' },
      { id: 'cycle', term: 'Cycle', def: 'The whole pipeline for one month, named after it (e.g. 202610). A cycle can have several passes.' },
      { id: 'default-file', term: 'Default file', def: 'The file offered by "Use default" for an input file, kept with the application. You can preview it before using it.' },
      { id: 'dry-run', term: 'Dry run (DRYRUN)', def: 'The scripts run without writing to DHIS2. It follows the mode: on in Test, off in Production.' },
      { id: 'gee', term: 'GEE', def: 'Google Earth Engine, the source of the climate variables imported in Data Import. You choose the variables in the Import GEE dialog.' },
      { id: 'input-file', term: 'Input file', def: 'A file a run needs: the config (parameters of a disease\'s forecast) and the external data of a level. Shared by the runs of that disease or level.' },
      { id: 'item', term: 'Item', def: 'One unit of work inside a step, with its own status: an import, an input file, a fetch, the forecast, an approval, a publication…' },
      { id: 'job', term: 'Job', def: 'One execution of a script, launched by a button (import, fetch, forecast…). It runs in the background; its toast, its logs and Recent Activity show how it goes.' },
      { id: 'job-lock', term: 'Job lock', def: 'Only one job runs at a time, for every user and both modes. The lock never expires: if a job crashed, release it at the bottom of the Journal.' },
      { id: 'journal', term: 'Journal', def: 'The history of one pass: every event (start, launch, success, error, approval, pause…), who did it and when, with the request and the job logs behind it. Exportable as CSV.' },
      { id: 'level', term: 'Level', def: 'The kind of health site a run forecasts for: ADJ (Adjusted), COM (Community sites) or CSB (Health Centres).' },
      { id: 'logs', term: 'Logs', def: 'The lines a job writes while it runs. Read them in a job\'s detail (Recent Activity, Tracking, Journal) or live on the Logs page. A forecast\'s logs arrive only at its end.' },
      { id: 'mode', term: 'Mode', def: 'Test or Production, chosen by each user. Test writes nothing to DHIS2 and keeps its passes, journals and files apart; Production writes for real. Each mode sees only its own passes.' },
      { id: 'pass', term: 'Pass', def: 'One attempt at a cycle, with its own id and journal. It is active, paused, complete or abandoned. A complete or abandoned pass is frozen: redoing the month starts a new pass.' },
      { id: 'pause-resume', term: 'Pause / Resume', def: 'Pause stops an active pass to continue it later, its state kept. Resume it from Start a pass or from the Journal.' },
      { id: 'recent-activity', term: 'Recent Activity', def: 'The jobs launched from the Forecast page since you opened it, with their result and a link to their request and logs.' },
      { id: 'request', term: 'Request', def: 'One call from this application to etlhub. Tracking lists them with their status and duration; a request that launched a job links to its logs.' },
      { id: 'run', term: 'Run', def: 'In Forecasts, the forecast of one disease at one level. Only one run is open at a time; publishing it closes it. Opening a run empties the server\'s working input and output folders.' },
      { id: 'status', term: 'Status', def: 'The state of an item, decided by etlhub: Pending (not done), Running, Success (counts) or Error (to relaunch).' },
      { id: 'step', term: 'Step', def: 'One of the 3 stages of a pass, done in order: ① Data Import, ② Forecasts, ③ System Update. A step only counts when the previous one counts.' },
      { id: 'test-mode', term: 'Test mode', def: 'See Mode and Dry run.' },
      { id: 'update-key', term: 'Update Key', def: 'Last action of System Update: it writes PRIDE-C\'s update key in the DHIS2 datastore. Refused in Test mode.' }
    ]
  },
  fr: {
    description: 'Comment fonctionne l\'application, et les mots qu\'elle emploie.',
    howTitle: 'Fonctionnement',
    how: [
      '<strong>Connectez-vous</strong> avec votre compte DHIS2, puis choisissez le <strong>mode</strong> : Test (rien n\'est écrit dans DHIS2) ou Production (écritures réelles).',
      '<strong>Démarrez une pass</strong> (Start a pass) : choisissez le cycle (le mois), puis Start, ou reprenez une pass en pause de ce mois.',
      'Sur <strong>Forecast</strong>, suivez les 3 étapes dans l\'ordre :',
      'La pass est <strong>terminée</strong> (complete) quand les 3 étapes sont faites. Vous pouvez la mettre en pause pour la reprendre plus tard, ou l\'abandonner.',
      'Suivez votre travail dans les notifications des jobs, Recent Activity, le <strong>Journal</strong> (historique d\'une pass), <strong>Tracking</strong> (chaque requête) et <strong>Logs</strong>.'
    ],
    steps: [
      '① <strong>Data Import</strong> : importez les données GEE et Pivot, vérifiez-les et approuvez-les, puis Build Analytics.',
      '② <strong>Forecasts</strong> : un run par maladie et par niveau. Ouvrez-le, fournissez ses fichiers d\'entrée, récupérez les données, lancez la vérification des données et la prévision, lisez et approuvez le rapport, publiez-le.',
      '③ <strong>System Update</strong> : Build Analytics, puis Update Key.'
    ],
    rules: 'etlhub impose l\'ordre : une action reste indisponible, ou est refusée avec un message, tant que ce dont elle dépend n\'a pas réussi. Un seul job tourne à la fois. Défaire ce qui a déjà réussi demande d\'abord une confirmation.',
    glossaryTitle: 'Glossaire',
    glossary: [
      { id: 'abandon', term: 'Abandon (abandonner)', def: 'Arrête une pass ou un run définitivement. Une pass abandonnée ne peut pas être reprise ; le mois peut être refait dans une nouvelle pass. Un run abandonné repart de zéro, la pass continue.' },
      { id: 'approval', term: 'Approval (approbation)', def: 'Votre décision avant toute écriture : dans Data Import, quels data elements Pivot récupérés publier ; dans un run, approuver ou rejeter le rapport de prévision avant sa publication.' },
      { id: 'confirmation', term: 'Confirmation', def: 'Demandée quand une action défait ce qui a réussi (la relancer, remplacer un fichier déjà utilisé, démarrer une nouvelle pass…). La fenêtre montre ce qui sera perdu.' },
      { id: 'cycle', term: 'Cycle', def: 'L\'ensemble du pipeline pour un mois, nommé d\'après lui (ex. 202610). Un cycle peut avoir plusieurs passes.' },
      { id: 'default-file', term: 'Default file (fichier par défaut)', def: 'Le fichier proposé par « Use default » pour un fichier d\'entrée, livré avec l\'application. Vous pouvez le prévisualiser avant de l\'utiliser.' },
      { id: 'dry-run', term: 'Dry run (DRYRUN)', def: 'Les scripts tournent sans écrire dans DHIS2. Il suit le mode : actif en Test, inactif en Production.' },
      { id: 'gee', term: 'GEE', def: 'Google Earth Engine, la source des variables climatiques importées dans Data Import. Vous choisissez les variables dans la fenêtre Import GEE.' },
      { id: 'input-file', term: 'Input file (fichier d\'entrée)', def: 'Un fichier dont un run a besoin : la config (paramètres de la prévision d\'une maladie) et les données externes d\'un niveau. Partagé par les runs de cette maladie ou de ce niveau.' },
      { id: 'item', term: 'Item', def: 'Une unité de travail dans une étape, avec son propre statut : un import, un fichier d\'entrée, une récupération de données, la prévision, une approbation, une publication…' },
      { id: 'job', term: 'Job', def: 'Une exécution d\'un script, lancée par un bouton (import, récupération, prévision…). Il tourne en arrière-plan ; sa notification, ses logs et Recent Activity montrent son avancement.' },
      { id: 'job-lock', term: 'Job lock (verrou)', def: 'Un seul job tourne à la fois, pour tous les utilisateurs et les deux modes. Le verrou n\'expire jamais : si un job a planté, libérez-le en bas du Journal.' },
      { id: 'journal', term: 'Journal', def: 'L\'historique d\'une pass : chaque événement (démarrage, lancement, succès, erreur, approbation, pause…), qui l\'a fait et quand, avec la requête et les logs du job correspondants. Exportable en CSV.' },
      { id: 'level', term: 'Level (niveau)', def: 'Le type de site de santé pour lequel un run fait sa prévision : ADJ (Adjusted, ajusté), COM (Community sites, sites communautaires) ou CSB (Health Centres, centres de santé de base).' },
      { id: 'logs', term: 'Logs', def: 'Les lignes qu\'un job écrit pendant qu\'il tourne. Lisez-les dans le détail d\'un job (Recent Activity, Tracking, Journal) ou en direct sur la page Logs. Les logs d\'une prévision n\'arrivent qu\'à sa fin.' },
      { id: 'mode', term: 'Mode', def: 'Test ou Production, choisi par chaque utilisateur. Test n\'écrit rien dans DHIS2 et garde ses passes, journaux et fichiers à part ; Production écrit pour de vrai. Chaque mode ne voit que ses propres passes.' },
      { id: 'pass', term: 'Pass', def: 'Une tentative de réaliser un cycle, avec son propre identifiant et son journal. Elle est active, en pause (paused), terminée (complete) ou abandonnée (abandoned). Une pass terminée ou abandonnée est figée : refaire le mois démarre une nouvelle pass.' },
      { id: 'pause-resume', term: 'Pause / Resume (reprendre)', def: 'Pause arrête une pass active pour la continuer plus tard, son état conservé. Reprenez-la depuis Start a pass ou depuis le Journal.' },
      { id: 'recent-activity', term: 'Recent Activity', def: 'Les jobs lancés depuis la page Forecast depuis que vous l\'avez ouverte, avec leur résultat et un lien vers leur requête et leurs logs.' },
      { id: 'request', term: 'Request (requête)', def: 'Un appel de cette application à etlhub. Tracking les liste avec leur statut et leur durée ; une requête qui a lancé un job mène à ses logs.' },
      { id: 'run', term: 'Run', def: 'Dans Forecasts, la prévision d\'une maladie à un niveau. Un seul run est ouvert à la fois ; le publier le ferme. Ouvrir un run vide les dossiers de travail input et output du serveur.' },
      { id: 'status', term: 'Status (statut)', def: 'L\'état d\'un item, décidé par etlhub : Pending (pas fait), Running (en cours), Success (réussi, compte) ou Error (à relancer).' },
      { id: 'step', term: 'Step (étape)', def: 'Une des 3 étapes d\'une pass, faites dans l\'ordre : ① Data Import, ② Forecasts, ③ System Update. Une étape ne compte que si la précédente compte.' },
      { id: 'test-mode', term: 'Test mode', def: 'Voir Mode et Dry run.' },
      { id: 'update-key', term: 'Update Key', def: 'Dernière action de System Update : elle écrit la clé de mise à jour de PRIDE-C dans le datastore DHIS2. Refusée en mode Test.' }
    ]
  }
}
