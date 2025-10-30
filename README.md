"# Projet_Scrape_Python" 

J’ai fait un premier fichier test.py pour tester les différentes manières de scraper les éléments des pages et des livres, et un deuxième fichier scraping.py sur lequel j’ai réalisé le projet concret.

Pour tester le scraping ciblé, il faut exécuter la commande :
python scraping.py --categorie nom_de_la_categorie

Lorsque l’on lance cette commande, un fichier CSV est créé automatiquement qui contient les elements de chaque livre dans le dossier outputs/categories (il est créé automatiquement s’il n’existe pas), et toutes les images présentes sont stockées dans un dossier également créé automatiquement, portant le nom de la catégorie et enregistré dans images/.
