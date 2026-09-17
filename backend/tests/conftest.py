import os
import sys

# Globally configure environment variables for all tests before PyTorch loads
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
