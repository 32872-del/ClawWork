# -*- coding: utf-8 -*-
import json
import os
import re
import threading
import time
import traceback
from copy import deepcopy
from html import escape as html_escape
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup, Comment
from loguru import logger
from scrapling.fetchers import Fetcher, StealthyFetcher

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("HEADLESS", "1")
os.environ.setdefault("BATCH", "4")
os.environ.setdefault("WAIT", "1")
os.environ.setdefault("KARACA_MAX_CATEGORIES", "0")
os.environ.setdefault("KARACA_MAX_PAGES", "0")
os.environ.setdefault("KARACA_MAX_PRODUCTS", "0")
os.environ.setdefault("KARACA_RECOLLECT", "1")

from fnspider import Spider, hash_md5, settings  # noqa: E402

SITE = "https://www.karaca.com"
HOME_URL = f"{SITE}/"
CACHE_NAME = "_54_karaca"

REQUEST_HEADERS = {
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.5",
}
HTML_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
}
JSON_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "application/json,text/javascript,*/*;q=0.01",
    "User-Agent": HTML_HEADERS["User-Agent"],
    "X-Requested-With": "XMLHttpRequest",
}

PAYLOAD_LIST = {
    "Sofra": {
        "Yemek Takımları": {
            "12 Kişilik Yemek Takımı": "https://www.karaca.com/12-kisilik-yemek-takimi",
            "6 Kişilik Yemek Takımı": "https://www.karaca.com/6-kisilik-yemek-takimi",
            "2-4 Kişilik Yemek Takımı": "https://www.karaca.com/2-4-kisilik-yemek-takimi",
        },
        "Kahvaltı Takımı": {
            "6 Kişilik Kahvaltı Takımı": "https://www.karaca.com/6-kisilik-kahvalti-takimi",
            "4 Kişilik Kahvaltı Takımı": "https://www.karaca.com/4-kisilik-kahvalti-takimi",
            "Tekli Kahvaltılık": "https://www.karaca.com/tekli-kahvaltilik",
        },
        "Çatal Kaşık Bıçak Takımları": {
            "12 Kişilik Çatal Kaşık Bıçak Takımı": "https://www.karaca.com/12-kisilik-catal-kasik-bicak-takimi",
            "6 Kişilik Çatal Kaşık Bıçak Takımı": "https://www.karaca.com/6-kisilik-catal-kasik-bicak-takimi",
            "Tekli Çatal Kaşık Bıçak Serileri": "https://www.karaca.com/tekli-catal-kasik-bicak-serileri",
            "Dondurma Kaşığı": "https://www.karaca.com/dondurma-kasigi",
            "Sofra Servis Seti": "https://www.karaca.com/sofra-servis-seti",
        },
        "Kahve Fincan Takımı": "https://www.karaca.com/kahve-fincan-takimi",
        "İçecek Sunum": {
            "Muglar Kupalar": "https://www.karaca.com/muglar-kupalar",
            "Çay Fincan Takımı": "https://www.karaca.com/cay-fincan-takimi",
            "Espresso Fincan Takımı": "https://www.karaca.com/espresso-fincan-takimi",
            "Sürahi": "https://www.karaca.com/surahi",
        },
        "Bardak ve Bardak Seti": {
            "Meşrubat Bardağı": "https://www.karaca.com/mesrubat-bardagi",
            "Su Bardağı": "https://www.karaca.com/su-bardagi",
            "Çay Bardağı": "https://www.karaca.com/cay-bardagi",
            "Kahve Yanı Bardağı": "https://www.karaca.com/kahve-yani-bardagi",
            "Karaf Seti": "https://www.karaca.com/karaf-seti",
            "Kadehler": "https://www.karaca.com/kadehler",
            "Çay Seti": "https://www.karaca.com/cay-seti",
            "Bardak Altlığı ve Çay Tabağı": "https://www.karaca.com/bardak-altligi-ve-cay-tabagi",
        },
        "Servis Sunum": {
            "Kek ve Pasta Takımları": "https://www.karaca.com/kek-ve-pasta-takimlari",
            "Kek Servis ve Kek Fanusları": "https://www.karaca.com/kek-servis-ve-kek-fanuslari",
            "Kurabiyelik": "https://www.karaca.com/kurabiyelik",
            "Değirmen": "https://www.karaca.com/degirmen",
            "Yağdanlık Sirkelik": "https://www.karaca.com/yagdanlik-sirkelik",
            "Tuzluk Biberlik": "https://www.karaca.com/tuzluk-biberlik",
            "Tepsi": "https://www.karaca.com/tepsi",
            "Meyvelik": "https://www.karaca.com/meyvelik",
            "Şekerlik": "https://www.karaca.com/sekerlik",
            "Peçetelik": "https://www.karaca.com/pecetelik",
            "Supla": "https://www.karaca.com/supla",
            "Buz Kovası": "https://www.karaca.com/buz-kovasi",
        },
        "Tekli Ürünler": {
            "Tabak": "https://www.karaca.com/tabak",
            "Kaseler": "https://www.karaca.com/kaseler",
            "Servis Tabağı": "https://www.karaca.com/servis-tabagi",
            "Pasta Tabağı": "https://www.karaca.com/pasta-tabagi",
            "Çukur Tabak": "https://www.karaca.com/cukur-tabak",
            "Çerezlik": "https://www.karaca.com/cerezlik",
            "Kayık Tabak": "https://www.karaca.com/kayik-tabak",
        },
        "Sofra Tekstili": {
            "Peçete / Peçete Halkaları": "https://www.karaca.com/pecete-pecete-halkalari",
            "Masa Örtüsü Takımı": "https://www.karaca.com/masa-ortusu-takimi",
            "Runner": "https://www.karaca.com/runner",
            "Amerikan Servisleri": "https://www.karaca.com/amerikan-servisleri",
        },
    },
    "Mutfak": {
        "Pişirme": {
            "Tencere Seti": "https://www.karaca.com/tencere-seti",
            "Düdüklü Tencere": "https://www.karaca.com/duduklu-tencere",
            "Tekli Tencereler": "https://www.karaca.com/tek-tencere",
            "Tava ve Tava Setleri": "https://www.karaca.com/tek-tava",
            "Kek Kalıpları": "https://www.karaca.com/kek-kaliplari",
            "Sos Tenceresi ve Sütlük": "https://www.karaca.com/sutluk-sosluk",
            "Sahan ve Sahan Seti": "https://www.karaca.com/sahan-ve-sahan-seti",
            "Çelik Çeyiz Seti": "https://www.karaca.com/celik-ceyiz-seti",
            "Fırın Kabı": "https://www.karaca.com/firin-kabi",
        },
        "Saklama Düzenleme": {
            "Saklama Kabı": "https://www.karaca.com/saklama-kabi",
            "Baharatlık ve Baharat Takımı": "https://www.karaca.com/baharatlik-baharat-takimi",
            "Ekmek Sepeti ve Kutusu": "https://www.karaca.com/ekmek-sepeti-ve-kutusu",
            "Kaşıklık": "https://www.karaca.com/kasiklik",
            "Mutfak Organizer": "https://www.karaca.com/mutfak-organizer",
            "Çöp Kovaları": "https://www.karaca.com/cop-kovalari",
            "Kavanoz": "https://www.karaca.com/kavanoz",
        },
        "Bıçak & Bıçak Seti": {
            "Bıçak Seti": "https://www.karaca.com/bicak-seti",
            "Ekmek Bıçakları": "https://www.karaca.com/ekmek-bicaklari",
            "Şef Bıçakları": "https://www.karaca.com/sef-bicaklari",
            "Soyma Bıçakları": "https://www.karaca.com/soyma-bicaklari",
        },
        "Mutfak Gereçleri": {
            "Kesme ve Sunum Tahtası": "https://www.karaca.com/kesme-tahtasi",
            "Servis Gereçleri": "https://www.karaca.com/servis-gerecleri",
            "Manuel Rondo ve Doğrayıcı": "https://www.karaca.com/manuel-rondo-dograyici",
            "Spatulalar": "https://www.karaca.com/spatulalar",
            "Soyacak": "https://www.karaca.com/soyacak",
            "Ölçek": "https://www.karaca.com/olcek",
            "Mutfak Makası": "https://www.karaca.com/cok-amacli-makas",
            "Rende": "https://www.karaca.com/rende",
            "Süzgeç": "https://www.karaca.com/suzgec",
            "Karıştırma Kabı": "https://www.karaca.com/karistirma-kabi",
            "Sarımsak Ezici": "https://www.karaca.com/sarimsak-ezici",
            "Tirbüşon": "https://www.karaca.com/tirbuson",
            "Sıkacak": "https://www.karaca.com/sikacak",
        },
        "İçecek Hazırlama": {
            "Termos": "https://www.karaca.com/termos",
            "Çaydanlık": "https://www.karaca.com/caydanlik",
            "Demlik": "https://www.karaca.com/demlik",
            "French Press": "https://www.karaca.com/french-press",
            "Kahve Ekipmanları": "https://www.karaca.com/kahve-ekipmanlari",
            "Cezve ve Cezve Takımı": "https://www.karaca.com/cezve-ve-cezve-takimi",
            "Kokteyl Ekipmanları": "https://www.karaca.com/kokteyl",
        },
        "Mutfak Tekstili": {
            "Mutfak Havlusu": "https://www.karaca.com/mutfak-havlusu",
            "Mutfak Önlüğü": "https://www.karaca.com/mutfak-onlugu",
        },
    },
    "Küçük Ev Aletleri": {
        "Kahve Makineleri": {
            "Türk Kahve Makinesi": "https://www.karaca.com/turk-kahve-makinesi",
            "Filtre Kahve Makinesi": "https://www.karaca.com/filtre-kahve-makinesi",
            "Espresso Makinesi": "https://www.karaca.com/espresso-makinesi",
        },
        "Elektrikli İçecek Hazırlama": {
            "Çaycı - Çay Makinesi": "https://www.karaca.com/cayci-cay-makinesi",
            "Su Isıtıcısı Kettle": "https://www.karaca.com/su-isiticisi-kettle",
            "Smoothie Blender": "https://www.karaca.com/smoothie-blender",
            "Katı Meyve Sıkacağı": "https://www.karaca.com/kati-meyve-sikacagi",
            "Narenciye Sıkacağı": "https://www.karaca.com/narenciye-sikacagi",
        },
        "Gıda Hazırlama": {
            "Mutfak Şefi ve Hamur Yoğurma Makinesi": "https://www.karaca.com/mutfak-sefi",
            "Mutfak Robotu": "https://www.karaca.com/mutfak-robotu",
            "El Mikseri ve Blenderı": "https://www.karaca.com/el-mikseri-ve-blenderi",
            "Doğrayıcı ve Rondo": "https://www.karaca.com/dograyici-ve-rondo",
            "Kıyma Makinesi": "https://www.karaca.com/kiyma-makinesi",
            "Makarna Makinesi": "https://www.karaca.com/makarna-makinesi",
            "Yoğurt Makinesi": "https://www.karaca.com/yogurt-makinesi",
            "Dondurma Makinesi": "https://www.karaca.com/dondurma-makinesi",
            "Pamuk Şeker Makinesi": "https://www.karaca.com/pamuk-seker",
        },
        "Elektrikli Pişirme Aletleri": {
            "Fritöz ve Airfryer": "https://www.karaca.com/fritoz",
            "Tost Makinesi": "https://www.karaca.com/tost-makinesi",
            "Pizza Makinesi": "https://www.karaca.com/pizza-makinesi",
            "Ekmek Kızartma Makinesi": "https://www.karaca.com/ekmek-kizartma-makinesi",
            "Waffle Makinesi": "https://www.karaca.com/waffle-makinesi",
            "Fırın": "https://www.karaca.com/firin",
            "Hotdog Sosis Makinesi": "https://www.karaca.com/hotdog-sosis-makinesi",
            "Mısır Patlatma Makinesi": "https://www.karaca.com/misir-patlatma-makinesi",
        },
        "Elektrikli Süpürge": {
            "Dikey Süpürge": "https://www.karaca.com/dikey-supurge",
            "Toz Torbasız Süpürge": "https://www.karaca.com/toz-torbasiz-supurge",
            "Halı ve Koltuk Yıkama Makinesi": "https://www.karaca.com/hali-ve-koltuk-yikama-makinesi",
            "Robot Süpürge": "https://www.karaca.com/robot-supurge",
            "Islak Kuru Kablosuz Süpürge": "https://www.karaca.com/islak-kuru-kablosuz-supurge",
        },
        "Ütüler": {
            "Buhar Kazanlı Ütüler": "https://www.karaca.com/buhar-kazanli-utuler",
        },
        "Elektrikli Ev Aletleri": {
            "Hava Temizleme ve Hava Nemlendirme": "https://www.karaca.com/hava-temizleme-hava-nemlendirme",
            "Vantilatör": "https://www.karaca.com/vantilator",
            "Su Arıtma Cihazı": "https://www.karaca.com/su-aritma-cihazi",
            "Mutfak Tartısı": "https://www.karaca.com/mutfak-tartisi",
            "Vakum Makineleri": "https://www.karaca.com/vakum-makineleri",
        },
        "Kişisel Bakım": {
            "Saç Şekillendirici": "https://www.karaca.com/sac-sekillendirici",
            "Ağız Bakım": "https://www.karaca.com/agiz-bakim",
            "Saç Kurutma Makinesi": "https://www.karaca.com/sac-kurutma-makinesi",
        },
        "Elektrikli Çeyiz Seti": "https://www.karaca.com/elektrikli-ceyiz-seti",
    },
    "Ev ve Yaşam": {
        "Yatak Odası": {
            "Nevresim Takımları": "https://www.karaca.com/nevresim-takimlari",
            "Pike Takımları": "https://www.karaca.com/pike-takimlari",
            "Yatak Örtüleri": "https://www.karaca.com/yatak-ortuleri",
            "Battaniye": "https://www.karaca.com/battaniye",
            "Yorgan": "https://www.karaca.com/yorgan",
            "Çarşaflar": "https://www.karaca.com/carsaf",
            "Uyku Setleri": "https://www.karaca.com/uyku-setleri",
            "Yastık Kılıfı": "https://www.karaca.com/yastik-kilifi",
            "Alez": "https://www.karaca.com/alez",
            "Yatak Odası Çeyiz Seti": "https://www.karaca.com/yatak-odasi-ceyiz-seti",
        },
        "Dekorasyon": {
            "Dekoratif Aksesuar": "https://www.karaca.com/dekoratif-aksesuar",
            "Aydınlatma": "https://www.karaca.com/aydinlatma",
            "Kırlentler": "https://www.karaca.com/kirlentler",
            "Vazo": "https://www.karaca.com/vazo",
            "Çerçeve": "https://www.karaca.com/cerceve",
            "Dekoratif Tepsi": "https://www.karaca.com/dekoratif-tepsi",
            "Biblo": "https://www.karaca.com/biblo",
            "Dekoratif Tabak": "https://www.karaca.com/dekoratif-tabak",
            "Şamdan - Mumluk": "https://www.karaca.com/samdan-mumluk",
            "Anahtarlık": "https://www.karaca.com/anahtarlik",
            "Saksı / Çiçek": "https://www.karaca.com/saksi-cicek",
            "Yılbaşı Çam Ağacı": "https://www.karaca.com/yilbasi-cam-agaci",
            "Mum": "https://www.karaca.com/mum",
            "Sepet - Organizer": "https://www.karaca.com/sepet-organizer",
        },
        "Halılar": {
            "Yolluk": "https://www.karaca.com/yolluk",
            "Oda Halısı": "https://www.karaca.com/oda-halisi",
            "Salon Halısı": "https://www.karaca.com/salon-halisi",
            "Paspas": "https://www.karaca.com/paspas",
            "Kapı Önü Paspası": "https://www.karaca.com/kapi-onu-paspasi",
            "Çocuk / Genç Halısı": "https://www.karaca.com/cocuk-genc-halisi",
            "Kilim": "https://www.karaca.com/kilim",
        },
        "Banyo": {
            "Havlu": "https://www.karaca.com/havlu",
            "Bornoz": "https://www.karaca.com/bornoz",
            "Banyo Aksesuarları": "https://www.karaca.com/banyo-aksesuarlari",
            "Banyo Paspası": "https://www.karaca.com/banyo-paspasi",
            "Banyo Seti": "https://www.karaca.com/banyo-setleri",
        },
        "Ev Gereçleri": {
            "Ütü Masası": "https://www.karaca.com/utu-masasi",
            "Çamaşır Askısı": "https://www.karaca.com/camasir-askisi",
            "Çamaşır Sepeti": "https://www.karaca.com/camasir-sepeti",
            "Çöp Kovası": "https://www.karaca.com/cop-kovasi",
            "Ev Terliği": "https://www.karaca.com/ev-terligi",
        },
        "Ortam ve Oda Kokuları": "https://www.karaca.com/koku",
        "Anne & Bebek": {
            "Bebek Odası Tekstili": "https://www.karaca.com/bebek-odasi",
            "Çocuk Genç Odası Tekstili": "https://www.karaca.com/cocuk-genc-odasi",
            "Bebek Çocuk Bornozları": "https://www.karaca.com/bebek-cocuk-bornozlari",
            "Mama Takımı": "https://www.karaca.com/mama-takimlari",
        },
        "Aydınlatma": {
            "Abajur": "https://www.karaca.com/abajur",
            "Aplik": "https://www.karaca.com/aplik",
            "Avize": "https://www.karaca.com/avize",
            "Lambader": "https://www.karaca.com/lambader",
        },
    },
    "Hobi Eğlence": {
        "Spor & Outdoor": {
            "Kişisel Termos": "https://www.karaca.com/kisisel-termos",
            "Suluklar Mataralar": "https://www.karaca.com/suluklar-mataralar",
            "Mangal ve Ekipmanları": "https://www.karaca.com/mangal-ve-ekipmanlari",
            "Kamp Malzemeleri": "https://www.karaca.com/kamp-malzemeleri",
            "Spor Malzemeleri": "https://www.karaca.com/spor-malzemeleri",
        },
        "Parti": {
            "Parti Kostümü": "https://www.karaca.com/parti-kostumu",
            "Parti Malzemeleri": "https://www.karaca.com/parti-malzemeleri",
        },
        "Kişisel Bakım ve Kozmetik": {
            "Koku": "https://www.karaca.com/koku",
            "Kolonya": "https://www.karaca.com/kolonya",
            "Vücut Spreyi": "https://www.karaca.com/vucut-spreyi",
            "Sabun": "https://www.karaca.com/sabun",
            "Takı Toka": "https://www.karaca.com/taki-toka",
            "Bakım Malzemeleri": "https://www.karaca.com/bakim-malzemeleri",
        },
        "Kırtasiye": {
            "Kalem": "https://www.karaca.com/kalem",
            "Ofis Malzemeleri": "https://www.karaca.com/ofis-malzemeleri",
            "Ajanda ve Not Defteri": "https://www.karaca.com/ajanda-ve-not-defteri",
            "Takvimler ve Planlayıcılar": "https://www.karaca.com/takvim-ve-planlayici",
            "Elektronik Aksesuarlar": "https://www.karaca.com/elektronik",
            "Hediye Paketi": "https://www.karaca.com/hediye-paketii",
        },
        "Oyun ve Eğlence": {
            "Oyuncak": "https://www.karaca.com/oyuncak",
            "Kart Masa Oyunları": "https://www.karaca.com/kart-masa-oyunlari",
            "Parti Malzemeleri": "https://www.karaca.com/parti-malzemeleri",
        },
        "Hobi Malzemeleri": {
            "Çizim ve Boyama": "https://www.karaca.com/cizim-ve-boyama",
            "Kendin Yap": "https://www.karaca.com/kendin-yap",
            "El İşi Malzemeleri": "https://www.karaca.com/el-isi-malzemeleri",
        },
        "Seyahat": {
            "Seyahat Aksesuarları": "https://www.karaca.com/seyahat-aksesuarlari",
            "Valiz": "https://www.karaca.com/valiz",
            "Yelpaze": "https://www.karaca.com/yelpaze",
            "Çantalar": "https://www.karaca.com/cantalar",
        },
        "Gıda": {
            "Kahvaltılıklar": "https://www.karaca.com/kahvaltiliklar",
            "Çaylar": "https://www.karaca.com/caylar",
            "Kahveler": "https://www.karaca.com/kahveler",
            "Sağlıklı Atıştırmalıklar": "https://www.karaca.com/saglikli-atistirmaliklar",
            "Yağlar": "https://www.karaca.com/yaglar",
            "Soslar ve Lezzetlendiriciler": "https://www.karaca.com/soslar-ve-lezzetlendiriciler",
            "Unlar - Bakliyatlar - Tahıllar": "https://www.karaca.com/unlar-bakliyatlar-tahillar",
        },
        "Pet Shop": {
            "Kedi Malzemeleri": "https://www.karaca.com/kedi-malzemeleri",
            "Köpek Malzemeleri": "https://www.karaca.com/kopek-malzemeleri",
        },
    },
    "Hediye": {
        "Tüm Hediyeler": "https://www.karaca.com/hediye-lp",
        "Kişiye Göre Hediyeler": {
            "Anneme Hediyeler": "https://www.karaca.com/anneme-hediyeler",
            "Babama Hediyeler": "https://www.karaca.com/babama-hediyeler",
            "Sevgiliye Hediye": "https://www.karaca.com/sevgiliye-hediye",
            "Kadınlara Özel Hediyeler": "https://www.karaca.com/kadinlara-ozel-hediyeler",
            "Erkeklere Özel Hediyeler": "https://www.karaca.com/erkeklere-ozel-hediyeler",
            "Ofis Hediyeleri": "https://www.karaca.com/ofis-hediyeleri",
            "Patili Dostlarımıza Hediyeler": "https://www.karaca.com/pet-shop",
        },
        "Özel Günlere Göre Hediyeler": {
            "Sevgililer Günü Hediyesi": "https://www.karaca.com/sevgiliye-hediye",
            "Doğum Günü Hediyesi": "https://www.karaca.com/dogum-gunu-hediyeleri",
            "Anneler Günü Hediyesi": "https://www.karaca.com/anneme-hediyeler",
            "Babalar Günü Hediyesi": "https://www.karaca.com/babama-hediyeler",
            "Yeni iş ve Terfi Hediyesi": "https://www.karaca.com/yeni-is-ve-terfi-hediyeleri",
            "Düğün Hediyesi": "https://www.karaca.com/dugun-hediyeleri",
            "Öğretmenler Günü Hediyesi": "https://www.karaca.com/ogretmenler-gunu-hediyesi",
            "Yılbaşı Hediyesi": "https://www.karaca.com/yilbasi-urunleri",
        },
        "Hediye Paketi Yapılabilir Ürünler": {
            "Hediye Setleri": "https://www.karaca.com/hediye-setleri",
            "Hediye Paketi": "https://www.karaca.com/hediye-paketii",
        },
    },
    # "Çeyiz Seti": "https://www.karaca.com/ceyiz-seti-kampanyalari",
    "İndirimli Ürünler": "https://www.karaca.com/indirimli-urunler",
    "Çok Satan": "https://www.karaca.com/cok-satanlar",
}

