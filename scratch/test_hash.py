def int32(x):
    x = x & 0xFFFFFFFF
    if x > 0x7FFFFFFF:
        return x - 0x100000000
    return x

def to_signed_byte(b):
    if b > 127:
        return b - 256
    return b

def unsigned_right_shift(val, n):
    return (val & 0xFFFFFFFF) >> n

def rotate_left(val, amount):
    val &= 0xFFFFFFFF
    return int32((val << amount) | (val >> (32 - amount)))

def mix32(k, hash_val):
    k = int32(k * -862048943)
    k = rotate_left(k, 15)
    k = int32(k * 461845907)
    hash_val = int32(hash_val ^ k)
    return int32(int32(rotate_left(hash_val, 13) * 5) + -430675100)

def getHash(data, offset, hash_val, idx, k1):
    k1 = int32(k1 ^ to_signed_byte(data[offset + idx]))
    k1 = int32(k1 * -862048943)
    k1 = rotate_left(k1, 15)
    k1 = int32(k1 * 461845907)
    hash_val = int32(hash_val ^ k1)
    return hash_val

def fmix32(length, hash_val):
    hash_val = int32(hash_val ^ length)
    hash_val = int32(hash_val ^ unsigned_right_shift(hash_val, 16))
    hash_val = int32(hash_val * -2048144789)
    hash_val = int32(hash_val ^ unsigned_right_shift(hash_val, 13))
    hash_val = int32(hash_val * -1028477387)
    hash_val = int32(hash_val ^ unsigned_right_shift(hash_val, 16))
    return hash_val

def hash32(data: bytes, offset=0, length=None, seed=104729):
    if length is None:
        length = len(data)
    hash_val = seed
    nblocks = length >> 2
    
    for idx in range(nblocks):
        i = idx << 2
        k = data[offset + i] | (data[offset + i + 1] << 8) | (data[offset + i + 2] << 16) | (data[offset + i + 3] << 24)
        k = int32(k)
        hash_val = mix32(k, hash_val)
        
    idx = nblocks << 2
    k1 = 0
    rem = length - idx
    if rem == 3:
        k1 = int32(k1 ^ (int32(to_signed_byte(data[offset + idx + 2]) << 16)))
        k1 = int32(k1 ^ (int32(to_signed_byte(data[offset + idx + 1]) << 8)))
        hash_val = getHash(data, offset, hash_val, idx, k1)
    elif rem == 2:
        k1 = int32(k1 ^ (int32(to_signed_byte(data[offset + idx + 1]) << 8)))
        hash_val = getHash(data, offset, hash_val, idx, k1)
    elif rem == 1:
        hash_val = getHash(data, offset, hash_val, idx, k1)
        
    return fmix32(length, hash_val)


tests = ["a", "ab", "abc", "abcd", "abcde", "abcdef", "1234567890", "C10000001", "C10000002", "你好", "测试123"]
for t in tests:
    print(f"{t}:{hash32(t.encode('utf-8'))}")
