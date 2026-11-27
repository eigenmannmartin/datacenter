# Rechenbox: datacenter in a box

Website: [rechenbox.ch](https://rechenbox.ch)

A managed private cloud that sits in the office of Swiss SMEs with 10–100 staff that handle confidential data (fiduciaries, law offices, medical practices, architects and engineers). One monthly fee covers hardware, software, local backup, security and operations; the backup copy in a Swiss data centre is an add-on.

- **Business plan, refined idea and technology:** [Claude Doc](https://claude.ai/artifact/CX8RcnpM9WqbKQivpnVjQs)
- **Engagement-test website:** [`site/`](site/README.md) (Cloudflare Pages + D1; German with English toggle)
- **Hardware and financing:** [`docs/hardware.md`](docs/hardware.md): three or more small nodes in a 10-inch rack, and how the hardware is financed
- **Financial model:** [`docs/model.py`](docs/model.py), run with `python3 docs/model.py`
- **Picture of the box:** [`docs/rack.py`](docs/rack.py) builds the cabinet as a 3D model and renders the images on the landing page (needs Blender as a Python module: `pip install bpy numpy pillow`)
- **Market research (quick scan, November 2026):** [`docs/market.md`](docs/market.md): who else sells to these offices, where the prices sit, what drives demand
