//! Effect renderer compute kernels
//!
//! Pure computation functions that fill pixel matrices.
//! Python wrappers maintain traitlets config and call these.

pub mod aurora;

pub use aurora::draw_aurora;
