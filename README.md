# LBR DJ Library Manager

Application Windows pour Tag Studio, MusicGenre, RekordSync et transfert Rekordbox vers Serato. Ã‰dition des mÃ©tadonnÃ©es et pochettes, glisser-dÃ©poser audio, sauvegardes, restauration et contrÃ´les d'intÃ©gritÃ© dans un espace BibliothÃ¨que et sÃ©curitÃ© facultatif.

**5.0 RC R10 â€” candidate non signÃ©e, validation stable non autorisÃ©e.** Utiliser exclusivement des fichiers et bibliothÃ¨ques fictifs pour la campagne de validation. LBR est indÃ©pendant d'AlphaTheta/Pioneer DJ et de Serato, sans agrÃ©ment revendiquÃ©.

## Installation et dÃ©sinstallation

La premiÃ¨re prÃ©version sera fournie depuis la page [Releases](https://github.com/tiikonic420/LBR-DJ-Library-Manager/releases) une fois publiÃ©e ; aucune disponibilitÃ© n'est revendiquÃ©e avant cette publication. TÃ©lÃ©charger le paquet complet avec notices et sources, extraire son contenu puis ouvrir le MSI. Le paquet est destinÃ© Ã  Windows 11 x64 et s'installe pour l'utilisateur courant. DÃ©sinstaller depuis ParamÃ¨tres Windows â†’ Applications â†’ Applications installÃ©es. Les sauvegardes du profil utilisateur doivent rester conservÃ©es. Ne pas dÃ©sactiver les protections si Windows bloque le lancement.

Lire [le guide](Documentation/GUIDE_UTILISATEUR.md), [les rÃ©sultats](Documentation/ESSAI_MSI_GITHUB.md) et [les contrÃ´les restants](Documentation/ETAT_VALIDATION.md). Le parcours PC sur donnÃ©es fictives passe ; le lancement non signÃ© reste bloquÃ© dans Sandbox. ICE exhaustif et intÃ©grations DJ externes restent ouverts.

## Licence et sources

Le code et les Ã©lÃ©ments originaux sont sous GPL-3.0-or-later, selon la dÃ©claration du mainteneur. Les composants tiers gardent leurs licences. Voir [LICENSE](LICENSE), [LICENSING.md](LICENSING.md), [la revue](Documentation/REVUE_LICENCES.md) et Licences. Les sources, tests et scripts de construction sont dans ce dÃ©pÃ´t. L'archive de sources accompagne le paquet publiÃ©.

## Construction Windows

Le [build Windows](Documentation/BUILD_PUBLIC.md) utilise Python 3.13 et le constructeur MSI natif. Le run GitHub [41406418487](https://github.com/tiikonic420/LBR-DJ-Library-Manager/actions/runs/41406418487) rÃ©ussit : 17 suites, 105 cas sans ignorÃ©s et six scÃ©narios GUI supplÃ©mentaires. Les sept tests audio passent. Les ajouts documentaires et de notices ultÃ©rieurs ne changent pas l'identitÃ© du MSI dÃ©jÃ  testÃ©.

## Code signing policy

La candidature gratuite SignPath Foundation est prÃ©parÃ©e, non envoyÃ©e et non acceptÃ©e. Aucune signature ni approbation SignPath n'est revendiquÃ©e. Voir [Code signing policy](CODE_SIGNING_POLICY.md), [Privacy policy](PRIVACY.md) et [les rÃ´les](GOVERNANCE.md). AprÃ¨s admission Ã©ventuelle seulement : Free code signing provided by SignPath.io, certificate by SignPath Foundation.

## Contributions et contact

Mainteneur : [tiikonic420](https://github.com/tiikonic420). Utiliser les issues pour les problÃ¨mes reproductibles avec donnÃ©es fictives, sans joindre de bibliothÃ¨que personnelle ni secret. Voir [CONTRIBUTING.md](CONTRIBUTING.md) et [SECURITY.md](SECURITY.md).
