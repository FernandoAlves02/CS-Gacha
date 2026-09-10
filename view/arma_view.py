from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from panda3d.core import AmbientLight, DirectionalLight

class WeaponInspector(ShowBase):

    def __init__(self):
        super().__init__()

        self.disableMouse()

        # =========================
        # ARMA.
        # =========================

        self.weapon = self.loader.loadModel(
            "models/Weapons/weapon_snip_awp.glb"
        )

        if self.weapon.isEmpty():
            print("Erro: não foi possível carregar a arma.")
            return
        self.weapon.reparentTo(self.render)

        # Posição
        self.weapon.setPos(0, 0, 0)

        # Escala
        self.weapon.setScale(1)

        # Rotação inicial
        self.weapon.setHpr(0, 0, 0)

        # =========================
        # CÂMERA
        # =========================

        self.camera.setPos(0, -8, 2)
        self.camera.lookAt(0, 0, 1)

        # =========================
        # ILUMINAÇÃO
        # =========================

        ambient = AmbientLight("ambient")
        ambient.setColor((0.5, 0.5, 0.5, 1))

        ambient_np = self.render.attachNewNode(ambient)
        self.render.setLight(ambient_np)

        directional = DirectionalLight("directional")
        directional.setColor((1, 1, 1, 1))

        directional_np = self.render.attachNewNode(directional)
        directional_np.setHpr(-45, -35, 0)

        self.render.setLight(directional_np)

        # =========================
        # CONTROLES
        # =========================

        self.rotation_speed = 50

        self.accept("arrow_left", self.girar_esquerda)
        self.accept("arrow_right", self.girar_direita)
        self.accept("arrow_up", self.subir)
        self.accept("arrow_down", self.descer)

        self.taskMgr.add(
            self.update,
            "update"
        )

    # =========================
    # ROTAÇÃO
    # =========================
    
    def girar_esquerda(self):
        self.weapon.setH(
            self.weapon.getH() - 10
        )
    
    def girar_direita(self):
        self.weapon.setH(
            self.weapon.getH() + 10
        )

    # =========================
    # ALTURA
    # =========================
    
    def subir(self):
        self.weapon.setZ(
            self.weapon.getZ() + 0.2
        )
    
    def descer(self):
        self.weapon.setZ(
            self.weapon.getZ() - 0.2
        )

    def update(self, task):
        return Task.cont

app = WeaponInspector()
app.run()
    
