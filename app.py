"""
AETHER NEXUS — Canlı portföy takip uygulaması (TEK DOSYA SÜRÜMÜ)

Bu dosya build_single_file.py tarafından üretilmiştir; elle düzenlemeyin.
Kaynak: portfolio/classification.py, prices.py, storage.py, analytics.py, app.py

Çalıştırma:  streamlit run aether_nexus.py
"""

from __future__ import annotations


# --- Sürüm damgası -----------------------------------------------------------
# Derleyici üretir. Amacı tek bir soruyu kesin cevaplamak: "yüklediğim dosya
# gerçekten çalışıyor mu?" Uygulama bunu başlıkta ve Ayarlar'da gösterir;
# yüklediğiniz dosyanınkiyle aynı değilse yayındaki sürüm eski demektir.
BUILD_ID = "adbcc5ccb2"
BUILD_TIME = "2026-09-24 16:54"


# ==========================================================================
# KAYNAK: portfolio/classification.py
# ==========================================================================


import re
from typing import Any

# --------------------------------------------------------------------------
# FİYAT KAYNAKLARI (teknik)
# --------------------------------------------------------------------------
SRC_YAHOO = "yahoo"          # yfinance ile çekilir
SRC_TEFAS = "tefas"          # TEFAS BindHistoryInfo API
SRC_GOLD = "gold"            # XAU/USD üzerinden türetilir
SRC_SILVER = "silver"        # XAG/USD üzerinden türetilir
SRC_CASH = "cash"            # nakit, fiyatı her zaman 1.0
SRC_MANUAL = "manual"        # elle girilen fiyat (borsada işlem görmeyen varlık)

VALID_SOURCES = {SRC_YAHOO, SRC_TEFAS, SRC_GOLD, SRC_SILVER, SRC_CASH, SRC_MANUAL}

# --------------------------------------------------------------------------
# SINIFLANDIRMA HİYERARŞİSİ
# Sankey / Sunburst bu sırayla çizilir. Sıralamayı değiştirebilir,
# seviye ekleyip çıkarabilirsiniz (ör. "hesap" ekleyip broker kırılımı almak).
# --------------------------------------------------------------------------
HIERARCHY = ["ana_sinif", "alt_sinif", "sektor", "display"]

HIERARCHY_LABELS = {
    "ana_sinif": "Ana Sınıf",
    "alt_sinif": "Alt Sınıf",
    "sektor": "Sektör",
    "display": "Varlık",
    "hesap": "Hesap / Kurum",
    "currency": "Para Birimi",
}

# Ana sınıf listesi — arayüzdeki açılır menüleri besler.
# Bluecoins hesap ağacınızdan türetildi (01_BIST … 08_CRYPTO + gizli hesaplar).
ANA_SINIFLAR = [
    "Hisse Senedi",     # 01_BIST, 02_US Stocks
    "Fon",              # 03_Fon
    "Emtia",            # 04A_Gold, 04B_SILVER
    "Kripto",           # 08_CRYPTO
    "Sabit Getirili",   # 05_Eurobond
    "Nakit",            # 06_$/€ Cash, 07_₺ Cash, Bank
    "Gayrimenkul",      # Properties
    "Alacaklar",        # Receivables (OYAK, BES)
    "Yükümlülük",       # Credit Card, Mortgages, Virtual Accounts
    "Diğer",            # Other Assets (taşıt, karavan)
]

# Net değer hesabında değeri NEGATİF sayılacak sınıflar.
BORC_SINIFLARI = {"Yükümlülük"}

# Altın/gümüş birim çarpanları (1 birim kaç gram saf metale denk).
# Fiyatlar gram saf metal üzerinden hesaplanır, işçilik/makas payı dahil değildir.
METAL_UNITS = {
    "GRAM": 1.0,
    "ONS": 31.1034768,
    "CEYREK": 1.6042,      # 1.75 g / 22 ayar (0.916) ≈ 1.6042 g saf
    "YARIM": 3.2084,
    "TAM": 6.4168,
    "CUMHURIYET": 6.6165,
    "ATA": 6.6165,
    "RESAT": 7.0160,
    "BILEZIK22": 0.916,    # 1 gram 22 ayar bilezik
    "BILEZIK14": 0.585,
}

# --------------------------------------------------------------------------
# BİLİNEN VARLIKLAR
# Buraya eklediğiniz her sembol, ekleme ekranında otomatik dolar.
# --------------------------------------------------------------------------
def _s(sektor: str, **kw: Any) -> dict[str, Any]:
    return {"sektor": sektor, **kw}


SMART_DATABASE: dict[str, dict[str, Any]] = {}


def _reg(codes: str, *, source: str, currency: str, ana: str, alt: str,
         sektor: str, suffix: str = "") -> None:
    """Toplu kayıt yardımcısı."""
    for code in codes.split():
        SMART_DATABASE[code] = {
            "source": source,
            "currency": currency,
            "ana_sinif": ana,
            "alt_sinif": alt,
            "sektor": sektor,
            "yahoo_suffix": suffix,
        }


# --- BIST hisseleri ---------------------------------------------------------
_reg("THYAO PGSUS TAVHL", source=SRC_YAHOO, currency="TRY",
     ana="Hisse Senedi", alt="BIST", sektor="Havacılık", suffix=".IS")
_reg("TUPRS AKSEN ZOREN ENJSA AYDEM", source=SRC_YAHOO, currency="TRY",
     ana="Hisse Senedi", alt="BIST", sektor="Enerji", suffix=".IS")
_reg("EREGL KRDMD ISDMR CEMTS", source=SRC_YAHOO, currency="TRY",
     ana="Hisse Senedi", alt="BIST", sektor="Demir-Çelik", suffix=".IS")
_reg("ASELS OTKAR KATMR", source=SRC_YAHOO, currency="TRY",
     ana="Hisse Senedi", alt="BIST", sektor="Savunma Sanayi", suffix=".IS")
_reg("ALKA KARTN SASA PETKM GUBRF HEKTS", source=SRC_YAHOO, currency="TRY",
     ana="Hisse Senedi", alt="BIST", sektor="Kimya / Kağıt", suffix=".IS")
_reg("GARAN AKBNK ISCTR YKBNK VAKBN HALKB TSKB", source=SRC_YAHOO, currency="TRY",
     ana="Hisse Senedi", alt="BIST", sektor="Bankacılık", suffix=".IS")
_reg("BIMAS MGROS SOKM ULKER CCOLA AEFES", source=SRC_YAHOO, currency="TRY",
     ana="Hisse Senedi", alt="BIST", sektor="Perakende / Gıda", suffix=".IS")
_reg("TCELL TTKOM LOGO ARDYZ NETAS", source=SRC_YAHOO, currency="TRY",
     ana="Hisse Senedi", alt="BIST", sektor="Teknoloji / Telekom", suffix=".IS")
_reg("FROTO TOASO TTRAK DOAS", source=SRC_YAHOO, currency="TRY",
     ana="Hisse Senedi", alt="BIST", sektor="Otomotiv", suffix=".IS")
_reg("KCHOL SAHOL SISE AGHOL", source=SRC_YAHOO, currency="TRY",
     ana="Hisse Senedi", alt="BIST", sektor="Holding", suffix=".IS")
_reg("ASTOR ENKAI TKFEN", source=SRC_YAHOO, currency="TRY",
     ana="Hisse Senedi", alt="BIST", sektor="Sanayi / Taahhüt", suffix=".IS")

# --- ABD hisseleri ----------------------------------------------------------
_reg("NVDA AMD AVGO INTC TSM MU ASML", source=SRC_YAHOO, currency="USD",
     ana="Hisse Senedi", alt="ABD", sektor="Yarı İletken")
_reg("AAPL MSFT GOOGL META AMZN CRM ADBE ORCL PLTR", source=SRC_YAHOO, currency="USD",
     ana="Hisse Senedi", alt="ABD", sektor="Teknoloji")
_reg("TSLA RIVN F GM", source=SRC_YAHOO, currency="USD",
     ana="Hisse Senedi", alt="ABD", sektor="Otomotiv / EV")
_reg("JPM BAC GS V MA", source=SRC_YAHOO, currency="USD",
     ana="Hisse Senedi", alt="ABD", sektor="Finans")
_reg("LLY UNH JNJ PFE NVO", source=SRC_YAHOO, currency="USD",
     ana="Hisse Senedi", alt="ABD", sektor="Sağlık")
_reg("XOM CVX OXY", source=SRC_YAHOO, currency="USD",
     ana="Hisse Senedi", alt="ABD", sektor="Enerji")

# --- ETF'ler ----------------------------------------------------------------
_reg("QQQ QQQM", source=SRC_YAHOO, currency="USD",
     ana="Fon", alt="ABD ETF", sektor="Teknoloji Endeksi")
_reg("SPY VOO IVV VTI", source=SRC_YAHOO, currency="USD",
     ana="Fon", alt="ABD ETF", sektor="Geniş Endeks")
_reg("XLU", source=SRC_YAHOO, currency="USD",
     ana="Fon", alt="ABD ETF", sektor="Altyapı / Kamu Hizmetleri")
_reg("XLE XLF XLV XLK SMH SOXX", source=SRC_YAHOO, currency="USD",
     ana="Fon", alt="ABD ETF", sektor="Sektör ETF")
_reg("GLD IAU SLV", source=SRC_YAHOO, currency="USD",
     ana="Fon", alt="ABD ETF", sektor="Kıymetli Maden ETF")
_reg("TLT IEF SHY", source=SRC_YAHOO, currency="USD",
     ana="Sabit Getirili", alt="ABD ETF", sektor="Tahvil ETF")

# --- Kripto -----------------------------------------------------------------
_reg("BTC ETH", source=SRC_YAHOO, currency="USD",
     ana="Kripto", alt="Majör", sektor="L1 Zincir", suffix="-USD")
_reg("SOL AVAX ADA DOT ATOM NEAR SUI APT TON", source=SRC_YAHOO, currency="USD",
     ana="Kripto", alt="Altcoin", sektor="L1 Zincir", suffix="-USD")
_reg("ARB OP MATIC", source=SRC_YAHOO, currency="USD",
     ana="Kripto", alt="Altcoin", sektor="L2 / Ölçekleme", suffix="-USD")
_reg("LINK UNI AAVE", source=SRC_YAHOO, currency="USD",
     ana="Kripto", alt="Altcoin", sektor="DeFi / Oracle", suffix="-USD")
_reg("USDT USDC", source=SRC_YAHOO, currency="USD",
     ana="Nakit", alt="Stablecoin", sektor="Dolar Stablecoin", suffix="-USD")

# --- Emtia (türetilmiş) -----------------------------------------------------
SMART_DATABASE["ALTIN"] = {
    "source": SRC_GOLD, "currency": "TRY", "ana_sinif": "Emtia",
    "alt_sinif": "Kıymetli Maden", "sektor": "Altın", "unit": "GRAM",
}
SMART_DATABASE["GUMUS"] = {
    "source": SRC_SILVER, "currency": "TRY", "ana_sinif": "Emtia",
    "alt_sinif": "Kıymetli Maden", "sektor": "Gümüş", "unit": "GRAM",
}
for _u in ("CEYREK", "YARIM", "TAM", "CUMHURIYET", "ATA", "RESAT",
           "BILEZIK22", "BILEZIK14", "ONS"):
    SMART_DATABASE[f"ALTIN-{_u}"] = {
        "source": SRC_GOLD, "currency": "TRY", "ana_sinif": "Emtia",
        "alt_sinif": "Kıymetli Maden", "sektor": "Altın", "unit": _u,
    }
SMART_DATABASE["GUMUS-ONS"] = {
    "source": SRC_SILVER, "currency": "USD", "ana_sinif": "Emtia",
    "alt_sinif": "Kıymetli Maden", "sektor": "Gümüş", "unit": "ONS",
}

# --- Nakit ------------------------------------------------------------------
for _cur, _ad in (("TRY", "Türk Lirası"), ("USD", "Dolar"), ("EUR", "Euro")):
    SMART_DATABASE[f"NAKIT-{_cur}"] = {
        "source": SRC_CASH, "currency": _cur, "ana_sinif": "Nakit",
        "alt_sinif": "Mevduat / Vadesiz", "sektor": _ad,
    }

# TEFAS fon kodları 3 karakterlidir; bilinen birkaçını isimlendiriyoruz.
TEFAS_KNOWN = {
    "MAC": "Hisse Fonu", "TI1": "Hisse Fonu", "TTE": "Hisse Fonu",
    "AFA": "Hisse Fonu", "IPJ": "Serbest Fon", "GBV": "Kıymetli Maden",
    "AFT": "Para Piyasası", "TCD": "Borçlanma Araçları",
}

# --------------------------------------------------------------------------
# BIST hisse kodları — çevrimdışı sınıflandırma için.
# Bu listede olmayan 4-5 harfli kod ABD hissesi varsayılır; "Yeni Varlık"
# ekranındaki canlı yoklama (prices.probe_symbol) bunu zaten düzeltir.
# --------------------------------------------------------------------------
BIST_TICKERS: set[str] = set("""
A1CAP ACSEL ADEL ADESE ADGYO AEFES AFYON AGHOL AGESA AGROT AGYO AHGAZ AKBNK
AKCNS AKENR AKFGY AKFYE AKGRT AKMGY AKSA AKSEN AKSGY AKSUE AKYHO ALARK ALBRK
ALCAR ALCTL ALFAS ALGYO ALKA ALKIM ALMAD ALTIN ALVES ANELE ANGEN ANHYT ANSGR
ARASE ARCLK ARDYZ ARENA ARSAN ARTMS ARZUM ASELS ASGYO ASTOR ASUZU ATAGY ATAKP
ATATP ATEKS ATLAS ATSYH AVGYO AVHOL AVOD AVPGY AVTUR AYCES AYDEM AYEN AYES
AYGAZ AZTEK BAGFS BAHKM BAKAB BALAT BANVT BARMA BASCM BASGZ BAYRK BEGYO BERA
BESLR BEYAZ BFREN BIENY BIGCH BIMAS BINHO BIOEN BIZIM BJKAS BLCYT BMSCH BMSTL
BNTAS BOBET BORLS BORSK BOSSA BRISA BRKO BRKSN BRKVY BRLSM BRMEN BRSAN BRYAT
BSOKE BTCIM BUCIM BURCE BURVA BVSAN CANTE CASA CATES CCOLA CELHA CEMAS CEMTS
CEOEM CIMSA CLEBI CMBTN CMENT CONSE COSMO CRDFA CRFSA CUSAN CVKMD CWENE DAGHL
DAGI DAPGM DARDL DENGE DERHL DERIM DESA DESPC DEVA DGATE DGGYO DGNMO DIRIT
DITAS DMSAS DNISI DOAS DOBUR DOCO DOFER DOGUB DOHOL DOKTA DURDO DYOBY DZGYO
ECILC ECZYT EDATA EDIP EFORC EGEEN EGEPO EGGUB EGPRO EGSER EKGYO EKIZ EKOS
EKSUN ELITE EMKEL EMNIS ENERY ENJSA ENKAI ENSRI EPLAS ERBOS ERCB EREGL ERSU
ESCAR ESCOM ESEN ETILR ETYAT EUHOL EUKYO EUPWR EUREN EUYO EYGYO FADE FENER
FLAP FMIZP FONET FORMT FORTE FRIGO FROTO FZLGY GARAN GARFA GEDIK GEDZA GENIL
GENTS GEREL GESAN GIPTA GLBMD GLCVY GLRYH GLYHO GMTAS GOKNR GOLTS GOODY GOZDE
GRNYO GRSEL GRTRK GSDDE GSDHO GSRAY GUBRF GWIND GZNMI HALKB HATEK HATSN HDFGS
HEDEF HEKTS HKTM HLGYO HTTBT HUBVC HUNER HURGZ ICBCT ICUGS IDGYO IEYHO IHAAS
IHEVA IHGZT IHLAS IHLGM IHYAY IMASM INDES INFO INGRM INTEM INVEO INVES IPEKE
ISATR ISBIR ISBTR ISCTR ISDMR ISFIN ISGSY ISGYO ISKPL ISMEN ISSEN ISYAT IZENR
IZFAS IZINV IZMDC JANTS KAPLM KAREL KARSN KARTN KARYE KATMR KAYSE KBORU KCAER
KCHOL KENT KERVT KFEIN KGYO KIMMR KLGYO KLKIM KLMSN KLNMA KLRHO KLSER KLSYN
KMPUR KNFRT KOCMT KONKA KONTR KONYA KOPOL KORDS KOTON KOZAA KOZAL KRDMA KRDMB
KRDMD KRGYO KRONT KRPLS KRSTL KRTEK KRVGD KSTUR KTLEV KTSKR KUTPO KUVVA KUYAS
KZBGY KZGYO LIDER LIDFA LILAK LINK LKMNH LMKDC LOGO LRSHO LUKSK MAALT MACKO
MAGEN MAKIM MAKTK MANAS MARBL MARKA MARTI MAVI MEDTR MEGAP MEGMT MEKAG MEPET
MERCN MERIT MERKO METRO METUR MGROS MHRGY MIATK MIPAZ MMCAS MNDRS MNDTR MOBTL
MOGAN MPARK MRGYO MRSHL MSGYO MTRKS MTRYO MZHLD NATEN NETAS NIBAS NTGAZ NTHOL
NUGYO NUHCM OBAMS OBASE ODAS ODINE OFSYM ONCSM ORCAY ORGE ORMA OSMEN OSTIM
OTKAR OTTO OYAKC OYAYO OYLUM OYYAT OZATD OZGYO OZKGY OZRDN OZSUB OZYSR PAGYO
PAMEL PAPIL PARSN PASEU PATEK PCILT PEHOL PEKGY PENGD PENTA PETKM PETUN PGSUS
PINSU PKART PKENT PLTUR PNLSN PNSUT POLHO POLTK PRDGS PRKAB PRKME PRZMA PSDTC
PSGYO QUAGR RALYH RAYSG REEDR RGYAS RNPOL RODRG ROYAL RTALB RUBNS RYGYO RYSAS
SAFKR SAHOL SAMAT SANEL SANFM SANKO SARKY SASA SAYAS SDTTR SEGMN SEGYO SEKFK
SEKUR SELEC SELGD SELVA SEYKM SILVR SISE SKBNK SKTAS SKYLP SKYMD SMART SMRTG
SNGYO SNICA SNKRN SNPAM SODSN SOKE SOKM SONME SRVGY SUMAS SUNTK SURGY SUWEN
TABGD TARKM TATEN TATGD TAVHL TBORG TCELL TDGYO TEKTU TERA TETMT TEZOL TGSAS
THYAO TKFEN TKNSA TLMAN TMPOL TMSN TNZTP TOASO TRCAS TRGYO TRILC TSGYO TSKB
TSPOR TTKOM TTRAK TUCLK TUKAS TUPRS TUREX TURGG TURSG UFUK ULAS ULKER ULUFA
ULUSE ULUUN UMPAS UNLU USAK VAKBN VAKFN VAKKO VANGD VBTYZ VERTU VERUS VESBE
VESTL VKFYO VKGYO VKING VRGYO YAPRK YATAS YAYLA YBTAS YEOTK YESIL YGGYO YGYO
YKBNK YKSLN YONGA YUNSA YYAPI YYLGD ZEDUR ZOREN ZRGYO
""".split())

# Yaygın kripto sembolleri (Yahoo'da "-USD" ekiyle işlem görür)
CRYPTO_TICKERS: set[str] = set("""
BTC ETH USDT USDC BNB XRP SOL ADA DOGE TRX AVAX SHIB DOT LINK BCH NEAR MATIC
LTC ICP UNI APT XLM ETC ATOM XMR FIL HBAR ARB VET OP INJ IMX GRT AAVE MKR
RUNE ALGO SAND MANA AXS FTM THETA EGLD FLOW CHZ SUI SEI TIA PEPE WIF BONK
TON KAS RNDR LDO CRV SNX COMP ENS DYDX GMX STX ZIL ONE QNT CAKE
""".split())

BIST_SUFFIX_RE = re.compile(r"\.IS$", re.IGNORECASE)
CRYPTO_SUFFIX_RE = re.compile(r"-USD$", re.IGNORECASE)
TEFAS_CODE_RE = re.compile(r"^[A-Z]{3}$")


def auto_fill_asset(raw: str) -> dict[str, Any]:
    """
    Kullanıcı sadece sembol girdiğinde kaynak, para birimi ve sınıflandırmayı
    doldurur. Bilinmeyen semboller için makul bir tahmin döner — kullanıcı
    arayüzde her alanı değiştirebilir.
    """
    text = (raw or "").strip().upper()
    if not text:
        raise ValueError("Sembol boş olamaz.")

    base = BIST_SUFFIX_RE.sub("", CRYPTO_SUFFIX_RE.sub("", text))

    # 1) Doğrudan veritabanı eşleşmesi
    entry = SMART_DATABASE.get(text) or SMART_DATABASE.get(base)
    if entry:
        key = text if text in SMART_DATABASE else base
        data = dict(entry)
        suffix = data.pop("yahoo_suffix", "")
        data["display"] = key
        data["symbol"] = f"{base}{suffix}" if data["source"] == SRC_YAHOO else key
        data.setdefault("unit", None)
        data["guessed"] = False
        return _finalize(data)

    # 2) Sembolün şeklinden / bilinen listelerden tahmin
    guessed = True
    if BIST_SUFFIX_RE.search(text):
        data = {"symbol": text, "display": base, "source": SRC_YAHOO, "currency": "TRY",
                "ana_sinif": "Hisse Senedi", "alt_sinif": "BIST", "sektor": "Diğer BIST"}
        guessed = base not in BIST_TICKERS
    elif CRYPTO_SUFFIX_RE.search(text):
        data = {"symbol": text, "display": base, "source": SRC_YAHOO, "currency": "USD",
                "ana_sinif": "Kripto", "alt_sinif": "Altcoin", "sektor": "Diğer Kripto"}
        guessed = base not in CRYPTO_TICKERS
    elif base in BIST_TICKERS:
        data = {"symbol": f"{base}.IS", "display": base, "source": SRC_YAHOO,
                "currency": "TRY", "ana_sinif": "Hisse Senedi", "alt_sinif": "BIST",
                "sektor": "Diğer BIST"}
        guessed = False
    elif base in CRYPTO_TICKERS:
        data = {"symbol": f"{base}-USD", "display": base, "source": SRC_YAHOO,
                "currency": "USD", "ana_sinif": "Kripto", "alt_sinif": "Altcoin",
                "sektor": "Diğer Kripto"}
        guessed = False
    elif TEFAS_CODE_RE.match(base):
        data = {"symbol": base, "display": base, "source": SRC_TEFAS, "currency": "TRY",
                "ana_sinif": "Fon", "alt_sinif": "TEFAS",
                "sektor": TEFAS_KNOWN.get(base, "Yatırım Fonu")}
        guessed = base not in TEFAS_KNOWN
    elif "=" in text or "^" in text:  # GC=F, ^GSPC gibi Yahoo özel sembolleri
        data = {"symbol": text, "display": text, "source": SRC_YAHOO, "currency": "USD",
                "ana_sinif": "Diğer", "alt_sinif": "Endeks / Vadeli", "sektor": "Diğer"}
    else:
        data = {"symbol": base, "display": base, "source": SRC_YAHOO, "currency": "USD",
                "ana_sinif": "Hisse Senedi", "alt_sinif": "ABD", "sektor": "Diğer ABD"}

    data["unit"] = None
    data["guessed"] = guessed
    return _finalize(data)


PLAIN_SYMBOL_RE = re.compile(r"^[A-Za-z0-9.\-^=]+$")


def resolve_symbol(raw: str, source: str) -> str:
    """
    Kullanıcı 'ASELS' yazdığında Yahoo'nun beklediği 'ASELS.IS'e, 'SOL' yazdığında
    'SOL-USD'ye çevirir. Sadece TANINAN sembollerde müdahale eder; tanınmayan
    kodlar ve içe aktarımdan gelen 'BC:01_BIST:MIDAS' gibi kimlikler olduğu gibi
    kalır.
    """
    text = (raw or "").strip()
    if not text or source != SRC_YAHOO or not PLAIN_SYMBOL_RE.match(text):
        return text
    try:
        guess = auto_fill_asset(text)
    except ValueError:
        return text
    return text if guess["guessed"] else guess["symbol"]


def classify_symbol(symbol: str, source: str) -> dict[str, str]:
    """
    Bir sembol + kaynak ikilisi için varlık sınıfını döndürür.
    Tabloya elle satır eklendiğinde sınıf alanlarını otomatik doldurmak için
    kullanılır; kullanıcı isterse üzerine yazabilir.
    """
    try:
        guess = auto_fill_asset(symbol)
    except ValueError:
        return {"ana_sinif": "Diğer", "alt_sinif": "Diğer", "sektor": "Diğer"}

    if source and source != guess["source"]:
        # Kullanıcı kaynağı elle değiştirmişse sınıfı kaynağa göre belirle
        by_source = {
            SRC_TEFAS: ("Fon", "TEFAS", "Yatırım Fonu"),
            SRC_GOLD: ("Emtia", "Altın", "Altın"),
            SRC_SILVER: ("Emtia", "Gümüş", "Gümüş"),
            SRC_CASH: ("Nakit", "Mevduat / Vadesiz", "Nakit"),
        }
        if source in by_source:
            ana, alt, sek = by_source[source]
            return {"ana_sinif": ana, "alt_sinif": alt, "sektor": sek}

    return {k: guess[k] for k in ("ana_sinif", "alt_sinif", "sektor")}


# --------------------------------------------------------------------------
# DEĞERLEME MODU
#   "qty"   -> değer = adet × canlı birim fiyat        (klasik pozisyon)
#   "value" -> değer = elle girilen toplam tutar       (kova / Bluecoins tarzı)
# Bir kova için fiyat kaynağı yine tanımlı olabilir; adet girildiği anda
# moda "qty" geçilir ve fiyat canlı hesaplanmaya başlar.
# --------------------------------------------------------------------------
VAL_QTY = "qty"
VAL_VALUE = "value"


def _finalize(data: dict[str, Any]) -> dict[str, Any]:
    data.setdefault("qty", 0.0)
    data.setdefault("avg_cost", 0.0)
    data.setdefault("cost_currency", data.get("currency", "TRY"))
    data.setdefault("hesap", "")
    data.setdefault("notlar", "")
    data.setdefault("manual_price", None)
    data.setdefault("valuation", VAL_QTY)
    return data


def normalize_asset(item: dict[str, Any]) -> dict[str, Any]:
    """
    Eski formatta ("type"/"type_tr") kaydedilmiş varlıkları yeni şemaya taşır.
    Böylece elinizdeki my_assets.json'u silmenize gerek kalmaz.
    """
    item = dict(item)

    if "source" not in item:
        legacy = str(item.get("type", "")).upper()
        legacy_map = {
            "TR_STOCK": (SRC_YAHOO, "Hisse Senedi", "BIST"),
            "US_STOCK": (SRC_YAHOO, "Hisse Senedi", "ABD"),
            "ETF": (SRC_YAHOO, "Fon", "ABD ETF"),
            "CRYPTO": (SRC_YAHOO, "Kripto", "Altcoin"),
            "TEFAS": (SRC_TEFAS, "Fon", "TEFAS"),
            "GOLD": (SRC_GOLD, "Emtia", "Kıymetli Maden"),
            "SILVER": (SRC_SILVER, "Emtia", "Kıymetli Maden"),
            "CASH": (SRC_CASH, "Nakit", "Mevduat / Vadesiz"),
        }
        src, ana, alt = legacy_map.get(legacy, (SRC_YAHOO, "Diğer", "Diğer"))
        item["source"] = src
        item.setdefault("ana_sinif", ana)
        item.setdefault("alt_sinif", item.get("type_tr") or alt)

    item.pop("type", None)
    item.pop("type_tr", None)

    sym = str(item.get("symbol", "")).strip()
    item["symbol"] = sym
    item.setdefault("display", BIST_SUFFIX_RE.sub("", CRYPTO_SUFFIX_RE.sub("", sym.upper())))
    item.setdefault("sektor", "Diğer")
    item.setdefault("currency", "TRY")
    item.setdefault("unit", None)
    item["qty"] = float(item.get("qty") or 0.0)
    item["avg_cost"] = float(item.get("avg_cost") or 0.0)
    # Maliyetin para birimi fiyatınkinden FARKLI olabilir: BIST hissesinin
    # fiyatı TRY'dir ama maliyeti dolar bazlı bir rapordan gelmiş olabilir.
    # Ayrı tutulmazsa maliyeti içe aktarırken dondurulmuş bir kurla TRY'ye
    # çevirmek zorunda kalırız; ayrı tutulunca uygulama her açılışta güncel
    # kurla çevirir.
    item["cost_currency"] = (str(item.get("cost_currency") or "").upper()
                             or item.get("currency", "TRY"))
    item.setdefault("hesap", "")
    item.setdefault("notlar", "")
    item.setdefault("manual_price", None)
    if item.get("source") not in VALID_SOURCES:
        item["source"] = SRC_YAHOO

    if item.get("valuation") not in (VAL_QTY, VAL_VALUE):
        # Adet yoksa ama elle girilmiş bir tutar varsa: kova
        item["valuation"] = (
            VAL_VALUE
            if (item["qty"] <= 0 and item.get("manual_price") is not None)
            or item["source"] == SRC_MANUAL
            else VAL_QTY
        )
    return item


def asset_key(item: dict[str, Any]) -> str:
    """Aynı varlığın farklı hesaplardaki pozisyonları ayrı satır olarak tutulur."""
    return f"{item.get('symbol', '').upper()}|{item.get('hesap', '')}"

# ==========================================================================
# KAYNAK: portfolio/prices.py
# ==========================================================================


import datetime as dt
import logging
import pathlib
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any, Iterable

import requests


log = logging.getLogger(__name__)

TROY_OUNCE_G = 31.1034768

YAHOO_FX = {"USDTRY": "TRY=X", "EURTRY": "EURTRY=X", "EURUSD": "EURUSD=X",
            # Hong Kong (SEHK) hisseleri HKD fiyatlanır. Doğrudan HKDTRY
            # gelmezse analytics.to_try_rate USDHKD üzerinden türetir.
            "HKDTRY": "HKDTRY=X", "USDHKD": "HKD=X"}
YAHOO_GOLD = "GC=F"      # Altın vadeli, USD/ons
YAHOO_SILVER = "SI=F"    # Gümüş vadeli, USD/ons

