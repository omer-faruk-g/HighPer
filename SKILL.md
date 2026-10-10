---
name: highper
description: Claude Code performansını (doğruluk, hız, güvenilirlik, tur verimi) ölçüp artırır. "yavaş", "takılıyor", "hata yapıyor", "performans", "kalite", "geç cevap veriyor", "uzun görev yarıda kalıyor" gibi isteklerde kullan. Önce ölçer, onayla önerir; yüzde vaadi vermez.
---

# HighPer

HighPer, Claude Code'un **performansını** artırır: daha doğru sonuç, daha az boşa tur, daha kısa bekleme, daha az hata/yeniden deneme, daha güvenilir uzun/gözetimsiz çalışma. Kardeş skill MinToken token'ı azaltır; ikisi bağımsız çalışır, birlikte de çalışır. HighPer bir görevi kendisi yapmaz; Claude Code'un nasıl çalıştığını ölçer ve ayar/alışkanlık önerir. Kullanıcının asıl kodunu (Fabric modları, sunucu betikleri) önerisiz değiştirmez.

Betikler: `scripts/` (Python stdlib, ağsız, `--help` ve `--dry-run`). Ayrıntılar: `references/`. Yollar bu skill dizinine göredir.

## İlkeler (her zaman)
1. **Bağımsız.** MinToken, Headroom, Graphify, Ponytail, claude-mem, everything-claude-code, SkillSpector kurulu olmasa da çalışır; `audit_perf.py` kurulu olanları SALT OKUNUR tespit eder. HighPer hiçbir aracı/skill'i/eklentiyi kurmaz veya kaldırmaz.
2. **Etiketler.** [D] resmi doküman/Anthropic yayını · [G] oturumda gözlendi · [R] üçüncü taraf, doğrulanmadı · [I] çıkarım, doğrulanmadı. [R]/[I] kesin bilgi gibi sunulmaz. Ayar anahtarı, env değişkeni, hook şeması, slash komutu, sürüm veya sayı yazmadan önce kurulu sürümde (`claude --version`, `claude --help`, `/doctor`) ve doküman sayfasında (WebFetch) yeniden doğrula; olmazsa "doğrulanamadı" yaz. Ezberden yazma.
3. **Yüzde/hız/"2 kat"/"sıfır kayıp" vaadi yok.** Sonuç görev, model, repo ve alışkanlığa bağlıdır. Kullanıcının kendi önce/sonra rakamı ölçülür (`references/axes-and-measurement.md`). Tek oturumluk fark kanıt değildir.
4. **Öncelik: DOĞRULUK > GÜVENİLİRLİK > HIZ > MALİYET.** Token/maliyeti artıran öneri bunu açıkça yazar. MinToken ile çelişen konuda iki yön yan yana gösterilir; HighPer kendisi seçmez (`references/mintoken-interplay.md`).
5. **Onay.** settings.json, hook, CLAUDE.md, .claudeignore, gradle.properties, izin kuralı, model/effort: önce diff, sonra açık onay. Geri dönüşü pahalı olanlar (önbellek bozan, oturum yeniden başlatan, yönetilen ayar, `disableAllHooks`, güvenlik/izin) ayrıca işaretlenir. Yönetilen/kuruluş politikasına dokunulmaz, yalnız raporlanır. Güvenliği gevşeten "performans" önerisi YOK (izin atlama, sandbox kapatma, `--dangerously-skip-permissions` yok). Hook'lar izin sistemini asla atlatmaz.
6. **Gizlilik.** Oturum kayıtları (`~/.claude/projects/**/*.jsonl`) yalnız yerelde okunur; rapora yalnız sayaç ve süre girer, ham mesaj metni girmez, hiçbir yere gönderilmez. HighPer `/heapdump` veya `/insights` çalıştırmaz (heap dump tüm konuşmayı ve kimlik bilgilerini içerir — paylaşılmaz; `/insights` token harcar → yalnız onaylı öneri).
7. **Önce ölç, sonra öner.** Bir kaldıraç ancak kullanıcının verisinde o sorun gösterildikten sonra önerilir; veri yoksa "olası, doğrulanmadı".
8. **Dil.** Kullanıcıya Türkçe, kısa ve düz; rapor tablo, açıklama kısa. Kod/komut/anahtar adları orijinal.
9. **Sınırlar.** Kendiliğinden commit/push yok. Canlı sunucuya yazan komut asla çalıştırılmaz/önerilmez; yalnız yerel/test ortamı.

## Çalışma akışı
1. Sorunu eksene bağla: P1 doğruluk · P2 gecikme · P3 tur verimi · P4 bağlam sağlığı · P5 güvenilirlik · P6 verim (`references/axes-and-measurement.md`).
2. Ölç: `python scripts/perf_baseline.py` (+ kullanıcının yapıştırdığı `/usage`, `/context`).
3. Şüpheli kaldıracı seç (H-numarası: `references/levers.md` H1–H48, `references/levers-v3.md` H49–H72).
4. Öneriyi kanıt + etiket + takas + geri alma + diff ile sun (MinToken çakışıyorsa iki sütun).
5. Açık onay al.
6. Uygula veya uygulat (kullanıcı uygular / onaylı Edit).
7. Tekrar ölç; "ölçülen değişim: X → Y". Gürültü uyarısı her raporda.

