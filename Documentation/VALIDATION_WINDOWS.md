# Validation finale Windows 11 — à exécuter

Aucune de ces validations cibles n'est annoncée comme exécutée dans la livraison locale. Utiliser uniquement une copie fictive/isolée des bibliothèques, y compris pour Rekordbox et Serato. Les véritables bases et morceaux ne sont pas nécessaires à cette campagne.

## 1. Sources et Python 3.13

- Installer/utiliser Python 3.13 x64 avec Tcl/Tk dans un environnement de validation.
- Préparer les dépendances isolées. `Build/build_windows.ps1 -AllowDownloads` autorise explicitement leur téléchargement dans son venv ; sans ce paramètre, aucun téléchargement n'est tenté.
- Exécuter `Build/validate_windows11.ps1` avec le Python du venv (`-Python chemin\vers\python.exe`). Les rapports sont écrits dans un nouveau dossier Results/WINDOWS_daté.
- Fournir FFmpeg pour les sept tests sur de vrais codecs ; sinon ces cas sont marqués non exécutés et doivent être rejoués ensuite.
- Conserver les journaux complets, y compris les échecs. Une suite non lancée ou un test ignoré n'est pas un succès.

## 2. Interface et performances

- Tester 100 %, 125 %, 150 % et 200 % de DPI, en sombre/clair, avec tailles de fenêtre réduites et maximisées.
- Ouvrir les quatre outils plusieurs fois, conserver leurs sélections, changer de thème, ouvrir les nouvelles vues et l'assistant.
- Vérifier la navigation pendant indexation, doublons, lecture de métadonnées et traitements par lots.
- Mesurer les benchmarks fournis sur la même machine pour la référence et la candidate, sans interaction pendant les captures. Les timings Linux sont des observations distinctes.
- Vérifier explicitement la fermeture refusée pendant les tâches, puis la fermeture normale du worker ; tuer un processus seulement avec des fixtures pour tester la reprise.

## 3. Données fictives et protections Windows réelles

- Verrouiller un fichier avec partage d'écriture refusé, puis vérifier que l'opération échoue sans modification.
- Tester une destination de sauvegarde non accessible par ACL et un disque plein/quota simulé : aucune écriture musicale ne doit commencer si la sauvegarde obligatoire échoue.
- Corrompre un blob de sauvegarde : vérification et restauration doivent être refusées.
- Modifier un fichier après aperçu ou après opération : conflit explicite, sans écrasement silencieux.
- Simuler un arrêt entre copie, manifeste et restauration sur plusieurs fichiers ; vérifier les états interrompus, les originaux et la reprise sélective. La restauration est atomique par fichier, pas pour tout le lot.
- Après un renommage, vérifier les octets et les références ; une restauration conserve le nouveau fichier et peut donc laisser un doublon volontaire.

Les simulations PermissionError et interruptions exécutées sous Linux ne remplacent pas ces contrôles natifs.

## 4. Moteurs musicaux

- Dans des profils Rekordbox/Serato de test fermés pendant les écritures, vérifier les plans CLI, les créations/ajouts/retraits de playlists et l'intégrité des bases après réouverture.
- Vérifier les crates, titres, pochettes, champs non modifiés, Hot Cues et Saved Loops aux formats réellement compatibles.
- Vérifier WAV : crates fonctionnelles, transfert des marqueurs refusé/ignoré avec avertissement.
- Vérifier l'AAC brut : analyse possible, édition non prise en charge sans altération de l'original.
- Tester les permissions et chemins Unicode/longs, les fichiers manquants et les cibles ambiguës.
- La nouvelle réparation de chemins agit sur un export XML uniquement ; son réimport doit être testé séparément sur une bibliothèque fictive.

## 5. Construction, installation et Sandbox

- Exécuter le script de build, vérifier les versions effectivement résolues, le runtime Python 3.13 copié et rbsync --help depuis ce runtime.
- Compiler NSIS seulement après les contrôles bloquants. Les candidats utilisent un emplacement, des clés et des raccourcis distincts de la version stable.
- Installer/démarrer/désinstaller dans Windows Sandbox et sur un profil Windows de test. Vérifier les chemins contenant espaces/accents, le mutex et la conservation des sauvegardes.
- Vérifier le manifeste, les empreintes des fichiers livrés et les notices de dépendances résolues. Le lanceur de référence réutilisé conserve ses métadonnées PE 4.0 RC2 ; l'application et le manifeste de candidate indiquent le nouveau palier.
- Aucun certificat n'a été fourni. Ne pas déclarer le produit signé ou stable avant les contrôles correspondants.

## Conditions de sortie

Les trois archives sont des candidates de sources. La mission ne peut être déclarée achevée qu'après résolution des échecs éventuels, validation du runtime 3.13, des synchronisations fictives réelles, de l'installation/Sandbox et des objectifs de performance sur Windows 11.