SKIP_URL_PARTS = (
    "/account",
    "/blog",
    "/cart",
    "/marka",
    "/product/search",
    "/uye",
    "hediye-karti",
    "hediye_karti",
)
SKIP_TEXT_PARTS = ("hediye kart", "gift card")
PRODUCT_URL_MARKER = "/urun/"

d1 = {
    "headless": os.environ.get("HEADLESS", "1") != "0",
    "stealth": True,
    "wait": _wait if (_wait := int(os.environ.get("WAIT", "1") or 1)) else 1,
}
d2 = deepcopy(d1)

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
    if hasattr(value, "get_text"):
        value = value.get_text(" ", strip=True)
    return " ".join(str(value or "").replace("\xa0", " ").split()).strip()


def uniq_keep_order(values, key_func=None):
    result = []
    seen = set()
    for value in values or []:
        if value is None:
            continue
        key = key_func(value) if key_func else value
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def normalize_url(url, base=HOME_URL, keep_query=False):
    if not url:
        return ""
    full = urljoin(base, str(url).strip())
    parsed = urlparse(full)
    if parsed.scheme not in {"http", "https"}:
        return ""
    path = re.sub(r"/{2,}", "/", parsed.path)
    query = parsed.query if keep_query else ""
    return urlunparse((parsed.scheme, parsed.netloc, path.rstrip("/") or "/", "", query, ""))


