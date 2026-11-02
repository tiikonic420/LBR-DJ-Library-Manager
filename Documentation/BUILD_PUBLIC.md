# Construction publique à qualifier

Prérequis : Windows x64 autorisé, Python 3.13.16 x64 avec Tcl/Tk, compilateur .NET Framework x64 csc.exe et makecab.exe. Les dépendances sont épinglées en version dans Build/requirements-windows.txt ; les sources rbsync fournies sont identifiées par SHA256. Les autres distributions ne sont pas encore toutes verrouillées par empreinte : qualifier ce verrouillage avant signature publique.

FFmpeg 9.0.2 est provisionné depuis la release Gyan avec le SHA256 du manifeste Microsoft winget fixé dans Build/ci-tools.json ; les sept tests audio sont obligatoires. Le modèle de workflow conserve les journaux et n'utilise ni NSIS ni option de contournement PowerShell.

La commande prévue est Build/build_windows.ps1 -AllowDownloads -CompileMsi. Elle construit depuis les sources plutôt que de réutiliser le MSI local. Le workflow .github/workflows/validation-windows.yml peut être lancé manuellement et vérifie les modifications de code/construction sur main. Il ne signe et ne publie aucun logiciel. Son premier résultat distant doit encore être observé. Le runner doit disposer des prérequis indiqués ; une absence doit produire un échec explicite, pas un succès partiel. La version Python demandée doit être réellement disponible via setup-python.

La validation locale d'un script ou d'un modèle YAML ne valide pas le build distant. Les performances ne sont pas comparées entre machines différentes comme si elles mesuraient une régression.

La signature sera ajoutée seulement après admission et qualification du build : soumission du lanceur construit, récupération de sa version signée, construction MSI intégrant ce lanceur, signature MSI et contrôle des manifestes finaux. Aucun secret SignPath n'est nécessaire pour le workflow de validation non signée fourni.
