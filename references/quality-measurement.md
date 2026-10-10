# Kalite ölçümü ve "2 kat" hedefinin sınanması (Bölüm I)

> **Doküman/sayı değişkenliği uyarısı:** Claude Code sürümden sürüme değişir. Buradaki ayar adları, sayılar ve sürüm numaraları 2026-10-10'da code.claude.com/docs (221 sayfa, changelog v2.1.296'ya kadar) ve kurulu sürüm 2.1.295 ile karşılaştırıldı; doğrulama durumu `scope-honesty.md` sonundaki tabloda. Kullanmadan önce yeniden doğrula. Etiketler: [D] resmi doküman/Anthropic yayını · [G] oturumda gözlendi · [R] üçüncü taraf, doğrulanmadı · [I] çıkarım, doğrulanmadı.

## I. "KALİTE" ÖLÇÜMÜ VE 2 KAT HEDEFİNİN SINANMASI

- I1 Kalite metriği (kullanıcı görev setinde, 5–10 görev): (a) ilk denemede derleme/test geçti mi (0/1), (b) kabul ölçütlerinin karşılanma oranı (kullanıcı işaretler), (c) düzeltme turu sayısı, (d) kullanıcı müdahalesi sayısı (itiraz/yön düzeltme), (e) gözden geçiricinin bulduğu gerçek hata sayısı, (f) görev süresi. "Kalite" tek bir sayıya indirgenmez; (a)–(d) birlikte raporlanır. Birleşik skor isteniyorsa formülü ve ağırlıkları açıkça yaz; ağırlığı kullanıcı seçer.
- I2 2 kat nasıl sınanır: hedef, "ilk denemede doğru oranı"nın veya "düzeltme turu azalışı"nın iki katı gibi KENDİ seçtiği bir metrikte tanımlanır. Taban: HighPer'siz mevcut düzen, en az 3 tekrar × görev seti. Sonra: profil açık. Aynı model/effort/başlangıç commit'i, tek değişken. Tavan uyarısı: taban zaten yüksekse (ör. %80+) 2 kat matematiksel olarak imkânsızdır; bunun yerine "hata oranının yarıya inmesi" daha anlamlı hedef olabilir; HighPer bunu önerir, seçimi kullanıcı yapar.
- I3 Sonuç raporu: metrik, taban, sonrası, tekrar sayısı, belirsizlik/gürültü, hangi kaldıraç (H/F/G) etkili görünüyor (bisect), maliyet/süre bedeli. Etki görünmezse "bu görev setinde fark görülmedi" yazılır; abartı yok. Örneklem küçükse "kanıt değil, işaret" denir.
- I4 Kör karşılaştırma: mümkünse sonuçları kullanıcı hangi koşuldan geldiğini bilmeden puanlar (iki çıktıyı karıştırıp sunar); beklenti yanlılığını azaltır [I].
- I5 Sürekli iyileştirme: perf_baseline.py aylık/oturum bazlı eğilimi (tur sayısı, hata oranı, tekrar sayısı) yalnız sayaç olarak gösterir; kötüleşen eksen için F avı çalıştırır.

Araç: `python scripts/quality_score.py` (I1 metrikleri, ağırlık/formül gösterimi, `--min-detectable`, üç kuralı).
"2 kat" bir VAAT değildir; yalnız kullanıcının seçtiği metrikte ölçülürse "bu görev setinde şu kadar oldu" diye raporlanır. Tavan: taban ≥%50 ise ilk-denemede-doğru oranı matematiksel olarak 2 katına çıkamaz (≤%100); o durumda "hata oranının yarıya inmesi" önerilir.
