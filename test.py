import requests 
import pandas as pd
from scrapy import Selector
from urllib.parse import urljoin
import os


url_pages = "https://books.toscrape.com/index.html"
base_url = "https://books.toscrape.com/"
# url = urljoin(base_url, "catalogue/")
# print(url)

# url = "https://books.toscrape.com/catalogue/page-7.html"
response = requests.get(url_pages)

# print(response.text)
select = Selector(text=response.text)
src_categorie = select.css("ul.nav.nav-list ul li a::attr(href)").getall()
# print(src_categorie)

for a in src_categorie:
    categorie_base_url = urljoin(base_url, a)
    url_categorie = categorie_base_url
    # print(a)
    all_images = []
    all_titre = []
    all_price = []
    all_stock = []
    all_note = []
    all_upc = []
    all_url_livre = []

    while url_categorie :

        r = requests.get(url_categorie)
        alpha = Selector(text=r.text)
        # print(url_categorie)



        texte = alpha.css("h3 a::text").getall()
        src = alpha.css("article.product_pod h3 a::attr(href)").getall()
        categorie = alpha.css("div.page-header.action h1::text").get()
        output_dir = f"images/{categorie}"
        os.makedirs(output_dir, exist_ok=True)
        # print(categorie)
        # print(texte)
        # print(src)

        # url_images = urljoin(base_url, src)

        for i in src :
            # print(url)
            url_livre = urljoin(url_categorie, i)
            all_url_livre.append(url_livre)
            # print(url_livre)
            r = requests.get(url_livre)
            response = Selector(text=r.text)

            titre = response.css("div.col-sm-6.product_main h1::text").get()
            all_titre.append(titre)

            price = response.css("div.col-sm-6.product_main p.price_color::text").get()
            all_price.append(price)

            stock_list = response.css("div.col-sm-6.product_main p.instock.availability::text").getall()
            stock = ''.join([s.strip() for s in stock_list if s.strip()])
            all_stock.append(stock)

            note_class = response.css("div.col-sm-6.product_main p.star-rating::attr(class)").get()
            note = note_class.replace('star-rating', '').strip() if note_class else None
            all_note.append(note)

            upc = response.css('table.table.table-striped tr:nth-child(1) td::text').get()
            all_upc.append(upc)

            img_src = response.css("div.item.active img::attr(src)").get()
            img_url = urljoin(url_livre, img_src)
            all_images.append(img_url)

            img_name = f"{titre.replace('/', '-')[:60]}.jpg"
            img_path = os.path.join(output_dir, img_name)

            img_data = requests.get(img_url)
            if img_data.status_code == 200:
                with open(img_path, "wb") as f:
                    f.write(img_data.content)
                # print(f"{img_url}")
            else:
                print(f"{img_name}")

        next_page = alpha.css("li.next a::attr(href)").get()
        # print(next_page)
        if next_page:
            url_categorie = urljoin(categorie_base_url, next_page)
        else:
            url_categorie = None



        
        # print(url_categorie)
    # for i, (titre, price, stock, note, upc, img_src) in enumerate(zip(all_titre, all_price, all_stock, all_note, all_upc, all_images), 1):
    #     print(f"{i}. {titre} — {price} — {stock} — {note} — {upc} — {img_src}")
    # print(all_url_livre)

    os.makedirs("solutions/categorie", exist_ok=True)
    df = pd.DataFrame({
        'Book Title': all_titre,
        'Price': all_price,
        'Stock': all_stock,
        'Note': all_note,
        'UPC': all_upc,
        'Image URL': all_images,
        'Nom categorie' : [categorie] * len(all_titre),
        'URL du produit' : all_url_livre
    })

    nom_dossier = f"solutions/categorie/categorie_{categorie}.csv"
    df.to_csv(nom_dossier, index=False)
    # print(df.head())


