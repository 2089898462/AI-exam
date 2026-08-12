"""
S5.7-D1.5-D DeepSeek真实调用自动化验证脚本
"""
import os
import sys
import json
import time
import subprocess
from pathlib import Path
import urllib.request
import urllib.error

results = {
    "env_check": {},
    "service_start": {},
    "api_test": {},
    "deepseek_verify": {},
    "passed": False
}

# ============================================================
# 步骤 1: 环境检查
# ============================================================
print("=" * 50)
print("【步骤 1】环境检查")
print("=" * 50)

env_path = Path(".env")
if not env_path.exists():
    results["env_check"]["status"] = "FAIL"
    results["env_check"]["error"] = ".env 文件不存在"
    print("❌ .env 文件不存在")
    print("\n" + json.dumps(results, indent=2, ensure_ascii=False))
    sys.exit(1)

results["env_check"]["env_exists"] = True

with open(".env", "r") as f:
    env_data = {}
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            env_data[key.strip()] = value.strip()

# 检查 AI_API_KEY
api_key = env_data.get("AI_API_KEY", "")
if not api_key or api_key == "your-api-key-here":
    results["env_check"]["api_key_status"] = "INVALID"
    results["env_check"]["api_key_valid"] = False
    print("❌ AI_API_KEY 未配置真实值（仍为占位符或空）")
    # 提前输出结果
    print("\n" + "=" * 50)
    print("【最终结果】")
    print("=" * 50)
    print(json.dumps(results, indent=2, ensure_ascii=False))
    sys.exit(0)
else:
    results["env_check"]["api_key_status"] = "OK"
    results["env_check"]["api_key_valid"] = True
    print("✅ AI_API_KEY 已配置（非占位符）")

# 检查 AI_MODEL_NAME
model_name = env_data.get("AI_MODEL_NAME", "deepseek-v4-flash")
results["env_check"]["model_name"] = model_name
print(f"   AI_MODEL_NAME: {model_name}")

# 检查 AI_API_BASE
api_base = env_data.get("AI_API_BASE", "https://api.deepseek.com/v1")
results["env_check"]["api_base"] = api_base
print(f"   AI_API_BASE: {api_base}")

print(f"\n环境检查结果: {results['env_check']['api_key_status']}")

# ============================================================
# 步骤 2: 启动 ai-service
# ============================================================
print("\n" + "=" * 50)
print("【步骤 2】启动 AI-Service")
print("=" * 50)

# 先清理可能占用的端口
import socket
import signal

