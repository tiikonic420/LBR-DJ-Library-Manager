# Validation ICE du MSI R10 publié — échec confirmé

État au 2 novembre 2026. MSI étudié : SHA256 `86dceabb773f6d8d601b3dcbc56d1dfacf40dead517deb8b4ca87e5fe6a00228`, publié dans la préversion `v5.0.0-rc10`.

## Méthode et portée

Le [run Windows GitHub 41486643145](https://github.com/tiikonic420/LBR-DJ-Library-Manager/actions/runs/41486643145) utilise l'API Validator de WiX 3.14.1 et le cube Microsoft darice.cub non modifié, avec liste de suppressions vide et sans filtre d'ICE. Les empreintes du paquet publié, du MSI, de l'archive d'outillage et du cube sont vérifiées avant exécution. Le lanceur de validation appelle les actions du cube sur une copie temporaire, jamais sur une installation personnelle. Il ne lance pas LBR et ne modifie aucune protection Windows.

Les **104 ICE de la séquence ont démarré et terminé**, ICE33 et ICE66 comprises. Les codes de retour des actions ne sont pas un verdict de conformité : les messages ICE contiennent **6 238 erreurs et 11 210 avertissements**. Le verdict est ÉCHEC.

L'analyseur initial ne reconnaissait que les libellés de fin d'action anglais ; le MSI étant en français, le contrôle de couverture a initialement indiqué incomplet. L'analyseur a été complété pour reconnaître les journaux français. Les journaux et archives initiaux restent conservés ; aucune erreur ICE n'a été retirée. Le replay vérifie à nouveau l'ensemble des 104 actions.

## Défauts détectés

| Contrôle | Erreurs | Cause observée |
| --- | ---: | --- |
| ICE03 | 121 | Métadonnées standard absentes de la table _Validation |
| ICE20 | 2 | Dialogues Windows Installer FilesInUse et ErrorDialog non définis conformément aux exigences |
| ICE38 | 5 605 | Composants installés dans le profil utilisateur avec chemin-clé fichier au lieu d'une clé HKCU |
| ICE64 | 510 | Dossiers du profil utilisateur sans ligne explicite de suppression de dossier vide |

| Contrôle | Avertissements | Cause observée |
| --- | ---: | --- |
| ICE39 | 5 605 | Compression spécifiée à la fois au niveau global et sur chaque fichier |
| ICE91 | 5 605 | Emplacements propres à l'utilisateur, non adaptés à un déploiement pour tous les utilisateurs |

ICE91 doit être interprété avec la conception du produit : le MSI est volontairement par utilisateur, et la condition NOT ALLUSERS refuse l'installation globale. Cela ne justifie pas de supprimer l'ICE ni les avertissements ; ils restent publiés et documentés. Les erreurs ci-dessus doivent être corrigées.

## Correction en copie isolée

Une candidate distincte « R10 ICE1 », à identité et chemins d'installation distincts, est préparée par Tools/Validation/repair_msi_ice.py. Elle ajoute les métadonnées officielles issues de WiX, les chemins-clés HKCU, le nettoyage explicite des dossiers vides et les dialogues standard, puis retire l'attribut de compression redondant. Les changements portent sur les tables MSI ; le cabinet et les fichiers applicatifs ne doivent pas changer. Les règles ICE ne sont ni supprimées ni assouplies.

**Cette candidate est en cours de validation et n'est pas un remplacement validé de la préversion publiée.** Aucun moteur, TaskHub, SQLite ou test applicatif n'est modifié. Une réussite ICE, si obtenue, devra être suivie des contrôles d'installation, réparation, désinstallation et conservation des sauvegardes sur les nouveaux octets. Les archives de release existantes ne sont pas remplacées.

## Essai local et preuves

L'hôte local n'a pas permis une validation : le SDK téléchargé depuis Microsoft, à signature valide, a retourné 1001 lors de la préparation de l'outillage ; l'essai via Validator a rencontré un refus Windows Installer 0x80070005 pour ses actions de validation. Ces résultats sont des échecs d'environnement, pas un passage des ICE. Le runner Windows hébergé a permis d'obtenir les résultats réels ci-dessus.

Les journaux complets, résumés, empreintes et échecs sont conservés localement et comme artefacts des runs. Les tests DJ sont distincts : le kit utilise Windows Sandbox, quatre fichiers audio synthétiques et des profils d'applications vierges. L'initialisation est confirmée ; les réouvertures et synchronisations externes ne sont pas encore validées.

La version reste RC non signée, demande SignPath en attente. Aucune stabilité autorisée.

Références : https://learn.microsoft.com/en-us/windows/win32/msi/ice20 ; https://learn.microsoft.com/en-us/windows/win32/msi/ice38 ; https://learn.microsoft.com/en-us/windows/win32/msi/ice64 ; https://learn.microsoft.com/en-us/windows/win32/msi/ice91 .
