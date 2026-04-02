import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
DB_DIR = DATA_DIR / "db"
SQLITE_DB = DB_DIR / "teardown.db"
CHROMA_DIR = DB_DIR / "chroma"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DB_DIR.mkdir(parents=True, exist_ok=True)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.2:3b")
VISION_MODEL = os.getenv("VISION_MODEL", "moondream")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")

CHUNK_SIZE = 256
CHUNK_OVERLAP = 32
TOP_K = 8

SUPPORTED_EXTENSIONS = {
    "pdf", "png", "jpg", "jpeg", "gif", "bmp", "tiff", "svg",
    "txt", "md", "csv", "json", "xml", "html", "htm",
    "py", "c", "cpp", "h", "hpp", "rs", "js", "ts", "java", "go", "sh",
    "yaml", "yml", "toml", "ini", "cfg", "conf", "log",
}

IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "bmp", "tiff"}
