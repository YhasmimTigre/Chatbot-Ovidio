from imports import *
from logger import configurar_logger
log = configurar_logger("tools")

_busca = None

def inicializar_retriever(retriever):
    global _busca
    _busca = retriever


@tool
def consultar_musas(termo_busca: str) -> str:
    """
    Use esta ferramenta para buscar informações sobre mitologia, deuses, lendas, heróis ou criaturas.
    Sempre que a pergunta for sobre esses temas, use esta ferramenta para encontrar a resposta no banco de dados.
    """
    log.info(f"RAG: Consultando as musas sobre '{termo_busca}'")

    if _busca is None:
        log.error("Retriever não foi inicializado!")
        return "As musas não foram invocadas corretamente. O oráculo está offline."

    try:
        docs = _busca.invoke(termo_busca)
    except Exception as e:
        log.error(f"Falha na busca vetorial: {e}")
        return "As musas estão em silêncio — houve uma falha ao consultar os pergaminhos."
    if not docs:
        return "As musas permaneceram em silêncio. Nenhuma informação foi encontrada sobre este mito."


    conteudo_texto = []

    for i, d in enumerate(docs):
        caminho_completo = d.metadata.get('source', 'Pergaminho Desconhecido')
        nome_arquivo = os.path.basename(caminho_completo).replace('.pdf', '').replace('-', ' ').replace('_', ' ')
        pagina = d.metadata.get('page', '?')
        
        trecho = f"[Pergaminho: '{nome_arquivo}' | Página {pagina}]\n{d.page_content}"
        conteudo_texto.append(trecho)
        log.debug(f"Fonte {i+1}: {nome_arquivo}, página {pagina}")

    return "\n\n---\n\n".join(conteudo_texto)
    

@tool
def assunto_desconhecido(assunto: str) -> str:
    """
    Use esta ferramenta quando o usuário perguntar sobre qualquer tema que NÃO seja mitologia 
    da antiguidade clássica ou tradicional (greco-romana, nórdica, egípcia, celta, árabe, hindu, 
    japonesa, chinesa, asteca).
    
    Exemplos de quando usar: folclore brasileiro (saci-pereré, curupira, boto cor-de-rosa), 
    tecnologia, esportes, política, música moderna, cinema, matemática, programação.
    
    O input deve ser o tema que o usuário tentou abordar.
    """
    log.warning(f"Bloqueio: usuário tentou falar sobre '{assunto}'")
    return (
        f"Perdoe-me, caro amigo. Minha sabedoria limita-se às eras antigas e aos feitos dos deuses. "
        f"Não possuo conhecimento sobre '{assunto}', pois isso pertence a um mundo além do meu."
    )  

@tool
def atualizar_conhecimento() -> str:
    """
    Use esta ferramenta APENAS se o usuário pedir explicitamente para 'ler novos livros' 
    ou 'atualizar a biblioteca'.
    """
    from DB import criar_banco
    criar_banco()
    return "As musas absorveram os novos pergaminhos com sucesso."