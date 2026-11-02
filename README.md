# LBR DJ Library Manager

Application Windows de gestion DJ : Tag Studio, MusicGenre, RekordSync et transfert Rekordbox vers Serato. Elle propose édition des métadonnées/pochettes, glisser-déposer audio et un espace Bibliothèque et sécurité facultatif avec sauvegardes et contrôles d'intégrité.

**État : 5.0 RC R10, non signée.** La validation stable n'est pas autorisée. Aucun partenariat ou agrément AlphaTheta/Pioneer DJ/Serato n'est revendiqué.

Cette copie est une préparation locale à relire avant publication. Le compte du mainteneur, la confirmation de titularité et les liens publics restent à compléter dans GOVERNANCE.md. Le compte GitHub tiikonic420 est déclaré créé ; aucun dépôt public ni candidature SignPath n'existe encore.

## Licence

Option choisie pour la préparation du code original LBR : GNU GPL version 3 ou, à votre choix, toute version ultérieure (SPDX: GPL-3.0-or-later). Voir LICENSE et LICENSING.md. Les bibliothèques tierces conservent leurs propres licences. L'autorisation de publier les éléments originaux doit être confirmée par leur titulaire avant diffusion publique.

## Installation et validation

La candidate MSI/portable est destinée à des essais sur des données fictives. Le paquet n'est pas actuellement disponible depuis ce dépôt préparatoire. Lire Documentation/ETAT_VALIDATION.md et Documentation/GUIDE_UTILISATEUR.md.

## Construction Windows

Le code et les tests sont dans ce dépôt ; Build/build_windows.ps1 prépare le runtime puis le MSI. Le téléchargement des dépendances est explicite avec -AllowDownloads ; -CompileMsi utilise le constructeur MSI natif. NSIS n'est pas utilisé pour cette candidature. Voir Documentation/BUILD_PUBLIC.md. Le modèle GitHub Actions doit encore être exécuté et qualifié ; aucun résultat distant n'est annoncé.

## Code signing policy

Candidature SignPath Foundation en préparation, non envoyée et non acceptée. Les fichiers restent non signés. Voir CODE_SIGNING_POLICY.md et PRIVACY.md. La formule d'attribution SignPath figurant dans la politique décrit la procédure envisagée après acceptation, pas un service déjà accordé.

## Contributions et contact

Les problèmes et contributions seront reçus via le futur dépôt public, après création du compte du mainteneur. Voir GOVERNANCE.md, CONTRIBUTING.md et SECURITY.md.