# TEFAS 2026'da altyapısını yeniledi: eski /api/DB/BindHistoryInfo uç noktası
# artık 404 veriyor ve HTML kazımaya dayalı bütün çözümler de kırıldı.
# Yeni uç nokta JSON gövde alıyor, tarihleri YYYYAAGG yazıyor ve alan adları
# camelCase (fonKodu / tarih / fiyat). Eskisini yine de son çare olarak
# deniyoruz: TEFAS geri alırsa ya da bir vekil sunucu hâlâ sunuyorsa çalışsın.
TEFAS_URL_YENI = "https://www.tefas.gov.tr/api/funds/fonGnlBlgSiraliGetir"
TEFAS_REFERER_YENI = "https://www.tefas.gov.tr/tr/fon-verileri"

TEFAS_URL = "https://www.tefas.gov.tr/api/DB/BindHistoryInfo"   # eski (404)
TEFAS_REFERER = "https://www.tefas.gov.tr/TarihselVeriler.aspx"

# TEFAS istek sıklığını sınırlıyor (429 Too Many Requests). Eskiden bir fon
# tipi 429 döndürdüğünde kod pes etmiyor, EKSİK KALAN HER KOD için ayrı ayrı
# (3 fon tipi x ~20 kod = ~60 istek) tekil denemeye geçiyordu — bu da zaten
# kızgın olan TEFAS'ı daha da kızdırıp yasağı uzatıyordu. Artık: bir 429
# görülür görülmez BÜTÜN denemeler o çalıştırma için durur ve birkaç dakikalık
# bir "sus" süresi başlar; bu süre boyunca hiç istek atılmaz.
#
# Sus süresi DİSKE yazılır, salt Python değişkenine değil. Sebebi: tek dosya
# sürümünde Streamlit her etkileşimde BÜTÜN betiği (bu modülün kodu dahil)
# baştan çalıştırıyor, bu da modül seviyesindeki sıradan bir değişkeni her
# seferinde sıfırlardı ve "sus" hiç kalıcı olmazdı. Geçici dosya süreç/betik
# çalıştırmaları arasında hayatta kalıyor.
_TEFAS_SUS_SANIYE = 360.0
_TEFAS_SUS_DOSYA = pathlib.Path(tempfile.gettempdir()) / "aether_tefas_sus.txt"


def _tefas_sus_oku() -> float:
    try:
        return float(_TEFAS_SUS_DOSYA.read_text().strip())
    except Exception:
        return 0.0


def _tefas_sus_yaz(zaman: float) -> None:
    try:
        _TEFAS_SUS_DOSYA.write_text(str(zaman))
    except Exception as exc:
        log.info("TEFAS sus dosyası yazılamadı (önemsiz): %s", exc)


def _tefas_429_mi(exc: Exception) -> bool:
    resp = getattr(exc, "response", None)
    return getattr(resp, "status_code", None) == 429


@dataclass
class Quote:
    symbol: str
    price: float | None = None
    currency: str = "TRY"
    source: str = ""
    ok: bool = False
    error: str = ""
    asof: str = ""


@dataclass
class MarketSnapshot:
    fx: dict[str, float] = field(default_factory=dict)
    gold_usd_oz: float | None = None
    silver_usd_oz: float | None = None
    quotes: dict[str, Quote] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    fetched_at: str = ""
    # sembol -> para birimi -> dönem -> yüzde değişim
    # Isı haritası bunu kullanır. Değişim, varlığın SEÇİLEN para birimindeki
    # değerine göre hesaplanır: TRY seçiliyse kur etkisi dahildir, USD
    # seçiliyse ABD hissesi kendi doğal hareketini gösterir.
    changes: dict[str, dict[str, dict[str, float]]] = field(default_factory=dict)
    # sembol -> [(tarih, bir birimin TL değeri)] — karşılaştırma grafiği
    # portföyün getiri serisini bundan üretir.
    series: dict[str, list] = field(default_factory=dict)
    # ölçüt adı -> [(tarih, TL değeri)]
    benchmarks: dict[str, list] = field(default_factory=dict)

    @property
    def usdtry(self) -> float | None:
        return self.fx.get("USDTRY")


# ---------------------------------------------------------------------------
# YAHOO FINANCE
# ---------------------------------------------------------------------------
def _close_series(df, ticker: str):
    """yf.download çıktısından bir sembolün kapanış SERİSİNİ çıkarır."""
    try:
        if df is None or len(df) == 0:
            return None
        if hasattr(df.columns, "levels") and df.columns.nlevels > 1:
            if "Close" in df.columns.get_level_values(0):
                series = (df["Close"][ticker]
                          if ticker in df["Close"].columns else None)
            elif ticker in df.columns.get_level_values(0):
                series = df[ticker]["Close"]
            else:
                series = None
        else:
            series = df["Close"] if "Close" in df.columns else None
        if series is None:
            return None
        series = series.dropna()
        series = series[series > 0]
        return series if len(series) else None
    except Exception as exc:                      # pragma: no cover
        log.warning("Yahoo serisi okunamadı (%s): %s", ticker, exc)
        return None


def _last_close(df, ticker: str) -> float | None:
    """yf.download çıktısından son geçerli kapanışı çıkarır (tek/çoklu sembol)."""
    try:
        if df is None or len(df) == 0:
            return None
        if hasattr(df.columns, "levels") and df.columns.nlevels > 1:
            # Sütunlar (alan, sembol) ya da (sembol, alan) olabilir; ikisini de dene
            if "Close" in df.columns.get_level_values(0):
                series = df["Close"][ticker] if ticker in df["Close"].columns else None
            elif ticker in df.columns.get_level_values(0):
                series = df[ticker]["Close"]
            else:
                series = None
        else:
            series = df["Close"] if "Close" in df.columns else None
        if series is None:
            return None
        series = series.dropna()
        if series.empty:
            return None
        return float(series.iloc[-1])
    except Exception as exc:  # pragma: no cover - savunmacı
        log.warning("Yahoo kapanış okunamadı (%s): %s", ticker, exc)
        return None


def fetch_yahoo(tickers: Iterable[str], *, period: str = "5d",
                retries: int = 2) -> dict[str, float]:
    """Son kapanışlar. Seriyi de isteyen build_snapshot fetch_yahoo_series kullanır."""
    return {t: float(sr.iloc[-1])
            for t, sr in fetch_yahoo_series(tickers, period=period,
                                            retries=retries).items()
            if len(sr)}


def fetch_yahoo_series(tickers: Iterable[str], *, period: str = "5d",
                       retries: int = 2) -> dict[str, "Any"]:
    """
    Sembollerin kapanış SERİLERİNİ tek toplu çağrıyla getirir.

    Seri gerekiyor çünkü ısı haritası 1 gün / 1 hafta / 1 ay değişimini
    hesaplıyor. Son fiyatı ayrıca indirmiyoruz: fetch_yahoo bu serinin son
    elemanını alıyor, böylece tek indirme iki işi de görüyor.
    """
    tickers = sorted({t for t in tickers if t})
    if not tickers:
        return {}

    import yfinance as yf  # yerel import: test ederken ağ gerekmesin

    out: dict[str, Any] = {}
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            df = yf.download(
                tickers=" ".join(tickers),
                period=period,
                interval="1d",
                auto_adjust=False,
                progress=False,
                threads=True,
                group_by="column",
            )
            for tk in tickers:
                sr = _close_series(df, tk)
                if sr is not None and len(sr):
                    out[tk] = sr
            if out:
                break
        except Exception as exc:
            last_exc = exc
            log.warning("Yahoo toplu çağrı hatası (deneme %s): %s", attempt + 1, exc)
            time.sleep(1.5 * (attempt + 1))

    # Toplu çağrıda düşen sembolleri tek tek dene
    missing = [t for t in tickers if t not in out]
    if missing:
        for tk in missing:
            try:
                hist = yf.Ticker(tk).history(period=period)
                if not hist.empty:
                    sr = hist["Close"].dropna()
                    sr = sr[sr > 0]
                    if len(sr):
                        out[tk] = sr
            except Exception as exc:
                log.warning("Yahoo tekil çağrı hatası (%s): %s", tk, exc)

    if not out and last_exc is not None:
        raise last_exc
    return out


# ---------------------------------------------------------------------------
# TEFAS
# ---------------------------------------------------------------------------
def _tefas_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
        "Origin": "https://www.tefas.gov.tr",
        "Referer": TEFAS_REFERER,
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    })
    return s


# TEFAS fonları üç tipe ayırır ve BindHistoryInfo bu filtreyi ZORUNLU sayar:
#   YAT -> yatırım fonları (hisse, borçlanma, altın, serbest, fon sepeti…)
#   EMK -> emeklilik (BES) fonları
#   BYF -> borsa yatırım fonları
# Eski kod yalnızca "YAT" soruyordu; diğer iki tipteki fonlar hiç bulunamıyordu.
TEFAS_FON_TIPLERI = ("YAT", "EMK", "BYF")


# Yanıttaki alan adları sürümden sürüme değişebiliyor (FONKODU / fonKodu /
# fonkod ...). Tek bir yazıma bağlanmak yerine adayları sırayla deniyoruz;
# karşılaştırma küçük harfe indirgenerek yapılır.
_TEFAS_ALAN = {
    "kod":   ("fonkodu", "fonkod", "kod", "code", "fund_code"),
    "fiyat": ("fiyat", "birimpaydegeri", "price", "sonfiyat"),
    "tarih": ("tarih", "date", "islemtarihi"),
}


def _tefas_sayi(ham) -> float | None:
    """TEFAS fiyatı sayı ya da metin ('1,4318' / '1.234,56') gelebilir."""
    if ham is None or ham == "":
        return None
    if isinstance(ham, (int, float)):
        return float(ham)
    metin = str(ham).strip()
    if "," in metin and "." in metin:
        metin = metin.replace(".", "").replace(",", ".")   # 1.234,56
    elif "," in metin:
        metin = metin.replace(",", ".")                    # 1,4318
    try:
        return float(metin)
    except ValueError:
        return None


def _alan(satir: dict, hangi: str):
    """Satırdan alanı, adı nasıl yazılmış olursa olsun okur."""
    kucuk = {str(k).lower().replace("_", ""): v for k, v in satir.items()}
    for aday in _TEFAS_ALAN[hangi]:
        if aday in kucuk and kucuk[aday] not in (None, ""):
            return kucuk[aday]
    return None


def _tefas_rows_yeni(session, fontip: str, start, end, timeout: int,
                     fon_kodu: str | None = None) -> list[dict]:
    """Yeni JSON API. fon_kodu None ise o tipteki bütün fonlar döner."""
    payload = {
        "fonTipi": fontip,
        "fonKodu": fon_kodu,
        "basTarih": start.strftime("%Y%m%d"),     # yeni API 8 haneli yazıyor
        "bitTarih": end.strftime("%Y%m%d"),
        "basSira": 1,
        "bitSira": 100000,
        "dil": "TR",
        "aramaMetni": None, "fonTurKod": None, "fonGrubu": None,
        "sfonTurKod": None, "fonTurAciklama": None, "kurucuKod": None,
        "sFonTurKod": "", "fonKod": "", "fonGrup": "", "fonUnvanTip": "",
    }
    resp = session.post(TEFAS_URL_YENI, json=payload, timeout=timeout,
                        headers={"Content-Type": "application/json",
                                 "Referer": TEFAS_REFERER_YENI,
                                 "Accept": "*/*"})
    resp.raise_for_status()
    veri = resp.json() or {}
    if veri.get("errorCode"):
        raise RuntimeError(f"TEFAS hata {veri['errorCode']}: "
                           f"{veri.get('errorMessage', '')}")
    return veri.get("resultList") or veri.get("data") or []


def _tefas_rows_eski(session, fontip: str, start, end, timeout: int) -> list[dict]:
    """Eski form-encoded API (2026 yenilemesinden önce). Son çare."""
    payload = {
        "fontip": fontip,
        "sfontur": "",
        "fonkod": "",
        "fongrup": "",
        "bastarih": start.strftime("%d.%m.%Y"),
        "bittarih": end.strftime("%d.%m.%Y"),
        "fonturkod": "",
        "fonunvantip": "",
        "strperiod": "1,1,1,1,1,1,1",
        "islemdurum": "1",
    }
    resp = session.post(TEFAS_URL, data=payload, timeout=timeout)
    resp.raise_for_status()
    return (resp.json() or {}).get("data") or []


def _tefas_rows(session, fontip: str, start, end, timeout: int) -> list[dict]:
    """Önce yeni API, olmazsa eski API. Geriye dönük uyumluluk için korunuyor."""
    return _tefas_rows_yeni(session, fontip, start, end, timeout)


def fetch_tefas(codes: Iterable[str], *, lookback_days: int = 15,
                timeout: int = 20,
                errors: list[str] | None = None,
                series_out: dict[str, dict[str, float]] | None = None
                ) -> dict[str, float]:
    """
    TEFAS fon fiyatlarını sitenin kendi API'sinden çeker.

    İKİ ÖNEMLİ DEĞİŞİKLİK
    ---------------------
    1) TOPLU İSTEK. Eskiden her fon için ayrı POST atılıyordu; 21 fonluk bir
       portföyde bu 21 ardışık istek (en kötü ihtimalle 21x20 sn) demekti ve
       tek bir yavaşlama bütün fonları düşürüyordu. Artık fon tipi başına tek
       istek atılıp sonuç yerelde filtreleniyor: en fazla 3 istek.
    2) ÜÇ FON TİPİ. "fontip" eskiden "YAT" sabitti; emeklilik (EMK) ve borsa
       yatırım fonları (BYF) hiçbir zaman bulunamıyordu.

    `errors` verilirse başarısızlığın GERÇEK sebebi (HTTP kodu / istisna)
    oraya yazılır — kullanıcıya "bulunamadı" yerine nedenini gösterebilmek için.

    429 (Too Many Requests) GÖRÜLÜRSE bütün denemeler hemen durur — daha
    fazla istek atmak yasağı uzatmaktan başka işe yaramaz — ve bir süreliğine
    (bkz. _TEFAS_SUS_SANIYE) TEFAS'a hiç istek atılmaz.
    """
    codes = sorted({c.strip().upper() for c in codes if c and c.strip()})
    if not codes:
        return {}

    simdi = time.time()
    susana_kadar = _tefas_sus_oku()
    if simdi < susana_kadar:
        kalan_dk = int((susana_kadar - simdi) / 60) + 1
        if errors is not None:
            errors.append(
                f"TEFAS çok sık istek nedeniyle geçici olarak sınırladı "
                f"(429). Yaklaşık {kalan_dk} dakika sonra tekrar denenecek; "
                f"bu süre içinde hiç istek atılmıyor ki yasak uzamasın.")
        return {}

    session = _tefas_session()
    try:
        session.get(TEFAS_REFERER, timeout=timeout)  # çerez almak için
    except Exception as exc:
        log.info("TEFAS ısınma isteği başarısız (önemsiz): %s", exc)

    end = dt.date.today()
    start = end - dt.timedelta(days=lookback_days)

    aranan = set(codes)
    en_guncel: dict[str, tuple[float, float]] = {}
    sorunlar: list[str] = []
    # kod -> {tarih_metni: fiyat} — ısı haritası dönem değişimi için kullanır
    seriler: dict[str, dict[str, float]] = {}
    sinirlandi = False   # 429 görüldü mü — görülürse bütün denemeler durur

    def isle(rows) -> None:
        for r in rows:
            if not isinstance(r, dict):
                continue
            kod = str(_alan(r, "kod") or "").strip().upper()
            if kod not in aranan:
                continue
            fiyat = _tefas_sayi(_alan(r, "fiyat"))
            if fiyat is None or fiyat <= 0:
                continue
            try:
                tarih = float(str(_alan(r, "tarih") or 0).replace("-", "")
                              .replace(".", "").replace("/", "")[:14] or 0)
            except ValueError:
                tarih = 0.0
            seriler.setdefault(kod, {})[f"{tarih:.0f}"] = fiyat
            onceki = en_guncel.get(kod)
            if onceki is None or tarih >= onceki[0]:
                en_guncel[kod] = (tarih, fiyat)

    # 1) YENİ API — fon tipi başına tek toplu istek
    for fontip in TEFAS_FON_TIPLERI:
        if not aranan - set(en_guncel):
            break
        try:
            isle(_tefas_rows_yeni(session, fontip, start, end, timeout))
        except Exception as exc:
            sorunlar.append(f"yeni API/{fontip}: {type(exc).__name__}: "
                            f"{str(exc)[:110]}")
            log.warning("TEFAS yeni API %s başarısız: %s", fontip, exc)
            if _tefas_429_mi(exc):
                sinirlandi = True
                break
        time.sleep(0.25)   # ardışık isteklerin hızını kes — TEFAS'ı ürkütme

    # 2) Toplu istek bazılarını getirmediyse tek tek sor (fon tipi bilinmiyor
    #    olabilir ya da toplu sonuç kırpılmış olabilir). 429 görülürse HİÇ
    #    başlamaz — 20 koda kadar tek tek istek atmak zaten 429'un sebebiydi.
    if not sinirlandi:
        for kod in sorted(aranan - set(en_guncel)):
            if sinirlandi:
                break
            for fontip in TEFAS_FON_TIPLERI:
                try:
                    isle(_tefas_rows_yeni(session, fontip, start, end, timeout,
                                          fon_kodu=kod))
                except Exception as exc:
                    log.info("TEFAS tekil %s/%s: %s", kod, fontip, exc)
                    if _tefas_429_mi(exc):
                        sorunlar.append(f"yeni API/tekil {kod}: 429 Too Many Requests")
                        sinirlandi = True
                        break
                if kod in en_guncel:
                    break
            time.sleep(0.25)

    # 3) Son çare: eski form-encoded API (TEFAS geri alırsa çalışsın).
    #    429 görüldüyse bu da atlanır.
    if not sinirlandi and aranan - set(en_guncel):
        for fontip in TEFAS_FON_TIPLERI:
            if not aranan - set(en_guncel):
                break
            try:
                isle(_tefas_rows_eski(session, fontip, start, end, timeout))
            except Exception as exc:
                log.info("TEFAS eski API %s: %s", fontip, exc)
                if _tefas_429_mi(exc):
                    sinirlandi = True
                    break

    if sinirlandi:
        _tefas_sus_yaz(simdi + _TEFAS_SUS_SANIYE)
        if errors is not None:
            errors.append(
                "TEFAS çok sık istek nedeniyle sizi geçici olarak sınırladı "
                "(429 Too Many Requests). Bir süre (birkaç dakika) hiç "
                "TEFAS isteği atılmayacak, sonra otomatik tekrar denenecek.")

    if errors is not None and sorunlar:
        errors.extend(sorunlar)
    if series_out is not None:
        series_out.update(seriler)

    eksik = sorted(aranan - set(en_guncel))
    if eksik:
        log.warning("TEFAS'ta bulunamayan kodlar: %s", ", ".join(eksik))

    return {kod: fiyat for kod, (_, fiyat) in en_guncel.items()}


# ---------------------------------------------------------------------------
# ANA GİRİŞ NOKTASI
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# DÖNEM DEĞİŞİMLERİ (ısı haritası)
# ---------------------------------------------------------------------------
# Etiket -> kaç TAKVİM günü geriye bakılacak. Borsa günü değil takvim günü
# kullanıyoruz: "1 hafta" kullanıcı için 7 gün öncesidir, 5 seans öncesi değil.
CHANGE_PERIODS = {"1g": 1, "1h": 7, "1a": 30, "3a": 90, "6a": 180, "1y": 365}
CHANGE_CURRENCIES = ("TRY", "USD", "EUR")

# Karşılaştırma aracının sunduğu ölçütler: etiket -> Yahoo sembolü.
# Hepsi TL'ye çevrilir, böylece portföyle aynı zeminde karşılaştırılır.
BENCHMARKS = {
    "BIST 100": "XU100.IS",
    "S&P 500": "^GSPC",
    "Nasdaq 100": "^NDX",
    "Altın (gram)": YAHOO_GOLD,
    "Gümüş (gram)": YAHOO_SILVER,
    "Dolar": "TRY=X",
    "Euro": "EURTRY=X",
    "Bitcoin": "BTC-USD",
}


def _to_points(obj) -> list[tuple[dt.date, float]]:
    """pandas Serisi ya da {tarih: fiyat} sözlüğünü sıralı (tarih, değer) listesine çevirir."""
    if obj is None:
        return []
    noktalar: list[tuple[dt.date, float]] = []

    if isinstance(obj, dict):
        for ham_tarih, deger in obj.items():
            metin = str(ham_tarih).split(".")[0]
            try:
                if len(metin) >= 14:            # epoch ms
                    tarih = dt.datetime.utcfromtimestamp(int(metin) / 1000).date()
                elif len(metin) == 8:           # YYYYAAGG
                    tarih = dt.date(int(metin[:4]), int(metin[4:6]), int(metin[6:8]))
                elif len(metin) >= 10:          # epoch sn
                    tarih = dt.datetime.utcfromtimestamp(int(metin)).date()
                else:
                    continue
            except (ValueError, OverflowError, OSError):
                continue
            noktalar.append((tarih, float(deger)))
    else:
        try:
            for damga, deger in obj.items():
                try:
                    tarih = damga.date() if hasattr(damga, "date") else damga
                    noktalar.append((tarih, float(deger)))
                except (TypeError, ValueError):
                    continue
        except AttributeError:
            return []

    noktalar = [(t, d) for t, d in noktalar if d == d and d > 0]
    noktalar.sort(key=lambda x: x[0])
    return noktalar


def _at_or_before(noktalar: list[tuple[dt.date, float]],
                  hedef: dt.date) -> float | None:
    """Hedef tarihe eşit ya da ondan önceki EN YAKIN kaydı verir (tatiller için)."""
    bulunan = None
    for tarih, deger in noktalar:
        if tarih <= hedef:
            bulunan = deger
        else:
            break
    return bulunan


def _combine(a: list[tuple[dt.date, float]], b: list[tuple[dt.date, float]],
             carp: bool = True) -> list[tuple[dt.date, float]]:
    """
    İki seriyi tarih bazında birleştirir (fiyat x kur gibi).

    b'de o tarih yoksa ondan önceki en yakın değer kullanılır: borsa günleri
    ile kur günleri her zaman örtüşmüyor ve kesişim alınsa seri çok kısalırdı.
    """
    if not a or not b:
        return []
    out: list[tuple[dt.date, float]] = []
    b_sozluk = dict(b)
    for tarih, deger in a:
        eslesen = b_sozluk.get(tarih)
        if eslesen is None:
            eslesen = _at_or_before(b, tarih)
        if eslesen is None or eslesen <= 0:
            continue
        out.append((tarih, deger * eslesen if carp else deger / eslesen))
    return out


def _pct_change(noktalar: list[tuple[dt.date, float]], gun: int) -> float | None:
    """Son değerin, 'gun' takvim günü öncesine göre yüzde değişimi."""
    if len(noktalar) < 2:
        return None
    son_tarih, son_deger = noktalar[-1]
    onceki = _at_or_before(noktalar, son_tarih - dt.timedelta(days=gun))
    if onceki is None or onceki <= 0:
        return None
    return (son_deger / onceki - 1.0) * 100.0


def compute_changes(assets: list[dict[str, Any]], snap: "MarketSnapshot",
                    yahoo_series: dict[str, Any],
                    tefas_series: dict[str, dict[str, float]]) -> None:
    """
    Her varlık için 1 gün / 1 hafta / 1 ay yüzde değişimini, TRY / USD / EUR
    cinsinden ayrı ayrı hesaplayıp snap.changes'e yazar.

    NEDEN üç para birimi: Türk yatırımcı için NVDA'nın TL getirisi kur etkisini
    içerir; dolar bazlı bakınca hissenin kendi hareketi görünür. Isı haritası
    hangi para birimi seçiliyse onu gösterir, böylece renk ile etiket aynı şeyi
    anlatır.
    """
    kur_noktalari = {
        ad: _to_points(yahoo_series.get(tk))
        for ad, tk in YAHOO_FX.items()
    }
    usdtry = kur_noktalari.get("USDTRY") or []
    eurtry = kur_noktalari.get("EURTRY") or []
    hkdtry = kur_noktalari.get("HKDTRY") or []
    altin = _to_points(yahoo_series.get(YAHOO_GOLD))
    gumus = _to_points(yahoo_series.get(YAHOO_SILVER))

    def try_serisi(a: dict[str, Any]) -> list[tuple[dt.date, float]]:
        """Varlığın BİR BİRİMİNİN TL değerinin zaman serisi."""
        kaynak, sembol = a.get("source"), a.get("symbol", "")
        birim_g = METAL_UNITS.get((a.get("unit") or "GRAM").upper(), 1.0)
        para = (a.get("currency") or "TRY").upper()

        if kaynak == SRC_GOLD or kaynak == SRC_SILVER:
            ons = altin if kaynak == SRC_GOLD else gumus
            usd = [(t, v / TROY_OUNCE_G * birim_g) for t, v in ons]
            return usd if para == "USD" else _combine(usd, usdtry)
        if kaynak == SRC_TEFAS:
            return _to_points(tefas_series.get(sembol.upper()))
        if kaynak == SRC_CASH:
            birim = [(t, 1.0) for t, _ in (usdtry or eurtry or [])]
            if para == "TRY":
                return birim
            return _combine(birim, usdtry if para == "USD" else eurtry)
        if kaynak == SRC_YAHOO:
            ham = _to_points(yahoo_series.get(sembol))
            if not ham:
                return []
            if para == "TRY":
                return ham
            if para == "USD":
                return _combine(ham, usdtry)
            if para == "EUR":
                return _combine(ham, eurtry)
            if para == "HKD":
                return _combine(ham, hkdtry)
        return []

    for a in assets:
        sembol = a.get("symbol", "")
        if not sembol or sembol in snap.changes:
            continue
        temel = try_serisi(a)
        if len(temel) < 2:
            continue
        snap.series[sembol] = temel
        kayit: dict[str, dict[str, float]] = {}
        for para in CHANGE_CURRENCIES:
            if para == "TRY":
                seri = temel
            elif para == "USD":
                seri = _combine(temel, usdtry, carp=False)
            else:
                seri = _combine(temel, eurtry, carp=False)
            donemler = {}
            for etiket, gun in CHANGE_PERIODS.items():
                yuzde = _pct_change(seri, gun)
                if yuzde is not None:
                    donemler[etiket] = yuzde
            if donemler:
                kayit[para] = donemler
        if kayit:
            snap.changes[sembol] = kayit

    # Ölçütler: hepsi TL cinsine çevrilir ki portföyle aynı zeminde dursun.
    for ad, tk in BENCHMARKS.items():
        ham = _to_points(yahoo_series.get(tk))
        if len(ham) < 2:
            continue
        if tk in (YAHOO_GOLD, YAHOO_SILVER):
            gram = [(t, v / TROY_OUNCE_G) for t, v in ham]
            snap.benchmarks[ad] = _combine(gram, usdtry)
        elif tk in ("^GSPC", "^NDX", "BTC-USD"):
            snap.benchmarks[ad] = _combine(ham, usdtry)
        else:
            snap.benchmarks[ad] = ham


# ---------------------------------------------------------------------------
# TEMEL VERİ (analist beklentileri)
# ---------------------------------------------------------------------------
# Buradaki her şey ÜÇÜNCÜ TARAF görüşüdür: analistlerin ortalama hedef fiyatı,
# beklenen kâr büyümesi, çarpanlar. Ne bizim tahminimiz ne de bir tavsiyedir;
# arayüzde de böyle etiketlenir. Analist hedefleri sistematik olarak iyimser
# olmakla bilinir, o yüzden "potansiyel" sütunu bir vaat değil bir beklentidir.
FUNDAMENTAL_ALANLAR = ("hedef", "potansiyel", "kar_buyume", "gelir_buyume",
                       "ileri_fk", "fk", "pd_dd", "analist_sayisi", "tavsiye",
                       "sektor", "ad", "piyasa_degeri")


def fetch_fundamentals(tickers: Iterable[str], *,
                       errors: list[str] | None = None) -> dict[str, dict]:
    """
    Sembol başına analist beklentilerini çeker (yfinance .info).

    Toplu uç noktası olmadığı için sembol başına bir istek gider; bu yüzden
    arayüzde OTOMATİK değil, düğmeyle ve uzun önbellekle çağrılır. Bir
    sembolün düşmesi diğerlerini etkilemez.
    """
    out: dict[str, dict] = {}
    sorunlar: list[str] = []
    try:
        import yfinance as yf
    except Exception as exc:                        # pragma: no cover
        if errors is not None:
            errors.append(f"yfinance yüklenemedi: {exc}")
        return out

    for tk in sorted({t for t in tickers if t}):
        try:
            bilgi = yf.Ticker(tk).info or {}
        except Exception as exc:
            sorunlar.append(f"{tk}: {type(exc).__name__}")
            continue
        if not bilgi:
            continue

        fiyat = (bilgi.get("currentPrice") or bilgi.get("regularMarketPrice")
                 or bilgi.get("previousClose"))
        hedef = bilgi.get("targetMeanPrice")
        potansiyel = ((hedef / fiyat - 1.0) * 100.0
                      if hedef and fiyat and fiyat > 0 else None)

        def _yuzde(anahtar):
            v = bilgi.get(anahtar)
            return v * 100.0 if isinstance(v, (int, float)) else None

        out[tk] = {
            "ad": bilgi.get("shortName") or bilgi.get("longName") or tk,
            "sektor": bilgi.get("sector") or "",
            "endustri": bilgi.get("industry") or "",
            "fiyat": fiyat,
            "hedef": hedef,
            "potansiyel": potansiyel,
            "kar_buyume": _yuzde("earningsGrowth"),
            "gelir_buyume": _yuzde("revenueGrowth"),
            "fk": bilgi.get("trailingPE"),
            "ileri_fk": bilgi.get("forwardPE"),
            "pd_dd": bilgi.get("priceToBook"),
            "analist_sayisi": bilgi.get("numberOfAnalystOpinions"),
            "tavsiye": bilgi.get("recommendationKey") or "",
            "piyasa_degeri": bilgi.get("marketCap"),
        }

    if errors is not None and sorunlar:
        errors.extend(sorunlar)
    return out


def _metal_unit_price(usd_per_oz: float, unit: str | None, currency: str,
                      usdtry: float | None) -> float | None:
    grams = METAL_UNITS.get((unit or "GRAM").upper(), 1.0)
    usd_price = (usd_per_oz / TROY_OUNCE_G) * grams
    if currency == "USD":
        return usd_price
    if usdtry:
        return usd_price * usdtry
    return None


