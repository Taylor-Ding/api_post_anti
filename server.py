"""
server.py
自动化核对工具 - 本地后端接口服务

提供 HTTP 接口，允许前端 React 页面直接调用后端的查询及 Diff 引擎。
"""
import os
import sys
from flask import Flask, request, jsonify, send_from_directory
from core.pipeline import TestPipeline
from main import extract_routing_key
from config.settings import settings

def get_base_dir():
    # PyInstaller creates a temp folder and stores path in _MEIPASS
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

# 静态资源所在目录 (需指向前端 vite build 生成的 dist 文件夹)
DIST_DIR = os.path.join(get_base_dir(), 'frontend', 'dist')
ASSETS_DIR = os.path.join(DIST_DIR, 'assets')

app = Flask(__name__, static_folder=ASSETS_DIR, static_url_path='/assets')

# 轻量级本地跨域 (CORS) 支持
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Accept'
    response.headers['Access-Control-Allow-Methods'] = 'POST,OPTIONS'
    return response

@app.route('/')
def serve_index():
    # 优先返回内嵌的前端页面
    index_path = os.path.join(DIST_DIR, 'index.html')
    if os.path.exists(index_path):
        return send_from_directory(DIST_DIR, 'index.html')
    return "自动化测试引擎后端正在运行。前端静态页面不存在 (请先执行 npm run build)", 200

@app.route('/<path:path>')
def serve_static_fallback(path):
    # 此路由用于兜底其他静态文件，例如 vite 生成的某些公共文件
    if os.path.exists(os.path.join(DIST_DIR, path)):
        return send_from_directory(DIST_DIR, path)
    return serve_index()

@app.route("/api/verify_pipeline", methods=["POST", "OPTIONS"])
def verify_pipeline():
    if request.method == "OPTIONS":
        return jsonify({}), 200

    try:
        req_data = request.json
        if not req_data:
            return jsonify({"error": "请求体不能为空或不是合法 JSON"}), 400

        target_url = req_data.get("url")
        payload = req_data.get("payload", {})
        
        # 1. 尝试从 payload 中解析路由键 (基于之前实现的 extract_routing_key 验证规则)
        routing_key = extract_routing_key(payload)
        
        # 若正常抛出 None（例如 key 为 "" 或者是 null），为了演示能够查表，我们可能目前只能拦截并提示前端
        if not routing_key:
            return jsonify({"error": "前端传入的报文虽然带有 mainMapElemntInfo 字段，但值为空，无法进行后续路由测试！"}), 400

        # 由于之前为了返回 key_type，我们在 frontend 识别了 custNo / mediumNo，
        # 我们可以在服务端反向检测或者让前端直接传进来，这里根据 04/05 重新判定返回用于日志展现
        txHeader = payload.get("txHeader", {})
        mainInfo = txHeader.get("mainMapElemntInfo", "")
        key_type = "custNo" if mainInfo.startswith("04") else "mediumNo"

        resolved_cust_no = routing_key if key_type == "custNo" else None

        lookup_log = None
        if key_type == "mediumNo":
            try:
                import requests
                import json
                route_url = settings.route_query_url
                # The user specified it's a @GetMapping conceptually but asked for POST. We'll post form-data.
                # Oh wait, it threw method not supported. Switching to GET.
                resp = requests.get(route_url, params={"mediumNo": routing_key}, timeout=5)
                
                if resp.ok:
                    resp_json = resp.json()
                    # It might return {"code":200, "data": "{\"custNo\":\"...\"}"} structure
                    # Or depending on R.ok() it might be different, let's look for "data" or "custNo" directly
                    raw_data = resp_json.get("data", resp_json)
                    if isinstance(raw_data, str):
                        try:
                            parsed_data = json.loads(raw_data)
                            resolved_cust_no = parsed_data.get("custNo")
                        except:
                            pass
                    elif isinstance(raw_data, dict):
                        resolved_cust_no = raw_data.get("custNo")
                        
                    if resolved_cust_no:
                        lookup_log = f"已通过后台反查接口成功换取客户号(custNo): {resolved_cust_no}"
                    else:
                        lookup_log = f"警告：后台反查接口未找到 custNo，返回：{resp_json}"
            except Exception as e:
                import traceback
                traceback.print_exc()
                lookup_log = f"后台反查请求失败或超时错误：{str(e)}"

        if not resolved_cust_no:
            return jsonify({"error": f"无法进行路由计算: 根据 {key_type}={routing_key} 无法获取到有效的 custNo 分片依据。 {lookup_log or ''}"}), 400

        # 由于之前为了返回 key_type，我们在 frontend 识别了 custNo / mediumNo，
        # 我们可以在服务端反向检测或者让前端直接传进来，这里根据 04/05 重新判定返回用于日志展现

        # 2. 调用核心测试引擎
        pipeline = TestPipeline()
        report, api_response = pipeline.run_verify(
            cust_no=resolved_cust_no,
            medium_no=routing_key if key_type == "mediumNo" else None,
            payload=payload,
            target_url=target_url
        )

        # 3. 构造给前端的响应大 JSON
        return jsonify({
            "success": True,
            "routing_key": routing_key,
            "key_type": key_type,
            "resolved_cust_no": resolved_cust_no,
            "lookup_log": lookup_log,
            "report": {
                "is_equal": report.is_equal,
                "summary": report.summary,
                "before_snapshot": {
                    "db_name": report.before_snapshot.get("db_name"),
                    "table_name": report.before_snapshot.get("table_name"),
                    "row_count": len(report.before_snapshot.get("rows", [])),
                    "rows": report.before_snapshot.get("rows", [])
                },
                "after_snapshot": {
                    "db_name": report.after_snapshot.get("db_name"),
                    "table_name": report.after_snapshot.get("table_name"),
                    "row_count": len(report.after_snapshot.get("rows", [])),
                    "rows": report.after_snapshot.get("rows", [])
                },
                "diff_detail": report.diff_detail
            },
            "api_response": api_response
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"后端引擎执行抛错: {str(e)}"}), 500

if __name__ == "__main__":
    import threading
    import webbrowser
    import time

    HOST = "127.0.0.1"
    PORT = 5000
    url = f"http://{HOST}:{PORT}"

    print(f"====== Flask Backend Engine Started at {url} ======")
    print("  ✅ 服务启动成功，浏览器将自动打开...")
    print("  ℹ️  若浏览器未自动打开，请手动访问:", url)
    print("  ⚠️  关闭此窗口将停止服务，请勿关闭！")

    # 打包为单体可执行文件时，自动唤起默认浏览器
    def _open_browser():
        time.sleep(1.5)
        webbrowser.open(url)

    browser_thread = threading.Thread(target=_open_browser, daemon=True)
    browser_thread.start()

    # debug=False + use_reloader=False：PyInstaller 冻结环境中必须关闭 reloader
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False, threaded=True)
