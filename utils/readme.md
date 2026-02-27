# Utilities and Prerequisites

The `utils` folder contains the necessary executable files and setup information for the **Firmware Lens** pipeline.

## Required Executables

### 1. Ollama (OllamaSetup.exe)
*   **Purpose**: Provides a local environment to run Large Language Models (LLMs) such as Mistral or Llama 3. In this project, it is used by the `generator` scripts to create AI-powered documentation and perform code analysis.
*   **Download**: [https://ollama.com](https://ollama.com)
*   **Installation**: Run the installer and follow the instructions.
*   **Usage**: 
    1.  Install and run the application.
    2.  Pull the model: `ollama pull mistral`
    3.  Run interactively: `ollama run mistral`
    
    The project interacts with Ollama via its REST API (default: `http://localhost:11434`).

#### API Usage Examples (Mistral)

**REST API (cURL):**
```bash
curl http://localhost:11434/api/generate -d '{
  "model": "mistral",
  "prompt": "Explain what a CAN filter is on STM32",
  "stream": false
}'
```

**Python Integration:**
```python
import requests

response = requests.post(
    "http://localhost:11434/api/generate",
    json={
        "model": "mistral",
        "prompt": "Explain J1939 Address Claimed procedure",
        "stream": False
    }
)
print(response.json()["response"])
```

**Node.js Integration:**
```javascript
fetch("http://localhost:11434/api/generate", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    model: "mistral",
    prompt: "What is an STM32 bootloader?",
    stream: false
  })
})
  .then(res => res.json())
  .then(data => console.log(data.response));
```

### 2. LLVM / Clang (LLVM-21.1.8-win64.exe)
*   **Purpose**: A collection of modular compiler technologies. It provides **Clang**, which is the primary engine used by this pipeline to parse C/C++ firmware code and build the Abstract Syntax Tree (AST) without needing the original proprietary toolchain.
*   **Download**: [https://github.com/llvm/llvm-project/releases](https://github.com/llvm/llvm-project/releases)
*   **Installation**: Run the installer. Ensure you select the option to **"Add LLVM to the system PATH"** during setup.
*   **Usage**: The pipeline uses the `libclang` components of this installation. You can also use `clang --version` in the terminal to verify it is correctly installed.

### 3. Graphviz (windows_10_cmake_Release_graphviz-install-14.1.2-win64.exe)
*   **Purpose**: An open-source graph visualization software. It is used by the `generator/generate_graph.py` script to transform technical data into visual diagrams, such as function call graphs and architectural maps.
*   **Download**: [https://graphviz.org/download/](https://graphviz.org/download/)
*   **Installation**: Run the installer. **Important**: Select "Add Graphviz to the system PATH" for all users (or current user) so the Python scripts can invoke the `dot` command.
*   **Usage**: Used automatically by the project. You can manually test it by running `dot -V` in your command prompt.