def is_internal_url(url):
    parsed = urlparse(url)
    return parsed.netloc in {"www.karaca.com", "karaca.com", ""}


def is_skipped_url(url, text=""):
    lower = ((url or "") + " " + (text or "")).casefold()
    return any(part in lower for part in SKIP_URL_PARTS) or any(part in lower for part in SKIP_TEXT_PARTS)


def response_text(resp):
    if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
        resp.encoding = resp.apparent_encoding or "utf-8"
    return resp.text


def fetch_requests(url, headers=None, referer=None):
    request_headers = dict(headers or HTML_HEADERS)
    if referer:
        request_headers["Referer"] = referer
    resp = SESSION.get(url, headers=request_headers, timeout=35)
    if resp.status_code >= 400:
        raise requests.HTTPError(f"{resp.status_code} {url}", response=resp)
    return response_text(resp), resp.url


def fetch_scrapling(url, headers=None, referer=None, stealth=False):
    request_headers = dict(headers or HTML_HEADERS)
    if referer:
        request_headers["Referer"] = referer
    fetcher = StealthyFetcher if stealth else Fetcher
    page = fetcher.get(url, headers=request_headers, **(d1 if stealth else {}))
    text = getattr(page, "text", None) or str(page)
    final_url = getattr(page, "url", None) or url
    return text, final_url


