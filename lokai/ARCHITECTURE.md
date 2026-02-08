# locAI – Arhitektura aplikacije (ASCII UML)

## 1. Visok nivo – slojevi i ulazna tačka

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              main.py (Entry Point)                                │
│  • Postavlja HF cache env (Q: drive)                                             │
│  • QApplication → ConfigManager → SetupWizard (first run?) → MainWindow          │
└─────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              UI SLOJ (PySide6)                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│  MainWindow  │  SettingsDialog  │  SetupWizard  │  ChatWidget  │  StatusPanel   │
│  DebugDialog │  VoiceInputWidget│  AudioPlayer  │  Theme       │  MaterialIcons │
│  Workers: OllamaWorker, EmbeddingWorker, ChatToolsWorker,                        │
│           ImageGenerationWorker, VideoGenerationWorker, AudioGenerationWorker,   │
│           ASRWorker                                                              │
└─────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              CORE SLOJ (logika)                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ConfigManager  │  OllamaClient  │  OllamaDetector  │  ImageGenerator           │
│  VideoGenerator │  AudioGenerator│  EmbeddingClient │  ChatVectorStore          │
│  ASREngine      │  TTSEngine     │  PocketTTSEngine │  ImageProcessor           │
│  tools_handler  │  global_shortcuts                                                │
└─────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              UTILS + SPOLJAŠNJI                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ModelManager  │  clear_gpu_memory  │  Ollama API  │  HuggingFace / diffusers   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Komponente i zavisnosti (komponentni dijagram)

```
                    ┌──────────────────┐
                    │   ConfigManager   │
                    │  (config.json)   │
                    └────────┬─────────┘
                             │ get/set/save
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│  SetupWizard   │  │   MainWindow    │  │ SettingsDialog │
│ (first run)    │  │                │  │                │
└───────┬────────┘  └───────┬────────┘  └────────────────┘
        │                   │
        │    ┌──────────────┼──────────────┐
        ▼    ▼              ▼              ▼
   OllamaDetector    ChatWidget     StatusPanel
        │                   │              │
        │                   │              │
        ▼                   ▼              ▼
   OllamaClient      OllamaWorker   (model, seed, status)
        │                   │
        │                   ├──────────────► OllamaClient.generate_response_stream
        │                   ├──────────────► EmbeddingClient (RAG)
        │                   ├──────────────► ChatVectorStore (semantic memory)
        │                   ├──────────────► ImageProcessor (slike u promptu)
        │                   └──────────────► execute_tool (tools_handler)
        │
        ▼
   Ollama API (localhost:11434)
```

---

## 3. Glavni tok: korisnik šalje poruku (sekvenca)

```
  User        ChatWidget    MainWindow    OllamaWorker    OllamaClient    Ollama API
   │               │             │              │               │              │
   │  Enter        │             │              │               │              │
   │──────────────►│             │              │               │              │
   │               │ send_message│              │               │              │
   │               │────────────►│              │               │              │
   │               │             │ start worker│               │              │
   │               │             │─────────────►│               │              │
   │               │             │              │ generate_     │              │
   │               │             │              │ response_     │              │
   │               │             │              │ stream        │              │
   │               │             │              │──────────────►│              │
   │               │             │              │               │ POST /api/   │
   │               │             │              │               │ generate     │
   │               │             │              │               │─────────────►│
   │               │             │              │               │   stream     │
   │               │             │  chunk       │               │◄─────────────│
   │               │             │◄─────────────│◄──────────────│              │
   │               │  append     │              │               │              │
   │               │◄────────────│              │               │              │
   │  (tekst se    │             │              │               │              │
   │   pojavljuje) │             │              │               │              │
```

---

## 4. Klase i nasljeđivanje (pojednostavljeni klasni dijagram)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ Qt / PySide6                                                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│  QMainWindow          QDialog           QWidget           QThread                │
│       △                  △                  △                  △                  │
│       │                  │                  │                  │                  │
│  MainWindow    SettingsDialog         ChatWidget      OllamaWorker               │
│               SetupWizard             StatusPanel     EmbeddingWorker            │
│               DebugDialog             VoiceInputWidget  ChatToolsWorker          │
│                                       ChatBubble       ImageGenerationWorker    │
│                                       ChatInputField   VideoGenerationWorker    │
│                                       AudioPlayerWidget  AudioGenerationWorker  │
│                                                         ASRWorker                │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│ Core (nema Qt nasljeđivanja)                                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ConfigManager     OllamaClient     OllamaDetector     EmbeddingClient           │
│  ChatVectorStore   ImageGenerator   VideoGenerator     AudioGenerator            │
│  ASREngine         TTSEngine        PocketTTSEngine    ImageProcessor            │
│  tools_handler (get_available_tools, execute_tool)                               │
│  GlobalShortcutHandler(QObject)                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Moduli po paketima

