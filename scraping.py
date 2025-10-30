import requests
import pandas as pd
import os
import time
from scrapy import Selector
from urllib.parse import urljoin
import argparse

BASE_URL = "https://books.toscrape.com/"

parser = argparse.ArgumentParser(description="Scraper Books to Scrape par catégorie")
parser.add_argument("--categorie", type=str, help="Nom de la catégorie à scraper")
parser.add_argument("--max-pages", type=int, default=None, help="Nombre maximum de pages à scraper par catégorie")
parser.add_argument("--delay", type=float, default=0, help="Délai (en secondes) entre les requêtes")
parser.add_argument("--outdir", type=str, default="outputs", help="Dossier de sortie (CSV + images)")
args = parser.parse_args()

categorie_voulue = args.categorie
print("Catégorie demandée :", categorie_voulue)

def parse_list_page(response):
    selector = Selector(text=response.text)
    links = selector.css("article.product_pod h3 a::attr(href)").getall()
    return [urljoin(response.url, link) for link in links]

def parse_product_page(response):
    selector = Selector(text=response.text)

    title = selector.css(".product_main h1::text").get(default="Unknown")
    price = selector.css(".product_main .price_color::text").get(default="Unknown")
    availability = selector.css(".availability::text").getall()
    availability = [a.strip() for a in availability if a.strip()]
    availability = availability[0] if availability else "Unknown"

    rating_class = selector.css("p.star-rating::attr(class)").get()
    rating = rating_class.replace("star-rating ", "") if rating_class else "Unknown"

    info = {}
    for row in selector.css("table.table-striped tr"):
        key = row.css("th::text").get()
        value = row.css("td::text").get()
        if key and value:
            info[key] = value

    img_src = selector.css(".carousel-inner img::attr(src)").get()
    if not img_src:
        img_src = selector.css("div.item.active img::attr(src)").get()
    img_url = urljoin(response.url, img_src) if img_src else None

    category = selector.css("ul.breadcrumb li:nth-child(3) a::text").get(default="Unknown")

    return {
        "Title": title,
        "Price": price,
        "Availability": availability,
        "Rating": rating,
        "UPC": info.get("UPC", ""),
        "Category": category,
        "Image URL": img_url,
        "Product URL": response.url
    }

def get_category_links(response):
    selector = Selector(text=response.text)
    categories = selector.css(".nav-list ul li a")
    result = []
    for cat in categories:
        name = cat.css("::text").get().strip()
        href = cat.css("::attr(href)").get()
        result.append((name, urljoin(BASE_URL, href)))
    return result

def get_next_page_url(response, current_url):
    selector = Selector(text=response.text)
    next_page = selector.css("li.next a::attr(href)").get()
    return urljoin(current_url, next_page) if next_page else None


def scrape_books():
    response = requests.get(BASE_URL)
    categories = get_category_links(response)

    for cat_name, cat_url in categories:
        if categorie_voulue and categorie_voulue.lower() != cat_name.lower():
            continue
        print(f"Scraping category: {cat_name}")
        url_categorie = cat_url
        all_books = []

        while url_categorie:
            r = requests.get(url_categorie)
            livre_links = parse_list_page(r)

            for livre_url in livre_links:
                livre_resp = requests.get(livre_url)
                livre_data = parse_product_page(livre_resp)
                all_books.append(livre_data)

                if livre_data["Image URL"]:
                    output_dir = f"images/{livre_data['Category']}"
                    os.makedirs(output_dir, exist_ok=True)
                    img_name = f"{livre_data['Title'].replace('/', '-')[:60]}.jpg"
                    img_path = os.path.join(output_dir, img_name)
                    img_data = requests.get(livre_data["Image URL"])
                    if img_data.status_code == 200:
                        with open(img_path, "wb") as f:
                            f.write(img_data.content)

            url_categorie = get_next_page_url(r, url_categorie)

        if all_books:
            os.makedirs("solutions/categorie", exist_ok=True)
            df = pd.DataFrame(all_books)
            df.to_csv(f"solutions/categorie/categorie_{cat_name}.csv", index=False)
            print(f"Saved CSV for category: {cat_name}")

if __name__ == "__main__":
    scrape_books()
