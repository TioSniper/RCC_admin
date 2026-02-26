# utils/cache_store.py
#
# Store central de dados do admin.
# Carrega tudo uma vez na abertura. Realtime atualiza só o objeto afetado.
# Controllers leem daqui — zero queries extras.

import threading
from PyQt6.QtCore import QObject, pyqtSignal


class AdminStore(QObject):
    """
    Cache central. Emite sinais quando os dados mudam
    para que os controllers atualizem a UI.
    """

    # Sinais emitidos após atualização do cache
    usuarios_atualizados = pyqtSignal()
    assinaturas_atualizadas = pyqtSignal()
    planos_atualizados = pyqtSignal()
    modulos_atualizados = pyqtSignal()
    logs_atualizados = pyqtSignal()
    solicitacoes_atualizadas = pyqtSignal()
    sessoes_atualizadas = pyqtSignal()
    resumo_atualizado = pyqtSignal()
    carregamento_completo = pyqtSignal()  # emitido quando carga inicial termina

    def __init__(self):
        super().__init__()
        self._lock = threading.Lock()

        # Dados em cache
        self.usuarios: list = []
        self.assinaturas: list = []
        self.planos: list = []
        self.modulos: list = []
        self.logs: list = []
        self.solicitacoes: list = []
        self.sessoes: set = set()
        self.resumo: dict = {}
        self.expirando: list = []

    # ── Carga inicial — roda tudo em paralelo ──────────────────

    def carregar_tudo(self):
        """Carrega todos os dados em threads paralelas."""
        threading.Thread(target=self._carga_inicial, daemon=True).start()

    def _carga_inicial(self):
        from utils.supabase_admin import (
            listar_usuarios,
            listar_assinaturas,
            listar_planos,
            listar_modulos,
            listar_logs,
            listar_solicitacoes,
            listar_sessoes_ativas,
            resumo_geral,
            listar_expirando,
        )

        tarefas = [
            ("usuarios", listar_usuarios),
            ("assinaturas", listar_assinaturas),
            ("planos", listar_planos),
            ("modulos", listar_modulos),
            ("logs", lambda: listar_logs(200)),
            ("solicitacoes", listar_solicitacoes),
            ("sessoes", listar_sessoes_ativas),
            ("resumo", resumo_geral),
            ("expirando", lambda: listar_expirando(7)),
        ]

        threads = []
        for nome, fn in tarefas:
            t = threading.Thread(target=self._carregar_um, args=(nome, fn), daemon=True)
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        self.carregamento_completo.emit()

    def _carregar_um(self, nome: str, fn):
        try:
            resultado = fn()
            with self._lock:
                setattr(self, nome, resultado)
            # Emite sinal correspondente
            sinal = (
                getattr(self, f"{nome}_atualizados", None)
                or getattr(self, f"{nome}_atualizado", None)
                or getattr(self, f"{nome}_atualizadas", None)
            )
            if sinal:
                sinal.emit()
        except Exception as e:
            print(f"[Store] Erro ao carregar {nome}: {e}")

    # ── Atualizações cirúrgicas via Realtime ───────────────────

    def on_usuario_mudou(self, payload: dict):
        tipo = payload.get("type")
        record = payload.get("record", {})
        uid = record.get("id") or payload.get("old_record", {}).get("id")

        with self._lock:
            if tipo == "DELETE":
                self.usuarios = [u for u in self.usuarios if u.get("id") != uid]
            elif tipo == "UPDATE" and uid:
                for u in self.usuarios:
                    if u.get("id") == uid:
                        u.update(record)
                        break
            elif tipo == "INSERT" and uid:
                record.setdefault("assinatura", None)
                self.usuarios.insert(0, record)

        self.usuarios_atualizados.emit()

    def on_assinatura_mudou(self, payload: dict):
        tipo = payload.get("type")
        record = payload.get("record", {})
        uid = record.get("user_id")

        with self._lock:
            # 1. Resolve plano_nome do cache local
            if record and record.get("plano_id") and "plano_nome" not in record:
                plano = next(
                    (p for p in self.planos if p.get("id") == record["plano_id"]), None
                )
                if plano:
                    record["plano_nome"] = plano.get("nome", "—")

            # 2. Resolve username do cache de usuários (Realtime não envia)
            if record and not record.get("username") and uid:
                usuario = next((u for u in self.usuarios if u.get("id") == uid), None)
                if usuario:
                    record["username"] = usuario.get("username", "—")

            # 3. Atualiza lista de assinaturas
            if tipo == "DELETE":
                ass_id = payload.get("old_record", {}).get("id")
                self.assinaturas = [
                    a for a in self.assinaturas if a.get("id") != ass_id
                ]

            elif tipo == "UPDATE" and record:
                if not record.get("ativo"):
                    # Assinatura desativada — remove da lista
                    self.assinaturas = [
                        a for a in self.assinaturas if a.get("id") != record.get("id")
                    ]
                else:
                    # Atualiza linha existente
                    existente = next(
                        (
                            a
                            for a in self.assinaturas
                            if a.get("id") == record.get("id")
                        ),
                        None,
                    )
                    if existente:
                        existente.update(record)
                    else:
                        self.assinaturas.insert(0, record)

            elif tipo == "INSERT" and record and record.get("ativo"):
                # Nova assinatura — remove qualquer outra do mesmo user_id antes de inserir
                self.assinaturas = [
                    a for a in self.assinaturas if a.get("user_id") != uid
                ]
                self.assinaturas.insert(0, record)
                # Se é o básico sendo inserido, significa que houve expiração
                # Recarrega o resumo do banco para atualizar contador de expiradas
                import os

                BASICO_ID = os.getenv(
                    "PLANO_BASICO_ID", "11111111-1111-1111-1111-111111111111"
                )
                if record.get("plano_id") == BASICO_ID:
                    threading.Thread(
                        target=self._recarregar_resumo, daemon=True
                    ).start()

            # 4. Atualiza campo assinatura no objeto usuário
            for u in self.usuarios:
                if u.get("id") == uid:
                    ass_ativa = next(
                        (
                            a
                            for a in self.assinaturas
                            if a.get("user_id") == uid and a.get("ativo")
                        ),
                        None,
                    )
                    u["assinatura"] = ass_ativa
                    break

        self.assinaturas_atualizadas.emit()
        self._recalcular_resumo()

    def on_sessao_mudou(self, payload: dict):
        tipo = payload.get("type")
        record = payload.get("record", {})
        uid = record.get("user_id") or payload.get("old_record", {}).get("user_id")
        if not uid:
            return

        with self._lock:
            if tipo == "DELETE":
                self.sessoes.discard(uid)
            else:
                self.sessoes.add(uid)

        self.sessoes_atualizadas.emit()

    def on_plano_mudou(self, payload: dict):
        tipo = payload.get("type")
        record = payload.get("record", {})
        pid = record.get("id") or payload.get("old_record", {}).get("id")

        if tipo == "INSERT" and pid:
            # INSERT não traz planos_modulos — busca o plano completo
            threading.Thread(
                target=self._fetch_plano_completo, args=(pid,), daemon=True
            ).start()
            return

        with self._lock:
            if tipo == "DELETE":
                self.planos = [p for p in self.planos if p.get("id") != pid]
            elif tipo == "UPDATE" and pid:
                for p in self.planos:
                    if p.get("id") == pid:
                        p.update(record)
                        break

        self.planos_atualizados.emit()

    def _fetch_plano_completo(self, plano_id: str):
        """Busca um plano com seus módulos e insere no cache."""
        from utils.supabase_admin import listar_planos

        planos = listar_planos()
        plano = next((p for p in planos if p.get("id") == plano_id), None)
        if plano:
            with self._lock:
                # Remove se já existia (evita duplicata)
                self.planos = [p for p in self.planos if p.get("id") != plano_id]
                self.planos.append(plano)
            self.planos_atualizados.emit()

    def on_planos_modulos_mudou(self, payload: dict):
        """Quando módulos de um plano mudam — atualiza o plano no cache."""
        record = payload.get("record", {}) or payload.get("old_record", {})
        pid = record.get("plano_id")
        if not pid:
            return
        # Rebusca o plano completo para ter a lista atualizada de módulos
        threading.Thread(
            target=self._fetch_plano_completo, args=(pid,), daemon=True
        ).start()

    def on_modulo_mudou(self, payload: dict):
        tipo = payload.get("type")
        record = payload.get("record", {})
        mid = record.get("id") or payload.get("old_record", {}).get("id")

        with self._lock:
            if tipo == "DELETE":
                self.modulos = [m for m in self.modulos if m.get("id") != mid]
            elif tipo == "UPDATE" and mid:
                for m in self.modulos:
                    if m.get("id") == mid:
                        m.update(record)
                        break
            elif tipo == "INSERT":
                self.modulos.append(record)

        self.modulos_atualizados.emit()

    def on_solicitacao_mudou(self, payload: dict):
        tipo = payload.get("type")
        record = payload.get("record", {})
        sid = record.get("id") or payload.get("old_record", {}).get("id")

        with self._lock:
            # Remove aprovadas/rejeitadas da lista pendente
            if tipo in ("UPDATE", "DELETE"):
                self.solicitacoes = [s for s in self.solicitacoes if s.get("id") != sid]
            # Adiciona nova solicitação pendente
            if tipo == "INSERT" and record.get("status") == "pendente":
                self.solicitacoes.insert(0, record)

        self.solicitacoes_atualizadas.emit()

    def on_log_mudou(self, payload: dict):
        record = payload.get("record", {})
        if record:
            with self._lock:
                self.logs.insert(0, record)
                self.logs = self.logs[:200]  # mantém só os últimos 200
        self.logs_atualizados.emit()

    def _recarregar_resumo(self):
        """Busca resumo atualizado do banco — usado quando expiradas mudam."""
        try:
            from utils.supabase_admin import resumo_geral

            r = resumo_geral()
            with self._lock:
                self.resumo = r
            self.resumo_atualizado.emit()
        except Exception as e:
            print(f"[Store] Erro ao recarregar resumo: {e}")

    def _recalcular_resumo(self):
        """Recalcula o resumo localmente sem query ao banco, ignorando plano basico."""
        import os
        from datetime import datetime, timezone, timedelta

        BASICO_ID = os.getenv("PLANO_BASICO_ID", "11111111-1111-1111-1111-111111111111")
        agora = datetime.now(timezone.utc)
        em_7_dias = agora + timedelta(days=7)

        with self._lock:
            total = len(self.usuarios)
            ativos = sum(1 for u in self.usuarios if u.get("ativo"))
            nao_basico = [
                a
                for a in self.assinaturas
                if a.get("ativo") and a.get("plano_id") != BASICO_ID
            ]
            ass_ativas = len(nao_basico)
            expirando = sum(
                1
                for a in nao_basico
                if a.get("expira_em")
                and agora
                <= datetime.fromisoformat(a["expira_em"].replace("Z", "+00:00"))
                <= em_7_dias
            )
            # Expiradas vem do resumo anterior (banco) — o cache só tem ativas
            # Preserva o valor que veio do banco na última carga completa
            expiradas = self.resumo.get("expiradas", 0) if self.resumo else 0
            self.resumo = {
                "total_usuarios": total,
                "usuarios_ativos": ativos,
                "assinaturas_ativas": ass_ativas,
                "expirando_7_dias": expirando,
                "expiradas": expiradas,
            }

        self.resumo_atualizado.emit()


# ── Instância global ───────────────────────────────────────────
_store: AdminStore | None = None


def obter_store() -> AdminStore:
    global _store
    if _store is None:
        _store = AdminStore()
    return _store
