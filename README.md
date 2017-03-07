## uChroma - Razer Chroma control for Linux 


The Razer Chroma line of peripherals have flashy features such as embedded LED matrices and macro keys. This project aims to provide rich support for these features under Linux without requiring kernel modifications. 

[![Codacy Badge](https://api.codacy.com/project/badge/Grade/b38cbbbd41e74cef89438b20faeb75d1)](https://www.codacy.com/app/shade_2/uchroma?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=cyanogen/uchroma&amp;utm_campaign=Badge_Grade)



## What can it do?

* Supports Razer keyboards, mice, mouse pads, laptops, and keypads
* Enables activation of built-in hardware lighting effects
* Several custom effects included for devices with LED matrices, more on the way
* Rich animation/framebuffer API for creation of custom effects
* Optimized for low power consumption
* Simple installation and setup
* Powerful command line interface
* D-Bus API
* 100% *asyncio*-powered Python, 100% open source (LGPL)



## Installation

Packages are available for Ubuntu Yakkety:

[UChroma PPA](https://launchpad.net/~cyanogen/+archive/ubuntu/uchroma) 

	sudo add-apt-repository ppa:cyanogen/uchroma
	sudo apt update
	sudo apt install uchroma

Submit a pull request if you'd like to package for other platforms.

To install from source, clone this repository and simply run "sudo make install" which will
fetch all required dependencies automatically.

The UChroma daemon installs itself as a systemd user service. You can check the status with:

	 systemctl --user uchromad status

Be sure to uninstall any other software which might alter permissions or change behavior of the devices or kernel HID drivers.



## Usage

UChroma consists of two main executables, *uchromad* and *uchroma*. The *uchromad* executable runs in the background as a systemd user service, handles all hardware interactions, executes animations, stores preferences, and publishes several D-Bus services for clients to use. The *uchroma* command provides a uniform interface to all discovered devices. The CLI tool is based on subcommands (similar to Git), and help can be viewed at any level by passing the "-h" flag.

***

### Listing devices
	
	$ uchroma -l
	[1532:0210.00]: Blade Pro (Late 2016) (BladeProLate2016 / v0.38)
	[1532:0510.01]: Kraken 7.1 V2 (Kylie) (HN1649D04607845 / v1.135)
	
The number after the dot is the device index. You may select a target device with the -d flag using the full identifier or just the device index.

***

### Dump device state

	$ uchroma -d 0 dump
	
	Device properties:
	
	         device-0 │ Blade Pro (Late 2016)
	 ─────────────────┼────────────────────────────────────────────────────
	       brightness │ 100.0
	      device_type │ laptop
	   driver_version │ 0.99
	 firmware_version │ v0.38
	       has_matrix │ True
	           height │ 6
	              key │ 1532:0210.00
	      key_mapping │ {'KEY_F12': [[0, 14]], 'KEY_ENTER': [[3, 15], [(...)
	     manufacturer │ Razer
	       product_id │ 528
	    serial_number │ BladeProLate2016
	        suspended │ False
	         sys_path │ /sys/devices/pci0000:00/0000:00:14.0/usb1/1-8
	        vendor_id │ 5426
	            width │ 25
	
	
	
	 Current LED state:
	
	             logo │ LED: Logo
	 ─────────────────┼────────────────────────────────────────────────────
	       brightness │ 0.0
	          (float) │ a float
	                  │ min: 0.0, max: 100.0, default: 0.0
	 ─────────────────┼────────────────────────────────────────────────────
	            color │  #000000 
	          (color) │ a color
	                  │ default: green
	 ─────────────────┼────────────────────────────────────────────────────
	             mode │ STATIC
	         (choice) │ one of: blink, pulse, spectrum, static
	                  │ default: STATIC
	
	
	
	 Current animation renderer state:
	
	           plasma │ Colorful moving blobs of plasma
	 ─────────────────┼────────────────────────────────────────────────────
	           author │ Steve Kondik
	      description │ Colorful moving blobs of plasma
	             name │ Plasma
	          version │ v1.0
	 ─────────────────┼────────────────────────────────────────────────────
	 background_color │  #000000 
	          (color) │ a color
	                  │ default: black
	 ─────────────────┼────────────────────────────────────────────────────
	     color_scheme │  #004777  #a30000  #ff7700  #efd28d  #00afb5 
	    (colorscheme) │ a list of colors
	                  │ min length: 2
	 ─────────────────┼────────────────────────────────────────────────────
	              fps │ 15.0
	          (float) │ a float
	                  │ min: 0.0, max: 30, default: 15
	 ─────────────────┼────────────────────────────────────────────────────
	  gradient_length │ 360
	            (int) │ an int
	                  │ min: 0, max: None, default: 360
	 ─────────────────┼────────────────────────────────────────────────────
	           preset │ Qap
	         (choice) │ one of: best, bluticas, bright, emma, newer, qa(...)
	                  │ default: Qap


***

### Built-in effects

Built-in effects are executed entirely by the hardware, and the supported types and options vary wildly between models.

#### List available effects:

	 $ uchroma -d 0 fx list
	
	 Built-in effects and arguments:
	
	          breathe │ Colors pulse in and out
	 ─────────────────┼────────────────────────────────────────────────────
	           colors │ colorscheme: max length: 2
	
	
	          disable │ Disable all effects
	
	
	             fire │ Keys on fire
	 ─────────────────┼────────────────────────────────────────────────────
	            color │ color: default: red
	            speed │ int: min: 16, max: 128, default: 64
	
	
	            morph │ Morphing colors when keys are pressed
	 ─────────────────┼────────────────────────────────────────────────────
	       base_color │ color: default: darkblue
	            color │ color: default: magenta
	            speed │ int: min: 1, max: 4, default: 2
	
	
	          rainbow │ Rainbow of hues
	 ─────────────────┼────────────────────────────────────────────────────
	           length │ int: min: 20, max: 360, default: 75
	          stagger │ int: min: 0, max: 100, default: 4
	
	
	         reactive │ Keys light up when pressed
	 ─────────────────┼────────────────────────────────────────────────────
	            color │ color: default: skyblue
	            speed │ int: min: 1, max: 4, default: 1
	
	
	           ripple │ Ripple effect when keys are pressed
	 ─────────────────┼────────────────────────────────────────────────────
	            color │ color: default: green
	            speed │ int: min: 1, max: 8, default: 3
	
	
	     ripple_solid │ Ripple effect on a solid background
	 ─────────────────┼────────────────────────────────────────────────────
	            color │ color: default: green
	            speed │ int: min: 1, max: 8, default: 3
	
	
	         spectrum │ Cycle thru all colors of the spectrum
	
	
	        starlight │ Keys sparkle with color
	 ─────────────────┼────────────────────────────────────────────────────
	           colors │ colorscheme: max length: 2
	            speed │ int: min: 1, max: 4, default: 1
	
	
	           static │ Static color
	 ─────────────────┼────────────────────────────────────────────────────
	            color │ color: default: green
	
	
	            sweep │ Colors sweep across the device
	 ─────────────────┼────────────────────────────────────────────────────
	       base_color │ color: default: black
	            color │ color: default: green
	        direction │ choice: default: RIGHT
	            speed │ int: min: 1, max: 30, default: 15
	
	
	             wave │ Waves of color
	 ─────────────────┼────────────────────────────────────────────────────
	        direction │ choice: default: RIGHT
	  trackpad_effect │ bool: default: False


#### Activate an effect:

	$ uchroma -d 0 fx fire --color magenta
	
	
#### Disable effects:

	$ uchroma -d 0 fx disable
	
***

### Brightness control

Overall brightness level of the device is represented by  a percentage from 0-100.

#### Show current brightness:

	$ uchroma -d 1 brightness
	100.00
	
	
#### Set brightness level:

	$ uchroma -d 1 brightness 85
	
***

### Animations

UChroma supports custom animations on devices which support a lighting matrix, such as Blade laptops, BlackWidow keyboards, and Mamba mice. Several animation renderers are included, and may also be provided by third-party modules (TODO). Multiple concurrent (stacked) animations are supported, and layers will be alpha-blended together. Animations may run at different frame rates, and may trigger from input events or sound. Current animation parameters are shown in the "uchroma dump" command, shown above.


#### List available animation renderers:
	
	 $ uchroma -d 0 anim list
	
	 Available renderers and arguments:
	
	            plasma │ Colorful moving blobs of plasma
	 ──────────────────┼───────────────────────────────────────────────────
	            author │ Steve Kondik
	       description │ Colorful moving blobs of plasma
	              name │ Plasma
	           version │ v1.0
	 ──────────────────┼───────────────────────────────────────────────────
	  background_color │  #000000 
	           (color) │ a color
	                   │ default: black
	 ──────────────────┼───────────────────────────────────────────────────
	      color_scheme │  #004777  #a30000  #ff7700  #efd28d  #00afb5 
	     (colorscheme) │ a list of colors
	                   │ min length: 2
	 ──────────────────┼───────────────────────────────────────────────────
	               fps │ 15.0
	           (float) │ a float
	                   │ min: 0.0, max: 30, default: 15
	 ──────────────────┼───────────────────────────────────────────────────
	   gradient_length │ 360
	             (int) │ an int
	                   │ min: 0, max: None, default: 360
	 ──────────────────┼───────────────────────────────────────────────────
	            preset │ Qap
	          (choice) │ one of: best, bluticas, bright, emma, newer, q(...)
	                   │ default: Qap
	
	
	          rainflow │ Simple flowing colors
	 ──────────────────┼───────────────────────────────────────────────────
	            author │ Steve Kondik
	       description │ Simple flowing colors
	              name │ Rainflow
	           version │ 1.0
	 ──────────────────┼───────────────────────────────────────────────────
	  background_color │ color: default: black
	        blend_mode │ string
	               fps │ float: min: 0.0, max: 30, default: 15
	           opacity │ float: min: 0.0, max: 1.0, default: 1.0
	             speed │ int: min: 0, max: 20, default: 8
	           stagger │ int: min: 0, max: 100, default: 4
	
	
	           ripples │ Ripples of color when keys are pressed
	 ──────────────────┼───────────────────────────────────────────────────
	            author │ Steve Kondik
	       description │ Ripples of color when keys are pressed
	              name │ Ripples
	           version │ 1.0
	 ──────────────────┼───────────────────────────────────────────────────
	  background_color │ color: default: black
	        blend_mode │ string
	             color │ color: default: black
	               fps │ float: min: 0.0, max: 30, default: 15
	           opacity │ float: min: 0.0, max: 1.0, default: 1.0
	            preset │ choice: default: Emma
	            random │ bool: default: True
	      ripple_width │ int: min: 1, max: 5, default: 3
	             speed │ int: min: 1, max: 9, default: 5
	

#### Start an animation:

	$ uchroma -d 0 anim add plasma --color_scheme newer
	
	
#### Add another layer:

	$ uchroma -d 0 anim add ripples
	
	
####Modify parameters of a running layer:

	$ uchroma -d 0 anim mod 0 --color-scheme emma --fps 10
	
	
#### Remove a layer:

	$ uchroma -d 0 anim del 1
	
	
#### Stop and clear animations:

	$ uchroma -d 0 anim stop
	
	

## Frequently Asked Questions

#### *My device is not recognized!*

>If you have a device which is not yet supported, you have a couple of options. If the device does not require a new protocol, it can simply be added to the appropriate YAML file under uchroma/server/data. If you like to see a particular model added, please open an issue on Github. If you've added support for a new device, please open a pull request!


#### *This is great, how can I donate hardware or fund development?*

>Razer makes a lot of devices, each with it's own quirks. If you'd like to see a piece of hardware supported, the best way to motivate me is to ship me a device to work with. If you'd like to help ensure continued development, please consider [sending a donation](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=2UQ62RBEANCHQ).


#### *How do I make a custom animation?*

>Proper documentation on this topic is forthcoming, but having a look at the bundled renderers in uchroma/fxlib should be enough to get started on. An upcoming release will support out-of-tree modules as well.  Implementations must extend **Renderer** and implement the *init*, *finish*, and *draw* methods. The animation system is a framebuffer and the draw method will be invoked at the FPS requested by your implementation. It's important to keep the FPS as low as possible to avoid unnecessary CPU usage! The draw method is called with a **Layer** object, which provides primitives for drawing shapes and setting individual pixels. The buffer of a frame is a Numpy matrix and may be manipulated directly, if desired.  Functions for performing color math and generating gradients/color schemes can be found in the *uchroma.color* module. We use **Traitlets** for user-configurable parameters. Send a pull request if you implement a new renderer and would like to have it included!
>

#### *Are you affiliated with Razer Inc?*

>Not in any way, but I won't mind if they deliver a truckload of hardware to me :)


#### *Is Windows supported?*

>No. UChroma relies on UDev and other Linux-specific subsystems to operate. 


#### *Is macro recording supported?*

>The skeleton of macro support is there, and will be finished in an upcoming release.


#### *The ripple effect seems misaligned with my keypresses!*

>This is because a mapping of keycodes to LED matrix coordinates must be provided, and the layout varies wildly among devices. Full support in the initial release is provided for the Blade Pro laptop, and a "generic" mapping is provided for other models which is almost certainly wrong. If you'd like to create a proper mapping for your device (and contribute it back!), I've created a simple tool which will help. You'll need to start *uchromad* with UCHROMA_DEV=1 set in the environment, then run "scripts/devstuff keys" from the source distribution. The tool will illuminate matrix cells and you just press the key that is lit, repeating for all cells. After creating a new mapping, it will need merged into the appropriate YAML file under uchroma/server/data (and send a pull request!). Support for cell swapping and relocation is also provided, see the Blade Pro configuration for an example of this.


#### *There are other projects with similar functionality, why this?*

>This project was born after realizing that there is zero chance to have the required code used by other projects merged into the Linux kernel since it's very specialized and can be done entirely in userspace. I also wanted rich animation support and low power consumption, which required rewriting large portions of the existing project (and my patches weren't moving forward). After implementing the initial user-space driver, I decided to keep going and try to make the hardware really shine under Linux. Choose what works best for you!


#### *Is a GUI available?*

>Not yet, but it will happen! We have a D-Bus API which provides total control of the hardware and a powerful CLI, but a GNOME frontend is definitely on the radar.


#### *How can I contribute?*

>Fork the project and send a pull request with a description of your changes. As this project is currently at the initial release stage, a lot of testing across different models is needed. Documentation is lacking, and support for more distributions is also high on the list. If you find a bug, please file an issue on Github.



## Powered by...

#### *Awesome libraries used by UChroma:*

* [Numpy](http://numpy.org)
* [Scikit-Image](http://scikit-image.org)
* [Grapefruit](https://github.com/xav/Grapefruit)
* [HIDAPI](https://github.com/NF6X/pyhidapi)
* [Traitlets](https://github.com/ipython/traitlets)
* [pydbus](https://github.com/LEW21/pydbus)
* [pyudev](https://pyudev.readthedocs.io/en/latest/)
* [python-evdev](https://python-evdev.readthedocs.io/en/latest/)
* [Gbulb](https://github.com/nathan-hoad/gbulb)



## Credits

[Copyright (C) 2017 Steve Kondik](https://github.com/cyanogen)

[Inspired by work from Tim Theede and Terry Cain](https://github.com/terrycain/razer-drivers)
 
This program is free software: you can redistribute it and/or modify it under the terms of the **GNU Lesser General Public License **as published by the Free Software Foundation, version 3.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Lesser Public License for more details.

You should have received a copy of the GNU Lesser General Public License along with this program. If not, see <http://www.gnu.org/licenses/>.
