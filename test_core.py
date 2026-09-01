"""Ağ gerektirmeyen mantık testleri: python -m pytest tests/ -q"""

import json
import math
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from portfolio import analytics as an
from portfolio import prices as px
from portfolio.classification import (
    METAL_UNITS, SRC_CASH, SRC_GOLD, SRC_TEFAS, SRC_YAHOO,
    auto_fill_asset, normalize_asset,
)
from portfolio.storage import Storage


# --------------------------------------------------------------- sınıflandırma
def test_bist_suffix():
    a = auto_fill_asset("thyao")
    assert a["symbol"] == "THYAO.IS" and a["currency"] == "TRY"
    assert a["ana_sinif"] == "Hisse Senedi" and a["alt_sinif"] == "BIST"
    assert auto_fill_asset("THYAO.IS")["symbol"] == "THYAO.IS"   # çift ek yok


def test_crypto_and_us():
    assert auto_fill_asset("btc")["symbol"] == "BTC-USD"
    assert auto_fill_asset("BTC-USD")["symbol"] == "BTC-USD"
    assert auto_fill_asset("NVDA")["symbol"] == "NVDA"
    assert auto_fill_asset("nvda")["currency"] == "USD"


def test_tefas_and_metal_and_cash():
    f = auto_fill_asset("mac")
    assert f["source"] == SRC_TEFAS and f["symbol"] == "MAC"
    g = auto_fill_asset("ALTIN-CEYREK")
    assert g["source"] == SRC_GOLD and g["unit"] == "CEYREK"
    n = auto_fill_asset("NAKIT-USD")
    assert n["source"] == SRC_CASH and n["currency"] == "USD"


def test_unknown_symbol_is_flagged():
    assert auto_fill_asset("ZZZZQQ")["guessed"] is True
    assert auto_fill_asset("AAPL")["guessed"] is False


def test_legacy_migration():
    old = {"symbol": "ALKA.IS", "type": "TR_STOCK", "type_tr": "BIST",
           "sector": "Kimya", "currency": "TRY", "qty": 100, "avg_cost": 10}
    new = normalize_asset(old)
    assert new["source"] == SRC_YAHOO and "type" not in new
    assert new["ana_sinif"] == "Hisse Senedi" and new["display"] == "ALKA"


# ------------------------------------------------------------------ hesaplama
def _q(price, ok=True, err=""):
    return px.Quote(symbol="X", price=price, ok=ok, error=err)


def test_dataframe_and_totals_fx():
    assets = [
        {"symbol": "THYAO.IS", "display": "THYAO", "currency": "TRY", "qty": 100,
         "avg_cost": 200, "ana_sinif": "Hisse Senedi", "alt_sinif": "BIST",
         "sektor": "Havacılık", "source": SRC_YAHOO},
        {"symbol": "NVDA", "display": "NVDA", "currency": "USD", "qty": 10,
         "avg_cost": 100, "ana_sinif": "Hisse Senedi", "alt_sinif": "ABD",
         "sektor": "Yarı İletken", "source": SRC_YAHOO},
    ]
    quotes = {"THYAO.IS": _q(250.0), "NVDA": _q(150.0)}
    df = an.build_dataframe(assets, quotes, {"USDTRY": 40.0})

    assert len(df) == 2
    # NVDA: 10 × 150 × 40 = 60.000 ; THYAO: 100 × 250 = 25.000
    assert df.set_index("Sembol").loc["NVDA", "Değer (TRY)"] == pytest.approx(60_000)
    assert df.set_index("Sembol").loc["THYAO", "Değer (TRY)"] == pytest.approx(25_000)

    t = an.totals(df, 40.0)
    assert t["deger_try"] == pytest.approx(85_000)
    assert t["maliyet_try"] == pytest.approx(100 * 200 + 10 * 100 * 40)  # 60.000
    assert t["kz_try"] == pytest.approx(25_000)
    # Ağırlıklı yüzde — satır yüzdelerinin ortalaması DEĞİL
    assert t["kz_pct"] == pytest.approx(25_000 / 60_000 * 100)
    assert t["deger_usd"] == pytest.approx(2_125)


def test_missing_fx_does_not_silently_become_one():
    assets = [{"symbol": "NVDA", "display": "NVDA", "currency": "USD", "qty": 1,
               "avg_cost": 100, "ana_sinif": "Hisse Senedi", "alt_sinif": "ABD",
               "sektor": "X", "source": SRC_YAHOO}]
    df = an.build_dataframe(assets, {"NVDA": _q(150.0)}, {})   # kur yok
    assert math.isnan(df.iloc[0]["Değer (TRY)"])               # 150 TL sanılmıyor


