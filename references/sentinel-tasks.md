# Regresyon nöbetçisi: mini görev seti ve kayıt şeması (Bölüm N)

> **Doküman/sayı değişkenliği uyarısı:** Claude Code sürümden sürüme değişir; ayar/komut adları 2026-10-10'da dokümana karşı doğrulandı (bkz. `scope-honesty.md`).

## Şablon (kullanıcı doldurur; içerik kullanıcıya aittir, hiçbir yere gönderilmez)
| Görev kimliği | Açıklama (kısa) | Başlangıç commit'i | Başarı ölçütü | Doğrulama komutu |
|---|---|---|---|---|
| T1 | yeni event handler ekle | `<sha>` | handler kayıtlı, test geçer | `./gradlew test --tests '*Handler*'` |
| T2 | mixin hatasını kök nedenle düzelt | `<sha>` | `compileJava` + `runServer` açılışında mixin hatası yok | `./gradlew compileJava` |
| T3 | komutu refactor et + test | `<sha>` | davranış aynı, test geçer | `./gradlew test` |

## Kayıt şeması (yerel JSON, `scripts/sentinel.py add`)
YALNIZ sayısal alanlar ve sürüm/ayar etiketleri saklanır; ham mesaj metni, kod ve serbest metin not SAKLANMAZ.

| Alan | Tür | Örnek |
|---|---|---|
| date | ISO tarih | 2026-10-10 |
| claude_version | etiket | 2.1.295 |
| model | etiket | claude-opus-5-5 |
| effort / effort_source | etiket | medium / model-default |
| output_style | etiket | default |
| plugins | etiket listesi (ad) | claude-mem |
| task_id | etiket | T1 |
| first_try_pass | 0/1 | 1 |
| fix_rounds | tam sayı | 0 |
| minutes | sayı | 7.5 |
| interventions | tam sayı | 1 |
| cache_misses | tam sayı | 0 |

Not: N2 "notlar" alanını sayar, ancak aynı maddedeki "YALNIZ sayısal alanlar ve sürüm/ayar etiketleri" kuralı daha sıkıdır; HighPer serbest metin notu saklamaz.

## Tetikleyiciler (N3) ve yorum (N4)
- Sürüm yükseltmesi, model takma adının yeni sürüme çözülmesi, changelog'da effort varsayılanı değişikliği, "kötüleşti" şikâyeti → N1 seti (kullanıcı onayıyla; token/süre bedeli var).
- Tek koşu kanıt değildir; ≥3 tekrar, aynı model/effort/başlangıç commit'i. Fark gürültü içindeyse "değişiklik görülmedi". Rastgele hata sınıfında (K2-3) aynı istem bir geçip bir kalabilir [D].
- Karşılaştırma: `python scripts/sentinel.py compare --by claude_version` (veya `--by model`).
