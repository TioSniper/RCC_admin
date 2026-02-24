import threading
from datetime import datetime, timezone
from PyQt6.QtWidgets import QTableWidgetItem
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QMetaObject, Q_ARG
from utils.supabase_admin import resumo_geral, listar_expirando


class DashboardWorker(QObject):
    dados_prontos = pyqtSignal(dict, list)

    def buscar(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        resumo = resumo_geral()
        expirando = listar_expirando(7)
        self.dados_prontos.emit(resumo, expirando)


class DashboardController:

    def __init__(self, ui):
        self.ui = ui
        self.worker = DashboardWorker()
        self.worker.dados_prontos.connect(self._atualizar_ui)
        self._conectar_eventos()
        self._carregar_dados()

    def _conectar_eventos(self):
        from PyQt6.QtWidgets import QPushButton

        for btn in self.ui.findChildren(QPushButton):
            if "Atualizar" in btn.text():
                btn.clicked.connect(self._carregar_dados)

    def _carregar_dados(self):
        self.worker.buscar()

    def _atualizar_ui(self, resumo: dict, expirando: list):
        if resumo:
            self.ui.card_usuarios.lbl_valor.setText(
                str(resumo.get("total_usuarios", 0))
            )
            self.ui.card_ativos.lbl_valor.setText(str(resumo.get("usuarios_ativos", 0)))
            self.ui.card_assinaturas.lbl_valor.setText(
                str(resumo.get("assinaturas_ativas", 0))
            )
            self.ui.card_expirando.lbl_valor.setText(
                str(resumo.get("expirando_7_dias", 0))
            )
            self.ui.card_expiradas.lbl_valor.setText(str(resumo.get("expiradas", 0)))

        tabela = self.ui.tabela_expirando
        tabela.setRowCount(0)

        for dados in expirando:
            row = tabela.rowCount()
            tabela.insertRow(row)

            username = dados.get("username", "—")
            plano = dados.get("plano_nome", "—")
            expira_raw = dados.get("expira_em", "")

            try:
                dt = datetime.fromisoformat(expira_raw.replace("Z", "+00:00"))
                dias = (dt - datetime.now(timezone.utc)).days
                expira_fmt = dt.strftime("%d/%m/%Y %H:%M")
            except Exception:
                dias = 0
                expira_fmt = expira_raw

            tabela.setItem(row, 0, self._item(username))
            tabela.setItem(row, 1, self._item(plano))
            tabela.setItem(row, 2, self._item(expira_fmt))

            item_dias = QTableWidgetItem(f"{dias} dias")
            item_dias.setForeground(
                Qt.GlobalColor.red if dias <= 2 else Qt.GlobalColor.yellow
            )
            item_dias.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            tabela.setItem(row, 3, item_dias)

    def _item(self, texto: str) -> QTableWidgetItem:
        item = QTableWidgetItem(str(texto))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item