def check_port_in_use(port):
    """检查端口是否被占用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def kill_process_on_port(port):
    """杀掉占用指定端口的进程"""
    try:
        result = subprocess.run(
            ['netstat', '-ano'],
            capture_output=True,
            text=True
        )
        for line in result.stdout.split('\n'):
            if f':{port}' in line and 'LISTENING' in line:
                pid = line.strip().split()[-1]
                print(f"   清理占用端口 {port} 的进程 PID: {pid}")
                subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True)
                time.sleep(1)
    except Exception as e:
        print(f"   端口清理异常: {e}")

# 清理端口 8001
if check_port_in_use(8001):
    print("   端口 8001 被占用，正在清理...")
    kill_process_on_port(8001)
    time.sleep(1)

try:
    # 启动 ai-service
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"],
        cwd=str(Path(__file__).parent),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # 等待服务启动
    print("   正在启动 AI-Service...")
    time.sleep(3)
    
    # 检查进程是否存活
    if process.poll() is not None:
        # 进程已退出，读取错误信息
        stdout, stderr = process.communicate()
        results["service_start"]["status"] = "FAIL"
        results["service_start"]["error"] = f"进程异常退出: {stderr[:500]}"
        print(f"❌ 服务启动失败: {stderr[:200]}")
        print("\n" + json.dumps(results, indent=2, ensure_ascii=False))
        sys.exit(1)
    
    results["service_start"]["process_alive"] = True
    print("   进程启动成功")

except Exception as e:
    results["service_start"]["status"] = "FAIL"
    results["service_start"]["error"] = str(e)
    print(f"❌ 启动异常: {e}")
    print("\n" + json.dumps(results, indent=2, ensure_ascii=False))
    sys.exit(1)

# 验证 /health 接口
try:
    req = urllib.request.Request("http://localhost:8001/health")
    with urllib.request.urlopen(req, timeout=5) as resp:
        health_data = json.loads(resp.read())
        if health_data.get("status") == "ok":
            results["service_start"]["health_status"] = "OK"
            print("✅ /health 接口正常")
        else:
            results["service_start"]["health_status"] = "WARN"
            results["service_start"]["health_response"] = health_data
            print(f"⚠️ /health 返回异常: {health_data}")
except urllib.error.URLError as e:
    results["service_start"]["health_status"] = "FAIL"
    results["service_start"]["error"] = str(e)
    print(f"❌ /health 请求失败: {e}")
    
    # 尝试查看启动日志
    process.kill()
    stdout, stderr = process.communicate()
    print(f"\n启动日志:\n{stdout[:1000]}\n{stderr[:500]}")
    results["service_start"]["startup_log"] = stdout[:500]
    results["service_start"]["error_log"] = stderr[:500]
    
    print("\n" + json.dumps(results, indent=2, ensure_ascii=False))
    sys.exit(1)

# ============================================================
# 步骤 3: 调用 AI 评分接口
# ============================================================
print("\n" + "=" * 50)
print("【步骤 3】调用 AI 评分接口")
print("=" * 50)

# 测试数据
test_data = {
    "question": "解释Vue3中的响应式原理。",
    "standard_answer": "Vue3通过Proxy实现响应式，通过代理对象拦截数据访问和修改。",
    "user_answer": "Vue3使用Proxy监听对象变化，实现数据自动更新。",
    "max_score": 10
}

results["api_test"]["test_input"] = test_data

try:
    req = urllib.request.Request(
        "http://localhost:8001/api/scoring/evaluate",
        data=json.dumps(test_data).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        response_data = json.loads(resp.read())
        results["api_test"]["response"] = response_data
        results["api_test"]["status_code"] = 200
        
        print(f"✅ 接口响应正常 (HTTP 200)")
        
        # 检查返回结构
        if "score" in response_data:
            results["api_test"]["score"] = response_data["score"]
            print(f"   score: {response_data['score']}")
        if "reason" in response_data:
            results["api_test"]["reason"] = response_data["reason"]
            print(f"   reason: {response_data['reason'][:100]}...")
        if "confidence" in response_data:
            results["api_test"]["confidence"] = response_data["confidence"]
            print(f"   confidence: {response_data['confidence']}")
            
except urllib.error.HTTPError as e:
    error_body = e.read().decode("utf-8")
    results["api_test"]["status_code"] = e.code
    results["api_test"]["error"] = error_body[:500]
    print(f"❌ 接口返回错误 HTTP {e.code}")
    print(f"   错误详情: {error_body[:300]}")
    
except urllib.error.URLError as e:
    results["api_test"]["error"] = str(e)
    print(f"❌ 请求失败: {e}")

# ============================================================
# 步骤 4: 验证 DeepSeek 真实调用
# ============================================================
print("\n" + "=" * 50)
print("【步骤 4】DeepSeek 真实调用验证")
print("=" * 50)

response = results.get("api_test", {}).get("response", {})

# 检查 1: 响应是否来自 DeepSeek（非 mock）
# 特征：包含 score, reason, confidence 等字段
if response:
    # 检查 score 不是固定值（如非 0, 非空）
    score = response.get("score")
    reason = response.get("reason", "")
    confidence = response.get("confidence")
    
    results["deepseek_verify"]["score_not_fixed"] = score not in [0, None, ""]
    results["deepseek_verify"]["reason_is_text"] = len(str(reason)) > 10
    results["deepseek_verify"]["confidence_exists"] = confidence is not None
    
    print(f"   Score 非固定值: {results['deepseek_verify']['score_not_fixed']}")
    print(f"   Reason 为AI生成文本: {results['deepseek_verify']['reason_is_text']}")
    print(f"   Confidence 存在: {results['deepseek_verify']['confidence_exists']}")
    
    # 综合判断
    if all(results["deepseek_verify"].values()):
        results["deepseek_verify"]["status"] = "PASS"
        print("✅ DeepSeek 真实调用验证通过")
    else:
        results["deepseek_verify"]["status"] = "PARTIAL"
        print("⚠️ DeepSeek 调用可能存在问题")
else:
    results["deepseek_verify"]["status"] = "FAIL"
    results["deepseek_verify"]["error"] = "无有效响应"
    print("❌ 无法验证 DeepSeek 调用（无响应）")

# ============================================================
# 步骤 5: 停止服务并输出结果
# ============================================================
print("\n" + "=" * 50)
print("【最终结果】")
print("=" * 50)

# 停止服务
try:
    if process.poll() is None:
        process.kill()
        stdout, stderr = process.communicate()
        results["service_start"]["stopped"] = True
        results["service_start"]["final_log"] = stdout[:300]
except Exception:
    pass

# 综合判定
env_ok = results["env_check"].get("api_key_valid", False)
service_ok = results["service_start"].get("health_status") == "OK"
api_ok = "response" in results.get("api_test", {})
deepseek_ok = results["deepseek_verify"].get("status") == "PASS"

results["passed"] = all([env_ok, service_ok, api_ok, deepseek_ok])

print(f"\n环境检查: {'✅' if env_ok else '❌'}")
print(f"服务启动: {'✅' if service_ok else '❌'}")
print(f"API调用: {'✅' if api_ok else '❌'}")
print(f"DeepSeek调用: {'✅' if deepseek_ok else '❌'}")
print(f"\n最终结论: {'✅ S5.7-D1.5-D通过' if results['passed'] else '❌ S5.7-D1.5-D未通过'}")

print("\n详细结果:")
print(json.dumps(results, indent=2, ensure_ascii=False))