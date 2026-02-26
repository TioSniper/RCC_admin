import os


class LoginController:

    def __init__(self, ui):
        self.ui = ui
        self._conectar_eventos()

    def _conectar_eventos(self):
        self.ui.btn_fechar.clicked.connect(self.ui.close)
        self.ui.btn_entrar.clicked.connect(self._fazer_login)
        self.ui.input_senha.returnPressed.connect(self._fazer_login)
        self.ui.input_usuario.returnPressed.connect(
            lambda: self.ui.input_senha.setFocus()
        )

    def _fazer_login(self):
        usuario = self.ui.input_usuario.text().strip()
        senha = self.ui.input_senha.text().strip()

        if not usuario or not senha:
            self.ui.lbl_aviso.setText("⚠️  Preencha usuário e senha.")
            return

        senha_master = os.getenv("ADMIN_SENHA_MASTER", "")

        if usuario != "admin" or senha != senha_master:
            self.ui.lbl_aviso.setText("⚠️  Usuário ou senha incorretos.")
            self.ui.input_senha.clear()
            return

        self._abrir_painel()

    def _abrir_painel(self):
        from telas.principal.principal_ui import PrincipalUI
        from telas.principal.principal_controller import PrincipalController
        from utils.admin_realtime import iniciar_realtime
        from config import (
            SUPABASE_URL,
            SUPABASE_SERVICE_KEY,
        )  # ajuste o import conforme seu projeto

        realtime = iniciar_realtime(SUPABASE_URL, SUPABASE_SERVICE_KEY)

        self.janela_principal = PrincipalUI()
        self.controller_principal = PrincipalController(self.janela_principal, realtime)
        self.janela_principal.show()
        self.ui.close()
