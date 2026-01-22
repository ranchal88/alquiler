from bs4 import BeautifulSoup
from src.extractors.idealista.extractor import fetch

url = "https://www.idealista.com/alquiler-viviendas/madrid/chamberi/trafalgar/"

html = fetch(url)
soup = BeautifulSoup(html, "html.parser")

print("article[data-element-id]:", len(soup.select("article[data-element-id]")))
print("div[data-adid]:", len(soup.select("div[data-adid]")))
