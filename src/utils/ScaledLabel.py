from PySide6.QtWidgets import QLabel, QStyle, QStyleOption
from PySide6.QtGui import QPixmap, QPainter
from PySide6.QtCore import Qt


class ScaledLabel(QLabel):
    """
    A QLabel subclass that automatically scales its pixmap to fit the label's
    size while preserving the original aspect ratio. The scaled image is
    always centered.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = QPixmap()

    def setPixmap(self, pixmap):
        """
        Sets the pixmap for the label.
        Args:
            pixmap (QPixmap): The pixmap to display.
        """
        self._pixmap = pixmap
        self.update()  # Trigger a repaint

    def paintEvent(self, event):
        """
        Overrides the paint event to draw the scaled pixmap.
        """
        if self._pixmap.isNull():
            # If no pixmap is set, draw the default QLabel content
            super().paintEvent(event)
            return

        painter = QPainter(self)
        pixmap_size = self._pixmap.size()
        label_size = self.size()

        # Scale pixmap to fit the label, maintaining aspect ratio
        scaled_pixmap = self._pixmap.scaled(
            label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )

        # Calculate coordinates to center the pixmap
        x = (label_size.width() - scaled_pixmap.width()) / 2
        y = (label_size.height() - scaled_pixmap.height()) / 2

        painter.drawPixmap(x, y, scaled_pixmap)
