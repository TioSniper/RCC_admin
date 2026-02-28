import json
import os
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path

LOGS_DIR = Path(os.environ.get("LOCALAPPDATA")) / "RCC" / "logs"
LOGS_FILE = LOGS_DIR / "admin_logs.json"

_MENSAGENS = {
    # Usuários
    "criar_usuario": lambda d: f"Usuário '{d.get('username','?')}' criado",
    "deletar_usuario": lambda d: f"Usuário '{d.get('username','?')}' deletado",
    "ativar_usuario": lambda d: f"Usuário '{d.get('username','?')}' ativado",
    "desativar_usuario": lambda d: f"Usuário '{d.get('username','?')}' desativado",
    "resetar_senha": lambda d: f"Senha de '{d.get('username','?')}' resetada",
    "editar_username": lambda d: f"Username alterado para '{d.get('username','?')}'",
    # Assinaturas
    "atribuir_plano": lambda d: f"Plano '{d.get('plano', d.get('plano_nome','?'))}' atribuído a '{d.get('username','?')}' — {d.get('dias') or '∞'} dias",
    "mudar_plano": lambda d: f"Plano de '{d.get('username','?')}' alterado para '{d.get('plano', d.get('plano_nome','?'))}' — {d.get('dias') or '∞'} dias",
    "renovar_assinatura": lambda d: f"Assinatura '{d.get('plano','?')}' de '{d.get('username','?')}' renovada +{d.get('dias_adicionados','?')} dias (era: {d.get('expiracao_anterior','?')} → nova: {d.get('nova_expiracao','?')})",
    "revogar_assinatura": lambda d: f"Plano de '{d.get('username','?')}' revogado de '{d.get('plano_anterior','?')}' → Básico",
    "revogar_para_basico": lambda d: f"Plano de '{d.get('username','?')}' revogado de '{d.get('plano_anterior', d.get('plano','?'))}' → Básico",
    # Planos
    "criar_plano": lambda d: f"Plano '{d.get('nome','?')}' criado",
    "editar_plano": lambda d: f"Plano '{d.get('nome','?')}' editado",
    "excluir_plano": lambda d: f"Plano '{d.get('nome','?')}' excluído",
    "ativar_plano": lambda d: f"Plano '{d.get('nome','?')}' ativado",
    "desativar_plano": lambda d: f"Plano '{d.get('nome','?')}' desativado",
    # Módulos
    "criar_modulo": lambda d: f"Módulo '{d.get('nome', d.get('modulo','?'))}' criado",
    "editar_modulo": lambda d: f"Módulo '{d.get('nome', d.get('modulo','?'))}' editado",
    "excluir_modulo": lambda d: f"Módulo '{d.get('modulo_id','?')}' excluído",
    "ativar_modulo": lambda d: f"Módulo '{d.get('modulo','?')}' ativado",
    "desativar_modulo": lambda d: f"Módulo '{d.get('modulo','?')}' desativado",
    # Solicitações
    "aprovar_solicitacao": lambda d: f"Solicitação de '{d.get('username','?')}' aprovada",
    "rejeitar_solicitacao": lambda d: f"Solicitação de '{d.get('username','?')}' rejeitada",
    # Update
    "disparar_update": lambda d: f"Notificação de update disparada para clientes",
    # Alias RPC
    "revogar_assinatura_admin": lambda d: f"Plano de '{d.get('username','?')}' revogado → Básico",
}


def _formatar_detalhe(acao: str, detalhes: dict) -> str:
    fn = _MENSAGENS.get(acao)
    if fn:
        try:
            return fn(detalhes)
        except Exception:
            pass
    # Fallback legível
    partes = [
        str(v)
        for k, v in (detalhes or {}).items()
        if v and k not in ("plano_id", "modulo_id", "user_id")
    ]
    return ", ".join(partes) if partes else "—"


class GerenciadorLogs:
    def __init__(self):
        self._lock = threading.Lock()
        self._listeners = []  # callbacks para notificar mudança
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
            "criado_em": (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat(),
            "acao": acao,
            "username": username,
            "detalhes": _formatar_detalhe(acao, detalhes),
        }
        threading.Thread(target=self._salvar, args=(entrada,), daemon=True).start()

    def _salvar(self, entrada: dict):
        with self._lock:
            try:
                dados = json.loads(LOGS_FILE.read_text(encoding="utf-8"))
                dados.insert(0, entrada)
                LOGS_FILE.write_text(
                    json.dumps(dados[:5000], ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                # Notifica listeners para atualizar a tela
                for cb in self._listeners:
                    try:
                        cb()
                    except Exception:
                        pass
            except Exception as e:
                print(f"[Logs] Erro ao salvar: {e}")

    def listar(self, limite: int = 200) -> list:
        with self._lock:
            try:
                dados = json.loads(LOGS_FILE.read_text(encoding="utf-8"))
                return dados[:limite]
            except Exception:
                return []

    def on_novo_log(self, callback):
        """Registra callback chamado sempre que um novo log é salvo."""
        self._listeners.append(callback)

    def forcar_salvar(self):
        pass


_logs = GerenciadorLogs()
