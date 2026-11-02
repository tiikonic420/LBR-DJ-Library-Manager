> Historical preparation document. Current status on 2 November 2026: repository and unsigned RC are public; application sent, receipt reported by the maintainer after CAPTCHA; admission pending. See [SUIVI_SIGNPATH.md](SUIVI_SIGNPATH.md). Earlier private/not-submitted statements below describe the preparation stage. Do not submit a duplicate application.

# Préparation SignPath — dépôt privé

État au 2 novembre 2026 : dépôt privé, aucune candidature envoyée, aucun fichier signé, version RC maintenue.

## Dépôt et construction vérifiés

- Dépôt : https://github.com/tiikonic420/LBR-DJ-Library-Manager (privé).
- Commit construit : `9881a5bc1eac1480d431b405745a09fbcb03bd95`.
- Vérification GitHub réussie : https://github.com/tiikonic420/LBR-DJ-Library-Manager/actions/runs/41406418487.
- 17 suites, 105 cas unittest réussis, zéro ignoré, et 6 scénarios GUI supplémentaires. Les 7 tests audio passent avec FFmpeg 9.0.2 vérifié par SHA256.
- Artefact privé `LBR-R10-unsigned-review-only` : MSI construit depuis les sources, non signé. SHA256 du MSI : `86dceabb773f6d8d601b3dcbc56d1dfacf40dead517deb8b4ca87e5fe6a00228`.
- Les 5 605 fichiers du MSI ont été extraits et contrôlés par SHA256 ; ses 26 fichiers de sources/ressources applicatives correspondent exactement au dépôt préparé. Lanceur et Python x64 ; vérification native MsiVerifyPackage à 0 ; aucune action personnalisée ; table Signature présente.
- Les moteurs, TaskHub et SQLite n'ont pas été modifiés. Les changements faits pour la préparation concernent les documents et les outils CI.

Les ajouts documentaires ultérieurs ne constituent pas une nouvelle compilation : le lien et le commit ci-dessus identifient exactement les artefacts contrôlés.

## Échecs et portée des résultats

Le premier essai GitHub, run 41406158325, a échoué avant les tests LBR dans le script de préparation FFmpeg (lecture du code retour après un pipeline interrompu). Le script de CI a été corrigé ; le journal initial et celui du succès sont conservés. Aucune assertion produit n'a été affaiblie. Les deux cas initialement ignorés sur le PC local passent aussi dans ce run GitHub ; les anciens journaux de skips ne sont pas effacés.

Ce MSI CI est une nouvelle compilation : sa documentation et certaines métadonnées de construction diffèrent du MSI R10 précédemment essayé sur Windows 11. Les essais du 2 novembre sont détaillés dans ESSAI_MSI_GITHUB.md : parcours GUI réussi sur le PC hôte et désinstallation avec conservation des 23 fichiers fictifs ; installation/désinstallation réussies dans Sandbox, mais lancement bloqué par erreur 4551. Le succès hôte ne valide pas la GUI dans Sandbox.

L'inventaire du runner trouve darice.cub et smoke.exe WiX 3.14.1, mais pas Msival2. Aucune validation ICE exhaustive n'a été exécutée. Le programme smoke de WiX 3 supprime ICE33/ICE66 par défaut ; son existence ne permet pas de déclarer ces contrôles réussis.

## Demande SignPath

Le texte de candidature est dans CANDIDATURE_SIGNPATH.md. Les liens sont encore privés et ne doivent pas être présentés comme des références publiques accessibles à SignPath. Ne pas soumettre le formulaire à ce stade.

Le 2 novembre 2026, le propriétaire confirme à sa connaissance les droits de publication du code et des images propres à LBR sous GPL-3.0-or-later, avec conservation des licences tierces, et confirme MFA activée sur GitHub. Ce sont ses déclarations, sans audit juridique indépendant. Avant une éventuelle demande : finaliser les obligations de redistribution et les rôles de signature, configurer MFA sur SignPath si l'accès est accordé, puis obtenir l'instruction explicite du propriétaire pour une ouverture publique et une release RC. Aucun changement de visibilité n'est autorisé par cette préparation.

L'admission reste à l'appréciation de SignPath, notamment pour la réputation publique d'un projet nouvellement créé. Une signature éventuelle apparaîtrait sous le nom du titulaire de leur certificat, SignPath Foundation. Aucun utilisateur, historique public ou soutien externe n'est inventé.

## Après une éventuelle admission

Qualifier les règles de métadonnées et les artefacts SignPath : signer uniquement le lanceur LBR construit sur GitHub, intégrer celui-ci dans le MSI, signer ensuite le MSI, vérifier les signatures et actualiser les manifestes/archives. Ne pas signer les binaires Python et bibliothèques tierces comme des créations LBR. Rejouer les contrôles Windows/Sandbox, ICE et les intégrations DJ fictives avant de discuter une promotion stable.

## Revue préalable à la publication — 2 novembre 2026

Les trois rôles sont confirmés pour tiikonic420 : committer, relecteur et approbateur manuel. La revue technique des licences est consignée dans REVUE_LICENCES.md. Les notices complémentaires SQLCipher, OpenSSL, Expat, zlib et XZ ainsi que GPL LBR sont ajoutées aux sources ; elles ne modifient pas le MSI déjà compilé. Publier le paquet complet accompagné de ces notices et des sources. Le dépôt reste privé jusqu’à l’étape de publication réalisée par son propriétaire. Aucune demande SignPath envoyée.
