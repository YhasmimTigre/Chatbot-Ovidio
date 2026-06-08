from dotenv import load_dotenv
load_dotenv()
from imports import *
from DB import criar_banco

PASTA_MONITORADA = "./historia"

class MeuVigia(FileSystemEventHandler):
    def on_created(self, event):

        if not event.is_directory and event.src_path.endswith(".pdf"):
            print(f"\n[VIGIA] Novo arquivo detectado: {event.src_path}")
            print("[VIGIA] Atualizando o conhecimento das Musas...")
            try:
                criar_banco()
                print("Banco atualizado com sucesso!")
            except Exception as e:
                print(f"ERRO: Falha ao atualizar banco: {e}")

if __name__ == "__main__":
    if not os.path.exists(PASTA_MONITORADA):
        os.makedirs(PASTA_MONITORADA)

    event_handler = MeuVigia()
    observer = Observer()
    observer.schedule(event_handler, path=PASTA_MONITORADA, recursive=False)
    
    print(f"Observando a pasta '{PASTA_MONITORADA}'.")
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()