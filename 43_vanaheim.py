# -*- coding: utf-8 -*-
import html
import json
import os
import re
import threading
import traceback
from copy import deepcopy
from html import escape as html_escape
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup
from curl_cffi import requests
from loguru import logger
from scrapling.fetchers import Fetcher, StealthyFetcher

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("HEADLESS", "1")
os.environ.setdefault("BATCH", "10")
os.environ.setdefault("WAIT", "1")
os.environ.setdefault("VANAHEIM_MAX_CATEGORIES", "0")
os.environ.setdefault("VANAHEIM_MAX_PAGES", "0")
os.environ.setdefault("VANAHEIM_MAX_PRODUCTS", "0")
os.environ.setdefault("VANAHEIM_RECOLLECT", "1")

from fnspider import Spider, hash_md5, settings  # noqa: E402

SITE = "https://vanaheim.pl"
HOME_URL = f"{SITE}/pl/"
CACHE_NAME = "_43_vanaheim"
REQUEST_HEADERS = {
    "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.7",
}
HTML_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
}

PAYLOAD_LIST = {'Games Workshop': {'Warhammer Age of Sigmar': {'NOWOŚCI': 'https://vanaheim.pl/pl/393-warhammer-aos-nowosci',
                                                'Od Czego Zacząć?': 'https://vanaheim.pl/pl/1893-warhammer-aos-start',
                                                'ZESTAWY STARTOWE': 'https://vanaheim.pl/pl/629-warhammer-aos-zestawy',
                                                'SPEARHEAD - Zestawy Armii': 'https://vanaheim.pl/pl/1710-age-of-sigmar-spearhead',
                                                'Battleforces': 'https://vanaheim.pl/pl/1344-aos-battleforces',
                                                'Grand Alliance: Order': 'https://vanaheim.pl/pl/927-warhammer-aos-order',
                                                'Grand Alliance: Chaos': 'https://vanaheim.pl/pl/928-warhammer-aos-chaos',
                                                'Grand Alliance: Death': 'https://vanaheim.pl/pl/929-warhammer-aos-death',
                                                'Grand Alliance: Destruction': 'https://vanaheim.pl/pl/930-warhammer-aos-destruction',
                                                'Podręczniki': 'https://vanaheim.pl/pl/32-age-of-sigmar-podreczniki',
                                                'Sceneria': 'https://vanaheim.pl/pl/34-warhammer-sceneria',
                                                'Akcesoria': 'https://vanaheim.pl/pl/837-akcesoria-warhammer'},
                    'Warhammer 40000': {'NOWOŚCI': 'https://vanaheim.pl/pl/394-w40k-nowosci',
                                        'Od Czego Zacząć?': 'https://vanaheim.pl/pl/1865-warhammer-40000-start',
                                        'ZESTAWY STARTOWE': 'https://vanaheim.pl/pl/630-warhammer-40000-zestawy',
                                        'COMBAT PATROL - Zestawy Armii': 'https://vanaheim.pl/pl/1248-combat-patrol-start-collecting-zestawy',
                                        'Battleforces': 'https://vanaheim.pl/pl/1345-w40k-battleforces',
                                        'SPACE MARINES': 'https://vanaheim.pl/pl/1895-space-marines',
                                        'ARMIES OF IMPERIUM': 'https://vanaheim.pl/pl/1703-warhammer-40000-armies-of-imperium',
                                        'ARMIES OF CHAOS': 'https://vanaheim.pl/pl/1704-warhammer-40000-armies-of-chaos',
                                        'ARMIES OF XENOS': 'https://vanaheim.pl/pl/1705-warhammer-40000-armies-of-xenos',
                                        'Podręczniki': 'https://vanaheim.pl/pl/20-w40k-podreczniki-kodeksy',
                                        'Akcesoria': 'https://vanaheim.pl/pl/561-akcesoria-w40k',
                                        'Sceneria': 'https://vanaheim.pl/pl/562-sceneria-warhammer-40000'},
                    'Warhammer: The Old World': {'NOWOŚCI': 'https://vanaheim.pl/pl/2417-nowosci-warhammer-the-old-world',
                                                 'Zestawy startowe': 'https://vanaheim.pl/pl/2352-warhammer-old-world-zestawy-startowe',
                                                 'Podręczniki': 'https://vanaheim.pl/pl/2353-warhammer-the-old-world-podreczniki',
                                                 'Beastmen Brayherds': 'https://vanaheim.pl/pl/2437-beastmen-brayherds',
                                                 'Dwarfen Mountain Holds': 'https://vanaheim.pl/pl/2384-dwarfen-mountain-holds',
                                                 'Empire of Man': 'https://vanaheim.pl/pl/2415-empire-of-man',
                                                 'Grand Cathay': 'https://vanaheim.pl/pl/2439-grand-cathay',
                                                 'High Elf Realms': 'https://vanaheim.pl/pl/9-warhammer-old-world-high-elf-realms',
                                                 'Kingdom of Bretonnia': 'https://vanaheim.pl/pl/2350-warhammer-old-world-kingdom-of-bretonnia',
                                                 'Orc & Goblin Tribes': 'https://vanaheim.pl/pl/2359-orc-goblin-tribes',
                                                 'Tomb Kings of Khemri': 'https://vanaheim.pl/pl/2351-warhammer-old-world-tomb-kings-of-khemri',
                                                 'Warriors of Chaos': 'https://vanaheim.pl/pl/2386-warriors-of-chaos',
                                                 'Wood Elf Realms': 'https://vanaheim.pl/pl/10-wood-elf-realms',
                                                 'Tereny i Akcesoria': 'https://vanaheim.pl/pl/2354-old-world-tereny-akcesoria',
                                                 'Movement Traye': 'https://vanaheim.pl/pl/2355-movement-traye',
                                                 'Podstawki kwadratowe i prostokątne': 'https://vanaheim.pl/pl/2358-podstawki-kwadratowe-i-prostokatne',
                                                 'Akcesoria innych producentów': 'https://vanaheim.pl/pl/2357-akcesoria-innych-producentow'},
                    'Middle-Earth Strategy Battle Game': {'Zestawy na Start': 'https://vanaheim.pl/pl/2236-zestawy-na-start',
                                                          'Podręczniki': 'https://vanaheim.pl/pl/67-middle-earth-sbg-podreczniki',
                                                          'Kingdoms of Men': 'https://vanaheim.pl/pl/419-lotr-kingdoms-of-men',
                                                          'The Free Peoples': 'https://vanaheim.pl/pl/420-lotr-free-peoples',
                                                          'The Fallen Realms': 'https://vanaheim.pl/pl/51-lotr-fallen-realms',
                                                          'Mordor': 'https://vanaheim.pl/pl/55-lotr-mordor',
                                                          'Moria & Angmar': 'https://vanaheim.pl/pl/421-lotr-moria-angmar',
                                                          'Hobbit: siły Dobra': 'https://vanaheim.pl/pl/552-hobbit-sily-dobra',
                                                          'Hobbit: siły Zła': 'https://vanaheim.pl/pl/553-hobbit-sily-zla',
                                                          'Sceneria do gry': 'https://vanaheim.pl/pl/551-hobbit-sceneria-do-gry'},
                    'Warhammer: The Horus Heresy': {'NOWOŚCI': 'https://vanaheim.pl/pl/2151-horus-heresy-nowosci',
                                                    'Zestawy Startowe': 'https://vanaheim.pl/pl/2152-horus-heresy-zestawy-startowe',
                                                    'Legiones Astartes': 'https://vanaheim.pl/pl/2154-horus-heresy-legiones-astartes',
                                                    'Mechanicum': 'https://vanaheim.pl/pl/2155-horus-heresy-mechanicum',
                                                    'Solar Auxilia': 'https://vanaheim.pl/pl/2363-solar-auxilia',
                                                    'Talons of the Emperor': 'https://vanaheim.pl/pl/2156-horus-heresy-talons-of-the-emperor',
                                                    'Daemons of the Ruinstorm': 'https://vanaheim.pl/pl/2158-horus-heresy-daemons-of-the-ruinstorm',
                                                    'Podręczniki': 'https://vanaheim.pl/pl/2153-horus-heresy-podreczniki',
                                                    'Akcesoria': 'https://vanaheim.pl/pl/2187-horus-heresy-akcesoria'},
                    'W40k: KILL TEAM': 'https://vanaheim.pl/pl/1079-w40k-kill-team',
                    'Necromunda': 'https://vanaheim.pl/pl/1314-necromunda',
                    'Warhammer: The Horus Heresy Legions Imperialis': 'https://vanaheim.pl/pl/2343-legions-imperialis',
                    'Warhammer Underworlds': 'https://vanaheim.pl/pl/1315-warhammer-underworlds',
                    'Warhammer Age of Sigmar: Warcry': 'https://vanaheim.pl/pl/1648-warhammer-age-of-sigmar-warcry',
                    'Blood Bowl': 'https://vanaheim.pl/pl/1177-blood-bowl-gra-figurkowa',
                    'Warhammer Quest': 'https://vanaheim.pl/pl/1086-warhammer-quest-gra-planszowa'},
 'Gry Figurkowe': {'Fantasy': {'Warhammer Age of Sigmar': 'https://vanaheim.pl/pl/5-warhammer-aos',
                               'Warhammer: The Old World': 'https://vanaheim.pl/pl/2349-warhammer-the-old-world',
                               'Middle-Earth Strategy Battle Game': 'https://vanaheim.pl/pl/46-middle-earth-lord-of-the-rings-game',
                               'A Song of Ice and Fire': 'https://vanaheim.pl/pl/1521-a-song-of-ice-and-fire',
                               'Blood Bowl': 'https://vanaheim.pl/pl/1177-blood-bowl-gra-figurkowa',
                               'Warhammer Underworlds': 'https://vanaheim.pl/pl/1315-warhammer-underworlds',
                               'Warhammer Age of Sigmar: Warcry': 'https://vanaheim.pl/pl/1648-warhammer-age-of-sigmar-warcry',
                               'Argatoria': 'https://vanaheim.pl/pl/2268-argatoria'},
                   'Science-Fiction': {'Warhammer 40000': 'https://vanaheim.pl/pl/7-warhammer-40000',
                                       'W40k: KILL TEAM': 'https://vanaheim.pl/pl/1079-w40k-kill-team',
                                       'Necromunda': 'https://vanaheim.pl/pl/1314-necromunda',
                                       'Warhammer: The Horus Heresy': 'https://vanaheim.pl/pl/2150-warhammer-the-horus-heresy',
                                       'StarCraft Figurkowa Gra Bitewna': 'https://vanaheim.pl/pl/2480-starcraft',
                                       'Star Wars Legion 2.0': 'https://vanaheim.pl/pl/1310-star-wars-legion',
                                       'Trench Crusade': 'https://vanaheim.pl/pl/2448-trench-crusade',
                                       'Dropfleet Commander': 'https://vanaheim.pl/pl/1359-dropfleet-commander',
                                       'Dropzone Commander': 'https://vanaheim.pl/pl/1911-dropzone-commander',
                                       'Star Wars: Shatterpoint': 'https://vanaheim.pl/pl/2283-star-wars-shatterpoint'},
                   'Historyczne': {'Hail Caesar': 'https://vanaheim.pl/pl/1493-hail-caesar',
                                   'Pike & Shotte': 'https://vanaheim.pl/pl/1484-pike-and-shotte',
                                   'Ogniem i Mieczem 2 Edycja': 'https://vanaheim.pl/pl/1377-ogniem-i-mieczem',
                                   'Black Powder': 'https://vanaheim.pl/pl/1468-black-powder',
                                   'Epic Battles': 'https://vanaheim.pl/pl/2111-black-powder-epic-battles',
                                   'Bolt Action': 'https://vanaheim.pl/pl/647-bolt-action',
                                   "Konflikt '47": 'https://vanaheim.pl/pl/2467-konflikt-47',
                                   'Flames Of War': 'https://vanaheim.pl/pl/1218-flames-of-war',
                                   'Victory at Sea': 'https://vanaheim.pl/pl/1868-victory-at-sea',
                                   'Blood Red Skies': 'https://vanaheim.pl/pl/1303-blood-red-skies',
                                   'Cruel Seas': 'https://vanaheim.pl/pl/1596-cruel-seas',
                                   'World of Tanks: Miniature Game': 'https://vanaheim.pl/pl/1908-world-of-tanks-miniature-game',
                                   'World War III (Team Yankee)': 'https://vanaheim.pl/pl/1116-team-yankee-gra-figurkowa'},
                   'Pozostałe Linie Modeli': {'Modele do Dungeons & Dragons': 'https://vanaheim.pl/pl/1686-modele-rpg-fantasy-dungeons-and-dragons',
                                              'Dungeons and Lasers': 'https://vanaheim.pl/pl/2214-dungeons-and-lasers',
                                              'Epic Encounters': 'https://vanaheim.pl/pl/1889-epic-encounters',
                                              'Rubicon Models': 'https://vanaheim.pl/pl/1655-rubicon-models',
                                              'Neko Galaxy': 'https://vanaheim.pl/pl/1994-neko-galaxy'},
                   'Tereny do gier': {'Tereny do gier fantasy': 'https://vanaheim.pl/pl/536-tereny-do-gier-fantasy',
                                      'Tereny do gier Sci-fi': 'https://vanaheim.pl/pl/537-tereny-do-gier-sci-fi',
                                      'TTCombat Tabletop Scenics': 'https://vanaheim.pl/pl/1946-ttcombat-tabletop-scenics',
                                      'Battle Systems - Tereny Kartonowe': 'https://vanaheim.pl/pl/2266-battle-systems-tereny-kartonowe'}},
 'Gry Karciane': {'Magic: The Gathering': {'NOWOŚCI': 'https://vanaheim.pl/pl/830-mtg-nowosci',
                                           'Boostery': 'https://vanaheim.pl/pl/2294-boostery',
                                           'Booster Boxy': 'https://vanaheim.pl/pl/2295-booster-box',
                                           'Bundle i Zestawy': 'https://vanaheim.pl/pl/2296-bundle-i-zestawy',
                                           'Commander Deck': 'https://vanaheim.pl/pl/1081-mtg-commander'},
                  'Flesh And Blood TCG': {'NOWOŚCI': 'https://vanaheim.pl/pl/2305-flesh-and-blood-nowosci',
                                          'Boostery': 'https://vanaheim.pl/pl/2302-boostery',
                                          'Booster Boxy': 'https://vanaheim.pl/pl/2303-booster-boxy',
                                          'Talie': 'https://vanaheim.pl/pl/2304-fab-talie'},
                  'Pokemon TCG': {'NOWOŚCI': 'https://vanaheim.pl/pl/2096-nowosci-pokemon-tcg',
                                  'Boostery': 'https://vanaheim.pl/pl/2297-boostery',
                                  'Booster Boxy': 'https://vanaheim.pl/pl/2298-booster-boxy',
                                  'Checklane Blistery': 'https://vanaheim.pl/pl/2301-checklane-blistery'},
                  'Disney Lorcana': {'NOWOŚCI': 'https://vanaheim.pl/pl/2377-disney-lorcana-nowosci',
                                     'Boostery': 'https://vanaheim.pl/pl/2372-lorcana-boostery',
                                     'Booster Boxy': 'https://vanaheim.pl/pl/2373-lorcana-booster-boxy',
                                     'Starter Decki': 'https://vanaheim.pl/pl/2374-lorcana-starter-decki',
                                     "Illumineer's Trove i inne Zestawy": 'https://vanaheim.pl/pl/2375-lorcana-illumineer-s-trove-i-inne-zestawy',
                                     'Akcesoria': 'https://vanaheim.pl/pl/2376-lorcana-akcesoria'},
                  'Star Wars: Unlimited': {'Boostery': 'https://vanaheim.pl/pl/2378-star-wars-unlimited-boostery',
                                           'Booster Boxy': 'https://vanaheim.pl/pl/2379-star-wars-unlimited-booster-boxy',
                                           'Zestawy Startowe i Inne': 'https://vanaheim.pl/pl/2380-star-wars-unlimited-zestawy',
                                           'Akcesoria': 'https://vanaheim.pl/pl/2340-akcesoria-star-wars-unlimited'},
                  'Riftbound - League of Legends TCG': 'https://vanaheim.pl/pl/2429-riftbound-league-of-legends-tcg',
                  'One Piece: The Card Game': 'https://vanaheim.pl/pl/2370-one-piece-card-game',
                  'Gwint - Legendarna Gra Karciana': 'https://vanaheim.pl/pl/2443-gwint-legendarna-gra-karciana',
                  'Munchkin': 'https://vanaheim.pl/pl/1076-munchkin-gra-karciana',
                  'Eksplodujące Kotki': 'https://vanaheim.pl/pl/1937-eksplodujace-kotki',
                  'Odjechane Jednorożce': 'https://vanaheim.pl/pl/2083-odjechane-jednorozce',
                  'Inne Gry Karciane': 'https://vanaheim.pl/pl/1046-inne-gry-karciane',
                  'Yu-Gi-Oh! TCG': 'https://vanaheim.pl/pl/2488-yu-gi-oh-tcg',
                  'Akcesoria do Kart': {'Koszulki': 'https://vanaheim.pl/pl/2104-koszulki-do-kart',
                                        'Deck Boxy': 'https://vanaheim.pl/pl/2105-deck-boxy-pudelka-na-karty',
                                        'Albumy, Segregatory i Wkłady': 'https://vanaheim.pl/pl/2106-albumy-segregatory-i-wklady',
                                        'Maty': 'https://vanaheim.pl/pl/2107-maty-do-gier-karcianych',
                                        'Pozostałe': 'https://vanaheim.pl/pl/2108-pozostale-akcesoria-do-kart'}},
 'Gry Planszowe': {'Gry Planszowe Według Tytułu': 'https://vanaheim.pl/pl/1040-gry-planszowe-wedlug-tytulu'},
 'Modelarstwo': {'Farby Citadel': {'Citadel Base': 'https://vanaheim.pl/pl/432-farby-citadel-base',
                                   'Citadel Layer': 'https://vanaheim.pl/pl/434-farby-citadel-layer',
                                   'Citadel Shade': 'https://vanaheim.pl/pl/433-citadel-shade',
                                   'Citadel Contrast': 'https://vanaheim.pl/pl/1672-farby-citadel-contrast',
                                   'Citadel Technical': 'https://vanaheim.pl/pl/438-farby-citadel-technical',
                                   'Citadel Dry': 'https://vanaheim.pl/pl/435-farby-citadel-dry'},
                 'Farby Scale75': {'Scalecolor': 'https://vanaheim.pl/pl/2243-scalecolor',
                                   'Scalecolor Artist': 'https://vanaheim.pl/pl/2319-artist',
                                   'Soilworks': 'https://vanaheim.pl/pl/2242-soil-works'},
                 'AK Interactive': {'AK Diorama Series': 'https://vanaheim.pl/pl/1307-ak-diorama-series',
                                    'AK Wargame': 'https://vanaheim.pl/pl/2248-ak-wargame',
                                    'AK Weathering': 'https://vanaheim.pl/pl/785-ak-weathering',
                                    'AK Playmarkers': 'https://vanaheim.pl/pl/2466-playmarkers',
                                    'AK Pigmenty': 'https://vanaheim.pl/pl/786-ak-pigmenty',
                                    'AK Watercolor pencil': 'https://vanaheim.pl/pl/2129-ak-watercolor-pencil',
                                    'AK Chemia': 'https://vanaheim.pl/pl/789-ak-chemia',
                                    'AK Weathering Sets': 'https://vanaheim.pl/pl/788-ak-weathering-sets'},
                 'Zestawy Farb': {'Citadel': 'https://vanaheim.pl/pl/1845-zestawy-farb-citadel',
                                  'Army Painter': 'https://vanaheim.pl/pl/1260-warpaints-zestawy',
                                  'Vallejo': 'https://vanaheim.pl/pl/1777-zestawy-farb-vallejo',
                                  'Green Stuff World': 'https://vanaheim.pl/pl/1844-zestawy-farb-green-stuff-world',
                                  'Scale75': 'https://vanaheim.pl/pl/1855-zestawy-scale75'},
                 'Farby Vallejo': {'Model Color': 'https://vanaheim.pl/pl/1775-vallejo-model-color',
                                   'Game Color': 'https://vanaheim.pl/pl/2233-vallejo-game-color-new',
                                   'Xpress Color': 'https://vanaheim.pl/pl/2234-vallejo-xpress-color',
                                   'True Metallic Metal': 'https://vanaheim.pl/pl/2460-true-metallic-metal',
                                   'Metal Color': 'https://vanaheim.pl/pl/1564-vallejo-metal-color',
                                   'Game Air': 'https://vanaheim.pl/pl/1205-vallejo-game-air',
                                   'Techniczne': 'https://vanaheim.pl/pl/484-vallejo-techniczne',
                                   'Surface Primer - podkłady': 'https://vanaheim.pl/pl/577-vallejo-surface-primer-podklady'},
                 'Farby Army Painter': {'Warpaints Fanatic': 'https://vanaheim.pl/pl/2369-warpaints-fanatic',
                                        'Speedpaint 2.0': 'https://vanaheim.pl/pl/2124-army-painter-speedpaint',
                                        'Speedpaint 2.0 Marker': 'https://vanaheim.pl/pl/2442-speedpaint-20-marker'},
                 'Farby Two Thin Coats': 'https://vanaheim.pl/pl/2286-farby-two-thin-coats',
                 'Farby w Sprayu': {'Spraye Citadel': 'https://vanaheim.pl/pl/294-spraye-citadel',
                                    'Spraye Army Painter': 'https://vanaheim.pl/pl/410-spraye-army-painter',
                                    'Spraye AK Interactive': 'https://vanaheim.pl/pl/1972-spraye-ak-interactive',
                                    'Spraye GSW': 'https://vanaheim.pl/pl/2052-spraye-gsw'},
                 'Paint Forge': {'Kępki Trawy': 'https://vanaheim.pl/pl/1784-kepki-trawy-paint-forge',
                                 'Kwiatki': 'https://vanaheim.pl/pl/1785-kwiatki-paint-forge',
                                 'Alien Tufts': 'https://vanaheim.pl/pl/1982-alien-tufts-paint-forge',
                                 'Modele Roślin': 'https://vanaheim.pl/pl/2395-modele-roslin',
                                 'Żywiczne elementy': 'https://vanaheim.pl/pl/2446-paint-forge-zywiczne-elementy',
                                 'Szablony do Aerografu': 'https://vanaheim.pl/pl/1786-szablony-do-aerografu-paint-forge'},
                 'Pędzle': {'Renesans': 'https://vanaheim.pl/pl/2068-pedzle-renesans',
                            'Army Painter': 'https://vanaheim.pl/pl/2069-army-painter',
                            'Citadel': 'https://vanaheim.pl/pl/2066-citadel',
                            'Rebel': 'https://vanaheim.pl/pl/2418-pedzle-rebel',
                            'AvantGarde': 'https://vanaheim.pl/pl/2461-pedzle-avantgarde',
                            'Vallejo': 'https://vanaheim.pl/pl/2071-vallejo',
                            'DaVinci': 'https://vanaheim.pl/pl/2065-davinci',
                            'Raphaël Kolinsky 8404': 'https://vanaheim.pl/pl/1941-raphael-kolinsky-8404',
                            'Green Stuff World': 'https://vanaheim.pl/pl/2070-green-stuff-world'},
                 'Narzędzia': {'Podstawowe': 'https://vanaheim.pl/pl/2113-podstawowe-narzedzia',
                               'Specjalistyczne': 'https://vanaheim.pl/pl/2114-specjalistyczne-narzedzia'},
                 'Masy Modelarskie': {'Green Stuff': 'https://vanaheim.pl/pl/2120-green-stuff',
                                      'Milliput': 'https://vanaheim.pl/pl/2121-milliput',
                                      'Pozostałe': 'https://vanaheim.pl/pl/2122-pozostale-masy-modelarskie'},
                 'Trawa i Posypki': {'Trawka statyczna': 'https://vanaheim.pl/pl/2115-trawka-statyczna',
                                     'Kępki samoprzylepne / Tufts': 'https://vanaheim.pl/pl/2116-kepki-samoprzylepne-tufts',
                                     'Pozostałe Posypki': 'https://vanaheim.pl/pl/2117-pozostale-posypki-modelarskie',
                                     'Roślinność': 'https://vanaheim.pl/pl/2118-roslinnosc'},
                 'Gamers Grass': {'Grass Tufts': 'https://vanaheim.pl/pl/1626-gamers-grass-tufts',
                                  'Flower Tufts': 'https://vanaheim.pl/pl/2440-gamers-grass-flower-tufts',
                                  'Special Tufts': 'https://vanaheim.pl/pl/1627-gamers-grass-special-tufts',
                                  'Basing Bits': 'https://vanaheim.pl/pl/1709-gamers-grass-basing-bits',
                                  'Laser Plants': 'https://vanaheim.pl/pl/2127-laser-plants',
                                  'Zestawy': 'https://vanaheim.pl/pl/2436-zestawy'},
                 'Kleje': 'https://vanaheim.pl/pl/284-kleje',
                 'Rozpuszczalniki i chemia': 'https://vanaheim.pl/pl/871-rozpuszczalniki-i-chemia',
                 'Mokre Palety': 'https://vanaheim.pl/pl/2047-mokre-palety',
                 'Aerografy i Kompresory': 'https://vanaheim.pl/pl/541-aerografia',
                 'Magnesy': 'https://vanaheim.pl/pl/578-magnesy',
                 'Noże i Ostrza OLFA': 'https://vanaheim.pl/pl/1246-narzedzia-olfa',
                 'Green Stuff World': {'NOWOŚCI': 'https://vanaheim.pl/pl/2084-nowosci',
                                       'Narzędzia': 'https://vanaheim.pl/pl/1372-green-stuff-world-narzedzia',
                                       'Rolling Pins': 'https://vanaheim.pl/pl/1373-green-stuff-world-rolling-pins',
                                       'Rzeźbienie: Masy i Formy': 'https://vanaheim.pl/pl/1374-green-stuff-world-masy-rzezbiarskie',
                                       'Akcesoria Hobbystyczne': 'https://vanaheim.pl/pl/1375-green-stuff-world-akcesoria',
                                       'Farby': 'https://vanaheim.pl/pl/1376-green-stuff-world-farby',
                                       'Chemia Modelarska': 'https://vanaheim.pl/pl/1570-chemia-modelarska-green-stuff-world',
                                       'Podstawki i Traye': 'https://vanaheim.pl/pl/1726-podstawki-traye-gsw',
                                       'Weathering': 'https://vanaheim.pl/pl/1870-green-stuff-world-weathering',
                                       'Sceneria, Trawki i Elementy Żywiczne': 'https://vanaheim.pl/pl/1943-sceneria-materialy-green-stuff-world',
                                       'Plasticard i Elementy do Budowy Dioram': 'https://vanaheim.pl/pl/1944-plasticard-i-elementy-do-budowy-dioram',
                                       'Suche Pigmenty': 'https://vanaheim.pl/pl/2045-suche-pigmenty',
                                       'Farby w Sprayu': 'https://vanaheim.pl/pl/2051-farby-w-sprayu'},
                 'Army Painter Gamemaster - Terenokreacja': 'https://vanaheim.pl/pl/2019-army-painter-gamemaster-terenokreacja',
                 'Zestawy Akcesoriów': 'https://vanaheim.pl/pl/409-akcesoria-zestawy',
                 'Pozostałe': 'https://vanaheim.pl/pl/295-akcesoria-pozostale'},
 'Akcesoria': {'Safe & Sound': {'Pudełka Magnetyczne (wszystkie)': 'https://vanaheim.pl/pl/2252-safe-and-sound-pudelka-magnetyczne',
                                'Pudełka Pełny Wymiar': 'https://vanaheim.pl/pl/1543-pudelka-pelny-wymiar-safe-and-sound',
                                'Pudełka "Black Box"': 'https://vanaheim.pl/pl/1544-black-box-safe-and-sound',
                                'Pudełka Mini': 'https://vanaheim.pl/pl/1542-pudelka-mini-safe-and-sound',
                                'Torby': 'https://vanaheim.pl/pl/1545-torby-safe-and-sound',
                                'Walizki Magnetyczne': 'https://vanaheim.pl/pl/2430-safe-and-sound-walizki-magnetyczne',
                                'Gąbki': 'https://vanaheim.pl/pl/1546-gabki-safe-and-sound',
                                'Akcesoria': 'https://vanaheim.pl/pl/1867-akcesoria-sa-and-sound',
                                'Instabases': 'https://vanaheim.pl/pl/2435-instabases'},
               'Torby i Walizki Citadel': 'https://vanaheim.pl/pl/309-torby-walizki-citadel',
               'Tereny do gier': {'Tereny do gier fantasy': 'https://vanaheim.pl/pl/536-tereny-do-gier-fantasy',
                                  'Tereny do gier Sci-fi': 'https://vanaheim.pl/pl/537-tereny-do-gier-sci-fi',
                                  'TTCombat Tabletop Scenics - City Streets': 'https://vanaheim.pl/pl/1962-ttcombat-city-streets',
                                  'TTCombat Tabletop Scenics - Eastern Empires': 'https://vanaheim.pl/pl/1963-ttcombat-eastern-empires',
                                  'TTCombat Tabletop Scenics - Fantasy Realms': 'https://vanaheim.pl/pl/1964-ttcombat-fantasy-realms',
                                  'TTCombat Tabletop Scenics - Industrial Hive': 'https://vanaheim.pl/pl/1965-ttcombat-industrial-hive',
                                  'TTCombat Tabletop Scenics - Sci-Fi Gothic': 'https://vanaheim.pl/pl/1966-ttcombat-sci-fi-gothic',
                                  'TTCombat Tabletop Scenics - Sci-Fi Utopia': 'https://vanaheim.pl/pl/1967-ttcombat-sci-fi-utopia',
                                  'TTCombat Tabletop Scenics - Sci-Fi X': 'https://vanaheim.pl/pl/1968-ttcombat-sci-fi-x',
                                  'TTCombat Tabletop Scenics - Streets of Venice': 'https://vanaheim.pl/pl/1969-ttcombat-streets-of-venice',
                                  'TTCombat Tabletop Scenics - Wild West': 'https://vanaheim.pl/pl/1970-ttcombat-wild-west',
                                  'TTCombat Tabletop Scenics - World War': 'https://vanaheim.pl/pl/1971-ttcombat-world-war',
                                  'TTCombat Tabletop Scenics - Warsztat': 'https://vanaheim.pl/pl/2284-warsztat',
                                  'TTCombat Tabletop Scenics - CHROMA - Sci Fi Gothic': 'https://vanaheim.pl/pl/2447-ttcombat-chroma-sci-fi-gothic',
                                  'Battle Systems - Tereny Kartonowe': 'https://vanaheim.pl/pl/2266-battle-systems-tereny-kartonowe'},
               'Podstawki': {'Okrągłe / Owalne': 'https://vanaheim.pl/pl/1727-podstawki-okragle-owalne',
                             'Kwadratowe / Prostokątne': 'https://vanaheim.pl/pl/1728-podstawki-kwadratowe-prostokatne'},
               'Micro Art Studio': {'Podstawki okrągłe': 'https://vanaheim.pl/pl/860-microart-podstawki-okragle',
                                    'Podstawki okrągłe Wide Lip': 'https://vanaheim.pl/pl/861-microart-podstawki-okragle-wide-lip',
                                    'Tereny żywiczne': 'https://vanaheim.pl/pl/863-microart-tereny-zywiczne',
                                    'Akcesoria': 'https://vanaheim.pl/pl/866-microart-akcesoria',
                                    'Designed for Infinity': 'https://vanaheim.pl/pl/867-microart-designed-for-infinity',
                                    'Designed for SWL': 'https://vanaheim.pl/pl/1458-designed-for-star-wars-legion',
                                    'Tereny HDF PREPAINTED': 'https://vanaheim.pl/pl/1863-tereny-hdf-prepainted'},
               'HobbyZone': {'Warsztatowy System modułowy': 'https://vanaheim.pl/pl/1827-warsztatowy-system-modulowy',
                             'Stoliki do Malowania': 'https://vanaheim.pl/pl/1828-stoliki-do-malowania',
                             'Stojaki i Wieszaki na Farby': 'https://vanaheim.pl/pl/1829-stojaki-i-wieszaki-na-farby',
                             'Organizery Warsztatu': 'https://vanaheim.pl/pl/1830-organizery-warsztatu',
                             'Akcesoria Modelarskie': 'https://vanaheim.pl/pl/1831-akcesoria-modelarskie',
                             'Przenośny Warsztat Hobbystyczny': 'https://vanaheim.pl/pl/2364-przenosny-warsztat-hobbystyczny'},
               'Kostki': {'Do gier RPG': 'https://vanaheim.pl/pl/298-kosci-do-gier-rpg',
                          'K6': 'https://vanaheim.pl/pl/299-kosci-bitewne-k6',
                          'Chessex': 'https://vanaheim.pl/pl/614-kosci-chessex',
                          'K20': 'https://vanaheim.pl/pl/1051-k20',
                          'Q-Workshop': 'https://vanaheim.pl/pl/1856-q-workshop'},
               'Akcesoria do Kart': {'Koszulki': 'https://vanaheim.pl/pl/2104-koszulki-do-kart',
                                     'Deck Boxy': 'https://vanaheim.pl/pl/2105-deck-boxy-pudelka-na-karty',
                                     'Albumy, Segregatory i Wkłady': 'https://vanaheim.pl/pl/2106-albumy-segregatory-i-wklady',
                                     'Maty': 'https://vanaheim.pl/pl/2107-maty-do-gier-karcianych',
                                     'Pozostałe': 'https://vanaheim.pl/pl/2108-pozostale-akcesoria-do-kart'},
               'Maty do gier bitewnych': {'Maty dostępne w naszym sklepie': 'https://vanaheim.pl/pl/2075-maty-dostepne-w-naszym-sklepie',
                                          'Pozostałe wzory mat na zamówienie': 'https://vanaheim.pl/pl/2076-pozostale-wzory-mat',
                                          'Akcesoria': 'https://vanaheim.pl/pl/2082-akcesoria'},
               'Akcesoria Firmowe Vanaheim': 'https://vanaheim.pl/pl/1765-miarki-firmowe-vanaheim',
               'Gadżety Warhammer 40000': 'https://vanaheim.pl/pl/1349-gadzety-warhammer-40000',
               'Gadżety Age of Sigmar': 'https://vanaheim.pl/pl/1522-gadzety-age-of-sigmar',
               'Dice Trays': 'https://vanaheim.pl/pl/1664-dice-trays',
               'Sakiewki na kostki': 'https://vanaheim.pl/pl/1294-sakiewki-na-kostki',
               'Do Gier RPG': 'https://vanaheim.pl/pl/1783-akcesoria-do-gier-rpg'},
 'Książki i RPG': {'Black Library PL - Fabularne książki polskojęzyczne': {'Warhammer Fantasy PL': 'https://vanaheim.pl/pl/1130-warhammer-fantasy-pl',
                                                                           'Warhammer 40000 PL': 'https://vanaheim.pl/pl/1131-ksiazki-warhammer-40000-pl',
                                                                           'Herezja Horusa': 'https://vanaheim.pl/pl/1180-herezja-horusa-pl'},
                   'Black Library - Fabularne książki anglojęzyczne': {'NOWOŚCI': 'https://vanaheim.pl/pl/1327-nowosci-black-library-en',
                                                                       'Warhammer Age of Sigmar': 'https://vanaheim.pl/pl/556-ksiazki-warhammer-aos',
                                                                       'Warhammer 40000': 'https://vanaheim.pl/pl/557-ksiazki-warhammer-40000',
                                                                       'Horus Heresy': 'https://vanaheim.pl/pl/558-ksiazki-horus-heresy',
                                                                       'Warhammer Fantasy': 'https://vanaheim.pl/pl/559-warhammer-fantasy'},
                   'Dungeons & Dragons': {'Podręczniki': 'https://vanaheim.pl/pl/2423-dungeons-and-dragons-podreczniki',
                                          'Modele': 'https://vanaheim.pl/pl/2424-dungeons-and-dragons-modele',
                                          'Plansze i Tereny': 'https://vanaheim.pl/pl/2425-plansze-i-tereny',
                                          'Akcesoria': 'https://vanaheim.pl/pl/2426-akcesoria'},
                   'Warhammer Fantasy Roleplay PL': {'Warhammer Fantasy Roleplay 4 edycja': 'https://vanaheim.pl/pl/2422-warhammer-fantasy-roleplay-4-edycja',
                                                     'Warhammer Fantasy Roleplay 2 edycja': 'https://vanaheim.pl/pl/2421-warhammer-fantasy-roleplay-2-edycja'},
                   'Warhammer 40.000 Roleplay': {'Imperium Maledictum': 'https://vanaheim.pl/pl/2390-imperium-maledictum',
                                                 'Wrath & Glory RPG': 'https://vanaheim.pl/pl/2391-warhammer-40000-wrath-glory-rpg',
                                                 'Dark Heresy 2ed. PL': 'https://vanaheim.pl/pl/2392-dark-heresy-2ed-pl'},
                   'Warhammer Age of Sigmar: Soulbound PL': 'https://vanaheim.pl/pl/1851-warhammer-age-of-sigmar-soulbound',
                   'Wiedźmin RPG / The Witcher RPG': 'https://vanaheim.pl/pl/1618-wiedzmin-rpg-the-witcher-rpg',
                   'Zew Cthulhu RPG PL': 'https://vanaheim.pl/pl/1685-zew-cthulhu-rpg-pl',
                   'Świat Mroku': {'Wampir: Maskarada': 'https://vanaheim.pl/pl/2485-wampir-maskarada-rpg',
                                   'Wilkołak: Apokalipsa': 'https://vanaheim.pl/pl/2486-wilkolak-apokalipsa-rpg',
                                   'Łowca: Porachunek': 'https://vanaheim.pl/pl/2487-lowca-porachunek-rpg'},
                   'Inne Gry RPG': {'Achtung! Chtulhu RPG PL': 'https://vanaheim.pl/pl/2433-achtung-chtulhu-rpg-pl',
                                    'Blade Runner Gra Fabularna': 'https://vanaheim.pl/pl/2338-blade-runner-gra-fabularna',
                                    'Cyberpunk Red': 'https://vanaheim.pl/pl/1129-cyberpunk-red',
                                    'Diuna RPG PL': 'https://vanaheim.pl/pl/2074-diuna-rpg-pl',
                                    'Fallout RPG PL': 'https://vanaheim.pl/pl/2309-fallout-rpg-pl',
                                    'Kult: Boskość Utracona': 'https://vanaheim.pl/pl/1947-kult-boskosc-utracona',
                                    'OBCY RPG': 'https://vanaheim.pl/pl/1853-obcy-rpg-pl',
                                    'Tajemnice Pętli': 'https://vanaheim.pl/pl/1877-tajemnice-petli-rpg',
                                    'Władca Pierścieni': 'https://vanaheim.pl/pl/2267-wladca-pierscieni-rpg'},
                   'White Dwarf': 'https://vanaheim.pl/pl/392-white-dwarf'}}

