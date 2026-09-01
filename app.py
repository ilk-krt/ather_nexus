"""
AETHER NEXUS — Canlı portföy takip uygulaması.
Streamlit üzerinde çalışır, portföyünü GitHub deposunda kalıcı tutar.

Çalıştırma:  streamlit run app.py
"""

from __future__ import annotations

import logging

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from portfolio import analytics as an
from portfolio import prices as px
from portfolio.classification import (
    ANA_SINIFLAR,
    HIERARCHY,
    HIERARCHY_LABELS,
    METAL_UNITS,
    SRC_CASH,
    SRC_GOLD,
    SRC_MANUAL,
    SRC_SILVER,
    SRC_TEFAS,
    SRC_YAHOO,
    VAL_QTY,
    VAL_VALUE,
    asset_key,
    auto_fill_asset,
    normalize_asset,
)
from portfolio.storage import Storage, StorageError, storage_from_secrets

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
