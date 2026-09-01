"""
Varlık sınıflandırma ve otomatik tanıma motoru.

TASARIM KARARI (önemli):
  - "source"  = fiyatın NEREDEN çekileceği (teknik)
  - "ana_sinif / alt_sinif / sektor" = varlığın NASIL gruplanacağı (sunum)
Bu ikisi ayrıdır. Eski kodda tek bir "type" alanı her iki işi birden yapıyordu,
bu yüzden sınıflandırmayı değiştirmek fiyat çekmeyi bozuyordu.

Sınıflandırma hiyerarşisini değiştirmek için sadece HIERARCHY ve
SMART_DATABASE'i düzenleyin; başka hiçbir dosyaya dokunmanız gerekmez.
"""

from __future__ import annotations

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

    # 2) Sembolün şeklinden tahmin
    if BIST_SUFFIX_RE.search(text):
        data = {"symbol": text, "display": base, "source": SRC_YAHOO, "currency": "TRY",
                "ana_sinif": "Hisse Senedi", "alt_sinif": "BIST", "sektor": "Diğer BIST"}
    elif CRYPTO_SUFFIX_RE.search(text):
        data = {"symbol": text, "display": base, "source": SRC_YAHOO, "currency": "USD",
                "ana_sinif": "Kripto", "alt_sinif": "Altcoin", "sektor": "Diğer Kripto"}
    elif TEFAS_CODE_RE.match(base):
        data = {"symbol": base, "display": base, "source": SRC_TEFAS, "currency": "TRY",
                "ana_sinif": "Fon", "alt_sinif": "TEFAS",
                "sektor": TEFAS_KNOWN.get(base, "Yatırım Fonu")}
    elif "=" in text or "^" in text:  # GC=F, ^GSPC gibi Yahoo özel sembolleri
        data = {"symbol": text, "display": text, "source": SRC_YAHOO, "currency": "USD",
                "ana_sinif": "Diğer", "alt_sinif": "Endeks / Vadeli", "sektor": "Diğer"}
    else:
        data = {"symbol": base, "display": base, "source": SRC_YAHOO, "currency": "USD",
                "ana_sinif": "Hisse Senedi", "alt_sinif": "ABD", "sektor": "Diğer ABD"}

    data["unit"] = None
    data["guessed"] = True
    return _finalize(data)


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
    item.setdefault("hesap", "")
    item.setdefault("notlar", "")
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
