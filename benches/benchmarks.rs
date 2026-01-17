//! Benchmarks for uchroma native extensions
//!
//! Run with: cargo bench

use std::hint::black_box;

use _native::fast_crc_impl;
use criterion::{criterion_group, criterion_main, Criterion, Throughput};

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

criterion_group!(benches, bench_crc, bench_crc_throughput);
criterion_main!(benches);
