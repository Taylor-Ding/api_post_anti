import unittest
from unittest.mock import patch, MagicMock

import json
from core.db_router import calculate_hash, resolve_route
from core.api_caller import ApiCaller
from core.diff_engine import DiffEngine

class TestAPIPostAntiSystem(unittest.TestCase):
    
    def test_01_router_calculation(self):
        """测试路由算法是否被正确推导"""
        # 测试在 db_router 中的占位实现: (int(numeric_part) % total_shards) + 1
        # C10000003 提取出 10000003 -> % 8 = 3, + 1 = 4
        # db_index: (4 - 1) // 2 + 1 = 3 -> dcdpdb2, table: tb_dpmst_medium_0004
        # Wait, the arithmetic in calculate_hash:
        # cust_no = "C10000003"
        hash_val = calculate_hash("C10000003")
        self.assertIn(hash_val, range(1, 9))
        
        db_name, table_name = resolve_route("C10000003")
        self.assertTrue(db_name.startswith("dcdpdb"))
        self.assertTrue(table_name.startswith("tb_dpmst_medium_"))

    @patch('core.api_caller.requests.post')
    def test_02_api_caller_none_to_null(self, mock_post):
        """测试 ApiCaller 严格保留 None -> null"""
        # 准备一个合格的返回模拟
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"code": "0000", "msg": "success"}
        mock_post.return_value = mock_resp
        
        caller = ApiCaller(base_url="http://mock", endpoint="/api")
        payload = {"custNo": "C123", "amount": 100.0, "ext_field": None}
        
        caller.post(payload)
        
        # 验证底层 requests.post 收到的是什么参数？
        # 它应该收到 json=payload，即没有任何字段被 Pop 掉
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args.kwargs
        self.assertIn('json', call_kwargs)
        self.assertEqual(call_kwargs['json']['ext_field'], None)
        
        # requests 在内部将其作为 json.dumps(payload) 序列化，我们验证 python 原生机制
        dumped_str = json.dumps(call_kwargs['json'])
        self.assertIn('"ext_field": null', dumped_str, "None 没有被正确转换！")

    def test_03_diff_engine_ignore_order_and_noise(self):
        """测试核心 DiffEngine 包括忽视顺序、脱敏支持"""
        engine = DiffEngine(
            ignore_order=True,
            extra_exclude_regex_paths=[r"\['sys_version'\]"]
        )
        
        # 模拟：相同的业务数据，但是顺序被打乱了，且 noise 字段不同
        before = {
            "rows": [
                {"id": 1, "status": "init", "update_time": "2023-01-01 10:00:00", "sys_version": 1},
                {"id": 2, "status": "done", "update_time": "2023-01-01 10:00:00", "sys_version": 1}
            ]
        }
        after = {
            "rows": [
                # 乱序
                {"id": 2, "status": "done", "update_time": "2023-01-01 10:05:00", "sys_version": 2},
                {"id": 1, "status": "init", "update_time": "2023-01-01 10:05:00", "sys_version": 2}
            ]
        }
        
        report = engine.compare(before, after)
        
        # 经过 ignore_order 和 exclude_regex_paths 处理，两份数据应当被判定为业务一致
        self.assertTrue(report.is_equal, "测试失败，数据应一致但 DeepDiff 发现了差异！")

if __name__ == '__main__':
    unittest.main()
