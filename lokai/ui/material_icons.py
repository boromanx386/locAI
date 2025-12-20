"""
Material Icons helper for locAI.
Provides Material Design icons using SVG icons.
"""

from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QPushButton, QLabel
import io


class MaterialIcons:
    """Material Icons SVG manager."""

    # Material Icons SVG paths (24px viewBox)
    CHAT_SVG = """<svg xmlns="http://www.w3.org/2000/svg" height="24" viewBox="0 0 24 24" width="24">
<path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z" fill="currentColor"/>
</svg>"""

    IMAGE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" height="24" viewBox="0 0 24 24" width="24">
<path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z" fill="currentColor"/>
</svg>"""

    SEND_SVG = """<svg xmlns="http://www.w3.org/2000/svg" height="24" viewBox="0 0 24 24" width="24">
<path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" fill="currentColor"/>
</svg>"""

    SETTINGS_SVG = """<svg xmlns="http://www.w3.org/2000/svg" height="24" viewBox="0 0 24 24" width="24">
<path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94L14.4 2.81c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.07.62-.07.94s.02.64.07.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z" fill="currentColor"/>
</svg>"""

    REFRESH_SVG = """<svg xmlns="http://www.w3.org/2000/svg" height="24" viewBox="0 0 24 24" width="24">
<path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z" fill="currentColor"/>
</svg>"""

    DELETE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" height="24" viewBox="0 0 24 24" width="24">
<path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z" fill="currentColor"/>
</svg>"""

    INFO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" height="24" viewBox="0 0 24 24" width="24">
<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z" fill="currentColor"/>
</svg>"""

    SAVE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" height="24" viewBox="0 0 24 24" width="24">
<path d="M17 3H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V7l-4-4zm-5 16c-1.66 0-3-1.34-3-3s1.34-3 3-3 3 1.34 3 3-1.34 3-3 3zm3-10H5V5h10v4z" fill="currentColor"/>
</svg>"""

    RESET_SVG = """<svg xmlns="http://www.w3.org/2000/svg" height="24" viewBox="0 0 24 24" width="24">
<path d="M14 12c0-1.1-.9-2-2-2s-2 .9-2 2 .9 2 2 2 2-.9 2-2zm-2-9c-4.97 0-9 4.03-9 9H0l4 4 4-4H5c0-3.87 3.13-7 7-7s7 3.13 7 7-3.13 7-7 7c-1.51 0-2.91-.49-4.06-1.3l-1.42 1.44C8.04 20.3 9.94 21 12 21c4.97 0 9-4.03 9-9s-4.03-9-9-9z" fill="currentColor"/>
</svg>"""

    LOCK_SVG = """<svg xmlns="http://www.w3.org/2000/svg" height="24" viewBox="0 0 24 24" width="24">
<path d="M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm-6 9c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm3.1-9H8.9V6c0-1.71 1.39-3.1 3.1-3.1 1.71 0 3.1 1.39 3.1 3.1v2z" fill="currentColor"/>
</svg>"""

    LOCK_OPEN_SVG = """<svg xmlns="http://www.w3.org/2000/svg" height="24" viewBox="0 0 24 24" width="24">
<path d="M12 17c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm6-9h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zM8.9 6c0-1.71 1.39-3.1 3.1-3.1 1.71 0 3.1 1.39 3.1 3.1v2H8.9V6z" fill="currentColor"/>
</svg>"""

    PLAY_SVG = """<svg xmlns="http://www.w3.org/2000/svg" height="24" viewBox="0 0 24 24" width="24">
<path d="M8 5v14l11-7z" fill="currentColor"/>
</svg>"""

    PAUSE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" height="24" viewBox="0 0 24 24" width="24">
<path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" fill="currentColor"/>
</svg>"""

    STOP_SVG = """<svg xmlns="http://www.w3.org/2000/svg" height="24" viewBox="0 0 24 24" width="24">