def test_failed_quote_marks_row():
    assets = [{"symbol": "XXX", "display": "XXX", "currency": "TRY", "qty": 5,
               "avg_cost": 10, "ana_sinif": "Diğer", "alt_sinif": "D",
               "sektor": "D", "source": SRC_YAHOO}]
    df = an.build_dataframe(assets, {"XXX": _q(None, ok=False, err="yok")}, {})
    assert df.iloc[0]["Fiyat OK"] is False or df.iloc[0]["Fiyat OK"] == False
    assert df.iloc[0]["Hata"] == "yok"
    assert math.isnan(df.iloc[0]["Değer (TRY)"])


def test_eur_via_cross_rate():
    assets = [{"symbol": "E", "display": "E", "currency": "EUR", "qty": 1,
               "avg_cost": 0, "ana_sinif": "Nakit", "alt_sinif": "Döviz",
               "sektor": "Euro", "source": SRC_CASH}]
    df = an.build_dataframe(assets, {"E": _q(100.0)}, {"USDTRY": 40.0, "EURUSD": 1.1})
    assert df.iloc[0]["Değer (TRY)"] == pytest.approx(100 * 44.0)


def test_liabilities_reduce_net_worth():
    assets = [
        {"symbol": "A", "display": "A", "currency": "TRY", "qty": 1, "avg_cost": 0,
         "ana_sinif": "Nakit", "alt_sinif": "x", "sektor": "x", "source": SRC_CASH},
        {"symbol": "B", "display": "B", "currency": "TRY", "qty": 1, "avg_cost": 0,
         "ana_sinif": "Yükümlülük", "alt_sinif": "Kredi Kartı", "sektor": "k",
         "source": SRC_CASH},
    ]
    df = an.build_dataframe(assets, {"A": _q(1000.0), "B": _q(-300.0)}, {})
    t = an.totals(df, None)
    assert t["deger_try"] == pytest.approx(1000)
    assert t["borc_try"] == pytest.approx(300)
    assert t["net_try"] == pytest.approx(700)


# --------------------------------------------------------------------- sankey
def test_sankey_no_label_collision():
    """
    Eski koddaki hata: 'Altın' hem alt sınıf hem sektör adı olduğunda düğümler
    birleşiyor ve akış iki katına çıkıyordu.
    """
    assets = [
        {"symbol": "A", "display": "Altın", "currency": "TRY", "qty": 1, "avg_cost": 0,
         "ana_sinif": "Emtia", "alt_sinif": "Altın", "sektor": "Altın",
         "source": SRC_CASH},
        {"symbol": "B", "display": "Gümüş", "currency": "TRY", "qty": 1, "avg_cost": 0,
         "ana_sinif": "Emtia", "alt_sinif": "Gümüş", "sektor": "Gümüş",
         "source": SRC_CASH},
    ]
    df = an.build_dataframe(assets, {"A": _q(100.0), "B": _q(50.0)}, {})
    sk = an.sankey_data(df, ["Ana Sınıf", "Alt Sınıf", "Sektör", "Sembol"])

    # Her seviye toplamı portföy toplamına eşit olmalı (150), katlanmamalı
    by_depth: dict[int, float] = {}
    depth_of = {0: 0}
    for s, t_, v in zip(sk["source"], sk["target"], sk["value"]):
        d = depth_of[s] + 1
        depth_of[t_] = d
        by_depth[d] = by_depth.get(d, 0) + v
    assert all(v == pytest.approx(150.0) for v in by_depth.values())
    assert len(by_depth) == 4
    # Düğüm sayısı: kök + 1 ana + 2 alt + 2 sektör + 2 sembol = 8
    assert len(sk["labels"]) == 8


def test_sankey_empty_is_safe():
    sk = an.sankey_data(pd.DataFrame(), ["Ana Sınıf"])
    assert sk["labels"] == [] and sk["value"] == []


# --------------------------------------------------------------- pozisyon ekle
def test_merge_add_recomputes_average_cost():
    base = [{"symbol": "THYAO.IS", "hesap": "", "qty": 100, "avg_cost": 200}]
    out = an.merge_position(base, {"symbol": "THYAO.IS", "hesap": "", "qty": 100,
                                   "avg_cost": 300}, mode="add")
    assert len(out) == 1
    assert out[0]["qty"] == 200 and out[0]["avg_cost"] == pytest.approx(250)


