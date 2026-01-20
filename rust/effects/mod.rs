//! Effect renderer compute kernels
//!
//! Pure computation functions that fill pixel matrices.
//! Python wrappers maintain traitlets config and call these.

pub mod aurora;
pub mod metaballs;
pub mod ocean;
pub mod plasma;

pub use aurora::draw_aurora;
pub use metaballs::draw_metaballs;
pub use ocean::draw_ocean;
pub use plasma::draw_plasma;
