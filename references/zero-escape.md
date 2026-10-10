# Sıfır Tolerans profili ("Zero-Escape") — Bölüm O

> **Doküman/sayı değişkenliği uyarısı:** hook şemaları (PreToolUse çıkış kodu 2 engeller; Stop `decision:"block"` + `reason`; ardışık engel üst sınırı 8, `CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`; PreModelSwitch v2.1.251+, çıkış kodu 2 geçişi engeller, otomatik yedek model geçişinde ÇALIŞMAZ) 2026-10-10'da code.claude.com/docs/en/hooks sayfasından doğrulandı. Kullanmadan önce yeniden doğrula.

**HighPer "sıfır kayıp" GARANTİ ETMEZ.** Hedef: doğrulanmadan kullanıcıya ulaşan hatalı sonuç (kaçak) yalnız belgelenmiş kör noktalardan geçebilsin; model hatası olabilir, sessiz kabul olmaz (fail-closed). %0,00001 (10⁻⁷) iddiası için üç kuralıyla ≈30.000.000 başarısız-olmayan bağımsız deneme gerekir [I: standart istatistik] — bu ölçülemez (`statistical-honesty.md`).

Profil HİÇBİR ZAMAN otomatik açılmaz. Takas: belirgin biçimde daha çok token, süre ve onay. Hız/token istenen işte Hızlı/Dengeli profil (`profiles.md`).

## Spec metni (aynen)

## O. SIFIR TOLERANS PROFİLİ ("Zero-Escape")

Profil HIÇBİR ZAMAN otomatik açılmaz; kullanıcı görev veya oturum için açar. Açıkken aşağıdaki kurallar ZORUNLUDUR. Takas: belirgin biçimde daha çok token, süre ve onay; hız ve token istenen görevde Hızlı/Dengeli profil kullanılır (Bölüm H). Profil istemi şablonu references/zero-escape.md içindedir.

