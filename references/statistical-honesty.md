# İstatistiksel dürüstlük (Bölüm Q)

> **Doküman/sayı değişkenliği uyarısı:** Claude Code sürümden sürüme değişir. Buradaki ayar adları, sayılar ve sürüm numaraları 2026-10-10'da code.claude.com/docs (221 sayfa, changelog v2.1.296'ya kadar) ve kurulu sürüm 2.1.295 ile karşılaştırıldı; doğrulama durumu `scope-honesty.md` sonundaki tabloda. Kullanmadan önce yeniden doğrula. Etiketler: [D] resmi doküman/Anthropic yayını · [G] oturumda gözlendi · [R] üçüncü taraf, doğrulanmadı · [I] çıkarım, doğrulanmadı.

## Q. İSTATİSTİKSEL DÜRÜSTLÜK (kullanıcının "%0,00001" beklentisi için)

- Q1 Rapor dili: "N tesliminde 0 kaçak görüldü; %95 güvenle üst sınır ≈ 3/N" ([I], üç kuralı); asla "kaçak yok", "sıfır risk" veya "garantili". Küçük N'de bu üst sınırın büyük olduğu açıkça yazılır.
- Q2 Ölçülebilir en küçük etki: görev seti büyüklüğüne bağlıdır (100 görevde bir görev = %1); daha küçük farkı görmek için çok daha fazla görev gerekir; HighPer kullanıcıya "bu görev setiyle görebileceğin en küçük fark şu" hesabını gösterir (quality_score.py `--min-detectable`).
- Q3 Tek ölçüt yanıltıcıdır: ilk-denemede-doğru oranı, kaçak oranı, düzeltme turu, kullanıcı müdahalesi ayrı raporlanır; tek bir "kalite" sayısına indirilmez (v2 I1).
- Q4 Sorumluluk dili: HighPer sonuçları "kanıtlandı" yerine "bu doğrulamalardan geçti" diye yazar; nihai karar kullanıcıdadır.

## Hesaplar (scripts/quality_score.py)
- Üç kuralı: N denemede 0 kaçak → %95 güvenle üst sınır ≈ 3/N [I: standart istatistik]. 40 teslimde ≈ %7,5; 300'de ≈ %1; 10⁻⁷ için ≈ 30.000.000 deneme.
- Ölçülebilir en küçük fark (iki oran, %95 güven, %80 güç, yaklaşık): her kolda n görevle MDE ≈ 2,8·√(2·p(1−p)/n). Rapor: "bu görev setiyle görebileceğin en küçük fark şu".
- Rapor dili: "N tesliminde 0 kaçak görüldü; %95 güvenle üst sınır ≈ 3/N" — asla "kaçak yok", "sıfır risk", "garantili".
