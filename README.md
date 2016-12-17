uChroma - Userspace Razer Chroma Driver
  (C) 2016 - Steve Kondik (cyanogen)

Based on work by Tim Theede and Terry Cain
https://github.com/terrycain/razer-drivers

See the LICENSE file for information regarding the GPLv2.

The Razer Chroma input peripherials are exotic, but fully HID-compliant
and work well with the generic HID drivers in the Linux kernel. For
this reason, it's unlikely that a custom driver which adds features such
as LED controls and macro keys will be accepted upstream.  Fortunately,
these features can be implemented in userspace using the hidraw interface.

uChroma is an experimental attempt at replicating all functionality of
the original kernel drivers in userspace on top of the generic HID driver.

