# AETHER NEXUS — Portföy Takip

Streamlit üzerinde çalışan, varlık sınıflarına göre kırılım veren canlı portföy
uygulaması. Portföy kaydı GitHub deposunda kalıcı tutulur.

## Kurulum

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Kalıcı kayıt (ÖNEMLİ)

Streamlit Community Cloud'da dosya sistemi geçicidir — uygulama uykuya girip
uyandığında `my_assets.json` silinir. Bu yüzden kayıt doğrudan GitHub'a commit
edilir.

1. GitHub → Settings → Developer settings → Personal access tokens →
   **Fine-grained tokens**
   - Repository access: sadece bu depo
   - Permissions → Repository permissions → **Contents: Read and write**
2. Streamlit Cloud → App → Settings → **Secrets**:

```toml
[github]
token  = "github_pat_..."
repo   = "kullaniciadi/depo-adi"
branch = "main"
path   = "my_assets.json"
```

Jeton yoksa uygulama yerel dosya moduna düşer ve ekranda uyarı gösterir.

## Bluecoins yedeğinden içe aktarma

```bash
python import_bluecoins.py Bluecoins_20260901.fydb -o my_assets.json
python import_bluecoins.py yedek.fydb --include-hidden --include-liabilities
```

Bluecoins'te tuttuğunuz hesap ağacı (`01_BIST` … `08_CRYPTO`, `Properties`,
`Receivables`, `Liabilities`) varlık sınıfı hiyerarşisine çevrilir. Döviz
hesaplarında bakiye hesabın kendi para biriminde yazılır; TL karşılığı
uygulamada **canlı kurla** hesaplanır (Bluecoins'teki sabit kur kullanılmaz).

## Dosya düzeni

```
app.py                      Streamlit arayüzü
import_bluecoins.py         .fydb → my_assets.json dönüştürücü
portfolio/classification.py Varlık sınıfları, otomatik tanıma, eski şema göçü
portfolio/prices.py         Yahoo Finance + TEFAS + altın/gümüş fiyat motoru
portfolio/storage.py        GitHub Contents API ile kalıcı kayıt
portfolio/analytics.py      Hesaplamalar, Sankey/dağılım verisi
tests/test_core.py          Ağ gerektirmeyen testler (pytest)
```

## Varlık kaydı şeması (`my_assets.json`)

```jsonc
{
  "symbol": "THYAO.IS",      // fiyat kaynağındaki tam sembol
  "display": "THYAO",        // ekranda görünen ad
  "source": "yahoo",         // yahoo | tefas | gold | silver | cash | manual
  "currency": "TRY",
  "ana_sinif": "Hisse Senedi",
  "alt_sinif": "BIST",
  "sektor": "Havacılık",
  "hesap": "Midas",          // aynı hisse farklı kurumda ayrı satır olur
  "unit": null,              // altın/gümüş için GRAM, CEYREK, ONS…
  "qty": 1000,
  "avg_cost": 250.0,
  "manual_price": null       // source="manual" ise güncel değer
}
```

`source` (fiyat nereden gelir) ile `ana_sinif/alt_sinif/sektor` (nasıl gruplanır)
**birbirinden bağımsızdır**. Sınıflandırmayı değiştirmek fiyat çekmeyi bozmaz.

## Eski koda göre düzeltilenler

| Sorun | Durum |
|---|---|
| Streamlit Cloud'da kayıtların silinmesi | GitHub'a commit ile çözüldü |
| TEFAS HTML scraping'i hep boş dönüyordu (sayfa JS ile doluyor) | Sitenin POST API'si (`BindHistoryInfo`) kullanılıyor |
| `if True else 34.50` — anlamsız ifade, kur çökerse uygulama kırılıyordu | Kur hatası açıkça raporlanıyor |
| `except: pass` — fiyat hataları sessizce yutuluyordu | Her satırda kaynak + hata gösteriliyor |
| Altın hep gram varsayılıyordu | GRAM/ÇEYREK/YARIM/TAM/CUMHURİYET/ONS/bilezik birimleri |
| Aynı sembolü ikinci kez eklemek ortalama maliyeti siliyordu | Ağırlıklı ortalama maliyet hesabı |
| Sankey'de aynı isimli sektör/sembol düğümleri birleşiyordu | Düğüm kimliği tam yol üzerinden üretiliyor |
| Toplam K/Z yüzdesi satır yüzdelerinden hesaplanıyordu | TL maliyet/değer üzerinden ağırlıklı hesap |
| Her sembol için ayrı ağ çağrısı | Tek toplu çağrı + tekil yedek + 5 dk önbellek |
| EUR varlıklar USD gibi çevriliyordu | EURTRY / EURUSD çapraz kuru |
| Pozisyon silme, yedek alma yoktu | Silme, CSV/JSON dışa aktarma, JSON'dan geri yükleme |

## Testler

```bash
python -m pytest tests/ -q
```

## Değerleme modu

Her pozisyonun bir `valuation` alanı vardır:

- `"qty"` → **Adet × canlı birim fiyat**. Klasik pozisyon.
- `"value"` → **Kova**: değer, elle girdiğiniz toplam tutardır (Bluecoins'teki
  *Adjustment* mantığı). Fiyat kaynağı tanımlıysa canlı birim fiyat yine gösterilir
  ama değere karışmaz.

"Değer Güncelle" sekmesinde bir kovanın **Adet** hücresine sıfırdan büyük bir sayı
yazıp kaydettiğinizde satır kalıcı olarak `"qty"` moduna geçer; toplam maliyet
otomatik olarak birim maliyete bölünür, böylece kâr/zarar tutarlı kalır.

Bu sayede portföyü tek seferde dönüştürmek zorunda kalmazsınız: elinizdeki
kovaların adedini öğrendikçe teker teker canlı fiyatlamaya geçirirsiniz.
