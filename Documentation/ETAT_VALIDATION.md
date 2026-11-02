# État public proposé — 5.0 RC R10

Candidate non signée, non déclarée stable. Validation Windows locale : 17 suites automatiques réussies, deux cas de liens symboliques initialement ignorés puis réussis dans Windows Sandbox ; huit contrôles natifs réussis ; tests audio synthétiques ; DPI Windows confirmés par l'utilisateur à 100/125/150/200 %.

Le dépôt audio et l'erreur MSI 2228 ont été corrigés dans R10. Le MSI s'installe et se désinstalle dans Sandbox avec empreintes conformes et sauvegardes conservées. Le lanceur non signé y est bloqué par la politique VerifiedAndReputableDesktop (erreur 4551). Aucune protection n'est désactivée.

Navigation chargée : 70,07 ms ; filtre : 36,17 ms, protocole R9/R10 alterné et tolérance +5 % satisfaits. Aucun résultat de performance sur GitHub n'est encore disponible.

Restent : signature reconnue et nouveau cycle Sandbox, validation MSI ICE, réouverture/synchronisations dans les applications Rekordbox et Serato sur un environnement exclusivement fictif. Les essais de format et de SQLite synthétique ne remplacent pas cette réouverture.

Un résumé public ne doit pas contenir les journaux Windows bruts du PC du mainteneur. Ils restent conservés séparément avec les preuves originales.

## Qualification du dépôt privé

Le run GitHub https://github.com/tiikonic420/LBR-DJ-Library-Manager/actions/runs/41406418487 passe les 17 suites avec 105 cas unittest sans ignorés et construit un MSI non signé. Les sources applicatives sont inchangées. Ce paquet CI reste à essayer en installation/Sandbox ; cette réussite ne lève pas le blocage de signature de la R10 ni les contrôles ICE et DJ externes.