SKIP_URL_PARTS = (
    "/koszyk",
    "/logowanie",
    "/moje-konto",
    "/kontakt",
    "/content/",
    "controller=",
    "search_query=",
    "karta-podarunkowa",
    "gift-card",
)

SESSION = requests.Session()
SESSION.headers.update(HTML_HEADERS)


def _int_env(name, default=0):
    try:
        return int(os.environ.get(name, default) or default)
    except ValueError:
        return default


def _cache_dir():
    path = BASE_DIR / settings.CACHE_DIR / CACHE_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cache_file(kind, payload):
    text = json.dumps(payload or {}, ensure_ascii=False, sort_keys=True)
    return _cache_dir() / f"{hash_md5(kind + text)}.json"


def clean_text(value):
    return " ".join(str(value or "").replace("\xa0", " ").split()).strip()


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


def normalize_url(url, base=HOME_URL, keep_query=False):
    if not url:
        return ""
    raw = str(url).strip()
    if raw.startswith("//"):
        raw = "https:" + raw
    full = urljoin(base, raw)
    parsed = urlparse(full)
    if parsed.scheme not in {"http", "https"}:
        return ""
    query = parsed.query if keep_query else ""
    return urlunparse((parsed.scheme, parsed.netloc.lower(), parsed.path.rstrip("/") or "/", "", query, ""))


