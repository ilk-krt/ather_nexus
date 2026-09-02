"""
MSP (mystocksportfolio.app) portföy raporunu AETHER NEXUS'a aktarır.

KAYNAK
------
"PORTFÖY RAPORU" · 2 Eyl 2026 · mystocksportfolio.app
Portföyler: Bist, US, Bist İsctr, Crypto, Altcoins, US Sattıklarım
Raporda TÜM değerler USD ($) cinsindendir.

TASARIM KARARLARI
-----------------
1) PARA BİRİMİ
   Rapor her şeyi USD'ye çevirmiş durumda. AETHER ise her varlığı kendi doğal
   para biriminde tutar (BIST hisseleri TRY, ABD/kripto USD) ve değerlemede
   TRY'ye çevirir. Bu yüzden BIST satırlarında:
       currency = "TRY"
       avg_cost = (rapordaki USD maliyet) x güncel USDTRY
   MSP maliyeti de güncel kurla USD'ye çevirdiği için bu dönüşüm pratikte
   kayıpsızdır. ABD hisseleri ve kripto USD olarak kalır.

2) ÇİFT SAYIM
   Mevcut my_assets.json Bluecoins'ten gelen "kova" satırlarından oluşuyor:
   toplam tutarlar, tek tek pozisyon yok. MSP raporu BIST / ABD / KRİPTO
   kovalarının İÇİNİ pozisyon bazında veriyor. İkisi birlikte durursa bu üç
   sınıf iki kez sayılır. Bu yüzden aşağıdaki kovalar kaldırılır; geri kalan
   (Fon, Altın, Gümüş, Eurobond, Nakit, Banka) olduğu gibi korunur.
   Eski dosya my_assets.backup-*.json olarak yedeklenir.

3) KAPANMIŞ POZİSYONLAR
   Değeri 0.00 ve adedi 0 olan satırlar (ASML, AVGO, CAT, KO, LLY, NOC, PFE,
   T, TSM) sadece gerçekleşmiş kâr/zarar kaydıdır; pozisyon olarak yazılmaz.

4) WBD ANOMALİSİ
   Raporda 32 adet @ $0.00 maliyet (+%5.664.680) görünüyor — muhtemelen
   spin-off/bölünme sonrası maliyet taşınmamış. Adet korunur, maliyet 0
   bırakılır ve notlara uyarı yazılır.
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from typing import Any

from portfolio.classification import SRC_YAHOO, auto_fill_asset, normalize_asset

RAPOR_TARIHI = "2026-09-02"
KAYNAK_NOT = f"MSP raporu · {RAPOR_TARIHI}"

# Rapordaki toplamlar — transkripsiyon doğrulaması için.
#
# DİKKAT: rapordaki "Değer $783.423,60" ve "Maliyete göre $717.828,35" AÇIK
# POZİSYONLARIN değeri DEĞİLDİR; her ikisi de gerçekleşmiş kâr dahil TÜM ZAMAN
# birikimidir (783.423,60 - 717.828,35 = 65.595,25 = "Tüm Zaman", ki bu da
# gerçekleşmemiş -18.735,24 + gerçekleşen +84.330,49 toplamına eşittir).
# Bu yüzden transkripsiyonu doğrulamak için tek geçerli çapa GERÇEKLEŞMEMİŞ
# K/Z'dir: (sum(değer) - sum(adet x maliyet)) ≈ -18.735,24 olmalı.
RAPOR_GERCEKLESMEMIS = -18_735.24
RAPOR_TOLERANS = 500.0   # maliyetler raporda 2 haneye yuvarlı; sapma normal

# --------------------------------------------------------------------------
# (sembol, rapordaki değer USD, adet, ortalama maliyet USD)
# --------------------------------------------------------------------------
POZISYONLAR: list[tuple[str, float, float, float]] = [
    ("BTC-USD",      95_164.83,      1.2328,  70_179.67),
    ("ISCTR.IS",     18_772.41,  71_075.0,         0.08),
    ("NVDA",          9_569.12,      44.0,       197.97),
    ("PGSUS.IS",      8_118.40,   2_580.0,         4.17),
    ("ETH-USD",       7_729.13,      3.1997,   2_319.15),
    ("META",          6_600.71,      11.44,      591.21),
    ("NOK",           5_469.75,     550.0,        12.17),
    ("BE",            5_019.45,      24.19,      167.33),
    ("NEE",           4_950.31,      60.0,        86.02),
    ("LINK-USD",      4_015.71,     358.13,        7.90),
    ("UFO",           3_758.04,      88.0,        54.76),
    ("AMD",           3_652.92,       8.0,       141.60),
    ("BMNR",          3_625.45,     155.0,        31.89),
    ("MA",            3_558.90,       6.10,      331.14),
    ("ISMEN.IS",      3_381.82,   4_810.0,         0.92),
    ("LKMNH.IS",      3_345.95,  12_000.0,         0.36),
    ("DGXX",          2_921.85,     842.98,        7.25),
    ("GRAB",          2_870.60,     819.0,         4.24),
    ("DERHL.IS",      2_432.89,  56_193.02,        0.09),
    ("HIMS",          2_432.70,      85.0,        43.51),
    ("GOOG",          2_409.64,       7.28,      340.21),
    ("PGY",           2_351.53,     113.0,        30.96),
    ("BMSTL.IS",      2_312.87,   2_500.0,         0.88),
    ("BULL",          2_310.30,     255.0,        13.56),
    ("SUI-USD",       2_213.74,   3_049.23,        1.19),
    ("TUREX.IS",      2_137.83,  16_252.0,         0.23),
    ("RAYSG.IS",      2_111.06,     652.0,         6.17),
    ("CEG",           1_955.38,       7.0,       309.45),
    ("LPTH",          1_917.00,     200.0,        16.51),
    ("CEMAS.IS",      1_863.97,  22_000.0,         0.11),
    ("ATLX",          1_788.01,     574.0,         4.99),
    ("WYFI",          1_777.04,     102.0,        38.66),
    ("OBAMS.IS",      1_709.02,  15_000.0,         0.16),
    ("KRGYO.IS",      1_705.00,  26_465.0,         0.08),
    ("MBLY",          1_666.00,     200.0,        10.42),
    ("ORCL",          1_646.24,      11.69,      119.63),
    ("OPEN",          1_644.30,     540.0,         6.00),
    ("ECILC.IS",      1_609.10,   1_035.0,         2.01),
    ("AI",            1_587.89,     155.72,       10.76),
    ("LUNR",          1_535.04,     104.0,        20.96),
    ("KTOS",          1_486.95,      30.0,        71.73),
    ("DVLT",          1_308.93,   4_600.0,         0.55),
    ("IREN",          1_287.00,      35.03,       38.86),
    ("SAYAS.IS",      1_266.18,   1_078.0,         1.11),
    ("PALL",          1_187.00,      50.0,        32.43),
    ("CPSH",          1_160.86,     318.0,         9.28),
    ("SMR",           1_132.33,     124.0,        13.44),
    ("ISRG",          1_106.13,       3.0,       357.85),
    ("CWEN",          1_008.00,      32.0,        34.44),
    ("BKR",             959.35,      15.0,        68.35),
    ("BZAI",            919.20,   2_000.0,         1.88),
    ("AVAX-USD",        919.05,     127.13,       25.28),
    ("WBD",             906.36,      32.0,         0.00),   # bkz. modül notu
    ("IOTA-USD",        724.55,  18_232.0,         0.04),
    ("CRML",            705.39,     100.0,        12.73),
    ("ALKA.IS",         672.01,   4_000.0,         0.31),
    ("HATEK.IS",        633.05,   2_252.0,         0.46),
    ("KIMMR.IS",        554.76,   2_000.0,         0.37),
    ("TON11419-USD",    549.73,     416.75,        3.01),
    ("SLNH",            527.50,     500.0,         1.40),
    ("FIL-USD",         486.30,     635.35,        2.46),
    ("SBET",            410.75,      50.0,        13.51),
    ("TIA-USD",         182.31,     529.22,        1.72),
    ("PYTH-USD",        155.74,   3_096.28,        0.16),
    ("AUDIO-USD",       113.60,   8_759.0,         0.07),
    ("EDU-USD",          79.48,   1_625.49,        0.19),
    ("ALT29073-USD",     51.48,   8_623.06,        0.02),
    ("VTRS",             49.89,       3.0,         8.34),
    ("MAGS",              1.36,       0.02,       43.97),
    ("FLY",               0.09,       0.0043642,  20.66),
]

# Değeri ve adedi 0 olan, sadece gerçekleşmiş K/Z taşıyan satırlar.
KAPANAN = ["ASML", "AVGO", "CAT", "KO", "LLY", "NOC", "PFE", "T", "TSM"]

# --------------------------------------------------------------------------
# Otomatik tanımanın "ABD hissesi" sandığı ama aslında ETF olan semboller.
# --------------------------------------------------------------------------
ETF_SEMBOLLERI = {
    "UFO":  ("Uzay / Uydu ETF", "ABD ETF"),
    "PALL": ("Kıymetli Maden ETF", "ABD ETF"),
    "MAGS": ("Tematik ETF", "ABD ETF"),
}

# Otomatik tanımanın bilmediği ABD sembolleri için sektör düzeltmesi.
SEKTOR_DUZELTME = {
    "NVDA": "Yarı İletken", "AMD": "Yarı İletken", "MBLY": "Yarı İletken",
    "META": "Teknoloji", "GOOG": "Teknoloji", "ORCL": "Teknoloji",
    "AI": "Teknoloji / Yazılım", "BZAI": "Teknoloji / Yazılım",
    "DVLT": "Teknoloji / Veri Merkezi", "IREN": "Teknoloji / Veri Merkezi",
    "NOK": "Teknoloji / Telekom", "GRAB": "Teknoloji / Platform",
    "OPEN": "Teknoloji / Platform", "DGXX": "Teknoloji / Platform",
    "MA": "Finans", "PGY": "Finans / Fintek", "BULL": "Finans / Aracı Kurum",
    "WYFI": "Finans / Fintek", "BMNR": "Kripto Hazine",
    "SBET": "Kripto Hazine", "SLNH": "Kripto Madencilik",
    "NEE": "Enerji / Kamu Hizmeti", "CEG": "Enerji / Kamu Hizmeti",
    "CWEN": "Enerji / Kamu Hizmeti", "BE": "Enerji / Yakıt Hücresi",
    "SMR": "Enerji / Nükleer", "BKR": "Enerji / Petrol Servis",
    "HIMS": "Sağlık", "ISRG": "Sağlık / Medikal Cihaz", "VTRS": "Sağlık / İlaç",
    "LUNR": "Uzay / Savunma", "KTOS": "Uzay / Savunma",
    "LPTH": "Optik / Savunma", "CPSH": "İleri Malzeme",
    "ATLX": "Madencilik", "CRML": "Madencilik",
    "WBD": "Medya / Eğlence", "FLY": "Diğer ABD",
}

# --------------------------------------------------------------------------
# Çift sayımı önlemek için kaldırılacak Bluecoins kovaları.
# (BIST / ABD hisse / kripto — MSP raporu bunların içini pozisyon bazında veriyor)
# --------------------------------------------------------------------------
CAKISAN_KOVALAR = {
    "BC:01_BIST:MIDAS", "BC:01_BIST:YK", "BC:01_BIST:VB",
    "BC:02_US_STOCKS:MIDAS", "BC:02_US_STOCKS:IS",
    "BTC-USD", "BC:08_CRYPTO:OTHERS",
}


def hesap_ata(sembol: str) -> str:
    """MSP'deki kaynak portföye göre hesap adı."""
    if sembol == "ISCTR.IS":
        return "MSP · Bist İsctr"
    if sembol.endswith(".IS"):
        return "MSP · Bist"
    if sembol.endswith("-USD"):
        return "MSP · Kripto"
    return "MSP · US"


