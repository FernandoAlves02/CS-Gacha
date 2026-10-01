from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from panda3d.core import (
    AmbientLight,
    DirectionalLight,
)


class MirageInspector(ShowBase):

    def __init__(self):
        super().__init__()

        self.disableMouse()

        # =========================
        # MAPA
        # =========================

        self.mirage = self.loader.loadModel(
            "models/Maps/de_mirage_physics.glb"
        )

        self.mirage.reparentTo(self.render)

        self.mirage.setScale(1)
        self.mirage.setPos(0, 0, 0)
        self.mirage.setHpr(0, 0, 0)

        # =========================
        # CÂMERA
        # =======================
        self.camera.setPos(0, 0, 20)
        self.camera.lookAt(0, 0, 0)

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
        # ROTAÇÃO DO MAPA
        # =========================

        self.rotation_speed = 20
        self.auto_rotate = False

        self.accept("space", self.toggle_rotation)

        # =========================
        # CÂMERA
        # =========================

        self.accept("arrow_up", self.camera_up)
        self.accept("arrow_down", self.camera_down)
        self.accept("arrow_left", self.camera_left)
        self.accept("arrow_right", self.camera_right)

        # =========================
        # LOOP
        # =========================

        self.taskMgr.add(
            self.update,
            "update"
        )

    def toggle_rotation(self):
        self.auto_rotate = not self.auto_rotate

        print(
            "Rotação automática:",
            self.auto_rotate
        )

    def camera_up(self):
        pos = self.camera.getPos()
        self.camera.setZ(pos.z + 1)

        print("Câmera:", self.camera.getPos())

    def camera_down(self):
        pos = self.camera.getPos()
        self.camera.setZ(pos.z - 1)

        print("Câmera:", self.camera.getPos())

    def camera_left(self):
        pos = self.camera.getPos()
        self.camera.setX(pos.x - 1)

        print("Câmera:", self.camera.getPos())

    def camera_right(self):
        pos = self.camera.getPos()
        self.camera.setX(pos.x + 1)

        print("Câmera:", self.camera.getPos())

    def update(self, task):

        if self.auto_rotate:
            self.mirage.setH(
                self.mirage.getH()
                + self.rotation_speed * globalClock.getDt()
            )

        return Task.cont


