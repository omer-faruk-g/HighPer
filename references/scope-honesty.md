# Kapsam dürüstlüğü ve doğrulama durumu

> **Doküman/sayı değişkenliği uyarısı:** bu tablo 2026-10-10 tarihlidir. Claude Code sürümden sürüme değişir; kullanmadan önce yeniden doğrula.

## Bu kurulumda ne doğrulandı (2026-10-10)
- Kaynak: code.claude.com/docs/llms.txt dizinindeki **221 İngilizce sayfanın tamamı** (ham markdown, changelog v2.1.296'ya kadar), kurulu Claude Code **2.1.295** (`claude --version`), Anthropic yazıları "April 23 postmortem", "A postmortem of three recent issues", "Effective context engineering for AI agents" (ham HTML).
- Yöntem: tam ad eşleşmesi (anahtar/env/slash komutu) ve sayı/sürüm için hedefli arama. Bir adın sayfada geçmesi, o sayfadaki her ayrıntının (varsayılan, davranış) doğru aktarıldığını kanıtlamaz; yalnız adın ve sayının belgelerde var olduğunu gösterir.
- Hook şemaları ayrıca okundu: PreToolUse çıkış kodu 2 → araç çağrısı engellenir; Stop `decision:"block"` + `reason`, girdi `stop_hook_active`, ardışık 8 devam sınırı (`CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`, 0 = kapalı); PreModelSwitch v2.1.251+, çıkış kodu 2 geçişi engeller, otomatik yedek modelde çalışmaz (yalnız PostModelSwitch) [D: hooks].
- Postmortem rakamları kaynaktan doğrulandı: 4 Mart high→medium, 7 Nisan geri alma (Opus 4.7 xhigh, diğerleri high), 26 Mart düşünme temizleme hatası (`clear_thinking_20251015`, `keep:1`), 10 Nisan v2.1.101, 16 Nisan ≤25/≤100 kelime istemi ve %3 düşüş, 20 Nisan v2.1.116, kullanım limitlerinin sıfırlanması, Opus 4.7 Code Review geri testi; Eylül 2025: 5 Ağustos başlangıç, 31 Ağustos en kötü saatte Sonnet 4 isteklerinin %16'sı, Claude Code kullanıcılarının ≈%30'u, 4 Eylül düzeltme, Vertex'te 16 Eylül'e kadar, 25 Ağustos–2 Eylül çıktı bozulması (Tayca/Çince karakter), Haiku 3.5 top-k, `/bug` [D]. "18 Eylül" yayılım tarihi kaynakta bulunamadı → doğrulanamadı.

## Ayar anahtarları ve env değişkenleri (84/84 dokümanda bulundu)

| Ad | Bulunduğu sayfa |
|---|---|
| `ANTHROPIC_DEFAULT_` | env-vars, agent-view |
| `ANTHROPIC_DEFAULT_HAIKU_MODEL` | env-vars, agent-view |
| `API_FORCE_IDLE_TIMEOUT` | env-vars, changelog |
| `API_TIMEOUT_MS` | env-vars, agent-sdk__python |
| `BASH_DEFAULT_TIMEOUT_MS` | env-vars, cloud-environments |
| `BASH_MAX_OUTPUT_LENGTH` | settings-reference, env-vars |
| `CLAUDE_BYTE_STREAM_IDLE_TIMEOUT_MS` | env-vars, network-config |
| `CLAUDE_CODE_API_KEY_HELPER_TTL_MS` | settings-reference, env-vars |
| `CLAUDE_CODE_AUTO_COMPACT_WINDOW` | settings-reference, env-vars |
| `CLAUDE_CODE_DISABLE_ATTACHMENTS` | settings-reference, env-vars |
| `CLAUDE_CODE_DISABLE_BEDROCK_CONTENT_TYPE_DEFAULT` | env-vars, amazon-bedrock |
| `CLAUDE_CODE_DISABLE_BUNDLED_SKILLS` | settings-reference, env-vars |
| `CLAUDE_CODE_DISABLE_CLAUDE_MDS` | env-vars, agent-sdk__modifying-system-prompts |
| `CLAUDE_CODE_DISABLE_FAST_MODE` | settings-reference, env-vars |
| `CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS` | settings-reference, env-vars |
| `CLAUDE_CODE_ENABLE_TODO_TOOLS` | env-vars, agent-sdk__todo-tracking |
| `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` | env-vars, agent-teams |
| `CLAUDE_CODE_GOAL_CHECKIN_MINUTES` | env-vars, changelog |
| `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` | env-vars, agent-sdk__subagents |
| `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` | env-vars, agent-sdk__subagents |
| `CLAUDE_CODE_MCP_STARTUP_WAIT_MS` | env-vars, agent-sdk__mcp |
| `CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT` | env-vars, changelog |
| `CLAUDE_CODE_RESUME_INTERRUPTED_TURN_MAX_AGE_MS` | env-vars, changelog |
| `CLAUDE_CODE_RETRY_WATCHDOG_MAX_WAIT_MS` | env-vars, changelog |
| `CLAUDE_CODE_SIMPLE_SYSTEM_PROMPT` | env-vars, agent-sdk__modifying-system-prompts |
| `CLAUDE_CODE_STOP_HOOK_BLOCK_CAP` | env-vars, hooks |
| `CLAUDE_CODE_SUBAGENT_MODEL` | env-vars, agent-teams |
| `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` | env-vars, agent-teams |
| `CLAUDE_CODE_WORKFLOW_MAX_CONCURRENT_AGENTS` | env-vars, changelog |
| `CLAUDE_ENABLE_BYTE_WATCHDOG` | env-vars, network-config |
| `CLAUDE_ENABLE_STREAM_WATCHDOG` | env-vars, agent-sdk__python |
| `CLAUDE_STREAM_FIRST_BYTE_TIMEOUT_MS` | env-vars, errors |
| `CLAUDE_STREAM_IDLE_TIMEOUT_MS` | env-vars, agent-sdk__python |
| `DISABLE_PROMPT_CACHING` | env-vars, amazon-bedrock |
| `ENABLE_CLAUDEAI_MCP_SERVERS` | settings-reference, env-vars |
| `ENABLE_PROMPT_CACHING_1H` | settings-reference, env-vars |
| `ENABLE_TOOL_SEARCH` | env-vars, agent-sdk__tool-search |
| `FORCE_PROMPT_CACHING_5M` | settings-reference, env-vars |
| `MAX_MCP_OUTPUT_TOKENS` | env-vars, agent-sdk__mcp |
| `MAX_THINKING_TOKENS` | settings-reference, env-vars |
| `MCP_TIMEOUT` | env-vars, hooks |
| `MCP_TOOL_TIMEOUT` | env-vars, agent-sdk__mcp |
| `OTEL_LOG_RAW_API_BODIES` | settings-reference, env-vars |
| `USE_BUILTIN_RIPGREP` | settings-reference, env-vars |
| `advisorModel` | settings-reference, env-vars |
| `allowedTools` | settings-reference, agent-sdk__agent-loop |
| `alwaysLoad` | env-vars, agent-sdk__custom-tools |
| `alwaysThinkingEnabled` | settings-reference, changelog |
| `autoCompactWindow` | settings-reference, env-vars |
| `autoContinueAtUsageLimit` | settings-reference, hooks |
| `autoMode.classifyAllShell` | settings-reference, auto-mode-config |
| `bashOutputMaxChars` | settings-reference, env-vars |
| `dangerouslyDisableSandbox` | settings-reference, agent-sdk__python |
| `disableAllHooks` | settings-reference, hooks |
| `dontAsk` | settings-reference, hooks |
| `effortLevel` | settings-reference, env-vars |
| `excludeDynamicSections` | agent-sdk__modifying-system-prompts, agent-sdk__typescript |
| `fallbackModel` | settings-reference, env-vars |
| `fastMode` | settings-reference, agent-sdk__typescript |
| `fastModePerSessionOptIn` | settings-reference, fast-mode |
| `getContextUsage` | agent-sdk__typescript |
| `includeGitInstructions` | settings-reference, env-vars |
| `maxBudgetUsd` | agent-sdk__agent-loop, agent-sdk__configuration |
| `maxEffortLevel` | settings-reference, env-vars |
| `maxTurns` | agent-sdk__agent-loop, agent-sdk__configuration |
| `mcpServers` | settings-reference, agent-sdk__claude-code-features |
| `modelSettings` | settings-reference, env-vars |
| `outputStyle` | settings-reference, agent-sdk__configuration |
| `permissionMode` | settings-reference, agent-sdk__agent-loop |
| `permissions.defaultMode` | settings-reference, hooks |
| `permissions.disableAutoMode` | settings-reference, admin-setup |
| `promptCacheTtl` | settings-reference, env-vars |
| `replace` | settings-reference, env-vars |
| `sandbox.allowUnsandboxedCommands` | settings-reference, changelog |
| `skipWebFetchPreflight` | settings-reference, claude-apps-gateway-deploy |
| `strictMcpConfig` | agent-sdk__claude-code-features, agent-sdk__typescript |
| `subagentPromptCacheTtl` | settings-reference, env-vars |
| `syncClaudeAiPlugins` | settings-reference, admin-setup |
| `syncClaudeAiSkills` | settings-reference, admin-setup |
| `ultracode` | settings-reference, commands |
| `useAutoModeDuringPlan` | settings-reference, managed-settings |
| `workflowKeywordTriggerEnabled` | settings-reference |
| `workflowSizeGuideline` | settings-reference, changelog |
| `worktree.sparsePaths` | settings-reference, changelog |

## Slash komutları (26/26 dokümanda bulundu)

| Komut | Bulunduğu sayfa |
|---|---|
| `/agents` | commands, agents |
| `/autocompact` | commands, changelog |
| `/batch` | commands, agents |
| `/btw` | commands, interactive-mode |
| `/bug` | commands, changelog |
| `/clear` | commands, interactive-mode |
| `/code-review` | commands, agent-sdk__skills |
| `/compact` | commands, advisor |
| `/config` | commands, interactive-mode |
| `/context` | commands, agent-sdk__python |
| `/doctor` | commands, best-practices |
| `/effort` | commands, interactive-mode |
| `/fast` | commands, interactive-mode |
| `/feedback` | commands, changelog |
| `/fork` | commands, agent-view |
| `/goal` | commands, best-practices |
| `/heapdump` | commands, changelog |
| `/insights` | commands, changelog |
| `/model` | commands, interactive-mode |
| `/name` | commands, agent-sdk__typescript |
| `/rewind` | commands, agent-teams |
| `/skill-doctor` | commands, changelog |
| `/status` | commands, interactive-mode |
| `/subtask` | commands, agent-view |
| `/usage` | commands, advisor |
| `/verify` | commands, best-practices |

## Sayılar ve sürümler

| İddia | Bulunduğu sayfa |
|---|---|
| 967K otomatik sıkıştırma | changelog, claude-apps-gateway-config |
| MEMORY.md 200 satır / 25 KB | changelog, claude-directory |
| CLAUDE.md 4 MiB | changelog, memory |
| sıkıştırmada 5.000 token dosya sınırı | agent-sdk__mcp, common-workflows |
| alt-ajan açıklama 15.000 token | errors, sub-agents |
| skills: ilk 32 ad | changelog, sub-agents |
| eşzamanlı alt-ajan 20 | agent-sdk__subagents, env-vars |
| iç içe derinlik 3 | agent-sdk__subagents, env-vars |
| 200 alt-ajan tavanı kaldırıldı v2.1.224 | agent-sdk__typescript, amazon-bedrock |
| workflow 16 eşzamanlı ajan | env-vars |
| workflow 1.000 ajan | workflows |
| parallel()/pipeline() 4.096 öğe | changelog, plugins__mods__reference |
| agent teams ≈7× | changelog, costs |
| istemci 10 yeniden deneme | changelog, chrome |
| watchdog 5 dk olaysız | agent-sdk__python, agent-sdk__typescript |
| MCP_TOOL_TIMEOUT ~28 saat | env-vars, mcp |
| MCP boşta 5 dk / stdio 30 dk | changelog, env-vars |
| MAX_MCP_OUTPUT_TOKENS 25.000 / 10.000 uyarı | agent-sdk__mcp, common-workflows |
| MCP metin >50.000 karakter dosyaya | agent-sdk__mcp, env-vars |
| hata metni 11.000 → 5.000+5.000 | mcp |
| bashOutputMaxChars tavanı 128.000 | tools-reference, whats-new__2026-w36 |
| BASH_MAX_OUTPUT_LENGTH 150.000 | env-vars, tools-reference |
| Bash komutu >10.000 karakter sorar | changelog, context-window |
| auto mod 3 ardışık / 20 toplam engel | changelog |
| heap 2,5 GB uyarısı | troubleshooting |
| alt-ajan 6.100 token / ≈420 özet | context-window |
| /code-review $15–25 | code-review, costs |
| agent hook ≤50 araç turu | hooks |
| hook çıktısı 10.000 karakter / 2.000 önizleme | agent-sdk__tool-search, changelog |
| 75 dk sonra /clear | changelog, whats-new__2026-w13 |
| özetten sürdür ≥100.000 token | llm-gateway-connect, sessions |
| prewarm 230–260 MB | agent-sdk__typescript, amazon-bedrock |
| MCP_TIMEOUT 30 sn | agent-sdk__mcp, changelog |
| alwaysLoad 5 sn tavan | agent-sdk__custom-tools, agent-sdk__mcp |
| WebFetch 300 sn | changelog, claude-apps-gateway-on-gcp |
| API_TIMEOUT_MS 600.000 | agent-sdk__python, agent-sdk__typescript |
| Stop hook 8 ardışık engel | hooks |
| PreModelSwitch v2.1.251 | hooks |
| auto mod sunucu tarafı v2.1.278 | changelog, permission-modes |
| `/name` model turu v2.1.274 | agent-sdk__mcp, agent-sdk__skills |
| mods v2.1.287 | advisor, agent-sdk__typescript |
| --bare v2.1.286 | agent-sdk__typescript, changelog |
| fast mode Opus 5.5 $8/$40 | fast-mode |
| NONESSENTIAL_TRAFFIC ↔ gateway model discovery | changelog |

## Çelişkiler ve düzeltmeler
- **Fast mode fiyatı (H5):** spec "fiyat sayfaları çelişkili" diyor; 2026-10-10 fast-mode sayfası: Opus 5.5 için $8/$40, Opus 5 ve Opus 4.8 için $10/$50 per MTok. Farklı modeller → çelişki değil. HighPer yine fiyat yazmaz, `/fast` ekranına yönlendirir.
- **`CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` ↔ ağ geçidi model keşfi:** sayfalar arası çelişki olarak işaretli kalır (connect sayfası durdurmadığını, protocol sayfası durdurduğunu söylüyor — MinToken v6 C164); kurulu sürümde test edilmedi.
- **Varsayılan effort (DZ-J3):** `high`; istisnalar Opus/Sonnet/Haiku 5.5 `medium`, Opus 4.7 `xhigh` [D: model-config].
- **Stop ardışık engel sınırı (DZ-J5, O2):** spec "sayfadan doğrula" diyordu → 8, `CLAUDE_CODE_STOP_HOOK_BLOCK_CAP` [D: hooks, env-vars].

## Doğrulanmayanlar ([R]/[I] — kesin bilgi gibi sunulmaz)
- [R] "Alt-ajanlar sessizce Haiku'ya devrediliyor" (DZ-J4).
- [I] Gradle/Loom ayar etkileri, Loom–configuration-cache uyumu, doğrulama merdiveninin etkisi (D1, D2), sürüm matrisinin hata azaltması (D4), mapping uyuşmazlığının en yaygın boşa tur kaynağı olduğu.
- [I] Bölüm G düzenlerinin (spec-first, test-first, bağımsız gözden geçirici, çoklu aday) etki büyüklüğü — bu kullanıcının görevlerinde ÖLÇÜLMEDİ; Bölüm I ile ölçülür.
- [I] Model yönlendirici puanlaması ve eşikleri (Bölüm L); satır sayısı için resmi eşik yoktur.
- [I] Üç kuralı ve en küçük ölçülebilir fark hesapları (standart istatistik, yaklaşık).
- [I] "Aynı model aynı kör noktayı paylaşır", "testi zayıflatma en klasik kaçak", başsız sunucu açılış testi önerisi.
- [G] Oturum kaydı biçimi (`type`, `message`, `timestamp`, `isCompactSummary`, `isApiErrorMessage`, `tool_result.is_error`, `[Request interrupted`) bu makinede gözlendi; sürümle değişebilir → `perf_baseline.py` önce şemayı denetler, tanımazsa durur.
- `scope_guard.py` Bash/PowerShell yazma hedeflerini sezgisel bulur; derlenmiş program, betik, gradle görevi, yorumlayıcı (`python -c`), değişkenli yol ve uzak eylemler görülmez (kör nokta).

## Spec'in kendi kapsam dürüstlüğü bölümleri (aynen)

### v1
## KAPSAM DÜRÜSTLÜĞÜ

- Bu prompttaki [D] maddeleri, MinToken v6 hazırlanırken okunan Claude Code dokümantasyon sayfalarından ve alt-ajan özetlerinden gelir; her sayfa satır satır doğrulanmadı. `env-vars`, `settings-reference` ve `hooks` sayfalarının sonları aracın kesme sınırı yüzünden okunamadı; `autoCompact*`, `bashOutputMaxChars`, `workflow*` gibi ayarların ayrıntı varsayılanları bu yüzden kurulu sürümde DOĞRULANMALIDIR.
- "Bağlam çürümesi", Gradle/Loom ayarları, "doğrulama merdiveni", "iki düzeltmeden sonra /rewind" ve paralel araç çağrısı etkileri [I]'dir; ölçülmeden kesin bilgi diye sunulmaz.
- Performans görev, model, repo ve ağa göre değişir; HighPer garanti vermez, yalnız ölçer ve takasıyla önerir.

### v2
## Kapsam Dürüstlüğü (v2)
- Bölüm G'deki düzenlerin (bağımsız gözden geçirici, test-first, spec-first, çoklu aday) kaliteyi artırdığı genel yazılım pratiği ve yaygın gözlemdir [I]; bu ortamda ve bu kullanıcının görevlerinde ÖLÇÜLMEDİ. Etki büyüklüğü bilinmez; Bölüm I ile ölçülür.
- "Kalite 2 kat" hedefi bir yön göstergesidir, vaat değildir. Verimsizliği azaltmak (F) doğruluk yerine hız/maliyet kazandırabilir; kaliteyi artırmak (G) token ve süre getirir. HighPer ikisini aynı anda maksimize edemez; seçimi takasıyla kullanıcıya sunar.

### v3
## Kapsam Dürüstlüğü (v3)
- Bu eki dayandıran kaynak okuması: iki Anthropic mühendislik yazısı (postmortem'ler) ve bir bağlam mühendisliği yazısı (alıntı ve özetle), docs: model-config (tam), best-practices (tam), costs (tam), troubleshooting (tam), how-claude-code-works (tam), features-overview (tam), prompt-caching (tam), sub-agents (ilk ~100.000 / 108.000 karakter; fork bölümü eksik). WebFetch özet katmanı kullanır: alıntılar ve sayılar kaynakta yeniden doğrulanmalıdır. InfoQ özeti ikincil kaynaktır; birincil yazıyla çelişirse birincil geçerlidir.
- Okunmayanlar: Anthropic'in "Lessons from building Claude Code: Prompt caching is everything" blog yazısı, Claude Code değişiklik günlüğünün (changelog) eski kısımları, GitHub issue'ları (kullanıcı raporları), Reddit/HN tartışmaları (yalnız ikincil alıntı var), Anthropic durum sayfası geçmişi. Postmortem'ler yalnız bildirilen olayları kapsar; bildirilmeyen kayıpları dışlamaz.
- "Model yönlendirici" puanlaması ve eşikleri HighPer'in önerisidir [I]; Anthropic yalnız model rollerini (Haiku basit, Sonnet günlük kodlama, Opus karmaşık akıl yürütme, Fable en zor/uzun işler) ve ilgili effort kılavuzunu verir. Satır sayısı için resmi bir eşik yoktur.
- "Kalite 2 kat" sözü v2'deki gibi vaat değildir. Postmortem'in en güçlü dersi şudur: varsayılan ve sürüm değişiklikleri kaliteyi (Anthropic'in ölçtüğü %3 gibi küçük farklarla bile) sessizce değiştirebilir ve bunu görmek için bile geniş ölçüm gerekir. HighPer kayıpları önlemeyi değil görünür kılmayı ve kullanıcı tarafı payı azaltmayı hedefler.

### v4
## Kapsam Dürüstlüğü (v4)
- Bu ek yeni bir araştırma sayfası okumadı; v3'te okunan kaynaklara (best-practices'teki doğrulama kapı seviyeleri ve karşı-inceleme, hooks/Stop ve PreModelSwitch bahisleri, prompt-caching'deki model değişimi, Anthropic postmortem'leri) dayanır. Hook girdi/çıktı şeması, ardışık engel üst sınırı ve PreModelSwitch hook'unun ayrıntıları bu oturumda hooks sayfasının ilgili bölümünden OKUNMADI (hooks sayfası daha önce araç sınırında kesilmişti) → kullanılmadan önce doğrulanmalıdır.
- Fabric/Minecraft'a özel doğrulama önerileri (başsız sunucu açılış testi, mixin/kayıt hatası taraması), "testi zayıflatma" kaçağı ve "aynı model aynı kör noktayı paylaşır" ifadesi [I]'dir; ölçülmedi.
- Kaçak oranını tek başına küçük örneklemle yorumlamak yanıltıcıdır; Q bölümü bunun için vardır. Garanti verilmez; hedef kaçağı görünür ve yakalanabilir kılmaktır.

## Kurulum notu (2026-10-10): Windows MSIX yolları
Claude masaüstü (MSIX) ve Microsoft Store Python, `AppData\Roaming` altını farklı sanal görünümlerle görür. Oturum klasörü `AppData\Roaming\Claude\...` altındaysa Store Python orayı göremez; gerçek kopya `AppData\Local\Packages\Claude_*\LocalCache\Roaming\...` altındadır. `scope_guard.py` ve `verify_gate.py` yapılandırmayı ve çalışma dizinini bu yola düşerek bulur (`real_path`). Normal proje klasörlerinde (Desktop, Downloads, Documents) bu durum yoktur. [G: bu makinede gözlendi]