def fetch_text(url, headers=None, referer=None, kind="html"):
    cache = _cache_file(kind, {"url": url})
    if cache.exists():
        return cache.read_text(encoding="utf-8"), url
    last_error = None
    for attempt in range(3):
        try:
            text, final_url = fetch_requests(url, headers=headers, referer=referer)
            if text and len(text) > 20:
                cache.write_text(text, encoding="utf-8")
                return text, final_url
        except Exception as exc:
            last_error = exc
            logger.warning(f"Karaca requests 失败({attempt + 1}/3): {url} {exc}")
            time.sleep(0.7 + attempt)
    for stealth in (False, True):
        try:
            text, final_url = fetch_scrapling(url, headers=headers, referer=referer, stealth=stealth)
            if text and len(text) > 20:
                cache.write_text(text, encoding="utf-8")
                return text, final_url
        except Exception as exc:
            last_error = exc
            logger.warning(f"Karaca Scrapling 失败 stealth={stealth}: {url} {exc}")
    raise RuntimeError(f"Karaca 请求失败: {url} {last_error}")


def fetch_json(url, headers=None, referer=None, kind="json"):
    text, final_url = fetch_text(url, headers=headers or JSON_HEADERS, referer=referer, kind=kind)
    return json.loads(text), final_url


def parse_price(value):
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = clean_text(value)
    text = text.replace("TL", "").replace("TRY", "").strip()
    text = re.sub(r"[^\d,.\-]", "", text)
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?", text):
        text = text.replace(".", "").replace(",", ".")
    elif "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def product_price(*sources):
    values = []
    for source in sources:
        if not source:
            continue
        for key in (
            "data-productoriginalprice",
            "data-productprice",
            "unFormattedOldPrice",
            "unFormattedPrice",
            "old_price",
            "price",
            "unit_price",
            "unit_sale_price",
            "item_originalPrice",
            "item_sale_price",
        ):
            if isinstance(source, dict) and key in source:
                price = parse_price(source.get(key))
                if price is not None:
                    values.append(price)
    return max(values) if values else None


