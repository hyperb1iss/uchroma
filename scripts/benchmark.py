#!/usr/bin/env python3
# ruff: noqa: PLC0415
"""
Benchmark comparisons for uchroma native extensions.

Compares Python implementations against Rust (via _native module).

Run with: uv run python scripts/benchmark.py
"""

import time
from dataclasses import dataclass

import numpy as np


@dataclass
class BenchResult:
    name: str
    iterations: int
    total_time: float

    @property
    def per_iter_ns(self) -> float:
        return (self.total_time / self.iterations) * 1e9

    @property
    def per_iter_us(self) -> float:
        return (self.total_time / self.iterations) * 1e6

    def __str__(self) -> str:
        if self.per_iter_ns < 1000:
            return f"{self.name}: {self.per_iter_ns:.2f} ns/iter"
        return f"{self.name}: {self.per_iter_us:.2f} µs/iter"


def bench(name: str, func, iterations: int = 100000) -> BenchResult:
    """Run a benchmark."""
    # Warmup
    for _ in range(min(1000, iterations // 10)):
        func()

    start = time.perf_counter()
    for _ in range(iterations):
        func()
    elapsed = time.perf_counter() - start

    return BenchResult(name, iterations, elapsed)


def python_crc(buf: bytes) -> int:
    """Pure Python CRC implementation."""
    crc = 0
    for i in range(1, 87):
        crc ^= buf[i]
    return crc


def bench_crc():
    """Benchmark CRC implementations."""
    print("\n" + "=" * 60)
    print("CRC Benchmarks")
    print("=" * 60)

    # Create test data
    report = bytes([(i * 7 + 13) % 256 for i in range(90)])

    # Python implementation
    py_result = bench("Python CRC", lambda: python_crc(report), iterations=100000)
    print(py_result)

    # Rust implementation
    try:
        from uchroma._native import fast_crc

        rust_result = bench("Rust CRC", lambda: fast_crc(report), iterations=100000)
        print(rust_result)

        speedup = py_result.per_iter_ns / rust_result.per_iter_ns
        print(f"\nRust is {speedup:.1f}x faster than Python")
    except ImportError:
        print("Rust module not available - run 'make rebuild' first")


def bench_plasma():
    """Benchmark plasma rendering."""
    print("\n" + "=" * 60)
    print("Plasma Benchmarks")
    print("=" * 60)

    # Typical keyboard dimensions
    width, height = 22, 6
    matrix = np.zeros((height, width, 4), dtype=np.float64)
    gradient = np.random.random((360, 3)).astype(np.float64)
    duration = 1.5

    # Python implementation (simplified)
    def python_plasma():
        from math import cos, pi, sin, sqrt

        glen = len(gradient)
        sin_d2 = sin(duration / 2.0)
        cos_d3 = cos(duration / 3.0)
        sin_d5 = sin(duration / 5.0)
        aspect = width / height

        for col in range(width):
            for row in range(height):
                y = row / (height * aspect)
                x = col / width

                val = sin(2.0 * (x * sin_d2 + y * cos_d3) + duration)
                cx = x * sin_d5
                cy = y * cos_d3
                val += sin(sqrt(20.0 * (cx * cx + cy * cy) + 1.0) + duration)

                pos = glen * ((1.0 + sin(pi * val)) / 2.0)
                idx = max(0, min(int(pos) - 1, glen - 1))
                matrix[row][col] = (*gradient[idx], 1.0)

    py_result = bench("Python Plasma", python_plasma, iterations=1000)
    print(py_result)

    # Rust implementation
    try:
        from uchroma._native import draw_plasma

        def rust_plasma():
            draw_plasma(width, height, matrix, duration, gradient)

        rust_result = bench("Rust Plasma", rust_plasma, iterations=1000)
        print(rust_result)

        speedup = py_result.per_iter_us / rust_result.per_iter_us
        print(f"\nRust is {speedup:.1f}x faster than Python")
    except ImportError:
        print("Rust module not available - run 'make rebuild' first")


def bench_metaballs():
    """Benchmark metaballs rendering."""
    print("\n" + "=" * 60)
    print("Metaballs Benchmarks")
    print("=" * 60)

    # Typical keyboard dimensions
    width, height = 22, 6
    matrix = np.zeros((height, width, 4), dtype=np.float64)
    gradient = np.random.random((360, 3)).astype(np.float64)

    # 4 blobs: [x, y, radius, hue_idx]
    blobs = np.array(
        [
            [5.0, 2.0, 3.0, 0],
            [15.0, 3.0, 2.5, 1],
            [10.0, 4.0, 2.8, 2],
            [18.0, 1.0, 2.2, 3],
        ],
        dtype=np.float64,
    )

    threshold = 1.0
    glow_falloff = 2.0
    base_brightness = 0.2

    # Python implementation
    def python_metaballs():
        grad_len = len(gradient)
        half_thresh = threshold * 0.5

        for row in range(height):
            for col in range(width):
                field = 0.0
                total_weight = 0.0
                weighted_hue = 0.0

                for b in blobs:
                    dx = col - b[0]
                    dy = row - b[1]
                    dist_sq = dx * dx + dy * dy + 0.1
                    radius_sq = b[2] * b[2]
                    contribution = radius_sq / dist_sq
                    field += contribution
                    blob_hue = (int(b[3]) * 60) % grad_len
                    weighted_hue += blob_hue * contribution
                    total_weight += contribution

                if field > threshold:
                    brightness = min(1.0, (field - threshold) * glow_falloff * 0.5 + 0.5)
                    hue_idx = int(weighted_hue / total_weight) % grad_len
                    r, g, b = gradient[hue_idx]
                    matrix[row][col] = (r * brightness, g * brightness, b * brightness, 1.0)
                elif field > half_thresh:
                    glow = (field - half_thresh) / half_thresh
                    brightness = base_brightness + glow * 0.3
                    hue_idx = int(weighted_hue / total_weight) % grad_len
                    r, g, b = gradient[hue_idx]
                    matrix[row][col] = (r * brightness, g * brightness, b * brightness, 1.0)
                else:
                    matrix[row][col] = (
                        base_brightness * 0.3,
                        base_brightness * 0.2,
                        base_brightness * 0.4,
                        1.0,
                    )

    py_result = bench("Python Metaballs", python_metaballs, iterations=500)
    print(py_result)

    # Rust implementation
    try:
        from uchroma._native import draw_metaballs

        def rust_metaballs():
            draw_metaballs(
                width,
                height,
                matrix,
                blobs,
                gradient,
                threshold,
                glow_falloff,
                base_brightness,
            )

        rust_result = bench("Rust Metaballs", rust_metaballs, iterations=500)
        print(rust_result)

        speedup = py_result.per_iter_us / rust_result.per_iter_us
        print(f"\nRust is {speedup:.1f}x faster than Python")
    except ImportError:
        print("Rust module not available - run 'make rebuild' first")


def main():
    print("UChroma Native Extension Benchmarks")
    print("=" * 60)

    bench_crc()
    bench_plasma()
    bench_metaballs()

    print("\n" + "=" * 60)
    print("Done!")


if __name__ == "__main__":
    main()
