#!/usr/bin/env python3
"""Django command-line entry point for the Talk2Draw project."""

import os
import sys


def main() -> None:
    """Run Django's management command dispatcher."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "talk2draw_project.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