```
lokai/
├── main.py                    # Ulaz: app, ConfigManager, SetupWizard?, MainWindow
├── config/
│   └── default_config.json   # Zadana konfiguracija
├── core/
│   ├── config_manager.py     # ConfigManager – čitanje/pisanje config.json
│   ├── ollama_client.py      # OllamaClient – API pozivi (generate, chat, tools)
│   ├── ollama_detector.py    # OllamaDetector – je li Ollama instalirana/pokrenuta
│   ├── asr_engine.py         # ASREngine – speech-to-text (voice input)
│   ├── tts_engine.py         # TTSEngine – Kokoro TTS
│   ├── pocket_tts_engine.py  # PocketTTSEngine – alternativni TTS
│   ├── audio_generator.py    # AudioGenerator – generiranje zvuka
│   ├── image_generator.py    # ImageGenerator – generiranje slika (diffusers)
│   ├── image_processor.py   # ImageProcessor – priprema slika za model
│   ├── video_generator.py   # VideoGenerator – generiranje videa
│   ├── embedding_client.py  # EmbeddingClient – embeddinsi (npr. nomic-embed)
│   ├── chat_vector_store.py # ChatVectorStore – RAG/semantic memory
│   ├── tools_handler.py     # get_available_tools, execute_tool
│   └── global_shortcuts.py  # GlobalShortcutHandler
├── ui/
│   ├── main_window.py        # MainWindow, OllamaWorker, EmbeddingWorker, ChatToolsWorker
│   ├── chat_widget.py        # ChatWidget, ChatInputField, ChatBubble, TypingIndicator
│   ├── settings_dialog.py    # SettingsDialog – sve postavke
│   ├── setup_wizard.py       # SetupWizard – first-run wizard
│   ├── debug_dialog.py       # DebugDialog
│   ├── status_panel.py       # StatusPanel – model, seed, status
│   ├── voice_input_widget.py # VoiceInputWidget – glasovni unos
│   ├── audio_player_widget.py# AudioPlayerWidget – reprodukcija TTS/audio
│   ├── theme.py              # Theme
│   ├── material_icons.py     # MaterialIcons
│   ├── attachments.py        # Pomoćne za priloge (datoteke)
│   ├── asr_worker.py         # ASRWorker (QThread)
│   ├── image_worker.py       # ImageGenerationWorker (QThread)
│   ├── video_worker.py      # VideoGenerationWorker (QThread)
│   └── audio_worker.py      # AudioGenerationWorker (QThread)
└── utils/
    ├── model_manager.py      # ModelManager – upravljanje modelima
    └── clear_gpu_memory.py  # Čišćenje GPU memorije
```

---

## 6. Kako funkcionira (kratki opis)

1. **Pokretanje**  
   `main.py` učitava konfiguraciju (`ConfigManager`). Ako je first run, prikaže se `SetupWizard` (Ollama provjera, tema, itd.). Zatim se kreira `MainWindow`.

2. **Glavni prozor**  
   `MainWindow` drži `ConfigManager`, kreira `OllamaDetector` i `OllamaClient`, te po potrebi (s odgodom) `EmbeddingClient` i `ChatVectorStore` za RAG. U sredini je `ChatWidget`, ispod `StatusPanel`. Postavke otvaraju `SettingsDialog`.

3. **Chat**  
   Korisnik piše u `ChatWidget` (ili glasovni unos preko ASR). Na Enter, `MainWindow` pokreće `OllamaWorker` u zasebnoj niti. Worker koristi `OllamaClient.generate_response_stream()` i šalje chunkove natrag u UI (streaming). Ako je RAG uključen, prije slanja u model mogu se dohvatiti relevantni konteksti iz `ChatVectorStore` (embeddingi preko `EmbeddingClient`). Ako model vrati tool call, `ChatToolsWorker` poziva `execute_tool` iz `tools_handler`.

4. **Slike / video / audio**  
   Generiranje slike: `ImageGenerationWorker` → `ImageGenerator` (diffusers). Video: `VideoGenerationWorker` → `VideoGenerator`. TTS/audio: `AudioGenerationWorker` / `TTSEngine` / `PocketTTSEngine`. Svi workers su `QThread` da ne blokiraju UI.

5. **Konfiguracija**  
   Sve postavke (Ollama URL, model, RAG, slike, TTS, tema, itd.) čitaju se i pišu preko `ConfigManager`; UI u `SettingsDialog` samo mapira polja na `config_manager.get/set/save`.

---

## 7. Ocena arhitekture (1–10) i predlozi za refaktorisanje

### Ocena: **6/10**

