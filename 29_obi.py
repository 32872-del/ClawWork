# -*- coding: utf-8 -*-
import ast
import json
import os
import re
import threading
from copy import deepcopy
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup
from loguru import logger
from scrapling.fetchers import Fetcher

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("HEADLESS", "1")
os.environ.setdefault("BATCH", "2")
os.environ.setdefault("WAIT", "1")
os.environ.setdefault("OBI_MAX_CATEGORIES", "0")
os.environ.setdefault("OBI_MAX_PAGES", "0")
os.environ.setdefault("OBI_MAX_PRODUCTS", "0")
os.environ.setdefault("OBI_RECOLLECT", "1")

from fnspider import Spider, hash_md5, settings  # noqa: E402

SITE = "https://www.obi.pl"
HOME_URL = f"{SITE}/"
CACHE_NAME = "_29_obi_cookie"
COOKIE = (
    "sdgvlhr=0; sdgvlhr-ro=0; obi-ab-id=e4a87e47-a08a-4441-a371-978891356b5e; "
    "kameleoonVisitorCode=pbd4c3mtuusvl66u; obiConsent=c1-1|c2-1|c3-1|c4-1|c5-1|ts-1778927044036|consent-true; "
    "obi_ca_eid=Direct; wtstp_eid=2177892704439105023; _gcl_au=1.1.241825469.1778927045; "
    "_fbp=fb.1.1778927053693.239329375235352052; "
    "_hjSessionUser_1572795=eyJpZCI6IjVlZmVkNzNmLWNmYzgtNTE4Yi04NTI0LTEzMTc3MWNhMjFlZSIsImNyZWF0ZWQiOjE3Nzg5MjcwNTQ5NjYsImV4aXN0aW5nIjp0cnVlfQ==; "
    "Obi_PrudsysID=sid%3D28d2335100675d4990ac237a338fb83f30ae5ba0df75ce01cffa1cce33a07c44%7Cuid%3D28d2335100675d4990ac237a338fb83f30ae5ba0df75ce01cffa1cce33a07c44; "
    "device=desktop; device_backend=desktop; os_backend=windows; BVBRANDID=6f3a5621-6f66-47a7-8c06-cfff1b20ec41; "
    "obi_storeid=028; geomarket=028; external_storeid=028; storechanged=1; wtstp_sid=1; "
    "_hjSession_1572795=eyJpZCI6IjQ2NmY0ZmI1LTBiYjktNDRiNC1iNzUyLTkwMjY2YTc2NjA2NiIsImMiOjE3NzkxNTQxNzI5ODEsInMiOjEsInIiOjAsInNiIjowLCJzciI6MCwic2UiOjAsImZzIjowLCJzcCI6MH0=; "
    "i18next=pl; _csrf=GWIgcOoRU62Vv5ZTvpHhsX40Cy9mL7x0; SERVERID=bbbea71f8a69b74a; "
    "lastVisitedPages=%7B%22history%22%3A%5B%22%2Fakcesoria-do-zlewozmywakow%2Flaveo-preparat-do-czyszczenia-zlewozmywakow-granitowych-250-ml%2Fp%2F5805916%22%2C%22%2Fakcesoria-do-przyczep%2Fneptun-klosz-lampy-ajba-lewy%2Fp%2F5794094%22%2C%22%2Fakcesoria-do-przyczep%2Fneptun-klosz-lampy-ajba-lewy%2Fp%2F5794094%22%2C%22%2Ffarby-do-efektow%2Fprimacol-farba-strukturalna-baranek-popielaty-5-l%2Fp%2F6091813%22%5D%2C%22session%22%3A%2231C4C5B5E31ADDEBF926043E16903BE2.HYB5%22%7D; "
    "lastVisitedProducts=6091813%2C5794094%2C5805916%2C7216104%2C7348402%2C6981328; _hjMinimizedPolls=1860568; "
    "JSESSIONID=AC49A80846DBECF9082703E6DA1C8528.HYB3; obi_ca_sid=Direct; account-csrf=3bd1c442-7aba-45cb-b20d-1ae8b28c9bcb; "
    "__rtbh.lid=%7B%22eventType%22%3A%22lid%22%2C%22id%22%3A%22ANC22WYp8r2dX18CS385%22%2C%22expiryDate%22%3A%222027-05-19T02%3A33%3A18.733Z%22%7D; "
    "__rtbh.uid=%7B%22eventType%22%3A%22uid%22%2C%22id%22%3A%22unknown%22%2C%22expiryDate%22%3A%222027-05-19T02%3A33%3A18.779Z%22%7D; "
    "_uetsid=208d9560525a11f1bb8353e983457673; _uetvid=61b26870511111f1ad04c9717515f0b6; "
    "cto_bundle=BzSEZV9FTlB1cDZVY20zN0p6QXZ6ViUyQlFWOTlpNXMyVHlhbmRGZVdydnpsSXY2JTJGT2IzSndTQmNPRnZyZEh2bFdQakk5OHFDMW42bnZ2JTJGazh1ZmZxN3JBdnBNS2VtY20lMkJob3c0aFpVRlJHYUFRYUFWNlglMkZBTXp2VlNYUDgwa0JORGVXbzQyaHclMkJuM3QxWEduR3JSQkZ4ZmR1ckElM0QlM0Q; "
    "wtstp_rla=443727226699263%2C58%2C1779157263808"
)
REQUEST_HEADERS = {
    "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.5",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Cookie": COOKIE,
}

TOP_CATEGORIES = {
    "Technika": "https://www.obi.pl/technika/c/876",
    "Mieszkać": "https://www.obi.pl/mieszkac/c/874",
    "Ogród i wypoczynek": "https://www.obi.pl/ogrod-i-wypoczynek/c/860",
    "Budować": "https://www.obi.pl/budowac/c/877",
    "Łazienka": "https://www.obi.pl/lazienka/c/4159",
    "Kuchnia": "https://www.obi.pl/kuchnia/c/875",
}