def is_internal_url(url):
    full = normalize_url(url, HOME_URL, keep_query=True)
    if not full:
        return False
    parsed = urlparse(full)
    low = full.lower()
    return parsed.netloc == "vanaheim.pl" and not any(part in low for part in SKIP_URL_PARTS)


def is_product_url(url):
    path = urlparse(normalize_url(url, HOME_URL)).path
    return path.endswith(".html")


def is_bad_html(text, status=None):
    if status and int(status) in {403, 429, 500, 502, 503, 504}:
        return True
    if not text or len(text) < 1000:
        return True
    low = text.lower()
    challenge = ("cf-challenge", "just a moment", "captcha", "access denied")
    has_shop_content = "product-miniature" in low or "product-details" in low or "prestashop" in low
    return any(part in low for part in challenge) and not has_shop_content


def fetch_text(url, *, cache=True, kind="html", headers=None, referer=None, dynamic=False, expect_selector=""):
    full_url = normalize_url(url, HOME_URL, keep_query=True)
    payload = {"url": full_url, "referer": referer or "", "dynamic": bool(dynamic)}
    cache_path = _cache_file(kind, payload)
    if cache and cache_path.exists():
        try:
            with cache_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data["text"], data.get("url") or full_url
        except Exception as exc:
            logger.warning(f"VANAHEIM 读取缓存失败: {cache_path} {exc}")

    request_headers = dict(headers or HTML_HEADERS)
    if referer:
        request_headers["Referer"] = referer
    status = None
    final_url = full_url
    try:
        resp = SESSION.get(full_url, headers=request_headers, impersonate="chrome120", timeout=40)
        text = resp.text
        final_url = resp.url
        status = resp.status_code
    except Exception as exc:
        logger.warning(f"VANAHEIM curl_cffi 请求失败，尝试 Scrapling: {full_url} {type(exc).__name__}: {exc}")
        page = Fetcher.get(full_url, timeout=40000, retries=2, stealthy_headers=True, impersonate=["chrome", "edge"], headers=request_headers)
        text = getattr(page, "body", "") or getattr(page, "html_content", "")
        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="ignore")
        final_url = getattr(page, "url", full_url) or full_url
        status = getattr(page, "status", None)

    if dynamic or is_bad_html(text, status) or (expect_selector and not BeautifulSoup(text, "html.parser").select_one(expect_selector)):
        logger.warning(f"VANAHEIM 静态页疑似无效，尝试 StealthyFetcher: {full_url}")
        page = StealthyFetcher.fetch(
            full_url,
            headless=os.environ.get("HEADLESS", "1") != "0",
            wait=max(1000, _int_env("WAIT", 1) * 1000),
            timeout=60000,
            network_idle=False,
            locale="pl-PL",
            extra_headers=request_headers,
        )
        text = getattr(page, "body", "") or getattr(page, "html_content", "")
        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="ignore")
        final_url = getattr(page, "url", full_url) or full_url
        status = getattr(page, "status", None)

    if cache and text and not is_bad_html(text, status):
        try:
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump({"url": final_url, "text": text}, f, ensure_ascii=False)
        except Exception as exc:
            logger.warning(f"VANAHEIM 写入缓存失败: {full_url} {exc}")
    return text, final_url


