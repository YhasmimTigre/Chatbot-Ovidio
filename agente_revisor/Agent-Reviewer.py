from imports import *
from dotenv import load_dotenv
load_dotenv()

# Modelo Gemini
#llm_revisor = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0.2)
#llm_juiz = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0)
llm_ovidio = ChatOllama(model="mistral-nemo", temperature=0.3)
llm_juiz   = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
# --- COMPONENTE RAG ---
def read_pdf(caminho_arquivo_pdf: str):
    print(f"--- RAG: Carregando arquivo {caminho_arquivo_pdf} ---")
    
    # 1. Carregar e Dividir
    loader = PyPDFLoader(caminho_arquivo_pdf)
    docs_brutos = loader.load()
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    chunks = text_splitter.split_documents(docs_brutos)
    print(f"   > Texto dividido em {len(chunks)} pedaços.")

    # 2. Configurar Embeddings e VectorStore VAZIO
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    # Criamos o banco vazio primeiro para adicionar aos poucos
    vectorstore = Chroma(
        collection_name="guia_estilo_pdf_db",
        embedding_function=embeddings,
        # Se quiser persistir em disco, descomente a linha abaixo:
        # persist_directory="./chroma_db" 
    )

    batch_size = 5
    total_chunks = len(chunks)
    
    print(f"   > Iniciando indexação lenta para respeitar limites da API...")
    
    for i in range(0, total_chunks, batch_size):
        # Pega um grupo de 5 documentos
        batch = chunks[i : i + batch_size]
        
        # Adiciona ao banco
        vectorstore.add_documents(batch)
        
        print(f"     Processado {min(i + batch_size, total_chunks)}/{total_chunks} chunks...")
        
        time.sleep(2) 

    print("   > Indexação concluída com sucesso!")
    
    return vectorstore.as_retriever(search_kwargs={"k": 3})

arquivo_pdf = "redacao101.pdf" 

if os.path.exists(arquivo_pdf):
    retriever = read_pdf(arquivo_pdf)
else:
    print(f"AVISO: '{arquivo_pdf}' não encontrado using mock RAG.")
    raise FileNotFoundError(f"Por favor, coloque um arquivo chamado {arquivo_pdf} na pasta.")

# --- ATUALIZAÇÃO DA FERRAMENTA (TOOL) ---
# A ferramenta agora usa o 'retriever' criado acima
from langchain_core.tools import tool

@tool
def consultar_guia_estilo(duvida: str) -> str:
    """
    Consulta o PDF do Guia de Estilo.
    Use para dúvidas de formatação, tom ou regras.
    """
    print(f"--- RAG: Buscando no PDF por: '{duvida}' ---")
    docs = retriever.invoke(duvida)
    
    if not docs:
        return "Nada encontrado."
        
    resposta = ""
    for i, doc in enumerate(docs):
        pag = doc.metadata.get('page', '?')
        conteudo = doc.page_content.replace('\n', ' ')
        resposta += f"[Fonte {i+1} - Pág {pag}]: {conteudo}\n\n"
        
    return resposta

tools = [consultar_guia_estilo]

# --- DEFINIÇÃO DO ESTADO DO GRAFO ---
class AgentState(TypedDict):
    texto_original: str
    texto_revisado: str
    feedback_juiz: str
    score: int
    revision_count: int
    messages: Annotated[List[BaseMessage], operator.add]

# --- NÓ 1: AGENTE REVISOR (ReAct) ---
def revisor_node(state: AgentState):
    messages = state['messages']
    
    # Se for a primeira vez, adicionar o prompt inicial
    if not messages:
        prompt_inicial = f"""
        Você é um Editor Sênior. Sua tarefa é revisar o seguinte texto:
        ---
        "{state['texto_original']}"
        ---
        
        PASSO 1: Use a ferramenta 'consultar_guia_estilo' para verificar as regras de 'erros comuns'.
        PASSO 2: Reescreva o texto aplicando essas regras estritamente.
        
        Se houver feedback anterior do Juiz, corrija o texto baseando-se nele: {state.get('feedback_juiz', '')}
        """
        messages = [HumanMessage(content=prompt_inicial)]
    
    # Vincula ferramentas ao LLM (ReAct behavior)
    revisor_com_tools = llm_ovidio.bind_tools(tools)
    response = revisor_com_tools.invoke(messages)
    
    return {"messages": [response]}

