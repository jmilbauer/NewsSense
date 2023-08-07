import json
import urllib.request
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
import re

def parse_document(soup):
    title = soup.title.text
    paragraphs = [p.text.strip() for p in soup.find_all('p')]
    links = set([l.get('href') for l in soup.find_all('a')])
    return title, paragraphs, links

def get_titles_and_links(http):
    soup = BeautifulSoup(http, 'html.parser')
    els = soup.find_all('h4')
    links = []
    titles = []
    for el in tqdm(els):
        link = f"https://news.google.com{el.a['href'][1:]}"
        referral_page = urllib.request.urlopen(link).read().decode('utf8')
        referral_soup = BeautifulSoup(referral_page, 'html.parser')
        linktexts = [x.get_text() for x in referral_soup.find_all('a')]
        linktexts = [l for l in linktexts if l[:4] == 'http']
        links.append(linktexts[-1])
        titles.append(el.get_text())
    return links, titles

def get_google_story(google_url, verbose=False, n=None):
    response = urllib.request.urlopen(google_url)
    http = response.read().decode('utf8')
    urls, titles = get_titles_and_links(http)
    
    texts = []
    links = []
    venues = []
    titles = []
    if n is not None:
        urls = urls[:n]
    print(f"Scraping from {len(urls)} urls.")
    for url in tqdm(urls):
        domains = re.findall('(http.*(com|org))', str(url))
        if len(domains) > 0:
            domain = domains[0][0]
        else:
            continue
        if verbose:
            print(f"Trying: {url}")
        try:
            response = requests.get(url, timeout=5)
        except:
            if verbose:
                print("Timeout")
            continue
        if response.status_code == 200:
            data = response.content
            soup = BeautifulSoup(data, 'html.parser')
            title_, paragraphs_, links_ = parse_document(soup)
            titles.append(title_)
            texts.append(paragraphs_)
            links.append(links_)
            venues.append(domain)
            if verbose:
                print(title_)
        else:
            if verbose:
                print(response.status_code)
    
    return titles, texts, links, venues, urls
