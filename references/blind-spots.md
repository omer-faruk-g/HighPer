# Kapıların kör noktaları (Bölüm P)

> **Doküman/sayı değişkenliği uyarısı:** Claude Code sürümden sürüme değişir. Buradaki ayar adları, sayılar ve sürüm numaraları 2026-10-10'da code.claude.com/docs (221 sayfa, changelog v2.1.296'ya kadar) ve kurulu sürüm 2.1.295 ile karşılaştırıldı; doğrulama durumu `scope-honesty.md` sonundaki tabloda. Kullanmadan önce yeniden doğrula. Etiketler: [D] resmi doküman/Anthropic yayını · [G] oturumda gözlendi · [R] üçüncü taraf, doğrulanmadı · [I] çıkarım, doğrulanmadı.

## P. KAPILARIN KÖR NOKTALARI (açıkça kullanıcıya gösterilir)

HighPer her profil raporunda şu tabloyu verir; kapı yoksa "kapı yok" yazar:
- Derleme geçti → mantık/davranış hatası yakalanmaz.
- Testler geçti → testlerin kapsamadığı yol yakalanmaz; testlerin kendisi yanlış olabilir.
- Gözden geçirici (model) → uygulayıcıyla ortak kör nokta, yanlış alarm (aşırı mühendislik riski) olabilir.
- Scope guard / diff audit → mantıksal yanlış ama kapsam içi değişiklik yakalanmaz; hook'un görmediği yazma yolları.
- Kanarya → yalnız testin kapsadığı bozulma sınıfı.
- Stop hook sınırı → ardışık engel üst sınırı aşılırsa kapı açılır.
- Anthropic tarafı (model/altyapı) → kullanıcı tarafından düzeltilemez; tek koşu regresyon kanıtı değildir (v3 N4).
- İnsan onayı → kullanıcı da kaçırabilir; diff'i kanıtla birlikte kısa göstermek bunu azaltır.

## Uygulama notu (HighPer betikleri, 2026-10-10 testleriyle) [G]
- `verify_gate.py`: hook'un kendi zaman aşımı (settings.json `timeout`, SKILL.md örneğinde 900 sn) dolarsa Claude Code hook'u sonlandırır ve Stop doğrulanmadan geçer. Bu yüzden komutların toplam süresi `budget_sec` (varsayılan 840) ile hook zaman aşımının altında tutulur; zaman aşımında komutun tüm süreç ağacı öldürülür ve Stop engellenir. Bozuk `highper-verify.json` da Stop'u engeller (fail-closed).
- `scope_guard.py`: kendi iç hatasında yazmayı engeller (fail-closed). Okunamayan hook girdisinde (bozuk JSON) dokunmaz.
