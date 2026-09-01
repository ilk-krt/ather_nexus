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

from __future__ import annotations

import datetime as dt
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Iterable

import requests

from .classification import (
    METAL_UNITS,
    SRC_CASH,
    SRC_GOLD,
    SRC_MANUAL,
    SRC_SILVER,
    SRC_TEFAS,
    SRC_YAHOO,
)

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