## Komutlar (`/highper <komut>`)
| Komut | Ne yapar | Araç / kaynak |
|---|---|---|
| `/highper` (argümansız) | genel denetim + kısa taban | `audit_perf.py`, `perf_baseline.py` |
| `/highper hunt` | verimsizlik avı: en çok 10 kanıtlı bulgu (doğruluk > güvenilirlik > gecikme > maliyet) | `hunt.py`, `references/inefficiency-hunt.md` |
| `/highper plan <görev>` | görevi XS/S/M/L sınıflandır, G adımlarını ve profili öner | `task_prompt_lint.py`, `references/quality-multipliers.md`, `references/profiles.md` |
| `/highper review` | G3 bağımsız gözden geçirici istemi (aşağıda) | `references/quality-multipliers.md` |
| `/highper measure` | kalite ölçümü (I1–I3), 2-kat sınaması, en küçük ölçülebilir fark | `quality_score.py`, `references/quality-measurement.md` |
| `/highper why-slow` | rejim değişikliği şüphelisi teşhisi (J-1), olay pencereleri (J-2) | `incident_check.py`, `pin_check.py`, `references/known-incidents.md` |
| `/highper route <görev>` | 5 eksenli model önerisi (satır sayısı kullanılmaz) | `route_model.py`, `references/model-router.md` |
| `/highper sentinel` | regresyon nöbetçisi: şablon, kayıt, karşılaştırma | `sentinel.py`, `references/sentinel-tasks.md` |
| `/highper zero` | Sıfır Tolerans profilini aç, kapıları listele | `references/zero-escape.md`, `references/blind-spots.md` |
| `/highper escape-log` | kaçak kaydı (O13) ve kaçak oranı (üç kuralı) | `sentinel.py escape/escapes`, `references/statistical-honesty.md` |
| `/highper report` | eksen → bulgu → öneri → takas → geri alma Markdown raporu | `report.py` (yalnız `--out` ile verilen dosyaya yazar) |
| `/highper gradle` | Gradle/Fabric ayarları, sürüm matrisi taslağı, log hata blokları | `gradle_perf.py`, `references/fabric-gradle.md` |
| `/highper lint` | CLAUDE.md/MEMORY.md lint; görev istemi lint | `claude_md_lint.py`, `task_prompt_lint.py` |

## Görev sınıfı ve profil (G11, H)
- XS (typo/rename): ek katman yok, plan modu yok (H62). S (tek dosya): Hızlı = G2+G7. M (çok dosya): Dengeli = G1+G2+G6+G7. L (mimari/riskli): Maksimum = G1–G7, gerekirse G8.
- Profiller otomatik açılmaz; yalnız görev/oturum için; istem bloğu `references/profiles.md`'den kopyalanır. Kalıcılık ancak diff + onayla.
- Kaliteyi artıran düzen token ve süre artırır (Bölüm C): bunu her öneride söyle.

## Gözden geçirici istemi (G3/G4, DZ-J1 ile)
Uygulayıcıdan AYRI alt-ajan, temiz bağlam, yalnız okuma araçları (`tools: Read, Grep, Glob` + gerekirse test komutu), en çok 2 tur:
> Bu diff'i yalnız şu kabul ölçütlerine göre incele: <ölçütler>. YALNIZ doğruluğu veya belirtilmiş gereksinimleri etkileyen boşlukları işaretle; gerisini "isteğe bağlı" başlığı altında ayrı listele. Kabul ölçütleri ve gerçekçi girdiler kapsamında bunu bozabilecek durumları yaz; mümkünse küçük bir testle çalıştır.
Yalnız "doğruluk/gereksinim" bulguları uygulayıcıya döner; her bulguyu kovalamak aşırı mühendisliğe yol açar [D: best-practices].

## Model ve effort (H1–H7, L)
- Modeli ve effort'u GÖREV BAŞINDA seç; ortada `/model` ve çoğu modelde effort değişimi önbelleği bozar (Opus 5.5 ve Fable 5.1'de effort değişimi önbelleği korur) [D].
- Önce "aynı model, doğru effort": Opus 5.5 `medium`, Opus 5 `high`'a eşit/üstün [D]. Tek tur için `ultrathink`.
- Düşünmeyi "kapat" önerisi YOK: Opus/Sonnet/Haiku 5.5 ve Fable'da kapatılamaz [D].
- "Sonnet yeter" hükmü kullanıcının kendi ölçümü olmadan verilmez (`sentinel.py compare --by model`, ≥3 tekrar).
- Alt-ajanların çözülen modelini raporla (`audit_perf.py` bölüm 5); "sessiz Haiku" iddiası [R], kanıtsız doğrulanmaz.

## Bağlam (H8–H14, H49–H56) — MinToken ile aynı yön
Görev değişince `/clear`; aynı görevde `/compact <odak>`; yanlış yolda `/rewind`; 2 başarısız düzeltmeden sonra `/clear` + daha iyi başlangıç istemi [D]. Kalıcı kural CLAUDE.md'ye (sohbette söylenen sınır sıkıştırmada kaybolabilir) + "Compact Instructions" bölümü [D]. Tek seferlik yan soru `/btw` [D].

