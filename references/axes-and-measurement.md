# Performans eksenleri ve ölçüm protokolü (Bölüm A + E)

> **Doküman/sayı değişkenliği uyarısı:** Claude Code sürümden sürüme değişir. Buradaki ayar adları, sayılar ve sürüm numaraları 2026-10-10'da code.claude.com/docs (221 sayfa, changelog v2.1.296'ya kadar) ve kurulu sürüm 2.1.295 ile karşılaştırıldı; doğrulama durumu `scope-honesty.md` sonundaki tabloda. Kullanmadan önce yeniden doğrula. Etiketler: [D] resmi doküman/Anthropic yayını · [G] oturumda gözlendi · [R] üçüncü taraf, doğrulanmadı · [I] çıkarım, doğrulanmadı.

## BÖLÜM A — "PERFORMANS" NEDİR: 6 EKSEN

HighPer her bulguyu bir eksene bağlar ve ekseni ölçülebilir kılar.

- P1 Doğruluk: ilk denemede doğru/derlenen/testi geçen sonuç oranı; geri alınan/yeniden yapılan iş.
- P2 Gecikme: bir görevin duvar saati süresi; ilk bayt/ilk yanıt beklemesi; araç çağrısı başına bekleme (build, MCP, hook).
- P3 Tur verimi: görev başına model turu ve araç çağrısı; aynı dosyanın/komutun tekrar okunması/çalıştırılması; boşa tur (reddedilen/engellenen eylem).
- P4 Bağlam sağlığı: bağlamın alakasız/eski içerikle şişmesi, sıkıştırma sonrası kayıp talimat, "yön kaybı".
- P5 Güvenilirlik: araç hata oranı, yeniden deneme/zaman aşımı/kesilen akış, tamamlanamayan uzun görev.
- P6 Verim: paralel yürütülebilen işin gerçekten paralel yürütülmesi; boşta bekleyen kullanıcı/oturum süresi.

## BÖLÜM E — ÖLÇÜM PROTOKOLÜ (yüzde iddiası yerine kullanıcının kendi rakamı)

Performans algısı yanıltıcıdır; HighPer ölçmeden öneri vermez (İlke 7).

1. Taban çizgisi: perf_baseline.py (salt okunur) yerel oturum kayıtlarını (`~/.claude/projects/**/*.jsonl`) tarar [G: bu tür kayıtlar bu ortamda gözlendi; biçim sürüme göre değişebilir → önce 1 satır şemasını doğrula, tanımazsa dur ve kullanıcıya söyle]. YALNIZ sayaç/süre çıkarır: oturum başına tur sayısı, araç çağrısı sayısı, başarısız araç çağrısı oranı, aynı komutun/dosyanın tekrar sayısı, mesajlar arası süre dağılımı (medyan/p90), sıkıştırma sayısı, yeniden deneme/kesinti işaretleri, önbellek okuma/oluşturma oranı (kayıtta varsa). Ham mesaj metni raporlanmaz.
2. `/usage` ve `/context` görüntüleri (kullanıcı yapıştırır): `Prompt cache (main)`, Loops, MCP/Skills/Memory satırları [D].
3. Karşılaştırma: aynı tür görevde (ör. "Fabric modda yeni bir event handler ekle") önce/sonra; aynı model, aynı effort, mümkünse aynı başlangıç commit'i. En az 3 tekrar; tek koşu istatistik değildir. Değişkenleri (model, effort, eklentiler, günün yükü) kaydet; birden çok şeyi aynı anda değiştirme (bisect).
4. Başarı ölçütleri (görev bazlı, kullanıcının tanımıyla): ilk denemede derleme/test geçti mi, kaç düzeltme turu, kaç dakika, kaç tekrar okuma, kaç araç hatası.
5. Bisect sırası: (1) `claude --safe-mode` temiz taban; (2) `claude plugin details <ad>` eklenti sürekli yükü; (3) `/context`; (4) `/usage` önbellek satırı; (5) `/skill-doctor`, `/doctor`; (6) tek tek kaldıraç aç/kapat [D].
6. Rapor: eksen (P1–P6) → ölçülen değer → şüpheli kaldıraç (H-numarası) → önerilen değişiklik → takas → nasıl geri alınır. Gürültü ve örneklem uyarısı her raporda.
7. Kuruluşta OTel: `claude_code.token.usage` (`query_source`: main/subagent/auxiliary) ve hook olayları `stdout_chars`/`additional_context_chars` raporlar [D]. Ham API gövde günlüğü (`OTEL_LOG_RAW_API_BODIES`) konuşmanın tamamını yazar → HighPer ASLA önermez [D].
