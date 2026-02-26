from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from telas.dashboard.dashboard_ui import DashboardUI
from telas.dashboard.dashboard_controller import DashboardController
from telas.usuarios.usuarios_ui import UsuariosUI
from telas.usuarios.usuarios_controller import UsuariosController
from telas.assinaturas.assinaturas_ui import AssinaturasUI
from telas.assinaturas.assinaturas_controller import AssinaturasController
from telas.planos.planos_ui import PlanosUI
from telas.planos.planos_controller import PlanosController
from telas.modulos.modulos_ui import ModulosUI
from telas.modulos.modulos_controller import ModulosController
from telas.acessos.acessos_ui import AcessosUI
from telas.acessos.acessos_controller import AcessosController
from telas.logs.logs_ui import LogsUI
from telas.logs.logs_controller import LogsController


class PrincipalController:

    def __init__(self, ui, realtime=None):
        self.ui = ui
        self._realtime = realtime
        self._paginas = {}
        self._carregar_paginas()
        self._conectar_eventos()
        self._ir_para("dashboard")

    def _carregar_paginas(self):
        rt = self._realtime

        paginas = {
            "dashboard": (DashboardUI, lambda ui: DashboardController(ui, rt)),
            "usuarios": (UsuariosUI, lambda ui: UsuariosController(ui, rt)),
            "assinaturas": (AssinaturasUI, lambda ui: AssinaturasController(ui, rt)),
            "planos": (PlanosUI, lambda ui: PlanosController(ui, rt)),
            "modulos": (ModulosUI, lambda ui: ModulosController(ui, rt)),
            "acessos": (AcessosUI, lambda ui: AcessosController(ui, rt)),
            "logs": (LogsUI, lambda ui: LogsController(ui, rt)),
        }

        self._controllers = {}

        for id_pagina, (UIClass, factory) in paginas.items():
            pagina_ui = UIClass()
            controller = factory(pagina_ui)
            self._controllers[id_pagina] = controller
            self.ui.area_conteudo.addWidget(pagina_ui)
            self._paginas[id_pagina] = pagina_ui

    def _conectar_eventos(self):
        self.ui.btn_fechar.clicked.connect(self._fechar)
        self.ui.btn_minimizar.clicked.connect(self.ui.showMinimized)
        self.ui.btn_maximizar.clicked.connect(self._toggle_maximizar)
        self.ui.btn_toggle_menu.clicked.connect(self._toggle_menu)

        for id_pagina, btn in self.ui.btns_menu.items():
            btn.clicked.connect(lambda checked, p=id_pagina: self._ir_para(p))

    def _ir_para(self, id_pagina: str):
        for btn in self.ui.btns_menu.values():
            btn.setChecked(False)
        if id_pagina in self.ui.btns_menu:
            self.ui.btns_menu[id_pagina].setChecked(True)
        if id_pagina in self._paginas:
            self.ui.area_conteudo.setCurrentWidget(self._paginas[id_pagina])

    def _toggle_menu(self):
        expandido = self.ui.menu_lateral.width() > 60

        if expandido:
            self.ui.menu_lateral.setFixedWidth(60)
            self.ui.btn_toggle_menu.setText("▶")
            for btn in self.ui.btns_menu.values():
                texto = btn.text().strip()
                partes = texto.split("  ")
                if len(partes) >= 2:
                    btn.setText(f"  {partes[1]}")
        else:
            self.ui.menu_lateral.setFixedWidth(220)
            self.ui.btn_toggle_menu.setText("◀")
            from telas.principal.principal_ui import MENU_ITENS

            for item in MENU_ITENS:
                btn = self.ui.btns_menu[item["id"]]
                btn.setText(f"  {item['emoji']}  {item['nome']}")

    def _toggle_maximizar(self):
        if self.ui.isMaximized():
            self.ui.showNormal()
            self.ui.btn_maximizar.setText("□")
        else:
            self.ui.showMaximized()
            self.ui.btn_maximizar.setText("❐")

    def _fechar(self):
        from utils.supabase_admin import _logs

        try:
            if self._realtime:
                print("[Realtime] Parando conexão...")
                self._realtime.parar()
            _logs.forcar_salvar()
        except Exception as e:
            print("Erro ao fechar recursos:", e)
        self.ui.close()
