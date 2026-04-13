public class TestShard {
    public static void main(String[] args) {
        String[] tests = {"a", "ab", "abc", "abcd", "abcde", "abcdef", "1234567890", "C10000001", "C10000002"};
        for (String t : tests) {
             System.out.println(t + " -> " + CustNoShardingUtil.determineShardingIdByCustNo(t, 8));
        }
    }
}

class CustNoShardingUtil {
    public static String determineShardingIdByCustNo(String custNo, int totalShardingTableNumber) {
        String shardingId = null;
        int hashKey = HashUtils.hash32(custNo);
        if (hashKey < 0) {
            hashKey = -hashKey;
        }
        int shardingNumber = hashKey % totalShardingTableNumber + 1;
        shardingId = "0000" + String.valueOf(shardingNumber);
        shardingId = shardingId.substring(shardingId.length() - 4);
        return shardingId;
    }
}