PAYLOAD_LIST = {'Technika': {'Akcesoria samochodowe': {'Akcesoria do przyczep': 'https://www.obi.pl/akcesoria-samochodowe/akcesoria-do-przyczep/c/142',
                                        'Elektryka samochodowa': 'https://www.obi.pl/akcesoria-samochodowe/elektryka-samochodowa/c/143',
                                        'Konserwacja i naprawy': 'https://www.obi.pl/akcesoria-samochodowe/konserwacja-i-naprawy/c/1882',
                                        'Materiały eksploatacyjne': 'https://www.obi.pl/akcesoria-samochodowe/materialy-eksploatacyjne/c/1165',
                                        'Oleje i dodatki': 'https://www.obi.pl/akcesoria-samochodowe/oleje-i-dodatki/c/911',
                                        'Pielęgnacja samochodu': 'https://www.obi.pl/akcesoria-samochodowe/pielegnacja-samochodu/c/144',
                                        'Pomoc drogowa i pierwsza pomoc': 'https://www.obi.pl/akcesoria-samochodowe/pomoc-drogowa-i-pierwsza-pomoc/c/593',
                                        'Przyczepy': 'https://www.obi.pl/akcesoria-samochodowe/przyczepy/c/1528',
                                        'Transport': 'https://www.obi.pl/akcesoria-samochodowe/transport/c/640',
                                        'Wyposażenie wnętrza samochodu': 'https://www.obi.pl/akcesoria-samochodowe/wyposazenie-wnetrza-samochodu/c/444',
                                        'Środek przeciwko zamarzaniu': 'https://www.obi.pl/akcesoria-samochodowe/srodek-przeciwko-zamarzaniu/c/1040',
                                        'Żarówki samochodowe': 'https://www.obi.pl/akcesoria-samochodowe/zarowki-samochodowe/c/137'},
              'Artykuły żelazne i okucia': {'Akcesoria meblowe': 'https://www.obi.pl/artykuly-zelazne-i-okucia/akcesoria-meblowe/c/1363',
                                            'Haki i mocowania': 'https://www.obi.pl/artykuly-zelazne-i-okucia/haki-i-mocowania/c/2444',
                                            'Koła transportowe': 'https://www.obi.pl/artykuly-zelazne-i-okucia/kola-transportowe/c/977',
                                            'Kołki i gwoździe': 'https://www.obi.pl/artykuly-zelazne-i-okucia/kolki-i-gwozdzie/c/2443',
                                            'Kołki, gwoździe, wkręty, śruby': 'https://www.obi.pl/artykuly-zelazne-i-okucia/kolki-gwozdzie-wkrety-sruby/c/1366',
                                            'Liny i łańcuchy': 'https://www.obi.pl/artykuly-zelazne-i-okucia/liny-i-lancuchy/c/2974',
                                            'Nakrętki': 'https://www.obi.pl/artykuly-zelazne-i-okucia/nakretki/c/2441',
                                            'Numery na dom': 'https://www.obi.pl/artykuly-zelazne-i-okucia/numery-na-dom/c/974',
                                            'Okucia': 'https://www.obi.pl/artykuly-zelazne-i-okucia/okucia/c/2921',
                                            'Platformy transportowe': 'https://www.obi.pl/artykuly-zelazne-i-okucia/platformy-transportowe/c/758',
                                            'Podkładki i pierścienie': 'https://www.obi.pl/artykuly-zelazne-i-okucia/podkladki-i-pierscienie/c/2442',
                                            'Profile i blachy': 'https://www.obi.pl/artykuly-zelazne-i-okucia/profile-i-blachy/c/1876',
                                            'Skrzynki na listy': 'https://www.obi.pl/artykuly-zelazne-i-okucia/skrzynki-na-listy/c/215',
                                            'Zawiasy i okucia': 'https://www.obi.pl/artykuly-zelazne-i-okucia/zawiasy-i-okucia/c/1826',
                                            'Zestaw śrub i nakrętek': 'https://www.obi.pl/artykuly-zelazne-i-okucia/zestaw-srub-i-nakretek/c/2445',
                                            'Znaki informacyjne': 'https://www.obi.pl/artykuly-zelazne-i-okucia/znaki-informacyjne/c/975',
                                            'Śruby': 'https://www.obi.pl/artykuly-zelazne-i-okucia/sruby/c/2440'},
              'Duże maszyny': {'Agregaty prądotwórcze': 'https://www.obi.pl/duze-maszyny/agregaty-pradotworcze/c/725',
                               'Maszyny do cięcia glazury': 'https://www.obi.pl/duze-maszyny/maszyny-do-ciecia-glazury/c/1416',
                               'Wyciągarki': 'https://www.obi.pl/duze-maszyny/wyciagarki/c/1417'},
              'Elektronarzędzia': {'Akumulatory do elektronarzędzi': 'https://www.obi.pl/elektronarzedzia/akumulatory-do-elektronarzedzi/c/3193',
                                   'Frezarki': 'https://www.obi.pl/elektronarzedzia/frezarki/c/3113',
                                   'Klej do pistoletów': 'https://www.obi.pl/elektronarzedzia/klej-do-pistoletow/c/3125',
                                   'Miniszlifierki i akcesoria': 'https://www.obi.pl/elektronarzedzia/miniszlifierki-i-akcesoria/c/3100',
                                   'Narzędzia do lutowania i spawania oraz akcesoria': 'https://www.obi.pl/elektronarzedzia/narzedzia-do-lutowania-i-spawania-oraz-akcesoria/c/3098',
                                   'Narzędzia specjalne i akcesoria': 'https://www.obi.pl/elektronarzedzia/narzedzia-specjalne-i-akcesoria/c/3107',
                                   'Narzędzia wielofunkcyjne i akcesoria': 'https://www.obi.pl/elektronarzedzia/narzedzia-wielofunkcyjne-i-akcesoria/c/3102',
                                   'Opalarki': 'https://www.obi.pl/elektronarzedzia/opalarki/c/1347',
                                   'Pilarki': 'https://www.obi.pl/elektronarzedzia/pilarki/c/3119',
                                   'Pistolety do kleju': 'https://www.obi.pl/elektronarzedzia/pistolety-do-kleju/c/1350',
                                   'Strugi': 'https://www.obi.pl/elektronarzedzia/strugi/c/3115',
                                   'Szlifierki i akcesoria': 'https://www.obi.pl/elektronarzedzia/szlifierki-i-akcesoria/c/3120',
                                   'Wiertarki i wkrętarki': 'https://www.obi.pl/elektronarzedzia/wiertarki-i-wkretarki/c/3111',
                                   'Zszywacze i akcesoria': 'https://www.obi.pl/elektronarzedzia/zszywacze-i-akcesoria/c/3109',
                                   'Ładowarki do elektronarzędzi': 'https://www.obi.pl/elektronarzedzia/ladowarki-do-elektronarzedzi/c/3306'},
              'Elektronika i zabezpieczenie domu': {'Audio i wideo': 'https://www.obi.pl/elektronika-i-zabezpieczenie-domu/audio-i-wideo/c/981',
                                                    'Baterie i akumulatory': 'https://www.obi.pl/elektronika-i-zabezpieczenie-domu/baterie-i-akumulatory/c/980',
                                                    'Domofony': 'https://www.obi.pl/elektronika-i-zabezpieczenie-domu/domofony/c/1003',
                                                    'Dzwonki do drzwi': 'https://www.obi.pl/elektronika-i-zabezpieczenie-domu/dzwonki-do-drzwi/c/1002',
                                                    'Komputery oraz multimedia': 'https://www.obi.pl/elektronika-i-zabezpieczenie-domu/komputery-oraz-multimedia/c/983',
                                                    'Latarki': 'https://www.obi.pl/elektronika-i-zabezpieczenie-domu/latarki/c/740',
                                                    'Stacje pogodowe': 'https://www.obi.pl/elektronika-i-zabezpieczenie-domu/stacje-pogodowe/c/821',
                                                    'Sterowanie domem': 'https://www.obi.pl/elektronika-i-zabezpieczenie-domu/sterowanie-domem/c/1004',
                                                    'Telefony': 'https://www.obi.pl/elektronika-i-zabezpieczenie-domu/telefony/c/985',
                                                    'Zabezpieczenie domu': 'https://www.obi.pl/elektronika-i-zabezpieczenie-domu/zabezpieczenie-domu/c/677',
                                                    'Zegarki i budziki': 'https://www.obi.pl/elektronika-i-zabezpieczenie-domu/zegarki-i-budziki/c/771'},
              'Fotowoltaika': 'https://www.obi.pl/technika/fotowoltaika/c/684',
              'Instalacja elektryczna': {'Akcesoria do montażu lamp': 'https://www.obi.pl/instalacja-elektryczna/akcesoria-do-montazu-lamp/c/1769',
                                         'Instalacje elektryczne': 'https://www.obi.pl/instalacja-elektryczna/instalacje-elektryczne/c/2681',
                                         'Przedłużacze': 'https://www.obi.pl/instalacja-elektryczna/przedluzacze/c/2685',
                                         'Przedłużacze na bębnach': 'https://www.obi.pl/instalacja-elektryczna/przedluzacze-na-bebnach/c/2684',
                                         'Rozgałęziacze i listwy zabezpieczające': 'https://www.obi.pl/instalacja-elektryczna/rozgaleziacze-i-listwy-zabezpieczajace/c/2629',
                                         'Serie wyłączników': 'https://www.obi.pl/instalacja-elektryczna/serie-wylacznikow/c/2641',
                                         'Układanie i mocowanie kabli': 'https://www.obi.pl/instalacja-elektryczna/ukladanie-i-mocowanie-kabli/c/2683',
                                         'Wtyczki, gniazda, adaptery': 'https://www.obi.pl/instalacja-elektryczna/wtyczki-gniazda-adaptery/c/2682'},
              'Kominki i piece': {'Akcesoria kominkowe': 'https://www.obi.pl/kominki-i-piece/akcesoria-kominkowe/c/1106',
                                  'Kominki': 'https://www.obi.pl/kominki-i-piece/kominki/c/456',
                                  'Kominki elektryczne': 'https://www.obi.pl/kominki-i-piece/kominki-elektryczne/c/4360',
                                  'Kotły': 'https://www.obi.pl/kominki-i-piece/kotly/c/236',
                                  'Nagrzewnice': 'https://www.obi.pl/kominki-i-piece/nagrzewnice/c/818',
                                  'Paliwa': 'https://www.obi.pl/kominki-i-piece/paliwa/c/214',
                                  'Piece gazowe': 'https://www.obi.pl/kominki-i-piece/piece-gazowe/c/1105',
                                  'Piece na pellet': 'https://www.obi.pl/kominki-i-piece/piece-na-pellet/c/1759'},
              'Maszyny czyszczące': {'Myjki wysokociśnieniowe i akcesoria': 'https://www.obi.pl/maszyny-czyszczace/myjki-wysokocisnieniowe-i-akcesoria/c/3095',
                                     'Odkurzacze, praca na mokro i sucho oraz akcesoria': 'https://www.obi.pl/maszyny-czyszczace/odkurzacze-praca-na-mokro-i-sucho-oraz-akcesoria/c/3104'},
              'Maszyny i urządzenia budowlane': {'Specjalne maszyny': 'https://www.obi.pl/maszyny-i-urzadzenia-budowlane/specjalne-maszyny/c/1934',
                                                 'Sprężarki i akcesoria': 'https://www.obi.pl/maszyny-i-urzadzenia-budowlane/sprezarki-i-akcesoria/c/3097',
                                                 'Zagęszczarki': 'https://www.obi.pl/maszyny-i-urzadzenia-budowlane/zageszczarki/c/1412'},
              'Narzędzia ręczne': {'Dłuta, zdzieraki i heble': 'https://www.obi.pl/narzedzia-reczne/dluta-zdzieraki-i-heble/c/1328',
                                   'Gwintowniki': 'https://www.obi.pl/narzedzia-reczne/gwintowniki/c/1336',
                                   'Klucze i zestawy kluczy': 'https://www.obi.pl/narzedzia-reczne/klucze-i-zestawy-kluczy/c/1332',
                                   'Młotki': 'https://www.obi.pl/narzedzia-reczne/mlotki/c/1333',
                                   'Narzędzia i urządzenia pomiarowe': 'https://www.obi.pl/narzedzia-reczne/narzedzia-i-urzadzenia-pomiarowe/c/1324',
                                   'Narzędzia murarskie i glazurnicze': 'https://www.obi.pl/narzedzia-reczne/narzedzia-murarskie-i-glazurnicze/c/1323',
                                   'Noże': 'https://www.obi.pl/narzedzia-reczne/noze/c/1326',
                                   'Nożyce': 'https://www.obi.pl/narzedzia-reczne/nozyce/c/4851',
                                   'Piły i pilniki': 'https://www.obi.pl/narzedzia-reczne/pily-i-pilniki/c/1325',
                                   'Przebijaki i przecinaki': 'https://www.obi.pl/narzedzia-reczne/przebijaki-i-przecinaki/c/1329',
                                   'Smary': 'https://www.obi.pl/narzedzia-reczne/smary/c/1334',
                                   'Szczypce i kombinerki': 'https://www.obi.pl/narzedzia-reczne/szczypce-i-kombinerki/c/1330',
                                   'Wkrętaki': 'https://www.obi.pl/narzedzia-reczne/wkretaki/c/1331',
                                   'Zestawy narzędzi': 'https://www.obi.pl/narzedzia-reczne/zestawy-narzedzi/c/1338',
                                   'Ściski stolarskie i imadła': 'https://www.obi.pl/narzedzia-reczne/sciski-stolarskie-i-imadla/c/1327'},
              'Odśnieżarki i zamiatarki': {'Akcesoria do zamiatarek': 'https://www.obi.pl/odsniezarki-i-zamiatarki/akcesoria-do-zamiatarek/c/3138',
                                           'Akumulatorowe odśnieżarki': 'https://www.obi.pl/odsniezarki-i-zamiatarki/akumulatorowe-odsniezarki/c/2722',
                                           'Elektryczne odśnieżarki': 'https://www.obi.pl/odsniezarki-i-zamiatarki/elektryczne-odsniezarki/c/2721',
                                           'Spalinowe odśnieżarki': 'https://www.obi.pl/odsniezarki-i-zamiatarki/spalinowe-odsniezarki/c/2720',
                                           'Zamiatarki': 'https://www.obi.pl/odsniezarki-i-zamiatarki/zamiatarki/c/2724'},
              'Ogrzewanie, klimatyzacja i wentylatory': {'Elektryczne urządzenia grzewcze': 'https://www.obi.pl/ogrzewanie-klimatyzacja-i-wentylatory/elektryczne-urzadzenia-grzewcze/c/268',
                                                         'Klimatyzatory': 'https://www.obi.pl/ogrzewanie-klimatyzacja-i-wentylatory/klimatyzatory/c/480',
                                                         'Nawilżacze powietrza i pochłaniacze wilgoci': 'https://www.obi.pl/ogrzewanie-klimatyzacja-i-wentylatory/nawilzacze-powietrza-i-pochlaniacze-wilgoci/c/1516',
                                                         'Oczyszczacze powietrza': 'https://www.obi.pl/ogrzewanie-klimatyzacja-i-wentylatory/oczyszczacze-powietrza/c/539',
                                                         'Ogrzewacze tarasowe': 'https://www.obi.pl/ogrzewanie-klimatyzacja-i-wentylatory/ogrzewacze-tarasowe/c/964',
                                                         'Systemy wentylacyjne': 'https://www.obi.pl/ogrzewanie-klimatyzacja-i-wentylatory/systemy-wentylacyjne/c/1066',
                                                         'Technika grzewcza': 'https://www.obi.pl/ogrzewanie-klimatyzacja-i-wentylatory/technika-grzewcza/c/410',
                                                         'Wentylatory': 'https://www.obi.pl/ogrzewanie-klimatyzacja-i-wentylatory/wentylatory/c/775'},
              'Warsztat': {'Artykuły BHP': 'https://www.obi.pl/warsztat/artykuly-bhp/c/1743',
                           'Porządek w warsztacie': 'https://www.obi.pl/warsztat/porzadek-w-warsztacie/c/941',
                           'Skrzynki narzędziowe': 'https://www.obi.pl/warsztat/skrzynki-narzedziowe/c/946',
                           'Walizki i nosidła tekstylne': 'https://www.obi.pl/warsztat/walizki-i-nosidla-tekstylne/c/951',
                           'Wyposażenie warsztatu': 'https://www.obi.pl/warsztat/wyposazenie-warsztatu/c/817'},
             'Akcesoria rowerowe': 'https://www.obi.pl/rowery/akcesoria-rowerowe/c/292'},
 'Mieszkać': {'Akcesoria do malowania i tapetowania': {'Emulsje gruntujące': 'https://www.obi.pl/akcesoria-do-malowania-i-tapetowania/emulsje-gruntujace/c/1285',
                                                       'Kleje': 'https://www.obi.pl/akcesoria-do-malowania-i-tapetowania/kleje/c/1286',
                                                       'Masy szpachlowe i kity': 'https://www.obi.pl/akcesoria-do-malowania-i-tapetowania/masy-szpachlowe-i-kity/c/1303',
                                                       'Materiały ścierne': 'https://www.obi.pl/akcesoria-do-malowania-i-tapetowania/materialy-scierne/c/665',
                                                       'Narzędzia malarskie': 'https://www.obi.pl/akcesoria-do-malowania-i-tapetowania/narzedzia-malarskie/c/1291',
                                                       'Pomoc przy tapetowaniu': 'https://www.obi.pl/akcesoria-do-malowania-i-tapetowania/pomoc-przy-tapetowaniu/c/1307',
                                                       'Rozpuszczalniki i rozcieńczalniki': 'https://www.obi.pl/akcesoria-do-malowania-i-tapetowania/rozpuszczalniki-i-rozcienczalniki/c/1313',
                                                       'Taśmy klejące': 'https://www.obi.pl/akcesoria-do-malowania-i-tapetowania/tasmy-klejace/c/1287',
                                                       'Zabezpieczenie przed malowaniem': 'https://www.obi.pl/akcesoria-do-malowania-i-tapetowania/zabezpieczenie-przed-malowaniem/c/1283'},
              'Artykuły dekoracyjne': {'Dodatki do tworzenia aranżacji': 'https://www.obi.pl/artykuly-dekoracyjne/dodatki-do-tworzenia-aranzacji/c/1681',
                                       'Folie samoprzylepne': 'https://www.obi.pl/artykuly-dekoracyjne/folie-samoprzylepne/c/1159',
                                       'Kreatywne projektowanie ścian': 'https://www.obi.pl/artykuly-dekoracyjne/kreatywne-projektowanie-scian/c/1891',
                                       'Lampiony': 'https://www.obi.pl/artykuly-dekoracyjne/lampiony/c/1684',
                                       'Latarnie na świeczki': 'https://www.obi.pl/artykuly-dekoracyjne/latarnie-na-swieczki/c/4859',
                                       'Naklejki na ścianę': 'https://www.obi.pl/artykuly-dekoracyjne/naklejki-na-sciane/c/1160',
                                       'Obrazy': 'https://www.obi.pl/artykuly-dekoracyjne/obrazy/c/1162',
                                       'Obrusy': 'https://www.obi.pl/artykuly-dekoracyjne/obrusy/c/1164',
                                       'Pozostałe artykuły dekoracyjne': 'https://www.obi.pl/artykuly-dekoracyjne/pozostale-artykuly-dekoracyjne/c/1687',
                                       'Ramy i antyramy': 'https://www.obi.pl/artykuly-dekoracyjne/ramy-i-antyramy/c/192',
                                       'Serwetki papierowe': 'https://www.obi.pl/artykuly-dekoracyjne/serwetki-papierowe/c/1686',
                                       'Sztuczne rośliny': 'https://www.obi.pl/artykuly-dekoracyjne/sztuczne-rosliny/c/1898',
                                       'Tablice korkowe': 'https://www.obi.pl/artykuly-dekoracyjne/tablice-korkowe/c/1798',
                                       'Wazony': 'https://www.obi.pl/artykuly-dekoracyjne/wazony/c/1685',
                                       'Świece': 'https://www.obi.pl/artykuly-dekoracyjne/swiece/c/1835',
                                       'Świeczniki': 'https://www.obi.pl/artykuly-dekoracyjne/swieczniki/c/1832'},
              'Farby i lakiery': {'Emalie': 'https://www.obi.pl/farby-i-lakiery/emalie/c/2985',
                                  'Farby artystyczne': 'https://www.obi.pl/farby-i-lakiery/farby-artystyczne/c/2984',
                                  'Farby do wnętrz': 'https://www.obi.pl/farby-i-lakiery/farby-do-wnetrz/c/2979',
                                  'Farby kreatywne': 'https://www.obi.pl/farby-i-lakiery/farby-kreatywne/c/2988',
                                  'Farby specjalistyczne': 'https://www.obi.pl/farby-i-lakiery/farby-specjalistyczne/c/2981',
                                  'Farby zewnętrzne': 'https://www.obi.pl/farby-i-lakiery/farby-zewnetrzne/c/3713',
                                  'Lakiery specjalistyczne': 'https://www.obi.pl/farby-i-lakiery/lakiery-specjalistyczne/c/2987',
                                  'Lazury i farby do drewna': 'https://www.obi.pl/farby-i-lakiery/lazury-i-farby-do-drewna/c/2991',
                                  'Serwis mieszania farb': 'https://www.obi.pl/farby-i-lakiery/serwis-mieszania-farb/c/3650',
                                  'Spraye': 'https://www.obi.pl/farby-i-lakiery/spraye/c/2986',
                                  'Środki do gruntowania': 'https://www.obi.pl/farby-i-lakiery/srodki-do-gruntowania/c/2982'},
              'Gospodarstwo domowe': {'Drabiny domowe': 'https://www.obi.pl/gospodarstwo-domowe/drabiny-domowe/c/523',
                                      'Pranie i suszenie': 'https://www.obi.pl/gospodarstwo-domowe/pranie-i-suszenie/c/796',
                                      'Produkty przeciw grzybom i pleśni': 'https://www.obi.pl/gospodarstwo-domowe/produkty-przeciw-grzybom-i-plesni/c/1284',
                                      'Przechowywanie i porządek': 'https://www.obi.pl/gospodarstwo-domowe/przechowywanie-i-porzadek/c/885',
                                      'Sprzątanie': 'https://www.obi.pl/gospodarstwo-domowe/sprzatanie/c/1289'},
              'Kreatywne projektowanie': {'Akcesoria dla artystów': 'https://www.obi.pl/kreatywne-projektowanie/akcesoria-dla-artystow/c/1622',
                                          'Modelowanie': 'https://www.obi.pl/kreatywne-projektowanie/modelowanie/c/1625'},
              'Meble': {'Garderoby': 'https://www.obi.pl/meble/garderoby/c/2327',
                        'Hokery': 'https://www.obi.pl/meble/hokery/c/2404',
                        'Krzesła': 'https://www.obi.pl/meble/krzesla/c/2343',
                        'Regaly': 'https://www.obi.pl/meble/regaly/c/2276',
                        'Stoły': 'https://www.obi.pl/meble/stoly/c/2295',
                        'Szafki': 'https://www.obi.pl/meble/szafki/c/2249',
                        'Łóżka': 'https://www.obi.pl/meble/lozka/c/2225'},
              'Oświetlenie': {'Lampy do wnętrz': 'https://www.obi.pl/oswietlenie/lampy-do-wnetrz/c/929',
                              'Lampy zewnętrzne': 'https://www.obi.pl/oswietlenie/lampy-zewnetrzne/c/1404',
                              'Oświetlenie LED': 'https://www.obi.pl/oswietlenie/oswietlenie-led/c/2152',
                              'Żarówki': 'https://www.obi.pl/oswietlenie/zarowki/c/2087'},
              'Podłogi': {'Dodatki do dywanów': 'https://www.obi.pl/podlogi/dodatki-do-dywanow/c/1543',
                          'Dywany': 'https://www.obi.pl/podlogi/dywany/c/2204',
                          'Panele podłogowe i podłogi drewniane': 'https://www.obi.pl/podlogi/panele-podlogowe-i-podlogi-drewniane/c/893',
                          'Wycieraczki': 'https://www.obi.pl/podlogi/wycieraczki/c/327',
                          'Wykładziny podłogowe PCV': 'https://www.obi.pl/podlogi/wykladziny-podlogowe-pcv/c/1544'},
              'Tapety': {'Elementy dekoracyjne': 'https://www.obi.pl/tapety/elementy-dekoracyjne/c/1799',
                         'Izolacje pomieszczeń mieszkalnych': 'https://www.obi.pl/tapety/izolacje-pomieszczen-mieszkalnych/c/1800',
                         'Tapety dekoracyjne': 'https://www.obi.pl/tapety/tapety-dekoracyjne/c/1267',
                         'Tapety do malowania': 'https://www.obi.pl/tapety/tapety-do-malowania/c/1266'},
              'Tekstylia dekoracyjne': {'Koce i narzuty': 'https://www.obi.pl/tekstylia-dekoracyjne/koce-i-narzuty/c/1061',
                                        'Poduszki': 'https://www.obi.pl/tekstylia-dekoracyjne/poduszki/c/1060',
                                        'Pościel': 'https://www.obi.pl/tekstylia-dekoracyjne/posciel/c/1893'},
              'Wszystko wokół okna': {'Karnisze': 'https://www.obi.pl/wszystko-wokol-okna/karnisze/c/1052',
                                      'Karnisze sufitowe': 'https://www.obi.pl/wszystko-wokol-okna/karnisze-sufitowe/c/1050',
                                      'Ochrona przed owadami': 'https://www.obi.pl/wszystko-wokol-okna/ochrona-przed-owadami/c/2196',
                                      'Plisy': 'https://www.obi.pl/wszystko-wokol-okna/plisy/c/1055',
                                      'Rolety': 'https://www.obi.pl/wszystko-wokol-okna/rolety/c/1053',
                                      'Zasłony i firany': 'https://www.obi.pl/wszystko-wokol-okna/zaslony-i-firany/c/1059',
                                      'Żaluzje': 'https://www.obi.pl/wszystko-wokol-okna/zaluzje/c/1054'}},
 'Ogród i wypoczynek': {'Akcesoria ogrodnicze': {'Folie i włóknina': 'https://www.obi.pl/akcesoria-ogrodnicze/folie-i-wloknina/c/1494',
                                                 'Odzież ogrodnicza': 'https://www.obi.pl/akcesoria-ogrodnicze/odziez-ogrodnicza/c/1495',
                                                 'Plony - winiarstwo i przetwórstwo': 'https://www.obi.pl/akcesoria-ogrodnicze/plony-winiarstwo-i-przetworstwo/c/1492',
                                                 'Pozostałe pomoce ogrodnicze': 'https://www.obi.pl/akcesoria-ogrodnicze/pozostale-pomoce-ogrodnicze/c/1493',
                                                 'Termometry i urządzenia miernicze': 'https://www.obi.pl/akcesoria-ogrodnicze/termometry-i-urzadzenia-miernicze/c/1496'},
                        'Artykuły dla zwierząt': {'Budki lęgowe i karmniki dla ptaków': 'https://www.obi.pl/artykuly-dla-zwierzat/budki-legowe-i-karmniki-dla-ptakow/c/3938',
                                                  'Hodowla drobiu': 'https://www.obi.pl/artykuly-dla-zwierzat/hodowla-drobiu/c/3858',
                                                  'Produkty dla psów': 'https://www.obi.pl/artykuly-dla-zwierzat/produkty-dla-psow/c/3747'},
                        'Artykuły zimowe': {'Łopaty do śniegu': 'https://www.obi.pl/artykuly-zimowe/lopaty-do-sniegu/c/1614',
                                            'Ślizgi, sanki': 'https://www.obi.pl/artykuly-zimowe/slizgi-sanki/c/1615',
                                            'Środki do posypywania chodników': 'https://www.obi.pl/artykuly-zimowe/srodki-do-posypywania-chodnikow/c/1618'},
                        'Baseny': {'Baseny rozstawiane': 'https://www.obi.pl/baseny/baseny-rozstawiane/c/4624',
                                   'Czyszczenie basenów': 'https://www.obi.pl/baseny/czyszczenie-basenow/c/4633',
                                   'Natryski zewnętrzne': 'https://www.obi.pl/baseny/natryski-zewnetrzne/c/4822',
                                   'Pielęgnacja basenów': 'https://www.obi.pl/baseny/pielegnacja-basenow/c/4632',
                                   'Pokrywy basenowe': 'https://www.obi.pl/baseny/pokrywy-basenowe/c/4629',
                                   'Technika basenowa': 'https://www.obi.pl/baseny/technika-basenowa/c/4631',
                                   'Zadaszenie basenowe': 'https://www.obi.pl/baseny/zadaszenie-basenowe/c/4746',
                                   'Zewnętrzne wanny z hydromasażem': 'https://www.obi.pl/baseny/zewnetrzne-wanny-z-hydromasazem/c/4627'},
                        'Boże Narodzenie': {'Dekoracje bożonarodzeniowe': 'https://www.obi.pl/boze-narodzenie/dekoracje-bozonarodzeniowe/c/1842'},
                        'Dekoracja ogrodu': 'https://www.obi.pl/ogrod-i-wypoczynek/dekoracja-ogrodu/c/1565',
                        'Domki ogrodowe i akcesoria': {'Akcesoria do domków ogrodowych': 'https://www.obi.pl/domki-ogrodowe-i-akcesoria/akcesoria-do-domkow-ogrodowych/c/3621',
                                                       'Domki drewniane': 'https://www.obi.pl/domki-ogrodowe-i-akcesoria/domki-drewniane/c/3623',
                                                       'Domki narzędziowe metalowe': 'https://www.obi.pl/domki-ogrodowe-i-akcesoria/domki-narzedziowe-metalowe/c/3626',
                                                       'Domki narzędziowe plastikowe': 'https://www.obi.pl/domki-ogrodowe-i-akcesoria/domki-narzedziowe-plastikowe/c/3624'},
                        'Doniczki do sadzenia roślin': {'Akcesoria do doniczek': 'https://www.obi.pl/doniczki-do-sadzenia-roslin/akcesoria-do-doniczek/c/1789',
                                                        'Donice': 'https://www.obi.pl/doniczki-do-sadzenia-roslin/donice/c/757',
                                                        'Doniczki na kwiaty': 'https://www.obi.pl/doniczki-do-sadzenia-roslin/doniczki-na-kwiaty/c/918',
                                                        'Doniczki na zioła': 'https://www.obi.pl/doniczki-do-sadzenia-roslin/doniczki-na-ziola/c/685',
                                                        'Doniczki wiszące': 'https://www.obi.pl/doniczki-do-sadzenia-roslin/doniczki-wiszace/c/525',
                                                        'Doniczki z terakoty': 'https://www.obi.pl/doniczki-do-sadzenia-roslin/doniczki-z-terakoty/c/922',
                                                        'Konewki': 'https://www.obi.pl/doniczki-do-sadzenia-roslin/konewki/c/1517',
                                                        'Misy na rośliny': 'https://www.obi.pl/doniczki-do-sadzenia-roslin/misy-na-rosliny/c/755',
                                                        'Osłonki': 'https://www.obi.pl/doniczki-do-sadzenia-roslin/oslonki/c/934',
                                                        'Podstawki': 'https://www.obi.pl/doniczki-do-sadzenia-roslin/podstawki/c/925',
                                                        'Podstawki na kółkach': 'https://www.obi.pl/doniczki-do-sadzenia-roslin/podstawki-na-kolkach/c/1500',
                                                        'Skrzynki na kwiatki': 'https://www.obi.pl/doniczki-do-sadzenia-roslin/skrzynki-na-kwiatki/c/1862',
                                                        'Spryskiwacze do kwiatów': 'https://www.obi.pl/doniczki-do-sadzenia-roslin/spryskiwacze-do-kwiatow/c/1541',
                                                        'Stojaki na kwiaty': 'https://www.obi.pl/doniczki-do-sadzenia-roslin/stojaki-na-kwiaty/c/1467',
                                                        'Uchwyt do skrzynki balkonowej': 'https://www.obi.pl/doniczki-do-sadzenia-roslin/uchwyt-do-skrzynki-balkonowej/c/2048'},
                        'Doniczki do uprawy': 'https://www.obi.pl/ogrod-i-wypoczynek/doniczki-do-uprawy/c/1790',
                        'Garaże i wiaty garażowe': {'Automaty do bram': 'https://www.obi.pl/garaze-i-wiaty-garazowe/automaty-do-bram/c/1538',
                                                    'Bramy garażowe': 'https://www.obi.pl/garaze-i-wiaty-garazowe/bramy-garazowe/c/1014',
                                                    'Wiaty garażowe': 'https://www.obi.pl/garaze-i-wiaty-garazowe/wiaty-garazowe/c/896'},
                        'Grille': {'Akcesoria do grilla': 'https://www.obi.pl/grille/akcesoria-do-grilla/c/381',
                                   'Grille betonowe': 'https://www.obi.pl/grille/grille-betonowe/c/1274',
                                   'Grille elektryczne': 'https://www.obi.pl/grille/grille-elektryczne/c/270',
                                   'Grille gazowe': 'https://www.obi.pl/grille/grille-gazowe/c/360',
                                   'Grille węglowe': 'https://www.obi.pl/grille/grille-weglowe/c/429',
                                   'Grillo-wędzarnie': 'https://www.obi.pl/grille/grillo-wedzarnie/c/4419',
                                   'Misy paleniskowe': 'https://www.obi.pl/grille/misy-paleniskowe/c/306'},
                        'Kratki ogrodowe i pergole': 'https://www.obi.pl/ogrod-i-wypoczynek/kratki-ogrodowe-i-pergole/c/1564',
                        'Markizy i ochrona przeciwsłoneczna': {'Markizy': 'https://www.obi.pl/markizy-i-ochrona-przeciwsloneczna/markizy/c/908',
                                                               'Parasole ogrodowe': 'https://www.obi.pl/markizy-i-ochrona-przeciwsloneczna/parasole-ogrodowe/c/1476'},
                        'Maszyny ogrodnicze': {'Glebogryzarki': 'https://www.obi.pl/maszyny-ogrodnicze/glebogryzarki/c/1402',
                                               'Kosiarki': 'https://www.obi.pl/maszyny-ogrodnicze/kosiarki/c/626',
                                               'Nożyce do traw i krzewów': 'https://www.obi.pl/maszyny-ogrodnicze/nozyce-do-traw-i-krzewow/c/1390',
                                               'Nożyce do żywopłotu': 'https://www.obi.pl/maszyny-ogrodnicze/nozyce-do-zywoplotu/c/405',
                                               'Odkurzacze i dmuchawy do liści': 'https://www.obi.pl/maszyny-ogrodnicze/odkurzacze-i-dmuchawy-do-lisci/c/1394',
                                               'Piły łańcuchowe': 'https://www.obi.pl/maszyny-ogrodnicze/pily-lancuchowe/c/1377',
                                               'Podkaszarki i kosy': 'https://www.obi.pl/maszyny-ogrodnicze/podkaszarki-i-kosy/c/1386',
                                               'Rozdrabniacze do gałęzi': 'https://www.obi.pl/maszyny-ogrodnicze/rozdrabniacze-do-galezi/c/386',
                                               'Traktory i akcesoria': 'https://www.obi.pl/maszyny-ogrodnicze/traktory-i-akcesoria/c/1375',
                                               'Wertykulatory i aeratory': 'https://www.obi.pl/maszyny-ogrodnicze/wertykulatory-i-aeratory/c/778',
                                               'Łuparki': 'https://www.obi.pl/maszyny-ogrodnicze/luparki/c/436'},
                        'Meble ogrodowe': {'Altanki ogrodowe i pawilony': 'https://www.obi.pl/meble-ogrodowe/altanki-ogrodowe-i-pawilony/c/1453',
                                           'Fotele bujane': 'https://www.obi.pl/meble-ogrodowe/fotele-bujane/c/2425',
                                           'Fotele wiszące': 'https://www.obi.pl/meble-ogrodowe/fotele-wiszace/c/2368',
                                           'Huśtawki ogrodowe': 'https://www.obi.pl/meble-ogrodowe/hustawki-ogrodowe/c/1847',
                                           'Inne meble ogrodowe': 'https://www.obi.pl/meble-ogrodowe/inne-meble-ogrodowe/c/691',
                                           'Komplet ław i ławek do namiotów': 'https://www.obi.pl/meble-ogrodowe/komplet-law-i-lawek-do-namiotow/c/1269',
                                           'Krzesła ogrodowe': 'https://www.obi.pl/meble-ogrodowe/krzesla-ogrodowe/c/1270',
                                           'Leżaki ogrodowe': 'https://www.obi.pl/meble-ogrodowe/lezaki-ogrodowe/c/1272',
                                           'Meble balkonowe': 'https://www.obi.pl/meble-ogrodowe/meble-balkonowe/c/158',
                                           'Meble ogrodowe dla dzieci': 'https://www.obi.pl/meble-ogrodowe/meble-ogrodowe-dla-dzieci/c/348',
                                           'Poduchy ogrodowe': 'https://www.obi.pl/meble-ogrodowe/poduchy-ogrodowe/c/1273',
                                           'Pokrowce': 'https://www.obi.pl/meble-ogrodowe/pokrowce/c/672',
                                           'Stoły ogrodowe': 'https://www.obi.pl/meble-ogrodowe/stoly-ogrodowe/c/1271',
                                           'Zestawy mebli ogrodowych': 'https://www.obi.pl/meble-ogrodowe/zestawy-mebli-ogrodowych/c/289',
                                           'Ławki ogrodowe': 'https://www.obi.pl/meble-ogrodowe/lawki-ogrodowe/c/335'},
                        'Ogrodowe narzędzia ręczne': {'Drobne narzędzia ogrodowe': 'https://www.obi.pl/ogrodowe-narzedzia-reczne/drobne-narzedzia-ogrodowe/c/1484',
                                                      'Narzędzia modułowe': 'https://www.obi.pl/ogrodowe-narzedzia-reczne/narzedzia-modulowe/c/1488',
                                                      'Piły ogrodowe': 'https://www.obi.pl/ogrodowe-narzedzia-reczne/pily-ogrodowe/c/1497',
                                                      'Porządki w ogrodzie': 'https://www.obi.pl/ogrodowe-narzedzia-reczne/porzadki-w-ogrodzie/c/1487',
                                                      'Prace w ziemi': 'https://www.obi.pl/ogrodowe-narzedzia-reczne/prace-w-ziemi/c/1486',
                                                      'Sekatory i nożyce do żywopłotów': 'https://www.obi.pl/ogrodowe-narzedzia-reczne/sekatory-i-nozyce-do-zywoplotow/c/1491',
                                                      'Siekiery': 'https://www.obi.pl/ogrodowe-narzedzia-reczne/siekiery/c/4846',
                                                      'Siewniki i walce': 'https://www.obi.pl/ogrodowe-narzedzia-reczne/siewniki-i-walce/c/723',
                                                      'Szpadle i łopaty': 'https://www.obi.pl/ogrodowe-narzedzia-reczne/szpadle-i-lopaty/c/1489'},
                        'Pielęgnacja i uprawa roślin': {'Herbicydy': 'https://www.obi.pl/pielegnacja-i-uprawa-roslin/herbicydy/c/2737',
                                                        'Kora': 'https://www.obi.pl/pielegnacja-i-uprawa-roslin/kora/c/2732',
                                                        'Nawozy': 'https://www.obi.pl/pielegnacja-i-uprawa-roslin/nawozy/c/2735',
                                                        'Odstraszanie zwierząt': 'https://www.obi.pl/pielegnacja-i-uprawa-roslin/odstraszanie-zwierzat/c/2738',
                                                        'Podłoża': 'https://www.obi.pl/pielegnacja-i-uprawa-roslin/podloza/c/2731',
                                                        'Substraty i dodatki do roślin': 'https://www.obi.pl/pielegnacja-i-uprawa-roslin/substraty-i-dodatki-do-roslin/c/2733',
                                                        'Środki ochrony roślin': 'https://www.obi.pl/pielegnacja-i-uprawa-roslin/srodki-ochrony-roslin/c/2736'},
                        'Podwyższone grządki': {'Akcesoria do podwyższonych grządek': 'https://www.obi.pl/podwyzszone-grzadki/akcesoria-do-podwyzszonych-grzadek/c/4279',
                                                'Podwyższone grządki drewniane': 'https://www.obi.pl/podwyzszone-grzadki/podwyzszone-grzadki-drewniane/c/4275',
                                                'Podwyższone grządki metalowe': 'https://www.obi.pl/podwyzszone-grzadki/podwyzszone-grzadki-metalowe/c/4276',
                                                'Podwyższone grządki plastikowe': 'https://www.obi.pl/podwyzszone-grzadki/podwyzszone-grzadki-plastikowe/c/4277'},
                        'Poidła dla ptaków': 'https://www.obi.pl/ogrod-i-wypoczynek/poidla-dla-ptakow/c/3952',
                        'Porządek w ogrodzie': {'Pojemniki na odpady': 'https://www.obi.pl/porzadek-w-ogrodzie/pojemniki-na-odpady/c/3635',
                                                'Skrzynie na poduszki': 'https://www.obi.pl/porzadek-w-ogrodzie/skrzynie-na-poduszki/c/3639',
                                                'Skrzynie uniwersalne': 'https://www.obi.pl/porzadek-w-ogrodzie/skrzynie-uniwersalne/c/3637',
                                                'Szafki ogrodowe': 'https://www.obi.pl/porzadek-w-ogrodzie/szafki-ogrodowe/c/3632',
                                                'Wyposażenie do ogrodowych systemów porządkowych': 'https://www.obi.pl/porzadek-w-ogrodzie/wyposazenie-do-ogrodowych-systemow-porzadkowych/c/3638'},
                        'Płoty i ogrodzenia': {'Akcesoria do płotów i ogrodzeń': 'https://www.obi.pl/ploty-i-ogrodzenia/akcesoria-do-plotow-i-ogrodzen/c/1469',
                                               'Maty na ogrodzenie': 'https://www.obi.pl/ploty-i-ogrodzenia/maty-na-ogrodzenie/c/1466',
                                               'Ogrodzenia drewniane': 'https://www.obi.pl/ploty-i-ogrodzenia/ogrodzenia-drewniane/c/1865',
                                               'Ogrodzenia metalowe': 'https://www.obi.pl/ploty-i-ogrodzenia/ogrodzenia-metalowe/c/1864',
                                               'Panele ogrodzeniowe i siatka ogrodzeniowa': 'https://www.obi.pl/ploty-i-ogrodzenia/panele-ogrodzeniowe-i-siatka-ogrodzeniowa/c/1468'},
                        'Rowery': {'Akcesoria rowerowe': 'https://www.obi.pl/rowery/akcesoria-rowerowe/c/292',
                                   'Rower elektryczny': 'https://www.obi.pl/rowery/rower-elektryczny/c/275'},
                        'Rośliny': {'Bukiety': 'https://www.obi.pl/rosliny/bukiety/c/1980',
                                    'Byliny': 'https://www.obi.pl/rosliny/byliny/c/1955',
                                    'Drzewa oliwne': 'https://www.obi.pl/rosliny/drzewa-oliwne/c/4852',
                                    'Drzewka do domów': 'https://www.obi.pl/rosliny/drzewka-do-domow/c/4156',
                                    'Krzewy': 'https://www.obi.pl/rosliny/krzewy/c/4122',
                                    'Kwiaty doniczkowe': 'https://www.obi.pl/rosliny/kwiaty-doniczkowe/c/1554',
                                    'Kwiaty na balkon': 'https://www.obi.pl/rosliny/kwiaty-na-balkon/c/2069',
                                    'Nasiona i cebulki': 'https://www.obi.pl/rosliny/nasiona-i-cebulki/c/1522',
                                    'Owoce i warzywa': 'https://www.obi.pl/rosliny/owoce-i-warzywa/c/2076',
                                    'Rośliny okrywowe': 'https://www.obi.pl/rosliny/rosliny-okrywowe/c/4267',
                                    'Rośliny pnące': 'https://www.obi.pl/rosliny/rosliny-pnace/c/1950',
                                    'Rośliny stawowe': 'https://www.obi.pl/rosliny/rosliny-stawowe/c/2072',
                                    'Róże': 'https://www.obi.pl/rosliny/roze/c/1956',
                                    'Sadzonki żywopłotu': 'https://www.obi.pl/rosliny/sadzonki-zywoplotu/c/2160',
                                    'Trawy': 'https://www.obi.pl/rosliny/trawy/c/4144'},
                        'Szklarnie i akcesoria': {'Akcesoria do szklarni': 'https://www.obi.pl/szklarnie-i-akcesoria/akcesoria-do-szklarni/c/1448',
                                                  'Szklarnie': 'https://www.obi.pl/szklarnie-i-akcesoria/szklarnie/c/371'},
                        'Taras i ścieżki ogrodowe': {'Akcesoria do zadaszeń tarasów': 'https://www.obi.pl/taras-i-sciezki-ogrodowe/akcesoria-do-zadaszen-tarasow/c/1452',
                                                     'Zadaszenie tarasu': 'https://www.obi.pl/taras-i-sciezki-ogrodowe/zadaszenie-tarasu/c/750'},
                        'Wielkanoc': 'https://www.obi.pl/ogrod-i-wypoczynek/wielkanoc/c/4828',
                        'Woda w ogrodzie': {'Akcesoria do oczek wodnych': 'https://www.obi.pl/woda-w-ogrodzie/akcesoria-do-oczek-wodnych/c/1381',
                                            'Fontanny ogrodowe': 'https://www.obi.pl/woda-w-ogrodzie/fontanny-ogrodowe/c/339',
                                            'Pistolety ogrodowe': 'https://www.obi.pl/woda-w-ogrodzie/pistolety-ogrodowe/c/1424',
                                            'Pompy wodne': 'https://www.obi.pl/woda-w-ogrodzie/pompy-wodne/c/1422',
                                            'Systemy nawadniania': 'https://www.obi.pl/woda-w-ogrodzie/systemy-nawadniania/c/1425',
                                            'Węże ogrodowe i wózki na węże ogrodowe': 'https://www.obi.pl/woda-w-ogrodzie/weze-ogrodowe-i-wozki-na-weze-ogrodowe/c/1423',
                                            'Zbiorniki na deszczówkę i akcesoria': 'https://www.obi.pl/woda-w-ogrodzie/zbiorniki-na-deszczowke-i-akcesoria/c/1426',
                                            'Złączki do wody': 'https://www.obi.pl/woda-w-ogrodzie/zlaczki-do-wody/c/1427'},
                        'Wypoczynek i zabawa': {'Akcesoria kempingowe': 'https://www.obi.pl/wypoczynek-i-zabawa/akcesoria-kempingowe/c/1125',
                                                'Dla dzieci do ogrodu': 'https://www.obi.pl/wypoczynek-i-zabawa/dla-dzieci-do-ogrodu/c/353',
                                                'Gry i zabawy dla dzieci': 'https://www.obi.pl/wypoczynek-i-zabawa/gry-i-zabawy-dla-dzieci/c/1807',
                                                'Sporty wodne': 'https://www.obi.pl/wypoczynek-i-zabawa/sporty-wodne/c/4820',
                                                'Sporty związane z pływaniem na łodziach': 'https://www.obi.pl/wypoczynek-i-zabawa/sporty-zwiazane-z-plywaniem-na-lodziach/c/210',
                                                'Trampoliny': 'https://www.obi.pl/wypoczynek-i-zabawa/trampoliny/c/4268',
                                                'Zabawki do wody': 'https://www.obi.pl/wypoczynek-i-zabawa/zabawki-do-wody/c/4634'}},
 'Budować': {'Akcesoria do płytek': {'Fugi do płytek': 'https://www.obi.pl/akcesoria-do-plytek/fugi-do-plytek/c/318',
                                     'Kleje do płytek': 'https://www.obi.pl/akcesoria-do-plytek/kleje-do-plytek/c/310',
                                     'Pozostałe akcesoria do płytek': 'https://www.obi.pl/akcesoria-do-plytek/pozostale-akcesoria-do-plytek/c/696',
                                     'Profile do płytek': 'https://www.obi.pl/akcesoria-do-plytek/profile-do-plytek/c/311',
                                     'Silikony i akryle': 'https://www.obi.pl/akcesoria-do-plytek/silikony-i-akryle/c/317'},
             'Architektura ogrodowa': {'Deski tarasowe': 'https://www.obi.pl/architektura-ogrodowa/deski-tarasowe/c/1464',
                                       'Kostka brukowa': 'https://www.obi.pl/architektura-ogrodowa/kostka-brukowa/c/608',
                                       'Obrzeża, palisady,krawężniki, murki': 'https://www.obi.pl/architektura-ogrodowa/obrzeza-palisady-krawezniki-murki/c/1281',
                                       'Podesty': 'https://www.obi.pl/architektura-ogrodowa/podesty/c/1463',
                                       'Płyty tarasowe i chodnikowe': 'https://www.obi.pl/architektura-ogrodowa/plyty-tarasowe-i-chodnikowe/c/1279',
                                       'Żwir, grys i kamienie ozdobne': 'https://www.obi.pl/architektura-ogrodowa/zwir-grys-i-kamienie-ozdobne/c/1382'},
             'Budowa mebli': {'Blaty kuchenne': 'https://www.obi.pl/budowa-mebli/blaty-kuchenne/c/916',
                              'Drzwiczki ażurowe': 'https://www.obi.pl/budowa-mebli/drzwiczki-azurowe/c/513',
                              'Płyty do budowy mebli': 'https://www.obi.pl/budowa-mebli/plyty-do-budowy-mebli/c/917'},
             'Daszki nad drzwi': 'https://www.obi.pl/budowac/daszki-nad-drzwi/c/783',
             'Drewno budowlane': {'Boazeria': 'https://www.obi.pl/drewno-budowlane/boazeria/c/1824',
                                  'Drewno heblowane': 'https://www.obi.pl/drewno-budowlane/drewno-heblowane/c/1822',
                                  'Drewno nieheblowane': 'https://www.obi.pl/drewno-budowlane/drewno-nieheblowane/c/1540',
                                  'Listwy modelarskie': 'https://www.obi.pl/drewno-budowlane/listwy-modelarskie/c/1820',
                                  'Płyty konstrukcyjne i meblowe': 'https://www.obi.pl/drewno-budowlane/plyty-konstrukcyjne-i-meblowe/c/776'},
             'Drzwi': {'Akcesoria do drzwi': 'https://www.obi.pl/drzwi/akcesoria-do-drzwi/c/959',
                       'Drzwi harmonijkowe': 'https://www.obi.pl/drzwi/drzwi-harmonijkowe/c/954',
                       'Drzwi stalowe': 'https://www.obi.pl/drzwi/drzwi-stalowe/c/956',
                       'Drzwi szklane i drzwi przesuwne': 'https://www.obi.pl/drzwi/drzwi-szklane-i-drzwi-przesuwne/c/955',
                       'Drzwi wewnętrzne': 'https://www.obi.pl/drzwi/drzwi-wewnetrzne/c/953',
                       'Drzwi zewnętrzne': 'https://www.obi.pl/drzwi/drzwi-zewnetrzne/c/957',
                       'Odbojniki do drzwi': 'https://www.obi.pl/drzwi/odbojniki-do-drzwi/c/970',
                       'Ościeżnice drzwiowe': 'https://www.obi.pl/drzwi/oscieznice-drzwiowe/c/4849'},
             'Materiały budowlane': {'Akcesoria budowlane': 'https://www.obi.pl/materialy-budowlane/akcesoria-budowlane/c/176',
                                     'Cegły, bloczki i materiały sypkie': 'https://www.obi.pl/materialy-budowlane/cegly-bloczki-i-materialy-sypkie/c/720',
                                     'Materiały izolacyjne': 'https://www.obi.pl/materialy-budowlane/materialy-izolacyjne/c/233',
                                     'Odprowadzenia wody i drenaż': 'https://www.obi.pl/materialy-budowlane/odprowadzenia-wody-i-drenaz/c/284',
                                     'Pokrycia dachowe i rynny dachowe': 'https://www.obi.pl/materialy-budowlane/pokrycia-dachowe-i-rynny-dachowe/c/1158',
                                     'Tynk, zaprawa i cement': 'https://www.obi.pl/materialy-budowlane/tynk-zaprawa-i-cement/c/619',
                                     'Wykończenie w suchej zabudowie': 'https://www.obi.pl/materialy-budowlane/wykonczenie-w-suchej-zabudowie/c/764'},
             'Okna': {'Akcesoria okienne': 'https://www.obi.pl/okna/akcesoria-okienne/c/4564',
                      'Okna dachowe': 'https://www.obi.pl/okna/okna-dachowe/c/231',
                      'Okna pcv': 'https://www.obi.pl/okna/okna-pcv/c/961',
                      'Parapety': 'https://www.obi.pl/okna/parapety/c/915'},
             'Panele ścienne i akcesoria': {'Akcesoria do montażu paneli': 'https://www.obi.pl/panele-scienne-i-akcesoria/akcesoria-do-montazu-paneli/c/1539',
                                            'Panele ścienne': 'https://www.obi.pl/panele-scienne-i-akcesoria/panele-scienne/c/243'},
             'Płytki': {'Cokoły i stopnice': 'https://www.obi.pl/plytki/cokoly-i-stopnice/c/683',
                        'Dekory i listwy': 'https://www.obi.pl/plytki/dekory-i-listwy/c/1152',
                        'Kamienie dekoracyjne i klinkiery': 'https://www.obi.pl/plytki/kamienie-dekoracyjne-i-klinkiery/c/481',
                        'Mozaiki': 'https://www.obi.pl/plytki/mozaiki/c/572',
                        'Płytki podłogowe': 'https://www.obi.pl/plytki/plytki-podlogowe/c/1150',
                        'Płytki ścienne': 'https://www.obi.pl/plytki/plytki-scienne/c/786'},
             'Schody i balustrady': {'Poręcze i balustrady': 'https://www.obi.pl/schody-i-balustrady/porecze-i-balustrady/c/962',
                                     'Schody wewnętrzne': 'https://www.obi.pl/schody-i-balustrady/schody-wewnetrzne/c/445'}},
 'Łazienka': {'Akcesoria do umywalek': {'Zatyczki do odpływów': 'https://www.obi.pl/akcesoria-do-umywalek/zatyczki-do-odplywow/c/3349'},
              'Akcesoria do łazienki': {'Bezpieczeństwo w łazience': 'https://www.obi.pl/akcesoria-do-lazienki/bezpieczenstwo-w-lazience/c/1197',
                                        'Dozowniki na mydło': 'https://www.obi.pl/akcesoria-do-lazienki/dozowniki-na-mydlo/c/1189',
                                        'Drążki prysznicowe': 'https://www.obi.pl/akcesoria-do-lazienki/drazki-prysznicowe/c/1195',
                                        'Kosze łazienkowe na śmieci': 'https://www.obi.pl/akcesoria-do-lazienki/kosze-lazienkowe-na-smieci/c/1190',
                                        'Szczotki do WC': 'https://www.obi.pl/akcesoria-do-lazienki/szczotki-do-wc/c/1191',
                                        'Zasłony prysznicowe': 'https://www.obi.pl/akcesoria-do-lazienki/zaslony-prysznicowe/c/1193',
                                        'Zestawy akcesoriów do łazienki': 'https://www.obi.pl/akcesoria-do-lazienki/zestawy-akcesoriow-do-lazienki/c/1192'},
              'Armatura łazienkowa': {'Akcesoria do armatury': 'https://www.obi.pl/armatura-lazienkowa/akcesoria-do-armatury/c/3354',
                                      'Akcesoria prysznicowe': 'https://www.obi.pl/armatura-lazienkowa/akcesoria-prysznicowe/c/1214',
                                      'Baterie bidetowe': 'https://www.obi.pl/armatura-lazienkowa/baterie-bidetowe/c/1888',
                                      'Baterie do umywalek': 'https://www.obi.pl/armatura-lazienkowa/baterie-do-umywalek/c/800',
                                      'Baterie prysznicowe': 'https://www.obi.pl/armatura-lazienkowa/baterie-prysznicowe/c/1221',
                                      'Baterie wannowe': 'https://www.obi.pl/armatura-lazienkowa/baterie-wannowe/c/790',
                                      'Baterie z termostatem': 'https://www.obi.pl/armatura-lazienkowa/baterie-z-termostatem/c/1222'},
              'Instalacja sanitarna': {'Akcesoria do syfonów': 'https://www.obi.pl/instalacja-sanitarna/akcesoria-do-syfonow/c/3529',
                                       'Elementy do zabudowy': 'https://www.obi.pl/instalacja-sanitarna/elementy-do-zabudowy/c/3556',
                                       'Liczniki wody': 'https://www.obi.pl/instalacja-sanitarna/liczniki-wody/c/3568',
                                       'Mocowania do rur': 'https://www.obi.pl/instalacja-sanitarna/mocowania-do-rur/c/3481',
                                       'Narzędzia sanitarne': 'https://www.obi.pl/instalacja-sanitarna/narzedzia-sanitarne/c/3597',
                                       'Przyłącza do WC': 'https://www.obi.pl/instalacja-sanitarna/przylacza-do-wc/c/3571',
                                       'Płytki z przyciskami': 'https://www.obi.pl/instalacja-sanitarna/plytki-z-przyciskami/c/3377',
                                       'Rury HT': 'https://www.obi.pl/instalacja-sanitarna/rury-ht/c/3436',
                                       'Rury wodne': 'https://www.obi.pl/instalacja-sanitarna/rury-wodne/c/3567',
                                       'Spłuczki': 'https://www.obi.pl/instalacja-sanitarna/spluczki/c/3533',
                                       'Syfony': 'https://www.obi.pl/instalacja-sanitarna/syfony/c/3520',
                                       'Systemy uzdatniania wody': 'https://www.obi.pl/instalacja-sanitarna/systemy-uzdatniania-wody/c/3559',
                                       'Węże przyłączeniowe': 'https://www.obi.pl/instalacja-sanitarna/weze-przylaczeniowe/c/3358',
                                       'Zawory': 'https://www.obi.pl/instalacja-sanitarna/zawory/c/3552',
                                       'Złączki': 'https://www.obi.pl/instalacja-sanitarna/zlaczki/c/3401'},
              'Kabiny, brodziki i akcesoria': {'Akcesoria do wanien': 'https://www.obi.pl/kabiny-brodziki-i-akcesoria/akcesoria-do-wanien/c/1233',
                                               'Brodziki prysznicowe': 'https://www.obi.pl/kabiny-brodziki-i-akcesoria/brodziki-prysznicowe/c/1225',
                                               'Drzwi prysznicowe': 'https://www.obi.pl/kabiny-brodziki-i-akcesoria/drzwi-prysznicowe/c/4404',
                                               'Kabiny prysznicowe': 'https://www.obi.pl/kabiny-brodziki-i-akcesoria/kabiny-prysznicowe/c/1226',
                                               'Odpływy prysznicowe': 'https://www.obi.pl/kabiny-brodziki-i-akcesoria/odplywy-prysznicowe/c/4407',
                                               'Uszczelki do pryszniców': 'https://www.obi.pl/kabiny-brodziki-i-akcesoria/uszczelki-do-prysznicow/c/4406',
                                               'Ścianki prysznicowe': 'https://www.obi.pl/kabiny-brodziki-i-akcesoria/scianki-prysznicowe/c/4403'},
              'Lustra łazienkowe': {'Lusterka kosmetyczne': 'https://www.obi.pl/lustra-lazienkowe/lusterka-kosmetyczne/c/1182',
                                    'Lustra': 'https://www.obi.pl/lustra-lazienkowe/lustra/c/1183'},
              'Meble łazienkowe': {'Akcesoria do mebli łazienkowych': 'https://www.obi.pl/meble-lazienkowe/akcesoria-do-mebli-lazienkowych/c/1180',
                                   'Szafki łazienkowe': 'https://www.obi.pl/meble-lazienkowe/szafki-lazienkowe/c/4165',
                                   'Umywalki': 'https://www.obi.pl/meble-lazienkowe/umywalki/c/4368',
                                   'Zestawy mebli łazienkowych': 'https://www.obi.pl/meble-lazienkowe/zestawy-mebli-lazienkowych/c/1177'},
              'Sauna i wellness': {'Sauny i piece do saun': 'https://www.obi.pl/sauna-i-wellness/sauny-i-piece-do-saun/c/1236',
                                   'Wanny z hydromasażem': 'https://www.obi.pl/sauna-i-wellness/wanny-z-hydromasazem/c/1241'},
              'Tekstylia łazienkowe': {'Dywaniki i maty łazienkowe': 'https://www.obi.pl/tekstylia-lazienkowe/dywaniki-i-maty-lazienkowe/c/1186',
                                       'Ręczniki': 'https://www.obi.pl/tekstylia-lazienkowe/reczniki/c/1187'},
              'Toalety': {'Akcesoria do desek sedesowych': 'https://www.obi.pl/toalety/akcesoria-do-desek-sedesowych/c/1201',
                          'Bidety': 'https://www.obi.pl/toalety/bidety/c/4168',
                          'Deski sedesowe': 'https://www.obi.pl/toalety/deski-sedesowe/c/1199',
                          'Kompakty i miski WC wiszące': 'https://www.obi.pl/toalety/kompakty-i-miski-wc-wiszace/c/4386',
                          'Pisuary': 'https://www.obi.pl/toalety/pisuary/c/4184',
                          'Zestawy WC': 'https://www.obi.pl/toalety/zestawy-wc/c/1207'},
              'Umywalki i półpostumenty': {'Umywalki blatowe': 'https://www.obi.pl/umywalki-i-polpostumenty/umywalki-blatowe/c/4364',
                                           'Umywalki nablatowe': 'https://www.obi.pl/umywalki-i-polpostumenty/umywalki-nablatowe/c/4365'},
              'Wanny': {'Akcesoria wannowe': 'https://www.obi.pl/wanny/akcesoria-wannowe/c/4161',
                        'Parawany wannowe': 'https://www.obi.pl/wanny/parawany-wannowe/c/1232',
                        'Wanny narożne': 'https://www.obi.pl/wanny/wanny-narozne/c/4381',
                        'Wanny prostokątne': 'https://www.obi.pl/wanny/wanny-prostokatne/c/4401',
                        'Wanny wolnostojące': 'https://www.obi.pl/wanny/wanny-wolnostojace/c/4380'}},
 'Kuchnia': {'AGD': {'Kuchenki': 'https://www.obi.pl/agd/kuchenki/c/4436',
                     'Lodówki': 'https://www.obi.pl/agd/lodowki/c/4336',
                     'Małe urządzenia kuchenne': 'https://www.obi.pl/agd/male-urzadzenia-kuchenne/c/1138',
                     'Piekarniki': 'https://www.obi.pl/agd/piekarniki/c/4430',
                     'Pralki': 'https://www.obi.pl/agd/pralki/c/4326',
                     'Przygotowanie kawy i espresso': 'https://www.obi.pl/agd/przygotowanie-kawy-i-espresso/c/1133',
                     'Płyty grzewcze': 'https://www.obi.pl/agd/plyty-grzewcze/c/4442',
                     'Zamrażarka': 'https://www.obi.pl/agd/zamrazarka/c/4347',
                     'Zmywarki do naczyń': 'https://www.obi.pl/agd/zmywarki-do-naczyn/c/4426'},
             'Aneksy kuchenne': {'Zestawy mebli kuchennych': 'https://www.obi.pl/aneksy-kuchenne/zestawy-mebli-kuchennych/c/4283'},
             'Baterie kuchenne': {'Armatura dwuuchwytowa': 'https://www.obi.pl/baterie-kuchenne/armatura-dwuuchwytowa/c/4355',
                                  'Jednouchwytowe baterie z mieszaczem': 'https://www.obi.pl/baterie-kuchenne/jednouchwytowe-baterie-z-mieszaczem/c/4354'},
             'Meble kuchenne': {'Ekrany kuchenne': 'https://www.obi.pl/meble-kuchenne/ekrany-kuchenne/c/2223',
                                'Szafki kuchenne': 'https://www.obi.pl/meble-kuchenne/szafki-kuchenne/c/4290'},
             'Okapy kuchenne': {'Filtry do okapów': 'https://www.obi.pl/okapy-kuchenne/filtry-do-okapow/c/4325',
                                'Okapy nad wyspę': 'https://www.obi.pl/okapy-kuchenne/okapy-nad-wyspe/c/4312',
                                'Okapy płaskie': 'https://www.obi.pl/okapy-kuchenne/okapy-plaskie/c/4317',
                                'Okapy stołowe': 'https://www.obi.pl/okapy-kuchenne/okapy-stolowe/c/4318',
                                'Okapy ścienne': 'https://www.obi.pl/okapy-kuchenne/okapy-scienne/c/4314'},
             'Woda ciepła': {'Bojlery': 'https://www.obi.pl/woda-ciepla/bojlery/c/1065',
                             'Przepływowe ogrzewacze wody': 'https://www.obi.pl/woda-ciepla/przeplywowe-ogrzewacze-wody/c/1064'},
             'Wyposażenie kuchni': {'Akcesoria kuchenne': 'https://www.obi.pl/wyposazenie-kuchni/akcesoria-kuchenne/c/1890',
                                    'Części zamienne do armatury kuchennej': 'https://www.obi.pl/wyposazenie-kuchni/czesci-zamienne-do-armatury-kuchennej/c/3395',
                                    'Garnki i patelnie': 'https://www.obi.pl/wyposazenie-kuchni/garnki-i-patelnie/c/4302',
                                    'Naczynia': 'https://www.obi.pl/wyposazenie-kuchni/naczynia/c/4303',
                                    'Suszarki ociekowe': 'https://www.obi.pl/wyposazenie-kuchni/suszarki-ociekowe/c/4308',
                                    'Systemy porządkowe do kuchni': 'https://www.obi.pl/wyposazenie-kuchni/systemy-porzadkowe-do-kuchni/c/4309',
                                    'Systemy wodne': 'https://www.obi.pl/wyposazenie-kuchni/systemy-wodne/c/1135'},
             'Zlewy i zlewozmywaki': {'Akcesoria do zlewozmywaków': 'https://www.obi.pl/zlewy-i-zlewozmywaki/akcesoria-do-zlewozmywakow/c/1149',
                                      'Zlewozmywaki ceramiczne': 'https://www.obi.pl/zlewy-i-zlewozmywaki/zlewozmywaki-ceramiczne/c/4358',
                                      'Zlewozmywaki granitowe': 'https://www.obi.pl/zlewy-i-zlewozmywaki/zlewozmywaki-granitowe/c/1148',
                                      'Zlewozmywaki ze stali szlachetnej': 'https://www.obi.pl/zlewy-i-zlewozmywaki/zlewozmywaki-ze-stali-szlachetnej/c/1147'}}}