## Hook'lar (hepsi opsiyonel; diff + açık onayla kurulur)
Kurmadan önce şemayı kurulu sürümün hooks sayfasından yeniden doğrula. Örnek `~/.claude/settings.json` (veya proje `.claude/settings.json`) parçaları:
```json
{"hooks": {
  "PreToolUse": [{"matcher": "Edit|Write|MultiEdit|NotebookEdit|Bash|PowerShell",
                  "hooks": [{"type": "command", "command": "python \"<HIGHPER>/scripts/scope_guard.py\"", "timeout": 10}]}],
  "Stop": [{"hooks": [{"type": "command", "command": "python \"<HIGHPER>/scripts/verify_gate.py\"", "timeout": 900}]}]
}}
```
- `scope_guard.py` (O3): yapılandırma `.claude/highper-scope.json`; kapsam dışı yazmayı çıkış kodu 2 ile ENGELLER; izin vermez, gevşetmez. Kör noktaları `references/blind-spots.md`.
- `verify_gate.py` (O2): yapılandırma `.claude/highper-verify.json`; doğrulama komutları geçene kadar Stop'u `decision:"block"` ile engeller; 8 ardışık engelden sonra Claude Code turu bitirir (`CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`) → teslim "DOĞRULANMADI". Hızlı komut kullan (H18).
- PreModelSwitch (O9, v2.1.251+): model değişimini onaya bağlar; otomatik yedek model geçişinde ÇALIŞMAZ (yalnız PostModelSwitch) [D]. Yalnız öneri.

## Sıfır Tolerans profili (`/highper zero`, O)
Asla otomatik açılmaz; takası (token, süre, onay) ve Hızlı/Dengeli alternatifi söylenir. Açıkken: fail-closed (emin değilsen DUR ve sor), deterministik kapı (verify_gate), kapsam bekçisi (scope_guard), teslim öncesi `diff_audit.py`, üç katmanlı doğrulama (statik / dinamik / bağımsız inceleme), kritik ad/sürümler projedeki kaynaktan (O8), `pin_check.py` ile sürüm/model/effort sabitleme (değişirse profil bozulmuş sayılır), görev başında kanarya (`canary.py`), kaçak kaydı (O13).
Teslim formatı (O12, zorunlu): (1) tek paragraf özet (2) değişen dosyalar (3) çalıştırılan komutlar + çıktıları (4) hangi katman geçti / hangisi çalıştırılmadı (5) bilinen sınırlamalar ve KÖR NOKTALAR (6) geri alma yolu. (3) ve (4) dolu değilse "yapıldı" yazılmaz; doğrulanmayan her şey "DOĞRULANMADI".

## İstatistik dili (Q)
"N tesliminde 0 kaçak görüldü; %95 güvenle üst sınır ≈ 3/N" — asla "kaçak yok", "sıfır risk", "garantili". 10⁻⁷ iddiası ≈30.000.000 deneme ister. Küçük örneklem: "işaret, kanıt değil". Metrikler ayrı raporlanır (ilk deneme, kaçak, düzeltme turu, müdahale). "Kanıtlandı" değil, "bu doğrulamalardan geçti".

## Rejim değişikliği (K, J-1)
Kalite/hız aniden düştüyse önce kullanıcı dışı nedenleri kontrol et: sürüm, model/alias, effort kaynağı, eklenti/mod/çıktı stili, `claude --safe-mode`, `/usage` önbellek ıskaları, uzun/boşta oturum, aynı istemde rastgele geç/kal. Anthropic'in belgelediği olaylar `references/known-incidents.md`. Geri bildirim `/feedback` (HighPer hiçbir şey göndermez).

## Fabric / Gradle (D)
Proje dosyalarından otomatik tanınır (`build.gradle`, `gradle.properties`, `fabric.mod.json`). Doğrulama merdiveni: `./gradlew compileJava` → ilgili test → tam build; `runClient`/`runServer` arka planda + çıkış koşulu. Sürüm matrisi CLAUDE.md'ye tek satır (onayla). `run/logs/latest.log` doğrudan okunmaz, filtrelenir. Loom/Gradle ayar önerileri [I]: sürümüne göre belgelerde doğrula.

## Referanslar
`axes-and-measurement.md` (A, E) · `levers.md` (H1–H48) · `levers-v3.md` (J0, H49–H72) · `mintoken-interplay.md` (C) · `fabric-gradle.md` (D) · `task-prompt-checklist.md` (H15/H61) · `inefficiency-hunt.md` (F) · `quality-multipliers.md` (G) · `profiles.md` (H) · `quality-measurement.md` (I) · `known-incidents.md` (K) · `model-router.md` (L) · `sentinel-tasks.md` (N) · `zero-escape.md` (O) · `blind-spots.md` (P) · `statistical-honesty.md` (Q) · `scope-honesty.md` (kapsam dürüstlüğü + doğrulama tablosu).