def page_url(base_url, page_num):
    full = normalize_url(base_url, HOME_URL, keep_query=True)
    if page_num <= 1:
        return full
    parsed = urlparse(full)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["page"] = str(page_num)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", urlencode(query), ""))


def money_value(value):
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    text = html.unescape(clean_text(value)).replace("zł", "").replace("PLN", "").replace(" ", "")
    text = text.replace(".", "").replace(",", ".") if "," in text else text
    text = re.sub(r"[^0-9.]", "", text)
    if not text:
        return None
    if text.count(".") > 1:
        head, tail = text.rsplit(".", 1)
        text = head.replace(".", "") + "." + tail
    try:
        return round(float(text), 2)
    except ValueError:
        return None


def product_id_from_url(url):
    match = re.search(r"/(\d+)-[^/]+\.html(?:$|[?#])", normalize_url(url, HOME_URL, keep_query=True))
    return match.group(1) if match else ""


def product_key(url):
    return product_id_from_url(url) or normalize_url(url, HOME_URL)


def extract_product_links(soup):
    links = []
    for card in soup.select("article.product-miniature, .product-miniature"):
        href = ""
        for selector in ("a.product-thumbnail[href]", ".product-title a[href]", "a[href]"):
            node = card.select_one(selector)
            if node and node.get("href"):
                href = node.get("href")
                break
        full = normalize_url(href, HOME_URL)
        if full and is_internal_url(full) and is_product_url(full):
            links.append(full)
    if not links:
        for a in soup.select(".products a.product-thumbnail[href], .products .product-title a[href]"):
            full = normalize_url(a.get("href"), HOME_URL)
            if full and is_internal_url(full) and is_product_url(full):
                links.append(full)
    return uniq_keep_order(links, product_key)