SKIP_URL_PARTS = (
    "karta-podarunkowa",
    "karty-podarunkowe",
    "/inspiracje/",
    "/porady/",
    "/service/",
    "/uslugi/",
    "/customer",
    "/account",
    "/cart",
    "/checkout",
)

d1 = {
    "headless": True,
    "driver_type": "chromium",
    "timeout": 30 * 1000,
    "window_size": (1900, 1200),
    "wait_until": "domcontentloaded",
    "render_time": 3,
}
d2 = {
    "lang": "Lang.Polish",
    "headless": True,
    "wait_for_complete_page_load": True,
}


def _int_env(name, default=0):
    try:
        return int(os.environ.get(name, default) or default)
    except ValueError:
        return default


def _cache_dir():
    path = BASE_DIR / settings.CACHE_DIR / CACHE_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cache_file(url, kind="html"):
    return _cache_dir() / f"{hash_md5(kind + url)}.json"


def _decode_page(page):
    body = getattr(page, "body", "")
    if isinstance(body, bytes):
        return body.decode(getattr(page, "encoding", None) or "utf-8", errors="ignore")
    if isinstance(body, str) and body:
        return body
    html = getattr(page, "html_content", "")
    return str(html or "")


def _is_bad_html(text, status=None):
    if not text or len(text) < 1000:
        return True
    if status and int(status) >= 500:
        return True
    low = text.lower()
    return "cf-challenge" in low or "just a moment" in low or "access denied" in low


