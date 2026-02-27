import os
import time
import threading
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
BASICO_ID = os.getenv("PLANO_BASICO_ID", "11111111-1111-1111-1111-111111111111")


def _cliente() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


# ═══════════════════════════════════════════════════════════════
# LOGS — arquivo JSON local via logs_manager
# ═══════════════════════════════════════════════════════════════

try:
    from utils.logs_manager import _logs
except ImportError:
    # fallback: objeto mudo para não quebrar imports
    class _LogsMudo:
        def registrar(self, *a, **kw):
            pass

        def forcar_salvar(self):
            pass

        def listar(self, limite=200):
            return []

    _logs = _LogsMudo()


# ═══════════════════════════════════════════════════════════════
# MÓDULOS
# ═══════════════════════════════════════════════════════════════


def listar_modulos() -> list:
    try:
        return _cliente().table("modulos").select("*").order("nome").execute().data
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
        _logs.registrar("criar_modulo", detalhes={"nome": nome, "modulo": id_modulo})
        return True, "Módulo criado."
    except Exception as e:
        return False, f"Erro: {e}"


def editar_modulo(id_modulo: str, nome: str, descricao: str) -> tuple[bool, str]:
    try:
        _cliente().table("modulos").update({"nome": nome, "descricao": descricao}).eq(
            "id", id_modulo
        ).execute()
        _logs.registrar("editar_modulo", detalhes={"nome": nome, "modulo": id_modulo})
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


def excluir_modulo(modulo_id: str) -> tuple[bool, str]:
    try:
        vinculado = (
            _cliente()
            .table("planos_modulos")
            .select("plano_id")
            .eq("modulo_id", modulo_id)
            .execute()
        )
        if vinculado.data:
            return (
                False,
                "Módulo vinculado a um ou mais planos. Remova-o dos planos antes.",
            )
        _cliente().table("modulos").delete().eq("id", modulo_id).execute()
        _logs.registrar("excluir_modulo", detalhes={"modulo_id": modulo_id})
        return True, "Módulo excluído."
    except Exception as e:
        return False, str(e)


# ═══════════════════════════════════════════════════════════════
# PLANOS
# ═══════════════════════════════════════════════════════════════


def listar_planos() -> list:
    try:
        return (
            _cliente()
            .table("planos")
            .select("*, planos_modulos(modulo_id)")
            .order("nome")
            .execute()
            .data
        )
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
        _logs.registrar("editar_plano", detalhes={"nome": nome})
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
        _logs.registrar("ativar_plano" if ativo else "desativar_plano", detalhes={})
        return True, "Plano atualizado."
    except Exception as e:
        return False, f"Erro: {e}"


def excluir_plano(plano_id: str) -> bool:
    try:
        _cliente().table("planos_modulos").delete().eq("plano_id", plano_id).execute()
        _cliente().table("planos").delete().eq("id", plano_id).execute()
        _logs.registrar("excluir_plano", detalhes={})
        return True
    except Exception as e:
        print(f"Erro ao excluir plano: {e}")
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
                .neq("plano_id", BASICO_ID)
                .order("criado_em", desc=True)
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
        _logs.registrar("criar_usuario", detalhes={"username": username})
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
        _logs.registrar("editar_username", detalhes={"username": novo_username})
        return True, "Username atualizado."
    except Exception as e:
        return False, f"Erro: {e}"


def ativar_usuario(user_id: str) -> tuple[bool, str]:
    try:
        _cliente().auth.admin.update_user_by_id(user_id, {"ban_duration": "none"})
        _cliente().table("perfis").update({"ativo": True}).eq("id", user_id).execute()
        _logs.registrar("ativar_usuario", detalhes={"user_id": user_id})
        return True, "Usuário ativado."
    except Exception as e:
        return False, f"Erro: {e}"


def desativar_usuario(user_id: str) -> tuple[bool, str]:
    try:
        # 1. Ban no Auth — bloqueia novos logins e invalida sessão
        _cliente().auth.admin.update_user_by_id(user_id, {"ban_duration": "876000h"})
        # 2. Marca perfil como inativo — NÃO toca em assinaturas
        _cliente().table("perfis").update({"ativo": False}).eq("id", user_id).execute()
        _logs.registrar("desativar_usuario", detalhes={"user_id": user_id})
        return True, "Usuário desativado."
    except Exception as e:
        print(f"[desativar_usuario] ERRO: {e}")
        return False, f"Erro: {e}"


def resetar_senha(user_id: str, nova_senha: str) -> tuple[bool, str]:
    try:
        _cliente().auth.admin.update_user_by_id(user_id, {"password": nova_senha})
        _logs.registrar("resetar_senha", detalhes={"user_id": user_id})
        return True, "Senha resetada."
    except Exception as e:
        return False, f"Erro: {e}"