- O1 Kapalı-devre (fail-closed) ilke: emin olunmayan her durumda DUR ve kullanıcıya sor; varsayım yapma, "muhtemelen çalışır" yazma. Doğrulama çalıştırılamadıysa sonuç "DOĞRULANMADI" etiketli teslim edilir, "tamam" denmez. Belirsiz gereksinimde uygulamadan önce kabul ölçütlerini yazdırıp onay iste (v2 G1).
- O2 Deterministik kapı (model yargısı değil): "bitti" ancak kullanıcının tanımladığı doğrulama komutları sıfırla çıkınca. Mekanizma: Stop hook'u doğrulama betiğini çalıştırır ve geçene kadar turun bitmesini engeller [D: best-practices "As a deterministic gate"]. Ardışık engel için bir üst sınır vardır ve aşılırsa tur biter; bu durumda HighPer teslimi "DOĞRULANMADI" olarak işaretler (kapının sınırı da bir kör noktadır) [D: hooks Stop input; sınırı sayfadan doğrula]. `/goal` koşulu ikinci katmandır (ayrı değerlendirici); ama yalnız model değerlendirmesidir, deterministik değildir. İkisi birlikte kullanılır, biri diğerinin yerine geçmez.
- O3 Kapsam bekçisi (scope guard): görev başında kullanıcı izin verilen dosya/dizin listesini ve YASAK listesini verir (örn. Fabric: `src/main/java/**`, `src/main/resources/**`; yasak: `build/**`, `run/**`, `.gradle/**`, canlı sunucu dizinleri, `*.jar`, `gradle/wrapper/**`). PreToolUse hook'u (scope_guard.py) Edit/Write ve dosya yazan Bash komutlarını bu listeye karşı denetler; liste dışı yazmayı ENGELLER (çıkış kodu 2 ile engelleme [D: sub-agents hook örneği; hook girdi/çıktı şemasını hooks sayfasından doğrula]). Hook izin sistemini atlatmaz, yalnız ek kısıt koyar; allow/deny kurallarını GEVŞETMEZ. Not: hook'un yakalayamadığı yollar vardır (derlenmiş betikler, dolaylı yazma); bu kör nokta listelenir. Checkpoint ve `/rewind` yalnız Claude'un dosya düzenleme araçlarını kapsar, Bash değişikliklerini ve dış sistem eylemlerini kapsamaz [D]; bu yüzden asıl güvence git'tir (O5).
- O4 Diff denetimi (diff_audit.py, salt okunur): teslimden önce `git diff --stat` ve tam diff'i okuyup kontrol eder: (a) değişen dosyalar izin listesinde mi; (b) kabul ölçütünde olmayan değişiklik var mı (kapsam sızıntısı); (c) silinen/yeniden adlandırılan dosya; (d) üretilmiş/ikili dosya değişti mi; (e) test dosyaları zayıflatıldı mı (silinen assert, `@Disabled`, atlanan test) — "testi geçirmek için testi değiştirme" en klasik kaçaktır [I]; (f) gizli bilgi/anahtar eklendi mi. Bulgular iki sınıfa ayrılır (v3 DZ-J1): doğruluk/gereksinim ve isteğe bağlı. Kullanıcıya diff özeti ve kanıt gösterilir; yorum yok, rakam ve dosya adı.
- O5 Geri dönüş noktası: görev başında temiz git durumu istenir (kirliyse uyar, dur); her adım için kullanıcı onayıyla commit/branch (HighPer kendiliğinden commit/push YAPMAZ). Geri alma planı teslim raporunda yazılır. Canlı sunucuya yazan hiçbir komut çalıştırılmaz; yalnız yerel/test ortamı.
- O6 Üç katmanlı doğrulama (hiçbiri tek başına yeterli sayılmaz): (1) statik: derleme/`compileJava`, linter, tür/LSP tanılamaları; (2) dinamik: ilgili birim/entegrasyon testi, mümkünse çalışan uygulamada `/verify` [D]; (3) bağımsız inceleme: taze bağlamlı alt-ajan veya `/code-review`, yalnız diff + kabul ölçütleriyle [D, v3 DZ-J1]. Fabric/Minecraft için dinamik katman: testler yoksa kısa, başsız (headless) sunucu açılış testi ve mod yükleme/kayıt hatası taraması; bu bir ÖNERİDİR [I], proje düzenine göre kullanıcı tanımlar. Her katmanın yakalayamadığı sınıf rapora yazılır (ör. statik: davranış; dinamik: test kapsamı dışı yol; inceleme: modelle ortak kör nokta).
- O7 Bağımsızlık: gözden geçirici uygulayıcıdan farklı BAĞLAMDA, mümkünse farklı model/effort ile çalışır (aynı model aynı kör noktayı paylaşabilir [I]); Anthropic'in Code Review geri testinde Opus 4.7 hatayı bulurken Opus 4.6 bulamadı [D] — model gücü gözden geçiricide fark yaratabilir; ama pahalıdır. Gözden geçirici salt okunur, en çok 2 tur.
- O8 Çift kontrol edilen kritik sayı/ad/sürüm: Minecraft/Fabric Loader/Fabric API/Loom/mappings sürümleri, mixin hedef adları, API imzaları hafızadan değil projedeki gerçek kaynaktan (gradle dependencies, jar, kaynak) doğrulanır; kaynağı olmayan bilgi "doğrulanmadı" etiketli yazılır (v2 G5).
- O9 Sürüm ve ayar sabitleme: oturum başında `claude --version`, ana model (ve çözülen sürüm), effort ve kaynağı, çıktı stili, eklenti/mod listesi kaydedilir (Bölüm N kayıt şeması); oturum içinde değişirse (model/effort/otomatik yedek model) kullanıcıya bildirilir ve profil bozulmuş sayılır → görev yeniden doğrulanır [D: otomatik yedek model bir model değişimidir]. PreModelSwitch hook'u ile model değişimi onaya bağlanabilir [D: prompt-caching "PreModelSwitch hook"]; hook şemasını sayfadan doğrula; kuruluşa yönelik değil, kullanıcıya onaylı.
- O10 Kanarya (canary): görev başında 1–3 dakikalık, bilinen cevaplı mini görev (ör. küçük bir deterministik fonksiyon + testi) çalıştırılır; beklenmedik düşüş (yanlış sonuç, yabancı karakter, boş yanıt, garip sözdizimi hatası) varsa DUR, `/clear` ile yeni oturum, `claude --safe-mode`, sürüm/model kontrolü (v3 J-1) ve gerekirse `/feedback`. Eylül 2025 olaylarındaki gibi çıktı bozulması İngilizce yanıtta yabancı karakter veya kodda bariz sözdizimi hatası olarak görünebilir [D]. Kanarya bir kaçağı garanti ETMEZ, yalnız bir sınıf bozulmayı erken yakalar.
- O11 Bağlam disiplini (kalıcı kural): görev başına temiz oturum, kritik kurallar CLAUDE.md'de ve ayrıca "Compact Instructions" bölümünde (değişen dosya listesi, doğrulama komutları, kabul ölçütleri), 2 başarısız düzeltmeden sonra `/clear` + daha iyi istem, boşta kalmış (≈1 saatten uzun) oturumda yeni oturum veya "özetten sürdür" [D]. K1-2 hatası (boşta oturumda düşünme geçmişi kaybı) gibi durumlarda belirti unutkanlık/tekrar olabilir.
- O12 Teslim formatı (zorunlu): her teslimde (1) yapılan değişikliğin tek paragraf özeti, (2) değişen dosya listesi, (3) çalıştırılan komutlar ve çıktıları (kanıt), (4) hangi katman geçti/hangisi çalıştırılmadı, (5) bilinen sınırlamalar ve KÖR NOKTALAR, (6) geri alma yolu. "Yapıldı" ancak (3) ve (4) doluysa yazılır. Doğrulanmayan her şey "DOĞRULANMADI" etiketlidir.
- O13 Kaçak kaydı ve öğrenme: sonradan bulunan her hata için (kaçak) şu kayıt tutulur: hangi kapıdan geçti, hangi sınıf, hangi kapı eklenirse yakalanırdı. Aynı sınıf iki kez geçtiyse HighPer yeni kapıyı (test, hook, CLAUDE.md kuralı) ÖNERİR (onayla). Kaçak oranı = kaçak sayısı / teslim sayısı; küçük örneklemde güven aralığıyla raporlanır ("0 kaçak / 40 teslim" ≠ "sıfır risk"; üst sınır ≈ 3/40 ≈ %7,5 [I]).

