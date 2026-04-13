public class HashUtils {
    private static final int C1_32 = -862048943;
    private static final int C2_32 = 461845907;
    private static final int R1_32 = 15;
    private static final int R2_32 = 13;
    private static final int M_32 = 5;
    private static final int N_32 = -430675100;
    public static final int DEFAULT_SEED = 104729;

    public static int hash32(byte[] data) {
        return hash32(data, 0, data.length, 104729);
    }

    public static int hash32(String data) {
        byte[] origin = data.getBytes();
        return hash32(origin, 0, origin.length, 104729);
    }

    public static int hash32(byte[] data, int offset, int length, int seed) {
        int hash = seed;
        int nblocks = length >> 2;
        int idx;
        for (idx = 0; idx < nblocks; idx++) {
            int i = idx << 2;
            int k = data[offset + i] & 0xFF | (data[offset + i + 1] & 0xFF) << 8 | (data[offset + i + 2] & 0xFF) << 16
                    | (data[offset + i + 3] & 0xFF) << 24;
            hash = mix32(k, hash);
        }
        idx = nblocks << 2;
        int k1 = 0;
        if (length - idx == 3) {
            k1 ^= data[offset + idx + 2] << 16;
            k1 ^= data[offset + idx + 1] << 8;
            hash = getHash(data, offset, hash, idx, k1);
        } else if (length - idx == 2) {
            k1 ^= data[offset + idx + 1] << 8;
            hash = getHash(data, offset, hash, idx, k1);
        } else if (length - idx == 1) {
            hash = getHash(data, offset, hash, idx, k1);
        }
        return fmix32(length, hash);
    }

    private static int getHash(byte[] data, int offset, int hash, int idx, int k1) {
        k1 ^= data[offset + idx];
        k1 *= -862048943;
        k1 = Integer.rotateLeft(k1, 15);
        k1 *= 461845907;
        hash ^= k1;
        return hash;
    }

    private static int mix32(int k, int hash) {
        k *= -862048943;
        k = Integer.rotateLeft(k, 15);
        k *= 461845907;
        hash ^= k;
        return Integer.rotateLeft(hash, 13) * 5 + -430675100;
    }

    private static int fmix32(int length, int hash) {
        hash ^= length;
        hash ^= hash >>> 16;
        hash *= -2048144789;
        hash ^= hash >>> 13;
        hash *= -1028477387;
        hash ^= hash >>> 16;
        return hash;
    }

    public static void main(String[] args) {
        String[] tests = {"a", "ab", "abc", "abcd", "abcde", "abcdef", "1234567890", "C10000001", "C10000002", "你好", "测试123"};
        for (String t : tests) {
            System.out.println(t + ":" + hash32(t));
        }
    }
}