def has_next_page(soup, page_num):
    for a in soup.select("a[rel=next], .pagination a[href]"):
        text = clean_text(a.get_text(" ", strip=True)).lower()
        href = a.get("href") or ""
        if "next" in text or "nast?pny" in text:
            return True
        parsed = urlparse(href)
        query = dict(parse_qsl(parsed.query))
        try:
            if int(query.get("page", "0")) > page_num:
                return True
        except ValueError:
            pass
    return False


def clean_fragment(fragment):
    soup = BeautifulSoup(str(fragment or ""), "html.parser")
    for node in soup.select("script, style, svg, picture, source, iframe, video, form, input, button, noscript"):
        node.decompose()
    for node in soup.find_all(string=re.compile(r"Zdjęcie\s+ze\s+strony\s+producenta", re.I)):
        parent = node.parent
        while parent and parent.name not in {"p", "div", "li"}:
            parent = parent.parent
        (parent or node).decompose()
    for tag in soup.find_all("a"):
        tag.unwrap()
    allowed = {"p", "ul", "ol", "li", "table", "tbody", "thead", "tr", "th", "td", "br", "strong", "b", "em", "i", "div", "span", "h2", "h3", "h4", "dl", "dt", "dd", "section"}
    for tag in soup.find_all(True):
        if tag.name not in allowed:
            tag.unwrap()
            continue
        if tag.name in {"h2", "h3", "h4"}:
            tag.name = "h2"
            tag.attrs = {"class": "body-section-title"}
        elif tag.name in {"table", "tbody", "thead", "tr", "th", "td", "ul", "ol", "li", "br", "strong", "b", "em", "i", "dl", "dt", "dd"}:
            tag.attrs = {}
        elif tag.name in {"div", "span", "section"}:
            tag.unwrap()
        else:
            tag.attrs = {}
    for tag in reversed(soup.find_all(["p", "li", "h2", "dt", "dd"])):
        if not clean_text(tag.get_text(" ", strip=True)):
            tag.decompose()
    text = str(soup).strip()
    text = re.sub(r">\s+<", "><", text)
    return text


