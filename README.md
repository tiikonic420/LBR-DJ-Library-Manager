# LBR DJ Library Manager

> **Contrôle de distribution en échec :** les 104 ICE ont été exécutés sur le MSI R10 publié et révèlent des erreurs de construction. Une correction d’installateur distincte est en cours de qualification. Voir [le rapport ICE](Documentation/VALIDATION_ICE_R10.md). R10 reste une préversion, pas une version stable.

Application Windows pour Tag Studio, MusicGenre, RekordSync et transfert Rekordbox vers Serato. Édition des métadonnées et pochettes, glisser-déposer audio, sauvegardes, restauration et contrôles d'intégrité dans un espace Bibliothèque et sécurité facultatif.

**5.0 RC R10 — candidate non signée, validation stable non autorisée.** Utiliser exclusivement des fichiers et bibliothèques fictifs pour la campagne de validation. LBR est indépendant d'AlphaTheta/Pioneer DJ et de Serato, sans agrément revendiqué.

## Installation et désinstallation

La [préversion R10 non signée est disponible](https://github.com/tiikonic420/LBR-DJ-Library-Manager/releases/tag/v5.0.0-rc10). Les quatre téléchargements publics ont été vérifiés par SHA256. Télécharger le paquet complet avec notices et sources, extraire son contenu puis ouvrir le MSI. Le paquet est destiné à Windows 11 x64 et s'installe pour l'utilisateur courant. Désinstaller depuis Paramètres Windows → Applications → Applications installées. Les sauvegardes du profil utilisateur doivent rester conservées. Ne pas désactiver les protections si Windows bloque le lancement.

Lire [le guide](Documentation/GUIDE_UTILISATEUR.md), [les résultats](Documentation/ESSAI_MSI_GITHUB.md) et [les contrôles restants](Documentation/ETAT_VALIDATION.md). Le parcours PC sur données fictives passe ; le lancement non signé reste bloqué dans Sandbox. ICE exhaustif et intégrations DJ externes restent ouverts.

## Licence et sources

Le code et les éléments originaux sont sous GPL-3.0-or-later, selon la déclaration du mainteneur. Les composants tiers gardent leurs licences. Voir [LICENSE](LICENSE), [LICENSING.md](LICENSING.md), [la revue](Documentation/REVUE_LICENCES.md) et Licences. Les sources, tests et scripts de construction sont dans ce dépôt. L'archive de sources accompagne le paquet publié.

## Construction Windows

Le [build Windows](Documentation/BUILD_PUBLIC.md) utilise Python 3.13 et le constructeur MSI natif. Le run GitHub [41406418487](https://github.com/tiikonic420/LBR-DJ-Library-Manager/actions/runs/41406418487) réussit : 17 suites, 105 cas sans ignorés et six scénarios GUI supplémentaires. Les sept tests audio passent. Les ajouts documentaires et de notices ultérieurs ne changent pas l'identité du MSI déjà testé.

## Code signing policy

La demande gratuite SignPath Foundation a été envoyée le 2 novembre 2026 ; le mainteneur confirme son message de réception. L'admission reste en attente. Voir [le suivi](Documentation/SUIVI_SIGNPATH.md). Aucune signature ni approbation SignPath n'est revendiquée. Voir [Code signing policy](CODE_SIGNING_POLICY.md), [Privacy policy](PRIVACY.md) et [les rôles](GOVERNANCE.md). Après admission éventuelle seulement : Free code signing provided by SignPath.io, certificate by SignPath Foundation.

## Contributions et contact

Mainteneur : [tiikonic420](https://github.com/tiikonic420). Utiliser les issues pour les problèmes reproductibles avec données fictives, sans joindre de bibliothèque personnelle ni secret. Voir [CONTRIBUTING.md](CONTRIBUTING.md) et [SECURITY.md](SECURITY.md).
