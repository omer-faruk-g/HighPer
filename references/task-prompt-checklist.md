# İyi görev istemi kontrol listesi (H15, H60, H61, G1)

> **Doküman/sayı değişkenliği uyarısı:** Claude Code sürümden sürüme değişir; buradaki kalıplar code.claude.com/docs best-practices sayfasıyla 2026-10-10'da karşılaştırıldı. Etiketler: [D] resmi doküman · [I] çıkarım, doğrulanmadı.

Araç: `python scripts/task_prompt_lint.py "<istem>"` veya `--file istem.txt` (salt okunur; eksik maddeleri işaretler).

| # | Madde | Neden | Örnek (Fabric/Java) | Etiket |
|---|---|---|---|---|
| 1 | Başarı ölçütü ("bitti" nasıl kontrol edilir) | En güçlü kaldıraç: Claude kendi işini doğrulayabilir | "`./gradlew compileJava` 0 ile çıkmalı ve `ExampleTest` geçmeli" | [I: ilke; best-practices ile uyumlu] |
| 2 | Doğrulama komutu (çalıştırılabilir) | Kanıt üretir (H59, G7) | "`./gradlew test --tests '*SpawnHandler*'`" | [D: best-practices "Provide verification"] |
| 3 | Kapsam (hangi dosya/senaryo) | Geniş tarama ve yanlış dosyayı önler | "yalnız `src/main/java/com/ex/event/`" | [D: best-practices "Scope the task"] |
| 4 | Dokunulmayacaklar | Kapsam sızıntısını önler | "`build/`, `run/`, `gradle/wrapper/` ve canlı sunucu dosyalarına dokunma" | [I] |
| 5 | Mevcut kalıba referans | Tutarlı kod, daha az uydurma | "`BlockBreakHandler.java` gibi yaz; yeni kütüphane ekleme" | [D: best-practices "Reference existing patterns"] |
| 6 | Kaynağa yönlendirme | Hafızadan değil gerçek kaynaktan | "git geçmişine bak", "`gradle dependencies` çıktısındaki Fabric API sürümünü kullan" | [D: best-practices "Point to sources"] |
| 7 | Belirti tarifi (hata işi) | Kök neden bulunur, susturulmaz | "Belirti: X; olası yer: Y; 'düzeldi' = Z" + tam stack trace | [D: best-practices "Describe the symptom"] |
| 8 | Kök neden talebi | Hatayı bastırma yerine düzeltme | "kök nedeni düzelt, hatayı susturma, build'in geçtiğini doğrula" | [D: H60] |
| 9 | Kabul ölçütü listesi (M/L iş) | Spec-first (G1) | 5–10 satır kabul ölçütü + kapsam dışı + riskler | [I] |
| 10 | Dönüş biçimi (alt-ajana devirde) | Ana bağlamı korur (H70) | "yalnız başarısız testler + hata mesajları" | [D: sub-agents] |

Keşif/belirsiz istemler bilinçli olarak serbest bırakılabilir [D: best-practices]; liste bir zorunluluk değil, eksik maddeleri görünür kılma aracıdır.
