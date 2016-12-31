### uChroma - Razer Chroma Control Library 

-------------------

The Razer Chroma input peripherials are exotic, but fully HID-compliant
and work well with the generic HID drivers in the Linux kernel. For
this reason, it's unlikely that a custom driver which adds features such
as LED controls and macro keys will be accepted upstream.  Fortunately,
these features can be implemented in userspace using standard HID commands.

uChroma is a Python library which replicates all functionality of
the original kernel drivers in userspace on top of the generic HID driver.
It also includes a basic command-line utility which can activate effects and
other features of the hardware.

-------------------

[Based on work by Tim Theede and Terry Cain](https://github.com/terrycain/razer-drivers)

See the LICENSE file for information regarding the LGPL.

This is a WORK IN PROGRESS and the API is not yet stable. It is also largely untested
on everything other than recent Blade laptops. If you have any of these peripherals and
try it out, please let me know! Documentation is lacking but will come soon.

