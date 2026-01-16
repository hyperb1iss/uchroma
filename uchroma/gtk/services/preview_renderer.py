"""
Preview Renderer Service

Renders effects locally for real-time preview visualization.
"""

import math
import time

import numpy as np
from gi.repository import GLib


class PreviewRenderer:
    """Renders effects locally for preview display."""

    def __init__(self, rows: int = 6, cols: int = 22):
        self.rows = rows
        self.cols = cols
        self.frame = np.zeros((rows, cols, 3), dtype=np.float32)

        self._effect_id = None
        self._effect_params = {}
        self._tick = 0
        self._start_time = time.time()

        self._running = False
        self._source_id = None
        self._fps = 30
        self._callback = None

    def set_size(self, rows: int, cols: int):
        """Update matrix size."""
        self.rows = rows
        self.cols = cols
        self.frame = np.zeros((rows, cols, 3), dtype=np.float32)

    def set_effect(self, effect_id: str, params: dict | None = None):
        """Set the effect to render."""
        self._effect_id = effect_id
        self._effect_params = params or {}
        self._tick = 0
        self._start_time = time.time()

    def set_callback(self, callback):
        """Set frame update callback: callback(frame: np.ndarray)."""
        self._callback = callback

    def start(self, fps: int = 30):
        """Start rendering loop."""
        if self._running:
            return

        self._fps = fps
        self._running = True
        self._source_id = GLib.timeout_add(1000 // fps, self._tick_callback)

    def stop(self):
        """Stop rendering loop."""
        if not self._running:
            return

        self._running = False
        if self._source_id:
            GLib.source_remove(self._source_id)
            self._source_id = None

    def _tick_callback(self) -> bool:
        """GLib timeout callback."""
        if not self._running:
            return False

        self._render_frame()
        self._tick += 1

        if self._callback:
            self._callback(self.frame)

        return True

    def _render_frame(self):
        """Render current frame based on effect."""
        t = time.time() - self._start_time

        if self._effect_id == "disable" or self._effect_id is None:
            self.frame.fill(0)

        elif self._effect_id == "static":
            color = self._parse_color(self._effect_params.get("color", "#e135ff"))
            self.frame[:, :] = color

        elif self._effect_id == "wave":
            self._render_wave(t)

        elif self._effect_id == "spectrum":
            self._render_spectrum(t)

        elif self._effect_id == "breathe":
            self._render_breathe(t)

        elif self._effect_id == "reactive":
            # Static preview for reactive (pulses on interaction)
            color = self._parse_color(self._effect_params.get("color", "#80ffea"))
            brightness = 0.3 + 0.2 * math.sin(t * 4)
            self.frame[:, :] = [c * brightness for c in color]

        elif self._effect_id == "starlight":
            self._render_starlight(t)

        elif self._effect_id == "plasma":
            self._render_plasma(t)

        elif self._effect_id == "rainbow":
            self._render_rainbow(t)

        else:
            self.frame.fill(0)

    def _render_wave(self, t: float):
        """Render wave effect."""
        direction = self._effect_params.get("direction", "RIGHT")
        speed = self._effect_params.get("speed", 2) * 2

        for col in range(self.cols):
            if direction == "LEFT":
                phase = (col / self.cols + t * speed * 0.1) % 1.0
            else:
                phase = (1 - col / self.cols + t * speed * 0.1) % 1.0

            # Rainbow gradient
            r, g, b = self._hsv_to_rgb(phase, 1.0, 1.0)
            self.frame[:, col] = [r, g, b]

    def _render_spectrum(self, t: float):
        """Render spectrum cycle effect."""
        hue = (t * 0.1) % 1.0
        r, g, b = self._hsv_to_rgb(hue, 1.0, 1.0)
        self.frame[:, :] = [r, g, b]

    def _render_breathe(self, t: float):
        """Render breathing effect."""
        colors = self._effect_params.get("colors") or []
        if colors:
            color1 = self._parse_color(colors[0])
            color2 = self._parse_color(colors[1] if len(colors) > 1 else colors[0])
        else:
            color1 = self._parse_color(self._effect_params.get("color1", "#e135ff"))
            color2 = self._parse_color(self._effect_params.get("color2", "#80ffea"))
        speed = self._effect_params.get("speed", 2)

        # Smooth sine wave between colors
        phase = (math.sin(t * speed * 0.5) + 1) / 2
        r = color1[0] * (1 - phase) + color2[0] * phase
        g = color1[1] * (1 - phase) + color2[1] * phase
        b = color1[2] * (1 - phase) + color2[2] * phase

        # Brightness pulse
        brightness = 0.5 + 0.5 * math.sin(t * speed * 0.5)
        self.frame[:, :] = [r * brightness, g * brightness, b * brightness]

    def _render_starlight(self, t: float):
        """Render twinkling starlight effect."""
        colors = self._effect_params.get("colors") or []
        if colors:
            color1 = self._parse_color(colors[0])
            color2 = self._parse_color(colors[1] if len(colors) > 1 else colors[0])
        else:
            color1 = self._parse_color(self._effect_params.get("color1", "#e135ff"))
            color2 = self._parse_color(self._effect_params.get("color2", "#80ffea"))

        # Base dim color
        self.frame[:, :] = [c * 0.1 for c in color1]

        # Random twinkling stars
        np.random.seed(int(t * 10) % 1000)
        for _ in range(self.rows * self.cols // 6):
            row = np.random.randint(0, self.rows)
            col = np.random.randint(0, self.cols)
            color = color1 if np.random.random() > 0.5 else color2
            brightness = 0.5 + 0.5 * np.random.random()
            self.frame[row, col] = [c * brightness for c in color]

    def _render_plasma(self, t: float):
        """Render plasma effect."""
        colors = [
            self._parse_color(self._effect_params.get("color1", "#e135ff")),
            self._parse_color(self._effect_params.get("color2", "#80ffea")),
            self._parse_color(self._effect_params.get("color3", "#ff6ac1")),
            self._parse_color(self._effect_params.get("color4", "#f1fa8c")),
        ]

        for row in range(self.rows):
            for col in range(self.cols):
                # Classic plasma formula
                x = col / self.cols
                y = row / self.rows

                v1 = math.sin(x * 10 + t)
                v2 = math.sin(10 * (x * math.sin(t / 2) + y * math.cos(t / 3)) + t)
                v3 = math.sin(math.sqrt((x - 0.5) ** 2 + (y - 0.5) ** 2) * 10 + t)
                v = (v1 + v2 + v3) / 3

                # Map to color palette
                idx = int((v + 1) / 2 * (len(colors) - 1))
                idx = max(0, min(len(colors) - 1, idx))
                frac = ((v + 1) / 2 * (len(colors) - 1)) % 1

                c1 = colors[idx]
                c2 = colors[min(idx + 1, len(colors) - 1)]

                r = c1[0] * (1 - frac) + c2[0] * frac
                g = c1[1] * (1 - frac) + c2[1] * frac
                b = c1[2] * (1 - frac) + c2[2] * frac

                self.frame[row, col] = [r, g, b]

    def _render_rainbow(self, t: float):
        """Render flowing rainbow effect."""
        speed = self._effect_params.get("speed", 1.0)

        for col in range(self.cols):
            hue = (col / self.cols + t * speed * 0.1) % 1.0
            r, g, b = self._hsv_to_rgb(hue, 1.0, 1.0)
            self.frame[:, col] = [r, g, b]

    def _parse_color(self, color_str: str) -> tuple:
        """Parse hex color to RGB floats."""
        if color_str.startswith("#"):
            color_str = color_str[1:]
        if len(color_str) == 6:
            r = int(color_str[0:2], 16) / 255
            g = int(color_str[2:4], 16) / 255
            b = int(color_str[4:6], 16) / 255
            return (r, g, b)
        return (1.0, 1.0, 1.0)

    def _hsv_to_rgb(self, h: float, s: float, v: float) -> tuple:
        """Convert HSV to RGB."""
        if s == 0:
            return (v, v, v)

        i = int(h * 6)
        f = (h * 6) - i
        p = v * (1 - s)
        q = v * (1 - s * f)
        t = v * (1 - s * (1 - f))
        i = i % 6

        if i == 0:
            return (v, t, p)
        if i == 1:
            return (q, v, p)
        if i == 2:
            return (p, v, t)
        if i == 3:
            return (p, q, v)
        if i == 4:
            return (t, p, v)
        return (v, p, q)
