"""
AETHER NEXUS — Canlı portföy takip uygulaması (TEK DOSYA SÜRÜMÜ)

Bu dosya build_single_file.py tarafından üretilmiştir; elle düzenlemeyin.
Kaynak: portfolio/classification.py, prices.py, storage.py, analytics.py, app.py

Çalıştırma:  streamlit run aether_nexus.py
"""

from __future__ import annotations


# ==========================================================================
# KAYNAK: portfolio/classification.py
# ==========================================================================
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

# ==========================================================================
# KAYNAK: portfolio/prices.py
# ==========================================================================
"""
Canlı fiyat motoru.

Eski koddaki sorunlar ve çözümleri:
  * `except: pass`  -> hata yutuluyordu, fiyat sessizce eskiden kalıyordu.
    Artık her varlık için (fiyat, kaynak, hata) üçlüsü döner, arayüz gösterir.
  * TEFAS HTML scraping -> sayfa JavaScript ile dolduğu için BeautifulSoup
    her zaman boş dönerdi. Artık sitenin kendi POST API'si kullanılıyor.
  * `if True else` -> anlamsız ifade, kur çekilemezse uygulama çöküyordu.
    Artık kur başarısız olursa açıkça uyarı verilir.
  * Her sembol için ayrı yfinance çağrısı -> yavaş. Artık tek toplu çağrı.
  * Altın sadece gram varsayılıyordu -> artık çeyrek/tam/ons birimleri var.
"""


import datetime as dt
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Iterable

import requests


log = logging.getLogger(__name__)

TROY_OUNCE_G = 31.1034768

YAHOO_FX = {"USDTRY": "TRY=X", "EURTRY": "EURTRY=X", "EURUSD": "EURUSD=X"}
YAHOO_GOLD = "GC=F"      # Altın vadeli, USD/ons
YAHOO_SILVER = "SI=F"    # Gümüş vadeli, USD/ons

TEFAS_URL = "https://www.tefas.gov.tr/api/DB/BindHistoryInfo"
TEFAS_REFERER = "https://www.tefas.gov.tr/TarihselVeriler.aspx"


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

    @property
    def usdtry(self) -> float | None:
        return self.fx.get("USDTRY")


# ---------------------------------------------------------------------------
# YAHOO FINANCE
# ---------------------------------------------------------------------------
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
    """Verilen sembollerin son kapanışlarını tek toplu çağrıyla getirir."""
    tickers = sorted({t for t in tickers if t})
    if not tickers:
        return {}

    import yfinance as yf  # yerel import: test ederken ağ gerekmesin

    out: dict[str, float] = {}
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
                px = _last_close(df, tk)
                if px is not None and px > 0:
                    out[tk] = px
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
                    val = float(hist["Close"].dropna().iloc[-1])
                    if val > 0:
                        out[tk] = val
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


def fetch_tefas(codes: Iterable[str], *, lookback_days: int = 15,
                timeout: int = 20) -> dict[str, float]:
    """
    TEFAS fon fiyatlarını sitenin kendi API'sinden çeker.
    Dönen JSON: {"data": [{"TARIH": <epoch_ms>, "FONKODU": "MAC", "FIYAT": 12.34, ...}]}
    Her fon için en güncel tarihli FIYAT alınır.
    """
    codes = sorted({c.strip().upper() for c in codes if c and c.strip()})
    if not codes:
        return {}

    session = _tefas_session()
    try:
        session.get(TEFAS_REFERER, timeout=timeout)  # çerez almak için
    except Exception as exc:
        log.info("TEFAS ısınma isteği başarısız (önemsiz): %s", exc)

    end = dt.date.today()
    start = end - dt.timedelta(days=lookback_days)
    out: dict[str, float] = {}

    for code in codes:
        payload = {
            "fontip": "YAT",
            "sfontur": "",
            "fonkod": code,
            "fongrup": "",
            "bastarih": start.strftime("%d.%m.%Y"),
            "bittarih": end.strftime("%d.%m.%Y"),
            "fonturkod": "",
            "fonunvantip": "",
            "strperiod": "1,1,1,1,1,1,1",
            "islemdurum": "1",
        }
        try:
            resp = session.post(TEFAS_URL, data=payload, timeout=timeout)
            resp.raise_for_status()
            rows = (resp.json() or {}).get("data") or []
            rows = [r for r in rows if r.get("FIYAT") not in (None, "")]
            if not rows:
                continue
            rows.sort(key=lambda r: r.get("TARIH") or 0)
            price = float(str(rows[-1]["FIYAT"]).replace(",", "."))
            if price > 0:
                out[code] = price
        except Exception as exc:
            log.warning("TEFAS fiyatı alınamadı (%s): %s", code, exc)

    return out