def test_merge_replace_and_separate_accounts():
    base = [{"symbol": "THYAO.IS", "hesap": "", "qty": 100, "avg_cost": 200}]
    out = an.merge_position(base, {"symbol": "THYAO.IS", "hesap": "", "qty": 50,
                                   "avg_cost": 400}, mode="replace")
    assert out[0]["qty"] == 50 and out[0]["avg_cost"] == 400
    out2 = an.merge_position(out, {"symbol": "THYAO.IS", "hesap": "Midas",
                                   "qty": 10, "avg_cost": 500}, mode="add")
    assert len(out2) == 2   # farklı kurum = ayrı pozisyon


# ---------------------------------------------------------------------- metal
def test_metal_unit_price():
    # 3000 $/ons, kur 40 -> gram TL ≈ 3000/31.1035*40
    gram = px._metal_unit_price(3000.0, "GRAM", "TRY", 40.0)
    assert gram == pytest.approx(3000 / px.TROY_OUNCE_G * 40, rel=1e-6)
    ceyrek = px._metal_unit_price(3000.0, "CEYREK", "TRY", 40.0)
    assert ceyrek == pytest.approx(gram * METAL_UNITS["CEYREK"], rel=1e-6)
    assert px._metal_unit_price(3000.0, "ONS", "USD", None) == pytest.approx(3000.0)
    assert px._metal_unit_price(3000.0, "GRAM", "TRY", None) is None  # kur yoksa None


# -------------------------------------------------------------------- depolama
def test_storage_local_roundtrip(tmp_path):
    p = tmp_path / "assets.json"
    s = Storage({}, local_path=str(p))
    assert s.backend == "local"
    s.save([{"symbol": "X"}], "test")
    assert s.load().data == [{"symbol": "X"}]
    assert json.loads(p.read_text(encoding="utf-8"))[0]["symbol"] == "X"


def test_storage_detects_github_config():
    s = Storage({"token": "t", "repo": "u/r"})
    assert s.enabled and s.backend == "github"


# ------------------------------------------------------- değerleme modu (kova)
def test_bucket_valuation_uses_manual_total_not_qty():
    """Kova satırı: adet 0 olsa bile değer sıfırlanmaz, elle girilen tutar kullanılır."""
    a = normalize_asset({
        "symbol": "GMSTR.IS", "display": "GMSTR_VB", "source": SRC_YAHOO,
        "currency": "TRY", "ana_sinif": "Emtia", "alt_sinif": "Gümüş",
        "sektor": "Gümüş ETF", "hesap": "GMSTR_VB",
        "valuation": "value", "qty": 0.0, "avg_cost": 50_000.0,
        "manual_price": 61_816.0,
    })
    assert a["valuation"] == "value"
    df = an.build_dataframe([a], {"GMSTR.IS": _q(52.3)}, {})
    row = df.iloc[0]
    assert row["Değer (TRY)"] == pytest.approx(61_816.0)      # 0 × 52.3 DEĞİL
    assert row["Maliyet (TRY)"] == pytest.approx(50_000.0)
    assert row["K/Z %"] == pytest.approx((61_816 - 50_000) / 50_000 * 100)
    assert row["Değerleme"] == "Kova (elle)"
    assert row["Fiyat"] == pytest.approx(52.3)                # canlı fiyat bilgi olarak


def test_bucket_infers_value_mode_from_legacy_record():
    a = normalize_asset({"symbol": "X", "source": "manual", "qty": 0,
                         "manual_price": 1000, "avg_cost": 900})
    assert a["valuation"] == "value"
    b = normalize_asset({"symbol": "Y", "source": "yahoo", "qty": 10, "avg_cost": 5})
    assert b["valuation"] == "qty"


def test_bucket_promotion_keeps_cost_basis():
    """Kova -> adet moduna geçişte toplam maliyet birim maliyete bölünmeli."""
    total_cost, qty = 50_000.0, 1_000.0
    unit_cost = total_cost / qty
    a = normalize_asset({
        "symbol": "GMSTR.IS", "source": SRC_YAHOO, "currency": "TRY",
        "ana_sinif": "Emtia", "alt_sinif": "Gümüş", "sektor": "Gümüş ETF",
        "valuation": "qty", "qty": qty, "avg_cost": unit_cost,
    })
    df = an.build_dataframe([a], {"GMSTR.IS": _q(62.0)}, {})
    assert df.iloc[0]["Maliyet (TRY)"] == pytest.approx(total_cost)
    assert df.iloc[0]["Değer (TRY)"] == pytest.approx(62_000.0)
