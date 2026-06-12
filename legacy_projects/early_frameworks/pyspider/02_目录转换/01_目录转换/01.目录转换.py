import json

start_data = {
  "Pilka nozna": {
    "Buty piłkarskie": {
      "Marka": "https://www.unisport.pl/wybierz-marke/",
      "Nawierzchnia": "https://www.unisport.pl/wybierz-powierzchnie/",
      "Kolekcja": "https://www.unisport.pl/wybierz-pakiet/",
      "Rodzaj butów": "https://www.unisport.pl/wybierz-typ/",
      "Kolor butów": "https://www.unisport.pl/buty-pilkarskie/wybierz-kolor-buta/",
      "Buty piłkarskie dla dzieci": "https://www.unisport.pl/dzieciece-buty-pilkarskie/",
      "Buty piłkarskie dla kobiet": "https://www.unisport.pl/buty-pilkarskie-dla-kobiet/",
      "Akcesoria do butów piłkarskich": "https://www.unisport.pl/akcesoria-do-butow-pilkarskich/",
      "Piłka nożna Freestyle": "https://www.unisport.pl/sprzet/freestyle-pilka-nozna/",
      "Edycja limitowana": "https://www.unisport.pl/edycja-limitowana/",
      "Punkty cenowe": "https://www.unisport.pl/punkty-cenowe/"
    },
    "Halówki (IC)": {
      "Buty do wnętrz Nike": "https://www.unisport.pl/buty-pilkarskie/buty-halowe-nike/",
      "Buty piłkarskie w pomieszczeniach New Balance": "https://www.unisport.pl/buty-pilkarskie/buty-do-pilki-halowej-new-balance/",
      "buty do wnętrz adidas": "https://www.unisport.pl/buty-pilkarskie/buty-halowe-adidas/",
      "Buty domowe PUMA": "https://www.unisport.pl/buty-pilkarskie/buty-halowe-puma/",
      "Buty domowe Joma": "https://www.unisport.pl/buty-pilkarskie/buty-halowe-joma/",
      "Buty domowe Mizuno": "https://www.unisport.pl/buty-pilkarskie/buty-halowe-mizuno/"
    },
    "Bramkarstwo": {
      "Rękawice bramkarskie": "https://www.unisport.pl/rekawice-bramkarskie/",
      "Kroje rękawic bramkarskich": "https://www.unisport.pl/bramkarz/rekawice-bramkarskie-cuts/",
      "Akcesoria bramkarskie": "https://www.unisport.pl/wyposazenie-bramkarza/",
      "Koszulki bramkarskie": "https://www.unisport.pl/rekawice-pilkarskie/koszulki-bramkarskie/",
      "Spodnie i spodenki bramkarskie": "https://www.unisport.pl/spodnie-i-spodenki-bramkarskie/",
      "Koszulki bramkarskie dla kibica": "https://www.unisport.pl/bramkarz/koszulki-kibica-bramkarza/"
    },
    "Piłki nożne": {
      "Piłki nożne adidas": "https://www.unisport.pl/pilki-nozne-adidas/",
      "Piłki nożne Select": "https://www.unisport.pl/wybierz-pilki-nozne/",
      "Piłki nożne Nike": "https://www.unisport.pl/pilki-nozne-nike/",
      "Piłki nożne PUMA": "https://www.unisport.pl/puma-pilki-nozne/",
      "Piłki nożne Uhlsport": "https://www.unisport.pl/pilki-nozne-uhlsport/",
      "Piłki nożne Derbystar": "https://www.unisport.pl/pilki-nozne-derbystar/",
      "Piłki nożne Hummel": "https://www.unisport.pl/pilki-nozne-hummel/",
      "Piłki nożne Premier League": "https://www.unisport.pl/pilki-nozne-premier-league/",
      "Piłki nożne Bundesliga": "https://www.unisport.pl/sprzet/pilki-nozne-bundesligi/",
      "Piłki nożne La Liga": "https://www.unisport.pl/pilki-nozne-la-liga/",
      "Piłki nożne Serie A": "https://www.unisport.pl/pilki-nozne-serie-a/",
      "Piłki na halę": "https://www.unisport.pl/pilki-halowe/",
      "Piłki do futsalu": "https://www.unisport.pl/pilki-do-futsalu/",
      "Piłki dla dzieci": "https://www.unisport.pl/pilki-dla-dzieci/"
    },
    "Ochraniacze": {
      "Ochraniacze adidas": "https://www.unisport.pl/ochraniacze-na-golenie-adidas/",
      "Ochraniacze Nike": "https://www.unisport.pl/ochraniacze-na-golenie-nike/",
      "Ochraniacze PUMA": "https://www.unisport.pl/puma-ochraniacze-na-golenie/",
      "Ochraniacze Liiteguard": "https://www.unisport.pl/ochraniacze-na-golenie-liiteguard/",
      "Ochraniacze G-Form": "https://www.unisport.pl/podkladki-do-goleni-g-form/",
      "Ochraniacze Select": "https://www.unisport.pl/wybierz-ochraniacze-na-golenie/",
      "Ochraniacze Uhlsport": "https://www.unisport.pl/uhlsport-ochraniacze-na-golenie/",
      "Ochraniacze Hummel": "https://www.unisport.pl/sprzet/ochraniacze-hummel/",
      "Ochraniacze dla dzieci": "https://www.unisport.pl/podkladki-na-golenie-dla-dzieci/"
    },
    "Odzież termoaktywna": {
      "Bielizna termoaktywna Unisport": "https://www.unisport.pl/odziez-treningowa/unisport-warstwa-podstawowa/",
      "Bielizna termoaktywna Nike": "https://www.unisport.pl/warstwa-podstawowa/nike-warstwa-podstawowa/",
      "Bielizna termoaktywna adidas": "https://www.unisport.pl/warstwa-podstawowa-adidas/",
      "Bielizna termoaktywna Hummel": "https://www.unisport.pl/podlozenie-hummel/",
      "Bielizna termoaktywna PUMA": "https://www.unisport.pl/warstwa-podstawowa-puma/",
      "Bielizna termoaktywna Liiteguard": "https://www.unisport.pl/odziez-treningowa/liiteguard-baselayer/",
      "Bielizna termoaktywna Select": "https://www.unisport.pl/wybierz-warstwe-bazowa/",
      "Bielizna termoaktywna G-Form": "https://www.unisport.pl/g-form-warstwa-podstawowa/",
      "Bielizna termoaktywna dla dzieci": "https://www.unisport.pl/warstwa-podstawowa-dla-dzieci/",
      "Bielizna termoaktywna dla kobiet": "https://www.unisport.pl/warstwa-podstawowa-dla-kobiet/",
      "Odzież termoaktywna - Cold": "https://www.unisport.pl/zachowaj-chlodna-warstwe-podstawowa/",
      "Biustonosze sportowe": "https://www.unisport.pl/odziez-treningowa/biustonosze-sportowe/",
      "Odzież termoaktywna - Hot": "https://www.unisport.pl/zachowaj-cieplo-warstwa-podstawowa/",
      "Legginsy": "https://www.unisport.pl/odziez-treningowa/rajstopy/"
    },
    "Akcesoria i sprzęt piłkarski": {
      "Akcesoria medyczne": "https://www.unisport.pl/produkty-do-pielegnacji-sportu/",
      "Akcesoria trenera": "https://www.unisport.pl/wyposazenie-autokarow/",
      "Akcesoria treningowe": "https://www.unisport.pl/sprzet-treningowy/",
      "Bidony": "https://www.unisport.pl/butelki-na-wode/",
      "Bramki piłkarskie": "https://www.unisport.pl/sprzet-pilkarski/bramki-pilkarskie/",
      "Opaski kapitańskie": "https://www.unisport.pl/opaska-kapitanow/",
      "Pompki": "https://www.unisport.pl/pompy-kulowe/",
      "Ręczniki": "https://www.unisport.pl/sprzet-pilkarski/reczniki/",
      "Taśmy do getr": "https://www.unisport.pl/tasma-skarpetkowa/",
      "Torby": "https://www.unisport.pl/sprzet-pilkarski/torby/",
      "Znaczniki": "https://www.unisport.pl/sprzet/sliniaki-treningowe/"
    },
    "Odzież piłkarska": {},
    "Koszulki klubowe": {
      "Koszulki klubowe dla dzieci": "https://www.unisport.pl/koszulki-pilkarskie-dla-dzieci/",
      "Koszulki klubowe dla kobiet": "https://www.unisport.pl/koszulki-pilkarskie-dla-kobiet/",
      "Komplety klubowe dla niemowląt": "https://www.unisport.pl/fanshop/zestaw-pilkarski-dla-niemowlat/",
      "Spodenki klubowe": "https://www.unisport.pl/fanshop/spodenki-pilkarskie-z-klubow/",
      "Skarpety klubowe": "https://www.unisport.pl/fanshop/skarpety-pilkarskie-z-klubow/"
    },
    "Getry i skarpety": {
      "Wybierz markę": "https://www.unisport.pl/wybierz-marke-skarpet/",
      "Skarpety treningowe": "https://www.unisport.pl/skarpety-treningowe/",
      "Skarpety piłkarskie antypoślizgowe": "https://www.unisport.pl/odziez-treningowa/skarpety-grip/"
    },
    "Dla sędziego": {
      "Odzież sędziowska": "https://www.unisport.pl/odziez-sedziego/",
      "Akcesoria sędziowskie": "https://www.unisport.pl/sprzet-pilkarski/wyposazenie-sedziego/"
    },
    "Kobieca piłka nożna": {
      "Odzież treningowa dla kobiet": "https://www.unisport.pl/sprzet-pilkarski/odziez-treningowa-dla-kobiet/",
      "Legginsy": "https://www.unisport.pl/odziez-treningowa/rajstopy-damskie/",
      "Sneakersy dla kobiet": "https://www.unisport.pl/trampki-dla-kobiet/",
      "Lifestyle dla kobiet": "https://www.unisport.pl/lifestyle/kobiety-na-co-dzien/",
      "Bieganie dla kobiet": "https://www.unisport.pl/bieganie-damskie/"
    }
  },
  "Sklep kibica": {
    "Sklep MŚ": {},
    "Reprezentacje": {
      "Albania": "https://www.unisport.pl/koszulki-pilkarskie/albania/",
      "Algieria": "https://www.unisport.pl/koszulki-pilkarskie/algieria/",
      "Anglia": "https://www.unisport.pl/koszulki-pilkarskie/anglia/",
      "Arabia Saudyjska": "https://www.unisport.pl/koszulki-pilkarskie/arabia-saudyjska/",
      "Argentyna": "https://www.unisport.pl/koszulki-pilkarskie/argentyna/",
      "Australia": "https://www.unisport.pl/koszulki-pilkarskie/australia/",
      "Austria": "https://www.unisport.pl/koszulki-pilkarskie/austria/",
      "Belgia": "https://www.unisport.pl/koszulki-pilkarskie/belgia/",
      "Brazylia": "https://www.unisport.pl/koszulki-pilkarskie/brazylia/",
      "Chile": "https://www.unisport.pl/koszulki-pilkarskie/chile/",
      "Chorwacja": "https://www.unisport.pl/koszulki-pilkarskie/chorwacja/",
      "Czechy": "https://www.unisport.pl/koszulki-pilkarskie/republika-czeska/",
      "Dania": "https://www.unisport.pl/koszulki-pilkarskie/dania/",
      "Egipt": "https://www.unisport.pl/koszulki-pilkarskie/egipt/",
      "Francja": "https://www.unisport.pl/koszulki-pilkarskie/francja/",
      "Ghana": "https://www.unisport.pl/koszulki-pilkarskie/ghana/",
      "Grenlandia": "https://www.unisport.pl/koszulki-pilkarskie/grenlandia/",
      "Hellada": "https://www.unisport.pl/koszulki-pilkarskie/hellada/",
      "Hiszpania": "https://www.unisport.pl/koszulki-pilkarskie/hiszpania/",
      "Holandia": "https://www.unisport.pl/koszulki-pilkarskie/holandia/",
      "Islandia": "https://www.unisport.pl/koszulki-pilkarskie/islandia/",
      "Jamajka": "https://www.unisport.pl/koszulki-pilkarskie/jamajka/",
      "Japonia": "https://www.unisport.pl/koszulki-pilkarskie/japonia/",
      "Kolumbia": "https://www.unisport.pl/koszulki-pilkarskie/kolumbia/",
      "Korea Południowa": "https://www.unisport.pl/koszulki-pilkarskie/korea-poludniowa/",
      "Kostaryka": "https://www.unisport.pl/koszulki-pilkarskie/kostaryka/",
      "Maroko": "https://www.unisport.pl/koszulki-pilkarskie/maroko/",
      "Meksyk": "https://www.unisport.pl/koszulki-pilkarskie/meksyk/",
      "Niemcy": "https://www.unisport.pl/koszulki-pilkarskie/niemcy/",
      "Nigeria": "https://www.unisport.pl/koszulki-pilkarskie/nigerii/",
      "Norwegia": "https://www.unisport.pl/koszulki-pilkarskie/norwegia/",
      "Peru": "https://www.unisport.pl/koszulki-pilkarskie/peru/",
      "Polska": "https://www.unisport.pl/koszulki-pilkarskie/polska/",
      "Portugalia": "https://www.unisport.pl/koszulki-pilkarskie/portugalia/",
      "Republika Południowej Afryki": "https://www.unisport.pl/koszulki-pilkarskie/republika-poludniowej-afryki/",
      "Rumunia": "https://www.unisport.pl/koszulki-pilkarskie/rumunia/",
      "Senegal": "https://www.unisport.pl/koszulki-pilkarskie/senegal/",
      "Serbia": "https://www.unisport.pl/koszulki-pilkarskie/serbia/",
      "Szwajcaria": "https://www.unisport.pl/koszulki-pilkarskie/szwajcaria/",
      "Szwecja": "https://www.unisport.pl/koszulki-pilkarskie/szwecja/",
      "Tunezja": "https://www.unisport.pl/koszulki-pilkarskie/tunezja/",
      "Turcja": "https://www.unisport.pl/koszulki-pilkarskie/turcja/",
      "USA": "https://www.unisport.pl/koszulki-pilkarskie/usa/",
      "Ukraina": "https://www.unisport.pl/koszulki-pilkarskie/ukraina/",
      "Urugwaj": "https://www.unisport.pl/koszulki-pilkarskie/urugwaj/",
      "Wenezuela": "https://www.unisport.pl/koszulki-pilkarskie/wenezuela/",
      "Wybrzeże Kości Słoniowej": "https://www.unisport.pl/koszulki-pilkarskie/wybrzeze-kosci-sloniowej/",
      "Węgry": "https://www.unisport.pl/koszulki-pilkarskie/wegry/",
      "Włochy": "https://www.unisport.pl/koszulki-pilkarskie/wlochy/"
    },
    "Kluby angielskie": {
      "Arsenal": "https://www.unisport.pl/fanshop/arsenal/",
      "Blackburn Rovers": "https://www.unisport.pl/koszulki-pilkarskie/rovers-blackburn/",
      "Bolton Wanderers FC": "https://www.unisport.pl/fanshop/bolton-wanderers-fc/",
      "Burnley": "https://www.unisport.pl/fanshop/burnley/",
      "Chelsea FC": "https://www.unisport.pl/fanshop/chelsea/",
      "Coventry": "https://www.unisport.pl/koszulki-pilkarskie/coventry/",
      "Crystal Palace": "https://www.unisport.pl/koszulki-pilkarskie/krysztalowy-palac/",
      "Everton": "https://www.unisport.pl/koszulki-pilkarskie/everton/",
      "Fulham": "https://www.unisport.pl/koszulki-pilkarskie/fulham/",
      "Liverpool FC": "https://www.unisport.pl/fanshop/liverpoolu/",
      "Manchester City": "https://www.unisport.pl/fanshop/manchester-city/",
      "Manchester United": "https://www.unisport.pl/fanshop/manchester-united/",
      "Queens Park Rangers": "https://www.unisport.pl/koszulki-pilkarskie/queens-park-rangers/",
      "Sheffield United": "https://www.unisport.pl/fanshop/sheffield-united/",
      "Stoke City": "https://www.unisport.pl/koszulki-pilkarskie/stoke-city/",
      "Sunderland": "https://www.unisport.pl/koszulki-pilkarskie/sunderland/",
      "Tottenham Hotspur": "https://www.unisport.pl/fanshop/tottenham/",
      "West Bromwich": "https://www.unisport.pl/koszulki-pilkarskie/west-bromwich/",
      "West Ham United": "https://www.unisport.pl/fanshop/west-ham/",
      "Wrexham AFC": "https://www.unisport.pl/koszulki-pilkarskie/wrexham-afc/"
    },
    "Kluby hiszpańskie": {
      "Athletic Bilbao": "https://www.unisport.pl/koszulki-pilkarskie/athletic-bilbao/",
      "Atletico Madryt": "https://www.unisport.pl/fanshop/atletico-madryt/",
      "FC Barcelona": "https://www.unisport.pl/fanshop/barcelona/",
      "CD Tenerife": "https://www.unisport.pl/koszulki-pilkarskie/cd-teneryfa/",
      "Celta Vigo": "https://www.unisport.pl/koszulki-pilkarskie/celta-vigo/",
      "Deportivo La Coruña": "https://www.unisport.pl/koszulki-pilkarskie/deportivo-la-coruna/",
      "Eibar": "https://www.unisport.pl/koszulki-pilkarskie/eibar/",
      "Girona FC": "https://www.unisport.pl/fanshop/girona-fc/",
      "Levante UD": "https://www.unisport.pl/koszulki-pilkarskie/levante-ud/",
      "Malaga": "https://www.unisport.pl/koszulki-pilkarskie/malaga/",
      "Real Betis": "https://www.unisport.pl/koszulki-pilkarskie/real-betis/",
      "Real Madryt": "https://www.unisport.pl/fanshop/real-madryt/",
      "Real Sociedad": "https://www.unisport.pl/koszulki-pilkarskie/real-sociedad/",
      "Real Valladolid": "https://www.unisport.pl/koszulki-pilkarskie/real-valladolid/",
      "Valencia": "https://www.unisport.pl/fanshop/walencja/"
    },
    "Kluby francuskie": {
      "AJ Auxerre": "https://www.unisport.pl/koszulki-pilkarskie/aj-auxerre/",
      "AS Monaco": "https://www.unisport.pl/koszulki-pilkarskie/as-monaco-fc/",
      "AS Saint-Étienne": "https://www.unisport.pl/koszulki-pilkarskie/as-saint-etienne/",
      "FC Metz": "https://www.unisport.pl/fanshop/fc-metz/",
      "FC Nantes": "https://www.unisport.pl/koszulki-pilkarskie/fc-nantes/",
      "OGC Nicea": "https://www.unisport.pl/koszulki-pilkarskie/ogc-nicea/",
      "Olympique Lyon": "https://www.unisport.pl/koszulki-pilkarskie/olympique-lyon/",
      "Olympique Marsylia": "https://www.unisport.pl/fanshop/olympique-marsylia/",
      "Paris Saint Germain": "https://www.unisport.pl/fanshop/paryz-saint-germain/",
      "RC Lens": "https://www.unisport.pl/koszulki-pilkarskie/obiektyw-rc/",
      "Red Star FC": "https://www.unisport.pl/fanshop/red-star-fc/",
      "Stade Rennais": "https://www.unisport.pl/koszulki-pilkarskie/stadion-rennais/"
    },
    "Kluby niemieckie": {
      "Arminia Bielefeld": "https://www.unisport.pl/koszulki-pilkarskie/arminia-bielefeld/",
      "Bayer Leverkusen": "https://www.unisport.pl/koszulki-pilkarskie/bayer-leverkusen/",
      "Bayern Monachium": "https://www.unisport.pl/fanshop/bayern-monachium/",
      "Borussia Monchengladbach": "https://www.unisport.pl/koszulki-pilkarskie/borussia-monchengladbach/",
      "Eintracht Frankfurt": "https://www.unisport.pl/koszulki-pilkarskie/eintracht-frankfurt/",
      "FC Augsburg": "https://www.unisport.pl/koszulki-pilkarskie/fc-augsburg/",
      "FC Köln": "https://www.unisport.pl/koszulki-pilkarskie/fc-kolonia/",
      "FC Magdeburg": "https://www.unisport.pl/koszulki-pilkarskie/fc-magdeburg/",
      "Hanower 96": "https://www.unisport.pl/koszulki-pilkarskie/hanower-96/",
      "Hertha Berlin": "https://www.unisport.pl/koszulki-pilkarskie/hertha-berlin/",
      "Holstein Kiel": "https://www.unisport.pl/fanshop/holsztyn-kilonia/",
      "Kaiserslautern": "https://www.unisport.pl/koszulki-pilkarskie/kaiserslautern/",
      "Karlsruher SC": "https://www.unisport.pl/koszulki-pilkarskie/karlsruher-sc/",
      "RB Lipsk": "https://www.unisport.pl/koszulki-pilkarskie/rb-lipsk/",
      "Sklep Borussia Dortmund": "https://www.unisport.pl/fanshop/borussia-dortmund/",
      "St. Pauli": "https://www.unisport.pl/koszulki-pilkarskie/sw-pauliego/",
      "Union Berlin": "https://www.unisport.pl/koszulki-pilkarskie/union-berlin/",
      "VfL Bochum": "https://www.unisport.pl/vfl-bochum/",
      "Werder Brema": "https://www.unisport.pl/koszulki-pilkarskie/werder-brema/"
    },
    "Kluby włoskie": {
      "AC Milan": "https://www.unisport.pl/fanshop/sklep-ac-milan/",
      "Atalanta": "https://www.unisport.pl/koszulki-pilkarskie/atalanta/",
      "Bologna": "https://www.unisport.pl/koszulki-pilkarskie/bolonii/",
      "Fiorentina": "https://www.unisport.pl/koszulki-pilkarskie/fiorentina/",
      "Genoa": "https://www.unisport.pl/koszulki-pilkarskie/genua/",
      "Inter Mediolan": "https://www.unisport.pl/fanshop/inter-mediolan/",
      "Juventus Turyn": "https://www.unisport.pl/fanshop/juventus/",
      "Lazio": "https://www.unisport.pl/koszulki-pilkarskie/lazio/",
      "Palermo": "https://www.unisport.pl/koszulki-pilkarskie/palermo/",
      "SSC Napoli": "https://www.unisport.pl/koszulki-pilkarskie/napoli/",
      "Udinese": "https://www.unisport.pl/koszulki-pilkarskie/udinese/"
    },
    "Kluby duńskie": {
      "Aab": "https://www.unisport.pl/koszulki-pilkarskie/aab/",
      "Brøndby IF": "https://www.unisport.pl/koszulki-pilkarskie/brondby-if/",
      "Christiania SC": "https://www.unisport.pl/koszulki-pilkarskie/klub-sportowy-christiania/",
      "FC Kopenhaga": "https://www.unisport.pl/fanshop/fc-kopenhaga/",
      "FC Nordsjælland": "https://www.unisport.pl/fanshop/fc-nordsjaelland/",
      "Lyngby BK": "https://www.unisport.pl/koszulki-pilkarskie/lyngby-bk/",
      "Odense Boldklub": "https://www.unisport.pl/koszulki-pilkarskie/klub-klubowy-odense/",
      "Wendsyssel FF": "https://www.unisport.pl/koszulki-pilkarskie/sprzedaz-ff/"
    },
    "Kluby norweskie": {
      "Bodø/Glimt": "https://www.unisport.pl/bodoglimt-fanshop/",
      "Brann": "https://www.unisport.pl/klub-sportowy-brann/",
      "Stabæk": "https://www.unisport.pl/stabaek-offisiell-fanshop/",
      "Strømsgodset": "https://www.unisport.pl/stromsgodset/"
    },
    "Szwedzkie kluby": {
      "Malmö FF": "https://www.unisport.pl/koszulki-pilkarskie/malmoe-ff/"
    },
    "Pozostałe kluby": {
      "Kluby MLS": "https://www.unisport.pl/koszulki-pilkarskie/kluby-mls/",
      "Kluby Meksykańskie": "https://www.unisport.pl/meksykanskie-koszulki-pilkarskie/",
      "Kluby argentyńskie": "https://www.unisport.pl/kategoria-argentynskie-kluby/",
      "Kluby austriackie": "https://www.unisport.pl/kategoria-kluby-austriackie/",
      "Kluby belgijskie": "https://www.unisport.pl/kluby-belgijskie/",
      "Kluby brazylijskie": "https://www.unisport.pl/brazylijskie-kluby/",
      "Kluby chilijskie": "https://www.unisport.pl/kluby-chilijskie/",
      "Kluby chorwackie": "https://www.unisport.pl/chorwackie-kluby/",
      "Kluby czeskie": "https://www.unisport.pl/czeskie-kluby/",
      "Kluby holenderskie": "https://www.unisport.pl/koszulki-pilkarskie/holenderskie-kluby/",
      "Kluby portugalskie": "https://www.unisport.pl/koszulki-pilkarskie/portugalskie-kluby/",
      "Kluby saudyjsko-arabskie": "https://www.unisport.pl/kluby-saudyjsko-arabskie/",
      "Kluby szkockie": "https://www.unisport.pl/szkockie-kluby/",
      "Kluby szwajcarskie": "https://www.unisport.pl/szwajcarskie-kluby/",
      "Kluby tureckie": "https://www.unisport.pl/kluby-tureckie/",
      "Koszulki piłkarskie RPA": "https://www.unisport.pl/koszulki-pilkarskie-z-rpa/"
    },
    "Kluby Ligi Mistrzów": {
      "Atalanta B.C.": "https://www.unisport.pl/koszulki-pilkarskie/atalanta-bc/",
      "Benfica": "https://www.unisport.pl/koszulki-pilkarskie/benfica/",
      "Club Brugge": "https://www.unisport.pl/club-brugge/",
      "PSV Eindhoven": "https://www.unisport.pl/koszulki-pilkarskie/psv-eindhoven/"
    },
    "Koszulki klubowe": {
      "Koszulki klubowe dla dzieci": "https://www.unisport.pl/koszulki-pilkarskie-dla-dzieci/",
      "Koszulki klubowe dla kobiet": "https://www.unisport.pl/koszulki-pilkarskie-dla-kobiet/",
      "Komplety klubowe dla niemowląt": "https://www.unisport.pl/fanshop/zestaw-pilkarski-dla-niemowlat/",
      "Spodenki klubowe": "https://www.unisport.pl/fanshop/spodenki-pilkarskie-z-klubow/",
      "Skarpety klubowe": "https://www.unisport.pl/fanshop/skarpety-pilkarskie-z-klubow/"
    },
    "Klubowa odzież treningowa": {
      "Spodnie klubowe": "https://www.unisport.pl/spodnie-treningowe-z-odznakami/",
      "Dresy klubowe": "https://www.unisport.pl/dresy-z-odznakami/",
      "Kurtki klubowe": "https://www.unisport.pl/odznakowane-kurtki-treningowe/"
    },
    "Gwiazdy piłki nożnej": {
      "Ada Hegerberg": "https://www.unisport.pl/gwiezdni-gracze/ada-hegerberg/",
      "Aitana Bonmati": "https://www.unisport.pl/gwiezdni-gracze/aitana-bonmati/",
      "Aleksander Isak": "https://www.unisport.pl/gwiezdni-gracze/aleksander-isak/",
      "Alessia Russo": "https://www.unisport.pl/gwiezdni-gracze/alessia-russo/",
      "Alexia Putellas": "https://www.unisport.pl/gwiezdni-gracze/alexia-putellas/",
      "Alexis Sanchez": "https://www.unisport.pl/gwiezdni-gracze/alexis-sanchez/",
      "Antoine Griezmann": "https://www.unisport.pl/gwiazdy-pilki-noznej/antoine-griezmann/",
      "Bruno Fernandes": "https://www.unisport.pl/gwiazdy-pilki-noznej/bruno-fernandes/",
      "Bukayo Saka": "https://www.unisport.pl/bukayo-saka/",
      "Caroline Graham Hansen": "https://www.unisport.pl/gwiezdni-gracze/caroline-graham-hansen/",
      "Christiana Eriksena": "https://www.unisport.pl/gwiazdy-pilki-noznej/christian-eriksen/",
      "Christiana Pulišića": "https://www.unisport.pl/gwiezdni-gracze/christiana-pulisica/",
      "Cody Gakpo": "https://www.unisport.pl/cody-gakpo/",
      "Cristiano Ronaldo": "https://www.unisport.pl/gwiazdy-pilki-noznej/cristiano-ronaldo/",
      "David Álaba": "https://www.unisport.pl/gwiazdy-pilki-noznej/dawid-alaba/",
      "Davida Beckhama": "https://www.unisport.pl/gwiezdni-gracze/davida-beckhama/",
      "Eduardo Camavinga": "https://www.unisport.pl/eduardo-camavinga/",
      "Erling Haaland": "https://www.unisport.pl/gwiazdy-pilki-noznej/erling-haaland/",
      "Frenkie de Jong": "https://www.unisport.pl/gwiazdy-pilki-noznej/frenkie-de-jong/",
      "Fridolina Rolfö": "https://www.unisport.pl/gwiezdni-gracze/fridolina-rolfoe/",
      "Georginio Wijnaldum": "https://www.unisport.pl/gwiazdy-pilki-noznej/georginio-wijnaldum/",
      "Gianluigi Donnarumma": "https://www.unisport.pl/gwiazdy-pilki-noznej/gianluigi-donnarumma/",
      "Harry'ego Kane'a": "https://www.unisport.pl/gwiazdy-pilki-noznej/harryego-kanea/",
      "Jadon Sancho": "https://www.unisport.pl/gwiezdni-gracze/jadon-sancho/",
      "Jamal Musiala": "https://www.unisport.pl/jamal-musiala/",
      "João Félix": "https://www.unisport.pl/gwiezdni-gracze/joao-felix/",
      "Jude Bellingham": "https://www.unisport.pl/gwiazdy-pilki-noznej/jude-bellingham/",
      "Julii Gwinn": "https://www.unisport.pl/gwiezdni-gracze/julii-gwinn/",
      "Kai Havertz": "https://www.unisport.pl/kai-havertz/",
      "Karim Benzema": "https://www.unisport.pl/gwiazdy-pilki-noznej/karim-benzema/",
      "Kevin De Bruyne": "https://www.unisport.pl/gwiazdy-pilki-noznej/kevina-de-bruyne/",
      "Kylian Mbappé": "https://www.unisport.pl/gwiezdni-gracze/kylian-mbappe/",
      "Lamine Yamal": "https://www.unisport.pl/gwiezdni-gracze/lamina-jamal/",
      "Leah Williamson": "https://www.unisport.pl/gwiezdni-gracze/leah-williamson/",
      "Lena Oberdorf": "https://www.unisport.pl/gwiezdni-gracze/lena-oberdorf/",
      "Leroy Sane": "https://www.unisport.pl/gwiazdy-pilki-noznej/leroy-sane/",
      "Lieke Martens": "https://www.unisport.pl/gwiezdni-gracze/lieke-martens/",
      "Lionel Messi": "https://www.unisport.pl/gwiazdy-pilki-noznej/lionel-messi/",
      "Luis Suarez": "https://www.unisport.pl/gwiazdy-pilki-noznej/luis-suarez/",
      "Manuel Neuer": "https://www.unisport.pl/gwiazdy-pilki-noznej/manuel-neuer/",
      "Marcus Rashford": "https://www.unisport.pl/gwiazdy-pilki-noznej/marcusa-rashforda/",
      "Martin Ødegaard": "https://www.unisport.pl/gwiazdy-pilki-noznej/martin-odegaard/",
      "Mary Earps": "https://www.unisport.pl/gwiezdni-gracze/mary-earps/",
      "Matthijs de Ligt": "https://www.unisport.pl/gwiezdni-gracze/matthijs-de-ligt/",
      "Mohamed Salah": "https://www.unisport.pl/gwiazdy-pilki-noznej/mohamed-salah/",
      "Neymar Jr.": "https://www.unisport.pl/gwiazdy-pilki-noznej/neymar-jr/",
      "Paulo Dybala": "https://www.unisport.pl/gwiazdy-pilki-noznej/paulo-dybala/",
      "Pernille Harder": "https://www.unisport.pl/gwiezdni-gracze/pernille-harder/",
      "Phil Foden": "https://www.unisport.pl/phil-foden/",
      "Raheem Sterling": "https://www.unisport.pl/gwiezdni-gracze/raheem-sterling/",
      "Rasmus Højlund": "https://www.unisport.pl/rasmus-hojlund/",
      "Robert Lewandowski": "https://www.unisport.pl/gwiazdy-pilki-noznej/roberta-lewandowskiego/",
      "Romelu Lukaku": "https://www.unisport.pl/gwiezdni-gracze/romelu-lukaku/",
      "Sadio Mané": "https://www.unisport.pl/gwiazdy-pilki-noznej/sadio-mane/",
      "Sakina Karchaoui": "https://www.unisport.pl/gwiezdni-gracze/kadidiatou-diani/",
      "Sam Kerr": "https://www.unisport.pl/gwiezdni-gracze/sam-kerr/",
      "Serge Gnabry": "https://www.unisport.pl/gwiazdy-pilki-noznej/serge-gnabry/",
      "Sergio Ramos": "https://www.unisport.pl/gwiezdni-gracze/sergio-ramos/",
      "Son Heung-Min": "https://www.unisport.pl/gwiezdni-gracze/syn-heung-min/",
      "Toni Kroos": "https://www.unisport.pl/gwiazdy-pilki-noznej/toni-kroos/",
      "Victor Lindelöf": "https://www.unisport.pl/gwiazdy-pilki-noznej/victor-lindeloef/",
      "Vinicius Junior": "https://www.unisport.pl/gwiezdni-gracze/vinicius-junior/",
      "Virgil van Dijk": "https://www.unisport.pl/gwiezdni-gracze/wergiliusz-van-dijk/",
      "Vivianne Miedema": "https://www.unisport.pl/gwiezdni-gracze/vivianne-miedema/",
      "Wendie Renard": "https://www.unisport.pl/gwiezdni-gracze/sakina-karchaoui/",
      "Xavi Simmons": "https://www.unisport.pl/xavi-simmons/"
    },
    "Gadżety klubowe": {
      "Pościele": "https://www.unisport.pl/posciel/",
      "Szaliki": "https://www.unisport.pl/fanshop/szalik-pilkarski/",
      "Gadżety AC Milan": "https://www.unisport.pl/fanshop/towar-ac-milan/",
      "Gadżety Arsenal FC": "https://www.unisport.pl/fanshop/towar-arsenal/",
      "Gadżety Atletico Madryt": "https://www.unisport.pl/fanshop/towar-atletico-madryt/",
      "Gadżety FC Barcelona": "https://www.unisport.pl/fanshop/towar-w-barcelonie/",
      "Gadżety Bayern Monachium": "https://www.unisport.pl/fanshop/towar-bayern-monachium/",
      "Gadżety Chelsea FC": "https://www.unisport.pl/fanshop/towar-chelsea/",
      "Gadżety Juventus FC": "https://www.unisport.pl/fanshop/towar-juventus/",
      "Gadżety Liverpool FC": "https://www.unisport.pl/fanshop/towar-z-liverpoolu/",
      "Gadżety Manchester City": "https://www.unisport.pl/fanshop/towar-z-manchesteru-city/",
      "Gadżety Manchester United": "https://www.unisport.pl/fanshop/towar-manchester-united/",
      "Gadżety Paris Saint Germain": "https://www.unisport.pl/fanshop/paris-saint-germain-towar/"
    },
    "Tajemnicze pudełka": {}
  },
  "Odziez treningowa": {
    "Spodnie treningowe": {
      "Spodnie treningowe adidas": "https://www.unisport.pl/odziez-treningowa/adidas-spodnie-treningowe/",
      "Spodnie treningowe Nike": "https://www.unisport.pl/odziez-treningowa/spodnie-treningowe-nike/",
      "Spodnie treningowe PUMA": "https://www.unisport.pl/odziez-treningowa/spodnie-treningowe-puma/",
      "Spodnie treningowe dla dzieci": "https://www.unisport.pl/spodnie-treningowe-dla-dzieci/"
    },
    "Spodenki treningowe": {
      "Spodenki treningowe adidas": "https://www.unisport.pl/odziez-treningowa/adidas-spodenki-treningowe/",
      "Spodenki treningowe Nike": "https://www.unisport.pl/odziez-treningowa/szorty-treningowe-nike/",
      "Spodenki treningowe PUMA": "https://www.unisport.pl/odziez-treningowa/szorty-treningowe-puma/",
      "Spodenki treningowe Hummel": "https://www.unisport.pl/odziez-treningowa/spodenki-treningowe-hummel/",
      "Spodenki treningowe dla dzieci": "https://www.unisport.pl/odziez-treningowa/szorty-treningowe-dla-dzieci/",
      "Spodenki treningowe dla kobiet": "https://www.unisport.pl/odziez-treningowa/szorty-treningowe-dla-kobiet/"
    },
    "Koszulki treningowe": {
      "Koszulki z krótkim rękawem": "https://www.unisport.pl/topy-z-krotkim-rekawem/",
      "Koszulki z długim rękawem": "https://www.unisport.pl/topy-z-dlugim-rekawem/"
    },
    "Dresy treningowe": {
      "Dresy Nike": "https://www.unisport.pl/odziez-treningowa/dres-nike/",
      "Dresy adidas": "https://www.unisport.pl/odziez-treningowa/dres-adidas/"
    },
    "Bluzy z zamkiem": {
      "Koszulki": "https://www.unisport.pl/football365/t-shirty/",
      "Bluzy z kapturem": "https://www.unisport.pl/bluzy-z-kapturem/",
      "Koszulki polo": "https://www.unisport.pl/koszulki-polo/",
      "Bluzy": "https://www.unisport.pl/bluzy/",
      "Skarpetki": "https://www.unisport.pl/football365/skarpetki/",
      "Spodenki kąpielowe": "https://www.unisport.pl/lifestyle/spodenki-kapielowe/",
      "Bielizna": "https://www.unisport.pl/football365/bielizna/",
      "Czapki": "https://www.unisport.pl/czapki/",
      "Kapelusze": "https://www.unisport.pl/kapelusze/",
      "Torby": "https://www.unisport.pl/sprzet-pilkarski/torby/",
      "Spodenki": "https://www.unisport.pl/football365/spodenki/",
      "Spodnie dresowe": "https://www.unisport.pl/spodnie-dresowe/"
    },
    "Trening zimowy": {
      "Kominy": "https://www.unisport.pl/ocieplacze-na-szyje/",
      "Opaski do włosów": "https://www.unisport.pl/sprzet-pilkarski/opaski-do-wlosow/",
      "Frotki": "https://www.unisport.pl/opaski/"
    },
    "Kurtki": {
      "Kurtki treningowe": "https://www.unisport.pl/sprzet-pilkarski/kurtki-treningowe/",
      "Kurtki zimowe": "https://www.unisport.pl/lifestyle/kurtki-zimowe/",
      "Kurtki przeciwdeszczowe": "https://www.unisport.pl/trening-w-zime/kurtki-przeciwdeszczowe/",
      "Kurtki wiatrówki": "https://www.unisport.pl/odziez-treningowa/wiatrowka/"
    },
    "Buty treningowe": {},
    "Odzież termoaktywna": {
      "Bielizna termoaktywna Unisport": "https://www.unisport.pl/odziez-treningowa/unisport-warstwa-podstawowa/",
      "Bielizna termoaktywna Nike": "https://www.unisport.pl/warstwa-podstawowa/nike-warstwa-podstawowa/",
      "Bielizna termoaktywna adidas": "https://www.unisport.pl/warstwa-podstawowa-adidas/",
      "Bielizna termoaktywna Hummel": "https://www.unisport.pl/podlozenie-hummel/",
      "Bielizna termoaktywna PUMA": "https://www.unisport.pl/warstwa-podstawowa-puma/",
      "Bielizna termoaktywna Liiteguard": "https://www.unisport.pl/odziez-treningowa/liiteguard-baselayer/",
      "Bielizna termoaktywna Select": "https://www.unisport.pl/wybierz-warstwe-bazowa/",
      "Bielizna termoaktywna G-Form": "https://www.unisport.pl/g-form-warstwa-podstawowa/",
      "Bielizna termoaktywna dla dzieci": "https://www.unisport.pl/warstwa-podstawowa-dla-dzieci/",
      "Bielizna termoaktywna dla kobiet": "https://www.unisport.pl/warstwa-podstawowa-dla-kobiet/",
      "Odzież termoaktywna - Cold": "https://www.unisport.pl/zachowaj-chlodna-warstwe-podstawowa/",
      "Biustonosze sportowe": "https://www.unisport.pl/odziez-treningowa/biustonosze-sportowe/",
      "Odzież termoaktywna - Hot": "https://www.unisport.pl/zachowaj-cieplo-warstwa-podstawowa/",
      "Legginsy": "https://www.unisport.pl/odziez-treningowa/rajstopy/"
    },
    "Rękawiczki zimowe": {
      "Rękawiczki adidas": "https://www.unisport.pl/sprzet/rekawice-dla-graczy-adidas/",
      "Rękawiczki Nike": "https://www.unisport.pl/sprzet/rekawice-dla-graczy-nike/",
      "Rękawiczki Nike hyperwarm": "https://www.unisport.pl/sprzet/rekawice-nike-hyperwarm/",
      "Rękawiczki PUMA": "https://www.unisport.pl/sprzet/rekawiczki-puma/",
      "Rękawiczki Unisport": "https://www.unisport.pl/sprzet/rekawiczki-unisport/"
    },
    "Czapki zimowe": {
      "Czapki Nike": "https://www.unisport.pl/odziez-treningowa/czapki-nike/",
      "Czapki adidas": "https://www.unisport.pl/odziez-treningowa/czapki-adidas/",
      "Czapki PUMA": "https://www.unisport.pl/odziez-treningowa/czapki-puma/",
      "Czapki dla dzieci": "https://www.unisport.pl/odziez-treningowa/czapki-dla-dzieci/"
    },
    "Wybierz kolekcję odzieży treningowej": {
      "Nike Academy": "https://www.unisport.pl/lifestyle/akademia-nike/",
      "Nike Dry": "https://www.unisport.pl/lifestyle/nike-dry/",
      "Nike Football Training": "https://www.unisport.pl/nike-football-training/",
      "Nike Park": "https://www.unisport.pl/lifestyle/park-nike/",
      "Nike Strike": "https://www.unisport.pl/lifestyle/nike-strike/",
      "PUMA Liga": "https://www.unisport.pl/lifestyle/puma-liga/",
      "adidas Condivo": "https://www.unisport.pl/sprzet-pilkarski/adidas-condivo/",
      "adidas Core": "https://www.unisport.pl/lifestyle/adidas-rdzen/",
      "adidas Tango": "https://www.unisport.pl/lifestyle/adidas-tango/",
      "adidas Tiro": "https://www.unisport.pl/lifestyle/adidas-tiro/"
    },
    "Odzież treningowa dla kobiet": {
      "Koszulki treningowe damskie": "https://www.unisport.pl/odziez-treningowa/damskie-koszulki-treningowe/",
      "Koszulki gimnastyczne": "https://www.unisport.pl/damskie-topy-gimnastyczne/",
      "Legginsy": "https://www.unisport.pl/odziez-treningowa/rajstopy-damskie/",
      "Koszulki damskie": "https://www.unisport.pl/lifestyle/koszulki-damskie/",
      "Buty do biegania dla kobiet": "https://www.unisport.pl/buty-do-biegania-dla-kobiet/"
    },
    "Odzież treningowa dla dzieci": {
      "Dresy dla dzieci": "https://www.unisport.pl/odziez-treningowa/dresy-dla-dzieci/",
      "Kurtki dla dzieci": "https://www.unisport.pl/lifestyle/kurtki-dla-dzieci/",
      "Buty do biegania dla dzieci": "https://www.unisport.pl/buty-do-biegania-dla-dzieci/"
    }
  },
  "Bieganie": {
    "Buty do biegania": {
      "Buty do biegania Nike": "https://www.unisport.pl/buty-do-biegania/nike-buty-do-biegania/",
      "Buty do biegania adidas": "https://www.unisport.pl/adidas-buty-do-biegania/",
      "Buty do biegania PUMA": "https://www.unisport.pl/puma-buty-do-biegania/",
      "Buty do biegania New Balance": "https://www.unisport.pl/buty-do-biegania/new-balance-buty-do-biegania/",
      "Buty do biegania Mizuno": "https://www.unisport.pl/bieganie/mizuno-buty-do-biegania/",
      "Buty do biegania dla kobiet": "https://www.unisport.pl/buty-do-biegania-dla-kobiet/",
      "Buty do biegania dla dzieci": "https://www.unisport.pl/buty-do-biegania-dla-dzieci/"
    },
    "Odzież do biegania": {
      "Odzież do biegania LiiteGuard": "https://www.unisport.pl/odziez-treningowa/odziez-do-biegania-liiteguard/"
    },
    "Bieganie dla kobiet": {}
  },
  "Lifestyle": {
    "Sneakersy": {
      "Sneakersy adidas": "https://www.unisport.pl/adidas-trampki/",
      "Sneakersy Nike": "https://www.unisport.pl/sneakersy-nike/",
      "Sneakersy New Balance": "https://www.unisport.pl/trampki-new-balance/",
      "Sneakersy PUMA": "https://www.unisport.pl/trampki-puma/",
      "Sneakersy Asics": "https://www.unisport.pl/lifestyle/trampki-asics/",
      "Sneakersy dla kobiet": "https://www.unisport.pl/trampki-dla-kobiet/",
      "Sneakersy dla dzieci": "https://www.unisport.pl/trampki-dla-dzieci/",
      "Akcesoria do pielęgnacji butów": "https://www.unisport.pl/lifestyle/pielegnacja-tenisowek/",
      "Kolor butów sneakers": "https://www.unisport.pl/lifestyle/wybierz-kolor-sneakersow/"
    },
    "Klapki": {
      "Sandały adidas": "https://www.unisport.pl/lifestyle/adidas-sandaly/",
      "Sandały Nike": "https://www.unisport.pl/lifestyle/sandaly-nike/",
      "Sandały H2O": "https://www.unisport.pl/lifestyle/sandaly-h2o/",
      "Crocs": "https://www.unisport.pl/lifestyle/crocs/",
      "Sandały Birkenstock": "https://www.unisport.pl/lifestyle/sandaly-birkenstock/",
      "Slajdy dla kobiet": "https://www.unisport.pl/lifestyle/slajdy-dla-kobiet/",
      "Klapki dla dzieci": "https://www.unisport.pl/lifestyle/zjezdzalnie-dla-dzieci/"
    },
    "Odzież lifestyle": {
      "Kurtki": "https://www.unisport.pl/lifestyle/kurtki/",
      "Koszulki": "https://www.unisport.pl/football365/t-shirty/",
      "Bluzy z kapturem": "https://www.unisport.pl/bluzy-z-kapturem/",
      "Koszulki polo": "https://www.unisport.pl/koszulki-polo/",
      "Bluzy": "https://www.unisport.pl/bluzy/",
      "Bluzy z zamkiem": "https://www.unisport.pl/topy-dresowe/",
      "Skarpetki": "https://www.unisport.pl/football365/skarpetki/",
      "Spodenki kąpielowe": "https://www.unisport.pl/lifestyle/spodenki-kapielowe/",
      "Bielizna": "https://www.unisport.pl/football365/bielizna/",
      "Czapki": "https://www.unisport.pl/czapki/",
      "Kapelusze": "https://www.unisport.pl/kapelusze/",
      "Torby": "https://www.unisport.pl/sprzet-pilkarski/torby/",
      "Spodenki": "https://www.unisport.pl/football365/spodenki/",
      "Spodnie dresowe": "https://www.unisport.pl/spodnie-dresowe/"
    },
    "Tech Fleece": {},
    "Kolekcje lifestyle": {
      "Nike T90": "https://www.unisport.pl/nike-t90/",
      "adidas Tango": "https://www.unisport.pl/adidas-tango/",
      "adidas Z.N.E.": "https://www.unisport.pl/adidas-zne/",
      "adidas Originals": "https://www.unisport.pl/oryginaly-adidas/",
      "Nike Tech Fleece": "https://www.unisport.pl/polar-nike-tech/",
      "Nike F.C.": "https://www.unisport.pl/football365/nike-fc/",
      "PUMATECH": "https://www.unisport.pl/lifestyle/",
      "Unisportlife Collection": "https://www.unisport.pl/football365/kolekcja-unisportlife/",
      "Nike Jordan x PSG": "https://www.unisport.pl/nike-jordan-x-psg/"
    },
    "Lifestyle dla kobiet": {
      "Bluzy damskie": "https://www.unisport.pl/lifestyle/bluzy-z-kapturem-damskie/",
      "Spodnie dresowe dla kobiet": "https://www.unisport.pl/lifestyle/spodnie-dresowe-dla-kobiet/",
      "Koszulki damskie": "https://www.unisport.pl/lifestyle/koszulki-damskie/",
      "Bielizna damska": "https://www.unisport.pl/lifestyle/bielizna-damska/"
    },
    "Lifestyle dla dzieci": {
      "Koszulki dla dzieci": "https://www.unisport.pl/lifestyle/koszulki-dla-dzieci/",
      "Bluzy z kapturem dla dzieci": "https://www.unisport.pl/lifestyle/bluzy-z-kapturem-dla-dzieci/",
      "Bluzy dla dzieci": "https://www.unisport.pl/lifestyle/bluzy-dla-dzieci/",
      "Spodnie dresowe dla dzieci": "https://www.unisport.pl/odziez-treningowa/spodnie-dresowe-dla-dzieci/",
      "Kurtki dla dzieci": "https://www.unisport.pl/lifestyle/kurtki-dla-dzieci/",
      "Kurtki zimowe dla dzieci": "https://www.unisport.pl/kurtki-zimowe-dla-dzieci/",
      "Bielizna dla dzieci": "https://www.unisport.pl/lifestyle/bielizna-dla-dzieci/",
      "Czapki dla dzieci": "https://www.unisport.pl/lifestyle/czapki-dla-dzieci/"
    },
    "Klubowa odzież lifestyle": {
      "Atletico Madryt lifestyle": "https://www.unisport.pl/fanshop/atletico-madryt-styl-zycia/",
      "FC Barcelona lifestyle": "https://www.unisport.pl/fanshop/barcelona-styl-zycia/",
      "Chelsea FC lifestyle": "https://www.unisport.pl/fanshop/chelsea-styl-zycia/",
      "Inter Mediolan lifestyle": "https://www.unisport.pl/fanshop/inter-mediolan-styl-zycia/",
      "Liverpool FC lifestyle": "https://www.unisport.pl/fanshop/liverpool-styl-zycia/",
      "Paris Saint Germain lifestyle": "https://www.unisport.pl/fanshop/paris-saint-germain-styl-zycia/",
      "Tottenham lifestyle": "https://www.unisport.pl/fanshop/tottenham-styl-zycia/"
    },
    "Odzież lifestyle reprezentacji": {}
  },
  "Dla druzyn": {
    "Odzież dla drużyn": {
      "Koszulki drużynowe": "https://www.unisport.pl/teamsport/koszulki-druzynowe/",
      "Spodenki drużynowe": "https://www.unisport.pl/teamsport/szorty-druzynowe/",
      "Skarpety i getry drużynowe": "https://www.unisport.pl/teamsport/skarpetki-druzynowe/",
      "Odzież treningowa dla drużyn": "https://www.unisport.pl/team-sport/odziez-treningowa-zespolu/"
    },
    "Piłki nożne": {
      "Piłki nożne adidas": "https://www.unisport.pl/pilki-nozne-adidas/",
      "Piłki nożne Select": "https://www.unisport.pl/wybierz-pilki-nozne/",
      "Piłki nożne Nike": "https://www.unisport.pl/pilki-nozne-nike/",
      "Piłki nożne PUMA": "https://www.unisport.pl/puma-pilki-nozne/",
      "Piłki nożne Uhlsport": "https://www.unisport.pl/pilki-nozne-uhlsport/",
      "Piłki nożne Derbystar": "https://www.unisport.pl/pilki-nozne-derbystar/",
      "Piłki nożne Hummel": "https://www.unisport.pl/pilki-nozne-hummel/",
      "Piłki nożne Premier League": "https://www.unisport.pl/pilki-nozne-premier-league/",
      "Piłki nożne Bundesliga": "https://www.unisport.pl/sprzet/pilki-nozne-bundesligi/",
      "Piłki nożne La Liga": "https://www.unisport.pl/pilki-nozne-la-liga/",
      "Piłki nożne Serie A": "https://www.unisport.pl/pilki-nozne-serie-a/",
      "Piłki na halę": "https://www.unisport.pl/pilki-halowe/",
      "Piłki do futsalu": "https://www.unisport.pl/pilki-do-futsalu/",
      "Piłki dla dzieci": "https://www.unisport.pl/pilki-dla-dzieci/"
    },
    "Akcesoria treningowe": {
      "Akcesoria do butów piłkarskich": "https://www.unisport.pl/akcesoria-do-butow-pilkarskich/",
      "Akcesoria medyczne": "https://www.unisport.pl/produkty-do-pielegnacji-sportu/",
      "Bidony": "https://www.unisport.pl/butelki-na-wode/",
      "Bramki piłkarskie": "https://www.unisport.pl/sprzet-pilkarski/bramki-pilkarskie/",
      "Opaski kapitańskie": "https://www.unisport.pl/opaska-kapitanow/",
      "Pompki": "https://www.unisport.pl/pompy-kulowe/",
      "Ręczniki": "https://www.unisport.pl/sprzet-pilkarski/reczniki/",
      "Taśmy do getr": "https://www.unisport.pl/tasma-skarpetkowa/",
      "Torby": "https://www.unisport.pl/sprzet-pilkarski/torby/"
    },
    "Znaczniki": {},
    "Akcesoria trenera": {},
    "Dla sędziego": {
      "Odzież sędziowska": "https://www.unisport.pl/odziez-sedziego/",
      "Akcesoria sędziowskie": "https://www.unisport.pl/sprzet-pilkarski/wyposazenie-sedziego/"
    },
    "Kluby partnerskie Unisport": {
      "Academy NF": "https://www.unisport.pl/akademia-nf/",
      "BK Sukienka": "https://www.unisport.pl/bk-sukienka/",
      "FC Helsingør Talent": "https://www.unisport.pl/team-sport/fc-helsingor-talent/",
      "Obóz piłkarski Liverpool": "https://www.unisport.pl/oboz-pilkarski-liverpool/"
    }
  },
  "Wiosenna wyprzedaz": {
    "Wyprzedaż butów piłkarskich": {
      "Buty piłkarskie Nike w sprzedaży": "https://www.unisport.pl/buty-pilkarskie-nike-w-sprzedazy/",
      "Buty piłkarskie adidas w sprzedaży": "https://www.unisport.pl/buty-pilkarskie-adidas-na-wyprzedazy/",
      "PUMA Buty piłkarskie w sprzedaży": "https://www.unisport.pl/buty-pilkarskie-puma-w-sprzedazy/",
      "Buty piłkarskie dla dzieci w sprzedaży": "https://www.unisport.pl/dzieciece-buty-pilkarskie-w-sprzedazy/"
    },
    "Wyprzedaż koszulek piłkarskich": {
      "Wyprzedaż bluz z kapturem": "https://www.unisport.pl/bluzy-z-kapturem-w-sprzedazy/",
      "Wyprzedaż Nike Tech Fleece": "https://www.unisport.pl/nike-tech-fleece-na-wyprzedazy/",
      "Wyprzedaż butów na halę": "https://www.unisport.pl/buty-halowe-w-sprzedazy/",
      "Wyprzedaż piłek nożnych": "https://www.unisport.pl/pilki-nozne-na-sprzedaz/",
      "Wyprzedaż ochraniaczy": "https://www.unisport.pl/ochraniacze-na-golenie-w-sprzedazy/",
      "Wyprzedaż sprzętu bramkarskiego": "https://www.unisport.pl/sprzedaz-dla-bramkarzy/",
      "Wyprzedaż skarpet i getrów piłkarskich": "https://www.unisport.pl/skarpety-pilkarskie-w-sprzedazy/",
      "Wyprzedaż odzieży termoaktywnej": "https://www.unisport.pl/warstwa-podstawowa-w-sprzedazy/",
      "Wyprzedaż odzieży treningowej": "https://www.unisport.pl/odziez-treningowa-w-sprzedazy/",
      "Wyprzedaż butów do biegania": "https://www.unisport.pl/buty-do-biegania-w-sprzedazy/",
      "Wyprzedaż odzieży klubowej": "https://www.unisport.pl/odziez-treningowa-z-odznakami-w-sprzedazy/",
      "Wyprzedaż lifestyle": "https://www.unisport.pl/moda-sportowa-na-sprzedaz/",
      "Wyprzedaż butów Sneakers": "https://www.unisport.pl/trampki-na-wyprzedazy/",
      "Wyprzedaż produktów dla dzieci": "https://www.unisport.pl/wyprzedaz-dla-dzieci/",
      "Wyprzedaż produktów dla kobiet": "https://www.unisport.pl/wyprzedaz-dla-kobiet/"
    }
  },
  "Outlet": {
    "Buty piłkarskie Outlet":"https://www.unisport.pl/wyprzedaz/buty-pilkarskie-outlet/",
    "Koszulki piłkarskie Outlet":"https://www.unisport.pl/wyprzedaz/koszulki-pilkarskie-outlet/",
    "Outlet dla biegacza": "https://www.unisport.pl/wyprzedaz/outlet-dla-biegacza/",
    "Odzież treningowa Outlet": "https://www.unisport.pl/wyprzedaz/outlet-odziez-treningowa/",
    "Sneakers Outlet": "https://www.unisport.pl/wyprzedaz/trampki-outlet/",
    "Bluzy Outlet": "https://www.unisport.pl/wyprzedaz/bluzy-outlet/"
  }

}