**Šta je dobro:**
- **Razdvajanje UI / Core** – Core ne zavisi od UI (nema `import lokai.ui` u core). ConfigManager, OllamaClient, workers, tools_handler su čisti.
- **Jedan ulaz** – `main.py` je jasan: config → wizard (ako treba) → MainWindow.
- **Workeri u zasebnim nitima** – Ollama, embedding, image/video/audio/ASR rade u QThread, UI ostaje odgovoran.
- **Signali/slotovi** – ChatWidget emituje signale (message_sent, image_prompt_sent, …), MainWindow ih povezuje; nema direktnog uplitanja.

**Šta vuče ocenu nadole:**
- **„God“ objekti** – MainWindow (~3270 linija, 90+ metoda) i SettingsDialog (~3010 linija) rade previše toga. Teško je održavati i testirati.
- **Workeri u main_window.py** – `EmbeddingWorker`, `OllamaWorker`, `ChatToolsWorker` su na dnu MainWindow fajla; trebali bi biti u zasebnim modulima (npr. `ui/ollama_worker.py`).
- **Duplikacija load/save u Settings** – `load_settings` i `save_settings` su ogromni i ponavljaju isti obrazac (get/set po ključu). Svaki tab može imati svoj load/save ili jedan generički binding (config key ↔ widget).
- **Previše stanja u MainWindow** – embedding, RAG, seed, model cache, conversation history, TTS/ASR/image/video inicijalizacije – sve u jednoj klasi. Dio toga može u „service“ objekte (npr. ChatSessionService, RAGService).
- **ChatWidget takođe velik** – ~2240 linija, više klasa u jednom fajlu; moguće je podeliti (npr. chat_bubble.py, chat_input.py) ili bar grupisati po odgovornosti.

---

### Šta bi moglo da se refaktorise (prioritet)

| Prioritet | Šta | Zašto |
|-----------|-----|--------|
| **1** | Izvući **OllamaWorker, EmbeddingWorker, ChatToolsWorker** u `ui/ollama_worker.py`, `ui/embedding_worker.py`, `ui/chat_tools_worker.py` (ili jedan `ui/chat_workers.py`) | Smanjuje main_window.py, jasnija odgovornost, lakše testiranje. |
| **2** | **SettingsDialog** podeliti po tabovima: svaki tab u zaseban modul (npr. `ui/settings/ollama_tab.py`, `general_tab.py`, …) ili jedan „tab factory“ sa zajedničkim load/save bindingom (config key → widget) | Fajl od 3000+ linija je neodrživ; manji fajlovi po tabu ili generički binding smanjuju duplikaciju. |
| **3** | Uvesti **ChatSessionService** (ili sličan servis) u core/ ili ui/: drži `conversation_history`, `current_context`, `current_chat_id`, a MainWindow samo poziva servis i osvežava UI | MainWindow gubi desetine polja i metoda; jedan mest za logiku konverzacije. |
| **4** | **RAG/embedding** logiku grupisati u jedan modul (npr. `core/rag_service.py`): inicijalizacija EmbeddingClient + ChatVectorStore, `_build_prompt_with_semantic_memory`, `_embed_message_async`, pa MainWindow samo koristi RAGService | Smanjuje broj metoda i stanja u MainWindow. |
| **5** | **ChatWidget** razbiti na manje fajlove: npr. `ChatBubble`, `ChatInputField`, `TypingIndicator` u `ui/chat/` (bubble.py, input.py, typing_indicator.py), a ChatWidget ih samo sastavlja | Lakše čitanje i izmene u chat UI. |
| **6** | Zajednički **config ↔ widget** binding za Settings: jedna mala biblioteka (npr. `config_manager.get/set` + mapa “key → (get_widget_value, set_widget_value)”) da load_settings/save_settings ne budu stotine linija | Manje duplikacije i grešaka pri dodavanju novih postavki. |

---

### Kratko

- **Arhitektura je 6/10**: jasna podela UI vs Core i solidan tok podataka, ali preveliki MainWindow i SettingsDialog i workers u istom fajlu kao MainWindow.
- **Najveći dobitak**: izvući workers u zasebne fajlove (1), pa podeliti Settings po tabovima ili uvesti binding (2), pa uvesti ChatSessionService i RAGService (3–4). To bi podiglo ocenu na oko 7.5–8/10 i znatno olakšalo održavanje.

---

## 8. Bezbednost (security) – pregled i preporuke

### Šta je u redu

