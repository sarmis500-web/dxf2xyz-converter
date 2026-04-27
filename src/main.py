import locale
import sys

# Force C locale for numeric formatting before anything else loads.
# Prevents decimal-comma corruption on French/German Windows.
locale.setlocale(locale.LC_NUMERIC, "C")

def main():
    # Only import gui after locale is pinned
    from gui import launch_gui
    launch_gui()

if __name__ == "__main__":
    main()
