from imports import *
from main import app
import re

@cl.on_chat_start
async def start():
    await cl.Message(
        content="Olá, caro mortal! Sou Ovídio Naso. Pergunte-me sobre os deuses e as transformações do mundo, e consultarei as musas para ti."
    ).send()
    cl.user_session.set("thread_id", cl.user_session.get("id"))

@cl.on_message
async def main(message: cl.Message):
    thread_id = cl.user_session.get("thread_id")
    config = {"configurable": {"thread_id": thread_id}}
    
    inputs = {
        "messages": [HumanMessage(content=message.content)],
        "revision_count": 0
    }

    msg_resposta = cl.Message(content="⏳ Ovídio está consultando os pergaminhos e debatendo com os escribas...")
    await msg_resposta.send()

    texto_final_ovidio = None
    ultimo_conteudo = None

    async for output in app.astream(inputs, config=config, stream_mode="updates"):
        # Captura qualquer mensagem do nó ovidio
        if "ovidio" in output:
            ultima_msg = output["ovidio"]["messages"][-1]
            if isinstance(ultima_msg, AIMessage):
                # Guarda sempre o último conteúdo, mesmo que seja tool_call
                if ultima_msg.content:
                    ultimo_conteudo = ultima_msg.content
                # Só considera resposta final se não for chamada de ferramenta
                if not ultima_msg.tool_calls and ultima_msg.content:
                    texto_final_ovidio = ultima_msg.content

        # Loga quando o nó de tools é executado
        if "tools" in output:
            log_msg = output["tools"]["messages"][-1]
            print(f"[Tools] Resultado: {str(log_msg.content)[:100]}...")

    # Prioriza resposta final, mas usa último conteúdo como fallback
    resposta = texto_final_ovidio or ultimo_conteudo

    if resposta:
        texto_limpo = re.sub(r'<[^>]+>', '', resposta).strip()
        msg_resposta.content = texto_limpo
        await msg_resposta.update()
    else:
        msg_resposta.content = "As musas permaneceram em silêncio absoluto. Tente novamente."
        await msg_resposta.update()





""""
from imports import *
from main import app 

@cl.on_chat_start
async def start():
    await cl.Message(
        content="Olá, caro mortal! Sou Ovídio Naso. Pergunte-me sobre os deuses e as transformações do mundo, e consultarei as musas para ti."
    ).send()
    cl.user_session.set("thread_id", cl.user_session.get("id"))

@cl.on_message
async def main(message: cl.Message):
    thread_id = cl.user_session.get("thread_id")
    config = {"configurable": {"thread_id": thread_id}}
    
    inputs = {
        "messages": [HumanMessage(content=message.content)],
        "revision_count": 0
    }

    # Placeholder
    msg_resposta = cl.Message(content="⏳ Ovídio está consultando os pergaminhos e debatendo com os escribas...")
    await msg_resposta.send()

    texto_final_ovidio = None

    async for output in app.astream(inputs, config=config, stream_mode="updates"):

        #Se for o nó do ovidio, guarda o texto na variável, mas não mostra ainda
        if "ovidio" in output:
            ultima_msg = output["ovidio"]["messages"][-1]
            if isinstance(ultima_msg, AIMessage) and not ultima_msg.tool_calls:
                texto_final_ovidio = ultima_msg.content
        
        # Se for o nó do Juiz, ignora
    if texto_final_ovidio:
        #Remove tags XML vazadas pelo modelo
        texto_limpo = re.sub(r'<[^>]+>', '', texto_final_ovidio).strip()
        msg_resposta.content = texto_limpo
        await msg_resposta.update()
    else:
        msg_resposta.content = "As musas permaneceram em silêncio absoluto. Tente novamente."
        await msg_resposta.update()

"""""
        
# chainlit run interface.py -w
# python -m chainlit run interface.py -w