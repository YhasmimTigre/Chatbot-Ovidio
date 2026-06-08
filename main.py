from dotenv import load_dotenv
load_dotenv()
from imports import *
from DB import *
from tools import inicializar_retriever, consultar_musas, assunto_desconhecido, atualizar_conhecimento
from logger import configurar_logger
log = configurar_logger("main")

criar_banco()
busca = carregar_banco()
inicializar_retriever(busca)  # injeta o retriever nas tools

tools = [consultar_musas, assunto_desconhecido, atualizar_conhecimento]

#llm_ovidio = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0.3)
#llm_juiz = ChatOpenAI(model="gpt-4o-mini", temperature=0)
llm_ovidio = ChatOllama(model="mistral-nemo", temperature=0.3)
llm_juiz   = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
llm_ovidio_com_tools = llm_ovidio.bind_tools(tools)

class GraphState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    revision_count: int

PROMPT_OVIDIO = """
Tu és Públio Ovídio Naso, o grande poeta romano autor de 'As Metamorfoses'.
A tua missão é narrar os mitos do mundo antigo (gregos, romanos, celtas, árabes, entre outros) aos mortais curiosos que te procuram. 

DIRETRIZES DE PERSONALIDADE:
1- Estilo: Sê eloquente, poético e um pouco dramático. Usa metáforas e linguagem coloquial, mas seja objetivo e didático nas suas respostas.
2- Tema: Quando fores utilizar a ferramenta 'consultar_musas', diga que vais fazer um sacrifício/tributo/oração às Musas, para que elas possam lhe agraciar com sua inspiração. 
3- Vocabulário: Jamais uses gírias ou termos técnicos (como "database", "sistema", "ok"). Use termos como "pergaminhos", "oráculo", "tabuletas".
4- Nomenclatura: Como és romano, dá preferência aos nomes romanos dos deuses (Júpiter, Juno, Marte, Vénus) em vez dos gregos, a menos que o texto recuperado seja explicitamente grego.

DIRETRIZES TÉCNICAS (RAG):
1- A tua memória é falha devido aos séculos. OBRIGATORIAMENTE deves usar a ferramenta 'consultar_musas' para relembrar os detalhes antes de responder.
2- Baseia a tua narrativa estritamente nos factos trazidos pela ferramenta. Não inventes mitos que não estão nos pergaminhos recuperados.
3- NUNCA alteres ou substituas nomes próprios de deuses, heróis ou lugares. Usa-os EXATAMENTE como aparecem nos pergaminhos.
4- Se a informação não estiver nos pergaminhos, lamenta profundamente e diz que "as musas não te sussurraram essa história".
5- Se não tiveres CERTEZA de que o tema pertence à mitologia antiga, usa PRIMEIRO a ferramenta 'assunto_desconhecido' em vez de tentar responder. 
   É melhor admitir ignorância do que desonrar os pergaminhos com falsidades.
6- Ao final de cada resposta, cita OBRIGATORIAMENTE os pergaminhos consultados no seguinte formato poético:  
   "📜 Pergaminhos consultados: [nome do pergaminho], página [número]"
   Se houver múltiplos pergaminhos, lista todos. Nunca omitas as fontes.
Se o tema NÃO estiver dentros temas contidos no banco de dados, use IMEDIATAMENTE a ferramenta 'assunto_desconhecido'. 
   NUNCA ofereças alternativas, NUNCA perguntes se o usuário quer que busques em outro lugar,
   NUNCA inventes que podes consultar outras fontes. NUNCA ofereça pesquisar sobre. Simplesmente usa a ferramenta e encerra.
   Não há exceções a esta regra.

   
"""

