# Kalite profilleri: Hızlı / Dengeli / Maksimum (Bölüm H)

> **Doküman/sayı değişkenliği uyarısı:** Claude Code sürümden sürüme değişir; komut ve ayar adları 2026-10-10'da dokümana karşı doğrulandı (bkz. `scope-honesty.md`). Etiketler: [D] doküman · [I] çıkarım, doğrulanmadı.

Hiçbir profil otomatik açılmaz. Seçilen profil yalnız o görev/oturum için geçerlidir ve ayar dosyalarına YAZILMAZ; aşağıdaki blok görev isteminin sonuna kopyalanır. Kalıcılık (CLAUDE.md, hook) ancak gösterilen diff ve açık onayla.
Takas sırası: Hızlı < Dengeli < Maksimum → token, süre ve onay sayısı artar (MinToken ile çelişir; `mintoken-interplay.md`). "Kaliteyi 2 katına çıkarır" vaadi YOKTUR; etki `quality-measurement.md` ile ölçülür.

## Hızlı (G7 + H15) — düşük ek yük
```
[HighPer: Hızlı]
- Başarı ölçütü: <buraya yaz: ör. "./gradlew compileJava 0 ile çıkar">
- Bitirirken: çalıştırdığın doğrulama komutunu ve çıktısını göster; çalıştırmadıysan "DOĞRULANMADI" yaz.
```

## Dengeli (varsayılan öneri) — G1 + G2 + G7 + dar doğrulama hook'u (H18) + /clear disiplini
```
[HighPer: Dengeli]
1. Kodlamadan önce 5–10 satır kabul ölçütü, kapsam dışı listesi ve riskleri yaz; onayımı bekle.
2. Mümkünse önce hatayı/başarısız testi yeniden üret (ör. ./gradlew compileJava), sonra düzelt.
3. Doğrulama merdiveni: compileJava → ilgili test → tam build. Yalnız geçen adım sonrakine geçer.
4. Bitirirken: değişen dosyalar, çalıştırılan komutlar + çıktıları, çalıştırılmayan doğrulamalar ("DOĞRULANMADI"), bilinen sınırlamalar.
Bu görev bitince yeni görev için /clear.
```
Dar doğrulama hook'u (opsiyonel, onaylı): `scripts/verify_gate.py` Stop hook'u — yalnız hızlı komutlarla (ör. `compileJava`); diff + açık onayla kurulur.

## Maksimum kalite — Dengeli + G3 + G4 + G6 (riskli işte G8), effort yükseltme (H1), gerekirse advisor (H6)
```
[HighPer: Maksimum]
(Dengeli'deki 1–4 aynen)
5. İşi bağımsız doğrulanabilir adımlara böl; her adım sonunda doğrulama komutu; her adımda git geri dönüş noktası (commit'i ben onaylarım).
6. Bitince AYRI bir alt-ajanla incele (temiz bağlam, yalnız diff + kabul ölçütleri, yalnız okuma araçları):
   "Bu diff kabul ölçütlerini karşılıyor mu? YALNIZ doğruluğu veya belirtilmiş gereksinimleri etkileyen boşlukları işaretle;
    gerisini 'isteğe bağlı' diye ayrı listele. Kabul ölçütleri ve gerçekçi girdiler kapsamında bunu bozabilecek durumları yaz
    ve mümkünse küçük bir testle çalıştır."
   Yalnız "doğruluk/gereksinim" bulgularını düzelt; en çok 2 inceleme turu.
7. API/sürüm/mixin hedefi/mapping adını hafızadan değil projedeki kaynaktan doğrula (gradle dependencies, jar).
```
Takas: belirgin biçimde daha çok token ve süre. Kullanım limiti/maliyet uyarısı: planına göre (Pro/Max/API) `/usage` ile ölç; tahmin verilmez. Effort'u görev başında seç (ortada değiştirmek bazı modellerde önbelleği bozar [D: H4]).

## Görev sınıfına göre öneri (G11)
| Sınıf | Örnek | Profil |
|---|---|---|
| XS | typo, rename, log satırı | profil yok (doğrudan yap; plan modu gereksiz [D: H62]) |
| S | tek dosya | Hızlı (G2+G7) |
| M | çok dosya | Dengeli (G1+G2+G6+G7) |
| L | mimari/riskli | Maksimum (G1–G7, gerekirse G8) |
Sınıfı kullanıcı değiştirebilir; aşırı süreç kalite getirmez, gecikme ve token getirir.
