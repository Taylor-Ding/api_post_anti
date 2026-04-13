import sys
import os

# 把当前路径加入 sys.path 以便正常引入包
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.db_router import get_connection

db_tables = {
    'dcdpdb1': ['tb_dpmst_medium_0001', 'tb_dpmst_medium_0002'],
    'dcdpdb2': ['tb_dpmst_medium_0003', 'tb_dpmst_medium_0004'],
    'dcdpdb3': ['tb_dpmst_medium_0005', 'tb_dpmst_medium_0006'],
    'dcdpdb4': ['tb_dpmst_medium_0007', 'tb_dpmst_medium_0008'],
}

def test_connections():
    success_count = 0
    fail_count = 0
    
    for db_name, tables in db_tables.items():
        print(f"\n--- Testing connection to database: {db_name} ---")
        try:
            with get_connection(db_name) as conn:
                print(f"[{db_name}] Database connection successful!")
                with conn.cursor() as cursor:
                    for table in tables:
                        try:
                            # 尝试查一个简单的语句
                            cursor.execute(f"SELECT 1 FROM {table} LIMIT 1")
                            print(f"  -> [{db_name}] Table `{table}` query successful!")
                            success_count += 1
                        except Exception as e:
                            print(f"  -> [{db_name}] Table `{table}` query failed: {e}")
                            fail_count += 1
        except Exception as e:
            print(f"[{db_name}] Database connection failed: {e}")
            fail_count += len(tables)
            
    print(f"\n--- Summary ---")
    print(f"Successfully checked {success_count} tables.")
    print(f"Failed to check {fail_count} tables.")

if __name__ == '__main__':
    test_connections()
