# Fabric / Gradle / Minecraft performansı (Bölüm D)

> **Doküman/sayı değişkenliği uyarısı:** Claude Code sürümden sürüme değişir. Buradaki ayar adları, sayılar ve sürüm numaraları 2026-10-10'da code.claude.com/docs (221 sayfa, changelog v2.1.296'ya kadar) ve kurulu sürüm 2.1.295 ile karşılaştırıldı; doğrulama durumu `scope-honesty.md` sonundaki tabloda. Kullanmadan önce yeniden doğrula. Etiketler: [D] resmi doküman/Anthropic yayını · [G] oturumda gözlendi · [R] üçüncü taraf, doğrulanmadı · [I] çıkarım, doğrulanmadı.

## BÖLÜM D — KULLANICIYA ÖZEL: FABRIC/GRADLE/MINECRAFT PERFORMANSI

Kullanıcı Fabric/Java mod geliştiricisi ve Minecraft sunucu operatörü (Skript, sunucu yönetimi). Skill, bu bağlamı proje dosyalarından (build.gradle, gradle.properties, fabric.mod.json, src/, run/) otomatik tanır; tanımazsa genel mod. Aşağıdakilerin hiçbiri otomatik uygulanmaz.

- D1 Gradle gecikmesi (P2): Claude'un en çok beklediği iş genellikle derlemedir [I]. gradle_perf.py `gradle.properties` ve `~/.gradle/gradle.properties` dosyalarını SALT OKUR; `org.gradle.daemon`, `org.gradle.parallel`, `org.gradle.caching`, `org.gradle.jvmargs` (bellek), `org.gradle.configuration-cache` değerlerini raporlar ve eksik/uygunsuz olanı önerir. Fabric Loom ile yapılandırma önbelleği uyumu sürüme bağlıdır → önermeden önce kullanıcının Loom/Gradle sürümü için Loom/Gradle belgelerinde doğrula [I].
- D2 Hızlı geri bildirim komutu (P1, P3): tam `./gradlew build` yerine önce `./gradlew compileJava` (veya projeye uygun hızlı görev), sonra gerekirse test/build; CLAUDE.md'ye "doğrulama merdiveni" olarak yazılır (kullanıcı onayıyla): 1) `compileJava` 2) ilgili test 3) tam build. Mod için `runClient`/`runServer` etkileşimli ve uzundur; arka plana at, kesin çıkış koşulu ver (H26).
- D3 Çıktı filtresi: Gradle/Fabric log gürültüsü hem bağlamı hem doğruluğu bozar; MinToken kuruluysa `filter_log.py` kullanılır, değilse `gradle_perf.py --tail-errors` yalnız hata/uyarı bloklarını özetler [I].
- D4 Mapping/sürüm hataları (P1): Minecraft/Fabric API/Loom/Yarn(Mojmap) sürümü uyuşmazlığı en yaygın boşa tur kaynaklarındandır [I]. CLAUDE.md'ye tek satırlık "sürüm matrisi" (Minecraft, Fabric Loader, Fabric API, Loom, mappings, Java) yazmak modelin eski API'leri hatırlayıp hata üretmesini azaltır [I]. Sürüm bilgisini `gradle.properties`'ten okuyup CLAUDE.md taslağına koyar; yazmadan önce onay.
- D5 Sunucu/Skript işleri: sunucu logları devasa; `run/logs/latest.log` doğrudan okunmaz, filtrelenir; sunucu betiği değişikliklerinde yedek ve `--dry-run`/test sunucusu iste. Canlı sunucuya (CPVPTurk) yazan komutları HighPer hiçbir zaman çalıştırmaz/önermez; yalnız test ortamı.
- D6 Büyük çıktı yasakları (MinToken B2/B3 ile aynı): `build/`, `.gradle/`, `run/`, `*.jar`, dekompilelenmiş kaynaklar `permissions.deny` `Read(...)` ile okunmaz önerisi (kullanıcı onayıyla, diff'le).

Araç: `python scripts/gradle_perf.py [proje_dizini]` (salt okunur), `--tail-errors <log>` hata/uyarı blokları.
