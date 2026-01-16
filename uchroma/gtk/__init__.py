# UChroma GTK4 Frontend
# A gorgeous, reactive RGB control interface

__version__ = "0.1.0"


def main():
    """Main entry point for uchroma-gtk."""
    from .application import main as app_main  # noqa: PLC0415

    return app_main()