def fetch_text(url, *, cache=True, kind="html"):
    full_url = normalize_url(url, HOME_URL, keep_query=True)
    cache_path = _cache_file(full_url, kind)
    if cache and cache_path.exists():
        try:
            with cache_path.open("r", encoding="utf-8") as f:
                return json.load(f)["text"], full_url
        except Exception as exc:
            logger.warning(f"读取 OBI 缓存失败: {cache_path} {exc}")

    page = Fetcher.get(
        full_url,
        timeout=30,
        retries=2,
        impersonate=["chrome", "edge"],
        stealthy_headers=True,
        headers=REQUEST_HEADERS,
    )
    text = _decode_page(page)
    final_url = getattr(page, "url", full_url) or full_url
    if cache and not _is_bad_html(text, getattr(page, "status", None)):
        try:
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump({"url": final_url, "text": text}, f, ensure_ascii=False)
        except Exception as exc:
            logger.warning(f"写入 OBI 缓存失败: {full_url} {exc}")
    return text, final_url


def normalize_url(url, base=SITE, keep_query=False):
    if not url:
        return ""
    full = urljoin(base, str(url).strip())
    parsed = urlparse(full)
    if parsed.scheme not in {"http", "https"}:
        return ""
    query = parsed.query if keep_query else ""
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", query, ""))