- **Config u korisničkom direktorijumu** – `config.json` je u `%LOCALAPPDATA%\locAI` (Windows) ili `~/.config/lokai` (Linux/Mac), ne u projektu; pristup ima samo trenutni korisnik.
- **Nema hardkodovanih tajni** – u kodu nema API ključeva ili lozinki; Ollama je lokalna, tools koriste javne API-je (DuckDuckGo, wttr.in, worldtimeapi, itd.) bez tajni.
- **Core ne zavisi od UI** – manji napadna površina, logika je izdvojena.
- **Subprocess bez shell-a** – `subprocess.run(["ollama", "stop", model_name])` koristi listu argumenata, ne shell=True, pa nema direktne command injection preko model_name (ostaje validacija imena modela).
- **HTML escape u chatu** – `_format_markdown` prvo escape-uje `&`, `<`, `>` pa tek onda formatira markdown; smanjuje XSS iz običnog teksta.
- **Attachments** – dozvoljene ekstenzije su eksplicitno liste (tekst/kod); binarni fajlovi se heuristički detektuju.

---

### Rizici i šta poboljšati

| Rizik | Gde | Šta uraditi |
|-------|-----|-------------|
| **XSS preko linkova u markdown-u** | `chat_widget._format_markdown`: link `[text](url)` → `href="\2"` bez provere URL-a. | Dozvoliti samo `http://` i `https://` u `href`. Odbaciti ili ne praviti link za `javascript:`, `data:`, `file:`, i ostale ne-http(s) sheme. |
| **SSRF u tools** | `scrape_webpage(url)` i `open_url` – URL dolazi od modela; nema provere da li je localhost / privatna mreža. | Validirati URL pre `requests.get`: dozvoliti samo `http`/`https`, zabraniti hostove koji se resolve-uju na 127.0.0.1, ::1, 10.x, 172.16–31.x, 192.168.x, 169.254.x (metadata), itd. |
| **Otvaranje fajla po putanji** | `ChatBubble`: "Open in default app" → `os.startfile(image_path)` / `subprocess.run(["open", image_path])`. `image_path` je putanja koju je korisnik uneo (upload/drop). | Opciono: pri otvaranju proveriti da je fajl zaista slika (npr. ekstenzija na allowlist: .png, .jpg, …) ili da je unutar direktorijuma za privremene slike; ili jasno dokumentovati da korisnik otvara fajl na svoju odgovornost. |
| **Path traversal u attachments** | `read_text_file_with_limits(path)` – `path` dolazi od korisnika (drag-and-drop). Nema provere da je unutar dozvoljenog stabla. | Normalizovati putanju (`os.path.realpath`) i proveriti da je unutar korisničkog home ili drugog dozvoljenog prefiksa; odbiti `../` izlazak iz tog stabla. |
| **Zlonamerni chat fajl** | `load_chat`: učitava JSON sa diska; `conversation` se prikazuje preko `_format_markdown`. | Link href sanitization (gore) štiti od XSS. Dodatno: ograničiti broj poruka ili ukupnu veličinu učitavanja da spreči DoS (npr. max 10k poruka ili max N MB). |
| **Ollama base_url iz config-a** | Ako neko izmeni config i stavi `base_url` na drugi server, sav prompt ide tamo. | Ovo je očekivano ponašanje (korisnik kontroliše config). Dokumentovati da se koristi samo pouzdana Ollama instanca; opciono upozorenje ako base_url nije localhost. |
| **Tool argumenti od modela** | `execute_tool(tool_name, arguments)` – argumenti dolaze od LLM-a. | `tool_name` je u suštini allowlist (switch u execute_tool). Validirati/ograničiti argumente po tool-u (npr. URL za scrape_webpage, repo format za search_code); već pomenuti SSRF za URL. |

---

### Preporuke (prioritet)

1. **Sanitizacija URL-a u markdown linkovima** – u `_format_markdown`, pre nego što postavite `href`: dozvoliti samo sheme `http` i `https`, u suprotnom ne praviti link ili staviti `href="#"`.
2. **SSRF zaštita u tools** – pre svakog `requests.get(url)` u `scrape_webpage` / `open_url`: parsirati URL, proveriti shemu (samo http/https), resolve-ovati host u IP i odbiti ako je privatna/loopback (ili koristiti biblioteku tipa `url-normalize` + allowlist domena).
3. **Path traversal za attachments** – u `read_text_file_with_limits` i kod drugog čitanja user path: `realpath` + provera da je path ispod dozvoljenog direktorijuma.
4. **Ograničenje učitavanja chat fajla** – pri `load_chat` ograničiti `len(conversation)` i/ili ukupnu veličinu JSON-a.
5. **Opciono: validacija `model_name`** pre `subprocess.run(["ollama", "stop", model_name])` – dozvoliti samo znakove tipa slova, cifre, `-`, `_`, `:`, da spreči bilo kakvu edge-case injection.

---

*Dijagram opisuje arhitekturu lokai aplikacije u ASCII UML formatu.*
