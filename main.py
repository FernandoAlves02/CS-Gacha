from direct.showbase.ShowBase import ShowBase
from app.controller.view_manager import ViewManager

class CSGachaGame(ShowBase):
    def __init__(self):
        super().__init__()
        
        self.disableMouse()

        self.view_manager = ViewManager(self)

        self.view_manager.change_view("login")

if __name__ == "__main__":
    app = CSGachaGame()
    app.run()