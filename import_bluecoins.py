"""
Bluecoins (.fydb) yedeğinden portföyü my_assets.json'a aktarır.

Kullanım:
    python import_bluecoins.py Bluecoins_YYYYMMDD.fydb -o my_assets.json

NASIL OKUNUYOR (Bluecoins şema notları):
  * TRANSACTIONSTABLE.amount  -> ana para birimi (TRY) cinsinden mikro birim (×1.000.000)
  * accountConversionRateNew  -> TRY tutarını hesabın kendi para birimine çevirir
  * deletedTransaction = 6    -> geçerli kayıt (5 = silinmiş) — filtrelenmezse
                                 bakiyeler yanlış çıkar
  * Gelecek tarihli kayıtlar  -> hatırlatıcı/planlı işlemler, bugüne kadar filtrelenir
  * accountReference 1..4     -> gerçek hesap hareketleri

Döviz hesaplarında hesabın kaydettiği kur ESKİ olabileceği için, dışa aktarımda
tutar HESABIN KENDİ para biriminde yazılır; TL karşılığı uygulamada canlı kurla
hesaplanır.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sqlite3
import sys
import unicodedata

# Bluecoins hesap tipi -> (ana sınıf, alt sınıf)
TYPE_MAP: dict[str, tuple[str, str]] = {
    "01_BIST":          ("Hisse Senedi", "BIST"),
    "02_US Stocks":     ("Hisse Senedi", "ABD"),
    "03_Fon":           ("Fon", "Yatırım Fonu"),
    "04A_Gold":         ("Emtia", "Altın"),
    "04B_SILVER":       ("Emtia", "Gümüş"),
    "05_Eurobond":      ("Sabit Getirili", "Eurobond"),
    "06_$/€ Cash":      ("Nakit", "Döviz"),
    "07_₺ Cash":        ("Nakit", "TL Likit"),
    "08_CRYPTO":        ("Kripto", "Kripto"),
    "Bank":             ("Nakit", "Vadesiz Mevduat"),
    "Properties":       ("Gayrimenkul", "Konut / Arsa"),
    "Other Assets":     ("Diğer", "Taşıt / Eşya"),
    "Receivables":      ("Alacaklar", "Alacak / BES"),
    "Credit Card":      ("Yükümlülük", "Kredi Kartı"),
    "Mortgages":        ("Yükümlülük", "Konut Kredisi"),
    "Virtual Accounts": ("Yükümlülük", "Sanal Hesap"),
}

# Hesap adından tanınan gerçek enstrümanlar.
# source/symbol dolu olanların fiyatı canlı çekilebilir; qty'yi siz gireceksiniz.
INSTRUMENT_HINTS: dict[str, dict] = {
    "Fon_VB_AFO":  {"source": "tefas", "symbol": "AFO", "sektor": "Altın Fonu"},
    "Fon_VB_YKT":  {"source": "tefas", "symbol": "YKT", "sektor": "Altın Fonu"},
    "Fon_VB_GGK":  {"source": "tefas", "symbol": "GGK", "sektor": "Altın Fonu"},
    "Fon_YK_GGK":  {"source": "tefas", "symbol": "GGK", "sektor": "Altın Fonu"},
    "VB NAU":      {"source": "tefas", "symbol": "NAU", "sektor": "Altın Fonu"},
    "Fon_YK_IOG":  {"source": "tefas", "symbol": "IOG", "sektor": "Gümüş Fonu"},
    "Fon_VB_YZG":  {"source": "tefas", "symbol": "YZG", "sektor": "Gümüş Fonu"},
    "IAR":         {"source": "tefas", "symbol": "IAR", "sektor": "Gümüş Fonu"},
    "ALTIN.S":     {"source": "yahoo", "symbol": "ALTIN.S1.IS", "sektor": "Altın ETF"},
    "GMSTR MIDAS": {"source": "yahoo", "symbol": "GMSTR.IS", "sektor": "Gümüş ETF"},
    "GMSTR_VB":    {"source": "yahoo", "symbol": "GMSTR.IS", "sektor": "Gümüş ETF"},
    "GMSTR_YK":    {"source": "yahoo", "symbol": "GMSTR.IS", "sektor": "Gümüş ETF"},
    "HM":          {"source": "gold",  "symbol": "ALTIN", "unit": "GRAM",
                    "sektor": "Fiziki Altın"},
    "BITCOIN":     {"source": "yahoo", "symbol": "BTC-USD", "sektor": "L1 Zincir"},
    "USDT":        {"source": "yahoo", "symbol": "USDT-USD", "sektor": "Stablecoin"},
}


def slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").upper()
    return text or "X"


def read_balances(db_path: str, asof: str | None = None) -> list[dict]:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    asof = asof or dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    rows = con.execute(
        """
        SELECT at.accountTypeName            AS atype,
               ag.accountGroupName           AS agroup,
               a.accountName                 AS acc,
               a.accountCurrency             AS cur,
               a.accountConversionRateNew    AS rate,
               a.accountHidden               AS hidden,
               SUM(t.amount) / 1000000.0     AS try_bal,
               MAX(t.date)                   AS last_date,
               COUNT(*)                      AS n
        FROM TRANSACTIONSTABLE t
        JOIN ACCOUNTSTABLE a  ON a.accountsTableID = t.accountID
        LEFT JOIN ACCOUNTTYPETABLE at ON at.accountTypeTableID = a.accountTypeID
        LEFT JOIN ACCOUNTINGGROUPTABLE ag ON ag.accountingGroupTableID = at.accountingGroupID
        WHERE t.deletedTransaction = 6
          AND t.date <= ?
          AND t.accountReference IN (1, 2, 3, 4)
        GROUP BY a.accountsTableID
        ORDER BY at.accountTypeName, try_bal DESC
        """,
        (asof,),
    ).fetchall()
    con.close()
    return [dict(r) for r in rows]


def to_assets(rows: list[dict], *, include_hidden: bool,
              include_liabilities: bool, drop_zero: bool) -> tuple[list[dict], list[str]]:
    assets: list[dict] = []
    notes: list[str] = []

    for r in rows:
        atype = r["atype"] or "Diğer"
        acc = (r["acc"] or "").strip()
        is_liab = (r["agroup"] or "") == "Liabilities"
        try_bal = float(r["try_bal"] or 0.0)
        rate = float(r["rate"] or 1.0) or 1.0
        cur = (r["cur"] or "TRY").upper()

        if atype == "(No Account)":
            continue
        if not include_hidden and r["hidden"]:
            continue
        if not include_liabilities and is_liab:
            continue

        # Döviz hesapları: hesabın kendi para birimindeki bakiye esas alınır
        native = try_bal * rate if cur != "TRY" else try_bal
        if drop_zero and abs(native) < 0.5:
            continue

        ana, alt = TYPE_MAP.get(atype, ("Diğer", atype))
        hint = INSTRUMENT_HINTS.get(acc, {})

        record = {
            "symbol": hint.get("symbol") or f"BC:{slug(atype)}:{slug(acc)}",
            "display": acc,
            "source": hint.get("source", "manual"),
            "currency": cur,
            "ana_sinif": ana,
            "alt_sinif": alt,
            "sektor": hint.get("sektor") or alt,
            "hesap": acc,
            "unit": hint.get("unit"),
            # Kova modeli: değer = elle girilen toplam tutar.
            # Adet girildiği anda uygulama otomatik "Adet × Fiyat" moduna geçer.
            "valuation": "value",
            "qty": 0.0,
            "avg_cost": round(native, 2),
            "manual_price": round(native, 2),
            "notlar": f"Bluecoins '{atype}' · son kayıt {str(r['last_date'])[:10]}",
        }

        if hint:
            record["notlar"] += f" · canlı kaynak bağlı ({hint['symbol']}), ADET girin"
            notes.append(
                f"{acc:<14} → {hint['source']:<6} {hint['symbol']:<12} "
                f"(mevcut değer {native:,.0f} {cur})"
            )

        assets.append(record)

    return assets, notes


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Bluecoins .fydb → my_assets.json")
    p.add_argument("fydb")
    p.add_argument("-o", "--out", default="my_assets.json")
    p.add_argument("--include-hidden", action="store_true",
                   help="Gizli hesapları da al (gayrimenkul, taşıt, alacaklar)")
    p.add_argument("--include-liabilities", action="store_true",
                   help="Borçları da al (negatif değerli satırlar)")
    p.add_argument("--keep-zero", action="store_true", help="Sıfır bakiyeli hesapları koru")
    p.add_argument("--asof", default=None, help="Bu tarihe kadar olan kayıtlar (YYYY-MM-DD)")
    args = p.parse_args(argv)

    asof = f"{args.asof} 23:59:59" if args.asof else None
    rows = read_balances(args.fydb, asof)
    assets, notes = to_assets(
        rows,
        include_hidden=args.include_hidden,
        include_liabilities=args.include_liabilities,
        drop_zero=not args.keep_zero,
    )

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(assets, f, indent=2, ensure_ascii=False)
        f.write("\n")

    total_try = sum(a["manual_price"] for a in assets if a["currency"] == "TRY")
    print(f"{len(assets)} pozisyon → {args.out}")
    print(f"TL bazlı satırların toplamı: ₺{total_try:,.0f} "
          f"(döviz satırları uygulamada canlı kurla çevrilir)")
    if notes:
        print("\nEnstrüman eşleşme önerileri:")
        for n in notes:
            print("  •", n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
