import os
import sys

# Configure environment variables at the absolute entrypoint
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import pytest

if __name__ == "__main__":
    # Forward command line arguments to pytest
    args = sys.argv[1:]
    if not args:
        args = ["backend/tests/test_pipeline.py"]
    sys.exit(pytest.main(args))
