# 🧩 Firmware Lens
 
Pipeline di **analisi statica per firmware embedded Keil (STM32)** basata su **clang / libclang**, progettata per analizzare codice **senza compilarlo**, ricostruendo **AST, simboli e dipendenze** a partire da un progetto Keil reale.
 
---
 
## 🎯 Scopo del progetto
 
Analizzare firmware embedded Keil **così com’è**, senza:
 
- modificare il codice sorgente
- usare toolchain proprietarie
- simulare l’esecuzione
- generare binari
 
> **Il codice NON viene adattato al tool.  
> È il tool che simula l’ambiente di compilazione.**
 
Questa pipeline replica ciò che fanno tool commerciali di analisi embedded, ma in modo:
- trasparente
- estendibile
- controllabile
- integrabile con LLM locali
 
---
 
## ✅ Stato attuale
 
- **Infrastruttura di Analisi (Stabile):**
  - ✔ Parsing completo del progetto Keil (`.uvprojx`) tramite [`keil_to_compile_commands.py`](keil_to_compile_commands.py).
  - ✔ Generazione corretta di `compile_commands.json`.
  - ✔ Clang configurato con `-nostdinc` e include path simulati (directory [`sensor_logic_ecu_JD/Sensor_Logic_ECU/analysis_stubs/`](sensor_logic_ecu_JD/Sensor_Logic_ECU/analysis_stubs/)).
  - ✔ AST costruibile **senza errori** e libclang operativo.
  - ✔ Estrazione funzioni funzionante tramite [`extract_functions.py`](extract_functions.py) e [`extract_all_functions.py`](extract_all_functions.py).
  - ✔ Warning residui (macro ridefinite, ecc.) gestiti e considerati attesi.
 
- **Logica Applicativa (In Sviluppo):**
  - **Prossimi Step (Definiti in [`extract_task.py`](extract_task.py)):**
    1. Estensione AST (tutte le funzioni, dichiarazioni, mapping file↔simboli).
    2. Generazione Call Graph (chi chiama chi, dipendenze driver↔applicazione) tramite [`build_task_call_graph.py`](build_task_call_graph.py).
    3. RTOS awareness (Task CMSIS, funzioni per task, sincronizzazioni).
    4. Generazione IR Strutturato stabile (`firmware_ir.json`) tramite [`classify_functions.py`](classify_functions.py).
    5. Integrazione LLM locale (spiegazione, documentazione, overview architetturali).
 
---
 
## ⚙️ Strumenti Principali
 
### 1. [`keil_to_compile_commands.py`](keil_to_compile_commands.py)
 
**Scopo:** Converte un progetto Keil in un database compatibile clang, estraendo sorgenti, include path reali e macro `-D`.
 
**Output:** `compile_commands.json`
 
**Note:** I comandi generati includono modifiche forzate come `-nostdinc` e `-Ianalysis_stubs`, rendendoli inadatti alla compilazione diretta ma perfetti per l'analisi statica.
 
### 2. [`extract_functions.py`](extract_functions.py) & [`extract_all_functions.py`](extract_all_functions.py)
 
**Scopo:** Analisi basata su **libclang** per costruire l’AST ed estrarre metadati delle funzioni (nome, ritorno, parametri, posizione).
 
**Output:** Prima forma di **IR strutturato** del progetto.
 
### 3. Directory degli Stub (`analysis_stubs/`)
 
**Scopo:** Fornire una libc / BSP minimale finta per risolvere tipi e simboli, necessaria poiché clang è eseguito con `-nostdinc`. Questi stub **non** servono per la compilazione.
 
**Header presenti (Esempi):**
- `keil_armcc_stubs.h`: Macro specifiche ARMCC e tipi base.
- `cmsis_os.h`: Definizione di costrutti CMSIS-RTOS v1 (task, event, signal).
- `Driver_UART.h`: Astrazione driver UART.
 
---
 
## ⚠️ Avvertenze e Limitazioni (Per Design)
 
Il sistema è progettato per l'analisi, non per la compilazione:
- **Non compila, non linka, non genera binari.**
- **Non esegue codice né verifica la correttezza funzionale.**
- Non dipende da toolchain proprietarie (ARMCC/GCC ARM).
 
I warning riportati da clang (`macro redefined`, `builtin redeclared`, ecc.) **non bloccano l’analisi** e non vengono corretti intenzionalmente.
 
---
 
## 🧩 Stato del Progetto e Visione
 
L'infrastruttura di analisi è stabile e il firmware è **completamente analizzabile** staticamente. Il progetto è maturo per le fasi di ingegneria inversa e supporto LLM:
 
- Autodocumentazione
- Reverse engineering
- Auditing
- Supporto a modelli LLM locali
 
---
 
## ✍️ TODO – Dominio Applicativo (Da Compilare)
 
Questa sezione è riservata alla documentazione del dominio funzionale del firmware analizzato:
- Scopo funzionale del firmware.
- Dominio applicativo (es. Controllo motore, gestione CAN bus).
- Dispositivo target (es. STM32F205VC).
- Flussi logici principali (es. Ciclo di campionamento, gestione messaggi Isobus).