def build_snapshot(assets: list[dict[str, Any]]) -> MarketSnapshot:
    """Portföydeki her varlık için güncel fiyatı toplar."""
    snap = MarketSnapshot(fetched_at=_now_istanbul())

    yahoo_tickers = {a["symbol"] for a in assets if a.get("source") == SRC_YAHOO}
    tefas_codes = {a["symbol"] for a in assets if a.get("source") == SRC_TEFAS}
    needs_gold = any(a.get("source") == SRC_GOLD for a in assets)
    needs_silver = any(a.get("source") == SRC_SILVER for a in assets)

    # Kur her zaman gerekli (USD varlıkların TRY karşılığı için)
    infra = set(YAHOO_FX.values())
    if needs_gold:
        infra.add(YAHOO_GOLD)
    if needs_silver:
        infra.add(YAHOO_SILVER)

    # 3 aylık geçmiş: hem son fiyat hem 1 gün / 1 hafta / 1 ay değişimi için.
    yahoo_series: dict[str, Any] = {}
    try:
        yahoo_series = fetch_yahoo_series(
            yahoo_tickers | infra | set(BENCHMARKS.values()), period="2y")
        prices = {t: float(sr.iloc[-1]) for t, sr in yahoo_series.items() if len(sr)}
    except Exception as exc:
        prices = {}
        snap.errors.append(f"Yahoo Finance'e ulaşılamadı: {exc}")

    for name, tk in YAHOO_FX.items():
        if tk in prices:
            snap.fx[name] = prices[tk]
    if "USDTRY" not in snap.fx:
        snap.errors.append(
            "USD/TRY kuru çekilemedi — dolar bazlı varlıkların TL karşılığı hesaplanamaz."
        )

    snap.gold_usd_oz = prices.get(YAHOO_GOLD)
    snap.silver_usd_oz = prices.get(YAHOO_SILVER)
    if needs_gold and snap.gold_usd_oz is None:
        snap.errors.append("Altın ons fiyatı (GC=F) çekilemedi.")
    if needs_silver and snap.silver_usd_oz is None:
        snap.errors.append("Gümüş ons fiyatı (SI=F) çekilemedi.")

    tefas_prices: dict[str, float] = {}
    tefas_errors: list[str] = []
    tefas_series: dict[str, dict[str, float]] = {}
    if tefas_codes:
        try:
            # 45 gün: 1 aylık değişim için yeterli geçmiş kalsın.
            tefas_prices = fetch_tefas(tefas_codes, lookback_days=45,
                                       errors=tefas_errors,
                                       series_out=tefas_series)
        except Exception as exc:
            snap.errors.append(f"TEFAS'a ulaşılamadı: {exc}")
        # Sadece değeri fiyata BAĞLI olan satırlar için uyar; kova satırlarının
        # değeri elle girilen tutardan gelir, fiyat bilgisi orada sadece yardımcıdır.
        critical = {a["symbol"].upper() for a in assets
                    if a.get("source") == SRC_TEFAS
                    and a.get("valuation") != "value"}
        missing = (tefas_codes & critical) - set(tefas_prices)
        if missing:
            # Sebebi de söyle: "bulunamadı" tek başına, TEFAS'a hiç
            # ulaşılamadığı durumla kodun yanlış olduğu durumu ayırt ettirmiyor.
            if tefas_errors and not tefas_prices:
                snap.errors.append(
                    "TEFAS'a ulaşılamadı, hiçbir fon fiyatı çekilemedi "
                    f"({len(missing)} fon). Sebep — {tefas_errors[0]}")
            elif tefas_errors:
                snap.errors.append(
                    "TEFAS kısmen yanıt verdi; şu fonlar alınamadı: "
                    + ", ".join(sorted(missing))
                    + f". Sebep — {tefas_errors[0]}")
            else:
                snap.errors.append(
                    "TEFAS bu kodları tanımadı (fon kodu yanlış ya da fon "
                    "kapanmış olabilir): " + ", ".join(sorted(missing)))

    for asset in assets:
        sym = asset["symbol"]
        src = asset.get("source", SRC_YAHOO)
        cur = asset.get("currency", "TRY")
        q = Quote(symbol=sym, currency=cur, source=src, asof=snap.fetched_at)

        if src == SRC_YAHOO:
            px = prices.get(sym)
            if px:
                q.price, q.ok = px, True
            else:
                q.error = "Yahoo Finance bu sembol için veri döndürmedi."
        elif src == SRC_TEFAS:
            px = tefas_prices.get(sym.upper())
            if px:
                q.price, q.ok = px, True
            else:
                q.error = "TEFAS bu fon kodu için fiyat döndürmedi."
        elif src in (SRC_GOLD, SRC_SILVER):
            oz = snap.gold_usd_oz if src == SRC_GOLD else snap.silver_usd_oz
            if oz:
                px = _metal_unit_price(oz, asset.get("unit"), cur, snap.usdtry)
                if px:
                    q.price, q.ok = px, True
                else:
                    q.error = "USD/TRY kuru olmadan TL fiyatı hesaplanamadı."
            else:
                q.error = "Ons fiyatı alınamadı."
        elif src == SRC_CASH:
            q.price, q.ok = 1.0, True
        elif src == SRC_MANUAL:
            px = asset.get("manual_price")
            if px:
                q.price, q.ok = float(px), True
            else:
                q.error = "Elle fiyat girilmemiş."
        else:
            q.error = f"Bilinmeyen fiyat kaynağı: {src}"

        snap.quotes[sym] = q

    # Isı haritası verisi. Fiyatlar gelmiş olsa bile geçmiş seri gelmemiş
    # olabilir; bu bir HATA değil, sadece o varlık renklendirilemez.
    try:
        compute_changes(assets, snap, yahoo_series, tefas_series)
    except Exception as exc:                       # noqa: BLE001
        log.warning("Dönem değişimleri hesaplanamadı: %s", exc)

    return snap


@dataclass
class Candidate:
    """Bir sembol için doğrulanmış fiyat kaynağı adayı."""
    symbol: str
    source: str
    currency: str
    price: float
    label: str


def probe_symbol(raw: str, *, timeout: int = 12) -> list[Candidate]:
    """
    Girilen kodu gerçek kaynaklarda yoklar ve fiyat DÖNEN adayları listeler.

    Neden gerekli: 'ASELS' de 'ADBE' de 4-5 harflidir; koda bakarak BIST mi ABD
    hissesi mi olduğunu kesin bilemezsiniz. Burada Yahoo ve TEFAS'a sorup
    gerçekten veri döneni seçiyoruz. Ağ yoksa boş liste döner ve uygulama
    çevrimdışı tahmine geri düşer.
    """
    text = (raw or "").strip().upper()
    if not text:
        return []
    base = text.replace(".IS", "").replace("-USD", "")

    # Denenecek adaylar: (yahoo sembolü, kaynak, para birimi, açıklama)
    trials: list[tuple[str, str, str, str]] = []
    if text.endswith(".IS"):
        trials.append((text, SRC_YAHOO, "TRY", "BIST hissesi / ETF"))
    elif text.endswith("-USD"):
        trials.append((text, SRC_YAHOO, "USD", "Kripto"))
    elif "=" in text or "^" in text:
        trials.append((text, SRC_YAHOO, "USD", "Endeks / vadeli"))
    else:
        trials.append((f"{base}.IS", SRC_YAHOO, "TRY", "BIST hissesi / ETF"))
        trials.append((base, SRC_YAHOO, "USD", "ABD hissesi / ETF"))
        trials.append((f"{base}-USD", SRC_YAHOO, "USD", "Kripto"))

    found: list[Candidate] = []
    yahoo_syms = [t[0] for t in trials]
    try:
        prices = fetch_yahoo(yahoo_syms, retries=0)
    except Exception as exc:
        log.info("Sembol yoklaması başarısız: %s", exc)
        prices = {}

    for sym, source, cur, label in trials:
        px_val = prices.get(sym)
        if px_val:
            found.append(Candidate(sym, source, cur, float(px_val), label))

    # TEFAS: 3 harfli kodlar fon olabilir
    if len(base) == 3 and base.isalpha():
        try:
            tefas = fetch_tefas([base], timeout=timeout)
        except Exception as exc:
            log.info("TEFAS yoklaması başarısız: %s", exc)
            tefas = {}
        if base in tefas:
            found.append(Candidate(base, SRC_TEFAS, "TRY", tefas[base], "TEFAS fonu"))

    return found


def _now_istanbul() -> str:
    try:
        from zoneinfo import ZoneInfo
        now = dt.datetime.now(ZoneInfo("Europe/Istanbul"))
    except Exception:
        now = dt.datetime.utcnow() + dt.timedelta(hours=3)
    return now.strftime("%d.%m.%Y %H:%M")

# ==========================================================================
# KAYNAK: portfolio/storage.py
# ==========================================================================


import base64
import json
import logging
import os
from dataclasses import dataclass
from typing import Any

import requests

log = logging.getLogger(__name__)

API = "https://api.github.com"
DEFAULT_PATH = "my_assets.json"


class StorageError(RuntimeError):
    pass


@dataclass
class LoadResult:
    data: Any
    sha: str | None
    backend: str          # "github" | "local"
    message: str = ""


class Storage:
    """GitHub'a yazar; yapılandırma yoksa yerel dosyaya düşer."""

    def __init__(self, config: dict[str, Any] | None = None,
                 local_path: str = DEFAULT_PATH):
        cfg = dict(config or {})
        self.token = (cfg.get("token") or "").strip()
        self.repo = (cfg.get("repo") or "").strip()
        self.branch = (cfg.get("branch") or "main").strip()
        self.path = (cfg.get("path") or local_path).strip()
        self.local_path = local_path
        self.committer_name = cfg.get("committer_name") or "aether-nexus-bot"
        self.committer_email = cfg.get("committer_email") or "bot@users.noreply.github.com"
        self._sha: str | None = None

    # -- durum -------------------------------------------------------------
    @property
    def enabled(self) -> bool:
        return bool(self.token and self.repo)

    @property
    def backend(self) -> str:
        return "github" if self.enabled else "local"

    def describe(self) -> str:
        if self.enabled:
            return f"GitHub → {self.repo}@{self.branch}/{self.path}"
        return f"Yerel dosya → {self.local_path} (kalıcı değil!)"

    # -- iç yardımcılar ----------------------------------------------------
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _url(self) -> str:
        return f"{API}/repos/{self.repo}/contents/{self.path}"

    # -- okuma -------------------------------------------------------------
    def load(self, default: Any = None) -> LoadResult:
        if default is None:
            default = []

        if self.enabled:
            try:
                r = requests.get(self._url(), headers=self._headers(),
                                 params={"ref": self.branch}, timeout=20)
                if r.status_code == 404:
                    self._sha = None
                    return LoadResult(default, None, "github",
                                      "Depoda dosya yok, ilk kayıtta oluşturulacak.")
                r.raise_for_status()
                payload = r.json()
                self._sha = payload.get("sha")
                raw = base64.b64decode(payload.get("content", "")).decode("utf-8")
                return LoadResult(json.loads(raw or "[]"), self._sha, "github")
            except Exception as exc:
                log.error("GitHub okuma hatası: %s", exc)
                raise StorageError(f"GitHub'dan okunamadı: {exc}") from exc

        if os.path.exists(self.local_path):
            with open(self.local_path, "r", encoding="utf-8") as f:
                return LoadResult(json.load(f), None, "local")
        return LoadResult(default, None, "local", "Yerel dosya bulunamadı.")

    # -- yazma -------------------------------------------------------------
    def save(self, data: Any, message: str = "portföy güncellendi") -> str:
        body = json.dumps(data, indent=2, ensure_ascii=False) + "\n"

        # Yerel kopya her zaman yazılır (aynı oturumda hızlı okuma için)
        try:
            with open(self.local_path, "w", encoding="utf-8") as f:
                f.write(body)
        except OSError as exc:
            log.warning("Yerel kopya yazılamadı: %s", exc)

        if not self.enabled:
            return "local"

        payload = {
            "message": message,
            "content": base64.b64encode(body.encode("utf-8")).decode("ascii"),
            "branch": self.branch,
            "committer": {"name": self.committer_name, "email": self.committer_email},
        }

        # sha ile ilgili KURTARILABİLİR hatalar:
        #   409 -> başka bir yerden commit gelmiş, elimizdeki sha eskimiş
        #   422 -> dosya depoda VAR ama sha göndermedik ("sha wasn't supplied").
        #          Bu, dosya uygulama dışından (elle upload) eklendiğinde ya da
        #          bu Storage örneği hiç load() etmeden save()'e geldiğinde olur.
        # İkisinin de çaresi aynı: sha'yı GET ile tazeleyip tekrar denemek.
        # Eskiden yalnız 409 ele alınıyordu, bu yüzden depoya elle yüklenen
        # portfolio_history.json ilk kayıtta 422 verip uygulamayı düşürüyordu.
        SHA_HATALARI = (409, 422)
        son_hata = ""

        for attempt in range(3):
            if self._sha:
                payload["sha"] = self._sha
            else:
                payload.pop("sha", None)
            try:
                r = requests.put(self._url(), headers=self._headers(),
                                 json=payload, timeout=25)
            except requests.RequestException as exc:
                # Ağ hatası da StorageError olmalı; yoksa çağıranın
                # `except StorageError` bloğu yakalayamaz ve uygulama düşer.
                raise StorageError(f"GitHub'a bağlanılamadı: {exc}") from exc

            if r.status_code in (200, 201):
                self._sha = (r.json().get("content") or {}).get("sha")
                return self._sha or "ok"

            son_hata = f"HTTP {r.status_code}: {r.text[:300]}"

            if r.status_code in SHA_HATALARI and attempt < 2:
                log.info("GitHub %s, sha tazeleniyor.", r.status_code)
                self._sha = None
                try:
                    self.load()          # _sha'yı günceller
                except StorageError as exc:
                    log.info("sha tazelenemedi: %s", exc)
                if not self._sha:
                    # Dosya gerçekten yoksa sha'sız deneme doğru olan.
                    log.info("sha alınamadı; sha'sız yazma denenecek.")
                continue

            raise StorageError(f"GitHub'a yazılamadı ({son_hata})")

        raise StorageError(f"GitHub'a yazılamadı, sha çakışması çözülemedi "
                           f"({son_hata})")


def storage_from_secrets(secrets: Any, local_path: str = DEFAULT_PATH) -> Storage:
    """st.secrets nesnesinden Storage üretir; bölüm yoksa yerel moda düşer."""
    cfg: dict[str, Any] = {}
    try:
        if secrets is not None and "github" in secrets:
            cfg = dict(secrets["github"])
    except Exception as exc:
        log.info("secrets okunamadı: %s", exc)
    return Storage(cfg, local_path=local_path)

# ==========================================================================
# KAYNAK: portfolio/analytics.py
# ==========================================================================


from typing import Any

import math

import pandas as pd

# dataviz referans paletinin koyu zemin adımları (doğrulanmış sıra)
SERIES_COLORS = [
    "#3987e5",  # mavi
    "#d95926",  # turuncu
    "#199e70",  # deniz yeşili
    "#c98500",  # sarı
    "#d55181",  # macenta
    "#2f9e44",  # yeşil (koyu zeminde okunurluk için bir adım açıldı)
    "#9085e9",  # mor
    "#e66767",  # kırmızı
]
OTHER_COLOR = "#6b6b66"

# Adet/maliyet girilmemiş satırların grafiklerdeki ortak etiketi
DIGER_ETIKET = "Diğer"
ACCENT = "#00f3ff"
POS_COLOR = "#199e70"
NEG_COLOR = "#e66767"


def color_map(keys: list[str]) -> dict[str, str]:
    """Kategoriye sabit renk atar; 9. kategoriden sonrası 'Diğer' rengine düşer."""
    out: dict[str, str] = {}
    for i, k in enumerate(keys):
        out[k] = SERIES_COLORS[i] if i < len(SERIES_COLORS) else OTHER_COLOR
    return out


def to_try_rate(currency: str, fx: dict[str, float]) -> float:
    """Bir para biriminin TL karşılığı. Kur yoksa NaN döner (sessizce 1 varsaymaz)."""
    cur = (currency or "TRY").upper()
    if cur == "TRY":
        return 1.0
    if cur == "USD":
        return fx.get("USDTRY", float("nan"))
    if cur == "EUR":
        if "EURTRY" in fx:
            return fx["EURTRY"]
        if "EURUSD" in fx and "USDTRY" in fx:
            return fx["EURUSD"] * fx["USDTRY"]
    if cur == "HKD":
        if "HKDTRY" in fx:
            return fx["HKDTRY"]
        # USDHKD = 1 USD kaç HKD -> 1 HKD = USDTRY / USDHKD lira
        if fx.get("USDHKD") and "USDTRY" in fx:
            return fx["USDTRY"] / fx["USDHKD"]
    return float("nan")


CHANGE_LABELS = {"1g": "1G %", "1h": "1H %", "1a": "1A %",
                 "3a": "3A %", "6a": "6A %", "1y": "1Y %"}
PERIOD_GUN = {"1G %": 1, "1H %": 7, "1A %": 30, "3A %": 90,
              "6A %": 180, "1Y %": 365}