# ---------------------------------------------------------------------------
# ANA GİRİŞ NOKTASI
# ---------------------------------------------------------------------------
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

    try:
        prices = fetch_yahoo(yahoo_tickers | infra)
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
    if tefas_codes:
        try:
            tefas_prices = fetch_tefas(tefas_codes)
        except Exception as exc:
            snap.errors.append(f"TEFAS'a ulaşılamadı: {exc}")
        # Sadece değeri fiyata BAĞLI olan satırlar için uyar; kova satırlarının
        # değeri elle girilen tutardan gelir, fiyat bilgisi orada sadece yardımcıdır.
        critical = {a["symbol"].upper() for a in assets
                    if a.get("source") == SRC_TEFAS
                    and a.get("valuation") != "value"}
        missing = (tefas_codes & critical) - set(tefas_prices)
        if missing:
            snap.errors.append(
                "TEFAS fiyatı bulunamadı: " + ", ".join(sorted(missing))
            )

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

    return snap


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
"""
Kalıcı depolama: GitHub Contents API üzerinden JSON commit'leme.

NEDEN: Streamlit Community Cloud'da dosya sistemi geçicidir. Uygulama uykuya
girip uyandığında ya da yeniden deploy olduğunda `open(...,"w")` ile yazdığınız
my_assets.json SİLİNİR. Eklediğiniz varlıklar kaybolur. Bu yüzden portföy
kaydı doğrudan GitHub deposuna commit edilir; depo tek doğruluk kaynağıdır.

KURULUM
-------
1) GitHub'da ince taneli (fine-grained) bir kişisel erişim jetonu üretin:
   Settings > Developer settings > Personal access tokens > Fine-grained tokens
   - Repository access: sadece bu depo
   - Permissions > Repository permissions > Contents: Read and write
2) Streamlit Cloud > App > Settings > Secrets alanına şunu yapıştırın:

   [github]
   token  = "github_pat_..."
   repo   = "kullanici-adi/depo-adi"
   branch = "main"
   path   = "my_assets.json"

Jeton yoksa uygulama otomatik olarak yerel dosya moduna düşer (lokal geliştirme).
"""


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

        for attempt in range(2):
            if self._sha:
                payload["sha"] = self._sha
            else:
                payload.pop("sha", None)
            r = requests.put(self._url(), headers=self._headers(),
                             json=payload, timeout=25)
            if r.status_code in (200, 201):
                self._sha = (r.json().get("content") or {}).get("sha")
                return self._sha or "ok"
            if r.status_code == 409 and attempt == 0:
                # Başka bir yerden commit gelmiş; sha'yı tazeleyip bir kez daha dene
                log.info("GitHub 409 çakışması, sha tazeleniyor.")
                try:
                    self.load()
                except StorageError:
                    pass
                continue
            raise StorageError(
                f"GitHub'a yazılamadı (HTTP {r.status_code}): {r.text[:300]}"
            )
        raise StorageError("GitHub'a yazılamadı: çakışma çözülemedi.")


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
"""
Portföy hesaplamaları ve grafik verisi üretimi.

Buradaki iki kritik düzeltme:
  1) Sankey düğüm çakışması: eski kodda etiketler tek bir sözlükte toplanıyordu.
     Bir sektör adı bir alt sınıf adıyla (veya bir sembol bir sektörle) aynı
     olduğunda düğümler birleşiyor, akışlar yanlış yere gidiyordu. Artık her
     düğümün kimliği tam yol ("Hisse Senedi > BIST > Bankacılık") üzerinden
     üretiliyor; etikette sadece son parça gösteriliyor.
  2) Toplam kâr/zarar yüzdesi: satır bazlı yüzdelerin ortalaması yanlıştır.
     Toplam, TL cinsinden maliyet ve değer üzerinden hesaplanır.
"""


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
    return float("nan")