def body_section(title, fragment):
    cleaned = clean_fragment(fragment)
    if not cleaned:
        return ""
    title_text = clean_text(title)
    cleaned = re.sub(rf'^(?:<h2 class="body-section-title">)?\s*{re.escape(title_text)}\s*(?:</h2>)?', "", cleaned, flags=re.I).strip()
    if not cleaned:
        return ""
    return f'<h2 class="body-section-title">{html_escape(title_text)}</h2>{cleaned}'


def extract_body_intro_image(soup):
    img = soup.select_one(".product-details-info .product-manufacturer img.manufacturer-logo[src]")
    if not img:
        return ""
    src = image_url(img.get("src"))
    if not src:
        return ""
    alt = clean_text(img.get("alt") or "")
    alt_attr = f' alt="{html_escape(alt)}"' if alt else ""
    return f'<div class="body-product-logo"><img src="{html_escape(src)}"{alt_attr}/></div>'


def extract_product_data(soup):
    node = soup.select_one("#product-details[data-product]")
    if not node or not node.get("data-product"):
        return {}
    try:
        return json.loads(html.unescape(node.get("data-product")))
    except Exception as exc:
        logger.warning(f"VANAHEIM data-product JSON 解析失败: {exc}")
        return {}


def extract_title(soup, data):
    title = clean_text(data.get("name") or data.get("meta_title"))
    if title:
        return title
    node = soup.select_one("h1.h1, h1[itemprop=name], h1")
    return clean_text(node.get_text(" ", strip=True) if node else "")


