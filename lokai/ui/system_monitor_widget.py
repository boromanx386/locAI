"""
Compact system monitor widget for header (CPU / RAM via psutil, GPU via pynvml).
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import QTimer

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import pynvml
    PYNVML_AVAILABLE = True
except ImportError:
    PYNVML_AVAILABLE = False


class SystemMonitorWidget(QWidget):
    """Compact one-line CPU, RAM and GPU display for menu bar corner."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(8, 2, 8, 2)
        self._layout.setSpacing(12)
        self._label = QLabel("—")
        self._label.setObjectName("systemMonitorLabel")
        self._layout.addWidget(self._label)

        self._nvml_handle = None
        if PYNVML_AVAILABLE:
            try:
                pynvml.nvmlInit()
                self._nvml_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            except Exception:
                self._nvml_handle = None

        if not PSUTIL_AVAILABLE:
            self._label.setText("psutil not installed")
            return

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update)
        self._timer.start(1500)
        self._update()

    def _gpu_str(self):
        if not PYNVML_AVAILABLE or self._nvml_handle is None:
            return ""
        try:
            util = pynvml.nvmlDeviceGetUtilizationRates(self._nvml_handle)
            mem = pynvml.nvmlDeviceGetMemoryInfo(self._nvml_handle)
            used_gb = mem.used / (1024 ** 3)
            total_gb = mem.total / (1024 ** 3)
            return f"  |  GPU {util.gpu}%  |  VRAM {used_gb:.1f}/{total_gb:.1f} GB"
        except Exception:
            return ""

    def _update(self):
        if not PSUTIL_AVAILABLE:
            return
        try:
            cpu = psutil.cpu_percent(interval=0)
            per_core = psutil.cpu_percent(interval=0, percpu=True)
            max_core = max(per_core) if per_core else 0
            mem = psutil.virtual_memory()
            gpu_part = self._gpu_str()
            self._label.setText(
                f"CPU {cpu:.0f}% (max core {max_core:.0f}%)  |  RAM {mem.percent:.0f}%{gpu_part}"
            )
        except Exception:
            self._label.setText("—")
