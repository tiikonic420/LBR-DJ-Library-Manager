# Guide des nouvelles fonctions

## V4.1 — sécurité

Le bouton Bibliothèque et sécurité donne accès aux sauvegardes, aux tâches et au diagnostic. Les points d'écriture des moteurs sont entourés de protections communes ; leurs encodeurs musicaux restent ceux de la version de référence.

**Sauvegardes.** Le dossier est choisi dans Dossiers. Chaque opération protégée conserve les originaux et un manifeste SHA-256. Dans Sauvegardes, actualiser la liste, sélectionner une sauvegarde, vérifier son intégrité puis sélectionner les fichiers à restaurer. Un conflit avec un fichier changé après l'opération bloque la restauration. Une copie de sécurité de l'état courant est préparée avant remplacement. Les remplacements se font fichier par fichier, sans suppression préalable du fichier courant.

La restauration ne supprime jamais automatiquement les fichiers nouvellement créés. Après un renommage, restaurer l'ancien chemin conserve donc aussi le fichier sous son nouveau nom. Ce choix évite de supprimer silencieusement un morceau ; vérifier manuellement les références avant tout nettoyage.

**Aperçus.** MusicGenre montre Genre/Année avant et après. Tag Studio montre les champs concernés ; les pochettes sont identifiées par empreinte et les renommages par chemins. RekordSync demande des plans CLI et présente ajouts, retraits, créations et éléments ignorés. Serato présente l'état des playlists, les références ajoutées/retirées et les marqueurs proposés. Les anciens marqueurs opaques ne sont pas décodés intégralement : la conservation repose sur les sauvegardes du fichier complet, pas sur une promesse d'interprétation de tous les blobs Serato.

Les grands rapports sont limités à l'affichage pour préserver la réactivité ; le rapport complet reste exportable. Un aperçu ne déclenche pas d'écriture musicale. La préparation RekordSync peut créer des listes de travail dans son dossier de configuration.

**Tâches.** Les traitements passent par le coordinateur commun. Les nouvelles opérations progressent avec un compteur réel quand le total est disponible ; un total inconnu n'est pas converti en pourcentage fictif. Les opérations différées du coordinateur apparaissent en attente. Les tâches démarrées sont persistées ; celles qui étaient en cours lors d'une interruption sont signalées au prochain démarrage. Les traitements différés qui n'avaient pas encore démarré ne sont pas repris automatiquement.

L'annulation est coopérative. Elle attend un point sûr et ne tue pas une écriture en cours ni un processus rbsync externe. Une demande trop tardive peut laisser l'opération se terminer ; le journal ne la déclare annulée que si un point d'annulation a réellement été atteint. Les erreurs gérées à l'intérieur d'un ancien moteur restent aussi à consulter dans son journal.

**Diagnostic.** Il interroge la version réelle de Python, les métadonnées rbsync et `--help`, sans ouvrir une base DJ ni installer un paquet. La compatibilité actuellement reconnue est Python 3.13 avec rbsync 0.2.0 et un CLI fonctionnel. Les autres versions sont signalées pour revue. L'ancien bouton d'installation RekordSync conserve sa demande d'autorisation ; le nouveau diagnostic ne télécharge rien.

## V4.5 — bibliothèque

Autoriser les dossiers, lancer Indexer, puis utiliser Recherche. L'index SQLite est indépendant de Rekordbox et Serato. Les fichiers inchangés selon taille/date ne sont pas relus ; les références disparues restent disponibles pour la recherche de chemins manquants. Refaire une indexation après des changements externes.

La recherche porte sur artiste, titre, album, genre, année et chemin ; les filtres BPM et tonalité sont disponibles. Les résultats sont paginés par 100 titres.

**Doublons.** Les doublons exacts utilisent le SHA-256, calculé sur les groupes de même taille. Les rapprochements probables utilisent artiste/titre normalisés et une durée à ±2 secondes. Ils restent des propositions. Aucune suppression n'est exécutée. Aucune empreinte acoustique n'est ajoutée à ce stade.

**Qualité.** Sélectionner des résultats, puis lancer l'analyse dans Analyses. Elle relève format/codec, débit, fréquence, profondeur, canaux, durée et erreurs quand ces informations existent. Un débit élevé ne démontre pas une bonne qualité réelle ; les champs inconnus restent inconnus.

**Chemins.** Le rapport recherche des noms de fichiers dans les seuls dossiers autorisés, avec indication d'ambiguïté. La réparation prise en charge vise un export XML Rekordbox : choisir l'ancien chemin exact, la nouvelle correspondance et un fichier XML de sortie, puis confirmer l'aperçu. Les marqueurs et les autres attributs du XML conservent leurs valeurs. La base `master.db` et les bases Serato ne sont pas modifiées par cet outil. Réimporter un XML dans un logiciel DJ est une action séparée, à valider sur une bibliothèque fictive.

## V5.0 — préparation DJ

**Playlists.** Choisir ET/OU (AND/OR), jusqu'à trois conditions dans l'éditeur, puis prévisualiser. Les règles peuvent être enregistrées/rechargées. Le moteur accepte aussi des groupes imbriqués via son API ; l'éditeur affiche ces fichiers pour revue sans les simplifier silencieusement. L'export contrôlé crée ou actualise une M3U8 avec sauvegarde de la destination existante. Il n'actualise pas automatiquement les playlists d'un logiciel DJ.

**Tags par lots.** Sélectionner plusieurs titres dans Recherche. Choisir le champ et une action : valeur, remplacement, expression régulière, normalisation NFKC/espaces ou extraction depuis le nom. Préparer l'aperçu, puis l'appliquer explicitement. Le SHA-256 initial doit encore correspondre. Les expressions régulières s'exécutent dans un processus limité à deux secondes par transformation. Enregistrer/recharger un modèle évite de reconfigurer les champs. Pour les pochettes, utiliser la sélection multiple dans Tag Studio ; les écritures passent aussi par les sauvegardes communes.

**Accueil enrichi.** Les statistiques se chargent à la demande sur un worker, avec état des modules, opérations récentes et dernière sauvegarde. Les nombres de fichiers manquants/doublons correspondent aux dernières analyses lancées et ne sont pas fabriqués avant celles-ci.

**Première utilisation.** L'assistant s'ouvre lors du premier lancement V5.0 et reste accessible depuis l'accueil du nouvel espace. Il guide les huit étapes, propose les diagnostics et la première indexation explicitement, et ne modifie pas de musique automatiquement.