def page_url(base_url, page_num):
    if page_num <= 1:
        return normalize_url(base_url, HOME_URL, keep_query=True)
    parsed = urlparse(normalize_url(base_url, HOME_URL, keep_query=True))
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["page"] = str(page_num)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", urlencode(query), ""))


def uniq_keep_order(values, key_func=None):
    seen = set()
    result = []
    for value in values:
        key = key_func(value) if key_func else value
        if value in (None, "") or key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def clean_text(value):
    if value is None:
        return ""
    text = BeautifulSoup(str(value), "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def image_key(url):
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) >= 2 and "bilder.obi" in parsed.netloc:
        return f"{parsed.netloc}/{parts[0]}"
    return f"{parsed.netloc}{parsed.path}".lower()


def money_value(value):
    if value in (None, ""):
        return None
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        text = str(value).replace("\xa0", " ").replace("zł", "").strip()
        text = text.replace(" ", "").replace(".", "").replace(",", ".")
        match = re.search(r"\d+(?:\.\d+)?", text)
        return round(float(match.group()), 2) if match else None


def extract_initial_state(html):
    pos = (html or "").find("window.__INITIAL_STATE__=")
    if pos < 0:
        return {}
    end = html.find("</script>", pos)
    if end < 0:
        end = len(html)
    script = html[pos:end]
    expr = script.split("=", 1)[1].strip().rstrip(";")
    try:
        return json.loads(ast.literal_eval(expr))
    except Exception as exc:
        logger.warning(f"OBI __INITIAL_STATE__ 解析失败: {exc}")
        return {}


