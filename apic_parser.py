#!/usr/bin/env python3
"""
APIC Parser - Main entry point
Run this script to parse and extract APIC configuration objects
"""
import sys
from core.parser import main

if __name__ == "__main__":
    sys.exit(main())