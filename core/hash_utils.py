"""
core/hash_utils.py
该模块实现了 Java 版本的 MurmurHash3 算法 (HashUtils.hash32) 
以及对应的分片路由逻辑 (CustNoShardingUtil.determineShardingIdByCustNo)。
所有计算皆模拟了 Java 32 位有符号整数溢出及其按位操作的行为，以保证和 Java 服务端一致。
"""

def int32(x: int) -> int:
    """模拟 Java 的强转 (int) 截断，保留 32 位有符号整数"""
    x = x & 0xFFFFFFFF
    if x > 0x7FFFFFFF:
        return x - 0x100000000
    return x

def to_signed_byte(b: int) -> int:
    """Java 中的 byte 为有符号整型 (-128 到 127)"""
    if b > 127:
        return b - 256
    return b

def unsigned_right_shift(val: int, n: int) -> int:
    """模拟 Java 的 >>> 无符号右移"""
    return (val & 0xFFFFFFFF) >> n

def rotate_left(val: int, amount: int) -> int:
    """模拟 Java 的 Integer.rotateLeft"""
    val &= 0xFFFFFFFF
    return int32((val << amount) | (val >> (32 - amount)))

def _mix32(k: int, hash_val: int) -> int:
    k = int32(k * -862048943)
    k = rotate_left(k, 15)
    k = int32(k * 461845907)
    hash_val = int32(hash_val ^ k)
    return int32(int32(rotate_left(hash_val, 13) * 5) + -430675100)

def _get_hash(data: bytes, offset: int, hash_val: int, idx: int, k1: int) -> int:
    # 注意这里还原了原 Java 代码块对 byte 无符号扩展（&0xFF）的遗漏导致的有符号移位逻辑
    k1 = int32(k1 ^ to_signed_byte(data[offset + idx]))
    k1 = int32(k1 * -862048943)
    k1 = rotate_left(k1, 15)
    k1 = int32(k1 * 461845907)
    hash_val = int32(hash_val ^ k1)
    return hash_val

def _fmix32(length: int, hash_val: int) -> int:
    hash_val = int32(hash_val ^ length)
    hash_val = int32(hash_val ^ unsigned_right_shift(hash_val, 16))
    hash_val = int32(hash_val * -2048144789)
    hash_val = int32(hash_val ^ unsigned_right_shift(hash_val, 13))
    hash_val = int32(hash_val * -1028477387)
    hash_val = int32(hash_val ^ unsigned_right_shift(hash_val, 16))
    return hash_val

def hash32(data: bytes, offset: int = 0, length: int = None, seed: int = 104729) -> int:
    """翻译自 Java 的 HashUtils.hash32"""
    if length is None:
        length = len(data)
    hash_val = seed
    nblocks = length >> 2
    
    for idx in range(nblocks):
        i = idx << 2
        # 注意: Java 里面 (data[offset + i] & 0xFF) 相当于 Python 直接读取 bytes 的元素
        k = data[offset + i] | (data[offset + i + 1] << 8) | (data[offset + i + 2] << 16) | (data[offset + i + 3] << 24)
        k = int32(k)
        hash_val = _mix32(k, hash_val)
        
    idx = nblocks << 2
    k1 = 0
    rem = length - idx
    if rem == 3:
        k1 = int32(k1 ^ (int32(to_signed_byte(data[offset + idx + 2]) << 16)))
        k1 = int32(k1 ^ (int32(to_signed_byte(data[offset + idx + 1]) << 8)))
        hash_val = _get_hash(data, offset, hash_val, idx, k1)
    elif rem == 2:
        k1 = int32(k1 ^ (int32(to_signed_byte(data[offset + idx + 1]) << 8)))
        hash_val = _get_hash(data, offset, hash_val, idx, k1)
    elif rem == 1:
        hash_val = _get_hash(data, offset, hash_val, idx, k1)
        
    return _fmix32(length, hash_val)

def java_modulo(a: int, b: int) -> int:
    """模拟 Java 的 % 求模，保留跟被除数一致的符号"""
    res = abs(a) % abs(b)
    return -res if a < 0 else res

def determine_sharding_number_by_cust_no(cust_no: str, total_sharding_table_number: int) -> int:
    """翻译自 Java 的 CustNoShardingUtil.determineShardingIdByCustNo 中的路由编号推导，直接返回整数形式"""
    hash_key = hash32(cust_no.encode('utf-8'))
    if hash_key < 0:
        hash_key = int32(-hash_key)
        
    return java_modulo(hash_key, total_sharding_table_number) + 1
