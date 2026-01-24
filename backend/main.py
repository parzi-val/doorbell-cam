import sys
import os
import numpy as np
# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.pipeline import Pipeline

def main():
    pipeline = Pipeline()
    pipeline.run()

if __name__ == "__main__":
    main()
