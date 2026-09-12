from app.view.login_view import LoginView
from app.view.home_view import HomeView
from app.view.inventory_view import InventoryView

class ViewManager:
    def __init__(self):
        self.active_base_view = None
        self.active_overlay = None

        self.base_view = {
            "login" : LoginView(self),
            "home" : HomeView(self)
        }

        self.overlays = {
            "inventory" : InventoryView(self)
        }

        def set_base_view(self, view_name):
            close_overlay()

            if self.active_base_view is not None:
                self.active_base_view.destroy()

            new_view = self.base_view.get(view_name)
            if new_view:
                self.active_base_view = new_view
                self.active_base_view.create_view()
            else:
                print(f"Erro: Tela base '{view_name}' não encontrada.")

        def open_overlay(self, view_name):
            close_overlay()

            new_overlay = self.overlays.get(view_name)
            if new_overlay:
                self.active_overlay = new_overlay
                self.active_overlay.create_view()

            else:
                print(f"Erro: Overlay '{view_name}' não encontrada.")

        def close_overlay(self):
            if self.active_overlay:
                self.active_overlay.destroy()
                self.active_overlay = None

        