def build_dataframe(assets: list[dict[str, Any]], quotes: dict[str, Any],
                    fx: dict[str, float] | None = None) -> pd.DataFrame:
    """Varlık listesi + fiyatlardan hesaplanmış tabloyu üretir."""
    fx = fx or {}
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
            "Değerleme": "Kova (elle)" if kova else "Adet × Fiyat",
            "Adet": qty,
            "Maliyet": cost,
            "Fiyat": price_val,
            "Maliyet (TRY)": maliyet_nat * rate,
            "Değer (TRY)": deger_nat * rate,
            "K/Z (TRY)": (deger_nat - maliyet_nat) * rate,
            "K/Z %": ((deger_nat - maliyet_nat) / maliyet_nat * 100.0)
                     if maliyet_nat > 0 else float("nan"),
            "Fiyat OK": ok,
            "Hata": "" if ok else err,
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    total = df["Değer (TRY)"].sum(skipna=True)
    df["Ağırlık %"] = (df["Değer (TRY)"] / total * 100.0) if total else float("nan")
    return df.sort_values("Değer (TRY)", ascending=False, na_position="last")


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
    if df.empty:
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


def allocation(df: pd.DataFrame, level: str) -> pd.DataFrame:
    """Bir hiyerarşi seviyesine göre dağılım tablosu."""
    if df.empty or level not in df.columns:
        return pd.DataFrame(columns=[level, "Değer (TRY)", "Pay %"])
    g = (df.groupby(level, dropna=False)["Değer (TRY)"]
           .sum(min_count=1).reset_index())
    total = g["Değer (TRY)"].sum(skipna=True)
    g["Pay %"] = (g["Değer (TRY)"] / total * 100.0) if total else float("nan")
    return g.sort_values("Değer (TRY)", ascending=False)


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

    root_key = "__ROOT__"
    node_ids: dict[str, int] = {root_key: 0}
    labels: list[str] = ["Portföy"]
    paths: list[str] = ["Portföy"]

    top_level = levels[0]
    top_colors = color_map(
        list(allocation(valid, top_level)[top_level].astype(str))
    )
    node_colors: list[str] = [ACCENT]
    node_group: list[str] = ["Portföy"]

    def node(path: tuple[str, ...], group: str) -> int:
        key = " > ".join(path)
        if key not in node_ids:
            node_ids[key] = len(labels)
            labels.append(path[-1])
            paths.append(key)
            node_colors.append(top_colors.get(group, OTHER_COLOR))
            node_group.append(group)
        return node_ids[key]

    src: list[int] = []
    tgt: list[int] = []
    val: list[float] = []
    link_colors: list[str] = []

    for depth in range(len(levels)):
        keys = levels[: depth + 1]
        grouped = valid.groupby([valid[k].fillna("Belirsiz").astype(str) for k in keys],
                                dropna=False)["Değer (TRY)"].sum(min_count=1)
        for combo, amount in grouped.items():
            if amount is None or amount <= 0:
                continue
            combo = combo if isinstance(combo, tuple) else (combo,)
            group = combo[0]
            parent = 0 if depth == 0 else node(combo[:-1], group)
            child = node(combo, group)
            src.append(parent)
            tgt.append(child)
            val.append(float(amount))
            link_colors.append(_rgba(top_colors.get(group, OTHER_COLOR), 0.35))

    return {
        "labels": labels,
        "paths": paths,
        "source": src,
        "target": tgt,
        "value": val,
        "node_colors": node_colors,
        "link_colors": link_colors,
    }


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


an = px = _Namespace()

"""
AETHER NEXUS — Canlı portföy takip uygulaması.
Streamlit üzerinde çalışır, portföyünü GitHub deposunda kalıcı tutar.

Çalıştırma:  streamlit run app.py
"""


import logging

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


logging.basicConfig(level=logging.INFO)

LEVEL_COLS = {"ana_sinif": "Ana Sınıf", "alt_sinif": "Alt Sınıf",
              "sektor": "Sektör", "display": "Sembol",
              "hesap": "Hesap", "currency": "Para Birimi"}

