"""
Theme system for locAI.
Provides modern, eye-friendly color schemes (without bright green #00FF00).
"""
from typing import Dict


class Theme:
    """Theme management for locAI UI."""
    
    # Modern color palette (eye-friendly, no bright green)
    DARK_THEME = {
        "primary": "#4A9EFF",          # Calming blue for primary actions
        "secondary": "#6B8E23",         # Olive green (subtle, not bright)
        "background": "#1E1E1E",        # Dark background
        "surface": "#2D2D2D",           # Lighter surface
        "card": "#252525",              # Card background
        "text_primary": "#E0E0E0",      # Light text
        "text_secondary": "#A0A0A0",   # Gray text
        "accent": "#FF6B6B",           # Red accent for actions
        "success": "#51CF66",          # Soft green for success/online
        "warning": "#FFA726",          # Orange for warnings
        "error": "#EF5350",            # Red for errors
        "border": "#404040",            # Subtle border
        "hover": "#3A3A3A",            # Hover effect
        "disabled": "#505050",         # Disabled state
    }
    
    LIGHT_THEME = {
        "primary": "#1976D2",          # Blue for primary actions
        "secondary": "#558B2F",       # Green for secondary
        "background": "#FAFAFA",      # Light background
        "surface": "#FFFFFF",          # White surface
        "card": "#F5F5F5",            # Card background
        "text_primary": "#212121",     # Dark text
        "text_secondary": "#757575",   # Gray text
        "accent": "#E53935",          # Red accent
        "success": "#43A047",         # Green for success
        "warning": "#FB8C00",         # Orange for warnings
        "error": "#E53935",           # Red for errors
        "border": "#E0E0E0",          # Light border
        "hover": "#EEEEEE",           # Hover effect
        "disabled": "#BDBDBD",        # Disabled state
    }
    
    @staticmethod
    def get_theme(theme_name: str = "dark") -> Dict[str, str]:
        """
        Get theme colors by name.
        
        Args:
            theme_name: Theme name ("dark" or "light")
            
        Returns:
            Dictionary of color values
        """
        if theme_name == "light":
            return Theme.LIGHT_THEME.copy()
        return Theme.DARK_THEME.copy()
    
    @staticmethod
    def get_stylesheet(theme_name: str = "dark") -> str:
        """
        Generate QSS stylesheet for the theme.
        
        Args:
            theme_name: Theme name ("dark" or "light")
            
        Returns:
            QSS stylesheet string
        """
        colors = Theme.get_theme(theme_name)
        
        return f"""
        /* Main Window */
        QMainWindow {{
            background: {colors["background"]};
            color: {colors["text_primary"]};
        }}
        
        /* Widgets */
        QWidget {{
            background: {colors["background"]};
            color: {colors["text_primary"]};
            font-family: 'Segoe UI', Arial, sans-serif;
        }}
        
        /* Buttons */
        QPushButton {{
            background: {colors["primary"]};
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: 500;
            font-size: 14px;
        }}
        QPushButton:hover {{
            background: {colors["hover"]};
        }}
        QPushButton:pressed {{
            background: {colors["accent"]};
        }}
        QPushButton:disabled {{
            background: {colors["disabled"]};
            color: {colors["text_secondary"]};
        }}
        /* Icon-only buttons */
        QPushButton[text=""] {{
            padding: 8px;
            min-width: 32px;
            min-height: 32px;
        }}
        
        /* Text Input */
        QLineEdit, QTextEdit {{
            background: {colors["surface"]};
            color: {colors["text_primary"]};
            border: 1px solid {colors["border"]};
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 14px;
        }}
        QLineEdit:focus, QTextEdit:focus {{
            border: 2px solid {colors["primary"]};
        }}
        
        /* ComboBox */
        QComboBox {{
            background: {colors["surface"]};
            color: {colors["text_primary"]};
            border: 1px solid {colors["border"]};
            border-radius: 6px;
            padding: 6px 12px;
            font-size: 14px;
        }}
        QComboBox:hover {{
            border: 1px solid {colors["primary"]};
        }}
        QComboBox::drop-down {{
            border: none;
            padding-right: 8px;
        }}
        QComboBox QAbstractItemView {{
            background: {colors["surface"]};
            color: {colors["text_primary"]};
            border: 1px solid {colors["border"]};
            selection-background-color: {colors["primary"]};
            selection-color: white;
        }}
        
        /* Scroll Area */
        QScrollArea {{
            border: none;
            background: {colors["background"]};
        }}
        QScrollBar:vertical {{
            background: {colors["surface"]};
            width: 12px;
            border: none;
        }}
        QScrollBar::handle:vertical {{
            background: {colors["border"]};
            border-radius: 6px;
            min-height: 20px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {colors["text_secondary"]};
        }}
        
        /* Status Bar */
        QStatusBar {{
            background: {colors["surface"]};
            border-top: 1px solid {colors["border"]};
            color: {colors["text_primary"]};
            font-size: 12px;
        }}
        
        /* Labels */
        QLabel {{
            color: {colors["text_primary"]};
            font-size: 14px;
        }}
        
        /* Frames */
        QFrame {{
            background: {colors["surface"]};
            border: 1px solid {colors["border"]};
            border-radius: 8px;
        }}
        
        /* Group Box */
        QGroupBox {{
            border: 1px solid {colors["border"]};
            border-radius: 6px;
            margin-top: 12px;
            padding-top: 12px;
            font-weight: 500;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px;
        }}
        
        /* Tab Widget */
        QTabWidget::pane {{
            border: 1px solid {colors["border"]};
            background: {colors["surface"]};
        }}
        QTabBar::tab {{
            background: {colors["surface"]};
            color: {colors["text_secondary"]};
            border: 1px solid {colors["border"]};
            padding: 8px 16px;
            margin-right: 2px;
        }}
        QTabBar::tab:selected {{
            background: {colors["primary"]};
            color: white;
        }}
        QTabBar::tab:hover {{
            background: {colors["hover"]};
        }}
        
        /* Menu Bar */
        QMenuBar {{
            background: {colors["surface"]};
            color: {colors["text_primary"]};
            border-bottom: 1px solid {colors["border"]};
        }}
        QMenuBar::item:selected {{
            background: {colors["hover"]};
        }}
        QMenu {{
            background: {colors["surface"]};
            color: {colors["text_primary"]};
            border: 1px solid {colors["border"]};
        }}
        QMenu::item:selected {{
            background: {colors["primary"]};
            color: white;
        }}
        """
    
    @staticmethod
    def get_status_color(is_online: bool) -> str:
        """
        Get color for status indicator.
        
        Args:
            is_online: True if online, False if offline
            
        Returns:
            Color hex code
        """
        colors = Theme.DARK_THEME
        return colors["success"] if is_online else colors["error"]

