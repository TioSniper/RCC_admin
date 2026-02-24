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
# CACHE
# ═══════════════════════════════════════════════════════════════


class Cache:
    def __init__(self, ttl: int = 60):
        self._dados = {}
        self._ts = {}
        self._ttl = ttl

    def get(self, chave: str):
        if chave not in self._dados:
            return None
        if time.time() - self._ts[chave] > self._ttl:
            del self._dados[chave]
            return None
        return self._dados[chave]

    def set(self, chave: str, valor):
        self._dados[chave] = valor
        self._ts[chave] = time.time()

    def invalidar(self, chave: str = None):
        if chave:
            self._dados.pop(chave, None)
            self._ts.pop(chave, None)
        else:
            self._dados.clear()
            self._ts.clear()


_cache = Cache(ttl=60)


# ═══════════════════════════════════════════════════════════════
# MÓDULOS
# ═══════════════════════════════════════════════════════════════


def listar_modulos() -> list:
    cached = _cache.get("modulos")
    if cached:
        return cached
    try:
        r = _cliente().table("modulos").select("*").order("nome").execute()
        _cache.set("modulos", r.data)
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
        _cache.invalidar("modulos")
        _logs.registrar("criar_modulo", detalhes={"modulo": id_modulo})
        return True, "Módulo criado."
    except Exception as e:
        return False, f"Erro: {e}"


def editar_modulo(id_modulo: str, nome: str, descricao: str) -> tuple[bool, str]:
    try:
        _cliente().table("modulos").update({"nome": nome, "descricao": descricao}).eq(
            "id", id_modulo
        ).execute()
        _cache.invalidar("modulos")
        _logs.registrar("editar_modulo", detalhes={"modulo": id_modulo})
        return True, "Módulo atualizado."
    except Exception as e:
        return False, f"Erro: {e}"


def ativar_modulo(id_modulo: str, ativo: bool) -> tuple[bool, str]:
    try:
        _cliente().table("modulos").update({"ativo": ativo}).eq(
            "id", id_modulo
        ).execute()
        _cache.invalidar("modulos")
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
    cached = _cache.get("planos")
    if cached:
        return cached
    try:
        r = (
            _cliente()
            .table("planos")
            .select("*, planos_modulos(modulo_id)")
            .order("nome")
            .execute()
        )
        _cache.set("planos", r.data)
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
        _cache.invalidar("planos")
        _logs.registrar("criar_plano", detalhes={"nome": nome})
        return True, "Plano criado."
    except Exception as e:
        return False, f"Erro: {e}"


def editar_plano(plano_id: str, nome: str, descricao: str) -> tuple[bool, str]:
    try:
        _cliente().table("planos").update({"nome": nome, "descricao": descricao}).eq(
            "id", plano_id
        ).execute()
        _cache.invalidar("planos")
        _logs.registrar("editar_plano", detalhes={"plano_id": plano_id})
        return True, "Plano atualizado."
    except Exception as e:
        return False, f"Erro: {e}"


def adicionar_modulo_plano(plano_id: str, modulo_id: str) -> tuple[bool, str]:
    try:
        _cliente().table("planos_modulos").insert(
            {"plano_id": plano_id, "modulo_id": modulo_id}
        ).execute()
        _cache.invalidar("planos")
        return True, "Módulo adicionado."
    except Exception as e:
        return False, f"Erro: {e}"


def remover_modulo_plano(plano_id: str, modulo_id: str) -> tuple[bool, str]:
    try:
        _cliente().table("planos_modulos").delete().eq("plano_id", plano_id).eq(
            "modulo_id", modulo_id
        ).execute()
        _cache.invalidar("planos")
        return True, "Módulo removido."
    except Exception as e:
        return False, f"Erro: {e}"


def ativar_plano(plano_id: str, ativo: bool) -> tuple[bool, str]:
    try:
        _cliente().table("planos").update({"ativo": ativo}).eq("id", plano_id).execute()
        _cache.invalidar("planos")
        return True, "Plano atualizado."
    except Exception as e:
        return False, f"Erro: {e}"


