import os
import time
import threading
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")


def _cliente() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


# ═══════════════════════════════════════════════════════════════
# LOGS EM LOTE
# ═══════════════════════════════════════════════════════════════


class GerenciadorLogs:
    def __init__(self):
        self._fila = []
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def registrar(self, acao: str, user_id: str = None, detalhes: dict = None):
        with self._lock:
            self._fila.append(
                {
                    "acao": acao,
                    "user_id": user_id,
                    "detalhes": detalhes or {},
                }
            )

    def _loop(self):
        while True:
            time.sleep(300)
            self._salvar_lote()

    def _salvar_lote(self):
        with self._lock:
            if not self._fila:
                return
            lote = self._fila.copy()
            self._fila.clear()
        try:
            _cliente().table("logs_admin").insert(lote).execute()
        except Exception as e:
            print(f"Erro ao salvar logs: {e}")

    def forcar_salvar(self):
        self._salvar_lote()


_logs = GerenciadorLogs()


# ═══════════════════════════════════════════════════════════════
# MÓDULOS
# ═══════════════════════════════════════════════════════════════


def listar_modulos() -> list:
    try:
        r = _cliente().table("modulos").select("*").order("nome").execute()
        return r.data
    except Exception as e:
        print(f"Erro ao listar módulos: {e}")
        return []


def criar_modulo(id_modulo: str, nome: str, descricao: str = "") -> tuple[bool, str]:
    try:
        _cliente().table("modulos").insert(
            {
                "id": id_modulo.lower().replace(" ", "_"),
                "nome": nome,
                "descricao": descricao,
                "ativo": True,
            }
        ).execute()
        _logs.registrar("criar_modulo", detalhes={"modulo": id_modulo})
        return True, "Módulo criado."
    except Exception as e:
        return False, f"Erro: {e}"


def editar_modulo(id_modulo: str, nome: str, descricao: str) -> tuple[bool, str]:
    try:
        _cliente().table("modulos").update({"nome": nome, "descricao": descricao}).eq(
            "id", id_modulo
        ).execute()
        _logs.registrar("editar_modulo", detalhes={"modulo": id_modulo})
        return True, "Módulo atualizado."
    except Exception as e:
        return False, f"Erro: {e}"


def ativar_modulo(id_modulo: str, ativo: bool) -> tuple[bool, str]:
    try:
        _cliente().table("modulos").update({"ativo": ativo}).eq(
            "id", id_modulo
        ).execute()
        _logs.registrar(
            "ativar_modulo" if ativo else "desativar_modulo",
            detalhes={"modulo": id_modulo},
        )
        return True, "Módulo atualizado."
    except Exception as e:
        return False, f"Erro: {e}"


# ═══════════════════════════════════════════════════════════════
# PLANOS
# ═══════════════════════════════════════════════════════════════


def listar_planos() -> list:
    try:
        r = (
            _cliente()
            .table("planos")
            .select("*, planos_modulos(modulo_id)")
            .order("nome")
            .execute()
        )
        return r.data
    except Exception as e:
        print(f"Erro ao listar planos: {e}")
        return []


def criar_plano(nome: str, descricao: str, modulos: list) -> tuple[bool, str]:
    try:
        r = (
            _cliente()
            .table("planos")
            .insert({"nome": nome, "descricao": descricao, "ativo": True})
            .execute()
        )
        plano_id = r.data[0]["id"]
        if modulos:
            _cliente().table("planos_modulos").insert(
                [{"plano_id": plano_id, "modulo_id": m} for m in modulos]
            ).execute()
        _logs.registrar("criar_plano", detalhes={"nome": nome})
        return True, "Plano criado."
    except Exception as e:
        return False, f"Erro: {e}"


def editar_plano(plano_id: str, nome: str, descricao: str) -> tuple[bool, str]:
    try:
        _cliente().table("planos").update({"nome": nome, "descricao": descricao}).eq(
            "id", plano_id
        ).execute()
        _logs.registrar("editar_plano", detalhes={"plano_id": plano_id})
        return True, "Plano atualizado."
    except Exception as e:
        return False, f"Erro: {e}"


def adicionar_modulo_plano(plano_id: str, modulo_id: str) -> tuple[bool, str]:
    try:
        _cliente().table("planos_modulos").insert(
            {"plano_id": plano_id, "modulo_id": modulo_id}
        ).execute()
        return True, "Módulo adicionado."
    except Exception as e:
        return False, f"Erro: {e}"


def remover_modulo_plano(plano_id: str, modulo_id: str) -> tuple[bool, str]:
    try:
        _cliente().table("planos_modulos").delete().eq("plano_id", plano_id).eq(
            "modulo_id", modulo_id
        ).execute()
        return True, "Módulo removido."
    except Exception as e:
        return False, f"Erro: {e}"