def normalize_keys(data):
    if isinstance(data, dict):
        new_dict = {}
        for key, value in data.items():
            # 1. 去除首尾空格
            # 2. 将多个连续空格替换为单个空格
            # 3. 将逗号替换为斜杠（注意保留空格）
            # 4. 将首字母转为大写
            key = str(key).strip()
            key = ' '.join(key.split())  # 处理多余空格

            # 替换逗号为斜杠（考虑可能的不同格式）
            if ',' in key:
                key = key.replace(',', ' /')

            # 将每个单词的首字母转为大写（保持葡萄牙语特殊字符）
            words = key.split()
            capitalized_words = []
            for word in words:
                if word:  # 确保单词不为空
                    # 保持特殊字符如 + 号不变
                    if word in ['+', '/', '&', '-']:
                        capitalized_words.append(word)
                    else:
                        # 首字母大写，其余保持原样
                        capitalized_words.append(word[0].upper() + word[1:] if len(word) > 0 else word)

            new_key = ' '.join(capitalized_words)

            # 递归处理值（保留原顺序）
            new_dict[new_key] = normalize_keys(value)
        return new_dict
    elif isinstance(data, list):
        return [normalize_keys(item) for item in data]
    else:
        return data


def normalize_json_structure(data):
    """标准化整个JSON数据结构"""
    # 处理键名（保留原顺序）
    normalized = normalize_keys(data)

    # 检查并确保所有URL值是字符串
    def ensure_string_values(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, str) and value.startswith('http'):
                    # URL已经是字符串，保持不变
                    continue
                elif isinstance(value, dict):
                    ensure_string_values(value)
                elif isinstance(value, list):
                    for item in value:
                        ensure_string_values(item)
        return obj

    return ensure_string_values(normalized)


# 处理数据
processed_data = normalize_json_structure(start_data)

# 保存到文件（移除sort_keys=True，保留原顺序）
with open('02_data.json', 'w', encoding='utf-8') as f:
    json.dump(processed_data, f, indent=4, ensure_ascii=False)  # 关键修改：删除sort_keys=True

print("处理完成！已生成合法的JSON数据（保留原字典顺序）。")
print(f"文件已保存为: 02_data.json")
print(f"顶层键: {list(processed_data.keys())}")

# 显示部分处理结果作为示例
# print("\n示例处理结果:")
# for category, subcategories in list(processed_data.items())[:2]:
#     print(f"\n{category}:")
#     for subcat, items in list(subcategories.items())[:2]:
#         print(f"  - {subcat}:")
#         if isinstance(items, dict):
#             for item, url in list(items.items())[:2]:
#                 print(f"    * {item}: {url[:50]}...")
#         else:
#             print(f"    * URL: {items[:50]}...")