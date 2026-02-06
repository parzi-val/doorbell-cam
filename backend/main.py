import sys
import os
import numpy as np
import cv2
# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Disable OpenCV internal threading to prevent GIL/Thread state crashes
# during multi-threaded inference and video writing.
cv2.setNumThreads(0)

from backend.core.pipeline import Pipeline

def main():
    pipeline = Pipeline()
    pipeline.run()

if __name__ == "__main__":
    main()