def ativar_plano(plano_id: str, ativo: bool) -> tuple[bool, str]:
    try:
        _cliente().table("planos").update({"ativo": ativo}).eq("id", plano_id).execute()
        return True, "Plano atualizado."
    except Exception as e:
        return False, f"Erro: {e}"


def excluir_plano(plano_id: str):
    try:
        _cliente().table("planos").delete().eq("id", plano_id).execute()

        return True
    except Exception as e:
        print("Erro ao excluir plano:", e)
        return False


# ═══════════════════════════════════════════════════════════════
# USUÁRIOS
# ═══════════════════════════════════════════════════════════════


def listar_usuarios() -> list:
    try:
        perfis = (
            _cliente()
            .table("perfis")
            .select("*")
            .order("criado_em", desc=True)
            .execute()
        )
        usuarios = []
        for p in perfis.data:
            ass = (
                _cliente()
                .table("v_assinaturas")
                .select("*")
                .eq("user_id", p["id"])
                .eq("ativo", True)
                .order("expira_em", desc=True)
                .limit(1)
                .execute()
            )
            p["assinatura"] = ass.data[0] if ass.data else None
            usuarios.append(p)
        return usuarios
    except Exception as e:
        print(f"Erro ao listar usuários: {e}")
        return []


def criar_usuario(username: str, senha: str) -> tuple[bool, str]:
    try:
        email = f"{username.lower().strip()}@rcc.app"
        response = _cliente().auth.admin.create_user(
            {
                "email": email,
                "password": senha,
                "email_confirm": True,
            }
        )
        user_id = response.user.id
        _cliente().table("perfis").update({"username": username.lower().strip()}).eq(
            "id", user_id
        ).execute()
        _logs.registrar("criar_usuario", user_id, {"username": username})
        return True, user_id
    except Exception as e:
        msg = str(e)
        if "already registered" in msg:
            return False, "Username já está em uso."
        return False, f"Erro: {msg}"


def editar_username(user_id: str, novo_username: str) -> tuple[bool, str]:
    try:
        _cliente().table("perfis").update(
            {"username": novo_username.lower().strip()}
        ).eq("id", user_id).execute()
        _logs.registrar("editar_username", user_id)
        return True, "Username atualizado."
    except Exception as e:
        return False, f"Erro: {e}"


def ativar_usuario(user_id: str) -> tuple[bool, str]:
    try:
        _cliente().table("perfis").update({"ativo": True}).eq("id", user_id).execute()
        _logs.registrar("ativar_usuario", user_id)
        return True, "Usuário ativado."
    except Exception as e:
        return False, f"Erro: {e}"


def desativar_usuario(user_id: str) -> tuple[bool, str]:
    try:
        _cliente().table("perfis").update({"ativo": False}).eq("id", user_id).execute()
        _logs.registrar("desativar_usuario", user_id)
        return True, "Usuário desativado."
    except Exception as e:
        return False, f"Erro: {e}"


def resetar_senha(user_id: str, nova_senha: str) -> tuple[bool, str]:
    try:
        _cliente().auth.admin.update_user_by_id(user_id, {"password": nova_senha})
        _logs.registrar("resetar_senha", user_id)
        return True, "Senha resetada."
    except Exception as e:
        return False, f"Erro: {e}"


def deletar_usuario(user_id: str) -> tuple[bool, str]:
    try:
        perfil = (
            _cliente().table("perfis").select("username").eq("id", user_id).execute()
        )
        username = perfil.data[0].get("username") if perfil.data else None
        if username:
            _cliente().table("solicitacoes").delete().eq("username", username).execute()
        _cliente().auth.admin.delete_user(user_id)
        _logs.registrar("deletar_usuario", user_id)
        return True, "Usuário deletado."
    except Exception as e:
        return False, f"Erro: {e}"


# ═══════════════════════════════════════════════════════════════
# ASSINATURAS
# ═══════════════════════════════════════════════════════════════


def listar_assinaturas() -> list:
    try:
        r = (
            _cliente()
            .table("v_assinaturas")
            .select("*")
            .eq("ativo", True)
            .order("expira_em")
            .execute()
        )
        return r.data
    except Exception as e:
        print(f"Erro ao listar assinaturas: {e}")
        return []


def historico_assinaturas(user_id: str) -> list:
    try:
        r = (
            _cliente()
            .table("v_assinaturas")
            .select("*")
            .eq("user_id", user_id)
            .order("criado_em", desc=True)
            .execute()
        )
        return r.data
    except Exception as e:
        print(f"Erro histórico: {e}")
        return []