def normalize_image_url(url):
    if not url:
        return ""
    full = str(url).replace("\\/", "/").strip()
    if full.startswith("//"):
        full = "https:" + full
    elif full.startswith("/"):
        full = urljoin(SITE, full)
    elif full.startswith("image/") or full.startswith("static/"):
        full = "https://cdn.karaca.com/" + full
    full = urljoin(SITE, full)
    parsed = urlparse(full)
    if not parsed.netloc or "karaca.com" not in parsed.netloc:
        return ""
    path = re.sub(r"/rcman/cw\d+h\d+q\d+gm/", "/rcman/cw1200h1200q90gm/", parsed.path)
    if "/rcman/" not in path and "/image/" in path:
        path = path.replace("/image/", "/rcman/cw1200h1200q90gm/image/", 1)
    return urlunparse((parsed.scheme or "https", parsed.netloc, path, "", "", ""))


def valid_product_image(url):
    lower = (url or "").casefold()
    if not lower:
        return False
    blocked = ("logo", "icon", "payment", "mastercard", "visa", "badge", "placeholder", "no-image", "favicon")
    return "cdn.karaca.com" in lower and not any(part in lower for part in blocked)


def extract_images(soup, list_info=None, detail_data=None):
    images = []
    if isinstance(detail_data, dict):
        images.append(normalize_image_url(detail_data.get("product_image_url")))
    if isinstance(list_info, dict):
        images.append(normalize_image_url(list_info.get("image") or list_info.get("thumb") or list_info.get("data-product-image-url")))
        for thumb in list_info.get("thumbs") or []:
            if isinstance(thumb, dict):
                images.append(normalize_image_url(thumb.get("image") or thumb.get("thumbnail")))
    for selector in (
        ".photos img",
        ".product-image img",
        ".productDetailImage img",
        ".swiper-slide img",
        "#productInfoWrap img",
    ):
        for img in soup.select(selector):
            for attr in ("data-src", "data-original", "srcset", "src"):
                value = img.get(attr)
                if not value:
                    continue
                if attr == "srcset":
                    value = value.split(",")[-1].strip().split(" ")[0]
                images.append(normalize_image_url(value))
    return uniq_keep_order([image for image in images if valid_product_image(image)])


