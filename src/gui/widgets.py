"""
Contains custom PyQt widgets for the Gesture Mapper GUI, such as ClickableLabel.
"""
from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import pyqtSignal, QPoint

class ClickableLabel(QLabel):
    """A QLabel that emits a signal with the coordinates of a click."""
    clicked = pyqtSignal(QPoint)

    def mousePressEvent(self, event):
        """Emit the clicked signal with the event's position."""
        self.clicked.emit(event.pos())
        super().mousePressEvent(event)
