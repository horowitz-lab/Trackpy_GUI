from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout

class DetectionParametersWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.layout = QVBoxLayout(self)
        self.label = QLabel("Tracking Parameters Widget")
        self.layout.addWidget(self.label)