def clean_body_html(fragment):
    soup = BeautifulSoup(fragment or "", "html.parser")
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    for bad in soup.select("script, style, svg, form, button, input, noscript, iframe, img"):
        bad.decompose()
    for tag in soup.find_all(True):
        if tag.name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            tag.name = "h2"
            tag.attrs = {"class": "body-section-title"}
        elif tag.name in {"table", "tbody", "tr", "td", "th", "ul", "ol", "li", "p", "strong", "em", "br"}:
            tag.attrs = {}
        else:
            tag.attrs = {}
    cleaned = str(soup).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r">\s+<", "><", cleaned)
    return cleaned


def body_section(title, html):
    html = clean_body_html(html)
    if not html:
        return ""
    return f'<h2 class="body-section-title">{html_escape(title)}</h2>{html}'


def specs_html(soup):
    panel = soup.select_one("#panel-specs")
    if not panel:
        return ""
    table = panel.select_one("table")
    if table and clean_text(table):
        return str(table)
    labels = []
    for row in panel.select(".item, .label, tr"):
        parts = [clean_text(part) for part in row.find_all(["span", "td"], recursive=False)]
        parts = [part for part in parts if part]
        if len(parts) >= 2:
            labels.append((parts[0].rstrip(":"), parts[1]))
    if labels:
        rows = "".join(f"<tr><td>{html_escape(name)}</td><td>{html_escape(value)}</td></tr>" for name, value in labels)
        return f"<table><tbody>{rows}</tbody></table>"
    return ""


def extract_body(soup):
    chunks = []
    desc = soup.select_one("#panel-desc .desc, #panel-desc, .description-body, .productInfo-desc")
    if desc and clean_text(desc):
        chunks.append(body_section("Ürün Açıklaması", str(desc)))
    spec = specs_html(soup)
    if spec:
        chunks.append(body_section("Ürün Özellikleri", spec))
    return "".join(chunks)


