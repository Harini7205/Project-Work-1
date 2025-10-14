import math
import numpy as np
from scipy.stats import chisquare

# --- Helper Functions ---
def calculate_entropy(data: bytes) -> float:
    """Calculate Shannon entropy of data"""
    if not data:
        return 0
    freq = [0] * 256
    for b in data:
        freq[b] += 1
    entropy = 0.0
    length = len(data)
    for f in freq:
        if f:
            p = f / length
            entropy -= p * math.log2(p)
    return entropy

def byte_difference(original: bytes, decrypted: bytes) -> int:
    """Count differing bytes between original and decrypted data"""
    return sum(o != d for o, d in zip(original, decrypted))

def byte_correlation(original: bytes, encrypted: bytes) -> float: 
    """Calculate correlation coefficient between original and encrypted bytes""" 
    if len(original) != len(encrypted): 
        raise ValueError("Files must be same length") 
    return np.corrcoef(np.frombuffer(original, dtype=np.uint8), np.frombuffer(encrypted, dtype=np.uint8))[0, 1] 

def chi_square_uniformity(data: bytes) -> float: 
    """Chi-square test to measure uniformity of byte distribution""" 
    freq = [0] * 256 
    for b in data: 
        freq[b] += 1 
    chi2, p = chisquare(freq) 
    return p