def deletar_usuario(user_id: str) -> tuple[bool, str]:
    try:
        _cliente().auth.admin.delete_user(user_id)
        _logs.registrar("deletar_usuario", detalhes={"user_id": user_id})
        return True, "Usuário deletado."
    except Exception as e:
        return False, f"Erro: {e}"


# ═══════════════════════════════════════════════════════════════
# SESSÕES
# ═══════════════════════════════════════════════════════════════


def listar_sessoes_ativas() -> list:
    try:
        return _cliente().table("sessoes_ativas").select("user_id").execute().data
    except Exception as e:
        print(f"Erro ao listar sessões: {e}")
        return []


# ═══════════════════════════════════════════════════════════════
# ASSINATURAS
# ═══════════════════════════════════════════════════════════════


def listar_assinaturas() -> list:
    try:
        return (
            _cliente()
            .table("v_assinaturas")
            .select("*")
            .eq("ativo", True)
            .neq("plano_id", BASICO_ID)
            .order("criado_em", desc=True)
            .execute()
            .data
        )
    except Exception as e:
        print(f"Erro ao listar assinaturas: {e}")
        return []


def renovar_assinatura(user_id: str, dias: int) -> tuple[bool, str]:
    try:
        _cliente().rpc(
            "renovar_assinatura_admin", {"p_user_id": user_id, "p_dias": dias}
        ).execute()
        _logs.registrar(
            "renovar_assinatura", detalhes={"user_id": user_id, "dias": dias}
        )
        return True, f"Renovada por mais {dias} dias."
    except Exception as e:
        return False, f"Erro: {e}"


def revogar_assinatura(user_id: str) -> tuple[bool, str]:
    try:
        _cliente().rpc("revogar_para_basico", {"p_user_id": user_id}).execute()
        _logs.registrar("revogar_assinatura", detalhes={"user_id": user_id})
        return True, "Assinatura revogada."
    except Exception as e:
        return False, f"Erro: {e}"


# ═══════════════════════════════════════════════════════════════
# SOLICITAÇÕES
# ═══════════════════════════════════════════════════════════════


def listar_solicitacoes() -> list:
    try:
        return (
            _cliente()
            .table("solicitacoes")
            .select("*")
            .eq("status", "pendente")
            .order("criado_em")
            .execute()
            .data
        )
    except Exception as e:
        print(f"Erro ao listar solicitações: {e}")
        return []


def aprovar_solicitacao(sol_id: str, username: str, dias: int) -> tuple[bool, str]:
    try:
        sol = (
            _cliente()
            .table("solicitacoes")
            .select("*")
            .eq("id", sol_id)
            .single()
            .execute()
        )
        email = sol.data["email"]
        response = _cliente().auth.admin.create_user(
            {
                "email": email,
                "password": "Trocar@123",
                "email_confirm": True,
            }
        )
        user_id = response.user.id
        _cliente().table("perfis").update({"username": username.lower().strip()}).eq(
            "id", user_id
        ).execute()
        _cliente().table("solicitacoes").update({"status": "aprovado"}).eq(
            "id", sol_id
        ).execute()
        _logs.registrar("aprovar_solicitacao", detalhes={"username": username})
        return True, f"Usuário '{username}' aprovado."
    except Exception as e:
        return False, f"Erro: {e}"


def rejeitar_solicitacao(sol_id: str) -> tuple[bool, str]:
    try:
        _cliente().table("solicitacoes").update({"status": "rejeitado"}).eq(
            "id", sol_id
        ).execute()
        _logs.registrar("rejeitar_solicitacao", detalhes={})
        return True, "Solicitação rejeitada."
    except Exception as e:
        return False, f"Erro: {e}"


# ═══════════════════════════════════════════════════════════════
# RELATÓRIOS
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
            .neq("plano_id", BASICO_ID)
            .execute()
            .data
        )
        expirando = len(
            _cliente()
            .table("assinaturas")
            .select("id")
            .eq("ativo", True)
            .neq("plano_id", BASICO_ID)
            .lte("expira_em", em_7_dias)
            .gte("expira_em", agora_iso)
            .execute()
            .data
        )
        expiradas = len(
            _cliente()
            .table("assinaturas")
            .select("id")
            .eq("ativo", False)
            .neq("plano_id", BASICO_ID)
            .not_.is_("expira_em", "null")
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
        return (
            _cliente()
            .table("v_assinaturas")
            .select("*")
            .eq("ativo", True)
            .neq("plano_id", BASICO_ID)
            .lte("expira_em", em_x_dias)
            .gte("expira_em", agora_iso)
            .order("expira_em")
            .execute()
            .data
        )
    except Exception as e:
        print(f"Erro expirando: {e}")
        return []


# ═══════════════════════════════════════════════════════════════
# LOGS
# ═══════════════════════════════════════════════════════════════


def listar_logs(limite: int = 200) -> list:
    return _logs.listar(limite)