def extract_price(soup, data):
    values = [
        money_value(data.get("price_without_reduction")),
        money_value(data.get("regular_price")),
        money_value(data.get("price")),
    ]
    main = soup.select_one(".product-prices, .product-information, .product-actions")
    if main:
        for node in main.select(".regular-price, .current-price, .product-price [itemprop=price], [itemprop=price]"):
            values.append(money_value(node.get("content") or node.get_text(" ", strip=True)))
    values = [value for value in values if value is not None and value > 0]
    return max(values) if values else None


def best_image_from_obj(image):
    if not isinstance(image, dict):
        return image if isinstance(image, str) else ""
    for key in ("large", "product_zoom", "large_default", "catalog_large", "medium"):
        value = image.get(key)
        if isinstance(value, dict) and value.get("url"):
            return value.get("url")
    by_size = image.get("bySize") or {}
    for key in ("product_zoom", "large_default", "catalog_large", "medium_default"):
        value = by_size.get(key)
        if isinstance(value, dict) and value.get("url"):
            return value.get("url")
    return image.get("url") or image.get("src") or ""


def image_key(url):
    parsed = urlparse(url)
    return re.sub(r"-(?:small|medium|large|home|cart|catalog|slider|product_zoom|large_default|medium_default|catalog_large|catalog_small|home_default|slider_photo|search_photo|attributes_default)(?=/)", "", parsed.path.lower())


def image_url(value):
    if not value:
        return ""
    raw = html.unescape(str(value).strip())
    full = normalize_url(raw, HOME_URL, keep_query=True)
    if full.startswith("data:"):
        return ""
    return full


