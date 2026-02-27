# Mistral LLM – Setup Locale con Ollama

Questo progetto utilizza **Mistral** come **Large Language Model (LLM) in locale**, senza dipendenze cloud, tramite **Ollama**.

L’obiettivo è fornire un LLM:
- completamente offline
- facilmente integrabile via API REST
- adatto a tool interni, backend e prototipi

---

## Requisiti

- macOS / Linux / Windows
- Minimo 8 GB RAM (16 GB consigliati)
- Connessione internet solo per il primo download del modello

---

## Installazione Ollama

### macOS / Windows
Scaricare e installare Ollama da:
https://ollama.com

### Linux
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Verifica installazione:
```bash
ollama --version
```

---

## Download del modello Mistral

```bash
ollama pull mistral
```

Varianti disponibili:
```bash
ollama pull mistral:7b-instruct
ollama pull mistral:latest
```

---

## Avvio del servizio

Avvio come servizio REST:
```bash
ollama serve
```

Endpoint:
http://localhost:11434

Avvio interattivo:
```bash
ollama run mistral
```

---

## Utilizzo via API REST

Endpoint:
POST http://localhost:11434/api/generate

Payload di esempio:
```json
{
  "model": "mistral",
  "prompt": "Spiegami cos'è un CAN filter su STM32",
  "stream": false
}
```

---

## Integrazione

### Python
```python
import requests

response = requests.post(
    "http://localhost:11434/api/generate",
    json={
        "model": "mistral",
        "prompt": "Spiegami J1939 Address Claimed",
        "stream": False
    }
)

print(response.json()["response"])
```

### Node.js
```js
fetch("http://localhost:11434/api/generate", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    model: "mistral",
    prompt: "Cos'è un bootloader STM32?",
    stream: false
  })
})
  .then(res => res.json())
  .then(data => console.log(data.response));
```

---

## Modelli alternativi

```bash
ollama pull mixtral
ollama pull codellama
ollama pull llama3
```

---

## Comandi utili

```bash
ollama list
ollama run <nome-modello>
```

---

## Note

- Tutto gira in locale
- Nessun dato inviato all'esterno
- Ideale per ambienti offline e industriali

---

## Licenze

- Modelli: fare riferimento alla licenza del modello specifico (Mistral AI)
- Ollama: https://ollama.com/license