def extract_search_state(html):
    state = extract_initial_state(html)
    return (((state.get("pinia") or {}).get("suche") or {}).get("suchergebnis") or {})


def category_filter(search_state):
    filters = ((search_state.get("filter") or {}).get("sortierbareFilter") or [])
    for item in filters:
        if item.get("filterAuspraegung") == "kategorieFilter":
            return item
    return {}


def category_leaf_items(top_url):
    html, _ = fetch_text(top_url, kind="category_tree")
    search_state = extract_search_state(html)
    roots = category_filter(search_state).get("kategorien") or []
    leaves = []

    def walk(node, path):
        name = clean_text(node.get("name"))
        if not name:
            return
        next_path = path + [name]
        children = node.get("unterKategorien") or []
        if children:
            for child in children:
                walk(child, next_path)
            return
        url_path = node.get("urlPfad")
        if not url_path:
            return
        leaves.append(
            {
                "path": next_path,
                "url": normalize_url(url_path, HOME_URL),
                "category_id": str(node.get("id") or ""),
            }
        )

    for root in roots:
        walk(root, [])
    return leaves


def categories_from_path(path):
    path = [clean_text(item) for item in path if clean_text(item)]
    if not path:
        return "", "", ""
    c1 = path[0]
    c2 = path[1] if len(path) > 1 else ""
    c3 = " > ".join(path[2:]) if len(path) > 2 else ""
    return c1, c2, c3