<path d="M6 6h12v12H6z" fill="currentColor"/>
</svg>"""

    MICROPHONE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" height="24" viewBox="0 -960 960 960" width="24">
<path d="M160-80q-33 0-56.5-23.5T80-160v-640q0-33 23.5-56.5T160-880h326l-80 80H160v640h440v-80h80v80q0 33-23.5 56.5T600-80H160Zm80-160v-80h280v80H240Zm0-120v-80h200v80H240Zm360 0L440-520H320v-200h120l160-160v520Zm80-122v-276q36 21 58 57t22 81q0 45-22 81t-58 57Zm0 172v-84q70-25 115-86.5T840-620q0-78-45-139.5T680-846v-84q104 27 172 112.5T920-620q0 112-68 197.5T680-310Z" fill="currentColor"/>
</svg>"""

    VOICE_SELECTION_SVG = """<svg xmlns="http://www.w3.org/2000/svg" height="24" viewBox="0 0 24 24" width="24">
<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z" fill="currentColor"/>
<path d="M12 14c-1.1 0-2-.9-2-2V8c0-1.1.9-2 2-2s2 .9 2 2v4c0 1.1-.9 2-2 2zm2.5 2.5c-.83 0-1.5-.67-1.5-1.5h-2c0 1.38 1.12 2.5 2.5 2.5s2.5-1.12 2.5-2.5h-2c0 .83-.67 1.5-1.5 1.5z" fill="currentColor"/>
</svg>"""

    ROBOT_SVG = """<svg xmlns="http://www.w3.org/2000/svg" height="24" viewBox="0 0 24 24" width="24">
<path d="M20 9V7c0-1.1-.9-2-2-2h-3c0-1.66-1.34-3-3-3S9 3.34 9 5H6c-1.1 0-2 .9-2 2v2c-1.66 0-3 1.34-3 3s1.34 3 3 3v4c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2v-4c1.66 0 3-1.34 3-3s-1.34-3-3-3zm-2 10H6V7h12v12zm-9-6c-.83 0-1.5-.67-1.5-1.5S8.17 10 9 10s1.5.67 1.5 1.5S9.83 13 9 13zm7.5-1.5c0 .83-.67 1.5-1.5 1.5s-1.5-.67-1.5-1.5S14.17 10 15 10s1.5.67 1.5 1.5zM8 15h8v2H8v-2z" fill="currentColor"/>
</svg>"""

    COGNITION_2_SVG = """<svg xmlns="http://www.w3.org/2000/svg" height="24" viewBox="0 -960 960 960" width="24">
<path d="M309-389q29 29 71 29t71-29l160-160q29-29 29-71t-29-71q-29-29-71-29t-71 29q-37-13-73-6t-61 32q-25 25-32 61t6 73q-29 29-29 71t29 71ZM240-80v-172q-57-52-88.5-121.5T120-520q0-150 105-255t255-105q125 0 221.5 73.5T827-615l52 205q5 19-7 34.5T840-360h-80v120q0 33-23.5 56.5T680-160h-80v80h-80v-160h160v-200h108l-38-155q-23-91-98-148t-172-57q-116 0-198 81t-82 197q0 60 24.5 114t69.5 96l26 24v208h-80Zm254-360Z" fill="currentColor"/>
</svg>"""

    @classmethod
    def svg_to_icon(
        cls, svg_string: str, size: int = 24, color: str = "white"
    ) -> QIcon:
        """
        Convert SVG string to QIcon.

        Args:
            svg_string: SVG XML string
            size: Icon size in pixels
            color: Icon color (default: white)

        Returns:
            QIcon instance
        """
        # Replace currentColor with actual color
        svg_with_color = svg_string.replace('fill="currentColor"', f'fill="{color}"')
        svg_with_color = svg_with_color.replace(
            "fill='currentColor'", f"fill='{color}'"
        )

        renderer = QSvgRenderer(QByteArray(svg_with_color.encode("utf-8")))
        if not renderer.isValid():
            # Return empty icon if SVG is invalid
            return QIcon()

        # Create pixmap with transparent background
        pixmap = QPixmap(size, size)
        pixmap.fill(QColor(0, 0, 0, 0))  # Fully transparent

        # Render SVG to pixmap
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Render the SVG
        renderer.render(painter)
        painter.end()

        return QIcon(pixmap)

    @classmethod
    def apply_to_button(
        cls,
        button: QPushButton,
        svg_string: str,
        size: int = 20,
        keep_text: bool = True,
        color: str = "white",
    ):
        """
        Apply Material Icon to a button.

        Args:
            button: QPushButton instance
            svg_string: SVG XML string
            size: Icon size in pixels
            keep_text: If True, keep existing text; if False, clear text for icon-only button
            color: Icon color (default: white)
        """
        icon = cls.svg_to_icon(svg_string, size, color)
        button.setIcon(icon)
        button.setIconSize(QSize(size, size))
        if not keep_text:
            button.setText("")  # Clear text for icon-only buttons

    @classmethod
    def apply_to_label(
        cls, label: QLabel, svg_string: str, size: int = 20, color: str = "white"
    ):
        """
        Apply Material Icon to a label.

        Args:
            label: QLabel instance
            svg_string: SVG XML string
            size: Icon size in pixels
            color: Icon color (default: white)
        """
        icon = cls.svg_to_icon(svg_string, size, color)
        label.setPixmap(icon.pixmap(size, size))
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