VARSAYILAN_USDTRY = 41.2   # portfolio_history.json son kaydı (2026-09-01)


def usdtry_kuru(history_path: str = "portfolio_history.json") -> tuple[float, str]:
    """
    USDTRY kuru sırasıyla: canlı Yahoo -> portföy geçmişinin son kaydı -> sabit.
    Bu kur SADECE BIST satırlarının USD maliyetini TRY'ye çevirmek için
    kullanılır; değerleme her zaman uygulamanın kendi canlı kuruyla yapılır.
    """
    try:
        from portfolio.prices import fetch_yahoo
        rate = fetch_yahoo(["TRY=X"]).get("TRY=X")
        if rate and rate > 0:
            return float(rate), "canlı"
    except Exception:
        pass
    try:
        with open(history_path, "r", encoding="utf-8") as f:
            gecmis = json.load(f)
        for kayit in reversed(gecmis):
            r = kayit.get("usdtry")
            if r and r > 0:
                return float(r), f"portföy geçmişi ({kayit.get('date', '?')})"
    except Exception:
        pass
    return VARSAYILAN_USDTRY, "varsayılan"


def kayit_uret(sembol: str, deger_usd: float, adet: float, maliyet_usd: float,
               usdtry: float) -> dict[str, Any]:
    """
    Tek bir MSP satırından AETHER varlık kaydı üretir.

    PAZAR, otomatik tanımaya DEĞİL sembolün rapordaki şekline göre belirlenir:
      *.IS   -> BIST      (TRY)
      *-USD  -> kripto    (USD)
      diğer  -> ABD       (USD)
    Bu şart, çünkü auto_fill_asset üç harfli her kodu TEFAS fonu sanıyor
    (TEFAS_CODE_RE = ^[A-Z]{3}$) ve NOK / NEE / PGY / CEG / SMR / BKR / WBD /
    FLY gibi ABD sembolleri yanlışlıkla "tefas" kaynağına düşüyordu — bu da
    fiyatın hiç çekilememesi demekti. Otomatik tanıma sadece pazar uyuşuyorsa
    sınıflandırmayı ZENGİNLEŞTİRMEK için kullanılır.
    """
    bist = sembol.endswith(".IS")
    kripto = sembol.endswith("-USD")

    if bist:
        currency, avg_cost = "TRY", maliyet_usd * usdtry
        varsayilan = ("Hisse Senedi", "BIST", "Diğer BIST")
    elif kripto:
        currency, avg_cost = "USD", maliyet_usd
        varsayilan = ("Kripto", "Altcoin", "Diğer Kripto")
    else:
        currency, avg_cost = "USD", maliyet_usd
        varsayilan = ("Hisse Senedi", "ABD", "Diğer ABD")

    ana, alt, sektor = varsayilan
    try:
        tanim = auto_fill_asset(sembol)
        # Sadece otomatik tanıma da aynı pazarı bulduysa güven.
        if tanim["source"] == SRC_YAHOO and tanim["ana_sinif"] == ana:
            ana, alt, sektor = (tanim["ana_sinif"], tanim["alt_sinif"],
                                tanim["sektor"])
        elif kripto and tanim["ana_sinif"] == "Kripto":
            ana, alt, sektor = ("Kripto", tanim["alt_sinif"], tanim["sektor"])
    except ValueError:
        pass

    kayit: dict[str, Any] = {
        "symbol": sembol,
        "display": sembol.replace(".IS", "").replace("-USD", ""),
        "source": SRC_YAHOO,
        "currency": currency,
        "ana_sinif": ana,
        "alt_sinif": alt,
        "sektor": sektor,
        "hesap": hesap_ata(sembol),
        "unit": None,
        "valuation": "qty",
        "qty": adet,
        "avg_cost": avg_cost,
        "manual_price": None,
        "notlar": KAYNAK_NOT,
    }

    base = sembol.replace(".IS", "").replace("-USD", "")
    if base in ETF_SEMBOLLERI:
        sektor, alt = ETF_SEMBOLLERI[base]
        kayit["ana_sinif"] = "Fon"
        kayit["alt_sinif"] = alt
        kayit["sektor"] = sektor
    elif base in SEKTOR_DUZELTME:
        kayit["sektor"] = SEKTOR_DUZELTME[base]

    if sembol == "WBD":
        kayit["notlar"] = (
            f"{KAYNAK_NOT} · UYARI: raporda maliyet $0,00 görünüyor "
            "(muhtemelen bölünme sonrası taşınmamış). K/Z anlamsız, "
            "gerçek maliyeti elle girin."
        )
    if bist:
        kayit["notlar"] = (
            f"{KAYNAK_NOT} · maliyet USD ${maliyet_usd:,.4f} → "
            f"TRY (kur {usdtry:,.4f})"
        )
    return kayit