## Profil istem şablonu (görev isteminin sonuna kopyalanır)
```
[HighPer: Sıfır Tolerans]
- Emin olmadığın her durumda DUR ve sor; varsayım yapma, "muhtemelen çalışır" yazma.
- Kodlamadan önce kabul ölçütlerini yaz, onayımı bekle.
- İzinli dosyalar: <liste>. Yasak: build/**, run/**, .gradle/**, *.jar, gradle/wrapper/**, canlı sunucu dizinleri.
- API/sürüm/mixin hedefi/mapping adlarını projedeki kaynaktan doğrula (gradle dependencies, jar); kaynağı yoksa "DOĞRULANMADI" yaz.
- Üç katman: (1) ./gradlew compileJava (+LSP tanıları) (2) ilgili test (3) ayrı alt-ajanla inceleme — yalnız diff + kabul ölçütleri,
  YALNIZ doğruluk/gereksinim boşlukları işaretlenir, gerisi "isteğe bağlı"; en çok 2 tur.
- Testleri geçirmek için testleri değiştirme/zayıflatma.
- Canlı sunucuya yazan hiçbir komut çalıştırma.
- Teslimi aşağıdaki 6 maddeyle yap; (3) ve (4) dolu değilse "yapıldı" yazma.
```

## O12 teslim formatı (zorunlu)
1. Yapılan değişikliğin tek paragraf özeti
2. Değişen dosya listesi (`git diff --stat`)
3. Çalıştırılan komutlar ve çıktıları (kanıt)
4. Hangi katman geçti / hangisi çalıştırılmadı ("DOĞRULANMADI")
5. Bilinen sınırlamalar ve KÖR NOKTALAR (`blind-spots.md`)
6. Geri alma yolu (commit/branch, `git restore`, yedek)

## Kapılar ve araçlar
| Kapı | Araç | Kurulum |
|---|---|---|
| O2 deterministik "bitti" | `scripts/verify_gate.py` (Stop hook) | diff + açık onay; 8 ardışık engel sonrası tur biter → teslim "DOĞRULANMADI" |
| O3 kapsam bekçisi | `scripts/scope_guard.py` (PreToolUse, çıkış kodu 2 ile engeller) | diff + açık onay; izin sistemini gevşetmez, yalnız ek kısıt |
| O4 diff denetimi | `scripts/diff_audit.py` | salt okunur |
| O9 sürüm/ayar sabitleme | `scripts/pin_check.py` (+ isteğe bağlı PreModelSwitch hook) | salt okunur; snapshot yalnız kullanıcının verdiği dosyaya |
| O10 kanarya | `scripts/canary.py` | `--yes` ile kullanıcı onayı |
| O13 kaçak kaydı | `/highper escape-log` → `scripts/sentinel.py escape` | yerel, yalnız sayaç/sınıf/sürüm etiketi |