def criar_assinatura(user_id: str, plano_id: str, dias: int) -> tuple[bool, str]:
    try:
        _cliente().table("assinaturas").update({"ativo": False}).eq(
            "user_id", user_id
        ).eq("ativo", True).execute()
        _cliente().rpc(
            "criar_assinatura_admin",
            {
                "p_user_id": user_id,
                "p_plano_id": plano_id,
                "p_dias": dias,
            },
        ).execute()
        _logs.registrar(
            "criar_assinatura", user_id, {"plano_id": plano_id, "dias": dias}
        )
        return True, "Assinatura criada."
    except Exception as e:
        return False, f"Erro: {e}"


def renovar_assinatura(user_id: str, dias: int) -> tuple[bool, str]:
    try:
        _cliente().rpc(
            "renovar_assinatura_admin",
            {
                "p_user_id": user_id,
                "p_dias": dias,
            },
        ).execute()
        _logs.registrar("renovar_assinatura", user_id, {"dias": dias})
        return True, f"Renovada por mais {dias} dias."
    except Exception as e:
        return False, f"Erro: {e}"


def revogar_assinatura(user_id: str) -> tuple[bool, str]:
    try:
        _cliente().table("assinaturas").update({"ativo": False}).eq(
            "user_id", user_id
        ).eq("ativo", True).execute()
        _logs.registrar("revogar_assinatura", user_id)
        return True, "Assinatura revogada."
    except Exception as e:
        return False, f"Erro: {e}"


def mudar_plano(user_id: str, novo_plano_id: str) -> tuple[bool, str]:
    try:
        _cliente().table("assinaturas").update(
            {
                "plano_id": novo_plano_id,
                "renovado_em": "now()",
            }
        ).eq("user_id", user_id).eq("ativo", True).execute()
        _logs.registrar("mudar_plano", user_id, {"novo_plano_id": novo_plano_id})
        return True, "Plano alterado."
    except Exception as e:
        return False, f"Erro: {e}"


# ═══════════════════════════════════════════════════════════════
# ACESSOS EXTRAS
# ═══════════════════════════════════════════════════════════════


def listar_acessos_extras() -> list:
    try:
        r = (
            _cliente()
            .table("v_acessos_extras")
            .select("*")
            .eq("ativo", True)
            .gte("expira_em", "now()")
            .order("expira_em")
            .execute()
        )
        return r.data
    except Exception as e:
        print(f"Erro ao listar acessos extras: {e}")
        return []


def dar_acesso_extra(user_id: str, modulo_id: str, horas: int) -> tuple[bool, str]:
    try:
        _cliente().rpc(
            "criar_acesso_extra_admin",
            {
                "p_user_id": user_id,
                "p_modulo_id": modulo_id,
                "p_horas": horas,
            },
        ).execute()
        _logs.registrar(
            "dar_acesso_extra", user_id, {"modulo_id": modulo_id, "horas": horas}
        )
        return True, f"Acesso extra de {horas}h concedido."
    except Exception as e:
        return False, f"Erro: {e}"


def revogar_acesso_extra(acesso_id: str, user_id: str) -> tuple[bool, str]:
    try:
        _cliente().table("acessos_extras").update({"ativo": False}).eq(
            "id", acesso_id
        ).execute()
        _logs.registrar("revogar_acesso_extra", user_id)
        return True, "Acesso extra revogado."
    except Exception as e:
        return False, f"Erro: {e}"


# ═══════════════════════════════════════════════════════════════
# RELATÓRIOS / DASHBOARD
# ═══════════════════════════════════════════════════════════════


def resumo_geral() -> dict:
    try:
        agora = datetime.now(timezone.utc)
        em_7_dias = (agora + timedelta(days=7)).isoformat()
        agora_iso = agora.isoformat()

        total = len(_cliente().table("perfis").select("id").execute().data)
        ativos = len(
            _cliente().table("perfis").select("id").eq("ativo", True).execute().data
        )
        ass_ativas = len(
            _cliente()
            .table("assinaturas")
            .select("id")
            .eq("ativo", True)
            .execute()
            .data
        )
        expirando = len(
            _cliente()
            .table("assinaturas")
            .select("id")
            .eq("ativo", True)
            .lte("expira_em", em_7_dias)
            .gte("expira_em", agora_iso)
            .execute()
            .data
        )
        expiradas = len(
            _cliente()
            .table("assinaturas")
            .select("id")
            .eq("ativo", True)
            .lt("expira_em", agora_iso)
            .execute()
            .data
        )

        return {
            "total_usuarios": total,
            "usuarios_ativos": ativos,
            "assinaturas_ativas": ass_ativas,
            "expirando_7_dias": expirando,
            "expiradas": expiradas,
        }
    except Exception as e:
        print(f"Erro resumo: {e}")
        return {}