def calistir(assets_path: str = "my_assets.json", *, yaz: bool = True,
             usdtry: float | None = None) -> dict[str, Any]:
    kur, kur_kaynak = (usdtry, "verilen") if usdtry else usdtry_kuru()

    with open(assets_path, "r", encoding="utf-8") as f:
        mevcut = json.load(f)

    def cakisiyor(a: dict[str, Any]) -> bool:
        # (a) Bluecoins kovaları — MSP raporu bunların içini pozisyon bazında veriyor
        # (b) önceki bir MSP aktarımı — betik tekrar çalıştırılabilir olsun
        return (a.get("symbol") in CAKISAN_KOVALAR
                or str(a.get("hesap", "")).startswith("MSP · "))

    korunan = [a for a in mevcut if not cakisiyor(a)]
    kaldirilan = [a for a in mevcut if cakisiyor(a)]

    yeni = [
        normalize_asset(kayit_uret(s, d, q, c, kur))
        for s, d, q, c in POZISYONLAR
    ]

    birlesik = korunan + yeni

    toplam_deger = sum(d for _, d, _, _ in POZISYONLAR)
    toplam_maliyet = sum(q * c for _, _, q, c in POZISYONLAR)

    ozet = {
        "usdtry": kur,
        "usdtry_kaynak": kur_kaynak,
        "eklenen": len(yeni),
        "kaldirilan": [a["symbol"] for a in kaldirilan],
        "korunan": len(korunan),
        "toplam": len(birlesik),
        "hesaplanan_deger_usd": toplam_deger,
        "hesaplanan_maliyet_usd": toplam_maliyet,
        "hesaplanan_gerceklesmemis": toplam_deger - toplam_maliyet,
        "rapor_gerceklesmemis": RAPOR_GERCEKLESMEMIS,
        "sapma": (toplam_deger - toplam_maliyet) - RAPOR_GERCEKLESMEMIS,
        "dogrulandi": abs((toplam_deger - toplam_maliyet)
                          - RAPOR_GERCEKLESMEMIS) <= RAPOR_TOLERANS,
        "yedek": None,
    }

    if yaz:
        damga = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        yedek = f"my_assets.backup-{damga}.json"
        shutil.copy2(assets_path, yedek)
        ozet["yedek"] = yedek
        with open(assets_path, "w", encoding="utf-8") as f:
            json.dump(birlesik, f, indent=2, ensure_ascii=False)
            f.write("\n")

    ozet["varliklar"] = birlesik
    return ozet


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="MSP raporunu AETHER'a aktarır.")
    ap.add_argument("--dosya", default="my_assets.json")
    ap.add_argument("--kur", type=float, default=None, help="USDTRY kuru")
    ap.add_argument("--dene", action="store_true", help="yazmadan sadece özet")
    ns = ap.parse_args()

    r = calistir(ns.dosya, yaz=not ns.dene, usdtry=ns.kur)
    print(f"USDTRY          : {r['usdtry']:,.4f}  ({r['usdtry_kaynak']})")
    print(f"Eklenen pozisyon: {r['eklenen']}")
    print(f"Kaldırılan kova : {len(r['kaldirilan'])}  {r['kaldirilan']}")
    print(f"Korunan satır   : {r['korunan']}")
    print(f"Toplam satır    : {r['toplam']}")
    print(f"Açık poz. değer : ${r['hesaplanan_deger_usd']:,.2f}")
    print(f"Açık poz. malij.: ${r['hesaplanan_maliyet_usd']:,.2f}")
    print(f"Gerçekleşmemiş  : ${r['hesaplanan_gerceklesmemis']:,.2f}   "
          f"rapor ${r['rapor_gerceklesmemis']:,.2f}   "
          f"sapma ${r['sapma']:,.2f}   "
          f"{'✓ doğrulandı' if r['dogrulandi'] else '✗ SAPMA BÜYÜK'}")
    if r["yedek"]:
        print(f"Yedek           : {r['yedek']}")
