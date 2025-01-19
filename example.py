import tokenize
from collections import Counter
import io

def findCommonConstants(code, length):
    tokens = []
    for tok in tokenize.generate_tokens(io.StringIO(code).readline):
        if tok.type in (tokenize.STRING, tokenize.NUMBER):
            tokens.append(tok.string)
    freq = Counter(tokens)
    return [(const,cnt) for const, cnt in freq.items() if cnt > 1 and len(str(const)) > length]

