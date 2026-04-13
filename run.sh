#!/usr/bin/env bash
# run.sh
# 自动化测试查-发-查-比 Linux 一键启动执行脚本

set -e  # 出错时立刻终止

# 切换到脚本所在目录以保证绝对路径相对化正常
cd "$(dirname "$0")"

PROJECT_DIR=$(pwd)
VENV_DIR="${PROJECT_DIR}/venv"
MAIN_SCRIPT="main.py"
LOGS_DIR="${PROJECT_DIR}/logs"

echo "=========================================================="
echo "    启动 查-发-查-比 分布式一致性核对平台"
echo "=========================================================="

echo "=> [1/4] 检查系统环境与 Python3..."
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未检测到 python3，请先在宿主机安装 Python 3.8+ 环境。"
    exit 1
fi

echo "=> [2/4] 初始化虚拟环境..."
if [ ! -d "$VENV_DIR" ]; then
    echo "   -> 未发现 venv 目录，正在创建独立的虚拟环境..."
    python3 -m venv "$VENV_DIR"
fi

# 激活虚拟环境
source "$VENV_DIR/bin/activate"

echo "=> [3/4] 检查并安装依赖库 (requirements.txt)..."
# 升级 pip 以防止某些旧版本安装依赖包报错
python3 -m pip install --upgrade pip -q
pip install -r "${PROJECT_DIR}/requirements.txt" -q
echo "   -> 依赖库准备就绪"

echo "=> [4/4] 准备日志目录及执行任务..."
mkdir -p "$LOGS_DIR"

if [ ! -f "conf/config.json" ]; then
    echo "[警告] conf/config.json 不存在。虽然代码层面已提供了一份占位的配置，但极有可能因为 DB 信息不正确而启动报错。"
    echo "       请先检查 conf 目录配置再重试！"
fi

echo "=========================================================="
echo "   任务即将启动 | 日志同步保留至: ${LOGS_DIR}/sync_test.log"
echo "=========================================================="

# 暴露 Python PATH 指向项目根目录，防止跨包 import 出错
export PYTHONPATH="${PROJECT_DIR}"

python3 "$MAIN_SCRIPT"

# 退出脚本
exit 0