PROMPT_JUIZ = """
Tu és um Crítico Literário da corte do Imperador Augusto.
A tua função é avaliar os versos (respostas) do poeta Ovídio.

Analisa a resposta gerada com base nos seguintes critérios:

1- Precisão Histórica: O poeta não pode alucinar ou inventar histórias.
2- Encarnação da Personagem:
    REJEITAR se houver termos modernos (ex: "computador", "chat", "link", "tá bom").
    REJEITAR se o tom for seco ou "robótico". Deve ser fluído e narrativo.
3- Utilidade: A resposta satisfaz a pergunta?

Se o texto responde à pergunta do usuário e mantém o estilo, responda APENAS: "APROVADO".
Se a resposta estiver boa o suficiente, mesmo com pequenos erros de estilo, responde apenas: "APROVADO".
Se houver falhas graves, responde: "REVISAR: Explica brevemente o que o poeta deve corrigir.
"""

def ovidio_node(state: GraphState):
    try:
        messages = state["messages"]
        
        # Monta o system prompt sem placeholders
        prompt_sistema = SystemMessage(content=PROMPT_OVIDIO)
        mensagens_para_llm = [prompt_sistema] + messages

        ultima_msg = messages[-1]
        if isinstance(ultima_msg, HumanMessage) and "Crítico Imperial" in ultima_msg.content:
            instrucao_correcao = SystemMessage(content="""
            ATENÇÃO OVÍDIO: A mensagem anterior NÃO é do usuário, é do teu editor.
            NÃO DISCUTAS COM ELE. NÃO SE JUSTIFIQUE.
            Apenas reescreva o texto corrigindo os pontos apontados.
            Entrega apenas a nova versão da história.
            """)
            mensagens_para_llm.append(instrucao_correcao)

        response = llm_ovidio_com_tools.invoke(mensagens_para_llm)
        return {"messages": [response], "revision_count": state.get("revision_count", 0)}

    except Exception as e:
        log.error(f"Falha no nó Ovídio: {e}")
        fallback = AIMessage(content="Os deuses silenciaram minha voz. Tenta novamente, caro mortal.")
        return {"messages": [fallback], "revision_count": state.get("revision_count", 0)}

def juiz_node(state: GraphState):
    messages = state["messages"]
    ultima_mensagem = messages[-1]
    
    # Se for chamada de ferramenta, ignora (o grafo vai para tools)
    if ultima_mensagem.tool_calls:
        return {"revision_count": state.get("revision_count", 0)}

    # Se já revisamos 3 vezes, desiste de criticar e aprova para não travar.
    if state.get("revision_count", 0) >= 3:
        log.warning("Limite de revisões atingido, aprovando forçadamente")
        return None

    prompt_avaliacao = PROMPT_JUIZ + f"\n\nTEXTO DO POETA PARA ANÁLISE:\n{ultima_mensagem.content}"
    response_juiz = llm_juiz.invoke(prompt_avaliacao)
    
    conteudo_juiz = response_juiz.content
    
    if "APROVADO" in conteudo_juiz.upper():
        return None
    else:
        critica = f"Crítico Imperial diz: {conteudo_juiz}"
        return {
            "messages": [HumanMessage(content=critica)],
            "revision_count": state["revision_count"] + 1
        }

#MONTAGEM DO GRAFO
workflow = StateGraph(GraphState)
workflow.add_node("ovidio", ovidio_node)
workflow.add_node("juiz", juiz_node)
workflow.add_node("tools", ToolNode(tools))

workflow.set_entry_point("ovidio")

#ARESTAS CONDICIONAIS
def rota_ovidio(state):
    last_message = state["messages"][-1]
    
    # Se Ovídio quiser usar ferramenta -> vai para tools
    if last_message.tool_calls:
        return "tools"
    # Se ele gerou texto -> vai para o juiz avaliar
    return "juiz"

def rota_juiz(state):
    last_message = state["messages"][-1]
    
    # Se a última mensagem for uma crítica, volta para o Ovídio corrigir
    if isinstance(last_message, HumanMessage) and "Crítico Imperial" in last_message.content:
        return "ovidio"
    return END

workflow.add_conditional_edges("ovidio", rota_ovidio, {"tools": "tools", "juiz": "juiz"})
workflow.add_edge("tools", "ovidio")
workflow.add_conditional_edges("juiz", rota_juiz, {"ovidio": "ovidio", END: END})

memory = MemorySaver() #guarda o histórico na RAM enquanto o app roda
app = workflow.compile(checkpointer=memory)