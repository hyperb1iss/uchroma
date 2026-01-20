//! Benchmarks for uchroma native extensions
//!
//! Run with: cargo bench

use std::hint::black_box;

use _native::{blend_full_impl, blend_screen_impl, fast_crc_impl};
use criterion::{criterion_group, criterion_main, BenchmarkId, Criterion, Throughput};

/// Benchmark CRC calculation
///
/// This is called for every USB HID report during animations,
/// so it's critical that it's fast.
fn bench_crc(c: &mut Criterion) {
    // Simulate a typical 90-byte HID report
    let report: Vec<u8> = (0..90).map(|i| (i * 7 + 13) as u8).collect();

    let mut group = c.benchmark_group("crc");
    group.throughput(Throughput::Bytes(86)); // We XOR 86 bytes

    group.bench_function("fast_crc", |b| b.iter(|| fast_crc_impl(black_box(&report))));

    // Compare with a naive Python-style loop
    group.bench_function("naive_loop", |b| {
        b.iter(|| {
            let buf = black_box(&report);
            buf[1..87].iter().fold(0u8, |crc, &byte| crc ^ byte)
        })
    });

    group.finish();
}

/// Benchmark throughput at animation frame rates
fn bench_crc_throughput(c: &mut Criterion) {
    let report: Vec<u8> = (0..90).map(|i| (i * 7 + 13) as u8).collect();

    let mut group = c.benchmark_group("crc_throughput");

    // At 30 FPS, we need to process 30 reports per second
    // At 60 FPS (optimistic), 60 reports per second
    // For a keyboard with 6 rows, that's 6 reports per frame

    // Simulate 6 rows at 30 FPS = 180 CRC calculations per second
    group.bench_function("180_crcs_per_sec", |b| {
        b.iter(|| {
            for _ in 0..180 {
                let _ = fast_crc_impl(black_box(&report));
            }
        })
    });

    group.finish();
}

/// Benchmark blend_screen at various frame sizes.
///
/// Tests the core screen blend operation used in layer compositing.
/// This is called multiple times per frame when layers are stacked.
fn bench_blend_screen(c: &mut Criterion) {
    let mut group = c.benchmark_group("blend_screen");

    // Test sizes matching typical LED matrix dimensions
    let sizes: &[(usize, usize)] = &[(32, 32), (64, 64), (128, 128)];

    for &(h, w) in sizes {
        let elements = h * w * 3; // RGB, no alpha for simple blend
        group.throughput(Throughput::Elements(elements as u64));

        // Create test data with realistic RGB values
        let base: Vec<f64> = (0..elements)
            .map(|i| (i as f64 * 0.1).sin() * 0.5 + 0.5)
            .collect();
        let layer: Vec<f64> = (0..elements)
            .map(|i| (i as f64 * 0.2).cos() * 0.5 + 0.5)
            .collect();
        let mut output = vec![0.0f64; elements];

        group.bench_with_input(
            BenchmarkId::new("rust", format!("{}x{}", h, w)),
            &(h, w),
            |b, _| {
                b.iter(|| {
                    blend_screen_impl(
                        black_box(&base),
                        black_box(&layer),
                        black_box(&mut output),
                    )
                })
            },
        );
    }

    group.finish();
}

/// Benchmark full blend with alpha composition.
///
/// Tests the complete blend pipeline including alpha handling,
/// which is the hot path during animation compositing.
fn bench_blend_full(c: &mut Criterion) {
    let mut group = c.benchmark_group("blend_full");

    let sizes: &[(usize, usize)] = &[(32, 32), (64, 64), (128, 128)];

    for &(h, w) in sizes {
        let elements = h * w * 4; // RGBA
        group.throughput(Throughput::Elements(elements as u64));

        // Create RGBA test data
        let base: Vec<f64> = (0..elements)
            .enumerate()
            .map(|(i, _)| {
                if i % 4 == 3 {
                    0.9 // Alpha channel
                } else {
                    (i as f64 * 0.1).sin() * 0.5 + 0.5
                }
            })
            .collect();
        let layer: Vec<f64> = (0..elements)
            .enumerate()
            .map(|(i, _)| {
                if i % 4 == 3 {
                    0.7 // Alpha channel
                } else {
                    (i as f64 * 0.2).cos() * 0.5 + 0.5
                }
            })
            .collect();
        let mut output = vec![0.0f64; elements];

        group.bench_with_input(
            BenchmarkId::new("rust", format!("{}x{}", h, w)),
            &(h, w),
            |b, _| {
                b.iter(|| {
                    blend_full_impl(
                        black_box(&base),
                        black_box(&layer),
                        black_box(&mut output),
                        black_box(0.8), // 80% opacity
                    )
                })
            },
        );
    }

    group.finish();
}

criterion_group!(benches, bench_crc, bench_crc_throughput, bench_blend_screen, bench_blend_full);
criterion_main!(benches);