# ═══════════════════════════════════════════════════════════════
# USUÁRIOS
# ═══════════════════════════════════════════════════════════════


def listar_usuarios() -> list:
    cached = _cache.get("usuarios")
    if cached:
        return cached
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
        _cache.set("usuarios", usuarios)
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
        _cache.invalidar("usuarios")
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
        _cache.invalidar("usuarios")
        _logs.registrar("editar_username", user_id)
        return True, "Username atualizado."
    except Exception as e:
        return False, f"Erro: {e}"


def ativar_usuario(user_id: str) -> tuple[bool, str]:
    try:
        _cliente().table("perfis").update({"ativo": True}).eq("id", user_id).execute()
        _cache.invalidar("usuarios")
        _logs.registrar("ativar_usuario", user_id)
        return True, "Usuário ativado."
    except Exception as e:
        return False, f"Erro: {e}"


def desativar_usuario(user_id: str) -> tuple[bool, str]:
    try:
        _cliente().table("perfis").update({"ativo": False}).eq("id", user_id).execute()
        _cache.invalidar("usuarios")
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
        _cliente().auth.admin.delete_user(user_id)
        _cache.invalidar("usuarios")
        _logs.registrar("deletar_usuario", user_id)
        return True, "Usuário deletado."
    except Exception as e:
        return False, f"Erro: {e}"


# ═══════════════════════════════════════════════════════════════
# ASSINATURAS — usa v_assinaturas
# ═══════════════════════════════════════════════════════════════


def listar_assinaturas() -> list:
    cached = _cache.get("assinaturas")
    if cached:
        return cached
    try:
        r = (
            _cliente()
            .table("v_assinaturas")
            .select("*")
            .eq("ativo", True)
            .order("expira_em")
            .execute()
        )
        _cache.set("assinaturas", r.data)
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
        _cache.invalidar("assinaturas")
        _cache.invalidar("usuarios")
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
        _cache.invalidar("assinaturas")
        _cache.invalidar("usuarios")
        _logs.registrar("renovar_assinatura", user_id, {"dias": dias})
        return True, f"Renovada por mais {dias} dias."
    except Exception as e:
        return False, f"Erro: {e}"


def revogar_assinatura(user_id: str) -> tuple[bool, str]:
    try:
        _cliente().table("assinaturas").update({"ativo": False}).eq(
            "user_id", user_id
        ).eq("ativo", True).execute()
        _cache.invalidar("assinaturas")
        _cache.invalidar("usuarios")
        _logs.registrar("revogar_assinatura", user_id)
        return True, "Assinatura revogada."
    except Exception as e:
        return False, f"Erro: {e}"


def mudar_plano(user_id: str, novo_plano_id: str) -> tuple[bool, str]:
    try:
        _cliente().table("assinaturas").update(
            {"plano_id": novo_plano_id, "renovado_em": "now()"}
        ).eq("user_id", user_id).eq("ativo", True).execute()
        _cache.invalidar("assinaturas")
        _cache.invalidar("usuarios")
        _logs.registrar("mudar_plano", user_id, {"novo_plano_id": novo_plano_id})
        return True, "Plano alterado."
    except Exception as e:
        return False, f"Erro: {e}"


# ═══════════════════════════════════════════════════════════════
# ACESSOS EXTRAS — usa v_acessos_extras
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
            .execute()
            .data
        )

        expirando = (
            _cliente()
            .table("assinaturas")
            .select("id")
            .eq("ativo", True)
            .lte("expira_em", em_7_dias)
            .gte("expira_em", agora_iso)
            .execute()
        )

        expiradas = (
            _cliente()
            .table("assinaturas")
            .select("id")
            .eq("ativo", True)
            .lt("expira_em", agora_iso)
            .execute()
        )

        return {
            "total_usuarios": total,
            "usuarios_ativos": ativos,
            "assinaturas_ativas": ass_ativas,
            "expirando_7_dias": len(expirando.data),
            "expiradas": len(expiradas.data),
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
# LOGS — usa v_logs_admin
# ═══════════════════════════════════════════════════════════════


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