def extract_datalayer_product(html_text):
    match = re.search(r"window\.datalayer_product\s*=\s*(\{.*?\})\?\.", html_text or "", re.S)
    if not match:
        return {}
    try:
        data = json.loads(match.group(1))
        return data.get("product") or {}
    except Exception:
        return {}


def extract_ga4_product(html_text):
    match = re.search(r"window\.ga4_product_item\s*=\s*(\{.*?\});", html_text or "", re.S)
    if not match:
        return {}
    try:
        return json.loads(match.group(1))
    except Exception:
        return {}


def title_from_soup(soup, fallback=""):
    node = soup.select_one("h1.title")
    if not node:
        return clean_text(fallback)
    brand = node.select_one(".pdp-NameToUrl")
    if brand:
        brand_text = clean_text(brand)
        text = clean_text(node)
        if brand_text and text.startswith(brand_text):
            return clean_text(text)
    return clean_text(node)


def color_from_specs(soup):
    for row in soup.select("#panel-specs tr, .product-informations .label"):
        cells = [clean_text(part) for part in row.find_all(["td", "span"], recursive=False)]
        cells = [cell for cell in cells if cell]
        if len(cells) >= 2 and cells[0].casefold().rstrip(":") == "renk":
            return cells[1]
    return ""


def extract_variant_urls(soup, current_url):
    variants = []
    seen = set()
    for a in soup.select('.swiper-slide a[href*="/urun/"], a[data-toggle="tooltip"][href*="/urun/"]'):
        href = normalize_url(a.get("href"), current_url)
        parsed = urlparse(href)
        if (
            not href
            or parsed.netloc not in {"www.karaca.com", "karaca.com"}
            or is_skipped_url(href)
            or not parsed.path.startswith(PRODUCT_URL_MARKER)
        ):
            continue
        label = clean_text(a.get("title") or a.get("data-original-title") or "")
        if not label:
            img = a.select_one("img")
            label = clean_text(img.get("alt") if img else "")
        key = href
        if key in seen:
            continue
        seen.add(key)
        variants.append({"url": href, "color": label})
    if current_url and normalize_url(current_url) not in seen:
        variants.insert(0, {"url": normalize_url(current_url), "color": ""})
    return variants


def parse_card_attrs(card):
    data = dict(card.attrs)
    for key in list(data):
        value = data[key]
        if not isinstance(value, str):
            data[key] = clean_text(value)
    href = normalize_url(card.get("href") or card.get("data-url") or "")
    title = clean_text(card.get("title") or card.get("data-productname") or card.get("data-name") or card)
    return {
        **data,
        "href": href,
        "title": title,
        "data-product-image-url": card.get("data-product-image-url") or "",
    }


def parse_html_products(html_text):
    soup = BeautifulSoup(html_text or "", "html.parser")
    products = []
    for card in soup.select(".productItem"):
        info = parse_card_attrs(card)
        url = info.get("href")
        title = info.get("title")
        if not url or PRODUCT_URL_MARKER not in urlparse(url).path or is_skipped_url(url, title):
            continue
        products.append(info)
    return uniq_keep_order(products, key_func=lambda item: item.get("href"))


def list_page_url(url, page_num):
    if page_num <= 1:
        return normalize_url(url, keep_query=True)
    parsed = urlparse(normalize_url(url, keep_query=True))
    query = dict(parse_qsl(parsed.query))
    query["json"] = "true"
    query["page"] = str(page_num)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", urlencode(query), ""))


def html_page_url(url, page_num):
    if page_num <= 1:
        return normalize_url(url, keep_query=True)
    parsed = urlparse(normalize_url(url, keep_query=True))
    query = dict(parse_qsl(parsed.query))
    query["page"] = str(page_num)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", urlencode(query), ""))


def parse_json_products(data):
    products = data.get("products") if isinstance(data, dict) else []
    result = []
    for product in products or []:
        url = normalize_url(product.get("href") or product.get("url") or "")
        title = clean_text(product.get("name") or product.get("title"))
        if not url or PRODUCT_URL_MARKER not in urlparse(url).path or is_skipped_url(url, title):
            continue
        result.append({
            **product,
            "href": url,
            "title": title,
            "data-productid": product.get("product_id") or product.get("id") or "",
            "data-productprice": product.get("unFormattedPrice") or product.get("price") or "",
            "data-productoriginalprice": product.get("unFormattedOldPrice") or product.get("old_price") or "",
            "data-product-image-url": product.get("thumb") or "",
        })
    return uniq_keep_order(result, key_func=lambda item: item.get("href"))


def payload_to_start_urls(payload_list):
    result = []
    seen = set()

    def add_item(url, c1, c2="", c3=""):
        full = normalize_url(url, HOME_URL, keep_query=True)
        text = " ".join([clean_text(c1), clean_text(c2), clean_text(c3)])
        if not full or not is_internal_url(full) or is_skipped_url(full, text):
            return
        c1 = clean_text(c1)
        c2 = clean_text(c2)
        c3 = clean_text(c3)
        key = (c1, c2, c3, full)
        if key in seen:
            return
        seen.add(key)
        result.append({
            "url": full,
            "categories_1": c1,
            "categories_2": c2,
            "categories_3": c3,
            "page_nums": 1,
        })

    def walk(node, c1="", c2=""):
        if isinstance(node, dict):
            for name, value in node.items():
                if not c1:
                    walk(value, name, "")
                elif isinstance(value, dict):
                    walk(value, c1, name)
                elif c2:
                    add_item(value, c1, c2, name)
                else:
                    add_item(value, c1, name)
        else:
            add_item(node, c1, c2)

    walk(payload_list)
    max_categories = _int_env("KARACA_MAX_CATEGORIES", 0)
    if max_categories:
        result = result[:max_categories]
    logger.info(f"Karaca PAYLOAD_LIST 目录生成完成: {len(result)} 个")
    return result