def is_allowed_category_url(url):
    full = normalize_url(url, HOME_URL, keep_query=True)
    if not full or urlparse(full).netloc != urlparse(SITE).netloc:
        return False
    path = urlparse(full).path.lower()
    if "/c/" not in path:
        return False
    return not any(part in path for part in SKIP_URL_PARTS)


def payload_to_start_urls(payload_list):
    result = []
    seen = set()

    def add_item(url, c1, c2="", c3=""):
        full = normalize_url(url, HOME_URL)
        if not is_allowed_category_url(full):
            return
        category_id = product_id_from_url(full) or ""
        match = re.search(r"/c/(\d+)", full)
        if match:
            category_id = match.group(1)
        key = (c1, c2, c3, full)
        if key in seen:
            return
        seen.add(key)
        result.append(
            {
                "url": full,
                "category_id": category_id,
                "categories_1": c1,
                "categories_2": c2,
                "categories_3": c3,
                "page_nums": 1,
            }
        )

    def walk(node, c1="", c2="", path=None):
        path = path or []
        if isinstance(node, dict):
            for name, value in node.items():
                if name == "__url__":
                    continue
                if not c1:
                    walk(value, name, "", [])
                elif not c2:
                    walk(value, c1, name, [])
                else:
                    next_path = path + [name]
                    if isinstance(value, dict):
                        walk(value, c1, c2, next_path)
                    else:
                        add_item(value, c1, c2, " > ".join(next_path))
        else:
            add_item(node, c1, c2, " > ".join(path))

    walk(payload_list)
    max_categories = _int_env("OBI_MAX_CATEGORIES", 0)
    if max_categories:
        result = result[:max_categories]
    logger.info(f"OBI payload 目录生成完成: {len(result)} 个")
    return result


def list_product_from_params(params):
    product = params.get("list_product") or {}
    if isinstance(product, str):
        try:
            return json.loads(product)
        except Exception:
            return {}
    return product if isinstance(product, dict) else {}


def product_price(product):
    values = []
    for key in ("jsonLdPreis",):
        price = money_value(product.get(key))
        if price is not None:
            values.append(price)
    tracking = product.get("addToCartTracking") or {}
    for key in ("itemValueGross",):
        price = money_value(tracking.get(key))
        if price is not None:
            values.append(price)
    price_primary = ((product.get("preise") or {}).get("preisPrimary") or {})
    formatted = price_primary.get("formatierterPreis")
    price = money_value(formatted)
    if price is not None:
        values.append(price)
    return values[0] if values else None


def product_images_from_card(product):
    images = []
    for image in product.get("bilder") or []:
        schema = image.get("urlSchema") or ""
        if schema:
            images.append(schema.replace("[PROFIL]", "prZZH"))
    return uniq_keep_order([normalize_url(url, HOME_URL, keep_query=True) for url in images], image_key)


def product_id_from_url(url):
    match = re.search(r"/p/(\d+)", url or "")
    return match.group(1) if match else ""


def detail_overview_map(soup):
    result = {}
    for li in soup.select(".overview__detail-list li"):
        text = clean_text(li.get_text(" ", strip=True))
        if ":" not in text:
            continue
        label, value = text.split(":", 1)
        label = label.strip()
        value = value.strip()
        if label and value:
            result[label] = value
    return result


