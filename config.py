import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL         = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
ADMIN_SENHA_MASTER   = os.getenv("ADMIN_SENHA_MASTER")

APP_NOME    = "RCC Admin"
APP_VERSAO  = "1.0.0"

# Cores padrão
COR_FUNDO_1    = "#1a2854"
COR_FUNDO_2    = "#0a1228"
COR_DOURADO    = "#FFD700"
COR_MENU       = "rgba(15, 26, 61, 0.9)"
COR_BARRA_TOPO = "rgba(15, 26, 61, 0.8)"