def listar_expirando(dias: int = 7) -> list:
    try:
        agora = datetime.now(timezone.utc)
        em_x_dias = (agora + timedelta(days=dias)).isoformat()
        agora_iso = agora.isoformat()
        r = (
            _cliente()
            .table("v_assinaturas")
            .select("*")
            .eq("ativo", True)
            .lte("expira_em", em_x_dias)
            .gte("expira_em", agora_iso)
            .order("expira_em")
            .execute()
        )
        return r.data
    except Exception as e:
        print(f"Erro expirando: {e}")
        return []


# ═══════════════════════════════════════════════════════════════
# LOGS
# ═══════════════════════════════════════════════════════════════


def listar_sessoes_ativas() -> set:
    """Retorna set de user_ids com sessão ativa nos últimos 40 minutos."""
    try:
        from datetime import timedelta

        limite = (datetime.now(timezone.utc) - timedelta(minutes=40)).isoformat()
        r = (
            _cliente()
            .table("sessoes_ativas")
            .select("user_id")
            .gte("ultimo_ping", limite)
            .execute()
        )
        return {row["user_id"] for row in r.data}
    except Exception as e:
        print(f"Erro ao listar sessões ativas: {e}")
        return set()


def listar_logs(limite: int = 200) -> list:
    try:
        r = (
            _cliente()
            .table("v_logs_admin")
            .select("*")
            .order("criado_em", desc=True)
            .limit(limite)
            .execute()
        )
        return r.data
    except Exception as e:
        print(f"Erro ao listar logs: {e}")
        return []


# ═══════════════════════════════════════════════════════════════
# SOLICITAÇÕES DE CADASTRO
# ═══════════════════════════════════════════════════════════════


def listar_solicitacoes() -> list:
    try:
        r = (
            _cliente()
            .table("solicitacoes")
            .select("id, username, criado_em")
            .eq("status", "pendente")
            .order("criado_em")
            .execute()
        )
        return r.data
    except Exception as e:
        print(f"Erro ao listar solicitações: {e}")
        return []


def aprovar_solicitacao(sol_id: str, username: str, dias: int) -> tuple[bool, str]:
    """
    Aprovação atômica: se qualquer passo falhar após criar o usuário no Auth,
    o usuário é deletado automaticamente para evitar usuários fantasmas.
    """
    user_id = None
    try:
        # 1. Busca senha real
        sol = (
            _cliente()
            .table("solicitacoes")
            .select("senha_real")
            .eq("id", sol_id)
            .execute()
        )
        if not sol.data:
            return False, "Solicitação não encontrada."
        senha_real = sol.data[0].get("senha_real")
        if not senha_real:
            return False, "Dados da solicitação incompletos."

        # 2. Remove fantasma se existir (mesmo email já cadastrado)
        email = f"{username}@rcc.app"
        try:
            todos = _cliente().auth.admin.list_users()
            for u in todos:
                if u.email == email:
                    print(f"[Aprovação] Removendo fantasma: {email}")
                    _cliente().auth.admin.delete_user(u.id)
                    break
        except Exception:
            pass

        # 3. Cria usuário no Auth
        response = _cliente().auth.admin.create_user(
            {
                "email": email,
                "password": senha_real,
                "email_confirm": True,
            }
        )
        user_id = response.user.id

        # 4. Atualiza perfil
        _cliente().table("perfis").update({"username": username}).eq(
            "id", user_id
        ).execute()

        # 5. Cria assinatura (dias=0 = sem expiração)
        planos = _cliente().table("planos").select("id").eq("nome", "Basico").execute()
        if planos.data:
            _cliente().rpc(
                "criar_assinatura_admin",
                {
                    "p_user_id": user_id,
                    "p_plano_id": planos.data[0]["id"],
                    "p_dias": dias,
                },
            ).execute()

        # 6. Marca solicitação como aprovada e apaga senha
        _cliente().table("solicitacoes").update(
            {
                "status": "aprovado",
                "senha_real": None,
                "atualizado": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", sol_id).execute()

        _logs.registrar(
            "aprovar_solicitacao", user_id, {"username": username, "dias": dias}
        )
        return True, f"Usuário '{username}' aprovado com sucesso."

    except Exception as e:
        # ROLLBACK: deleta usuário do Auth se foi criado mas algo falhou depois
        if user_id:
            try:
                print(f"[Aprovação] Rollback: deletando {user_id} após falha")
                _cliente().auth.admin.delete_user(user_id)
            except Exception as del_err:
                print(f"[Aprovação] Erro no rollback: {del_err}")
        import traceback

        traceback.print_exc()
        return False, f"Erro: {e}"


def rejeitar_solicitacao(sol_id: str) -> tuple[bool, str]:
    try:
        _cliente().table("solicitacoes").update(
            {
                "status": "rejeitado",
                "senha_real": None,
                "atualizado": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", sol_id).execute()
        _logs.registrar("rejeitar_solicitacao", detalhes={"sol_id": sol_id})
        return True, "Solicitação rejeitada."
    except Exception as e:
        return False, f"Erro: {e}"