def extract_images(soup, data):
    images = []
    for image in data.get("images") or []:
        images.append(best_image_from_obj(image))
    if data.get("cover"):
        images.insert(0, best_image_from_obj(data.get("cover")))
    for img in soup.select(".product-images img, .images-container img, .js-qv-product-images img"):
        images.append(img.get("data-image-large-src"))
        images.append(img.get("data-src"))
        images.append(img.get("src"))
    cleaned = []
    for src in images:
        full = image_url(src)
        low = full.lower()
        if not full or any(part in low for part in ("logo", "placeholder", "favicon", ".svg", "/m/")):
            continue
        if "vanaheim.pl" not in low and "warhammer.com" not in low:
            continue
        cleaned.append(full)
    return uniq_keep_order(cleaned, image_key)


def extract_body(soup):
    chunks = []
    intro_image = extract_body_intro_image(soup)
    if intro_image:
        chunks.append(intro_image)
    desc = soup.select_one("#description")
    if desc:
        chunks.append(body_section("Opis", str(desc)))
    details = soup.select_one("#product-details")
    if details:
        detail_soup = BeautifulSoup(str(details), "html.parser")
        for node in detail_soup.select(".product-manufacturer, .vh-gpsr-section, .gpsr-manufacturer, .gpsr-responsible"):
            node.decompose()
        for h in detail_soup.find_all(["h2", "h3", "h4"]):
            if clean_text(h.get_text(" ", strip=True)).casefold() in {"producent", "podmiot odpowiedzialny na terenie ue"}:
                parent = h.parent
                (parent if parent and parent.name == "div" else h).decompose()
        root = detail_soup.select_one("#product-details") or detail_soup
        for attr in ("data-product", "class", "id", "role"):
            if hasattr(root, "attrs"):
                root.attrs.pop(attr, None)
        chunks.append(body_section("Szczegóły produktu", str(root)))
    return "".join(chunk for chunk in chunks if chunk)


def extract_options(soup, data):
    options = []
    for item in soup.select(".product-variants .product-variants-item"):
        if item.select_one("#quantity_wanted") or "quantity" in " ".join(item.get("class") or []):
            continue
        label = clean_text((item.select_one(".control-label, label") or item).get_text(" ", strip=True))
        label = re.sub(r":.*$", "", label).strip()
        values = []
        for selected in item.select("select option"):
            text = clean_text(selected.get_text(" ", strip=True))
            if text:
                values.append(text)
        for radio in item.select("input[type=radio], input[type=checkbox]"):
            val = clean_text(radio.get("title") or radio.get("aria-label") or radio.get("value"))
            if val:
                values.append(val)
        values = uniq_keep_order(values)
        if label and values:
            options.append((label, values if len(values) > 1 else values[0]))
    return options[:3]


def payload_to_start_urls(payload_list):
    result = []
    seen = set()

    def add_item(url, c1, c2="", c3=""):
        full = normalize_url(url, HOME_URL, keep_query=True)
        if not full or not is_internal_url(full):
            return
        key = (clean_text(c1), clean_text(c2), clean_text(c3), full)
        if key in seen:
            return
        seen.add(key)
        result.append({
            "url": full,
            "categories_1": clean_text(c1),
            "categories_2": clean_text(c2),
            "categories_3": clean_text(c3),
            "page_nums": 1,
        })

    def walk(node, path=()):
        if isinstance(node, dict):
            for name, value in node.items():
                walk(value, path + (name,))
            return
        if not path:
            return
        c1 = path[0]
        c2 = path[1] if len(path) > 1 else ""
        c3 = " - ".join(path[2:]) if len(path) > 2 else ""
        add_item(node, c1, c2, c3)

    walk(payload_list)
    max_categories = _int_env("VANAHEIM_MAX_CATEGORIES", 0)
    if max_categories:
        result = result[:max_categories]
    logger.info(f"VANAHEIM PAYLOAD_LIST 目录生成完成: {len(result)} 个")
    return result


class CrawlerObject(Spider):
    driver1 = {"headless": os.environ.get("HEADLESS", "1") != "0", "stealth": True, "wait": max(1, _int_env("WAIT", 1))}
    driver2 = deepcopy(driver1)
    start_urls = []
    is_recollect = _int_env("VANAHEIM_RECOLLECT", 1)
    is_proxy = 0
    collect_thread_number = max(1, _int_env("BATCH", 6))
    more_collect_thread_number = max(1, _int_env("BATCH", 6))
    filename = os.path.basename(__file__)
    name = "_" + filename.replace(".py", "")

    def __init__(self):
        self.max_pages = _int_env("VANAHEIM_MAX_PAGES", 0)
        self.max_products = _int_env("VANAHEIM_MAX_PRODUCTS", 0)
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
        if is_product_url(params["url"]):
            if self._can_emit_product():
                yield deepcopy(params)
            return

        page_num = 1
        while True:
            if self.max_pages and page_num > self.max_pages:
                break
            list_url = page_url(params["url"], page_num)
            html_text, final_url = fetch_text(
                list_url,
                headers=HTML_HEADERS,
                referer=params["url"] if page_num > 1 else HOME_URL,
                kind="list",
                expect_selector="article.product-miniature, .product-miniature",
            )
            soup = BeautifulSoup(html_text, "html.parser")
            product_links = extract_product_links(soup)
            if not product_links:
                logger.warning(f"VANAHEIM 列表页没有商品链接: {final_url}")
                break
            logger.info(f"VANAHEIM 列表页 {final_url} page={page_num} 提取商品 {len(product_links)} 个")
            for href in product_links:
                if not self._can_emit_product():
                    return
                item = deepcopy(params)
                item["url"] = href
                item["list_url"] = final_url
                yield item
            if not has_next_page(soup, page_num):
                break
            page_num += 1

    def get_content(self, params):
        try:
            item = deepcopy(params)
            item["handle"] = self.counter()
            return [item]
        except Exception:
            logger.error(f"VANAHEIM get_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            return []

    def get_more_content(self, params):
        html_text, final_url = fetch_text(params["url"], headers=HTML_HEADERS, referer=params.get("list_url") or HOME_URL, kind="detail", expect_selector="#product-details[data-product]")
        soup = BeautifulSoup(html_text, "html.parser")
        data = extract_product_data(soup)
        title = extract_title(soup, data)
        price = extract_price(soup, data)
        images = extract_images(soup, data)
        if not title or price is None or not images:
            logger.warning(f"VANAHEIM 详情核心字段缺失: title={title!r} price={price} images={len(images)} url={final_url}")
            return None

        item = deepcopy(params)
        item["url"] = normalize_url(data.get("link") or final_url or params["url"], HOME_URL)
        item["title"] = title
        item["subtitle"] = ""
        item["price"] = float(price)
        item["image_src"] = images
        item["body"] = extract_body(soup)
        item["more_info"] = ""
        item["option1_name"] = ""
        item["option1_value"] = ""
        item["option2_name"] = ""
        item["option2_value"] = ""
        item["option3_name"] = ""
        item["option3_value"] = ""
        for index, (name, value) in enumerate(extract_options(soup, data), start=1):
            item[f"option{index}_name"] = name
            item[f"option{index}_value"] = value
        item["size_price"] = ""
        return item


if __name__ == "__main__":
    CrawlerObject().start()
