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

from __future__ import annotations

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
    from .classification import asset_key

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
