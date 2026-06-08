from dotenv import load_dotenv
load_dotenv()
from imports import *

from logger import configurar_logger
log = configurar_logger("DB")

PASTA_PDFS = "./historia"
PASTA_BANCO = "./banco_mitologia"

# DB.py — substitui a função criar_banco() completa

import json

ARQUIVO_CONTROLE = "./banco_mitologia/arquivos_processados.json"

def carregar_arquivos_processados():
    if os.path.exists(ARQUIVO_CONTROLE):
        with open(ARQUIVO_CONTROLE, 'r', encoding='utf-8') as f:
            return set(json.load(f))
    return set()

def salvar_arquivos_processados(arquivos: set):
    os.makedirs(os.path.dirname(ARQUIVO_CONTROLE), exist_ok=True)
    with open(ARQUIVO_CONTROLE, 'w', encoding='utf-8') as f:
        json.dump(list(arquivos), f, ensure_ascii=False, indent=2)

def criar_banco():
    log.info("Verificando atualizações no banco de dados")

    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    vectorstore = Chroma(
        persist_directory=PASTA_BANCO,
        embedding_function=embeddings,
        collection_name="mitologia_db"
    )

    # Carrega controle de arquivos já processados
    arquivos_processados = carregar_arquivos_processados()
    log.info(f"Arquivos já no banco: {len(arquivos_processados)}")

    novos_docs = []
    arquivos_novos = set()

    if os.path.exists(PASTA_PDFS):
        for arquivo in os.listdir(PASTA_PDFS):
            if arquivo.endswith('.pdf'):
                caminho_absoluto = os.path.abspath(os.path.join(PASTA_PDFS, arquivo))

                if caminho_absoluto not in arquivos_processados:
                    log.info(f"Lendo novo arquivo: {arquivo}")
                    try:
                        loader = PyPDFLoader(caminho_absoluto)
                        docs = loader.load()
                        novos_docs.extend(docs)
                        arquivos_novos.add(caminho_absoluto)
                    except Exception as e:
                        log.error(f"Falha ao carregar {arquivo}: {e}")
                        continue
                else:
                    log.debug(f"Já processado, ignorando: {arquivo}")

    if novos_docs:
        log.info(f"Processando {len(novos_docs)} novas páginas...")

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=256,
            chunk_overlap=50,
            separators=["\n\n", "\n", ".", " ", ""]
        )
        chunks = text_splitter.split_documents(novos_docs)

        if chunks:
            total_chunks = len(chunks)
            log.info(f"Total de chunks gerados: {total_chunks}")

            BATCH_SIZE = 4000
            for i in range(0, total_chunks, BATCH_SIZE):
                batch = chunks[i: i + BATCH_SIZE]
                log.info(f"Inserindo lote {i} até {i + len(batch)} de {total_chunks}...")
                vectorstore.add_documents(batch)
                time.sleep(0.1)

            # Só salva o controle após inserção bem-sucedida
            arquivos_processados.update(arquivos_novos)
            salvar_arquivos_processados(arquivos_processados)
            log.info("Atualização concluída com sucesso")
    else:
        log.info("Banco já atualizado, nenhum arquivo novo")
            

def carregar_banco():
    print("--- Carregando Banco Vetorial Local ---")
    
    try:
        log.info("Carregando banco vetorial local")
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        vectorstore = Chroma(
            persist_directory=PASTA_BANCO,
            embedding_function=embeddings,
            collection_name="mitologia_db"
        )
        log.info("Banco carregado com sucesso")
        return vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={'k': 5, 'fetch_k': 10, 'lambda_mult': 0.7}
        )
    except Exception as e:
        log.error(f"Falha crítica ao carregar o banco: {e}")
        raise RuntimeError("Não foi possível carregar o banco vetorial.") from e


criar_banco()