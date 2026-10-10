# Kalite çarpanları G1–G11 ve görev sınıfları XS/S/M/L (Bölüm G)

> **Doküman/sayı değişkenliği uyarısı:** Claude Code sürümden sürüme değişir. Buradaki ayar adları, sayılar ve sürüm numaraları 2026-10-10'da code.claude.com/docs (221 sayfa, changelog v2.1.296'ya kadar) ve kurulu sürüm 2.1.295 ile karşılaştırıldı; doğrulama durumu `scope-honesty.md` sonundaki tabloda. Kullanmadan önce yeniden doğrula. Etiketler: [D] resmi doküman/Anthropic yayını · [G] oturumda gözlendi · [R] üçüncü taraf, doğrulanmadı · [I] çıkarım, doğrulanmadı.

## Bu dosyaya uygulanan düzeltmeler (v3 J0 — çelişkide geçerli olan)
- DZ-J1: G3/G4 gözden geçirici YALNIZ doğruluğu veya belirtilmiş gereksinimleri etkileyen boşlukları işaretler; gerisi "isteğe bağlı". Bulgular iki sınıf: doğruluk/gereksinim → uygulayıcıya döner; isteğe bağlı → döndürülmez.
- DZ-J2: H8 (bağlam çürümesi), H11 (2 düzeltmeden sonra temiz başla) ve G10 (iki kez yanlış → CLAUDE.md) artık [D].
- DZ-J3: varsayılan effort `high`; istisnalar Opus 5.5/Sonnet 5.5/Haiku 5.5 `medium`, Opus 4.7 `xhigh` [D: model-config].
- DZ-J4: "alt-ajanlar sessizce Haiku'ya devrediliyor" iddiası [R]; çözülen alt-ajan modeli raporlanır, kanıtsız doğrulanmaz.
- DZ-J5: Stop hook ardışık engel üst sınırı 8 (`CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`, 0 = kapalı) [D: hooks, 2026-10-10 doğrulandı].
- DZ-J6: `.gitignore` aramalardan zaten dışlanır; büyük derleme dizinlerini `.gitignore`'a koymak dokümanın önerisidir [D: troubleshooting].

## G. KALİTE ÇARPANLARI (tek geçişli yürütmeye karşı çok geçişli yürütme)

Kalitenin en büyük kaldıraçları model veya ayar değil, yürütme DÜZENİDİR [I: bu ortamda ölçülmedi; Bölüm I ile kullanıcı kendi verisinde ölçer]. Bu düzenlerin hepsi onaylıdır ve token/gecikme ARTIRIR (Bölüm C); HighPer bunu açıkça söyler ve "yüksek kalite profili"ni görev bazlı, isteğe bağlı sunar.

- G1 Önce belirt (spec-first): kodlamadan önce Claude'dan 5–10 satırlık kabul ölçütü, kapsam dışı liste ve riskleri yazdırmak; kullanıcı onayı sonrası uygula. Belirsiz görev, boşa tur ve yanlış yönün baş nedenidir [I]. task_prompt_lint.py eksik ölçütleri işaretler (H15). Plan modu ile birleştir (H16).
- G2 Önce test/derleme (test-first, doğrulanabilir hedef): mümkünse başarısız testi/derleme hatasını önce yazdır, sonra geçir; `/goal` koşulu olarak ver (H17). Fabric modda: önce `compileJava` hatasını yeniden üret, sonra düzelt [I].
- G3 Bağımsız gözden geçirici (ikinci geçiş): uygulamayı yapan ajandan AYRI bir alt-ajan (temiz bağlam, yalnız diff + gereksinim) diff'i inceler; "bu görevin kabul ölçütlerini karşılıyor mu, hangi hata/regresyon/kenar durum var" diye sorulur. Uygulayıcı kendi çıktısını aynı bağlamda "kontrol ettiğinde" aynı kör noktayı paylaşır [I]. Gözden geçirici SALT OKUNUR araçlarla (`tools:` kısıtlı) çalışır. Bulgular uygulayıcıya geri verilir; en çok 2 tur (sonsuz döngü yok). Takas: bir ek alt-ajan maliyeti; kritik/riskli değişiklikte değer, typo'da değil.
- G4 Karşı-örnek avı (adversarial pass): gözden geçirici ayrıca "bunu bozacak 5 girdi/durum" üretir ve mümkünse çalıştırır (birim test, küçük betik). Fabric/Minecraft için: boş/null eşya, çoklu oyuncu eşzamanlılığı, sunucu/istemci tarafı ayrımı, chunk yükleme sınırı, tick süresi [I].
- G5 Gerçeği kaynaktan doğrula: API/sürüm bilgisini hafızadan yazma; Fabric API/Minecraft sınıf adı, mixin hedefi, mapping adı için projedeki gerçek kaynağa/bağımlılık jar'ına/`gradle dependencies` çıktısına bak; kütüphane dokümanı gerekiyorsa WebFetch ile oku. "Emin değilim" demeyi ve doğrulama adımı eklemeyi ödüllendir; uydurma API'yi derleme zaten yakalar → derle (G2) [I].
- G6 Parçala ve kanıtla: büyük işi bağımsız doğrulanabilir adımlara böl; her adım sonunda doğrulama komutu çalışsın; yalnız geçen adım sonraki adıma geçer. Çok dosyalı işte "yarım değişiklik" riskini düşürür [I]. Worktree/git ile her adımda geri dönüş noktası (kullanıcı onayıyla commit; HighPer kendiliğinden commit/push yapmaz).
- G7 Kanıtla bitir (done-definition): "bitti" ancak şu kanıtlarla: çalıştırılan komut ve çıktısı (derleme/test), değişen dosya listesi, bilinen sınırlamalar. Doğrulama çalıştırılmadıysa AÇIKÇA "çalıştırılmadı" yazılır; kanıt olmadan "çalışıyor" denmez. Bunu CLAUDE.md'ye tek satırlık kural olarak önerir (onayla) ve Stop hook ile destekler (H18).
- G8 Çoklu aday ve seçim (yalnız zor/ belirsiz tasarım): 2–3 bağımsız çözüm taslağı (ayrı alt-ajanlar), ölçütlere göre karşılaştırma, seçim. En pahalı çarpan; yalnız mimari kararlarda, kullanıcı onayıyla [I].
- G9 Bağlam bütçesi: görev başına temiz bağlam (`/clear`), keşif alt-ajanda, kritik kurallar CLAUDE.md'de, sıkıştırma sonrası "kritik talimat envanteri" yeniden doğrulaması (H9). Uzun oturumda doğruluk düşüşü şüphesinde yeni oturum + özet.
- G10 Hataları kalıcı öğrenmeye çevir: kullanıcı aynı düzeltmeyi 2. kez yapıyorsa HighPer bunu CLAUDE.md/skill/hook adayı olarak önerir ("5 kez 'Mojmap kullan' dediniz → CLAUDE.md'ye tek satır", H12, D4). Önerir, yazmaz; onay şart. Otomatik bellek yazımını HighPer kendisi yapmaz.
- G11 Düşük riskli işte hafif mod: kaliteyi artıran her katman her işe uygulanmaz; HighPer görevi sınıflandırır: XS (typo/rename: ek katman yok), S (tek dosya: G2+G7), M (çok dosya: G1+G2+G6+G7), L (mimari/riskli: G1–G7, gerekirse G8). Aşırı süreç kalite getirmez, gecikme ve token getirir; sınıfı kullanıcıya göster, kullanıcı değiştirebilir.
