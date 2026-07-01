# 📜 Ovídio — O Poeta dos Mitos

Um chatbot que encarna Públio Ovídio Naso, o poeta romano autor de *As Metamorfoses*. Ao receber uma pergunta sobre mitologia, Ovídio consulta uma biblioteca local de PDFs e narra a história solicitada com estilo poético e dramático.

O projeto usa um grafo de agentes (LangGraph) com duas LLMs trabalhando em conjunto: o **Ovídio** gera a narrativa, e um **Juiz** avalia a qualidade da resposta antes de enviá-la ao usuário.

---

## Como funciona

```
Usuário → Ovídio → consulta PDFs (RAG) → gera narrativa → Juiz avalia → resposta final
                        ↑                                        |
                        └────────── reescreve se reprovado ──────┘
```

1. O usuário faz uma pergunta sobre mitologia.
2. O Ovídio consulta o banco vetorial local (Chroma) com os PDFs indexados.
3. O Juiz avalia a resposta. Se reprovada, o Ovídio reescreve (até 3 tentativas).
4. A resposta aprovada é exibida na interface Chainlit.

---

## Pré-requisitos

- Python 3.10+
- [Ollama](https://ollama.com) instalado e rodando
- Conta gratuita no [Groq](https://console.groq.com) para a chave de API do Juiz
- PDFs de mitologia na pasta `./historia/`

---

## Instalação

**1. Clone o repositório:**
```bash
git clone https://github.com/seu-usuario/ovidio.git
cd ovidio
```

**2. Crie e ative o ambiente virtual:**
```bash
python -m venv .venv
source .venv/bin/activate  # Mac/Linux
.venv\Scripts\activate     # Windows
```

**3. Instale as dependências:**
```bash
pip install -r requirements.txt
pip install langchain-ollama langchain-groq sentence-transformers cryptography
```

**4. Configure as variáveis de ambiente:**
```bash
cp .env.example .env
```
Edite o `.env` e preencha sua `GROQ_API_KEY`.

**5. Baixe os modelos locais:**
```bash
ollama pull mistral-nemo   # Ovídio (geração narrativa)
```

**6. Adicione seus PDFs:**

Coloque arquivos PDF sobre mitologia na pasta `./historia/`. O banco vetorial será criado automaticamente na primeira execução.

> **Nota:** as pastas `banco_mitologia/` e `historia/` não estão incluídas no repositório.
> A pasta `banco_mitologia/` é gerada automaticamente na primeira execução.
> Adicione seus próprios PDFs de mitologia na pasta `./historia/` antes de iniciar.
---

## Como usar

Abra dois terminais:

**Terminal 1 — inicia o Ollama:**
```bash
ollama serve
```

**Terminal 2 — inicia o chatbot:**
```bash
chainlit run interface.py -w
```

Acesse `http://localhost:8000` no navegador e comece a conversar com Ovídio.

---

## Estrutura dos arquivos

| Arquivo | O que faz |
|---|---|
| `main.py` | Monta o grafo de agentes (Ovídio + Juiz + Tools), define os prompts e compila o fluxo de execução |
| `interface.py` | Interface Chainlit — recebe mensagens do usuário, executa o grafo e exibe as respostas |
| `tools.py` | Define as ferramentas disponíveis para o Ovídio: consultar PDFs, bloquear temas fora do escopo e atualizar o banco |
| `DB.py` | Cria e gerencia o banco vetorial Chroma a partir dos PDFs da pasta `./historia/` |
| `imports.py` | Centraliza todos os imports do projeto |
| `logger.py` | Configura o sistema de logs (nível controlado pela variável `LOG_LEVEL` no `.env`) |
| `monitor.py` | Monitora a pasta `./historia/` e atualiza o banco automaticamente ao detectar novos PDFs |
| `Agent-Reviewer.py` | Agente separado de revisão de texto com RAG próprio (independente do chatbot principal) |
| `teste_interface.py` | Interface mock para testar o visual do Chainlit sem consumir as LLMs |
| `test_models.py` | Script para verificar quais modelos estão disponíveis nas APIs configuradas |
| `chainlit.md` | Texto exibido na tela de boas-vindas do chat |
| `requirements.txt` | Dependências do projeto |
| `.env.example` | Modelo do arquivo de variáveis de ambiente |

---

## Modelos utilizados

| Papel | Modelo | Onde roda |
|---|---|---|
| Ovídio (narrador) | `mistral-nemo` | Local via Ollama |
| Juiz (avaliador) | `llama-3.3-70b-versatile` *| Groq (nuvem, gratuito) |
| Embeddings (busca) | `all-MiniLM-L6-v2` | Local via HuggingFace |

> Nota: lllama-3.3-70b-versatile foi descomissionado em 01/07/26, utilize GPT OSS 120B ou Qwen3.6 27B em seu lugar.
---

## Variáveis de ambiente

```bash
# Nível de log: DEBUG | INFO | WARNING | ERROR (padrão: INFO)
LOG_LEVEL=INFO

# Chave da API do Groq (obrigatória)
# Obter em: https://console.groq.com
GROQ_API_KEY=sua_chave_aqui
```

---

## Adicionando novos livros

Há duas formas de adicionar novos PDFs ao conhecimento do Ovídio:

**Automático:** com o `monitor.py` rodando em um terminal separado, qualquer PDF copiado para a pasta `./historia/` é indexado automaticamente.

```bash
python monitor.py
```

**Manual:** peça diretamente ao Ovídio no chat: *"atualize sua biblioteca"*.

---

## Observações

- Na primeira execução, a indexação dos PDFs pode demorar alguns minutos dependendo da quantidade de arquivos.
- PDFs protegidos por senha não são indexados automaticamente.
- O histórico da conversa é mantido em memória durante a sessão e é perdido ao reiniciar.

