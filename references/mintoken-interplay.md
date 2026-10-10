# MinToken ile etkileşim (Bölüm C)

> **Doküman/sayı değişkenliği uyarısı:** Claude Code sürümden sürüme değişir. Buradaki ayar adları, sayılar ve sürüm numaraları 2026-10-10'da code.claude.com/docs (221 sayfa, changelog v2.1.296'ya kadar) ve kurulu sürüm 2.1.295 ile karşılaştırıldı; doğrulama durumu `scope-honesty.md` sonundaki tabloda. Kullanmadan önce yeniden doğrula. Etiketler: [D] resmi doküman/Anthropic yayını · [G] oturumda gözlendi · [R] üçüncü taraf, doğrulanmadı · [I] çıkarım, doğrulanmadı.

## BÖLÜM C — MİNTOKEN İLE ETKİLEŞİM (çakışma tablosu)

HighPer, MinToken kurulu mu diye `~/.claude/skills/mintoken/` varlığına bakar (salt okunur). Çelişki varsa rapor yan yana iki sütun verir; kendi seçmez.

| Konu | HighPer'in yönü | MinToken'ın yönü | Takas |
|---|---|---|---|
| Effort | karmaşık işte yükselt | düşür/varsayılanda tut | doğruluk ↔ token, gecikme |
| Alt-ajan | keşfi ayır, paralelleştir | çarpanı azalt (B8) | bağlam temizliği ↔ token çarpanı |
| `/compact` zamanı | erken, kontrollü | önbellek sıcakken ucuz | kayıp ↔ yeniden kurma |
| Workflow/ultracode, agent teams | büyük bağımsız işte hız | yasak/uyarı | hız ↔ yüksek token |
| Basitleştirme anahtarları | önerme (kalite riski) | öner (token) | kalite ↔ token |
| İnceleme kapıları (`/code-review`, security-guidance) | doğruluk artar | yük ve maliyet | doğruluk ↔ maliyet, gecikme |
| Tool search / alwaysLoad | gecikme ve doğruluk için seçici | hepsini ertele | ilk tur hız ↔ bağlam |
| Hook | deterministik doğrulama | yan istek/bağlam maliyeti | doğruluk ↔ gecikme |

Ortak (çakışmayan) noktalar: bağlam hijyeni (`/clear`, `/rewind`), önbellek korunumu, gürültülü çıktının filtrelenmesi, dar arama, gözetimsiz çalışma freni, ağ geçidi önbelleği. Bunlarda iki skill aynı yöndedir.

HighPer bu tabloyu kendi seçmeden, iki sütun yan yana raporlar. MinToken kurulu değilse (`~/.claude/skills/mintoken/` yok) tablo yalnız bilgi amaçlıdır.