def option_value(details, labels):
    lowered = {key.casefold(): value for key, value in details.items()}
    for label in labels:
        value = lowered.get(label.casefold())
        if value:
            return value
    return ""


def variant_groups_from_selectboxes(soup, current_url):
    groups = []
    for box in soup.select(".selectboxes .selectbox"):
        heading = box.find_previous(["p", "strong"])
        label = clean_text(heading.get_text(" ", strip=True) if heading else "").rstrip(":")
        values = []
        for link in box.select("a[href]"):
            href = normalize_url(link.get("href"), HOME_URL)
            value = clean_text(link.get_text(" ", strip=True))
            if not href or not value or value == "-":
                continue
            if "/p/" not in urlparse(href).path:
                continue
            values.append({"url": href, "value": value, "wt_name": link.get("wt_name") or ""})
        values = uniq_keep_order(values, lambda item: (item["url"], item["value"]))
        if label and values:
            groups.append({"name": label, "values": values})
    return groups


def current_options_from_detail(soup):
    details = detail_overview_map(soup)
    color = option_value(details, ["Kolor", "Kolor bazowy"])
    size = option_value(details, ["Rozmiar", "Rozmiar [cm]", "Wymiary", "Wymiar"])
    return color, size


def extract_variants_from_detail(soup, current_url):
    groups = variant_groups_from_selectboxes(soup, current_url)
    color_group = next((group for group in groups if group["name"].casefold() == "kolor"), None)
    size_group = next(
        (
            group
            for group in groups
            if group["name"].casefold() in {"warianty", "rozmiar", "wymiary"}
            or any("size_variant" in str(value.get("wt_name", "")) for value in group["values"])
        ),
        None,
    )
    color_options = color_group["values"] if color_group else []
    size_options = size_group["values"] if size_group else []
    current = normalize_url(current_url, HOME_URL)
    current_color, current_size = current_options_from_detail(soup)
    variants = []

    if color_options:
        for option in color_options:
            variants.append(
                {
                    "url": option["url"],
                    "option1_name": "Kolor",
                    "option1_value": option["value"],
                    "option2_name": "Wariant" if size_options else "",
                    "option2_value": [item["value"] for item in size_options] if size_options else "",
                }
            )
    elif size_options:
        variants.append(
            {
                "url": current,
                "option1_name": "Kolor" if current_color else "",
                "option1_value": current_color,
                "option2_name": "Wariant",
                "option2_value": [item["value"] for item in size_options],
            }
        )
    else:
        variants.append(
            {
                "url": current,
                "option1_name": "Kolor" if current_color else "",
                "option1_value": current_color,
                "option2_name": "Rozmiar" if current_size else "",
                "option2_value": [current_size] if current_size else "",
            }
        )

    return uniq_keep_order(variants, lambda item: (item["url"], item.get("option1_value", "")))


def detail_images(soup, fallback_product=None):
    images = []
    for a in soup.select(".ads-slider__link[href]"):
        images.append(a.get("href"))
    if not images:
        for img in soup.select(".overview-gallery img"):
            images.append(img.get("data-bigpic") or img.get("data-src") or img.get("src") or "")
    cleaned = []
    for url in images:
        full = normalize_url(url, HOME_URL, keep_query=True)
        low = full.lower()
        if not full or "blind.gif" in low or "logo" in low or "payment" in low:
            continue
        cleaned.append(full)
    if not cleaned and fallback_product:
        cleaned = product_images_from_card(fallback_product)
    return uniq_keep_order(cleaned, image_key)


def detail_price(soup, fallback_product=None):
    for selector in ('span[data-ui-name="ads.price.strong"]', ".overview-sticky-header__price"):
        for node in soup.select(selector):
            price = money_value(node.get_text(" ", strip=True))
            if price is not None:
                return price
    if fallback_product:
        price = product_price(fallback_product)
        if price is not None:
            return price
    return None


def overview_details_html(soup):
    rows = []
    details = detail_overview_map(soup)
    for label, value in details.items():
        rows.append((label, value))
    if not rows:
        return ""
    chunks = ['<h2 class="body-section-title">Cechy produktu</h2><table><tbody>']
    for label, value in rows:
        if value:
            chunks.append(f"<tr><th>{label}</th><td>{value}</td></tr>")
        else:
            chunks.append(f"<tr><td colspan=\"2\">{label}</td></tr>")
    chunks.append("</tbody></table>")
    return "".join(chunks)


def clean_body_fragment(fragment):
    if not fragment:
        return ""
    soup = BeautifulSoup(str(fragment), "html.parser")
    for tag in soup.select("script, style, svg, picture, source, iframe, video, form, input, button, noscript"):
        tag.decompose()
    for tag in soup.select("[data-bv-show], .article-number"):
        tag.decompose()
    for heading in soup.find_all(["h2", "h3"]):
        heading_text = clean_text(heading.get_text()).rstrip(":").casefold()
        if heading_text == "dane wytwórcy":
            container = heading.find_parent("section") or heading.find_parent("div") or heading
            container.decompose()
    for tag in soup.find_all("a"):
        tag.unwrap()
    for tag in soup.find_all("img"):
        src = normalize_url(tag.get("src") or tag.get("data-src") or "", HOME_URL, keep_query=True)
        if not src:
            tag.decompose()
        else:
            tag.attrs = {"src": src}
    for tag in soup.find_all(True):
        if tag.name == "img":
            allowed = {"src"}
        elif tag.name in {"h2", "h3"}:
            allowed = {"class"}
        else:
            allowed = set()
        for attr in list(tag.attrs):
            if attr not in allowed:
                del tag.attrs[attr]
    for tag in soup.find_all(["h2", "h3"]):
        tag.attrs = {"class": "body-section-title"}
    for tag in reversed(soup.find_all(["div", "span", "p", "li", "td", "th", "section"])):
        if not tag.get_text(" ", strip=True) and not tag.find(["table", "ul", "ol", "img"]):
            tag.decompose()
    return str(soup).strip()


def remove_leading_duplicate_title(html, title):
    if not html:
        return ""
    soup = BeautifulSoup(str(html), "html.parser")
    target = clean_text(title).rstrip(":").casefold()

    def normalized_heading_text(tag):
        return clean_text(tag.get_text(" ", strip=True)).rstrip(":").casefold()

    def first_meaningful_child(node):
        for child in node.children:
            if getattr(child, "name", None):
                if child.name == "br":
                    continue
                return child
            if str(child).strip():
                return child
        return None

    current = soup
    while True:
        first = first_meaningful_child(current)
        if not getattr(first, "name", None):
            break
        if first.name in {"h2", "h3"}:
            if normalized_heading_text(first) == target:
                first.decompose()
            break
        if first.name in {"div", "section", "article"}:
            current = first
            continue
        break
    return str(soup).strip()


def body_section(title, html):
    cleaned = clean_body_fragment(html)
    if not cleaned:
        return ""
    cleaned = remove_leading_duplicate_title(cleaned, title)
    if not cleaned:
        return ""
    return f'<h2 class="body-section-title">{title}</h2>{cleaned}'


def detail_body(soup):
    chunks = []
    overview = overview_details_html(soup)
    if overview:
        chunks.append(overview)
    desc = soup.select_one("section#desc > .description-text") or soup.select_one("#desc .description-text")
    if desc:
        body = body_section("Opis produktu", desc)
        if body:
            chunks.append(body)
    return "".join(chunks)


def master_id_from_detail(soup, product_id):
    node = soup.select_one('input[name="masterCode"][value]')
    master = node.get("value") if node else ""
    return master or (f"Master{product_id}" if product_id else "")


class CrawlerObject(Spider):
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = _int_env("OBI_RECOLLECT", 1)
    is_proxy = 0
    collect_thread_number = max(1, _int_env("BATCH", 2))
    more_collect_thread_number = max(1, _int_env("BATCH", 2))
    filename = os.path.basename(__file__)
    name = "_" + filename.replace(".py", "")

    def __init__(self):
        self.max_pages = _int_env("OBI_MAX_PAGES", 0)
        self.max_products = _int_env("OBI_MAX_PRODUCTS", 0)
        self._emitted_products = 0
        self._emit_lock = threading.Lock()
        super().__init__()

    @classmethod
    def init_func(cls):
        cls.start_urls.clear()
        cls.start_urls.extend(payload_to_start_urls(PAYLOAD_LIST))

    def _can_emit_product(self):
        if not self.max_products:
            return True
        with self._emit_lock:
            if self._emitted_products >= self.max_products:
                return False
            self._emitted_products += 1
            return True

    def get_list(self, params):
        page_num = 1
        while True:
            if self.max_pages and page_num > self.max_pages:
                break
            current_url = page_url(params["url"], page_num)
            html, final_url = fetch_text(current_url, kind="list")
            search_state = extract_search_state(html)
            products = search_state.get("ergebnisListe") or []
            total_pages = int(search_state.get("seitenAnzahl") or 0)
            if not products:
                break
            logger.info(f"OBI 列表页 {final_url} page={page_num} 提取商品 {len(products)} 个")
            for product in products:
                href = normalize_url(product.get("detailseitenUrl"), HOME_URL)
                if not href:
                    continue
                if not self._can_emit_product():
                    if getattr(self, "_limit_notice_count", 0) < 1:
                        self._limit_notice_count = 1
                        logger.info("OBI_MAX_PRODUCTS 已达到调试上限，停止继续加入商品任务")
                    return
                item = deepcopy(params)
                item["url"] = href
                item["list_url"] = final_url
                item["product_id"] = str(product.get("artikelNummer") or product_id_from_url(href))
                item["list_product"] = product
                yield item
            if not total_pages or page_num >= total_pages:
                break
            page_num += 1

    def get_content(self, params):
        html, _ = fetch_text(params["url"], kind="detail")
        soup = BeautifulSoup(html, "html.parser")
        product = list_product_from_params(params)
        product_id = str(params.get("product_id") or product.get("artikelNummer") or product_id_from_url(params.get("url")))
        variants = extract_variants_from_detail(soup, params["url"])
        handle = self.counter()
        for index, variant in enumerate(variants, start=1):
            item = deepcopy(params)
            item["url"] = variant["url"]
            item["product_id"] = product_id_from_url(variant["url"]) or product_id
            item["handle"] = f"{handle}_{index}" if len(variants) > 1 else handle
            item["option1_name"] = variant.get("option1_name") or ""
            item["option1_value"] = variant.get("option1_value") or ""
            item["option2_name"] = variant.get("option2_name") or ""
            item["option2_value"] = variant.get("option2_value") or ""
            yield item

    def get_more_content(self, params):
        html, _ = fetch_text(params["url"], kind="detail")
        soup = BeautifulSoup(html, "html.parser")
        product = list_product_from_params(params)
        product_id = str(params.get("product_id") or product.get("artikelNummer") or product_id_from_url(params.get("url")))

        title_node = soup.select_one('h1[data-ui-name="ads.overview-description.product-name.h1"]') or soup.select_one("h1")
        title = clean_text(title_node.get_text(" ", strip=True) if title_node else "") or clean_text(product.get("artikelName"))
        if not title:
            return None

        price = detail_price(soup, product)
        if price is None:
            return None

        images = detail_images(soup, product)
        if not images:
            return None

        item = deepcopy(params)
        item["title"] = title
        item["subtitle"] = ""
        item["price"] = float(price)
        item["image_src"] = images
        item["body"] = detail_body(soup)
        item["more_info"] = ""
        item.setdefault("option1_name", "")
        item.setdefault("option1_value", "")
        item.setdefault("option2_name", "")
        item.setdefault("option2_value", "")
        item.setdefault("option3_name", "")
        item.setdefault("option3_value", "")
        item["size_price"] = ""
        return item


if __name__ == "__main__":
    CrawlerObject().start()
