#!/usr/bin/env bash
# ==========================================================
# 分布式核对工具 - 一键内网离线打包脚本 (适用当前系统架构)
# ==========================================================

echo "1. 清理历史遗留构建目录"
rm -rf build dist API_Test_Tool_MacOS.spec

echo "2. 安装/验证 PyInstaller 打包依赖"
./venv/bin/pip install pyinstaller

echo "3. 编译 React 生产级纯净静态文件"
cd frontend
export PATH=/opt/homebrew/bin:/usr/local/bin:$PATH 
pnpm install
pnpm run build
cd ..

echo "4. 执行黑盒二进制封装"
# --onefile: 压包成一个独立的二进制执行文件
# --add-data: 嵌入静态前端文件及默认配置文件
./venv/bin/pyinstaller --name "API_Test_Tool_Offline" \
  --add-data "frontend/dist:frontend/dist" \
  --add-data "conf:conf" \
  --onefile \
  --clean \
  server.py

echo "5. 封装完成！"
echo "✅ 请提取生成的二进制单体部署文件: dist/API_Test_Tool_Offline"