def build_dataframe(assets: list[dict[str, Any]], quotes: dict[str, Any],
                    fx: dict[str, float] | None = None,
                    changes: dict[str, dict[str, dict[str, float]]] | None = None,
                    change_currency: str = "TRY") -> pd.DataFrame:
    """
    Varlık listesi + fiyatlardan hesaplanmış tabloyu üretir.

    `changes` verilirse 1 Gün / 1 Hafta / 1 Ay yüzde sütunları eklenir. Bunlar
    ISI HARİTASININ girdisidir ve `change_currency` cinsinden hesaplanmıştır:
    TRY'de kur etkisi dahildir, USD'de ABD hissesinin kendi hareketi görünür.
    """
    fx = fx or {}
    changes = changes or {}
    rows: list[dict[str, Any]] = []
    for a in assets:
        sym = a["symbol"]
        q = quotes.get(sym)
        price = getattr(q, "price", None) if q is not None else None
        ok = bool(getattr(q, "ok", False)) if q is not None else False
        err = getattr(q, "error", "") if q is not None else "Fiyat çekilmedi."

        cur = a.get("currency", "TRY")
        qty = float(a.get("qty") or 0.0)
        cost = float(a.get("avg_cost") or 0.0)
        rate = to_try_rate(cur, fx)
        # Maliyet ayrı bir para biriminde tutulabilir (bkz. classification.
        # normalize_asset): BIST hissesinin fiyatı TRY, maliyeti USD olabilir.
        cost_cur = a.get("cost_currency") or cur
        cost_rate = rate if cost_cur == cur else to_try_rate(cost_cur, fx)
        price_val = float(price) if price else float("nan")

        # Değerleme modu: adet × canlı fiyat mı, elle girilen toplam tutar mı?
        kova = a.get("valuation") == "value"
        if kova:
            deger_nat = float(a.get("manual_price") or 0.0)   # toplam tutar
            maliyet_nat = cost                                 # toplam maliyet
            ok = True
            err = ""
            if not math.isnan(price_val) and price_val > 0:
                err = ""  # canlı fiyat bilgi amaçlı gösterilir
            else:
                price_val = float("nan")
        else:
            deger_nat = qty * price_val
            maliyet_nat = qty * cost

        rows.append({
            "Sembol": a.get("display") or sym,
            "Yahoo Sembol": sym,
            "Ana Sınıf": a.get("ana_sinif", "Diğer"),
            "Alt Sınıf": a.get("alt_sinif", "Diğer"),
            "Sektör": a.get("sektor", "Diğer"),
            "Hesap": a.get("hesap", ""),
            "Kaynak": a.get("source", ""),
            "Birim": a.get("unit") or "",
            "Para Birimi": cur,
            "Maliyet Para Birimi": cost_cur,
            "Değerleme": "Diğer" if kova else "Canlı",
            "Adet": qty,
            "Maliyet": cost,
            # Varlığın KENDİ para birimindeki değeri — etiketlerde bunu
            # gösteriyoruz ki ABD hissesi dolar, BIST hissesi lira okunsun.
            "Değer (kendi)": deger_nat,
            "Fiyat": price_val,
            "Maliyet (TRY)": maliyet_nat * cost_rate,
            "Değer (TRY)": deger_nat * rate,
            "K/Z (TRY)": deger_nat * rate - maliyet_nat * cost_rate,
            "K/Z %": ((deger_nat * rate - maliyet_nat * cost_rate)
                      / (maliyet_nat * cost_rate) * 100.0)
                     if maliyet_nat * cost_rate > 0 else float("nan"),
            "Fiyat OK": ok,
            "Hata": "" if ok else err,
            **{etiket: (changes.get(sym, {}).get(change_currency, {}).get(anahtar)
                        if not kova else None)
               for anahtar, etiket in CHANGE_LABELS.items()},
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df["Etiket"] = _unique_labels(df)
    df["Varlık"] = _chart_labels(df)
    total = df["Değer (TRY)"].sum(skipna=True)
    df["Ağırlık %"] = (df["Değer (TRY)"] / total * 100.0) if total else float("nan")
    return df.sort_values("Değer (TRY)", ascending=False, na_position="last")


def _chart_labels(df: pd.DataFrame) -> pd.Series:
    """
    Grafiklerde kullanılacak varlık etiketi.

    Adet girilmemiş ("Diğer") satırlar, AYNI GRUPTA canlı fiyatlanan bir varlık
    varsa tek bir "Diğer" kutusunda toplanır — kullanıcının istediği davranış:
    "bir fonda adet/maliyet yazıyorsa canlı, yazmıyorsa 'Diğer' olarak son
    değeriyle işlensin".

    Grubun TAMAMI elle değerliyse toplama yapılmaz; aksi halde harita tek bir
    isimsiz "Diğer" kutusuna düşer ve hiçbir şey görünmezdi.
    """
    grup = df["Ana Sınıf"].astype(str) + "|" + df["Alt Sınıf"].astype(str)
    canli_var = grup.isin(set(grup[df["Değerleme"] == "Canlı"]))
    topla = (df["Değerleme"] != "Canlı") & canli_var
    return df["Etiket"].mask(topla, DIGER_ETIKET)


def _unique_labels(df: pd.DataFrame) -> pd.Series:
    """
    Grafik ekseninde kullanılacak TEKİL etiket üretir.

    Portföyde aynı ada sahip birden çok pozisyon olabiliyor (BIST'teki 'YK' ile
    fon hesabındaki 'YK' gibi). Aynı etiketle çizilirlerse Plotly onları tek
    kategoride üst üste yığar ve çubuk grafik yanlış okunur. Tekrar eden adlara
    önce alt sınıf, gerekirse hesap adı eklenir.
    """
    labels = df["Sembol"].astype(str).copy()
    dupe = labels.duplicated(keep=False)
    if dupe.any():
        labels[dupe] = labels[dupe] + " · " + df.loc[dupe, "Alt Sınıf"].astype(str)
        still = labels.duplicated(keep=False)
        if still.any():
            labels[still] = labels[still] + " · " + df.loc[still, "Hesap"].astype(str)
            # Hesap da aynıysa sıra numarası ver — hiçbir zaman çakışmasın
            final = labels.duplicated(keep=False)
            if final.any():
                labels[final] = [f"{v} ({i + 1})"
                                 for i, v in enumerate(labels[final])]
    return labels


BORC_SINIFLARI = {"Yükümlülük"}


def split_borc(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Varlık satırlarını borç satırlarından ayırır."""
    if df.empty:
        return df, df
    mask = df["Ana Sınıf"].isin(BORC_SINIFLARI)
    return df[~mask], df[mask]


def totals(df: pd.DataFrame, usdtry: float | None) -> dict[str, float]:
    empty = {"deger_try": 0.0, "maliyet_try": 0.0, "kz_try": 0.0, "kz_pct": 0.0,
             "deger_usd": float("nan"), "eksik": 0, "borc_try": 0.0, "net_try": 0.0}
    if df is None or df.empty:
        return empty

    varlik, borc = split_borc(df)
    deger = float(varlik["Değer (TRY)"].sum(skipna=True))
    maliyet = float(varlik["Maliyet (TRY)"].sum(skipna=True))
    borc_try = abs(float(borc["Değer (TRY)"].sum(skipna=True))) if not borc.empty else 0.0
    kz = deger - maliyet
    return {
        "deger_try": deger,
        "maliyet_try": maliyet,
        "kz_try": kz,
        "kz_pct": (kz / maliyet * 100.0) if maliyet else 0.0,
        "deger_usd": (deger / usdtry) if usdtry else float("nan"),
        "eksik": int((~df["Fiyat OK"]).sum()),
        "borc_try": borc_try,
        "net_try": deger - borc_try,
    }


# ---------------------------------------------------------------------------
# GÖRÜNTÜLEME PARA BİRİMİ
# Bütün hesaplar TRY üzerinden yapılır; burada sadece SUNUM çevrilir. Böylece
# para birimini değiştirmek hiçbir hesabı, oranı veya sıralamayı bozmaz.
# ---------------------------------------------------------------------------
DISPLAY_CURRENCIES = ("TRY", "USD", "EUR")
CURRENCY_SYMBOLS = {"TRY": "₺", "USD": "$", "EUR": "€"}


def display_rate(currency: str, fx: dict[str, float] | None) -> float:
    """1 TRY kaç <currency> eder? TRY için 1.0, kur yoksa NaN."""
    cur = (currency or "TRY").upper()
    if cur == "TRY":
        return 1.0
    try_per_unit = to_try_rate(cur, fx or {})
    if not try_per_unit or try_per_unit != try_per_unit or try_per_unit <= 0:
        return float("nan")
    return 1.0 / try_per_unit


def format_money(try_value: float, currency: str, fx: dict[str, float] | None,
                 decimals: int | None = None) -> str:
    """TRY tutarını seçilen para biriminde biçimlendirir."""
    if try_value != try_value:
        return "—"
    oran = display_rate(currency, fx)
    if oran != oran:
        return "—"
    cur = (currency or "TRY").upper()
    tutar = try_value * oran
    if decimals is None:
        decimals = 0 if abs(tutar) >= 100 else 2
    return f"{CURRENCY_SYMBOLS.get(cur, '')}{tutar:,.{decimals}f}"


def convert_columns(df: pd.DataFrame, currency: str,
                    fx: dict[str, float] | None) -> pd.DataFrame:
    """(TRY) ile biten sütunları seçilen para birimine çevirir, başlığı yeniler."""
    if df is None or df.empty or (currency or "TRY").upper() == "TRY":
        return df
    oran = display_rate(currency, fx)
    if oran != oran:
        return df
    cur = currency.upper()
    out = df.copy()
    yeniden_ad: dict[str, str] = {}
    for col in out.columns:
        if isinstance(col, str) and col.endswith("(TRY)"):
            out[col] = out[col] * oran
            yeniden_ad[col] = col.replace("(TRY)", f"({cur})")
    return out.rename(columns=yeniden_ad)


# ---------------------------------------------------------------------------
# KARŞILAŞTIRMA SERİSİ
# ---------------------------------------------------------------------------
def _endeksle(noktalar: list[tuple], baslangic) -> list[tuple]:
    """Seriyi başlangıç tarihinde 100'e sabitler; farklı ölçekler kıyaslanabilsin."""
    taban = None
    for tarih, deger in noktalar:
        if tarih >= baslangic and deger > 0:
            taban = deger
            break
    if not taban:
        return []
    return [(t, v / taban * 100.0) for t, v in noktalar if t >= baslangic]


def portfoy_getiri_serisi(df: pd.DataFrame, series: dict[str, list],
                          gun: int) -> list[tuple]:
    """
    Portföyün getiri serisi: BUGÜNKÜ ağırlıklarla geriye dönük hesaplanır.

    DİKKAT — bu bir "şu anki portföyü o gün de elimde tutsaydım" senaryosudur.
    Geçmişteki alım satımları bilmediği için gerçekleşmiş performansınız değil;
    ama portföy değeri serisinden farklı olarak para giriş/çıkışlarından
    ETKİLENMEZ, bu yüzden bir endeksle yan yana konabilecek tek seri budur.
    """
    if df is None or df.empty or not series:
        return []
    import datetime as _dt
    baslangic = _dt.date.today() - _dt.timedelta(days=gun)

    agirlikli: dict = {}
    toplam_agirlik = 0.0
    for _, satir in df.iterrows():
        sembol = satir.get("Yahoo Sembol")
        deger = satir.get("Değer (TRY)")
        noktalar = series.get(sembol)
        if not noktalar or deger is None or deger != deger or deger <= 0:
            continue
        endeks = _endeksle(noktalar, baslangic)
        if len(endeks) < 2:
            continue
        toplam_agirlik += float(deger)
        for tarih, puan in endeks:
            onceki = agirlikli.get(tarih, (0.0, 0.0))
            agirlikli[tarih] = (onceki[0] + puan * float(deger),
                                onceki[1] + float(deger))

    if not agirlikli or toplam_agirlik <= 0:
        return []
    # Her gün için O GÜN verisi olan pozisyonların ağırlıklı ortalaması
    return sorted((t, pay / agr) for t, (pay, agr) in agirlikli.items() if agr > 0)


def karsilastirma_tablosu(portfoy: list[tuple], olcutler: dict[str, list],
                          gun: int) -> pd.DataFrame:
    """Portföy ve seçilen ölçütlerin 100'e endekslenmiş serileri."""
    import datetime as _dt
    baslangic = _dt.date.today() - _dt.timedelta(days=gun)
    seriler: dict[str, dict] = {}
    if portfoy:
        seriler["Portföyüm"] = dict(portfoy)
    for ad, noktalar in olcutler.items():
        endeks = _endeksle(noktalar, baslangic)
        if len(endeks) >= 2:
            seriler[ad] = dict(endeks)
    if not seriler:
        return pd.DataFrame()
    df = pd.DataFrame(seriler).sort_index()
    return df.ffill().dropna(how="all")


# ---------------------------------------------------------------------------
# HEDEF AĞIRLIK / DENGE
# ---------------------------------------------------------------------------
def denge_tablosu(df: pd.DataFrame, seviye: str,
                  hedefler: dict[str, float]) -> pd.DataFrame:
    """
    Mevcut ağırlık ile KULLANICININ belirlediği hedef ağırlığı karşılaştırır.

    Hedefleri biz üretmiyoruz — kullanıcı giriyor, biz aradaki farkı TL
    cinsine çeviriyoruz. "Şu sınıfı %25'e indirmek istersem ne kadar kaydırmam
    gerekir" sorusunun cevabı aritmetiktir; ne yapması gerektiği değildir.
    """
    bos = pd.DataFrame(columns=[seviye, "Mevcut %", "Hedef %", "Fark puan",
                                "Fark (TRY)"])
    if df is None or df.empty or seviye not in df.columns:
        return bos
    varlik = df[df["Ana Sınıf"] != "Yükümlülük"] if "Ana Sınıf" in df.columns else df
    grup = varlik.groupby(seviye)["Değer (TRY)"].sum(min_count=1).dropna()
    toplam = float(grup.sum())
    if toplam <= 0:
        return bos

    satirlar = []
    for ad, deger in grup.items():
        mevcut = float(deger) / toplam * 100.0
        hedef = float(hedefler.get(str(ad), mevcut))
        satirlar.append({
            seviye: ad,
            "Mevcut %": mevcut,
            "Hedef %": hedef,
            "Fark puan": hedef - mevcut,
            "Fark (TRY)": (hedef - mevcut) / 100.0 * toplam,
        })
    out = pd.DataFrame(satirlar).sort_values("Mevcut %", ascending=False)
    return out.reset_index(drop=True)


def allocation(df: pd.DataFrame, level: str) -> pd.DataFrame:
    """Bir hiyerarşi seviyesine göre dağılım tablosu."""
    if df.empty or level not in df.columns:
        return pd.DataFrame(columns=[level, "Değer (TRY)", "Pay %"])
    g = (df.groupby(level, dropna=False)["Değer (TRY)"]
           .sum(min_count=1).reset_index())
    total = g["Değer (TRY)"].sum(skipna=True)
    g["Pay %"] = (g["Değer (TRY)"] / total * 100.0) if total else float("nan")
    return g.sort_values("Değer (TRY)", ascending=False)


def _row_paths(valid: pd.DataFrame, levels: list[str]) -> list[tuple]:
    """
    Her satır için hiyerarşi yolunu üretir ve ÜST ÜSTE GELEN aynı etiketleri
    teker. Örneğin alt sınıfı 'Gümüş', sektörü de 'Gümüş' olan bir satır
    "Emtia > Gümüş > Gümüş" değil "Emtia > Gümüş" olur; grafiklerde anlamsız
    tekrarlar kaybolur.
    """
    out: list[tuple] = []
    for _, r in valid.iterrows():
        path: list[str] = []
        for lv in levels:
            raw = r.get(lv)
            label = "Belirsiz" if raw is None or pd.isna(raw) else str(raw).strip()
            label = label or "Belirsiz"
            if not path or path[-1] != label:
                path.append(label)
        out.append((tuple(path), float(r["Değer (TRY)"])))
    return out


def _hierarchy_nodes(valid: pd.DataFrame,
                     levels: list[str]) -> tuple[dict[tuple, float], dict[tuple, str]]:
    """Yol öneklerinin toplamları ve her düğümün ait olduğu ana grup."""
    totals: dict[tuple, float] = {}
    group: dict[tuple, str] = {}
    for path, value in _row_paths(valid, levels):
        for depth in range(1, len(path) + 1):
            key = path[:depth]
            totals[key] = totals.get(key, 0.0) + value
            group[key] = path[0]
    return totals, group


def _sorted_keys(totals: dict[tuple, float]) -> list[tuple]:
    """Önce sığ düğümler, sonra büyükten küçüğe."""
    return sorted(totals, key=lambda k: (len(k), -totals[k]))


def sankey_data(df: pd.DataFrame, levels: list[str]) -> dict[str, Any]:
    """
    Çok seviyeli akış diyagramı için düğüm/bağlantı verisi.
    Düğüm kimliği tam yoldur; bu sayede aynı isimli sektör ve sembol birbirine
    karışmaz (eski koddaki en büyük görsel hata buydu).
    """
    if df.empty or "Değer (TRY)" not in df.columns or not levels:
        return {"labels": [], "paths": [], "source": [], "target": [], "value": [],
                "node_colors": [], "link_colors": []}
    valid = df[df["Değer (TRY)"].notna() & (df["Değer (TRY)"] > 0)]
    if valid.empty:
        return {"labels": [], "paths": [], "source": [], "target": [], "value": [],
                "node_colors": [], "link_colors": []}

    totals, group = _hierarchy_nodes(valid, levels)
    top_colors = color_map(list(allocation(valid, levels[0])[levels[0]].astype(str)))

    labels: list[str] = ["Portföy"]
    paths: list[str] = ["Portföy"]
    node_colors: list[str] = [ACCENT]
    index: dict[tuple, int] = {}

    for key in _sorted_keys(totals):
        index[key] = len(labels)
        labels.append(key[-1])
        paths.append(" › ".join(key))
        node_colors.append(top_colors.get(group[key], OTHER_COLOR))

    src: list[int] = []
    tgt: list[int] = []
    val: list[float] = []
    link_colors: list[str] = []

    for key, amount in totals.items():
        parent = 0 if len(key) == 1 else index[key[:-1]]
        src.append(parent)
        tgt.append(index[key])
        val.append(amount)
        link_colors.append(_rgba(top_colors.get(group[key], OTHER_COLOR), 0.32))

    return {
        "labels": labels,
        "paths": paths,
        "source": src,
        "target": tgt,
        "value": val,
        "node_colors": node_colors,
        "link_colors": link_colors,
    }


# ---------------------------------------------------------------------------
# ISI HARİTASI PALETİ
# ---------------------------------------------------------------------------
# Iraksak (diverging) rampa: iki kutup + NÖTR GRİ orta nokta. Orta noktada hue
# yok — gökkuşağı rampası okunamaz olurdu.
#
# Neden saf kırmızı/yeşil değil: renk körlüğünde ayırt edilemez. Somon (#f07a72)
# ile deniz yeşili (#45d69a) hem tonda hem AÇIKLIKTA ayrışır. Açıklık orta
# noktadan iki uca doğru tekdüze artar (0.05 -> 0.34 ve 0.05 -> 0.52), yani
# renk görülmese bile yoğunluk okunur. Ayrıca her kutuda yüzde YAZILI olduğu
# için kimlik hiçbir zaman yalnız renge bağlı değildir.
HEAT_STEPS: list[tuple[float, str]] = [
    (-8.0, "#f07a72"),   # güçlü düşüş
    (-4.0, "#d15a55"),
    (-1.5, "#a24448"),
    (-0.3, "#6e3a3f"),
    (0.0,  "#3f3f4a"),   # nötr — hue yok
    (0.3,  "#2a6b52"),
    (1.5,  "#219166"),
    (4.0,  "#27b87e"),
    (8.0,  "#45d69a"),   # güçlü yükseliş
]
HEAT_NEUTRAL = "#3f3f4a"
HEAT_UNKNOWN = "#26262e"     # değişim hesaplanamadı


def heat_color(pct: float | None) -> str:
    """Yüzde değişimi ıraksak rampadaki en yakın adıma oturtur."""
    if pct is None or pct != pct:
        return HEAT_UNKNOWN
    if pct <= HEAT_STEPS[0][0]:
        return HEAT_STEPS[0][1]
    if pct >= HEAT_STEPS[-1][0]:
        return HEAT_STEPS[-1][1]
    for (alt, renk), (ust, _) in zip(HEAT_STEPS, HEAT_STEPS[1:]):
        if alt <= pct < ust:
            return renk
    return HEAT_NEUTRAL


def _relative_luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    kanal = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        kanal.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * kanal[0] + 0.7152 * kanal[1] + 0.0722 * kanal[2]


def text_on(hex_color: str) -> str:
    """
    Zemine göre okunur yazı rengi. Rampanın her adımı için seçilen renk
    4.5:1 kontrastı geçiyor (doğrulandı); açık uçlarda koyu, koyu uçlarda
    beyaz yazı çıkar.
    """
    return "#0a0a0c" if _relative_luminance(hex_color) > 0.18 else "#ffffff"


def _node_changes(valid: pd.DataFrame, levels: list[str],
                  change_col: str) -> dict[tuple, float]:
    """
    Her hiyerarşi düğümü için DEĞERE GÖRE AĞIRLIKLI ortalama yüzde değişim.

    Basit ortalama yanlış olurdu: 1.000 TL'lik pozisyonun %10'u ile 500.000
    TL'lik pozisyonun %1'i aynı ağırlıkta sayılırdı. Grup rengi, grubun
    gerçekte ne kadar hareket ettiğini göstermeli.
    """
    paylar: dict[tuple, float] = {}
    agirliklar: dict[tuple, float] = {}
    # _row_paths ile AYNI yol üretimini kullanmak şart: farklı üretirsek
    # ağırlıklı ortalama, treemap'in gerçekte çizdiği düğümlere denk gelmez.
    yollar = _row_paths(valid, levels)          # [(yol, değer), ...]
    for (yol, agirlik), (_, satir) in zip(yollar, valid.iterrows()):
        pct = satir.get(change_col)
        if pct is None or pct != pct or agirlik <= 0:
            continue
        for derinlik in range(1, len(yol) + 1):
            anahtar = yol[:derinlik]
            paylar[anahtar] = paylar.get(anahtar, 0.0) + pct * agirlik
            agirliklar[anahtar] = agirliklar.get(anahtar, 0.0) + agirlik
    return {k: paylar[k] / agirliklar[k] for k in paylar if agirliklar.get(k)}


def _node_native(valid: pd.DataFrame, levels: list[str]) -> dict[tuple, str]:
    """
    Her düğüm için KENDİ para birimindeki toplam — ama yalnızca düğümün
    altındaki bütün satırlar aynı para birimindeyse.

    Karışık bir düğümde (ör. "Hisse Senedi" altında hem BIST hem ABD)
    dolarla lirayı toplamak anlamsız olurdu; orada boş dönüp arayüzün
    seçili para birimini göstermesine bırakıyoruz.
    """
    toplam: dict[tuple, float] = {}
    paralar: dict[tuple, set] = {}
    yollar = _row_paths(valid, levels)
    for (yol, _), (_, satir) in zip(yollar, valid.iterrows()):
        deger = satir.get("Değer (kendi)")
        para = str(satir.get("Para Birimi") or "TRY")
        if deger is None or deger != deger:
            continue
        for derinlik in range(1, len(yol) + 1):
            anahtar = yol[:derinlik]
            toplam[anahtar] = toplam.get(anahtar, 0.0) + float(deger)
            paralar.setdefault(anahtar, set()).add(para)

    out: dict[tuple, str] = {}
    for anahtar, tutar in toplam.items():
        birimler = paralar.get(anahtar, set())
        if len(birimler) != 1:
            continue
        para = next(iter(birimler))
        isaret = CURRENCY_SYMBOLS.get(para, para + " ")
        out[anahtar] = f"{isaret}{tutar:,.0f}"
    return out


def treemap_data(df: pd.DataFrame, levels: list[str],
                 change_col: str | None = None) -> dict[str, Any]:
    """
    Treemap için ids/labels/parents/values. Sankey ile aynı hiyerarşiyi kullanır
    ama büyüklüğü alan olarak gösterdiği için 30+ pozisyonda çok daha okunaklıdır.

    `change_col` verilirse kutular ANA SINIF rengiyle değil, o sütundaki yüzde
    değişimle (ısı haritası) boyanır. Alan yine değeri gösterir; renk hareketi
    gösterir — iki farklı bilgi, iki farklı kanal.
    """
    empty = {"ids": [], "labels": [], "parents": [], "values": [],
             "colors": [], "paths": [], "changes": [], "text_colors": [],
             "natives": []}
    if df.empty or "Değer (TRY)" not in df.columns or not levels:
        return empty
    valid = df[df["Değer (TRY)"].notna() & (df["Değer (TRY)"] > 0)]
    if valid.empty:
        return empty

    totals, group = _hierarchy_nodes(valid, levels)
    top_colors = color_map(list(allocation(valid, levels[0])[levels[0]].astype(str)))
    max_depth = max((len(k) for k in totals), default=1)

    isi = (_node_changes(valid, levels, change_col)
           if change_col and change_col in valid.columns else {})
    dogal = _node_native(valid, levels)

    ids: list[str] = []
    labels: list[str] = []
    parents: list[str] = []
    values: list[float] = []
    colors: list[str] = []
    changes: list[float | None] = []
    text_colors: list[str] = []
    natives: list[str] = []

    for key in _sorted_keys(totals):
        ids.append(" › ".join(key))
        labels.append(key[-1])
        parents.append(" › ".join(key[:-1]) if len(key) > 1 else "")
        values.append(totals[key])
        natives.append(dogal.get(key, ""))
        if change_col:
            pct = isi.get(key)
            renk = heat_color(pct)
            colors.append(renk)
            changes.append(pct)
            text_colors.append(text_on(renk))
        else:
            # Derinleştikçe saydamlaşan dolgu: iç içe kutular birbirinden ayrışır
            alpha = 0.88 - 0.16 * min(len(key) - 1, max(max_depth - 1, 1))
            colors.append(_rgba(top_colors.get(group[key], OTHER_COLOR),
                                max(alpha, 0.34)))
            changes.append(None)
            text_colors.append("#ececf1")

    return {"ids": ids, "labels": labels, "parents": parents,
            "values": values, "colors": colors, "paths": ids,
            "changes": changes, "text_colors": text_colors,
            "natives": natives}


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def merge_position(assets: list[dict[str, Any]], new: dict[str, Any],
                   mode: str = "replace") -> list[dict[str, Any]]:
    """
    Varlık ekler veya günceller.
      mode="replace" : mevcut satırı olduğu gibi değiştirir
      mode="add"     : adet ekler ve ağırlıklı ortalama maliyeti yeniden hesaplar
    Eski kodda her ekleme mevcut pozisyonu eziyordu; ikinci alım yaptığınızda
    ortalama maliyetiniz kayboluyordu.
    """

    out = [dict(a) for a in assets]
    key = asset_key(new)
    idx = next((i for i, a in enumerate(out) if asset_key(a) == key), None)

    if idx is None:
        out.append(dict(new))
        return out

    if mode == "add":
        old = out[idx]
        q_old, c_old = float(old.get("qty") or 0), float(old.get("avg_cost") or 0)
        q_new, c_new = float(new.get("qty") or 0), float(new.get("avg_cost") or 0)
        q_tot = q_old + q_new
        merged = dict(old)
        merged.update({k: v for k, v in new.items()
                       if k not in ("qty", "avg_cost")})
        merged["qty"] = q_tot
        merged["avg_cost"] = ((q_old * c_old + q_new * c_new) / q_tot) if q_tot else 0.0
        out[idx] = merged
    else:
        out[idx] = dict(new)
    return out

# ==========================================================================
# KAYNAK: portfolio/editing.py
# ==========================================================================


from typing import Any

import pandas as pd


SOURCE_LABELS: dict[str, str] = {
    SRC_YAHOO: "Yahoo Finance",
    SRC_TEFAS: "TEFAS",
    SRC_GOLD: "Altın (ons)",
    SRC_SILVER: "Gümüş (ons)",
    SRC_CASH: "Nakit",
    SRC_MANUAL: "Elle fiyat",
}
VAL_LABELS: dict[str, str] = {
    VAL_QTY: "Canlı (adet × fiyat)",
    VAL_VALUE: "Diğer (son değer)",
}


def derive_valuation(qty: float, source: str) -> str:
    """
    Değerleme modunu ADET alanından türetir — kullanıcı ayrıca seçmek zorunda
    kalmasın diye:
      * adet girilmişse  -> canlı fiyatla değerlenir
      * adet boş/0 ise   -> "Diğer" sayılır, son girilen toplam değer kullanılır
    Fiyat kaynağı "elle fiyat" olan satırlar her zaman "Diğer"dir.
    """
    if source == SRC_MANUAL:
        return VAL_VALUE
    return VAL_QTY if (qty or 0) > 0 else VAL_VALUE
CURRENCIES = ["TRY", "USD", "EUR", "HKD"]

# Altın/gümüş dışındaki satırlarda "Birim" boş kalır; tabloda "Yok" görünür.
NO_UNIT = "Yok"
UNIT_OPTIONS = [NO_UNIT] + list(METAL_UNITS)

EDIT_COLS = ["Sembol", "Fiyat Sembolü", "Kaynak", "Değerleme", "Para Birimi",
             "Ana Sınıf", "Alt Sınıf", "Sektör", "Hesap", "Birim",
             "Adet", "Birim Maliyet", "Maliyet Para Birimi", "Son Değer",
             "Notlar"]

_SRC_REV = {v: k for k, v in SOURCE_LABELS.items()}
_VAL_REV = {v: k for k, v in VAL_LABELS.items()}


def assets_to_editor(items: list[dict[str, Any]]) -> pd.DataFrame:
    """Varlık listesini düzenlenebilir tabloya çevirir."""
    return pd.DataFrame([{
        "Sembol": a.get("display") or a["symbol"],
        "Fiyat Sembolü": a["symbol"],
        "Kaynak": SOURCE_LABELS.get(a.get("source", SRC_YAHOO),
                                    SOURCE_LABELS[SRC_YAHOO]),
        "Değerleme": VAL_LABELS.get(a.get("valuation", VAL_QTY), VAL_LABELS[VAL_QTY]),
        "Para Birimi": a.get("currency", "TRY"),
        "Ana Sınıf": a.get("ana_sinif", "Diğer"),
        "Alt Sınıf": a.get("alt_sinif", ""),
        "Sektör": a.get("sektor", ""),
        "Hesap": a.get("hesap", ""),
        "Birim": a.get("unit") or NO_UNIT,
        "Adet": float(a.get("qty") or 0.0),
        "Birim Maliyet": float(a.get("avg_cost") or 0.0),
        # Maliyet fiyattan farklı bir para biriminde olabilir: BIST hissesinin
        # fiyatı TRY iken maliyeti dolar bazlı bir rapordan gelmiş olabilir.
        "Maliyet Para Birimi": a.get("cost_currency") or a.get("currency", "TRY"),
        "Son Değer": float(a.get("manual_price") or 0.0),
        "Notlar": a.get("notlar", ""),
    } for a in items], columns=EDIT_COLS)


def editor_to_assets(edited: pd.DataFrame) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Düzenlenmiş tabloyu varlık listesine çevirir.

    - Tamamen boş satırlar atlanır (kullanıcı satır ekleyip vazgeçmiş olabilir).
    - Aynı sembol + hesap ikilisi tekrar ederse ikinci satır alınmaz ve uyarılır;
      aksi halde sessizce veri kaybı olurdu.
    - Değerleme moduyla tutarsız satırlar (adet 0 ama canlı mod gibi) rapor edilir.
    """
    out: list[dict[str, Any]] = []
    problems: list[str] = []
    seen: set[str] = set()

    for pos, (_, row) in enumerate(edited.iterrows(), start=1):
        sym = str(row.get("Fiyat Sembolü") or "").strip()
        disp = str(row.get("Sembol") or "").strip()
        if not sym and not disp:
            continue
        if not sym:
            sym = disp.upper()

        unit_raw = str(row.get("Birim") or "").strip().upper()
        source = _SRC_REV.get(str(row.get("Kaynak")), SRC_YAHOO)
        qty = float(row.get("Adet") or 0.0)
        sym = resolve_symbol(sym, source)      # ASELS -> ASELS.IS, SOL -> SOL-USD

        # Sınıf alanları boşsa sembolden otomatik doldur — yeni satır eklemek
        # için sadece sembol + kaynak yazmak yeterli olsun.
        auto = classify_symbol(sym, source)
        ana = str(row.get("Ana Sınıf") or "").strip()
        alt = str(row.get("Alt Sınıf") or "").strip()
        sek = str(row.get("Sektör") or "").strip()

        rec = normalize_asset({
            "symbol": sym,
            "display": disp or sym,
            "source": source,
            "valuation": derive_valuation(qty, source),
            "currency": str(row.get("Para Birimi") or "TRY").upper(),
            "ana_sinif": ana or auto["ana_sinif"],
            "alt_sinif": alt or auto["alt_sinif"],
            "sektor": sek or auto["sektor"],
            "hesap": str(row.get("Hesap") or "").strip(),
            "unit": unit_raw if unit_raw in METAL_UNITS else None,
            "qty": qty,
            "avg_cost": float(row.get("Birim Maliyet") or 0.0),
            "cost_currency": (str(row.get("Maliyet Para Birimi") or "").strip().upper()
                              or str(row.get("Para Birimi") or "TRY").upper()),
            "manual_price": float(row.get("Son Değer") or 0.0) or None,
            "notlar": str(row.get("Notlar") or ""),
        })

        key = asset_key(rec)
        if key in seen:
            problems.append(
                f"Satır {pos}: '{rec['symbol']}' + hesap '{rec['hesap']}' ikilisi "
                f"zaten var; bu satır alınmadı. Ayırmak için 'Hesap' sütununu "
                f"farklılaştırın.")
            continue
        seen.add(key)

        if rec["valuation"] == VAL_VALUE and not rec.get("manual_price"):
            problems.append(
                f"Satır {pos}: '{rec['display']}' için ne adet ne de son değer "
                f"girilmiş — portföyde 0 TL görünecek. Adet yazarsanız canlı "
                f"fiyatlanır, 'Son Değer' yazarsanız 'Diğer' olarak işlenir.")
        out.append(rec)

    return out, problems

# ==========================================================================
# KAYNAK: portfolio/history.py
# ==========================================================================


import datetime as dt
from dataclasses import dataclass
from typing import Any, Iterable

# Ana ekranda gösterilen dönemler: (etiket, gün sayısı | None = en baştan)
PERIODS: list[tuple[str, int | None]] = [
    ("Günlük", 1),
    ("Haftalık", 7),
    ("Aylık", 30),
    ("3 Aylık", 90),
    ("6 Aylık", 180),
    ("Yıllık", 365),
    ("Başlangıçtan", None),
]


@dataclass
class Change:
    label: str
    start_date: str
    end_date: str
    start_value: float
    end_value: float

    @property
    def delta(self) -> float:
        return self.end_value - self.start_value

    @property
    def pct(self) -> float:
        # Başlangıç değeri sıfır ya da negatifse yüzde anlamsızdır
        # (portföyün ilk günlerinde bakiye eksi olabiliyor). Uydurma bir
        # sayı yazmak yerine boş bırakıyoruz.
        if self.start_value <= 0:
            return float("nan")
        return self.delta / self.start_value * 100.0

    @property
    def pct_display(self) -> float:
        """
        Tabloda gösterilecek yüzde.

        Bu seri NET VARLIK serisidir; yatırım getirisi değil, para yatırma ve
        çekmeleri de içerir. Başlangıç değeri bugünkünün %1'inden küçükse
        (portföyün kurulma dönemi) yüzde binlerce puana çıkıyor ve hiçbir şey
        anlatmıyor — o durumda yüzde yerine sadece TL değişimi gösterilir.
        """
        if self.start_value <= 0 or self.start_value < abs(self.end_value) * 0.01:
            return float("nan")
        return self.pct

    @property
    def days(self) -> int:
        try:
            a = dt.date.fromisoformat(self.start_date)
            b = dt.date.fromisoformat(self.end_date)
            return (b - a).days
        except ValueError:
            return 0


def _key(row: dict[str, Any]) -> str:
    return str(row.get("date", ""))


def normalize_history(rows: Iterable[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Tarihe göre sıralar, aynı güne ait tekrarları sonuncusuyla teker."""
    by_date: dict[str, dict[str, Any]] = {}
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        date = _key(row)[:10]
        if not date:
            continue
        try:
            dt.date.fromisoformat(date)
        except ValueError:
            continue
        by_date[date] = {
            "date": date,
            "total_try": float(row.get("total_try") or 0.0),
            "usdtry": (float(row["usdtry"]) if row.get("usdtry") else None),
            "by_class": {str(k): float(v)
                         for k, v in (row.get("by_class") or {}).items()},
        }
    return [by_date[d] for d in sorted(by_date)]


def upsert_today(history: list[dict[str, Any]], total_try: float,
                 usdtry: float | None, by_class: dict[str, float],
                 today: str | None = None) -> tuple[list[dict[str, Any]], bool]:
    """
    Bugünün kaydını ekler ya da günceller.

    Döner: (yeni tarihçe, değişti mi). Aynı gün içinde tekrar açıldığında
    değer anlamlı biçimde değişmediyse yazma yapılmaz — GitHub'a gereksiz
    commit atılmasın diye.
    """
    today = today or dt.date.today().isoformat()
    rows = normalize_history(history)
    entry = {
        "date": today,
        "total_try": float(total_try),
        "usdtry": float(usdtry) if usdtry else None,
        "by_class": {str(k): float(v) for k, v in by_class.items()},
    }

    for i, row in enumerate(rows):
        if row["date"] == today:
            # 1 TL'den küçük fark için commit atma
            if abs(row["total_try"] - entry["total_try"]) < 1.0:
                return rows, False
            rows[i] = entry
            return rows, True

    rows.append(entry)
    rows.sort(key=lambda r: r["date"])
    return rows, True


def _value_on_or_before(rows: list[dict[str, Any]], target: dt.date) -> dict | None:
    """Verilen tarihteki ya da ondan önceki en yakın kayıt."""
    chosen = None
    for row in rows:
        if dt.date.fromisoformat(row["date"]) <= target:
            chosen = row
        else:
            break
    return chosen


def period_changes(history: list[dict[str, Any]],
                   periods: list[tuple[str, int | None]] | None = None
                   ) -> list[Change]:
    """
    Her dönem için başlangıç/bitiş değerini ve değişimi hesaplar.

    Kayıt her gün olmayabilir (uygulama açılmadığı günler); bu yüzden hedef
    tarihe eşit ya da ondan ÖNCEKİ en yakın kayıt alınır. Dönemi karşılayacak
    kadar geçmiş yoksa o dönem atlanır — uydurma sayı üretilmez.
    """
    rows = normalize_history(history)
    if len(rows) < 2:
        return []

    last = rows[-1]
    end_date = dt.date.fromisoformat(last["date"])
    first_date = dt.date.fromisoformat(rows[0]["date"])
    out: list[Change] = []

    for label, days in (periods or PERIODS):
        if days is None:
            # "Başlangıçtan": portföyün gerçekten pozitife geçtiği ilk gün.
            # İlk kayıtlar eksi bakiye olabiliyor ve yüzdeyi anlamsız yapıyor.
            start = next((r for r in rows if r["total_try"] > 0), rows[0])
        else:
            target = end_date - dt.timedelta(days=days)
            if target < first_date:
                continue          # bu dönemi kapsayacak veri yok
            start = _value_on_or_before(rows, target)
        if not start or start["date"] == last["date"]:
            continue
        out.append(Change(label, start["date"], last["date"],
                          start["total_try"], last["total_try"]))
    return out


def series(history: list[dict[str, Any]], days: int | None) -> list[dict[str, Any]]:
    """Grafik için son N günlük dilim (None = tamamı)."""
    rows = normalize_history(history)
    if days is None or not rows:
        return rows
    end = dt.date.fromisoformat(rows[-1]["date"])
    cutoff = end - dt.timedelta(days=days)
    sliced = [r for r in rows if dt.date.fromisoformat(r["date"]) >= cutoff]
    # Dilimin başında referans noktası kalsın diye bir önceki kaydı da al
    before = _value_on_or_before(rows, cutoff - dt.timedelta(days=1))
    if before and (not sliced or sliced[0]["date"] != before["date"]):
        sliced = [before] + sliced
    return sliced


def class_series(history: list[dict[str, Any]], days: int | None) -> tuple[list[str], dict[str, list[float]]]:
    """Varlık sınıfı bazında yığılmış alan grafiği için seri."""
    rows = series(history, days)
    dates = [r["date"] for r in rows]
    classes: list[str] = []
    for r in rows:
        for k in r["by_class"]:
            if k not in classes:
                classes.append(k)
    # Son kayıttaki büyüklüğe göre sırala
    if rows:
        classes.sort(key=lambda c: rows[-1]["by_class"].get(c, 0.0), reverse=True)
    return dates, {c: [r["by_class"].get(c, 0.0) for r in rows] for c in classes}

# ==========================================================================
# KAYNAK: portfolio/importers.py
# ==========================================================================


import io
import json
import math
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

import pandas as pd


# --------------------------------------------------------------------------
# BİRLEŞTİRME KİPLERİ
# --------------------------------------------------------------------------
MODE_MERGE = "birlestir"        # eşleşeni güncelle, yeniyi ekle, gerisine dokunma
MODE_ACCOUNT = "hesap_yenile"   # dosyadaki HESAPLARI tamamen dosyadaki hâline getir
MODE_REPLACE = "tam_degistir"   # portföyü tamamen dosyadaki hâle getir

MODE_LABELS = {
    MODE_MERGE: "Birleştir — eşleşenleri güncelle, yenileri ekle, kalanına dokunma",
    MODE_ACCOUNT: "Hesabı yenile — dosyadaki hesapların ESKİ satırlarını sil, dosyadakini yaz",
    MODE_REPLACE: "Tamamen değiştir — portföyü dosyadaki hâle getir (en riskli)",
}

# --------------------------------------------------------------------------
# BİÇİMLER
# --------------------------------------------------------------------------
FMT_AETHER = "aether"
FMT_MSP = "msp"
FMT_BLUECOINS = "bluecoins"
FMT_JSON = "json"

FORMAT_LABELS = {
    FMT_AETHER: "AETHER tablosu (sembol / adet / maliyet / hesap)",
    FMT_MSP: "MyStocksPortfolio dışa aktarımı",
    FMT_BLUECOINS: "Bluecoins hesap dökümü (CSV)",
    FMT_JSON: "AETHER my_assets.json",
}


class ImportError_(ValueError):
    """İçe aktarma hatası (yerleşik ImportError ile karışmasın diye alt çizgili)."""


# --------------------------------------------------------------------------
# BAŞLIK EŞLEŞTİRME
# Türkçe/İngilizce, büyük/küçük, aksanlı/aksansız hepsini kabul eder.
# --------------------------------------------------------------------------
def _slug(text: Any) -> str:
    s = unicodedata.normalize("NFKD", str(text or ""))
    s = s.replace("ı", "i").replace("İ", "i").replace("ş", "s").replace("Ş", "s")
    s = s.replace("ğ", "g").replace("Ğ", "g").replace("ü", "u").replace("Ü", "u")
    s = s.replace("ö", "o").replace("Ö", "o").replace("ç", "c").replace("Ç", "c")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", s.lower())


# alan -> kabul edilen başlıklar (slug hâlinde)
FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "symbol":    ("sembol", "symbol", "kod", "code", "ticker", "fonkodu", "hissekodu"),
    "qty":       ("adet", "qty", "quantity", "shares", "lot", "miktar", "adetlot",
                  "birimsayisi", "pay"),
    "avg_cost":  ("maliyet", "ortalamamaliyet", "ortmaliyet", "avgcost", "cost",
                  "costbasis", "birimmaliyet", "alisfiyati", "avgprice"),
    "hesap":     ("hesap", "account", "kurum", "banka", "portfoy", "portfolio",
                  "broker"),
    "currency":  ("parabirimi", "currency", "kur", "doviz", "ccy"),
    # Maliyetin para birimi fiyatınkinden farklı olabilir (BIST hissesi TRY
    # fiyatlanır ama maliyeti USD raporundan gelmiş olabilir). Ayrı tutulunca
    # dondurulmuş kur saklamak gerekmez; uygulama canlı kurla çevirir.
    "cost_currency": ("maliyetparabirimi", "maliyetkuru", "costcurrency",
                      "costccy", "maliyetdovizi"),
    "source":    ("kaynak", "source", "fiyatkaynagi"),
    "ana_sinif": ("anasinif", "anaclass", "assetclass", "sinif", "class"),
    "alt_sinif": ("altsinif", "altclass", "subclass"),
    "sektor":    ("sektor", "sector"),
    "unit":      ("birim", "unit"),
    "notlar":    ("notlar", "not", "notes", "note", "aciklama", "description"),
    "deger":     ("deger", "value", "tutar", "marketvalue", "guncel", "guncledeger",
                  "toplamdeger"),
}


def _column_map(df: pd.DataFrame) -> dict[str, str]:
    """DataFrame başlıklarını iç alan adlarına eşler."""
    out: dict[str, str] = {}
    for col in df.columns:
        s = _slug(col)
        for field_name, aliases in FIELD_ALIASES.items():
            if field_name in out:
                continue
            if s in aliases:
                out[field_name] = col
                break
    return out


# --------------------------------------------------------------------------
# SAYI OKUMA — "1.234,56" / "1,234.56" / "$1 234" hepsini çözer
# --------------------------------------------------------------------------
_NUM_CLEAN = re.compile(r"[^\d,.\-]")


def parse_number(raw: Any) -> float:
    """Türkçe ve İngilizce sayı biçimlerinin ikisini de okur."""
    if raw is None:
        return 0.0
    if isinstance(raw, (int, float)):
        return 0.0 if (isinstance(raw, float) and math.isnan(raw)) else float(raw)

    text = _NUM_CLEAN.sub("", str(raw).strip())
    if not text or text in {"-", ".", ","}:
        return 0.0

    has_dot, has_comma = "." in text, "," in text
    if has_dot and has_comma:
        # Son görülen ayırıcı ondalıktır: "1.234,56" -> virgül, "1,234.56" -> nokta
        ondalik = "," if text.rfind(",") > text.rfind(".") else "."
        binlik = "." if ondalik == "," else ","
        text = text.replace(binlik, "").replace(ondalik, ".")
    elif has_comma:
        # Tek virgül: sağında 3 hane ve başka virgül yoksa binlik olabilir.
        parca = text.split(",")
        text = ("".join(parca) if len(parca[-1]) == 3 and len(parca) > 2
                else text.replace(",", "."))
    elif has_dot:
        parca = text.split(".")
        if len(parca) > 2 and all(len(p) == 3 for p in parca[1:]):
            text = "".join(parca)          # 1.234.567
    try:
        return float(text)
    except ValueError:
        return 0.0


# --------------------------------------------------------------------------
# DOSYA OKUMA
# --------------------------------------------------------------------------
def read_any(data: bytes, filename: str = "") -> pd.DataFrame | list[dict[str, Any]]:
    """Yüklenen baytları DataFrame'e (veya JSON listesine) çevirir."""
    ad = (filename or "").lower()

    if ad.endswith(".json") or data[:1].strip() in (b"[", b"{"):
        try:
            veri = json.loads(data.decode("utf-8"))
        except Exception as exc:
            raise ImportError_(f"JSON okunamadı: {exc}") from exc
        if isinstance(veri, dict):
            veri = veri.get("assets") or veri.get("varliklar") or []
        if not isinstance(veri, list):
            raise ImportError_("JSON bir varlık listesi içermiyor.")
        return veri

    if ad.endswith((".xlsx", ".xlsm", ".xls")):
        try:
            return pd.read_excel(io.BytesIO(data))
        except Exception as exc:
            raise ImportError_(f"Excel okunamadı: {exc}") from exc

    metin = data.decode("utf-8-sig", errors="replace")
    for ayirici in (None, ";", ",", "\t", "|"):
        try:
            df = pd.read_csv(io.StringIO(metin), sep=ayirici,
                             engine="python" if ayirici is None else "c")
            if df.shape[1] > 1:
                return df
        except Exception:
            continue
    raise ImportError_("Dosya CSV/Excel/JSON olarak okunamadı.")


def sniff(veri: pd.DataFrame | list[dict[str, Any]]) -> str:
    """Biçimi tahmin eder."""
    if isinstance(veri, list):
        return FMT_JSON

    sluglar = {_slug(c) for c in veri.columns}
    if {"symbol", "sembol"} & sluglar and {"portfolio", "portfoy"} & sluglar:
        return FMT_MSP
    if {"account", "hesap"} & sluglar and not ({"sembol", "symbol"} & sluglar):
        return FMT_BLUECOINS
    return FMT_AETHER


# --------------------------------------------------------------------------
# AYRIŞTIRMA
# --------------------------------------------------------------------------
def _base_record(sembol: str) -> dict[str, Any]:
    """Sembolden sınıflandırmayı otomatik doldurur.

    DİKKAT: auto_fill_asset üç harfli her kodu TEFAS fonu sayar; bu doğru
    davranış (fon kodları üç harflidir) ama ABD sembolleriyle çakışır. Bu
    yüzden çağıran taraf 'kaynak' sütununu verebilir ve o her zaman kazanır.
    """
    try:
        return auto_fill_asset(sembol)
    except ValueError as exc:
        raise ImportError_(f"Geçersiz sembol: {sembol!r}") from exc


def parse_table(df: pd.DataFrame, fmt: str = FMT_AETHER,
                varsayilan_hesap: str = "") -> list[dict[str, Any]]:
    """Tabloyu normalize edilmiş varlık kayıtlarına çevirir."""
    if df is None or df.empty:
        raise ImportError_("Dosya boş.")

    esle = _column_map(df)
    if "symbol" not in esle:
        raise ImportError_(
            "Zorunlu 'Sembol' sütunu bulunamadı. Kabul edilen başlıklar: "
            + ", ".join(FIELD_ALIASES["symbol"])
        )

    kayitlar: list[dict[str, Any]] = []
    for _, satir in df.iterrows():
        ham = str(satir[esle["symbol"]] or "").strip()
        if not ham or ham.lower() in {"nan", "none", "-"}:
            continue

        adet = parse_number(satir[esle["qty"]]) if "qty" in esle else 0.0
        deger = parse_number(satir[esle["deger"]]) if "deger" in esle else 0.0
        maliyet = parse_number(satir[esle["avg_cost"]]) if "avg_cost" in esle else 0.0

        # Değeri ve adedi sıfır olan satırlar kapanmış pozisyondur, atlanır.
        if adet == 0 and deger == 0:
            continue

        kayit = dict(_base_record(ham))
        kayit.pop("guessed", None)
        kayit["qty"] = adet
        kayit["avg_cost"] = maliyet
        kayit["hesap"] = (str(satir[esle["hesap"]]).strip()
                          if "hesap" in esle and pd.notna(satir[esle["hesap"]])
                          else varsayilan_hesap)

        # Dosyada açıkça verilen alanlar otomatik tahmini EZER.
        verilen: set[str] = set()
        for alan in ("currency", "cost_currency", "source", "ana_sinif",
                     "alt_sinif", "sektor", "unit", "notlar"):
            if alan in esle and pd.notna(satir[esle[alan]]):
                deger_ = str(satir[esle[alan]]).strip()
                if deger_:
                    kayit[alan] = deger_
                    verilen.add(alan)

        # Satırda maliyet para birimi YAZILMAMIŞSA maliyet, fiyatın para
        # biriminde sayılır. Sütunun varlığına değil HÜCRENİN doluluğuna
        # bakmak şart: sütun var ama hücre boşken otomatik tahminin para
        # birimi yapışık kalıyordu — "GCL" üç harfli olduğu için TEFAS fonu
        # sanılıp TRY, "0209.HK" ise ABD hissesi sanılıp USD maliyet alıyordu
        # ve ikisi de yanlış kurla çevriliyordu.
        if "cost_currency" not in verilen:
            kayit["cost_currency"] = kayit["currency"]

        if kayit.get("source") not in VALID_SOURCES:
            kayit["source"] = SRC_YAHOO
        if kayit.get("unit") in ("", "Yok", "yok", "-"):
            kayit["unit"] = None
        if kayit.get("unit") and kayit["unit"] not in METAL_UNITS:
            raise ImportError_(
                f"{ham}: bilinmeyen birim {kayit['unit']!r}. "
                f"Geçerli birimler: {', '.join(METAL_UNITS)}")

        # Adet yoksa ama toplam değer varsa: kova satırı
        if adet == 0 and deger > 0:
            kayit["valuation"] = VAL_VALUE
            kayit["manual_price"] = deger
            kayit["avg_cost"] = maliyet or deger
        else:
            kayit["valuation"] = VAL_VALUE if kayit["source"] == SRC_MANUAL else VAL_QTY

        kayitlar.append(normalize_asset(kayit))

    if not kayitlar:
        raise ImportError_("Dosyada içe aktarılacak satır bulunamadı "
                           "(adet ve değer sütunlarının ikisi de boş olabilir).")
    return kayitlar


def parse_json(veri: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Bir my_assets.json içeriğini doğrular ve normalize eder."""
    if not isinstance(veri, list):
        raise ImportError_("JSON bir liste olmalı.")
    out = []
    for i, ham in enumerate(veri):
        if not isinstance(ham, dict):
            raise ImportError_(f"{i}. kayıt sözlük değil.")
        if not str(ham.get("symbol", "")).strip():
            raise ImportError_(f"{i}. kaydın 'symbol' alanı boş.")
        out.append(normalize_asset(ham))
    if not out:
        raise ImportError_("JSON boş bir liste.")
    return out


def parse(veri: pd.DataFrame | list[dict[str, Any]], fmt: str | None = None,
          varsayilan_hesap: str = "") -> list[dict[str, Any]]:
    fmt = fmt or sniff(veri)
    if fmt == FMT_JSON or isinstance(veri, list):
        return parse_json(veri)          # type: ignore[arg-type]
    return parse_table(veri, fmt, varsayilan_hesap)


# --------------------------------------------------------------------------
# KARŞILAŞTIRMA
# --------------------------------------------------------------------------
# Karşılaştırmada bakılan alanlar (notlar kasten dışarıda: not değişikliği
# "güncellendi" saydırmasın).
COMPARE_FIELDS = ("qty", "avg_cost", "currency", "source", "ana_sinif",
                  "alt_sinif", "sektor", "unit", "valuation", "manual_price")


@dataclass
class Diff:
    eklenen: list[dict[str, Any]] = field(default_factory=list)
    guncellenen: list[tuple[dict[str, Any], dict[str, Any]]] = field(default_factory=list)
    silinen: list[dict[str, Any]] = field(default_factory=list)
    degismeyen: list[dict[str, Any]] = field(default_factory=list)

    @property
    def ozet(self) -> str:
        return (f"{len(self.eklenen)} eklenecek · "
                f"{len(self.guncellenen)} güncellenecek · "
                f"{len(self.silinen)} silinecek · "
                f"{len(self.degismeyen)} değişmeyecek")

    def bos_mu(self) -> bool:
        return not (self.eklenen or self.guncellenen or self.silinen)


def _degisen_alanlar(eski: dict[str, Any], yeni: dict[str, Any]) -> list[str]:
    farklar = []
    for alan in COMPARE_FIELDS:
        a, b = eski.get(alan), yeni.get(alan)
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            if not math.isclose(float(a), float(b), rel_tol=1e-9, abs_tol=1e-9):
                farklar.append(alan)
        elif (a or None) != (b or None):
            farklar.append(alan)
    return farklar


def diff(mevcut: list[dict[str, Any]], gelen: list[dict[str, Any]],
         mode: str = MODE_MERGE) -> Diff:
    """Uygulanmadan ÖNCE ne olacağını hesaplar."""
    if mode not in MODE_LABELS:
        raise ImportError_(f"Bilinmeyen kip: {mode}")

    eski_map = {asset_key(a): a for a in mevcut}
    yeni_map = {asset_key(a): a for a in gelen}
    gelen_hesaplar = {str(a.get("hesap", "")) for a in gelen}

    d = Diff()
    for anahtar, yeni in yeni_map.items():
        eski = eski_map.get(anahtar)
        if eski is None:
            d.eklenen.append(yeni)
        elif _degisen_alanlar(eski, yeni):
            d.guncellenen.append((eski, yeni))
        else:
            d.degismeyen.append(eski)

    for anahtar, eski in eski_map.items():
        if anahtar in yeni_map:
            continue
        if mode == MODE_REPLACE:
            d.silinen.append(eski)
        elif mode == MODE_ACCOUNT and str(eski.get("hesap", "")) in gelen_hesaplar:
            d.silinen.append(eski)
        else:
            d.degismeyen.append(eski)
    return d


def apply(mevcut: list[dict[str, Any]], gelen: list[dict[str, Any]],
          mode: str = MODE_MERGE) -> list[dict[str, Any]]:
    """diff() ile gösterileni fiilen uygular. Sıra korunur: önce mevcutlar."""
    d = diff(mevcut, gelen, mode)
    silinen_anahtarlar = {asset_key(a) for a in d.silinen}
    yeni_map = {asset_key(a): a for a in gelen}

    out: list[dict[str, Any]] = []
    goruldu: set[str] = set()
    for a in mevcut:
        anahtar = asset_key(a)
        if anahtar in silinen_anahtarlar:
            continue
        out.append(yeni_map.get(anahtar, a))
        goruldu.add(anahtar)
    for a in gelen:
        if asset_key(a) not in goruldu:
            out.append(a)
    return out


# --------------------------------------------------------------------------
# ARAYÜZ İÇİN TABLO GÖRÜNÜMÜ
# --------------------------------------------------------------------------
def diff_table(d: Diff) -> pd.DataFrame:
    """Diff'i kullanıcıya gösterilecek tek tabloya çevirir."""
    satirlar: list[dict[str, Any]] = []

    for a in d.eklenen:
        satirlar.append({
            "İşlem": "➕ eklenecek", "Sembol": a.get("display") or a["symbol"],
            "Hesap": a.get("hesap", ""), "Adet": a.get("qty"),
            "Maliyet": a.get("avg_cost"), "Değişen alan": "",
        })
    for eski, yeni in d.guncellenen:
        alanlar = _degisen_alanlar(eski, yeni)
        detay = ", ".join(
            f"{ad}: {eski.get(ad)!r} → {yeni.get(ad)!r}" for ad in alanlar[:3]
        ) + (" …" if len(alanlar) > 3 else "")
        satirlar.append({
            "İşlem": "✏️ güncellenecek", "Sembol": yeni.get("display") or yeni["symbol"],
            "Hesap": yeni.get("hesap", ""), "Adet": yeni.get("qty"),
            "Maliyet": yeni.get("avg_cost"), "Değişen alan": detay,
        })
    for a in d.silinen:
        satirlar.append({
            "İşlem": "🗑️ silinecek", "Sembol": a.get("display") or a["symbol"],
            "Hesap": a.get("hesap", ""), "Adet": a.get("qty"),
            "Maliyet": a.get("avg_cost"), "Değişen alan": "",
        })

    if not satirlar:
        return pd.DataFrame(columns=["İşlem", "Sembol", "Hesap", "Adet",
                                     "Maliyet", "Değişen alan"])
    return pd.DataFrame(satirlar)


def ornek_csv() -> str:
    """Kullanıcının indirip dolduracağı şablon."""
    return (
        "sembol,adet,maliyet,hesap,para_birimi,kaynak,ana_sinif,alt_sinif,sektor,birim,notlar\n"
        "THYAO.IS,1000,285.50,Midas,TRY,yahoo,Hisse Senedi,BIST,Havacılık,,\n"
        "NVDA,44,197.97,Midas,USD,yahoo,Hisse Senedi,ABD,Yarı İletken,,\n"
        "BTC-USD,1.2328,70179.67,Kripto,USD,yahoo,Kripto,Majör,L1 Zincir,,\n"
        "MAC,254292,0.589873,Yapı Kredi,TRY,tefas,Fon,TEFAS,Hisse Fonu,,\n"
        "ALTIN,135.37,6551.45,Vakıfbank,TRY,gold,Emtia,Altın,Fiziki Altın,GRAM,\n"
        "GUMUS,31252.46,87.61,Vakıfbank,TRY,silver,Emtia,Gümüş,Fiziki Gümüş,GRAM,\n"
        "NAKIT-USD,2111.91,1,İş Bankası,USD,cash,Nakit,Döviz,Dolar,,\n"
    )

# ==========================================================================
# KAYNAK: portfolio/insights.py
# ==========================================================================


import math
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

# --------------------------------------------------------------------------
# SEVİYELER
# --------------------------------------------------------------------------
KRITIK = "kritik"      # sayılar yanlış olabilir ya da tek kalemde aşırı risk
DIKKAT = "dikkat"      # bakılmaya değer
BILGI = "bilgi"        # nötr tespit
IYI = "iyi"            # olumlu tespit

SEVIYE_SIRA = {KRITIK: 0, DIKKAT: 1, BILGI: 2, IYI: 3}
SEVIYE_ETIKET = {KRITIK: "🔴 Kritik", DIKKAT: "🟠 Dikkat",
                 BILGI: "⚪ Bilgi", IYI: "🟢 İyi"}

EŞIKLER: dict[str, float] = {
    "tek_pozisyon_uyari": 15.0,     # tek pozisyon portföyün %'si
    "tek_pozisyon_kritik": 25.0,
    "tek_sinif_uyari": 45.0,        # tek ana sınıfın %'si
    "ilk5_uyari": 60.0,             # en büyük 5 pozisyonun toplam %'si
    "kucuk_pozisyon": 0.35,         # bu %'nin altı "kuyruk"
    "kuyruk_sayisi": 8,             # kaç kuyruk pozisyondan sonra uyarılır
    "nakit_yuksek": 20.0,
    "nakit_dusuk": 2.0,
    "borc_orani_uyari": 20.0,       # borç / varlık
    "buyuk_zarar": -35.0,           # tek pozisyonda K/Z %
    "buyuk_kar": 100.0,
}


@dataclass
class Finding:
    seviye: str
    baslik: str
    detay: str
    metrik: str = ""
    etiketler: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------
# YARDIMCILAR
# --------------------------------------------------------------------------
def _yuzde(deger: float, toplam: float) -> float:
    return (deger / toplam * 100.0) if toplam else float("nan")


def _fmt(sayi: float, basamak: int = 1) -> str:
    if sayi is None or sayi != sayi:
        return "—"
    return f"{sayi:,.{basamak}f}"


def hhi(agirliklar: list[float]) -> float:
    """
    Herfindahl-Hirschman yoğunlaşma endeksi (0-10.000).

    Ağırlıkların yüzde cinsinden KARELERİ toplamıdır. Eşit ağırlıklı N
    pozisyonda 10.000/N çıkar; yani 1/HHI*10.000 "etkin pozisyon sayısı"nı
    verir — 40 satırlık bir portföy aslında 6 pozisyon gibi davranıyorsa
    bunu ortalama ağırlığa bakarak göremezsiniz, HHI gösterir.
    """
    return sum(w * w for w in agirliklar if w == w)


def etkin_pozisyon_sayisi(agirliklar: list[float]) -> float:
    h = hhi(agirliklar)
    return (10_000.0 / h) if h > 0 else float("nan")


# --------------------------------------------------------------------------
# KURALLAR
# --------------------------------------------------------------------------
def _kural_yogunlasma(df: pd.DataFrame, toplam: float,
                      esik: dict[str, float]) -> list[Finding]:
    out: list[Finding] = []
    canli = df[df["Değer (TRY)"].notna() & (df["Değer (TRY)"] > 0)]
    if canli.empty:
        return out

    sirali = canli.sort_values("Değer (TRY)", ascending=False)
    agirliklar = [_yuzde(v, toplam) for v in sirali["Değer (TRY)"]]

    en_buyuk = sirali.iloc[0]
    w1 = agirliklar[0]
    if w1 >= esik["tek_pozisyon_kritik"]:
        out.append(Finding(
            KRITIK, f"{en_buyuk['Etiket']} tek başına portföyün %{_fmt(w1)}'i",
            "Tek bir pozisyonun bu ağırlıkta olması, portföyün getirisini büyük "
            "ölçüde o varlığın hareketine bağlar. Diğer bütün pozisyonların "
            "toplamı bu tek kalemin etkisini dengelemekte zorlanır.",
            f"%{_fmt(w1)}", ["yoğunlaşma"]))
    elif w1 >= esik["tek_pozisyon_uyari"]:
        out.append(Finding(
            DIKKAT, f"En büyük pozisyon: {en_buyuk['Etiket']} (%{_fmt(w1)})",
            "Portföyün altıda birinden fazlası tek bir varlıkta.",
            f"%{_fmt(w1)}", ["yoğunlaşma"]))

    ilk5 = sum(agirliklar[:5])
    if ilk5 >= esik["ilk5_uyari"]:
        adlar = ", ".join(str(x) for x in sirali["Etiket"].head(5))
        out.append(Finding(
            DIKKAT, f"En büyük 5 pozisyon portföyün %{_fmt(ilk5)}'i",
            f"{adlar}. Kalan {len(sirali) - 5} pozisyon toplamda "
            f"%{_fmt(100 - ilk5)} yer tutuyor.",
            f"%{_fmt(ilk5)}", ["yoğunlaşma"]))

    etkin = etkin_pozisyon_sayisi(agirliklar)
    out.append(Finding(
        BILGI, f"Etkin pozisyon sayısı: {_fmt(etkin)}",
        f"Portföyde {len(sirali)} satır var ama ağırlıklar eşit olmadığı için "
        f"çeşitlenme, eşit ağırlıklı {_fmt(etkin)} pozisyonluk bir portföye "
        f"denk düşüyor. (Herfindahl endeksi {_fmt(hhi(agirliklar), 0)}.)",
        f"{_fmt(etkin)} / {len(sirali)}", ["yoğunlaşma"]))

    # Kuyruk pozisyonlar
    kuyruk = [(e, w) for e, w in zip(sirali["Etiket"], agirliklar)
              if w < esik["kucuk_pozisyon"]]
    if len(kuyruk) >= esik["kuyruk_sayisi"]:
        pay = sum(w for _, w in kuyruk)
        out.append(Finding(
            BILGI, f"{len(kuyruk)} pozisyon portföyün yalnızca %{_fmt(pay)}'ini "
                   f"oluşturuyor",
            "Bu kadar küçük pozisyonlar portföyün getirisini pratikte "
            "etkilemez ama takip, komisyon ve vergi tarafında yük yaratır: "
            + ", ".join(str(e) for e, _ in kuyruk[:10])
            + (" …" if len(kuyruk) > 10 else ""),
            f"{len(kuyruk)} satır · %{_fmt(pay)}", ["kuyruk"]))
    return out


def _kural_sinif_dagilimi(df: pd.DataFrame, toplam: float,
                          esik: dict[str, float]) -> list[Finding]:
    out: list[Finding] = []
    if "Ana Sınıf" not in df.columns:
        return out
    grup = (df.groupby("Ana Sınıf")["Değer (TRY)"].sum(min_count=1)
              .dropna().sort_values(ascending=False))
    if grup.empty:
        return out

    for sinif, deger in grup.items():
        pay = _yuzde(deger, toplam)
        if sinif == "Nakit":
            if pay >= esik["nakit_yuksek"]:
                out.append(Finding(
                    DIKKAT, f"Nakit portföyün %{_fmt(pay)}'i",
                    "Nakit, enflasyonun altında getiri sağlarsa reel olarak "
                    "değer kaybeder. Bu oranın bilinçli bir tercih mi yoksa "
                    "birikmiş bakiye mi olduğu bakılmaya değer.",
                    f"%{_fmt(pay)}", ["dağılım"]))
            elif pay <= esik["nakit_dusuk"]:
                out.append(Finding(
                    BILGI, f"Nakit portföyün yalnızca %{_fmt(pay)}'i",
                    "Beklenmedik bir harcama ya da fırsat çıktığında pozisyon "
                    "satmak gerekir.", f"%{_fmt(pay)}", ["dağılım"]))
        elif pay >= esik["tek_sinif_uyari"]:
            out.append(Finding(
                DIKKAT, f"{sinif} portföyün %{_fmt(pay)}'i",
                f"Portföyün neredeyse yarısı tek bir varlık sınıfında. Bu "
                f"sınıfı etkileyen bir gelişme portföyün tamamını aynı yönde "
                f"hareket ettirir.", f"%{_fmt(pay)}", ["dağılım"]))

    dagilim = " · ".join(f"{s} %{_fmt(_yuzde(v, toplam))}"
                         for s, v in grup.items())
    out.append(Finding(BILGI, "Varlık sınıfı dağılımı", dagilim, "",
                       ["dağılım"]))
    return out


def _kural_para_birimi(df: pd.DataFrame, toplam: float) -> list[Finding]:
    out: list[Finding] = []
    if "Para Birimi" not in df.columns:
        return out
    grup = (df.groupby("Para Birimi")["Değer (TRY)"].sum(min_count=1)
              .dropna().sort_values(ascending=False))
    if grup.empty:
        return out

    try_pay = _yuzde(float(grup.get("TRY", 0.0)), toplam)
    doviz_pay = 100.0 - try_pay if try_pay == try_pay else float("nan")
    dagilim = " · ".join(f"{p} %{_fmt(_yuzde(v, toplam))}"
                         for p, v in grup.items())

    out.append(Finding(
        BILGI, f"Döviz cinsi varlıklar portföyün %{_fmt(doviz_pay)}'i",
        f"{dagilim}. Not: BIST hisseleri ve TL fonlar TRY sayılır; bunların "
        f"bir kısmı (yabancı teknoloji fonları, eurobond fonu, emtia fonları) "
        f"TL fiyatlansa da esasen döviz/emtia riski taşır, yani gerçek döviz "
        f"maruziyetiniz bu orandan yüksektir.",
        f"%{_fmt(doviz_pay)}", ["kur"]))
    return out


def _kural_veri_sagligi(df: pd.DataFrame, toplam: float) -> list[Finding]:
    """Sayıların GÜVENİLİRLİĞİ — yorumdan önce gelmesi gereken kontroller."""
    out: list[Finding] = []

    if "Fiyat OK" in df.columns:
        eksik = df[~df["Fiyat OK"]]
        if not eksik.empty:
            adlar = ", ".join(str(x) for x in eksik["Etiket"].head(10))
            out.append(Finding(
                KRITIK, f"{len(eksik)} varlığın fiyatı çekilemedi",
                f"Bu satırlar toplamlara DAHİL DEĞİL, yani portföy değeriniz "
                f"olduğundan düşük görünüyor: {adlar}"
                + (" …" if len(eksik) > 10 else ""),
                f"{len(eksik)} satır", ["veri"]))

    if "Değerleme" in df.columns:
        kova = df[df["Değerleme"] == "Diğer"]
        if not kova.empty:
            pay = _yuzde(float(kova["Değer (TRY)"].sum(skipna=True)), toplam)
            out.append(Finding(
                DIKKAT if pay >= 5 else BILGI,
                f"Portföyün %{_fmt(pay)}'i elle girilen tutarla değerleniyor",
                f"{len(kova)} satırda adet yok; değer en son yazdığınız tutarda "
                f"sabit duruyor ve piyasayla birlikte güncellenmiyor. Bu "
                f"satırlar eskidikçe portföy değeri gerçeklikten uzaklaşır.",
                f"%{_fmt(pay)}", ["veri"]))

    if {"Maliyet", "Adet"} <= set(df.columns):
        sifir = df[(df["Adet"] > 0) & (df["Maliyet"] <= 0)]
        if not sifir.empty:
            adlar = ", ".join(str(x) for x in sifir["Etiket"])
            out.append(Finding(
                DIKKAT, f"{len(sifir)} pozisyonun maliyeti sıfır: {adlar}",
                "Maliyet sıfırken kâr/zarar yüzdesi sonsuza gider ve portföy "
                "toplam K/Z'sini bozar. Gerçek maliyeti girmeden bu satırların "
                "getirisi okunamaz.", "", ["veri"]))

    if {"Para Birimi", "Maliyet Para Birimi"} <= set(df.columns):
        farkli = df[df["Para Birimi"] != df["Maliyet Para Birimi"]]
        if not farkli.empty:
            out.append(Finding(
                BILGI, f"{len(farkli)} satırda maliyet farklı para biriminde",
                "Fiyat bir para biriminde, maliyet başka birinde tutuluyor "
                "(ör. BIST hissesinin fiyatı TL, maliyeti USD). Çevrim her "
                "açılışta güncel kurla yapıldığı için bu satırların K/Z "
                "yüzdesi kur hareketiyle de değişir.",
                f"{len(farkli)} satır", ["veri"]))
    return out


def _kural_borc(df: pd.DataFrame, toplam: float,
                esik: dict[str, float]) -> list[Finding]:
    out: list[Finding] = []
    if "Ana Sınıf" not in df.columns:
        return out
    borc = df[df["Ana Sınıf"] == "Yükümlülük"]
    if borc.empty:
        return out
    tutar = abs(float(borc["Değer (TRY)"].sum(skipna=True)))
    oran = _yuzde(tutar, toplam)
    out.append(Finding(
        DIKKAT if oran >= esik["borc_orani_uyari"] else BILGI,
        f"Yükümlülükler varlıkların %{_fmt(oran)}'i",
        f"Toplam borç {_fmt(tutar, 0)} TL. Net değeriniz bu tutar düşülerek "
        f"hesaplanıyor.", f"%{_fmt(oran)}", ["borç"]))
    return out


def _kural_pozisyon_getirisi(df: pd.DataFrame,
                             esik: dict[str, float]) -> list[Finding]:
    out: list[Finding] = []
    if "K/Z %" not in df.columns:
        return out
    gecerli = df[df["K/Z %"].notna() & (df["Maliyet (TRY)"] > 0)]
    if gecerli.empty:
        return out

    zarar = gecerli[gecerli["K/Z %"] <= esik["buyuk_zarar"]].sort_values("K/Z %")
    if not zarar.empty:
        satirlar = ", ".join(f"{r['Etiket']} %{_fmt(r['K/Z %'])}"
                             for _, r in zarar.head(8).iterrows())
        out.append(Finding(
            DIKKAT, f"{len(zarar)} pozisyon maliyetinin %{abs(esik['buyuk_zarar']):.0f}"
                    f"'inden fazla altında",
            satirlar + (" …" if len(zarar) > 8 else ""),
            "", ["getiri"]))

    kar = gecerli[gecerli["K/Z %"] >= esik["buyuk_kar"]].sort_values(
        "K/Z %", ascending=False)
    if not kar.empty:
        satirlar = ", ".join(f"{r['Etiket']} +%{_fmt(r['K/Z %'])}"
                             for _, r in kar.head(8).iterrows())
        out.append(Finding(
            IYI, f"{len(kar)} pozisyon maliyetinin iki katından fazla",
            satirlar + (" …" if len(kar) > 8 else ""), "", ["getiri"]))
    return out


def _kural_ayni_varlik(df: pd.DataFrame, toplam: float) -> list[Finding]:
    """
    Aynı varlığın farklı hesaplardaki parçaları tek tek küçük görünür ama
    TOPLAM maruziyet büyük olabilir — yoğunlaşma tam olarak burada gizlenir.
    """
    out: list[Finding] = []
    if "Yahoo Sembol" not in df.columns:
        return out
    grup = df.groupby("Yahoo Sembol").agg(
        deger=("Değer (TRY)", "sum"), adet=("Yahoo Sembol", "size"))
    coklu = grup[grup["adet"] > 1].sort_values("deger", ascending=False)
    if coklu.empty:
        return out
    satirlar = ", ".join(
        f"{sym} ({int(r['adet'])} hesap, %{_fmt(_yuzde(r['deger'], toplam))})"
        for sym, r in coklu.head(6).iterrows())
    out.append(Finding(
        BILGI, f"{len(coklu)} varlık birden fazla hesapta duruyor",
        f"Tek tek bakıldığında küçük görünen bu satırların toplam maruziyeti "
        f"daha büyük: {satirlar}" + (" …" if len(coklu) > 6 else ""),
        "", ["yoğunlaşma"]))
    return out


def _kural_donem_hareketi(df: pd.DataFrame,
                          sutun: str = "1 Ay %") -> list[Finding]:
    out: list[Finding] = []
    if sutun not in df.columns:
        return out
    gecerli = df[df[sutun].notna() & (df["Değer (TRY)"] > 0)]
    if len(gecerli) < 3:
        return out

    agirlikli = ((gecerli[sutun] * gecerli["Değer (TRY)"]).sum()
                 / gecerli["Değer (TRY)"].sum())
    sirali = gecerli.sort_values(sutun, ascending=False)
    en_iyi = ", ".join(f"{r['Etiket']} %{_fmt(r[sutun])}"
                       for _, r in sirali.head(3).iterrows())
    en_kotu = ", ".join(f"{r['Etiket']} %{_fmt(r[sutun])}"
                        for _, r in sirali.tail(3).iloc[::-1].iterrows())
    out.append(Finding(
        BILGI, f"Son 1 ayda portföy %{_fmt(agirlikli)} hareket etti",
        f"En çok yükselen: {en_iyi}. En çok gerileyen: {en_kotu}. "
        f"(Fiyatı ve geçmişi çekilebilen {len(gecerli)} pozisyon üzerinden, "
        f"değere göre ağırlıklı.)",
        f"%{_fmt(agirlikli)}", ["hareket"]))
    return out


# --------------------------------------------------------------------------
# ANA GİRİŞ
# --------------------------------------------------------------------------
KURALLAR = (_kural_veri_sagligi, _kural_yogunlasma, _kural_sinif_dagilimi,
            _kural_para_birimi, _kural_ayni_varlik, _kural_borc,
            _kural_pozisyon_getirisi, _kural_donem_hareketi)


def analyze(df: pd.DataFrame,
            esik: dict[str, float] | None = None) -> list[Finding]:
    """Tabloyu tarar, bulguları önem sırasına dizilmiş olarak döndürür."""
    if df is None or df.empty or "Değer (TRY)" not in df.columns:
        return []
    esik = {**EŞIKLER, **(esik or {})}

    varlik = df[df["Ana Sınıf"] != "Yükümlülük"] if "Ana Sınıf" in df.columns else df
    toplam = float(varlik["Değer (TRY)"].sum(skipna=True))
    if not toplam or toplam != toplam or toplam <= 0:
        return []

    bulgular: list[Finding] = []
    for kural in KURALLAR:
        try:
            if kural in (_kural_pozisyon_getirisi,):
                bulgular.extend(kural(varlik, esik))
            elif kural in (_kural_para_birimi, _kural_ayni_varlik):
                bulgular.extend(kural(varlik, toplam))
            elif kural is _kural_donem_hareketi:
                bulgular.extend(kural(varlik))
            elif kural is _kural_veri_sagligi:
                bulgular.extend(kural(df, toplam))
            else:
                bulgular.extend(kural(varlik if kural is not _kural_borc else df,
                                      toplam, esik))
        except Exception:                                   # noqa: BLE001
            # Tek bir kuralın patlaması bütün analizi düşürmesin.
            continue

    bulgular.sort(key=lambda f: SEVIYE_SIRA.get(f.seviye, 9))
    return bulgular


def ozet_sayilar(df: pd.DataFrame) -> dict[str, float]:
    """Analiz sekmesinin üst şeridi için birkaç tek sayı."""
    bos = {"pozisyon": 0, "etkin": float("nan"), "hhi": float("nan"),
           "ilk5": float("nan"), "doviz_pay": float("nan")}
    if df is None or df.empty or "Değer (TRY)" not in df.columns:
        return bos
    varlik = df[df["Ana Sınıf"] != "Yükümlülük"] if "Ana Sınıf" in df.columns else df
    canli = varlik[varlik["Değer (TRY)"].notna() & (varlik["Değer (TRY)"] > 0)]
    toplam = float(canli["Değer (TRY)"].sum(skipna=True))
    if not toplam:
        return bos

    agirliklar = sorted((_yuzde(v, toplam) for v in canli["Değer (TRY)"]),
                        reverse=True)
    doviz = float(canli[canli.get("Para Birimi", "TRY") != "TRY"]
                  ["Değer (TRY)"].sum(skipna=True)) \
        if "Para Birimi" in canli.columns else float("nan")
    return {
        "pozisyon": len(canli),
        "etkin": etkin_pozisyon_sayisi(agirliklar),
        "hhi": hhi(agirliklar),
        "ilk5": sum(agirliklar[:5]),
        "doviz_pay": _yuzde(doviz, toplam),
    }

# ==========================================================================
# KAYNAK: app.py
# ==========================================================================


# --- Modül kısayolları -------------------------------------------------------
# Modüler sürümde `an` = analytics, `px` = prices modülüydü. Tek dosyada hepsi
# aynı isim alanında olduğundan ikisini de bu dosyanın global alanına bağlıyoruz.
# (sys.modules kullanılmıyor: Streamlit betiği kendi isim alanında çalıştırır.)
class _Namespace:
    def __getattr__(self, name):
        try:
            return globals()[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


an = hist = imp = ins = px = _Namespace()



import json
import logging

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


logging.basicConfig(level=logging.INFO)

LEVEL_COLS = {"ana_sinif": "Ana Sınıf", "alt_sinif": "Alt Sınıf",
              "sektor": "Sektör", "display": "Varlık",
              "hesap": "Hesap", "currency": "Para Birimi"}

# Varsayılan kırılım: 4 seviye 37 pozisyonda okunamayacak kadar küçük kutular
# ürettiği için Sektör'ü dışarıda bırakıyoruz — kullanıcı isterse ekler.
DEFAULT_LEVELS = ["ana_sinif", "alt_sinif", "display"]



st.set_page_config(layout="wide", page_title="AETHER NEXUS", page_icon="🌌",
                   initial_sidebar_state="collapsed")

# ---------------------------------------------------------------------------
# TEMA
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    :root {
      --bg:        #050506;
      --surface:   #0d0d11;
      --surface-2: #131319;
      --line:      #1e1e26;
      --line-soft: #17171d;
      --ink:       #ececf1;
      --ink-2:     #a0a0ab;
      --ink-3:     #6e6e7a;
      --accent:    #00e5ff;
      --pos:       #2fbe86;
      --neg:       #f0736f;
    }

    .stApp { background: var(--bg); color: var(--ink); }
    .block-container { padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1500px; }

    /* Sayılar hizalı okunsun */
    .stApp, .stApp p, .stApp div, .stApp span,
    [data-testid="stDataFrame"], [data-testid="stDataEditor"] {
      font-variant-numeric: tabular-nums;
      -webkit-font-smoothing: antialiased;
    }

    /* --- Başlık --- */
    .nx-brand { display: flex; align-items: baseline; gap: .6rem; }
    .nx-brand h1 {
      font-size: 1.55rem; font-weight: 700; letter-spacing: -.02em;
      margin: 0; color: var(--ink);
    }
    .nx-brand .tag {
      font-size: .62rem; font-weight: 700; letter-spacing: .18em;
      text-transform: uppercase; color: var(--bg);
      background: var(--accent); padding: .18rem .45rem; border-radius: 4px;
    }
    .nx-meta { color: var(--ink-3); font-size: .8rem; margin-top: .35rem; }
    .nx-meta b { color: var(--ink-2); font-weight: 600; }

    /* --- KPI kartları --- */
    .kpi {
      background: linear-gradient(160deg, var(--surface-2) 0%, var(--surface) 100%);
      border: 1px solid var(--line);
      border-radius: 14px; padding: 1rem 1.15rem 1.05rem;
      position: relative; overflow: hidden; height: 100%;
    }
    .kpi::before {
      content: ""; position: absolute; inset: 0 auto 0 0; width: 3px;
      background: var(--accent); opacity: .85;
    }
    .kpi.pos::before { background: var(--pos); }
    .kpi.neg::before { background: var(--neg); }
    .kpi-label {
      font-size: .66rem; letter-spacing: .13em; text-transform: uppercase;
      color: var(--ink-3); font-weight: 600; margin-bottom: .5rem;
    }
    .kpi-value {
      font-size: 1.65rem; font-weight: 700; letter-spacing: -.025em;
      line-height: 1.15; color: var(--ink);
    }
    .kpi-sub { font-size: .76rem; color: var(--ink-3); margin-top: .38rem; }
    .kpi-value.pos, .kpi-sub.pos, .badge.pos { color: var(--pos); }
    .kpi-value.neg, .kpi-sub.neg, .badge.neg { color: var(--neg); }
    .badge {
      display: inline-block; font-size: .72rem; font-weight: 600;
      padding: .12rem .42rem; border-radius: 5px;
      background: rgba(255,255,255,.05);
    }
    .badge.pos { background: rgba(47,190,134,.13); }
    .badge.neg { background: rgba(240,115,111,.13); }

    /* --- Bölüm başlığı --- */
    .nx-section {
      font-size: .68rem; letter-spacing: .14em; text-transform: uppercase;
      color: var(--ink-3); font-weight: 600;
      margin: 1.6rem 0 .7rem; padding-bottom: .45rem;
      border-bottom: 1px solid var(--line-soft);
    }

    /* --- Sekmeler --- */
    .stTabs [data-baseweb="tab-list"] {
      gap: .15rem; border-bottom: 1px solid var(--line); padding-bottom: 0;
    }
    .stTabs [data-baseweb="tab"] {
      height: 42px; padding: 0 1.05rem; background: transparent;
      color: var(--ink-3); font-size: .87rem; font-weight: 500;
      border-radius: 8px 8px 0 0;
    }
    .stTabs [aria-selected="true"] {
      color: var(--ink) !important; background: var(--surface) !important;
      border-bottom: 2px solid var(--accent) !important;
    }

    /* --- Tablolar --- */
    [data-testid="stDataFrame"], [data-testid="stDataEditor"] {
      border: 1px solid var(--line); border-radius: 12px; overflow: hidden;
    }

    /* --- Butonlar ---
       Koyu zeminde ikincil butonlar varsayılan olarak siyah üstüne siyah
       kalıyordu; ancak imleç üzerine gelince görünüyorlardı. Hepsine görünür
       bir yüzey, kenarlık ve açık yazı rengi veriyoruz. */
    /* Seçici listesi Streamlit sürümüne göre değişiyor; hem eski sınıf
       adlarını hem yeni data-testid'leri hem de çıplak <button>'ları
       hedefliyoruz. Asıl çözüm .streamlit/config.toml'daki koyu tema —
       bu kurallar o dosya olmasa da butonlar kaybolmasın diye var. */
    .stButton > button,
    .stDownloadButton > button,
    .stFormSubmitButton > button,
    .stPopover > button,
    [data-testid="stBaseButton-secondary"],
    [data-testid="stBaseButton-secondaryFormSubmit"],
    [data-testid="stBaseButton-borderless"],
    [data-testid="stFileUploaderDropzone"] button,
    [data-testid="stExpander"] summary,
    div[data-testid="stVerticalBlock"] button:not([kind="primary"]) {
      background: var(--surface-2) !important;
      color: var(--ink) !important;
      border: 1px solid #2b2b36 !important;
      border-radius: 9px;
      font-weight: 600; font-size: .85rem; transition: all .12s ease;
    }
    .stButton > button:hover,
    .stDownloadButton > button:hover,
    .stFormSubmitButton > button:hover,
    [data-testid="stFileUploaderDropzone"] button:hover {
      background: #1b1b23 !important;
      border-color: var(--accent) !important;
      color: var(--accent) !important;
    }

    /* Açılır menü, radyo, sayı ve metin kutuları: config.toml yoksa
       Streamlit bunları AÇIK temayla çizer ve siyah zeminde kaybolurlar. */
    [data-baseweb="select"] > div,
    [data-baseweb="input"] > div,
    .stTextInput input, .stNumberInput input, .stDateInput input {
      background: var(--surface-2) !important;
      border-color: #2b2b36 !important;
      color: var(--ink) !important;
    }
    [data-baseweb="select"] svg { fill: var(--ink-2) !important; }
    [data-baseweb="popover"] li { color: var(--ink) !important; }
    [data-testid="stFileUploaderDropzone"] {
      background: var(--surface) !important; border: 1px dashed #2b2b36 !important;
    }
    label, .stSelectbox label, .stRadio label { color: var(--ink-2) !important; }
    .stButton > button * , .stDownloadButton > button *,
    .stFormSubmitButton > button * { color: inherit !important; }

    /* Birincil buton her zaman dolu cyan */
    .stButton > button[kind="primary"],
    .stFormSubmitButton > button[kind="primary"],
    [data-testid="stBaseButton-primary"],
    [data-testid="stBaseButton-primaryFormSubmit"] {
      background: var(--accent) !important; color: #04141a !important;
      border-color: var(--accent) !important;
    }
    .stButton > button[kind="primary"] *,
    .stFormSubmitButton > button[kind="primary"] * { color: #04141a !important; }
    .stButton > button[kind="primary"]:hover,
    .stFormSubmitButton > button[kind="primary"]:hover {
      filter: brightness(1.1); color: #04141a !important;
    }

    /* Dönem seçici (radio) düğme görünümünde */
    div[role="radiogroup"] > label {
      background: var(--surface-2); border: 1px solid #2b2b36;
      border-radius: 8px; padding: .3rem .7rem; margin-right: .35rem;
      transition: all .12s ease;
    }
    div[role="radiogroup"] > label:hover { border-color: var(--accent); }

    /* Katlanır bölüm başlıkları da görünür olsun */
    div[data-testid="stExpander"] summary,
    div[data-testid="stExpander"] details > div:first-child {
      color: var(--ink) !important;
    }

    /* --- Giriş alanları --- */
    .stTextInput input, .stNumberInput input, .stSelectbox > div > div {
      background: var(--surface) !important; border-color: var(--line) !important;
      border-radius: 9px !important;
    }
    div[data-testid="stExpander"] {
      border: 1px solid var(--line); border-radius: 12px; background: var(--surface);
    }
    hr { border-color: var(--line-soft); }

    /* Streamlit'in varsayılan kırmızı vurgusunu temaya çek */
    [data-baseweb="tag"] {
      background-color: rgba(0,229,255,.13) !important;
      color: var(--accent) !important;
      border: 1px solid rgba(0,229,255,.28) !important;
      border-radius: 7px !important;
    }
    [data-baseweb="tag"] span, [data-baseweb="tag"] svg { color: var(--accent) !important; }
    .stSlider [data-baseweb="slider"] div[role="slider"] { background: var(--accent) !important; }
    [data-testid="stFileUploaderDropzone"] {
      background: var(--surface) !important; border: 1px dashed var(--line) !important;
      border-radius: 12px !important;
    }
    a, a:visited { color: var(--accent); }
    kbd {
      background: var(--surface-2); border: 1px solid var(--line);
      border-radius: 5px; padding: .05rem .3rem; font-size: .78rem; color: var(--ink-2);
    }
    /* Uyarı / bilgi kutuları */
    div[data-testid="stAlert"] { border-radius: 11px; border: 1px solid var(--line); }

    /* =====================================================================
       SON ÇARE OKUNURLUK KATMANI
       .streamlit/config.toml yüklenmemişse Streamlit uygulamayı KENDİ AÇIK
       temasıyla çizer: yazı rengi koyu kalır, zemin ise buradaki CSS ile
       siyah olur — sonuç siyah üstüne siyah, başlıklar ve butonlar okunmaz.
       Tek tek seçici avlamak Streamlit sürümleriyle sürekli kırıldığı için
       metin rengini GENİŞ kapsamda zorluyoruz; hemen altındaki blok da
       renkli olması gereken öğeleri geri alıyor. Sıra önemli: eşit
       özgüllükte sonra gelen kural kazanır.
       ===================================================================== */
    :root { color-scheme: dark; }
    html, body, .stApp, [data-testid="stAppViewContainer"],
    [data-testid="stHeader"], [data-testid="stToolbar"] {
      background-color: var(--bg) !important;
    }
    .stApp, .stApp p, .stApp span, .stApp div, .stApp label, .stApp li,
    .stApp td, .stApp th, .stApp summary, .stApp small, .stApp strong,
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
    [data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] *,
    [data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] *,
    [data-baseweb="select"] *, [data-baseweb="popover"] *,
    [data-testid="stExpander"] * {
      color: var(--ink) !important;
    }

    /* --- Geri alınanlar: renkli kalması gereken öğeler ------------------- */
    .nx-section, .kpi-label, .kpi-sub, .nx-meta { color: var(--ink-3) !important; }
    .nx-meta b { color: var(--ink-2) !important; }
    .kpi-value { color: var(--ink) !important; }
    .kpi-value.pos, .kpi-sub.pos, .badge.pos { color: var(--pos) !important; }
    .kpi-value.neg, .kpi-sub.neg, .badge.neg { color: var(--neg) !important; }
    .nx-brand .tag { color: var(--bg) !important; }
    a, a:visited, a * { color: var(--accent) !important; }
    .stTabs [aria-selected="true"], .stTabs [aria-selected="true"] * {
      color: var(--ink) !important;
    }
    .stTabs [data-baseweb="tab"] p { color: var(--ink-3) !important; }
    .stTabs [aria-selected="true"] p { color: var(--ink) !important; }
    /* Birincil buton koyu zemin üstünde açık yazı DEĞİL, tam tersi */
    .stButton > button[kind="primary"],
    .stButton > button[kind="primary"] *,
    .stFormSubmitButton > button[kind="primary"],
    .stFormSubmitButton > button[kind="primary"] *,
    [data-testid="stBaseButton-primary"],
    [data-testid="stBaseButton-primary"] * {
      color: #04141a !important;
    }
    [data-baseweb="tag"], [data-baseweb="tag"] * { color: var(--accent) !important; }
    /* Uyarı kutularının kendi ikon renkleri korunsun */
    div[data-testid="stAlert"] svg { color: inherit !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#a0a0ab", size=12,
              family='-apple-system, "Segoe UI", Roboto, Inter, sans-serif'),
    margin=dict(t=8, b=8, l=8, r=8),
    hoverlabel=dict(bgcolor="#131319", bordercolor="#1e1e26",
                    font=dict(color="#ececf1", size=12)),
)


def section(title: str) -> None:
    st.markdown(f"<div class='nx-section'>{title}</div>", unsafe_allow_html=True)


def kpi(label: str, value: str, sub: str = "", tone: str = "") -> str:
    cls = f" {tone}" if tone else ""
    return (f"<div class='kpi{cls}'><div class='kpi-label'>{label}</div>"
            f"<div class='kpi-value{cls}'>{value}</div>"
            f"<div class='kpi-sub{cls}'>{sub}</div></div>")


# ---------------------------------------------------------------------------
# DEPOLAMA & FİYAT
# ---------------------------------------------------------------------------
@st.cache_resource
def get_storage() -> Storage:
    return storage_from_secrets(getattr(st, "secrets", None))


def load_assets(store: Storage) -> list[dict]:
    try:
        result = store.load(default=[])
    except StorageError as exc:
        st.error(f"Portföy okunamadı: {exc}")
        return []
    raw = result.data if isinstance(result.data, list) else result.data.get("assets", [])
    return [normalize_asset(a) for a in raw]


def save_assets(store: Storage, assets: list[dict], message: str) -> bool:
    try:
        store.save(assets, message)
        return True
    except StorageError as exc:
        st.error(f"Kaydedilemedi: {exc}")
        return False


@st.cache_resource
def get_history_store() -> Storage:
    """Tarihçe, portföyle aynı depoda ama ayrı dosyada tutulur."""
    base = storage_from_secrets(getattr(st, "secrets", None),
                                local_path="portfolio_history.json")
    if base.enabled:
        # [github].path portföy dosyasını gösterir; tarihçe için komşu dosya
        base.path = (base.path.rsplit("/", 1)[0] + "/portfolio_history.json"
                     if "/" in base.path else "portfolio_history.json")
    return base


@st.cache_resource(ttl=300, show_spinner=False)
def cached_snapshot(fingerprint: str, _assets: list[dict]) -> px.MarketSnapshot:
    """
    Piyasa anlık görüntüsünü önbellekler.

    NEDEN cache_data DEĞİL cache_resource:
      st.cache_data dönen değeri PICKLE eder. MarketSnapshot ve Quote tek
      dosya sürümünde betiğin kendi isim alanında tanımlıdır; pickle bir
      sınıfı ancak içe aktarılabilir bir modülde bulabildiği için burada
      UnserializableReturnValueError atıyordu. Modüler sürümde sınıflar
      portfolio.prices içinde olduğu için aynı kod sorunsuz çalışıyordu —
      yani hata yalnızca dağıtılan sürümde ortaya çıkıyordu.
      cache_resource nesneyi olduğu gibi saklar, serileştirmez.

    `_assets` alt çizgiyle başlıyor: Streamlit bu parametreyi
    ANAHTARLAMADA KULLANMAZ. Önbellek anahtarı fingerprint'tir; fiyatlar
    yalnızca sembol/kaynak/birim üçlüsüne bağlı olduğu için adet veya
    maliyet değişince fiyatları yeniden çekmek gereksizdir.
    """
    return px.build_snapshot(_assets)


def snapshot_fingerprint(assets: list[dict]) -> str:
    return "|".join(sorted(f"{a['symbol']}:{a.get('source')}:{a.get('unit')}"
                           for a in assets))


def fmt_try(v: float) -> str:
    """TRY tutarını KULLANICININ seçtiği para biriminde yazar.

    Ad geriye dönük uyumluluk için 'try' kalıyor; girdi her zaman TRY'dir,
    çevrim yalnızca sunumda yapılır (bkz. analytics.format_money).
    """
    return an.format_money(v, st.session_state.get("goster_para", "TRY"),
                           globals().get("_fx_now") or {})


# ---------------------------------------------------------------------------
# BAŞLIK
# ---------------------------------------------------------------------------
store = get_storage()
if "assets" not in st.session_state:
    st.session_state.assets = load_assets(store)
assets: list[dict] = st.session_state.assets

head_l, head_c, head_r = st.columns([4, 1, 1])
with head_l:
    st.markdown(
        "<div class='nx-brand'><h1>AETHER NEXUS</h1><span class='tag'>Live</span></div>",
        unsafe_allow_html=True)
with head_c:
    st.selectbox("Para birimi", an.DISPLAY_CURRENCIES, key="goster_para",
                 help="Bütün tutarlar bu para biriminde gösterilir. Hesaplar "
                      "TRY üzerinden yapılır, çevrim yalnızca sunumdadır.")
with head_r:
    st.markdown("<div style='height:1.75rem'></div>", unsafe_allow_html=True)
    if st.button("⚡ Fiyatları Yenile", width="stretch", type="primary"):
        cached_snapshot.clear()
        st.rerun()

with st.spinner("Piyasa verisi çekiliyor…"):
    if not assets:
        snap = px.MarketSnapshot(fetched_at=px._now_istanbul())
    else:
        # Önbellek bir HIZLANDIRMADIR; bozulursa uygulamayı düşürmemeli.
        try:
            snap = cached_snapshot(snapshot_fingerprint(assets), assets)
        except Exception as exc:                          # noqa: BLE001
            st.caption(f"ℹ️ Fiyat önbelleği devre dışı ({type(exc).__name__}); "
                       f"veriler doğrudan çekiliyor.")
            snap = px.build_snapshot(assets)

usdtry = snap.usdtry
# fmt_try() bu sözlüğü globals() üzerinden okur; kur her yenilemede tazelenir.
_fx_now = snap.fx
GOSTER = st.session_state.get("goster_para", "TRY")
PARA_ISARETI = an.CURRENCY_SYMBOLS.get(GOSTER, "")

if GOSTER != "TRY" and an.display_rate(GOSTER, snap.fx) != \
        an.display_rate(GOSTER, snap.fx):
    st.warning(
        f"{GOSTER} kuru çekilemedi; tutarlar TRY olarak gösteriliyor.",
        icon="⚠️")
    GOSTER = "TRY"
    PARA_ISARETI = "₺"
    st.session_state.goster_para = "TRY"

# 1 TRY kaç <GOSTER> eder. Hesaplar TRY üzerinden yapılır; bu oran yalnızca
# grafik ve tablolarda SUNUM için kullanılır, tarihçeye TRY yazılmaya devam
# eder — yoksa para birimini değiştirmek geçmişi bozardı.
GOSTER_ORAN = an.display_rate(GOSTER, snap.fx)
if GOSTER_ORAN != GOSTER_ORAN:
    GOSTER_ORAN = 1.0

# Tek dosya sürümünde derleyici BUILD_ID/BUILD_TIME enjekte eder; modüler
# çalıştırmada yoktur. globals() ile okuyoruz ki iki kipte de çalışsın.
SURUM = globals().get("BUILD_ID", "modüler")
SURUM_ZAMAN = globals().get("BUILD_TIME", "")

meta = [f"Son güncelleme <b>{snap.fetched_at}</b>"]
meta.append(f"USD/TRY <b>{usdtry:,.2f}</b>" if usdtry else "USD/TRY <b>—</b>")
if snap.fx.get("EURTRY"):
    meta.append(f"EUR/TRY <b>{snap.fx['EURTRY']:,.2f}</b>")
if snap.gold_usd_oz and usdtry:
    meta.append(f"Gram altın <b>₺{snap.gold_usd_oz / px.TROY_OUNCE_G * usdtry:,.0f}</b>")
meta.append(f"Kayıt <b>{'GitHub' if store.backend == 'github' else 'yerel'}</b>")
meta.append(f"Sürüm <b>{SURUM}</b>")
st.markdown(f"<div class='nx-meta'>{'  ·  '.join(meta)}</div>", unsafe_allow_html=True)

if store.backend == "local":
    st.warning(
        "**Kalıcılık kapalı.** Portföy sadece geçici dosyaya yazılıyor; Streamlit "
        "Cloud uygulamayı uyuttuğunda kayıtlar silinir. Secrets içine `[github]` "
        "bölümünü ekleyin.", icon="⚠️")
for err in snap.errors:
    st.warning(err, icon="⚠️")

df = an.build_dataframe(assets, snap.quotes, snap.fx,
                        changes=snap.changes, change_currency=GOSTER)

# ---------------------------------------------------------------------------
# KPI ŞERİDİ
# ---------------------------------------------------------------------------
if not df.empty:
    t = an.totals(df, usdtry)
    tone = "pos" if t["kz_try"] >= 0 else "neg"
    sign = "+" if t["kz_try"] >= 0 else "−"
    abs_kz = abs(t["kz_try"])
    def diger_paralar(try_value: float) -> str:
        """Seçili olmayan iki para birimindeki karşılığı alt satırda gösterir."""
        parcalar = [an.format_money(try_value, cur, snap.fx)
                    for cur in an.DISPLAY_CURRENCIES if cur != GOSTER]
        return "  ·  ".join(p for p in parcalar if p != "—") or "kur yok"

    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(kpi("Varlık Toplamı", fmt_try(t["deger_try"]),
                    diger_paralar(t["deger_try"])),
                unsafe_allow_html=True)
    k2.markdown(kpi("Net Değer", fmt_try(t["net_try"]),
                    (f"borç {fmt_try(t['borc_try'])}" if t["borc_try"]
                     else "borç yok")
                    + f"  ·  {diger_paralar(t['net_try'])}"),
                unsafe_allow_html=True)
    k3.markdown(kpi("Kâr / Zarar", f"{sign}{fmt_try(abs_kz)}",
                    f"<span class='badge {tone}'>{sign}%{abs(t['kz_pct']):.2f}</span>"
                    f"&nbsp; maliyet {fmt_try(t['maliyet_try'])}", tone),
                unsafe_allow_html=True)
    biggest = df.iloc[0]
    k4.markdown(kpi("En Büyük Pozisyon", str(biggest["Etiket"]),
                    f"%{biggest['Ağırlık %']:.1f} ağırlık  ·  {len(df)} pozisyon"),
                unsafe_allow_html=True)

    if t["eksik"]:
        # Sadece sayı vermek işe yaramıyor — HANGİ varlıklar olduğunu söyle ki
        # kullanıcı sembolü düzeltebilsin ya da elle değer girebilsin.
        _eksik_df = df[~df["Fiyat OK"]]
        _adlar = ", ".join(
            f"{r['Sembol']} ({r['Yahoo Sembol']})" if r["Sembol"] != r["Yahoo Sembol"]
            else str(r["Sembol"])
            for _, r in _eksik_df.head(12).iterrows())
        if len(_eksik_df) > 12:
            _adlar += f" … +{len(_eksik_df) - 12}"
        st.info(f"**{t['eksik']} varlığın fiyatı çekilemedi**, toplamlara dahil "
                f"değil: {_adlar}\n\nSebebini *Ayarlar → Fiyat kaynağı durumu* "
                f"tablosundaki **Hata** sütununda görebilirsiniz. Sembol yanlışsa "
                f"*Varlıklar* sekmesinden düzeltin; fiyatı hiç çekilemeyen bir "
                f"varlık için *Değer Güncelle* sekmesinden elle tutar girin.",
                icon="ℹ️")

# ---------------------------------------------------------------------------
# TARİHÇE — günde bir anlık görüntü
# ---------------------------------------------------------------------------
hist_store = get_history_store()

if "history" not in st.session_state:
    try:
        st.session_state.history = hist.normalize_history(
            hist_store.load(default=[]).data)
    except StorageError as exc:
        st.session_state.history = []
        st.info(f"Tarihçe okunamadı: {exc}", icon="ℹ️")

history: list[dict] = st.session_state.history

# Bugünün kaydını ekle/güncelle (aynı gün tekrar açılırsa üzerine yazılır).
# Fiyatların hiçbiri gelmediyse (ağ kesik) sıfır değerle kayıt atmıyoruz —
# yoksa tarihçede sahte bir çöküş görünürdü.
if not df.empty and not df["Değer (TRY)"].isna().all():
    _by_class = (an.split_borc(df)[0]
                 .groupby("Ana Sınıf")["Değer (TRY)"].sum(min_count=1)
                 .dropna().round(2).to_dict())
    _toplam = an.totals(df, usdtry)["deger_try"]
    if _toplam > 0:
        _new_hist, _changed = hist.upsert_today(history, _toplam, usdtry, _by_class)
        if _changed:
            st.session_state.history = _new_hist
            history = _new_hist
            # Tarihçe kaydı YARDIMCI bir işlevdir; başarısız olması uygulamayı
            # ASLA düşürmemeli. Bu yüzden StorageError değil Exception
            # yakalıyoruz: ağ hatası, JSON hatası, izin hatası — hepsi burada
            # kalsın, portföy görüntülenmeye devam etsin.
            try:
                hist_store.save(_new_hist, "günlük değer kaydı")
            except Exception as exc:                      # noqa: BLE001
                st.caption(f"⚠️ Tarihçe kaydedilemedi (portföy etkilenmedi): "
                           f"{type(exc).__name__}: {exc}")

# ---------------------------------------------------------------------------
# SEKMELER
# ---------------------------------------------------------------------------
(tab_dag, tab_poz, tab_analiz, tab_hisse, tab_duzen, tab_kova, tab_ekle,
 tab_ice, tab_ayar) = st.tabs(
    ["Dağılım", "Pozisyonlar", "Analiz", "Hisse", "Varlıklar",
     "Değer Güncelle", "Yeni Varlık", "İçe Aktar", "Ayarlar"])

# ============================== DAĞILIM ====================================
PERIOD_DAYS = {lbl: d for lbl, d in hist.PERIODS}


def render_degisim(history: list[dict]) -> None:
    """Ana sayfadaki varlık değişimi bölümü: grafik + dönem dökümü."""
    section("Varlık değişimi")

    if len(history) < 2:
        st.info(
            "Değişim grafiği için en az iki günlük kayıt gerekiyor. Uygulama "
            "her gün açıldığında bir anlık görüntü kaydediyor; Bluecoins "
            "yedeğinizden geçmiş çıkarmak için "
            "`python import_bluecoins.py yedek.fydb --history portfolio_history.json` "
            "komutunu çalıştırıp dosyayı depoya ekleyin.", icon="ℹ️")
        return

    changes = hist.period_changes(history)
    cols = st.columns([3, 1])
    with cols[0]:
        secim = st.radio(
            "Dönem", [lbl for lbl, _ in hist.PERIODS], horizontal=True,
            index=len(hist.PERIODS) - 1, label_visibility="collapsed",
            key="degisim_periyot")
    with cols[1]:
        yigin = st.toggle("Sınıf kırılımı", value=False,
                          help="Toplam çizgisi yerine varlık sınıflarına göre "
                               "yığılmış alan grafiği")

    days = PERIOD_DAYS.get(secim)
    rows = hist.series(history, days)
    if len(rows) < 2:
        st.warning(f"'{secim}' dönemi için yeterli kayıt yok "
                   f"(elde {len(rows)} nokta var).", icon="⚠️")
        return

    fig = go.Figure()
    if yigin:
        dates, by_class = hist.class_series(history, days)
        cmap = an.color_map(list(by_class))
        for name, values in by_class.items():
            fig.add_trace(go.Scatter(
                x=dates, y=[v * GOSTER_ORAN for v in values], name=name, mode="lines",
                stackgroup="one", line=dict(width=0.5, color=cmap[name]),
                fillcolor=cmap[name],
                hovertemplate="%{x}<br>" + name +
                              f" {PARA_ISARETI}%{{y:,.0f}}<extra></extra>"))
        fig.update_layout(legend=dict(orientation="h", y=-0.18))
    else:
        dates = [r["date"] for r in rows]
        values = [r["total_try"] * GOSTER_ORAN for r in rows]
        artis = values[-1] >= values[0]
        renk = an.POS_COLOR if artis else an.NEG_COLOR
        fig.add_trace(go.Scatter(
            x=dates, y=values, mode="lines", line=dict(color=renk, width=2),
            fill="tozeroy",
            fillcolor=an._rgba(renk, 0.12),
            hovertemplate=f"%{{x}}<br>{PARA_ISARETI}%{{y:,.0f}}<extra></extra>",
            name="Toplam"))
        fig.add_hline(y=values[0], line=dict(color="#3a3a45", width=1, dash="dot"))
        fig.update_layout(showlegend=False)

    fig.update_layout(
        height=330,
        xaxis=dict(showgrid=False, showline=False, tickfont=dict(size=11)),
        yaxis=dict(gridcolor="#17171d", zeroline=False, tickformat=",.0f",
                   tickfont=dict(size=11)),
        hovermode="x unified", **CHART_LAYOUT)
    st.plotly_chart(fig, width="stretch")

    # --- Dönem dökümü ---
    if not changes:
        st.caption("Dönem karşılaştırması için henüz yeterli geçmiş yok.")
        return

    dokum = pd.DataFrame([{
        "Dönem": c.label,
        "Başlangıç": c.start_date,
        "Bitiş": c.end_date,
        "Gün": c.days,
        "Başlangıç Değeri": c.start_value * GOSTER_ORAN,
        "Güncel Değer": c.end_value * GOSTER_ORAN,
        f"Değişim ({GOSTER})": c.delta * GOSTER_ORAN,
        "Değişim %": c.pct_display,
    } for c in changes])

    st.dataframe(
        dokum, width="stretch", hide_index=True,
        column_config={
            "Başlangıç Değeri": st.column_config.NumberColumn(format="%.0f"),
            "Güncel Değer": st.column_config.NumberColumn(format="%.0f"),
            f"Değişim ({GOSTER})": st.column_config.NumberColumn(format="%+.0f"),
            "Değişim %": st.column_config.NumberColumn(format="%+.2f%%"),
        })
    st.caption(
        "Bu seri **net varlık** serisidir — yatırım getirisinin yanı sıra para "
        "yatırma/çekmeleri de içerir, dolayısıyla uzun dönem yüzdeleri getiri "
        "olarak okunmamalıdır. Başlangıç değeri bugünkünün %1'inden küçük olan "
        "dönemlerde yüzde anlamsızlaştığı için boş bırakılır. Kayıt olmayan "
        "günlerde hedef tarihe eşit ya da ondan önceki en yakın kayıt esas "
        "alınır; dönemi karşılayacak geçmiş yoksa o satır hiç gösterilmez.")


with tab_dag:
    render_degisim(history)

    if df.empty or df["Değer (TRY)"].fillna(0).sum() <= 0:
        st.info("Henüz gösterilecek veri yok. 'Yeni Varlık' sekmesinden başlayın.")
    else:
        levels = st.multiselect(
            "Kırılım seviyeleri", options=list(LEVEL_COLS.values()),
            default=[LEVEL_COLS[k] for k in DEFAULT_LEVELS],
            help="Sırayı değiştirebilir, seviye ekleyip çıkarabilirsiniz.")
        if not levels:
            levels = [LEVEL_COLS["ana_sinif"]]

        section("Portföy haritası")
        hm_l, hm_r = st.columns([3, 2])
        RENK_SECENEK = {"Ana sınıf": None, **{v: v for v in an.CHANGE_LABELS.values()}}
        renk_modu = hm_l.radio(
            "Renk", list(RENK_SECENEK), horizontal=True, key="tm_renk",
            help="Kutu ALANI her zaman değeri gösterir. Renk ya varlık "
                 "sınıfını ya da seçilen dönemdeki yüzde değişimi gösterir.")
        isi_sutun = RENK_SECENEK[renk_modu]
        if isi_sutun and isi_sutun not in df.columns:
            hm_r.warning("Dönem verisi yok.", icon="⚠️")
            isi_sutun = None
        elif isi_sutun:
            _kapsam = int(df[isi_sutun].notna().sum())
            hm_r.caption(
                f"{_kapsam}/{len(df)} varlık için değişim hesaplandı · "
                f"yüzdeler **{GOSTER}** cinsinden"
                + ("" if GOSTER == "TRY" else " (kur etkisi hariç)"))

        tm = an.treemap_data(df, levels, change_col=isi_sutun)
        # customdata: [0] kendi para birimindeki tutar, [1] dönem değişimi
        _tm_custom = [
            [dogal or f"{PARA_ISARETI}{deger * GOSTER_ORAN:,.0f}",
             "—" if pct is None else f"{pct:+.2f}%"]
            for dogal, deger, pct in zip(tm["natives"], tm["values"], tm["changes"])
        ]
        # Isı modunda yazı rengi kutunun rengine göre seçilir (kontrast >= 4.5:1)
        _yazi_rengi = tm["text_colors"] if isi_sutun else "#ececf1"
        _alt_satir = ("%{customdata[1]}" if isi_sutun else "%{percentParent}")

        fig_tm = go.Figure(go.Treemap(
            ids=tm["ids"], labels=tm["labels"], parents=tm["parents"],
            values=[v * GOSTER_ORAN for v in tm["values"]],
            branchvalues="total",
            customdata=_tm_custom,
            marker=dict(colors=tm["colors"], line=dict(color="#050506", width=2),
                        cornerradius=6),
            textinfo="label+text",
            texttemplate="<b>%{label}</b><br>%{customdata[0]}<br>" + _alt_satir,
            textfont=dict(size=13, color=_yazi_rengi),
            hovertemplate=(
                "<b>%{id}</b><br>%{customdata[0]}"
                "<br>" + PARA_ISARETI + "%{value:,.0f}"
                "<br>Dönem değişimi %{customdata[1]}"
                "<br>Üst grubun %{percentParent} kadarı<extra></extra>"),
            pathbar=dict(visible=True, thickness=22),
        ))
        fig_tm.update_layout(height=520, **CHART_LAYOUT)
        st.plotly_chart(fig_tm, width="stretch")

        if isi_sutun:
            # Renk tek başına kimlik taşımasın diye her kutuda yüzde YAZILI;
            # bu şerit de rampanın nasıl okunacağını gösteriyor.
            _lejant = "".join(
                f"<span style='display:inline-block;padding:.16rem .5rem;"
                f"background:{renk};color:{an.text_on(renk)};font-size:.72rem;"
                f"border-radius:4px;margin-right:3px'>"
                f"{'≤' if i == 0 else '≥' if i == len(an.HEAT_STEPS) - 1 else ''}"
                f"{esik:+.1f}%</span>"
                for i, (esik, renk) in enumerate(an.HEAT_STEPS))
            st.markdown(
                f"<div style='margin:-.4rem 0 .2rem'>{_lejant}"
                f"<span style='display:inline-block;padding:.16rem .5rem;"
                f"background:{an.HEAT_UNKNOWN};color:#a0a0ab;font-size:.72rem;"
                f"border-radius:4px;margin-left:6px'>veri yok</span></div>",
                unsafe_allow_html=True)

        c1, c2 = st.columns([1, 1])
        with c1:
            section("Ana sınıf dağılımı")
            alloc = an.allocation(df, LEVEL_COLS["ana_sinif"])
            keys = list(alloc[LEVEL_COLS["ana_sinif"]].astype(str))
            cmap = an.color_map(keys)
            donut = go.Figure(go.Pie(
                labels=keys, values=alloc["Değer (TRY)"] * GOSTER_ORAN,
                hole=0.62, sort=False,
                marker=dict(colors=[cmap[k] for k in keys],
                            line=dict(color="#050506", width=2)),
                textinfo="percent", textposition="inside",
                insidetextfont=dict(size=12, color="#ffffff"),
                hovertemplate=("%{label}<br>" + PARA_ISARETI +
                               "%{value:,.0f} (%{percent})<extra></extra>"),
            ))
            donut.update_layout(
                height=380, showlegend=True,
                legend=dict(orientation="v", x=1.0, y=0.5, xanchor="left",
                            font=dict(size=12)),
                annotations=[dict(text=f"<b>{fmt_try(t['deger_try'])}</b>",
                                  x=0.5, y=0.5, showarrow=False,
                                  font=dict(size=17, color="#ececf1"))],
                **CHART_LAYOUT)
            st.plotly_chart(donut, width="stretch")
        with c2:
            section("En büyük 15 pozisyon")
            bar_df = df.dropna(subset=["Değer (TRY)"]).head(15).iloc[::-1]
            top_map = an.color_map(list(an.allocation(df, "Ana Sınıf")["Ana Sınıf"]))
            bar = go.Figure(go.Bar(
                x=bar_df["Değer (TRY)"] * GOSTER_ORAN, y=bar_df["Etiket"],
                orientation="h",
                marker=dict(color=[top_map.get(c, an.OTHER_COLOR)
                                   for c in bar_df["Ana Sınıf"]],
                            cornerradius=4),
                hovertemplate=("%{y}<br>" + PARA_ISARETI +
                               "%{x:,.0f}<extra></extra>"),
            ))
            bar.update_layout(
                height=380, bargap=0.32,
                xaxis=dict(gridcolor="#17171d", zeroline=False, showline=False,
                           tickformat=",.0f"),
                yaxis=dict(showgrid=False, tickfont=dict(size=11)),
                **CHART_LAYOUT)
            st.plotly_chart(bar, width="stretch")

        with st.expander("Akış diyagramı (Sankey)"):
            sk = an.sankey_data(df, levels)
            fig_sk = go.Figure(go.Sankey(
                arrangement="snap",
                node=dict(pad=16, thickness=14, line=dict(color="#050506", width=1),
                          label=sk["labels"], color=sk["node_colors"],
                          customdata=sk["paths"],
                          hovertemplate=("%{customdata}<br>" + PARA_ISARETI +
                                         "%{value:,.0f}<extra></extra>")),
                link=dict(source=sk["source"], target=sk["target"],
                          value=[v * GOSTER_ORAN for v in sk["value"]],
                          color=sk["link_colors"],
                          hovertemplate="%{source.label} → %{target.label}"
                                        "<br>" + PARA_ISARETI +
                                        "%{value:,.0f}<extra></extra>"),
            ))
            fig_sk.update_layout(height=110 + 30 * max(6, len(sk["labels"])),
                                 **CHART_LAYOUT)
            st.plotly_chart(fig_sk, width="stretch")

        with st.expander("Dağılım tabloları"):
            for lvl in levels:
                st.markdown(f"**{lvl}**")
                st.dataframe(an.convert_columns(an.allocation(df, lvl),
                                                GOSTER, snap.fx),
                             width="stretch",
                             hide_index=True,
                             column_config={f"Değer ({GOSTER})": st.column_config.NumberColumn(
                                 format="%.0f"),
                                 "Pay %": st.column_config.NumberColumn(format="%.2f%%")})

# ============================== POZİSYONLAR =================================
with tab_poz:
    if df.empty:
        st.info("Henüz pozisyon yok.")
    else:
        _don = list(an.PERIOD_GUN)
        _mevcut_don = [d for d in _don if d in df.columns]
        _sec = st.radio("Sırala / vurgula", ["Ağırlık"] + _mevcut_don + ["Toplam"],
                        horizontal=True, key="poz_donem",
                        help="Tablo bu sütuna göre sıralanır. Bütün dönemler "
                             "tabloda durur; başlıklara tıklayıp kendiniz de "
                             "sıralayabilirsiniz.")

        _kapsam = st.columns([2, 2, 3])
        _sinif = _kapsam[0].multiselect(
            "Ana sınıf", sorted(df["Ana Sınıf"].dropna().unique()),
            key="poz_sinif")
        _hesap = _kapsam[1].multiselect(
            "Hesap", sorted(x for x in df["Hesap"].dropna().unique() if x),
            key="poz_hesap")

        _t = df.copy()
        if _sinif:
            _t = _t[_t["Ana Sınıf"].isin(_sinif)]
        if _hesap:
            _t = _t[_t["Hesap"].isin(_hesap)]

        # Kendi para biriminde fiyat/maliyet; değer seçili para biriminde.
        _t["Değer"] = _t["Değer (TRY)"] * GOSTER_ORAN
        _t["Toplam %"] = _t["K/Z %"]
        _t["K/Z"] = _t["K/Z (TRY)"] * GOSTER_ORAN

        _sirala = {"Ağırlık": "Ağırlık %", "Toplam": "Toplam %"}.get(_sec, _sec)
        _t = _t.sort_values(_sirala, ascending=False, na_position="last")

        _sutunlar = (["Etiket", "Hesap", "Para Birimi", "Ağırlık %", "Adet",
                      "Maliyet", "Fiyat", "Değer", "K/Z", "Toplam %"]
                     + _mevcut_don)
        _gorunum = _t[[c for c in _sutunlar if c in _t.columns]].rename(
            columns={"Etiket": "Sembol", "Maliyet": "Ort. Maliyet",
                     "Fiyat": "Güncel Fiyat", "Değer": f"Değer ({GOSTER})",
                     "K/Z": f"K/Z ({GOSTER})"})

        _cfg = {
            "Ağırlık %": st.column_config.ProgressColumn(
                format="%.2f%%", min_value=0.0,
                max_value=float(_t["Ağırlık %"].max(skipna=True) or 100)),
            "Adet": st.column_config.NumberColumn(format="%.4f"),
            "Ort. Maliyet": st.column_config.NumberColumn(format="%.4f"),
            "Güncel Fiyat": st.column_config.NumberColumn(format="%.4f"),
            f"Değer ({GOSTER})": st.column_config.NumberColumn(format="%.0f"),
            f"K/Z ({GOSTER})": st.column_config.NumberColumn(format="%+.0f"),
            "Toplam %": st.column_config.NumberColumn(format="%+.2f%%"),
        }
        for _d in _mevcut_don:
            _cfg[_d] = st.column_config.NumberColumn(format="%+.2f%%")

        st.dataframe(_gorunum, width="stretch", hide_index=True,
                     column_config=_cfg, height=560)

        _eksik_don = [d for d in _don if d not in df.columns]
        st.caption(
            f"{len(_gorunum)} pozisyon · fiyat ve maliyet varlığın KENDİ para "
            f"biriminde, değer {GOSTER} cinsinden · dönem getirileri {GOSTER} "
            f"bazlı"
            + (f" · şu dönemler için yeterli geçmiş yok: {', '.join(_eksik_don)}"
               if _eksik_don else ""))
        st.download_button(
            "⬇️ CSV indir", _gorunum.to_csv(index=False).encode("utf-8-sig"),
            "pozisyonlar.csv", "text/csv")

# ================================ ANALİZ ====================================
with tab_analiz:
    if df.empty:
        st.info("Analiz için önce portföyünüzü doldurun.")
    else:
        _oz = ins.ozet_sayilar(df)
        a1, a2, a3, a4 = st.columns(4)
        a1.markdown(kpi("Pozisyon", f"{int(_oz['pozisyon'])}",
                        "fiyatı çekilebilen"), unsafe_allow_html=True)
        a2.markdown(kpi("Etkin pozisyon", f"{_oz['etkin']:,.1f}",
                        "ağırlıklar eşit olsaydı kaç pozisyona denk"),
                    unsafe_allow_html=True)
        a3.markdown(kpi("En büyük 5", f"%{_oz['ilk5']:,.1f}",
                        "portföydeki payı"), unsafe_allow_html=True)
        a4.markdown(kpi("Döviz cinsi", f"%{_oz['doviz_pay']:,.1f}",
                        "TRY dışı fiyatlanan"), unsafe_allow_html=True)

        st.caption(
            "**Bunlar yatırım tavsiyesi değildir.** Her madde sizin kendi "
            "rakamlarınızdan aritmetikle çıkan bir gözlemdir; ne alınıp "
            "satılacağına dair bir yargı ya da piyasa tahmini içermez. "
            "Ben finansal danışman değilim — bu bölüm karar vermek için "
            "gereken olguları bir araya getirir, kararı sizin yerinize vermez.")

        _bulgular = ins.analyze(df)
        if not _bulgular:
            st.info("Bulgu üretilemedi (fiyat verisi yetersiz olabilir).")
        else:
            _sayim = {}
            for _b in _bulgular:
                _sayim[_b.seviye] = _sayim.get(_b.seviye, 0) + 1
            _secim = st.multiselect(
                "Seviye", [s for s in ins.SEVIYE_SIRA if s in _sayim],
                default=[s for s in (ins.KRITIK, ins.DIKKAT, ins.BILGI, ins.IYI)
                         if s in _sayim],
                format_func=lambda s: f"{ins.SEVIYE_ETIKET[s]} ({_sayim[s]})",
                key="analiz_seviye")

            for _b in _bulgular:
                if _b.seviye not in _secim:
                    continue
                with st.container(border=True):
                    _sol, _sag = st.columns([5, 1])
                    _sol.markdown(
                        f"**{ins.SEVIYE_ETIKET[_b.seviye]} · {_b.baslik}**")
                    if _b.metrik:
                        _sag.markdown(
                            f"<div style='text-align:right;font-size:1.05rem;"
                            f"font-weight:700'>{_b.metrik}</div>",
                            unsafe_allow_html=True)
                    st.markdown(
                        f"<div style='color:var(--ink-2);font-size:.88rem'>"
                        f"{_b.detay}</div>", unsafe_allow_html=True)

        # ----------------------------- KARŞILAŞTIRMA --------------------
        section("Piyasayla karşılaştırma")
        _k1, _k2 = st.columns([2, 3])
        _kdon = _k1.selectbox("Dönem", list(an.PERIOD_GUN),
                              index=len(an.PERIOD_GUN) - 1, key="kars_donem")
        _kolcut = _k2.multiselect(
            "Ölçütler", list(snap.benchmarks),
            default=[o for o in ("BIST 100", "S&P 500", "Altın (gram)")
                     if o in snap.benchmarks],
            key="kars_olcut")

        _gun = an.PERIOD_GUN[_kdon]
        _pser = an.portfoy_getiri_serisi(
            df[df["Ana Sınıf"] != "Yükümlülük"], snap.series, _gun)
        _ktab = an.karsilastirma_tablosu(
            _pser, {k: v for k, v in snap.benchmarks.items() if k in _kolcut},
            _gun)

        if _ktab.empty:
            st.info("Karşılaştırma için yeterli geçmiş fiyat verisi yok.")
        else:
            _cmap = an.color_map([c for c in _ktab.columns if c != "Portföyüm"])
            _fig = go.Figure()
            for _sutun in _ktab.columns:
                _portfoy = _sutun == "Portföyüm"
                _fig.add_trace(go.Scatter(
                    x=_ktab.index, y=_ktab[_sutun], name=_sutun, mode="lines",
                    line=dict(width=3 if _portfoy else 2,
                              color=an.ACCENT if _portfoy
                              else _cmap.get(_sutun, an.OTHER_COLOR)),
                    hovertemplate="%{x}<br>" + _sutun +
                                  " %{y:,.1f}<extra></extra>"))
            _fig.add_hline(y=100, line=dict(color="#3a3a45", width=1, dash="dot"))
            _fig.update_layout(
                height=360,
                yaxis=dict(gridcolor="#17171d", zeroline=False,
                           title="başlangıç = 100"),
                xaxis=dict(showgrid=False),
                legend=dict(orientation="h", y=-0.18), **CHART_LAYOUT)
            st.plotly_chart(_fig, width="stretch")

            _son = _ktab.iloc[-1] - 100.0
            _ozet = pd.DataFrame({"Getiri %": _son}).sort_values(
                "Getiri %", ascending=False)
            st.dataframe(_ozet, width="stretch", column_config={
                "Getiri %": st.column_config.NumberColumn(format="%+.2f%%")})
            st.caption(
                "**Portföy serisi BUGÜNKÜ ağırlıklarla geriye dönük "
                "hesaplanır** — 'şu anki portföyü o gün de elimde tutsaydım' "
                "senaryosudur, gerçekleşmiş performansınız değildir; geçmişteki "
                "alım satımları bilmiyor. Buna karşılık para giriş/çıkışlarından "
                "etkilenmediği için bir endeksle yan yana konabilecek tek seri "
                "budur. Hepsi TL bazlıdır: yabancı endeksler kur etkisi dahil "
                "gösterilir.")

        # ----------------------------- ÇEŞİTLENME ------------------------
        section("Çeşitlenme ve hedef ağırlık")
        _dseviye = st.selectbox(
            "Kırılım", [LEVEL_COLS[k] for k in ("ana_sinif", "alt_sinif",
                                                "sektor", "hesap")],
            key="denge_seviye")

        _dagilim = an.allocation(df[df["Ana Sınıf"] != "Yükümlülük"], _dseviye)
        if not _dagilim.empty:
            _paylar = list(_dagilim["Pay %"].dropna())
            _hhi = ins.hhi(_paylar)
            _etkin = ins.etkin_pozisyon_sayisi(_paylar)
            _d1, _d2, _d3 = st.columns(3)
            _d1.markdown(kpi(f"{_dseviye} sayısı", f"{len(_dagilim)}", ""),
                         unsafe_allow_html=True)
            _d2.markdown(kpi("Etkin grup sayısı", f"{_etkin:,.1f}",
                             "ağırlıklar eşit olsaydı kaça denk"),
                         unsafe_allow_html=True)
            _d3.markdown(kpi("En büyük grup",
                             f"%{_dagilim['Pay %'].max():,.1f}",
                             str(_dagilim.iloc[0][_dseviye])),
                         unsafe_allow_html=True)

        with st.expander("Hedef ağırlık belirle ve farkı gör", expanded=False):
            st.caption(
                "Hedefleri **siz** giriyorsunuz; uygulama yalnızca aradaki "
                "farkı TL'ye çeviriyor. Bu bir dağılım önerisi değil, "
                "'şu ağırlığı istersem ne kadar kaydırmam gerekir' "
                "hesabıdır. Toplamın 100 olması gerekmez; olmadığında farklar "
                "yine de tek tek doğrudur.")
            _hedefler = {}
            _hk = st.columns(3)
            for _i, (_, _sat) in enumerate(_dagilim.iterrows()):
                _ad = str(_sat[_dseviye])
                _hedefler[_ad] = _hk[_i % 3].number_input(
                    _ad, min_value=0.0, max_value=100.0,
                    value=float(round(_sat["Pay %"], 1)), step=0.5,
                    key=f"hedef_{_dseviye}_{_ad}")

            _denge = an.denge_tablosu(df, _dseviye, _hedefler)
            if not _denge.empty:
                _denge_g = _denge.copy()
                _denge_g["Fark (TRY)"] = _denge_g["Fark (TRY)"] * GOSTER_ORAN
                _denge_g = _denge_g.rename(
                    columns={"Fark (TRY)": f"Fark ({GOSTER})"})
                st.dataframe(
                    _denge_g, width="stretch", hide_index=True,
                    column_config={
                        "Mevcut %": st.column_config.NumberColumn(format="%.2f%%"),
                        "Hedef %": st.column_config.NumberColumn(format="%.2f%%"),
                        "Fark puan": st.column_config.NumberColumn(format="%+.2f"),
                        f"Fark ({GOSTER})": st.column_config.NumberColumn(
                            format="%+.0f")})
                _top = float(_denge["Hedef %"].sum())
                if abs(_top - 100.0) > 0.5:
                    st.caption(f"Girdiğiniz hedeflerin toplamı %{_top:,.1f} "
                               f"(100 değil) — farklar yine de tek tek doğru.")

        with st.expander("Eşikleri değiştir"):
            st.caption("Bulguların hangi noktada uyarıya dönüştüğünü siz "
                       "belirleyin; değişiklik anında yansır.")
            _yeni_esik = {}
            _kolonlar = st.columns(3)
            for _i, (_ad, _var) in enumerate(ins.EŞIKLER.items()):
                _yeni_esik[_ad] = _kolonlar[_i % 3].number_input(
                    _ad.replace("_", " "), value=float(_var),
                    key=f"esik_{_ad}")
            if _yeni_esik != ins.EŞIKLER:
                st.caption(f"{sum(1 for k in _yeni_esik if _yeni_esik[k] != ins.EŞIKLER[k])}"
                           " eşik değiştirildi — yukarıdaki liste bu değerlerle yenilendi.")
                _bulgular = ins.analyze(df, _yeni_esik)

# ================================ HİSSE =====================================
with tab_hisse:
    _hisseler = df[(df["Ana Sınıf"] == "Hisse Senedi")
                   & (df["Alt Sınıf"] == "ABD")
                   & df["Değer (TRY)"].notna()] if not df.empty else df

    if _hisseler is None or _hisseler.empty:
        st.info("ABD hissesi bulunamadı.")
    else:
        st.markdown(
            f"**{len(_hisseler)} ABD hissesi.** Aşağıdaki veriler "
            f"**analistlerin ortalama beklentisidir** — ne benim tahminim ne "
            f"de bir tavsiye. Analist hedefleri sistematik olarak iyimser "
            f"olmakla bilinir; 'potansiyel' bir vaat değil, beklenti "
            f"dağılımının ortalamasıdır.")

        @st.cache_resource(ttl=3600, show_spinner=False)
        def cached_fundamentals(parmak: str, _semboller: list) -> dict:
            """
            Analist verisi. Toplu uç nokta olmadığı için sembol başına bir
            istek gider; bu yüzden otomatik değil DÜĞMEYLE çağrılır ve bir
            saat önbellekte tutulur. (cache_data değil cache_resource:
            bkz. cached_snapshot açıklaması.)
            """
            return px.fetch_fundamentals(_semboller)

        _sem = sorted(_hisseler["Yahoo Sembol"].unique())
        _hb1, _hb2 = st.columns([1, 3])
        if _hb1.button("📊 Analist verisini çek", type="primary",
                       key="hisse_cek"):
            st.session_state.hisse_cekildi = True
            cached_fundamentals.clear()
        _hb2.caption(f"{len(_sem)} sembol için ayrı ayrı sorgulanır, "
                     f"15-40 saniye sürebilir. Sonuç 1 saat önbellekte kalır.")

        if st.session_state.get("hisse_cekildi"):
            with st.spinner("Analist beklentileri çekiliyor…"):
                try:
                    _tv = cached_fundamentals("|".join(_sem), _sem)
                except Exception as exc:                  # noqa: BLE001
                    _tv = {}
                    st.error(f"Veri çekilemedi: {type(exc).__name__}: {exc}")

            if not _tv:
                st.warning("Hiçbir sembol için analist verisi gelmedi.")
            else:
                _sat = []
                for _, _r in _hisseler.iterrows():
                    _b = _tv.get(_r["Yahoo Sembol"])
                    if not _b:
                        continue
                    _sat.append({
                        "Sembol": _r["Etiket"], "Şirket": _b.get("ad", ""),
                        "Sektör": _b.get("sektor", ""),
                        "Ağırlık %": _r["Ağırlık %"],
                        "Fiyat": _b.get("fiyat"), "Hedef": _b.get("hedef"),
                        "Potansiyel %": _b.get("potansiyel"),
                        "Kâr büyüme %": _b.get("kar_buyume"),
                        "Gelir büyüme %": _b.get("gelir_buyume"),
                        "F/K": _b.get("fk"), "İleri F/K": _b.get("ileri_fk"),
                        "Analist": _b.get("analist_sayisi"),
                        "Tavsiye": _b.get("tavsiye", ""),
                    })
                _fdf = pd.DataFrame(_sat)
                _yok = sorted(set(_sem) - set(_tv))
                if _yok:
                    st.caption(f"Veri gelmeyen semboller: {', '.join(_yok)}")

                def _baloncuk(sutun: str, baslik: str, aciklama: str,
                              esik: float | None = None):
                    _v = _fdf[_fdf[sutun].notna()]
                    if _v.empty:
                        st.info(f"{baslik}: veri yok.")
                        return
                    section(baslik)
                    st.caption(aciklama)
                    _ort = float((_v[sutun] * _v["Ağırlık %"]).sum()
                                 / _v["Ağırlık %"].sum())
                    _renk = [an.heat_color(x / 4.0) for x in _v[sutun]] \
                        if esik is None else \
                        [an.POS_COLOR if x >= esik else an.NEG_COLOR
                         for x in _v[sutun]]
                    _f = go.Figure(go.Scatter(
                        x=_v[sutun], y=_v["Sembol"], mode="markers+text",
                        marker=dict(
                            size=_v["Ağırlık %"], sizemode="area",
                            sizeref=max(_v["Ağırlık %"]) / 1600.0, sizemin=8,
                            color=_renk, line=dict(color="#050506", width=2)),
                        text=_v["Sembol"], textposition="middle right",
                        textfont=dict(size=11, color="#ececf1"),
                        customdata=_v[["Ağırlık %", "Şirket"]],
                        hovertemplate="<b>%{y}</b> %{customdata[1]}<br>"
                                      + sutun + " %{x:,.1f}<br>"
                                      "Portföy ağırlığı %{customdata[0]:.2f}"
                                      "<extra></extra>"))
                    _f.add_vline(x=_ort, line=dict(color=an.ACCENT, width=2,
                                                   dash="dot"))
                    if esik is not None:
                        _f.add_vline(x=esik, line=dict(color="#6e6e7a",
                                                       width=1, dash="dash"))
                    _f.update_layout(
                        height=max(320, 22 * len(_v)),
                        xaxis=dict(gridcolor="#17171d", zeroline=False,
                                   ticksuffix="%"),
                        yaxis=dict(showgrid=False, tickfont=dict(size=10),
                                   categoryorder="total ascending"),
                        showlegend=False, **CHART_LAYOUT)
                    st.plotly_chart(_f, width="stretch")
                    st.caption(f"Kesikli mavi çizgi: portföyünüzün ağırlıklı "
                               f"ortalaması (%{_ort:,.1f}). Baloncuk büyüklüğü "
                               f"portföy ağırlığıdır.")

                _baloncuk("Potansiyel %", "Analist hedefine göre potansiyel",
                          "Ortalama analist hedef fiyatının bugünkü fiyata "
                          "göre farkı. Pozitif, analistlerin fiyatı bugünkünün "
                          "üzerinde beklediği anlamına gelir — gerçekleşeceği "
                          "anlamına gelmez.", esik=0.0)
                _baloncuk("Kâr büyüme %", "Beklenen kâr büyümesi",
                          "Analistlerin önümüzdeki dönem için beklediği kâr "
                          "büyümesi.")

                section("Tablo")
                st.dataframe(
                    _fdf.sort_values("Ağırlık %", ascending=False),
                    width="stretch", hide_index=True,
                    column_config={
                        "Ağırlık %": st.column_config.NumberColumn(format="%.2f%%"),
                        "Fiyat": st.column_config.NumberColumn(format="$%.2f"),
                        "Hedef": st.column_config.NumberColumn(format="$%.2f"),
                        "Potansiyel %": st.column_config.NumberColumn(format="%+.1f%%"),
                        "Kâr büyüme %": st.column_config.NumberColumn(format="%+.1f%%"),
                        "Gelir büyüme %": st.column_config.NumberColumn(format="%+.1f%%"),
                        "F/K": st.column_config.NumberColumn(format="%.1f"),
                        "İleri F/K": st.column_config.NumberColumn(format="%.1f"),
                    })

                section("Sektör dağılımı (analist verisine göre)")
                _sk = (_fdf[_fdf["Sektör"] != ""]
                       .groupby("Sektör")["Ağırlık %"].sum()
                       .sort_values(ascending=False))
                if not _sk.empty:
                    _sf = go.Figure(go.Bar(
                        x=_sk.values, y=_sk.index, orientation="h",
                        marker=dict(color=an.SERIES_COLORS[0], cornerradius=4),
                        hovertemplate="%{y}<br>%{x:.2f}%<extra></extra>"))
                    _sf.update_layout(
                        height=max(260, 30 * len(_sk)),
                        xaxis=dict(gridcolor="#17171d", ticksuffix="%",
                                   zeroline=False),
                        yaxis=dict(showgrid=False), **CHART_LAYOUT)
                    st.plotly_chart(_sf, width="stretch")
                    st.caption("Yahoo'nun sektör etiketlerine göre; portföy "
                               "içindeki ABD hisselerinin ağırlıkları.")

# ======================= VARLIKLAR (TAM DÜZENLEME) ==========================
with tab_duzen:
    st.markdown(
        "Tablodaki her alanı doğrudan düzenleyebilirsiniz. **Satır eklemek** için "
        "en alttaki boş satırı doldurun, **silmek** için satırın solundaki kutuyu "
        "işaretleyip <kbd>Delete</kbd> tuşuna basın. Değişiklikler *Kaydet*'e "
        "basana kadar yazılmaz.",
        unsafe_allow_html=True)

    if "editor_version" not in st.session_state:
        st.session_state.editor_version = 0

    edited = st.data_editor(
        assets_to_editor(assets),
        width="stretch", hide_index=True, num_rows="dynamic",
        key=f"asset_editor_{st.session_state.editor_version}",
        disabled=["Değerleme"],
        column_config={
            "Sembol": st.column_config.TextColumn(
                width="small", help="Ekranda görünen ad"),
            "Fiyat Sembolü": st.column_config.TextColumn(
                width="small", help="Kaynaktaki tam sembol: THYAO.IS, BTC-USD, MAC"),
            "Kaynak": st.column_config.SelectboxColumn(
                options=list(SOURCE_LABELS.values()), width="small", required=True),
            "Değerleme": st.column_config.TextColumn(
                width="small",
                help="Otomatik: Adet yazarsanız canlı fiyatlanır, boş "
                     "bırakırsanız 'Diğer' olur ve Son Değer kullanılır"),
            "Para Birimi": st.column_config.SelectboxColumn(
                options=CURRENCIES, width="small", required=True),
            "Ana Sınıf": st.column_config.SelectboxColumn(
                options=ANA_SINIFLAR, width="small", required=True),
            "Alt Sınıf": st.column_config.TextColumn(width="small"),
            "Sektör": st.column_config.TextColumn(width="small"),
            "Hesap": st.column_config.TextColumn(
                width="small", help="Aynı sembol farklı kurumdaysa burayı doldurun"),
            "Birim": st.column_config.SelectboxColumn(
                options=UNIT_OPTIONS, width="small",
                help="Sadece altın/gümüş için; diğerlerinde 'Yok'"),
            "Adet": st.column_config.NumberColumn(format="%.4f", min_value=0.0),
            "Birim Maliyet": st.column_config.NumberColumn(
                format="%.4f", min_value=0.0,
                help="Canlı modda birim maliyet, kova modunda toplam maliyet"),
            "Maliyet Para Birimi": st.column_config.SelectboxColumn(
                options=CURRENCIES, width="small", required=True,
                help="Maliyet fiyattan farklı para biriminde olabilir: BIST "
                     "hissesinin fiyatı TRY iken maliyeti USD olabilir. "
                     "Çevrim her açılışta güncel kurla yapılır."),
            "Son Değer": st.column_config.NumberColumn(
                format="%.2f", min_value=0.0,
                help="Adet girilmediğinde kullanılan güncel toplam tutar"),
            "Notlar": st.column_config.TextColumn(width="medium"),
        },
    )

    b1, b2, b3 = st.columns([1, 1, 3])
    if b1.button("💾 Kaydet", type="primary", width="stretch"):
        new_assets, problems = editor_to_assets(edited)
        removed = len(assets) - len(new_assets)
        for p in problems:
            st.warning(p, icon="⚠️")
        st.session_state.assets = new_assets
        msg = f"portföy düzenlendi ({len(new_assets)} pozisyon)"
        if save_assets(store, new_assets, msg):
            cached_snapshot.clear()
            st.success(f"{len(new_assets)} pozisyon kaydedildi"
                       + (f", {removed} satır silindi." if removed > 0 else "."))
            st.rerun()
    if b2.button("↩️ Değişiklikleri geri al", width="stretch"):
        st.session_state.editor_version += 1
        st.rerun()

    if not df.empty:
        section("Hesaplanmış görünüm")
        view = an.convert_columns(
            df[["Sembol", "Ana Sınıf", "Alt Sınıf", "Sektör", "Değerleme",
                "Para Birimi", "Maliyet Para Birimi", "Adet", "Fiyat", "K/Z %",
                "Değer (TRY)", "Ağırlık %", "Hata"]], GOSTER, snap.fx)
        st.dataframe(
            view, width="stretch", hide_index=True,
            column_config={
                "Adet": st.column_config.NumberColumn(format="%.4f"),
                "Fiyat": st.column_config.NumberColumn(format="%.4f"),
                "K/Z %": st.column_config.NumberColumn(format="%.2f%%"),
                f"Değer ({GOSTER})": st.column_config.NumberColumn(format="%.0f"),
                "Ağırlık %": st.column_config.ProgressColumn(
                    format="%.1f%%", min_value=0.0,
                    max_value=float(df["Ağırlık %"].max(skipna=True) or 100)),
            })
        st.download_button("⬇️ CSV indir",
                           view.to_csv(index=False).encode("utf-8-sig"),
                           "portfoy.csv", "text/csv")

# ========================== DEĞER GÜNCELLE (KOVA) ==========================
with tab_kova:
    st.markdown(
        "Canlı fiyatı olmayan kovaların (aracı kurum bakiyesi, gayrimenkul, "
        "alacak…) güncel değerini buradan girin. **Adet** hücresine sıfırdan "
        "büyük bir sayı yazıp kaydederseniz o satır kalıcı olarak canlı "
        "fiyatlamaya geçer.")

    kova_rows = [a for a in assets if a.get("valuation") == VAL_VALUE]
    if not kova_rows:
        st.info("Elle değerlenen pozisyon yok — her şey canlı fiyatla hesaplanıyor.")
    else:
        live = {a["symbol"]: snap.quotes.get(a["symbol"]) for a in kova_rows}
        edit_df = pd.DataFrame([{
            "Pozisyon": a.get("display") or a["symbol"],
            "Ana Sınıf": a.get("ana_sinif", ""),
            "Sembol": a["symbol"],
            # Kaynağı "elle fiyat" olan satırda canlı fiyat yoktur; oraya
            # kovanın kendi tutarını yazmak kafa karıştırıcı olurdu.
            "Canlı Birim Fiyat": (
                getattr(live.get(a["symbol"]), "price", None)
                if (a.get("source") not in (SRC_MANUAL, SRC_CASH)
                    and getattr(live.get(a["symbol"]), "ok", False))
                else None),
            "Para Birimi": a.get("currency", "TRY"),
            "Güncel Değer": float(a.get("manual_price") or 0.0),
            "Toplam Maliyet": float(a.get("avg_cost") or 0.0),
            "Adet": float(a.get("qty") or 0.0),
            "_key": asset_key(a),
        } for a in kova_rows])

        kova_edited = st.data_editor(
            edit_df, width="stretch", hide_index=True, num_rows="fixed",
            disabled=["Pozisyon", "Ana Sınıf", "Sembol", "Canlı Birim Fiyat",
                      "Para Birimi", "_key"],
            column_config={
                "_key": None,
                "Canlı Birim Fiyat": st.column_config.NumberColumn(format="%.4f"),
                "Güncel Değer": st.column_config.NumberColumn(
                    format="%.2f", min_value=0.0),
                "Toplam Maliyet": st.column_config.NumberColumn(
                    format="%.2f", min_value=0.0),
                "Adet": st.column_config.NumberColumn(format="%.4f", min_value=0.0),
            },
            key="kova_editor")

        st.caption("İpucu: Adet ≈ Güncel Değer ÷ Canlı Birim Fiyat")

        if st.button("💾 Kaydet", type="primary", width="stretch", key="kova_save"):
            by_key = {r["_key"]: r for _, r in kova_edited.iterrows()}
            changed, promoted = 0, []
            for a in st.session_state.assets:
                row = by_key.get(asset_key(a))
                if row is None:
                    continue
                new_val = float(row["Güncel Değer"])
                new_cost = float(row["Toplam Maliyet"])
                new_qty = float(row["Adet"] or 0.0)
                touched = False
                if new_qty > 0 and a.get("source") != SRC_MANUAL:
                    a["valuation"] = VAL_QTY
                    a["qty"] = new_qty
                    a["avg_cost"] = new_cost / new_qty if new_qty else 0.0
                    a["manual_price"] = None
                    promoted.append(a.get("display") or a["symbol"])
                    touched = True
                elif (float(a.get("manual_price") or 0) != new_val
                      or float(a.get("avg_cost") or 0) != new_cost):
                    a["manual_price"] = new_val
                    a["avg_cost"] = new_cost
                    touched = True
                changed += int(touched)

            if not changed:
                st.info("Değişiklik yok.")
            elif save_assets(store, st.session_state.assets,
                             f"değer güncelleme ({changed} pozisyon)"):
                cached_snapshot.clear()
                if promoted:
                    st.success("Canlı fiyatlamaya geçirildi: " + ", ".join(promoted))
                st.success(f"{changed} pozisyon kaydedildi.")
                st.rerun()

# ============================== YENİ VARLIK ================================
with tab_ekle:
    st.markdown("Sembolü yazın — sınıf, para birimi ve fiyat kaynağı otomatik dolar.")
    sym_in = st.text_input(
        "Sembol / Kod", placeholder="ALKA · NVDA · MAC · BTC · ALTIN-CEYREK · NAKIT-USD",
        label_visibility="collapsed")

    @st.cache_resource(ttl=900, show_spinner=False)
    def cached_probe(raw: str) -> list:
        """
        Sembolü gerçek kaynaklarda yoklar (15 dk önbellekli).

        cached_snapshot ile aynı sebeple cache_resource: probe_symbol
        yerel bir dataclass olan Candidate listesi döndürür, cache_data
        bunu pickle edemez (bkz. cached_snapshot açıklaması).
        """
        return px.probe_symbol(raw)

    if sym_in.strip():
        try:
            guess = auto_fill_asset(sym_in)
        except ValueError as exc:
            st.error(str(exc))
            guess = None

        if guess:
            # Canlı yoklama: 'ASELS' BIST mi ABD mi, 'MAC' fon mu — koda bakarak
            # kesin bilinemez. Kaynaklara sorup gerçekten fiyat döneni seçiyoruz.
            with st.spinner("Sembol kaynaklarda aranıyor…"):
                adaylar = cached_probe(sym_in.strip())

            if adaylar:
                etiketler = [
                    f"{c.label} — {c.symbol} · {c.price:,.4f} {c.currency}"
                    for c in adaylar]
                sec = 0
                if len(adaylar) > 1:
                    st.warning(
                        f"Bu kod {len(adaylar)} farklı piyasada bulundu. "
                        f"Hangisi olduğunu seçin.", icon="⚠️")
                    sec = etiketler.index(
                        st.radio("Doğrulanan kaynaklar", etiketler,
                                 label_visibility="collapsed", key="aday_sec"))
                else:
                    st.success(f"Doğrulandı — {etiketler[0]}", icon="✅")

                aday = adaylar[sec]
                sinif = classify_symbol(aday.symbol, aday.source)
                guess = dict(guess)
                guess.update({"symbol": aday.symbol, "source": aday.source,
                              "currency": aday.currency, **sinif})
                if guess["ana_sinif"] == "Diğer":
                    guess.update(sinif)
                st.caption(f"Otomatik sınıf: **{guess['ana_sinif']} · "
                           f"{guess['alt_sinif']} · {guess['sektor']}**")
            elif guess["guessed"]:
                st.info("Bu kod hiçbir kaynakta bulunamadı; aşağıdaki tahmini "
                        "alanları kontrol edip elle düzeltin.", icon="🔎")
            else:
                st.success(f"Tanındı — {guess['ana_sinif']} · {guess['alt_sinif']} "
                           f"· {guess['sektor']}", icon="✅")

            with st.form("add_form"):
                r1 = st.columns(3)
                symbol = r1[0].text_input("Fiyat sembolü", guess["symbol"])
                source = r1[1].selectbox(
                    "Fiyat kaynağı", list(SOURCE_LABELS),
                    index=list(SOURCE_LABELS).index(guess["source"]),
                    format_func=lambda s: SOURCE_LABELS[s])
                currency = r1[2].selectbox(
                    "Para birimi", CURRENCIES,
                    index=CURRENCIES.index(guess["currency"])
                    if guess["currency"] in CURRENCIES else 0)

                r2 = st.columns(3)
                ana = r2[0].selectbox(
                    "Ana sınıf", ANA_SINIFLAR,
                    index=ANA_SINIFLAR.index(guess["ana_sinif"])
                    if guess["ana_sinif"] in ANA_SINIFLAR else len(ANA_SINIFLAR) - 1)
                alt = r2[1].text_input("Alt sınıf", guess["alt_sinif"])
                sektor = r2[2].text_input("Sektör", guess["sektor"])

                r3 = st.columns(3)
                qty = r3[0].number_input("Adet / Gram", min_value=0.0, value=0.0,
                                         step=1.0, format="%.4f")
                cost = r3[1].number_input("Birim maliyet", min_value=0.0, value=0.0,
                                          step=0.01, format="%.4f")
                hesap = r3[2].text_input("Hesap / Kurum", guess.get("hesap", ""),
                                         placeholder="Midas, VB, YK…")

                unit = None
                manual_price = None
                if source in (SRC_GOLD, SRC_SILVER):
                    units = list(METAL_UNITS)
                    cur_unit = (guess.get("unit") or "GRAM").upper()
                    unit = st.selectbox("Birim", units,
                                        index=units.index(cur_unit)
                                        if cur_unit in units else 0)
                manual_price = st.number_input(
                    "Güncel toplam değer (adet girmeyecekseniz)",
                    min_value=0.0, value=0.0, format="%.2f",
                    help="Adet boş bırakılırsa bu tutar kullanılır ve varlık "
                         "grafiklerde sınıfının 'Diğer' kutusunda toplanır.")

                mode = st.radio(
                    "Bu pozisyon zaten varsa", ["add", "replace"], horizontal=True,
                    format_func=lambda m: "Üzerine ekle (ortalama maliyet güncellenir)"
                    if m == "add" else "Tamamen değiştir")

                submitted = st.form_submit_button("Portföye kaydet", width="stretch",
                                                  type="primary")

            if submitted:
                # Adet girilmemişse satır otomatik "Diğer" olur ve son değer
                # kullanılır; kullanıcıyı adet girmeye zorlamıyoruz.
                if qty <= 0 and not manual_price:
                    st.error("Ya adet ya da güncel toplam değer girmelisiniz.")
                else:
                    record = normalize_asset({
                        "symbol": symbol.strip(),
                        "display": (guess["display"] or symbol).strip().upper(),
                        "source": source, "currency": currency,
                        "ana_sinif": ana, "alt_sinif": alt.strip() or "Diğer",
                        "sektor": sektor.strip() or "Diğer",
                        "qty": float(qty), "avg_cost": float(cost),
                        "hesap": hesap.strip(), "unit": unit,
                        "manual_price": manual_price, "notlar": "",
                        "valuation": VAL_QTY if qty > 0 else VAL_VALUE,
                    })
                    st.session_state.assets = an.merge_position(
                        st.session_state.assets, record, mode=mode)
                    if save_assets(store, st.session_state.assets,
                                   f"portföy: {record['display']} eklendi"):
                        cached_snapshot.clear()
                        st.success(f"{record['display']} kaydedildi.")
                        st.rerun()

# ============================== AYARLAR ====================================
with tab_ice:
    section("Dosyadan içe aktar")
    st.caption(
        "Bluecoins, MyStocksPortfolio ya da bankanızdan aldığınız dökümü "
        "tabloya çevirip yükleyin. **Hiçbir şey siz önizlemeyi onaylamadan "
        "değişmez.**")

    ia_ust = st.columns([3, 2])
    ia_dosya = ia_ust[0].file_uploader(
        "CSV, Excel veya JSON", type=["csv", "xlsx", "xlsm", "xls", "json"],
        key="ia_upload")
    ia_ust[1].download_button(
        "⬇️ Boş şablon indir (CSV)", imp.ornek_csv().encode("utf-8"),
        "aether_sablon.csv", "text/csv", width="stretch")
    ia_ust[1].caption(
        "Zorunlu tek sütun **sembol**. Diğerleri boş bırakılırsa otomatik "
        "doldurulur.")

    if ia_dosya is None:
        with st.expander("Sütun başlıkları nasıl yazılmalı?"):
            st.markdown(
                "Başlıklar Türkçe/İngilizce, büyük/küçük harf ve aksan farkı "
                "gözetilmeden tanınır. Sayılarda hem `1.234,56` hem "
                "`1,234.56` biçimi okunur.")
            st.dataframe(pd.DataFrame(
                [{"Alan": ia_alan, "Kabul edilen başlıklar": ", ".join(ia_adlar)}
                 for ia_alan, ia_adlar in imp.FIELD_ALIASES.items()]),
                width="stretch", hide_index=True)
    else:
        try:
            ia_ham = imp.read_any(ia_dosya.getvalue(), ia_dosya.name)
            ia_bulunan = imp.sniff(ia_ham)

            ia_orta = st.columns([2, 2, 3])
            ia_fmt = ia_orta[0].selectbox(
                "Biçim", list(imp.FORMAT_LABELS),
                index=list(imp.FORMAT_LABELS).index(ia_bulunan),
                format_func=lambda k: imp.FORMAT_LABELS[k], key="ia_fmt")
            ia_hesap = ia_orta[1].text_input(
                "Varsayılan hesap", value="",
                help="Dosyada 'hesap' sütunu yoksa bütün satırlara bu yazılır.",
                key="ia_hesap")
            ia_mod = ia_orta[2].radio(
                "Birleştirme kipi", list(imp.MODE_LABELS),
                format_func=lambda k: imp.MODE_LABELS[k], key="ia_mod")

            ia_gelen = imp.parse(ia_ham, ia_fmt, ia_hesap.strip())
            ia_fark = imp.diff(assets, ia_gelen, ia_mod)

            section("Önizleme")
            st.markdown(f"**{len(ia_gelen)} satır okundu** — {ia_fark.ozet}")

            if ia_fark.silinen:
                st.warning(
                    f"Bu kip **{len(ia_fark.silinen)} satırı silecek**. "
                    "Aşağıdaki listede beklemediğiniz bir şey varsa kipi "
                    "değiştirin.")

            ia_tablo = imp.diff_table(ia_fark)
            if ia_tablo.empty:
                st.info("Dosya portföyle birebir aynı — değişecek bir şey yok.")
            else:
                st.dataframe(ia_tablo, width="stretch", hide_index=True)

            if not ia_fark.bos_mu():
                st.caption(
                    "Uygulamadan önce **Ayarlar → Yedek → my_assets.json "
                    "indir** ile bir kopya almanız önerilir.")
                if st.button("✅ Bu değişiklikleri uygula", type="primary",
                             key="ia_uygula"):
                    st.session_state.assets = imp.apply(
                        assets, ia_gelen, ia_mod)
                    if save_assets(store, st.session_state.assets,
                                   f"içe aktarma ({ia_dosya.name})"):
                        cached_snapshot.clear()
                        st.session_state.editor_version = \
                            st.session_state.get("editor_version", 0) + 1
                        st.success(
                            f"Uygulandı — {ia_fark.ozet}. "
                            f"Portföy {len(st.session_state.assets)} satır.")
                        st.rerun()
        except imp.ImportError_ as exc:
            st.error(f"Dosya okunamadı: {exc}")
        except Exception as exc:  # beklenmeyen hata portföyü bozmasın
            st.error(f"Beklenmeyen hata: {exc}")

with tab_ayar:
    section("Sürüm")
    st.code(f"Yapı kimliği : {SURUM}\n"
            f"Derlenme     : {SURUM_ZAMAN or 'bilinmiyor'}", language="text")
    st.caption(
        "Yapı kimliği dosyanın İÇERİĞİNDEN üretilir. Yeni bir app.py "
        "yükledikten sonra buradaki kimlik değişmediyse yayındaki sürüm hâlâ "
        "eskidir — dosya yanlış depoya gitmiş, yanlış dalda kalmış ya da "
        "uygulama yeniden başlatılmamış demektir.")

    section("Depolama")
    st.code(store.describe(), language="text")
    if store.backend == "local":
        st.markdown(
            "Kalıcı kayıt için Streamlit **Settings → Secrets**:\n\n"
            "```toml\n[github]\ntoken  = \"github_pat_...\"\n"
            "repo   = \"kullanici/depo\"\nbranch = \"main\"\n"
            "path   = \"my_assets.json\"\n```")
    else:
        st.caption("Jetonun gerçekten yazma yetkisi olup olmadığını sınamak "
                   "portföyünüzü riske atmaz: sınama, dosyayı kendi mevcut "
                   "içeriğiyle yeniden yazar.")
        if st.button("🔍 Depolama iznini sına", key="ayar_depo_sina"):
            for _ad, _st in (("Portföy", store), ("Tarihçe", hist_store)):
                try:
                    _mevcut = _st.load(default=[])
                except StorageError as exc:
                    st.error(f"**{_ad} — OKUMA başarısız.** {exc}")
                    continue
                try:
                    _st.save(_mevcut.data, f"izin sınaması ({_ad.lower()})")
                    st.success(f"**{_ad}** — okuma ve yazma çalışıyor "
                               f"(`{_st.path}`).")
                except StorageError as exc:
                    _metin = str(exc)
                    st.error(f"**{_ad} — YAZMA başarısız.** {_metin}")
                    if "not accessible by personal access token" in _metin \
                            or "HTTP 403" in _metin:
                        st.markdown(
                            "Bu mesaj jetonun **yazma yetkisi olmadığını** "
                            "söyler; depo adı ya da dosya yolu yanlış olsaydı "
                            "404 alırdınız. GitHub → **Settings → Developer "
                            "settings → Personal access tokens → "
                            "Fine-grained tokens** → jetonunuz → "
                            "**Repository permissions → Contents**'i "
                            "*Read and write* yapın. Depo bir kuruluşa aitse "
                            "kuruluş yöneticisinin jetonu ayrıca onaylaması "
                            "gerekir. Değişiklikten sonra Streamlit'te "
                            "**Reboot app** deyin.")
                    elif "HTTP 404" in _metin:
                        st.markdown(
                            "404: `repo`, `branch` veya `path` değerlerinden "
                            "biri yanlış — ya da jeton bu depoyu hiç görmüyor.")
                    elif "HTTP 409" in _metin or "HTTP 422" in _metin:
                        st.markdown(
                            "Dosya başka bir yerden değiştirilmiş. Sayfayı "
                            "yenileyip tekrar deneyin.")

    section("Fiyat kaynağı durumu")
    if not df.empty:
        diag = df[["Sembol", "Yahoo Sembol", "Kaynak", "Değerleme", "Fiyat",
                   "Fiyat OK", "Hata"]]
        st.dataframe(diag, width="stretch", hide_index=True,
                     column_config={"Fiyat": st.column_config.NumberColumn(
                         format="%.4f")})

    section("Yedek")
    y1, y2 = st.columns(2)
    y1.download_button(
        "⬇️ my_assets.json indir",
        json.dumps(assets, indent=2, ensure_ascii=False).encode("utf-8"),
        "my_assets.json", "application/json", width="stretch")
    up = y2.file_uploader("Yedekten yükle (mevcut portföyün üzerine yazar)",
                          type="json")
    if up is not None and st.button("📥 Yüklemeyi uygula"):
        try:
            data = json.loads(up.getvalue().decode("utf-8"))
            st.session_state.assets = [normalize_asset(a) for a in data]
            if save_assets(store, st.session_state.assets, "yedekten geri yükleme"):
                cached_snapshot.clear()
                st.session_state.editor_version = \
                    st.session_state.get("editor_version", 0) + 1
                st.success("Yedek yüklendi.")
                st.rerun()
        except Exception as exc:
            st.error(f"Dosya okunamadı: {exc}")
