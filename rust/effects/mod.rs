//! Effect renderer compute kernels
//!
//! Pure computation functions that fill pixel matrices.
//! Python wrappers maintain traitlets config and call these.

pub mod aurora;
pub mod embers;
pub mod kaleidoscope;
pub mod metaballs;
pub mod nebula;
pub mod ocean;
pub mod plasma;
pub mod vortex;

pub use aurora::draw_aurora;
pub use embers::draw_embers;
pub use kaleidoscope::{compute_polar_map, draw_kaleidoscope};
pub use metaballs::draw_metaballs;
pub use nebula::draw_nebula;
pub use ocean::draw_ocean;
pub use plasma::draw_plasma;
pub use vortex::draw_vortex;
