import logging
import os

def configurar_logger(nome: str) -> logging.Logger:
    logger = logging.getLogger(nome)
    
    if logger.handlers:
        return logger

    nivel = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, nivel, logging.INFO))

    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger