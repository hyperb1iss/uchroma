//! CRC calculation for Razer USB HID reports
//!
//! XOR checksum over bytes 1-87 of the report buffer.
//! Called for every USB report during animations - hot path.
//!
//! Optimizations:
//! - Process 8 bytes at a time using u64 XOR
//! - Final horizontal XOR to reduce to u8

use pyo3::prelude::*;

/// Pure Rust CRC implementation with SIMD-style u64 processing.
/// XORs 8 bytes at a time, then reduces to single byte.
///
/// Returns 0 for buffers smaller than 87 bytes (defensive, avoids panic).
#[inline]
pub fn fast_crc_impl(buf: &[u8]) -> u8 {
    // Range: bytes 1..87 (86 bytes total)
    // Guard against short buffers to prevent panic
    if buf.len() < 87 {
        return 0;
    }

    // Process as 10 u64s (80 bytes) + 6 remaining bytes
    let slice = &buf[1..87]; // 86 bytes

    // XOR 8 bytes at a time using u64
    let mut acc: u64 = 0;
    let chunks = slice.chunks_exact(8);
    let remainder = chunks.remainder();

    for chunk in chunks {
        // Safe: chunks_exact guarantees 8 bytes
        let val = u64::from_ne_bytes(chunk.try_into().unwrap());
        acc ^= val;
    }

    // Horizontal XOR: fold u64 down to u8
    // XOR all 8 bytes of acc together
    let mut result = (acc & 0xFF) as u8;
    result ^= ((acc >> 8) & 0xFF) as u8;
    result ^= ((acc >> 16) & 0xFF) as u8;
    result ^= ((acc >> 24) & 0xFF) as u8;
    result ^= ((acc >> 32) & 0xFF) as u8;
    result ^= ((acc >> 40) & 0xFF) as u8;
    result ^= ((acc >> 48) & 0xFF) as u8;
    result ^= ((acc >> 56) & 0xFF) as u8;

    // XOR remaining bytes
    for &byte in remainder {
        result ^= byte;
    }

    result
}

/// Calculate XOR checksum for a Razer HID report buffer.
///
/// The checksum is computed by XORing bytes 1 through 86 (inclusive).
/// This matches the original Cython implementation.
///
/// # Arguments
/// * `buf` - Raw bytes of the HID report (must be at least 87 bytes)
///
/// # Returns
/// The computed CRC as a single byte
///
/// # Errors
/// Returns `ValueError` if buffer is smaller than 87 bytes.
#[pyfunction]
pub fn fast_crc(buf: &[u8]) -> PyResult<u8> {
    if buf.len() < 87 {
        return Err(pyo3::exceptions::PyValueError::new_err(format!(
            "Buffer must be at least 87 bytes, got {}",
            buf.len()
        )));
    }
    Ok(fast_crc_impl(buf))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_crc_zeros() {
        let buf = [0u8; 90];
        assert_eq!(fast_crc_impl(&buf), 0);
    }

    #[test]
    fn test_crc_ones() {
        let mut buf = [0u8; 90];
        // Set all bytes in checksum range to 1
        buf[1..87].fill(1);
        // XOR of 86 ones = 0 (even count)
        assert_eq!(fast_crc_impl(&buf), 0);
    }

    #[test]
    fn test_crc_pattern() {
        let mut buf = [0u8; 90];
        buf[1] = 0xAA;
        buf[2] = 0x55;
        // 0xAA ^ 0x55 = 0xFF
        assert_eq!(fast_crc_impl(&buf), 0xFF);
    }

    #[test]
    fn test_crc_ignores_byte_zero() {
        let mut buf = [0u8; 90];
        buf[0] = 0xFF; // Should be ignored
        buf[1] = 0x42;
        assert_eq!(fast_crc_impl(&buf), 0x42);
    }

    #[test]
    fn test_crc_ignores_bytes_after_86() {
        let mut buf = [0u8; 90];
        buf[87] = 0xFF; // Should be ignored
        buf[88] = 0xFF; // Should be ignored
        assert_eq!(fast_crc_impl(&buf), 0);
    }

    #[test]
    fn test_crc_matches_naive() {
        // Test with random-ish data
        let buf: Vec<u8> = (0..90).map(|i| (i * 7 + 13) as u8).collect();

        // Naive implementation
        let naive: u8 = buf[1..87].iter().fold(0, |acc, &b| acc ^ b);

        assert_eq!(fast_crc_impl(&buf), naive);
    }

    #[test]
    fn test_crc_short_buffer_returns_zero() {
        // Buffer shorter than 87 bytes should return 0 (defensive)
        let short_buf = [0xFFu8; 50];
        assert_eq!(fast_crc_impl(&short_buf), 0);

        // Exactly 86 bytes (one short) should also return 0
        let almost_buf = [0xFFu8; 86];
        assert_eq!(fast_crc_impl(&almost_buf), 0);

        // Exactly 87 bytes should work
        let mut exact_buf = [0u8; 87];
        exact_buf[1] = 0x42;
        assert_eq!(fast_crc_impl(&exact_buf), 0x42);
    }
}
