# Verimsizlik avı (Bölüm F)

> **Doküman/sayı değişkenliği uyarısı:** Claude Code sürümden sürüme değişir. Buradaki ayar adları, sayılar ve sürüm numaraları 2026-10-10'da code.claude.com/docs (221 sayfa, changelog v2.1.296'ya kadar) ve kurulu sürüm 2.1.295 ile karşılaştırıldı; doğrulama durumu `scope-honesty.md` sonundaki tabloda. Kullanmadan önce yeniden doğrula. Etiketler: [D] resmi doküman/Anthropic yayını · [G] oturumda gözlendi · [R] üçüncü taraf, doğrulanmadı · [I] çıkarım, doğrulanmadı.

## F. VERİMSİZLİK AVCISI (araç, eklenti, alışkanlık, yapılandırma)

HighPer her oturumda, istenince `/highper hunt` ile şu avı yapar. Hepsi SALT OKUNUR; bulgu → kanıt → öneri → takas → geri alma biçiminde raporlanır; hiçbir şey onaysız değişmez.

- F1 Kullanılmayan yük: kullanılmayan eklenti/skill/MCP/hook; `/doctor` ve `/skill-doctor` çıktısı, `claude plugin details` "Always-on" satırı, "Not used recently" grubu [D, v6 C135]. Bağlam ve araç seçimi karışıklığı (modelin yanlış araca yönelmesi) doğruluğu da düşürür [I].
- F2 Çakışan araçlar: aynı işi yapan iki skill/eklenti/MCP (ör. iki kod arama aracı, iki bellek aracı); açıklamaları örtüşen skill'ler yanlış tetiklenir [I]. Çift yüklenen skill/hook (eklentiye çevrilip orijinali silinmeyen kurulum) hook'u İKİ KEZ çalıştırır [D]. Çakışan çiftleri listele, hangisinin kalacağını kullanıcı seçsin.
- F3 Tekrarlayan aynı eylem: oturum kayıtlarında aynı dosyanın/komutun art arda yeniden okunması/çalıştırılması (perf_baseline.py sayaçları). Nedenleri: sıkıştırmada kaybolan içerik, belirsiz görev, başarı ölçütü eksikliği, ilgisiz çıktı. Çözüm: ilgili H maddesi.
- F4 Başarısız araç çağrısı kümeleri: aynı araç/komut tekrar tekrar hata veriyorsa kök neden sınıfı: izin reddi, yanlış yol, eksik araç, zaman aşımı, sandbox. İzin reddi kaynaklıysa dar `allow` kuralı önerisi (gevşetmeden, onayla); hata döngüsünde 2 başarısız denemeden sonra durma/geri sarma kuralı (H11).
- F5 Yavaş hook/komut: her düzenlemede çalışan yavaş hook, uzun bloklayan Bash, ön planda bekleyen Gradle/sunucu süreci. Ölçülen süre + matcher/`if` daraltma + arka plana alma [D, H18, H26].
- F6 Zayıf talimat: çelişkili/eski/belirsiz CLAUDE.md kuralları, doğrulama komutu eksikliği, 200 satırı/25 KB'ı aşan MEMORY.md [D]. claude_md_lint.py bulgularını önem sırasıyla ver.
- F7 Yanlış model/effort eşleşmesi: zor işte düşük effort (hata), kolay işte yüksek effort (yavaşlık); alt-ajanların beklenmedik modele çözülmesi [D, H1–H3].
- F8 Ağ/sağlayıcı yavaşlığı: önbellek ıskası, geçidin `cache_control` silmesi, tekrarlayan yeniden denemeler [D, H28–H36].
- F9 Davranış değiştiren gizli bileşenler: mod (`turn.step`, `$.prompt.submit`), eklenti hook'ları, çıktı stili (kodlama talimatını düşüren), `outputStyle`, `force-for-plugin` [D, H44, H46]. `claude --safe-mode` ile temiz tabana karşı karşılaştır: kalite/hız farkı bunlardan geliyorsa kanıt budur.
- F10 Sinyal/gürültü: kullanıcı istemlerinde yapıştırılan dev log, belirsiz tek cümlelik görev, aynı oturumda ilgisiz çoklu görev (H8).
Bulguların öncelik sırası: (1) doğruluğu bozan, (2) güvenilirliği bozan, (3) gecikme, (4) maliyet. Çıktı en fazla 10 madde; her biri kanıt taşır.

Araç: `python scripts/hunt.py` (salt okunur; audit_perf + claude_md_lint + perf_baseline + dup_detect birleşik, en çok 10 bulgu).
