"""
GerenciadorLogs — armazena logs localmente em JSON.
Arquivo: utils/logs_manager.py
"""

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

# Pasta: mesma pasta do executável / projeto
local = os.environ.get("LOCALAPPDATA")
LOGS_DIR = Path(local) / "RCC"
LOGS_FILE = LOGS_DIR / "admin_logs.json"

# Mensagens legíveis por ação
_MENSAGENS = {
    # Usuários
    "criar_usuario": lambda d: f"Novo usuário criado: {d.get('username','?')}",
    "deletar_usuario": lambda d: f"Usuário deletado",
    "ativar_usuario": lambda d: f"Usuário ativado",
    "desativar_usuario": lambda d: f"Usuário desativado",
    "resetar_senha": lambda d: f"Senha resetada",
    "editar_username": lambda d: f"Username alterado",
    # Assinaturas
    "atribuir_plano": lambda d: f"Plano '{d.get('plano_nome','?')}' atribuído — {d.get('dias',0) or '∞'} dias",
    "renovar_assinatura": lambda d: f"Assinatura renovada por {d.get('dias','?')} dias",
    "revogar_assinatura": lambda d: f"Assinatura revogada → plano básico",
    # Planos
    "criar_plano": lambda d: f"Plano criado: {d.get('nome','?')}",
    "editar_plano": lambda d: f"Plano editado: {d.get('nome','?')}",
    "excluir_plano": lambda d: f"Plano excluído",
    "ativar_plano": lambda d: f"Plano ativado",
    "desativar_plano": lambda d: f"Plano desativado",
    # Módulos
    "criar_modulo": lambda d: f"Módulo criado: {d.get('nome', d.get('modulo','?'))}",
    "editar_modulo": lambda d: f"Módulo editado: {d.get('nome', d.get('modulo','?'))}",
    "excluir_modulo": lambda d: f"Módulo excluído: {d.get('modulo_id','?')}",
    "ativar_modulo": lambda d: f"Módulo ativado: {d.get('modulo','?')}",
    "desativar_modulo": lambda d: f"Módulo desativado: {d.get('modulo','?')}",
    # Solicitações
    "aprovar_solicitacao": lambda d: f"Solicitação aprovada: {d.get('username','?')}",
    "rejeitar_solicitacao": lambda d: f"Solicitação rejeitada",
}


def _formatar_detalhe(acao: str, detalhes: dict) -> str:
    fn = _MENSAGENS.get(acao)
    if fn:
        try:
            return fn(detalhes)
        except Exception:
            pass
    # Fallback legível: só mostra valores relevantes
    partes = []
    for k, v in (detalhes or {}).items():
        if v and k not in ("plano_id", "modulo_id", "user_id"):
            partes.append(str(v))
    return ", ".join(partes) if partes else "—"


class GerenciadorLogs:
    def __init__(self):
        self._lock = threading.Lock()
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        if not LOGS_FILE.exists():
            LOGS_FILE.write_text("[]", encoding="utf-8")

    def registrar(
        self,
        acao: str,
        username: str = "admin",
        user_id: str = None,
        detalhes: dict = None,
    ):
        detalhes = detalhes or {}
        entrada = {
            "criado_em": datetime.now(timezone.utc).isoformat(),
            "acao": acao,
            "username": username,
            "detalhes": _formatar_detalhe(acao, detalhes),
        }
        threading.Thread(target=self._salvar, args=(entrada,), daemon=True).start()

    def _salvar(self, entrada: dict):
        with self._lock:
            try:
                dados = json.loads(LOGS_FILE.read_text(encoding="utf-8"))
                dados.insert(0, entrada)  # mais recente primeiro
                # Mantém só os últimos 5000 registros para não crescer infinito
                LOGS_FILE.write_text(
                    json.dumps(dados[:5000], ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            except Exception as e:
                print(f"[Logs] Erro ao salvar: {e}")

    def listar(self, limite: int = 200) -> list:
        with self._lock:
            try:
                dados = json.loads(LOGS_FILE.read_text(encoding="utf-8"))
                return dados[:limite]
            except Exception:
                return []

    def forcar_salvar(self):
        pass  # compatibilidade — JSON é síncrono, não precisa forçar


_logs = GerenciadorLogs()
