"""Pop-up MINHA CONTA (épico "Gestão de Usuário" da documentação):
"O usuário deve conseguir visualizar e editar seus dados."

Abre ao clicar no nome do jogador no header (em qualquer tela do jogo).
Mostra nome, e-mail e saldo; permite trocar nome, e-mail e senha e EXCLUIR A
CONTA (com confirmação). Com o cadastro (tela de login), fica o CRUD completo
do usuário, como no projeto feito em aula: Create, Read, Update e Delete.
Toda regra (validação, e-mail repetido, hash da senha) fica no User_Controller;
esta janela só cumpre o contrato de "view" dele:
    read_profile_data() -> (nome, senha nova ou "", e-mail)
    show_message(mensagem, sucesso)
"""
from direct.showbase.DirectObject import DirectObject

from app.controller.user_controller import User_Controller
from app.core.game_rules import format_money
from app.core.i18n import t
from app.view.ui_kit import CENTRO, COR_TEXTO, COR_TEXTO_2, COR_TEXTO_3, COR_VERDE, COR_VERMELHO, ESQUERDA, Janela


class JanelaMinhaConta:

    LARGURA, ALTURA = 1.9, 1.32

    def __init__(self, tela, ao_fechar=None):
        """tela: a GameViewBase que abriu (usa o kit de interface, o header e o ViewManager)."""
        self.tela = tela
        self.ao_fechar = ao_fechar
        vm = tela.view_manager
        self.usuario = vm.usuario_logado
        self.controller = User_Controller(vm.user_dao, self)
        ui = tela.ui

        self.janela = Janela(ui, tela.ui_root, self.LARGURA, self.ALTURA, t("MINHA CONTA"), ao_fechar=self._ao_fechar)
        p = self.janela.painel
        x = -self.LARGURA / 2 + 0.08
        largura_campo = self.LARGURA - 0.16

        def rotulo(texto, z):
            ui.texto(p, texto, x, z, 0.024, COR_TEXTO_3, ESQUERDA, negrito=True)

        rotulo(t("NOME DE USUÁRIO"), 0.43)
        self.campo_nome, exemplo_nome = ui.campo_texto(p, x, 0.37, largura_campo, 0.075, t("Nome de usuário"),
                                                        lambda: None, self._salvar_enter, max_caracteres=50)
        self.campo_nome.enterText(self.usuario.username)
        exemplo_nome()

        rotulo(t("E-MAIL"), 0.27)
        self.campo_email, exemplo_email = ui.campo_texto(p, x, 0.21, largura_campo, 0.075, t("E-mail"),
                                                          lambda: None, self._salvar_enter, max_caracteres=100)
        self.campo_email.enterText(self.usuario.email or "")
        exemplo_email()

        rotulo(t("NOVA SENHA (deixe em branco para manter a atual)"), 0.11)
        self.campo_senha, self.exemplo_senha = ui.campo_texto(
            p, x, 0.05, largura_campo, 0.075, t("Nova senha (opcional)"),
            lambda: None, self._salvar_enter, oculto=True,
        )

        rotulo(t("SALDO"), -0.06)
        ui.texto(p, format_money(self.usuario.balance), x, -0.125, 0.045, COR_VERDE, negrito=True)
        ui.texto(p, t("O saldo só muda comprando, abrindo caixas ou vendendo."), x, -0.18, 0.024, COR_TEXTO_2)

        self.mensagem = ui.texto(p, "", x, -0.29, 0.028, COR_TEXTO)
        ui.botao(p, t("FECHAR"), self.LARGURA / 2 - 0.30, -0.52, 0.40, 0.09, self.fechar, tipo="secundario",
                 escala=0.03)
        ui.botao(p, t("SALVAR"), self.LARGURA / 2 - 0.74, -0.52, 0.40, 0.09, self.salvar, escala=0.032)
        excluir = ui.botao(p, t("EXCLUIR CONTA"), -self.LARGURA / 2 + 0.28, -0.52, 0.40, 0.09,
                           self._confirmar_exclusao, tipo="secundario", escala=0.028)
        excluir["text_fg"] = COR_VERMELHO
        self.confirmacao = None             # janelinha "Excluir a conta?" (quando aberta)

        self.eventos = DirectObject()
        self.eventos.accept("escape", self._tecla_esc)
        self.campo_nome["focus"] = 1

    # ------------------------------------------------------------------
    # contrato com o User_Controller
    # ------------------------------------------------------------------

    def read_profile_data(self):
        return self.campo_nome.get(), self.campo_senha.get(), self.campo_email.get()

    def show_message(self, message, success=True):
        self.mensagem.setText(message)
        self.mensagem.setFg(COR_VERDE if success else COR_VERMELHO)

    # ------------------------------------------------------------------

    def salvar(self):
        self.controller.update(self.usuario)
        self.tela.ui.selecao.desmarcar_todos()      # tira a marcação do Ctrl+A, se houver
        self.campo_senha.enterText("")             # a senha digitada não fica na tela
        self.exemplo_senha()                        # ...e o texto de exemplo volta a aparecer
        self.tela.atualizar_saldo()                 # o header mostra o nome novo

    def _salvar_enter(self, _texto=None):
        if self.confirmacao is None:
            self.salvar()

    # ------------------------------------------------------------------
    # EXCLUIR CONTA (com confirmação: não dá para desfazer)
    # ------------------------------------------------------------------

    def _confirmar_exclusao(self):
        ui = self.tela.ui
        for campo in (self.campo_nome, self.campo_email, self.campo_senha):
            campo["focus"] = 0                      # o teclado não continua escrevendo nos campos de trás
        self.confirmacao = Janela(ui, self.tela.ui_root, 1.6, 0.78, t("EXCLUIR CONTA"))
        p = self.confirmacao.painel
        ui.texto(p, t("Excluir a conta {nome}?", nome=self.usuario.username), 0, 0.12, 0.036, COR_TEXTO, CENTRO,
                 negrito=True, largura_max=1.45)
        ui.texto(p, t("O inventário, o saldo e as estatísticas desta conta são apagados. Não dá para desfazer."),
                 0, 0.03, 0.025, COR_TEXTO_2, CENTRO, quebra_em=1.4)
        ui.botao(p, t("CANCELAR"), 0.33, -0.25, 0.48, 0.09, self._cancelar_exclusao, tipo="secundario", escala=0.03)
        confirmar = ui.botao(p, t("EXCLUIR"), -0.33, -0.25, 0.48, 0.09, self._excluir, tipo="secundario",
                             escala=0.03)
        confirmar["text_fg"] = COR_VERMELHO

    def _cancelar_exclusao(self):
        if self.confirmacao is not None:
            self.confirmacao.fechar()
            self.confirmacao = None

    def _excluir(self):
        self._cancelar_exclusao()
        if self.controller.delete(self.usuario):
            view_manager = self.tela.view_manager
            self.fechar()
            view_manager.sair()                                   # volta ao login, sem ninguém logado
            login = view_manager.tela_atual
            if hasattr(login, "show_message"):
                login.show_message(t("Conta excluída. Até a próxima!"))

    def _tecla_esc(self):
        if self.confirmacao is not None:
            self._cancelar_exclusao()               # ESC fecha só a pergunta
        else:
            self.fechar()

    @property
    def aberta(self):
        return self.janela is not None and self.janela.aberta

    def fechar(self):
        if self.janela is not None:
            self.janela.fechar()                    # chama _ao_fechar

    def _ao_fechar(self):
        self.eventos.ignoreAll()
        self._cancelar_exclusao()
        self.janela = None
        if self.ao_fechar:
            self.ao_fechar()