SOURCE_LABELS = {
    SRC_YAHOO: "Yahoo Finance (hisse / ETF / kripto)",
    SRC_TEFAS: "TEFAS (yatırım fonu)",
    SRC_GOLD: "Altın (ons üzerinden türetilir)",
    SRC_SILVER: "Gümüş (ons üzerinden türetilir)",
    SRC_CASH: "Nakit (fiyat = 1)",
    SRC_MANUAL: "Elle girilen fiyat",
}

st.set_page_config(layout="wide", page_title="AETHER NEXUS", page_icon="🌌")

st.markdown(
    """
    <style>
    .stApp { background-color: #050505; color: #e6e6e6; }
    .metric-card { background: linear-gradient(145deg,#121212 0%,#0a0a0a 100%);
        padding: 14px 16px; border-radius: 12px; border-left: 4px solid #00f3ff;
        margin-bottom: 10px; }
    .metric-title { font-size: .72rem; color: #8a8a8a; text-transform: uppercase;
        letter-spacing: .08em; }
    .metric-val { font-size: 1.7rem; font-weight: 700; color: #f2f2f2;
        line-height: 1.25; }
    .metric-sub { font-size: .78rem; color: #9a9a9a; }
    .pos { color: #199e70; } .neg { color: #e66767; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# DEPOLAMA
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


# ---------------------------------------------------------------------------
# FİYATLAR
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def cached_snapshot(fingerprint: str, assets: list[dict]) -> px.MarketSnapshot:
    """fingerprint değişince veya 5 dakika geçince yeniden çeker."""
    return px.build_snapshot(assets)


def snapshot_fingerprint(assets: list[dict]) -> str:
    return "|".join(sorted(f"{a['symbol']}:{a.get('source')}:{a.get('unit')}"
                           for a in assets))


# ---------------------------------------------------------------------------
# ARAYÜZ
# ---------------------------------------------------------------------------
store = get_storage()

if "assets" not in st.session_state:
    st.session_state.assets = load_assets(store)
assets: list[dict] = st.session_state.assets

head_l, head_r = st.columns([3, 1])
with head_l:
    st.markdown("## 🌌 AETHER NEXUS <span style='color:#00f3ff'>LIVE</span>",
                unsafe_allow_html=True)
with head_r:
    if st.button("⚡ Fiyatları Yenile", width="stretch", type="primary"):
        cached_snapshot.clear()
        st.rerun()

if store.backend == "local":
    st.warning(
        "**Kalıcılık kapalı.** Portföy sadece geçici dosyaya yazılıyor; Streamlit "
        "Cloud uygulamayı uyuttuğunda kayıtlar silinir. Secrets içine `[github]` "
        "bölümünü ekleyin (token / repo / branch / path).",
        icon="⚠️",
    )
else:
    st.caption(f"💾 Kalıcı kayıt: {store.describe()}")

with st.spinner("Piyasa verisi çekiliyor…"):
    snap = cached_snapshot(snapshot_fingerprint(assets), assets) if assets \
        else px.MarketSnapshot(fetched_at=px._now_istanbul())

usdtry = snap.usdtry
fx_line = f"USD/TRY {usdtry:,.2f}" if usdtry else "USD/TRY —"
if snap.gold_usd_oz and usdtry:
    fx_line += f" · Gram altın ₺{snap.gold_usd_oz / px.TROY_OUNCE_G * usdtry:,.0f}"
st.caption(f"🔄 Son güncelleme: {snap.fetched_at} · {fx_line}")

for err in snap.errors:
    st.warning(err, icon="⚠️")

df = an.build_dataframe(assets, snap.quotes, snap.fx)

# --- ÖZET METRİKLER --------------------------------------------------------
if not df.empty:
    t = an.totals(df, usdtry)
    kz_cls = "pos" if t["kz_try"] >= 0 else "neg"
    sign = "+" if t["kz_try"] >= 0 else ""
    usd_txt = f"$ {t['deger_usd']:,.0f}" if usdtry else "kur yok"
    net_usd = (t["net_try"] / usdtry) if usdtry else float("nan")

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(
        f"<div class='metric-card'><div class='metric-title'>Varlık Toplamı</div>"
        f"<div class='metric-val'>₺ {t['deger_try']:,.0f}</div>"
        f"<div class='metric-sub'>{usd_txt}</div></div>", unsafe_allow_html=True)
    c2.markdown(
        f"<div class='metric-card'><div class='metric-title'>Net Değer "
        f"(borç düşülmüş)</div>"
        f"<div class='metric-val'>₺ {t['net_try']:,.0f}</div>"
        f"<div class='metric-sub'>borç ₺{t['borc_try']:,.0f}"
        + (f" · $ {net_usd:,.0f}" if usdtry else "") + "</div></div>",
        unsafe_allow_html=True)
    c3.markdown(
        f"<div class='metric-card'><div class='metric-title'>Kâr / Zarar</div>"
        f"<div class='metric-val {kz_cls}'>{sign}₺ {t['kz_try']:,.0f}</div>"
        f"<div class='metric-sub {kz_cls}'>{sign}%{t['kz_pct']:.2f} · "
        f"maliyet ₺{t['maliyet_try']:,.0f}</div></div>",
        unsafe_allow_html=True)
    top = df.iloc[0] if len(df) else None
    if top is not None:
        c4.markdown(
            f"<div class='metric-card'><div class='metric-title'>En Büyük Pozisyon</div>"
            f"<div class='metric-val'>{top['Sembol']}</div>"
            f"<div class='metric-sub'>portföyün %{top['Ağırlık %']:.1f}'i · "
            f"{len(df)} pozisyon</div></div>", unsafe_allow_html=True)

    if t["eksik"]:
        st.info(f"{t['eksik']} varlığın fiyatı çekilemedi; bu satırlar toplamlara "
                f"dahil değil. Ayrıntı için 'Varlıklar' sekmesindeki Hata sütununa "
                f"bakın.", icon="ℹ️")

# --- SEKMELER --------------------------------------------------------------
tab_dag, tab_tablo, tab_kova, tab_ekle, tab_ayar = st.tabs(
    ["📊 Dağılım", "🗃️ Varlıklar", "✏️ Değer Güncelle", "➕ Yeni Varlık", "⚙️ Ayarlar"]
)

# ============================== DAĞILIM ====================================
with tab_dag:
    if df.empty or df["Değer (TRY)"].fillna(0).sum() <= 0:
        st.info("Henüz gösterilecek veri yok. 'Yeni Varlık' sekmesinden "
                "portföyünüze varlık ekleyin.")
    else:
        levels = st.multiselect(
            "Kırılım seviyeleri (sırayı değiştirebilirsiniz)",
            options=list(LEVEL_COLS.values()),
            default=[LEVEL_COLS[k] for k in HIERARCHY],
        )
        if not levels:
            levels = [LEVEL_COLS["ana_sinif"]]

        sk = an.sankey_data(df, levels)
        fig = go.Figure(go.Sankey(
            arrangement="snap",
            node=dict(pad=18, thickness=16,
                      line=dict(color="#050505", width=2),
                      label=sk["labels"], color=sk["node_colors"],
                      customdata=sk["paths"],
                      hovertemplate="%{customdata}<br>₺%{value:,.0f}<extra></extra>"),
            link=dict(source=sk["source"], target=sk["target"], value=sk["value"],
                      color=sk["link_colors"],
                      hovertemplate="%{source.label} → %{target.label}"
                                    "<br>₺%{value:,.0f}<extra></extra>"),
        ))
        fig.update_layout(height=120 + 34 * max(6, len(sk["labels"])),
                          paper_bgcolor="#050505", font=dict(color="#e6e6e6", size=13),
                          margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig, width="stretch")

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("#### Ana sınıf dağılımı")
            alloc = an.allocation(df, LEVEL_COLS["ana_sinif"])
            cmap = an.color_map(list(alloc[LEVEL_COLS["ana_sinif"]].astype(str)))
            donut = go.Figure(go.Pie(
                labels=alloc[LEVEL_COLS["ana_sinif"]], values=alloc["Değer (TRY)"],
                hole=0.58, sort=False,
                marker=dict(colors=[cmap[k] for k in alloc[LEVEL_COLS["ana_sinif"]]],
                            line=dict(color="#050505", width=2)),
                textinfo="label+percent", textposition="outside",
                hovertemplate="%{label}<br>₺%{value:,.0f} (%{percent})<extra></extra>",
            ))
            donut.update_layout(height=380, showlegend=True,
                                legend=dict(orientation="h", y=-0.12),
                                paper_bgcolor="#050505",
                                font=dict(color="#e6e6e6"),
                                margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(donut, width="stretch")
        with col_b:
            st.markdown("#### Pozisyon ağırlıkları")
            bar_df = df.dropna(subset=["Değer (TRY)"]).head(15).iloc[::-1]
            top_map = an.color_map(list(an.allocation(df, "Ana Sınıf")["Ana Sınıf"]))
            bar = go.Figure(go.Bar(
                x=bar_df["Değer (TRY)"], y=bar_df["Sembol"], orientation="h",
                marker=dict(color=[top_map.get(c, an.OTHER_COLOR)
                                   for c in bar_df["Ana Sınıf"]]),
                hovertemplate="%{y}<br>₺%{x:,.0f}<extra></extra>",
            ))
            bar.update_layout(height=380, paper_bgcolor="#050505",
                              plot_bgcolor="#050505", font=dict(color="#e6e6e6"),
                              xaxis=dict(gridcolor="#1e1e1e", zeroline=False),
                              yaxis=dict(gridcolor="#1e1e1e"),
                              margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(bar, width="stretch")

        with st.expander("Dağılım tabloları"):
            for key in ("ana_sinif", "alt_sinif", "sektor"):
                st.markdown(f"**{HIERARCHY_LABELS[key]}**")
                st.dataframe(an.allocation(df, LEVEL_COLS[key]),
                             width="stretch", hide_index=True)

# ============================== VARLIKLAR ==================================
with tab_tablo:
    if df.empty:
        st.info("Portföy boş.")
    else:
        show = df[["Sembol", "Ana Sınıf", "Alt Sınıf", "Sektör", "Değerleme",
                   "Para Birimi", "Adet", "Maliyet", "Fiyat", "K/Z %",
                   "Değer (TRY)", "Ağırlık %", "Hata"]]
        st.dataframe(
            show, width="stretch", hide_index=True,
            column_config={
                "Adet": st.column_config.NumberColumn(format="%.4f"),
                "Maliyet": st.column_config.NumberColumn(format="%.4f"),
                "Fiyat": st.column_config.NumberColumn(format="%.4f"),
                "K/Z %": st.column_config.NumberColumn(format="%.2f%%"),
                "Değer (TRY)": st.column_config.NumberColumn(format="%.0f"),
                "Ağırlık %": st.column_config.ProgressColumn(
                    format="%.1f%%", min_value=0.0,
                    max_value=float(df["Ağırlık %"].max(skipna=True) or 100)),
            },
        )
        st.download_button("⬇️ CSV indir", show.to_csv(index=False).encode("utf-8-sig"),
                           "portfoy.csv", "text/csv")

        st.markdown("#### Pozisyon sil")
        del_key = st.selectbox(
            "Silinecek pozisyon", options=[asset_key(a) for a in assets],
            format_func=lambda k: k.replace("|", "  ·  ").rstrip(" ·"),
            index=None, placeholder="Seçin…",
        )
        if del_key and st.button("🗑️ Sil", type="secondary"):
            st.session_state.assets = [a for a in assets if asset_key(a) != del_key]
            if save_assets(store, st.session_state.assets, f"sil: {del_key}"):
                cached_snapshot.clear()
                st.success("Pozisyon silindi.")
                st.rerun()

# ========================== DEĞER GÜNCELLE (KOVA) ==========================
with tab_kova:
    st.markdown(
        "Bluecoins'teki **Adjustment** mantığının karşılığı. Bu satırların değeri "
        "elle girdiğiniz toplam tutardır. **Adet sütununa sıfırdan büyük bir sayı "
        "yazdığınız anda** o satır kalıcı olarak *Adet × canlı fiyat* moduna geçer "
        "ve bir daha elle güncelleme gerektirmez."
    )
    kova_rows = [a for a in assets if a.get("valuation") == VAL_VALUE]
    if not kova_rows:
        st.info("Elle değerlenen pozisyon yok — her şey canlı fiyatla hesaplanıyor.")
    else:
        live = {a["symbol"]: snap.quotes.get(a["symbol"]) for a in kova_rows}
        edit_df = pd.DataFrame([{
            "Pozisyon": a.get("display") or a["symbol"],
            "Ana Sınıf": a.get("ana_sinif", ""),
            "Kaynak": a.get("source", ""),
            "Sembol": a["symbol"],
            "Canlı Birim Fiyat": (getattr(live.get(a["symbol"]), "price", None)
                                  if getattr(live.get(a["symbol"]), "ok", False)
                                  else None),
            "Para Birimi": a.get("currency", "TRY"),
            "Güncel Değer": float(a.get("manual_price") or 0.0),
            "Maliyet": float(a.get("avg_cost") or 0.0),
            "Adet": float(a.get("qty") or 0.0),
            "_key": asset_key(a),
        } for a in kova_rows])

        edited = st.data_editor(
            edit_df, width="stretch", hide_index=True, num_rows="fixed",
            disabled=["Pozisyon", "Ana Sınıf", "Kaynak", "Sembol",
                      "Canlı Birim Fiyat", "Para Birimi", "_key"],
            column_config={
                "_key": None,
                "Canlı Birim Fiyat": st.column_config.NumberColumn(
                    format="%.4f",
                    help="Bu kaynağın şu anki birim fiyatı. Adedi buradan "
                         "hesaplayabilirsiniz: değer ÷ birim fiyat."),
                "Güncel Değer": st.column_config.NumberColumn(
                    format="%.2f", min_value=0.0, help="Kovanın toplam güncel tutarı"),
                "Maliyet": st.column_config.NumberColumn(
                    format="%.2f", min_value=0.0,
                    help="Bu kovaya koyduğunuz toplam para (K/Z bundan hesaplanır)"),
                "Adet": st.column_config.NumberColumn(
                    format="%.4f", min_value=0.0,
                    help="Doldurursanız satır canlı fiyatlamaya geçer"),
            },
            key="kova_editor",
        )

        st.caption("İpucu: Adet ≈ Güncel Değer ÷ Canlı Birim Fiyat")

        if st.button("💾 Kaydet", type="primary", width="stretch"):
            by_key = {r["_key"]: r for _, r in edited.iterrows()}
            changed, promoted = 0, []
            for a in st.session_state.assets:
                row = by_key.get(asset_key(a))
                if row is None:
                    continue
                new_val = float(row["Güncel Değer"])
                new_cost = float(row["Maliyet"])
                new_qty = float(row["Adet"] or 0.0)
                touched = False

                if new_qty > 0 and a.get("source") != SRC_MANUAL:
                    # Kovadan gerçek pozisyona terfi: toplam maliyeti birim
                    # maliyete çevir ki K/Z tutarlı kalsın.
                    a["valuation"] = VAL_QTY
                    a["qty"] = new_qty
                    a["avg_cost"] = (new_cost / new_qty) if new_qty else 0.0
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


# ============================== EKLE =======================================
with tab_ekle:
    st.markdown("#### 1) Sembolü girin — kalan alanlar otomatik dolar")
    sym_in = st.text_input("Sembol / Kod", placeholder="ALKA, NVDA, MAC, BTC, ALTIN-CEYREK, NAKIT-USD")

    if sym_in.strip():
        try:
            guess = auto_fill_asset(sym_in)
        except ValueError as exc:
            st.error(str(exc))
            guess = None

        if guess:
            if guess["guessed"]:
                st.info("Bu sembol veritabanında yok; tahmin edildi. Aşağıdaki "
                        "alanları kontrol edin.", icon="🔎")
            else:
                st.success(f"Tanındı: {guess['ana_sinif']} · {guess['alt_sinif']} "
                           f"· {guess['sektor']}", icon="✅")

            with st.form("add_form"):
                r1c1, r1c2, r1c3 = st.columns(3)
                symbol = r1c1.text_input("Fiyat sembolü", guess["symbol"],
                                         help="Yahoo için tam sembol (THYAO.IS, BTC-USD)")
                source = r1c2.selectbox(
                    "Fiyat kaynağı", list(SOURCE_LABELS),
                    index=list(SOURCE_LABELS).index(guess["source"]),
                    format_func=lambda s: SOURCE_LABELS[s])
                currency = r1c3.selectbox("Para birimi", ["TRY", "USD", "EUR"],
                                          index=["TRY", "USD", "EUR"].index(guess["currency"]))

                r2c1, r2c2, r2c3 = st.columns(3)
                ana = r2c1.selectbox(
                    "Ana sınıf", ANA_SINIFLAR,
                    index=ANA_SINIFLAR.index(guess["ana_sinif"])
                    if guess["ana_sinif"] in ANA_SINIFLAR else len(ANA_SINIFLAR) - 1)
                alt = r2c2.text_input("Alt sınıf", guess["alt_sinif"])
                sektor = r2c3.text_input("Sektör", guess["sektor"])

                r3c1, r3c2, r3c3 = st.columns(3)
                qty = r3c1.number_input("Adet / Gram", min_value=0.0, value=0.0,
                                        step=1.0, format="%.4f")
                cost = r3c2.number_input("Birim maliyet", min_value=0.0, value=0.0,
                                         step=0.01, format="%.4f")
                hesap = r3c3.text_input("Hesap / Kurum (opsiyonel)", guess.get("hesap", ""))

                unit = None
                manual_price = None
                if source in (SRC_GOLD, SRC_SILVER):
                    units = list(METAL_UNITS)
                    cur_unit = (guess.get("unit") or "GRAM").upper()
                    unit = st.selectbox("Birim", units,
                                        index=units.index(cur_unit) if cur_unit in units else 0)
                if source == SRC_MANUAL:
                    manual_price = st.number_input("Güncel fiyat (elle)",
                                                   min_value=0.0, value=0.0, format="%.4f")

                mode = st.radio(
                    "Bu pozisyon zaten varsa", ["add", "replace"], horizontal=True,
                    format_func=lambda m: "Üzerine ekle (ortalama maliyeti güncelle)"
                    if m == "add" else "Tamamen değiştir")

                submitted = st.form_submit_button("🚀 Portföye kaydet",
                                                  width="stretch")

            if submitted:
                if qty <= 0:
                    st.error("Adet sıfırdan büyük olmalı.")
                else:
                    record = {
                        "symbol": symbol.strip(),
                        "display": (guess["display"] or symbol).strip().upper(),
                        "source": source, "currency": currency,
                        "ana_sinif": ana, "alt_sinif": alt.strip() or "Diğer",
                        "sektor": sektor.strip() or "Diğer",
                        "qty": float(qty), "avg_cost": float(cost),
                        "hesap": hesap.strip(), "unit": unit,
                        "manual_price": manual_price, "notlar": "",
                        "valuation": VAL_VALUE if source == SRC_MANUAL else VAL_QTY,
                    }
                    st.session_state.assets = an.merge_position(
                        st.session_state.assets, record, mode=mode)
                    if save_assets(store, st.session_state.assets,
                                   f"portföy: {record['display']} güncellendi"):
                        cached_snapshot.clear()
                        st.success(f"{record['display']} kaydedildi.")
                        st.rerun()

# ============================== AYARLAR ====================================
with tab_ayar:
    st.markdown("#### Depolama durumu")
    st.code(store.describe(), language="text")
    if store.backend == "local":
        st.markdown(
            "Kalıcı kayıt için Streamlit **Settings → Secrets** alanına:\n\n"
            "```toml\n[github]\ntoken  = \"github_pat_...\"\n"
            "repo   = \"kullanici/depo\"\nbranch = \"main\"\n"
            "path   = \"my_assets.json\"\n```"
        )

    st.markdown("#### Fiyat kaynakları")
    if not df.empty:
        st.dataframe(
            df[["Sembol", "Yahoo Sembol", "Kaynak", "Fiyat", "Fiyat OK", "Hata"]],
            width="stretch", hide_index=True)

    st.markdown("#### Yedek")
    import json as _json
    st.download_button("⬇️ my_assets.json indir",
                       _json.dumps(assets, indent=2, ensure_ascii=False).encode("utf-8"),
                       "my_assets.json", "application/json")
    up = st.file_uploader("Yedekten yükle (mevcut portföyün üzerine yazar)", type="json")
    if up is not None and st.button("📥 Yüklemeyi uygula"):
        try:
            data = _json.loads(up.getvalue().decode("utf-8"))
            st.session_state.assets = [normalize_asset(a) for a in data]
            if save_assets(store, st.session_state.assets, "yedekten geri yükleme"):
                cached_snapshot.clear()
                st.success("Yedek yüklendi.")
                st.rerun()
        except Exception as exc:
            st.error(f"Dosya okunamadı: {exc}")
