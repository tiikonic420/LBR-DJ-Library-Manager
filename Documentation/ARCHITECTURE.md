# Architecture et points de reprise

## Référence et séparation

La référence est l'archive PERFORMANCE 2.3 FINAL d'empreinte `8153015fa4525143e912a2b04e6a41623185b20f773944e131767be2e38bd454`. Le Setup inclus a l'empreinte `895ace3436d963c703c097bf45ea34486dbc178bbd1a6552520fdbf9ad9a9711`.

Les 18 fichiers applicatifs/ressources de la copie de référence ont été comparés intégralement aux blocs du flux NSIS LZMA, puis indépendamment à une extraction 7-Zip. Les sources 2.2 plus le correctif RekordSync séparé correspondent exactement au payload final. La provenance détaillée est dans PROVENANCE_REFERENCE.json. Aucun des ZIP fournis n'a été remplacé.

`Reference_FINAL` est la copie de sources de cette référence. Les cinq fichiers musicaux (`musicgenre_v2`, `tag_engine`, `tag_studio`, `rekordbox_serato_v1_4`, `rekordsync_v5_0_6`) restent identiques dans Sources_application. Les adaptations sont installées lors du chargement des contrôleurs, après la préparation de leur cache et avant l'enveloppement TaskHub.

## Services ajoutés

- `reliability.py` : SHA-256 en blocs, JSON atomique, BackupStore, conflits, annulation, journal SQLite et diagnostic en lecture seule. Une sauvegarde partielle n'a pas de manifeste et n'est pas proposée à la restauration.
- `legacy_safety.py` : protections des écritures Genre/Année, tags/pochettes, renommages, marqueurs et snapshots Rekordbox/crates ; aperçus et orientation vers la restauration sélective commune.
- `library_services.py` : autorisation des racines, analyse Mutagen, catalogue SQLite, indexation incrémentale, recherche, doublons, propositions de chemins, réparation XML, règles ET/OU, export M3U8 et plans de tags.
- `workspace_ui.py` : espace secondaire Tk/ttk, opérations asynchrones via le worker existant, affichage borné des rapports, choix/confirmations, assistant et contrôles par palier.
- `release_info.py` : version et activation du palier 41, 45 ou 50. Les sources communes avancées sont présentes dans les archives intermédiaires mais leurs vues avancées restent désactivées.

Le gestionnaire n'ajoute qu'un accès à cet espace, une identification de version et la préparation des adaptateurs. Les préférences candidates sont isolées. TaskHub reçoit un seul mécanisme supplémentaire : des finaliseurs exécutés sur le worker avant la notification finale. Cela évite de recalculer des SHA-256 de grandes bases dans le thread graphique. Les files, le bridge Tk, les limites du cache et le rendu historique restent en place.

## Contrats de sécurité

Les écritures de tags par lots revalident les empreintes de l'aperçu puis protègent l'ensemble des originaux. Chaque fichier est revérifié juste avant écriture et relu après. Une exception déclenche une tentative de restauration des originaux avec conservation des preuves. L'échec de cette restauration reste une erreur et ne devient jamais un succès.

La restauration vérifie les blobs et les postimages attendues, prépare les copies et une sauvegarde de l'état courant, puis utilise des remplacements atomiques fichier par fichier. Ce n'est pas une transaction atomique multi-fichiers : une interruption entre deux remplacements peut nécessiter une reprise sélective. Le manifeste journalise les remplacements déjà achevés. Les créations nouvelles ne sont jamais supprimées automatiquement.

Le renommage utilise une destination créée exclusivement, vérifie les octets copiés avant de retirer l'ancien nom, et conserve une sauvegarde. Si une cible apparaît après l'aperçu, elle n'est pas écrasée. Après restauration, un doublon sous le nouveau nom peut subsister volontairement.

Les snapshots de bases sont de simples copies de fichiers et de sidecars lorsqu'ils existent. Rekordbox doit être fermé ; ils ne prétendent pas fournir une sauvegarde transactionnelle d'une base DJ ouverte. Le service ne décrypte ni ne modifie directement master.db.

Les racines autorisées bornent les nouvelles lectures/analyse/écritures musicales. Les liens qui sortent de ces racines sont refusés ou ignorés au scan. Les destinations d'exports sont choisies explicitement. Les moteurs historiques conservent leurs sélecteurs propres.

Le diagnostic n'appelle que Python pour version/métadonnées puis rbsync --help, avec délais. Il ne lance jamais pip. Les regex utilisent un processus séparé et un délai ; pas d'exécution de code à partir des modèles.

## Tests historiques adaptés sans neutralisation

Le test différentiel AST des moteurs utilise désormais la vraie source FINAL pour RekordSync : la référence RC2 antérieure ne contient pas son correctif validé. Les autres comparaisons gardent les références historiques. Le test d'invariant retire précisément le crochet de finalisation ajouté à TaskHub avant de vérifier l'identité de son ancien code. La surcouche du gestionnaire a des tests d'intégration dédiés. Les anciens tests non adaptés qui comparent toutes les différences au RC2 initial sont conservés dans l'audit initial ; ils ne définissent pas l'identité de FINAL.

## Distribution

Le build Windows prépare un runtime privé Python 3.13 depuis un venv isolé, copie les sources, réutilise le lanceur natif vérifié et exécute les contrôles d'import/CLI. Les sources C/RC du lanceur et NSIS sont fournies. L'installateur candidat est configuré dans un répertoire et des clés/raccourcis distincts de la version stable. Aucun nouveau Setup d'application n'a été compilé ou exécuté dans cet environnement.

La liste verrouillée de dépendances vise Python 3.13 ; sa résolution effective et la disponibilité de tous les wheels sont des contrôles Windows restant à réaliser. Aucun téléchargement n'est autorisé par défaut dans le script. Les notices et sources tierces fournies sont conservées ; aucune nouvelle dépendance d'application n'est ajoutée hors bibliothèque standard.
