"""
CRT Scanline Overlay for locAI.
Renders horizontal scanlines and optional vignette for dystopian terminal aesthetic.
"""

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPainter, QColor, QPen, QLinearGradient, QBrush


class CRTOverlay(QWidget):
    """
    Transparent overlay widget that draws CRT scanlines over its parent.
    Does not block mouse events (WA_TransparentForMouseEvents).
    """

    def __init__(
        self,
        parent=None,
        scanline_spacing: int = 3,
        scanline_opacity: int = 25,
        vignette_strength: float = 0.15,
    ):
        """
        Initialize CRT overlay.

        Args:
            parent: Parent widget (typically central widget)
            scanline_spacing: Pixels between scanlines (default 3)
            scanline_opacity: Scanline darkness 0-255 (default 25)
            vignette_strength: Vignette darkness at edges 0.0-1.0 (default 0.15)
        """
        super().__init__(parent)
        self.scanline_spacing = scanline_spacing
        self.scanline_opacity = scanline_opacity
        self.vignette_strength = vignette_strength

        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

    def paintEvent(self, event):
        """Draw scanlines and vignette."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)

        rect = self.rect()
        w, h = rect.width(), rect.height()

        # Draw horizontal scanlines
        pen = QPen(QColor(0, 0, 0, self.scanline_opacity))
        pen.setWidth(1)
        painter.setPen(pen)

        y = 0
        while y < h:
            painter.drawLine(0, y, w, y)
            y += self.scanline_spacing

        # Draw vignette (darker edges)
        if self.vignette_strength > 0:
            # Top edge gradient
            grad_top = QLinearGradient(0, 0, 0, h * 0.2)
            grad_top.setColorAt(0, QColor(0, 0, 0, int(255 * self.vignette_strength)))
            grad_top.setColorAt(1, QColor(0, 0, 0, 0))
            painter.fillRect(0, 0, w, int(h * 0.2), QBrush(grad_top))

            # Bottom edge gradient
            grad_bottom = QLinearGradient(0, h * 0.8, 0, h)
            grad_bottom.setColorAt(0, QColor(0, 0, 0, 0))
            grad_bottom.setColorAt(
                1, QColor(0, 0, 0, int(255 * self.vignette_strength))
            )
            painter.fillRect(0, int(h * 0.8), w, int(h * 0.2) + 1, QBrush(grad_bottom))

            # Left edge gradient
            grad_left = QLinearGradient(0, 0, w * 0.15, 0)
            grad_left.setColorAt(
                0, QColor(0, 0, 0, int(255 * self.vignette_strength))
            )
            grad_left.setColorAt(1, QColor(0, 0, 0, 0))
            painter.fillRect(0, 0, int(w * 0.15), h, QBrush(grad_left))

            # Right edge gradient
            grad_right = QLinearGradient(w * 0.85, 0, w, 0)
            grad_right.setColorAt(0, QColor(0, 0, 0, 0))
            grad_right.setColorAt(
                1, QColor(0, 0, 0, int(255 * self.vignette_strength))
            )
            painter.fillRect(int(w * 0.85), 0, int(w * 0.15) + 1, h, QBrush(grad_right))

        painter.end()