class CrawlerObject(Spider):
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = _int_env("KARACA_RECOLLECT", 1)
    is_proxy = 0
    collect_thread_number = max(1, _int_env("BATCH", 4))
    more_collect_thread_number = max(1, _int_env("BATCH", 4))
    filename = os.path.basename(__file__)
    name = "_" + filename.replace(".py", "")

    def __init__(self):
        self.max_pages = _int_env("KARACA_MAX_PAGES", 0)
        self.max_products = _int_env("KARACA_MAX_PRODUCTS", 0)
        self._emitted_products = 0
        self._emit_lock = threading.Lock()
        self._product_limit_reached = False
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
                self._product_limit_reached = True
                self.start_urls.clear()
                return False
            self._emitted_products += 1
            return True

    def get_list(self, params):
        page_num = 1
        while True:
            if self.max_pages and page_num > self.max_pages:
                break
            if page_num == 1:
                html_text, final_url = fetch_text(html_page_url(params["url"], page_num), headers=HTML_HEADERS, referer=HOME_URL, kind="list")
                products = parse_html_products(html_text)
            else:
                json_url = list_page_url(params["url"], page_num)
                data, final_url = fetch_json(json_url, headers=JSON_HEADERS, referer=params["url"], kind="list")
                products = parse_json_products(data)
            if not products:
                if page_num == 1:
                    logger.warning(f"Karaca 列表页没有商品: {params['url']}")
                break
            logger.info(f"Karaca 列表页 {params['url']} page={page_num} 提取商品 {len(products)} 个")
            for product in products:
                if not self._can_emit_product():
                    logger.info(f"Karaca 已达到测试商品上限 {self.max_products}，停止继续读取后续目录")
                    return
                item = deepcopy(params)
                item["url"] = product.get("href")
                item["list_url"] = final_url
                item["list_info"] = product
                yield item
            if page_num == 1:
                soup = BeautifulSoup(html_text or "", "html.parser")
                has_next = bool(soup.select_one('link[rel="next"], a[rel="next"], .pagination a.next'))
                if not has_next:
                    break
            elif len(products) < 40:
                break
            page_num += 1

    def get_content(self, params):
        try:
            html_text, _ = fetch_text(params["url"], headers=HTML_HEADERS, referer=params.get("list_url") or HOME_URL, kind="detail")
            soup = BeautifulSoup(html_text or "", "html.parser")
            variants = extract_variant_urls(soup, params["url"])
            if not variants:
                variants = [{"url": params["url"], "color": ""}]
            handle = self.counter()
            multi_variant = len(variants) > 1
            items = []
            for index, variant in enumerate(variants, start=1):
                item = deepcopy(params)
                item["url"] = variant["url"]
                item["handle"] = f"{handle}_{index}" if multi_variant else handle
                color = clean_text(variant.get("color"))
                if color:
                    item["option1_name"] = "Renk"
                    item["option1_value"] = color
                item["variant_index"] = index
                items.append(item)
            return items
        except Exception:
            logger.error(f"Karaca get_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            return []

    def get_more_content(self, params):
        html_text, _ = fetch_text(params["url"], headers=HTML_HEADERS, referer=params.get("list_url") or HOME_URL, kind="detail")
        soup = BeautifulSoup(html_text or "", "html.parser")
        detail_data = extract_datalayer_product(html_text)
        ga4_data = extract_ga4_product(html_text)
        list_info = params.get("list_info") if isinstance(params.get("list_info"), dict) else {}

        title = title_from_soup(soup, detail_data.get("product_name") or ga4_data.get("item_name") or list_info.get("title"))
        price = product_price(detail_data, ga4_data, list_info)
        images = extract_images(soup, list_info=list_info, detail_data=detail_data or ga4_data)
        if not title or price is None or not images:
            logger.warning(f"Karaca 核心字段缺失: title={bool(title)} price={price} images={len(images)} url={params.get('url')}")
            return None

        item = deepcopy(params)
        item["title"] = title
        item["subtitle"] = ""
        item["price"] = float(price)
        item["body"] = extract_body(soup)
        item["image_src"] = images
        item["more_info"] = ""
        color = color_from_specs(soup)
        if color:
            item["option1_name"] = "Renk"
            item["option1_value"] = color
        item.setdefault("option1_name", "")
        item.setdefault("option1_value", "")
        item.setdefault("option2_name", "")
        item.setdefault("option2_value", "")
        item.setdefault("option3_name", "")
        item.setdefault("option3_value", "")
        item["size_price"] = ""
        item["product_id"] = clean_text(detail_data.get("productid") or ga4_data.get("item_id") or list_info.get("data-productid"))
        item["product_mpn"] = clean_text(detail_data.get("productmpn") or ga4_data.get("item_mpn") or list_info.get("data-productmpn"))
        return item


if __name__ == "__main__":
    CrawlerObject().start()
