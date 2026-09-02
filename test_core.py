"""MSP portföy raporu içe aktarımı testleri."""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import import_msp as msp  # noqa: E402
from portfolio.classification import SRC_YAHOO, VALID_SOURCES  # noqa: E402

KUR = 41.2


@pytest.fixture(scope="module")
def kayitlar():
    return [msp.kayit_uret(s, d, q, c, KUR) for s, d, q, c in msp.POZISYONLAR]


def test_transkripsiyon_gerceklesmemis_kz_ile_dogrulanir():
    """
    Rapordaki "Değer"/"Maliyete göre" satırları gerçekleşmiş kâr dahil TÜM
    ZAMAN birikimidir; açık pozisyonların toplamı DEĞİLDİR. Transkripsiyonun
    tek geçerli çapası gerçekleşmemiş K/Z'dir.
    """
    deger = sum(d for _, d, _, _ in msp.POZISYONLAR)
    maliyet = sum(q * c for _, _, q, c in msp.POZISYONLAR)
    sapma = (deger - maliyet) - msp.RAPOR_GERCEKLESMEMIS
    assert abs(sapma) <= msp.RAPOR_TOLERANS, (
        f"gerçekleşmemiş K/Z {deger - maliyet:,.2f}, "
        f"rapor {msp.RAPOR_GERCEKLESMEMIS:,.2f}"
    )


def test_uc_harfli_abd_sembolleri_tefas_sanilmaz(kayitlar):
    """
    REGRESYON: auto_fill_asset üç harfli her kodu TEFAS fonu sayıyor
    (TEFAS_CODE_RE = ^[A-Z]{3}$). NOK / NEE / PGY / CEG / SMR / BKR / WBD /
    FLY bu yüzden "tefas" kaynağına düşüyor ve fiyatı hiç çekilemiyordu.
    """
    kritik = {"NOK", "NEE", "PGY", "CEG", "SMR", "BKR", "WBD", "FLY"}
    for k in kayitlar:
        if k["symbol"] in kritik:
            assert k["source"] == SRC_YAHOO, k["symbol"]
            assert k["currency"] == "USD", k["symbol"]
            assert k["alt_sinif"] != "TEFAS", k["symbol"]


def test_tum_kayitlar_yahoo_kaynakli(kayitlar):
    """MSP raporundaki her satır borsada işlem gören bir semboldür."""
    for k in kayitlar:
        assert k["source"] == SRC_YAHOO
        assert k["source"] in VALID_SOURCES


def test_pazar_ayrimi(kayitlar):
    for k in kayitlar:
        sym = k["symbol"]
        if sym.endswith(".IS"):
            assert k["currency"] == "TRY" and k["alt_sinif"] == "BIST"
        elif sym.endswith("-USD"):
            assert k["currency"] == "USD" and k["ana_sinif"] == "Kripto"
        else:
            assert k["currency"] == "USD" and k["ana_sinif"] != "Kripto"


def test_bist_maliyeti_kurla_cevrilir(kayitlar):
    isctr = next(k for k in kayitlar if k["symbol"] == "ISCTR.IS")
    assert isctr["avg_cost"] == pytest.approx(0.08 * KUR)
    assert "kur" in isctr["notlar"]


def test_abd_maliyeti_cevrilmez(kayitlar):
    nvda = next(k for k in kayitlar if k["symbol"] == "NVDA")
    assert nvda["avg_cost"] == pytest.approx(197.97)


def test_kapanan_pozisyonlar_yazilmaz(kayitlar):
    semboller = {k["symbol"] for k in kayitlar}
    for s in msp.KAPANAN:
        assert s not in semboller


def test_wbd_sifir_maliyet_uyarisi(kayitlar):
    wbd = next(k for k in kayitlar if k["symbol"] == "WBD")
    assert wbd["qty"] == 32
    assert wbd["avg_cost"] == 0.0
    assert "UYARI" in wbd["notlar"]


def test_hepsi_canli_degerlemede(kayitlar):
    """Adet girildiği için hiçbiri 'kova' moduna düşmemeli."""
    for k in kayitlar:
        assert k["valuation"] == "qty"
        assert k["qty"] > 0


def test_semboller_benzersiz(kayitlar):
    anahtarlar = [f"{k['symbol']}|{k['hesap']}" for k in kayitlar]
    assert len(anahtarlar) == len(set(anahtarlar))


def test_cakisan_kovalar_kaldirilir(tmp_path):
    kaynak = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "my_assets.json")
    hedef = tmp_path / "assets.json"
    with open(kaynak, encoding="utf-8") as f:
        mevcut = json.load(f)
    hedef.write_text(json.dumps(mevcut, ensure_ascii=False), encoding="utf-8")

    r = msp.calistir(str(hedef), yaz=False, usdtry=KUR)
    kalan = {a["symbol"] for a in r["varliklar"][: r["korunan"]]}
    assert not (kalan & msp.CAKISAN_KOVALAR)
    assert r["eklenen"] == len(msp.POZISYONLAR)
    assert r["dogrulandi"]

    # Tekrar çalıştırmak satırları ÇOĞALTMAMALI: önceki MSP aktarımı silinir.
    hedef.write_text(json.dumps(r["varliklar"], ensure_ascii=False),
                     encoding="utf-8")
    r2 = msp.calistir(str(hedef), yaz=False, usdtry=KUR)
    assert r2["toplam"] == r["toplam"]
    assert r2["korunan"] == r["korunan"]