# --- NÓ 2: EXECUÇÃO DE FERRAMENTAS (Parte do ReAct) ---
# Este nó executa a busca no RAG se o LLM solicitar
tool_node = ToolNode(tools)

# --- NÓ 3: AGENTE JUIZ (Gemini) ---
def juiz_node(state: AgentState):
    # O último "AIMessage" das mensagens contém o texto final revisado (se não foi uma chamada de tool)
    last_message = state['messages'][-1]
    
    # Extração simples do texto (num caso real, faríamos um parse mais robusto)
    texto_candidato = last_message.content
    
    prompt_juiz = f"""
    Atue como um Juiz de Qualidade Implacável.
    
    Texto Original: "{state['texto_original']}"
    Texto Revisado pelo Agente: "{texto_candidato}"
    
    Critérios:
    1. O uso da crase está correto?
    2. Há uso de verbo composto?
    3. A palavra "onde" está sendo usada corretamente?
    
    Responda EXATAMENTE neste formato:
    SCORE: [Nota de 0 a 10]
    FEEDBACK: [Sua crítica detalhada ou "Aprovado" se nota > 8]
    """
    
    avaliacao = llm_juiz.invoke(prompt_juiz)
    conteudo = avaliacao.content
    
    # Parse simples da resposta
    import re
    score_match = re.search(r"SCORE: (\d+)", conteudo)
    score = int(score_match.group(1)) if score_match else 0
    feedback = conteudo.split("FEEDBACK:")[1].strip() if "FEEDBACK:" in conteudo else conteudo
    
    print(f"\n--- AVALIAÇÃO DO JUIZ (Tentativa {state['revision_count'] + 1}) ---")
    print(f"Nota: {score}/10")
    print(f"Feedback: {feedback}")
    
    return {
        "texto_revisado": texto_candidato,
        "score": score,
        "feedback_juiz": feedback,
        "revision_count": state.get("revision_count", 0) + 1
    }

# --- LÓGICA CONDICIONAL ---
def deve_continuar(state: AgentState):
    messages = state['messages']
    last_message = messages[-1]
    
    # 1. Se o agente pediu para usar uma ferramenta, vá para o nó de ferramentas
    if last_message.tool_calls:
        return "tools"
    
    # 2. Se o agente apenas respondeu (texto), vá para o Juiz
    # Mas antes, verificamos se o Juiz já aprovou ou se estouramos o limite
    if state.get("score", 0) >= 8:
        return END
    
    if state.get("revision_count", 0) >= 3: # Limite de 3 tentativas para evitar loop infinito
        print("--- Limite de tentativas atingido ---")
        return END
        
    return "juiz"

def rota_pos_juiz(state: AgentState):
    if state['score'] >= 8:
        return END
    else:
        # Se a nota for baixa, limpamos as mensagens antigas para focar no feedback novo
        # ou mantemos o histórico. Aqui, reinjetamos o feedback como instrução humana.
        return "revisor"

# --- CONSTRUÇÃO DO GRAFO ---
workflow = StateGraph(AgentState)

# Adiciona nós
workflow.add_node("revisor", revisor_node)
workflow.add_node("tools", tool_node)
workflow.add_node("juiz", juiz_node)

# Define arestas
workflow.set_entry_point("revisor")

# Lógica do Revisor: Ou chama ferramenta, ou manda pro Juiz
workflow.add_conditional_edges(
    "revisor",
    deve_continuar,
    {
        "tools": "tools", 
        "juiz": "juiz",
        END: END
    }
)

# Lógica da Ferramenta: Volta pro Revisor (para ele usar a info recuperada)
workflow.add_edge("tools", "revisor")

# Lógica do Juiz: Se bom -> Fim, Se ruim -> Volta pro Revisor
workflow.add_conditional_edges(
    "juiz",
    rota_pos_juiz,
    {
        END: END,
        "revisor": "revisor"
    }
)

memory = MemorySaver()
app = workflow.compile(checkpointer=memory)

# --- EXECUÇÃO ---
texto_input = """
A respeito do trabalho, vou fazer melhorias onde precisar
"""

inputs = {
    "texto_original": texto_input, 
    "revision_count": 0, 
    "messages": []
}

config = {"configurable": {"thread_id": "revisao-1"}}

print("--- INICIANDO AGENTE DE REVISÃO ---")
for output in app.stream(inputs, config=config):
    pass

print("\n--- RESULTADO FINAL ---")
final_state = app.get_state(config).values
print(f"Texto revisado: {final_state.get('texto_revisado')}")
print(f"Score: {final_state.get('score')}")