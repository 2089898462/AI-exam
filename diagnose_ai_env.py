"""
AI_API_KEY 加载问题诊断脚本
检查 ai-service 启动时环境变量加载链路
"""
import os
import sys
from pathlib import Path

print("=" * 60)
print("AI_API_KEY 加载链路诊断")
print("=" * 60)

# ============================================================
# 1. 检查启动目录
# ============================================================
print("\n[1] 启动目录检查")
cwd = os.getcwd()
print(f"  当前工作目录 (CWD): {cwd}")
print(f"  ai-service 期望目录: {os.path.join(cwd, 'ai-service')}")

# ============================================================
# 2. 检查 .env 文件是否存在
# ============================================================
print("\n[2] .env 文件检查")

# 可能的 .env 路径
possible_paths = [
    os.path.join(cwd, ".env"),              # 项目根目录
    os.path.join(cwd, "ai-service", ".env"), # ai-service 目录
    os.path.join(cwd, "backend", ".env"),    # backend 目录
]

for p in possible_paths:
    exists = os.path.exists(p)
    print(f"  {p}")
    print(f"    存在: {'✅' if exists else '❌'}")
    
    if exists and ai_service_dir := "ai-service" in p:
        # 检查文件内容（只看变量名，不输出值）
        with open(p, 'r') as f:
            content = f.read()
        has_key = "AI_API_KEY" in content and "your-api-key-here" not in content
        print(f"    包含 AI_API_KEY 真实值: {'✅' if has_key else '❌ (占位符或不存在)'}")

# 检查 .env.example
env_example = os.path.join(cwd, "ai-service", ".env.example")
if os.path.exists(env_example):
    with open(env_example, 'r') as f:
        content = f.read()
    lines = [l.strip() for l in content.split('\n') if l.strip() and not l.startswith('#')]
    print(f"\n  .env.example 中的变量定义:")
    for line in lines:
        if '=' in line:
            var_name = line.split('=')[0]
            print(f"    {var_name}")

# ============================================================
# 3. 模拟 AI-Service 配置读取
# ============================================================
print("\n[3] AI-Service 配置读取模拟")

# 注入 ai-service 路径
sys.path.insert(0, os.path.join(cwd, "ai-service"))

from app.core.config import config as ai_config

print(f"  AIConfig 类类型: {type(ai_config).__name__}")
print(f"  是否继承 BaseSettings: {'否 (普通类)' if 'BaseSettings' not in str(type(ai_config).__mro__) else '是'}")
print(f"  是否有 env_file 配置: {'否 (无)' if not hasattr(ai_config, 'model_config') or not hasattr(ai_config.model_config, 'env_file') else '是'}")
print()
print(f"  AIConfig.API_KEY = '{ai_config.API_KEY}'")
print(f"  AIConfig.MODEL_NAME = '{ai_config.MODEL_NAME}'")
print(f"  AIConfig.API_BASE = '{ai_config.API_BASE}'")

# ============================================================
# 4. 检查 os.environ 实际内容
# ============================================================
print("\n[4] os.environ 环境变量检查")

# AI_ 前缀变量
ai_vars = {k: '[已设置]' if v else '[空]' for k, v in os.environ.items() if k.startswith("AI_")}
print(f"  AI_ 前缀变量数: {len(ai_vars)}")
if ai_vars:
    for k, v in sorted(ai_vars.items()):
        print(f"    {k}: {v}")
else:
    print("    (无 AI_ 前缀变量)")

# 关键变量
key_vars = ["AI_API_KEY", "AI_MODEL_NAME", "AI_API_BASE"]
for var in key_vars:
    val = os.environ.get(var)
    print(f"  os.environ.get('{var}'): {'[已设置]' if val else '[空]'}")

# ============================================================
# 5. 与后端对比
# ============================================================
print("\n[5] 后端配置方式对比")

# 注入 backend 路径
sys.path.insert(0, os.path.join(cwd, "backend"))

# 检查是否有 pydantic_settings
try:
    from pydantic_settings import BaseSettings
    print(f"  pydantic_settings 可用: ✅")
    
    # 检查 backend config
    backend_config_path = os.path.join(cwd, "backend", "app", "core", "config.py")
    with open(backend_config_path, 'r') as f:
        content = f.read()
    
    has_env_file = 'env_file' in content
    has_base_settings = 'BaseSettings' in content
    print(f"  backend/config.py 使用 BaseSettings: {'✅' if has_base_settings else '❌'}")
    print(f"  backend/config.py 有 env_file 配置: {'✅' if has_env_file else '❌'}")
    
except ImportError:
    print(f"  pydantic_settings 可用: ❌ (未安装)")

# ai-service 是否有 dotenv
sys.path.pop(0)  # remove backend path
sys.path.insert(0, os.path.join(cwd, "ai-service"))

has_dotenv = False
try:
    from dotenv import load_dotenv
    has_dotenv = True
except ImportError:
    pass

# 检查代码中是否调用了 load_dotenv
ai_service_main = os.path.join(cwd, "ai-service", "main.py")
with open(ai_service_main, 'r') as f:
    main_content = f.read()

main_has_dotenv = 'load_dotenv' in main_content

print(f"\n  ai-service dotenv 库可用: {'✅' if has_dotenv else '❌'}")
print(f"  ai-service main.py 调用 load_dotenv: {'✅' if main_has_dotenv else '❌'}")

# 检查 config.py 是否调用了 load_dotenv
ai_service_config = os.path.join(cwd, "ai-service", "app", "core", "config.py")
with open(ai_service_config, 'r') as f:
    config_content = f.read()
config_has_dotenv = 'load_dotenv' in config_content

print(f"  ai-service config.py 调用 load_dotenv: {'✅' if config_has_dotenv else '❌'}")

# ============================================================
# 6. 根因分析
# ============================================================
print("\n" + "=" * 60)
print("根因分析")
print("=" * 60)

print("""
问题: AI_API_KEY 始终为空

根因链路:
┌─────────────────────────────────────────────────────────┐
│ 1. ai-service/.env 文件不存在                           │
│    → 无地方存放 AI_API_KEY                             │
│                                                         │
│ 2. AIConfig 使用 os.environ.get()                      │
│    → 只读系统环境变量，不读 .env 文件                    │
│                                                         │
│ 3. ai-service 未实现任何 .env 加载机制                   │
│    → 无 load_dotenv() 调用                              │
│    → 无 pydantic_settings.BaseSettings                  │
│                                                         │
│ 4. 即使创建了 .env 文件也不会被读取                      │
│    → 因为没有代码加载它                                  │
│                                                         │
│ 5. os.environ.get("AI_API_KEY", "") 返回 ""             │
│    → Authorization: Bearer                              │
│    → httpx 拒绝非法 header                              │
└─────────────────────────────────────────────────────────┘

对比后端:
  backend/app/core/config.py
    └── class Settings(BaseSettings)
          └── class Config: env_file = ".env"
                → 自动加载 .env → AI_SERVICE_URL 可正常读取

  ai-service/app/core/config.py
    └── class AIConfig: (普通类)
          └── os.environ.get("AI_API_KEY", "")
                → 不加载 .env → AI_API_KEY 始终为空
""")

# ============================================================
# 7. 最小修复方案
# ============================================================
print("\n" + "=" * 60)
print("最小修复方案")
print("=" * 60)

print("""
方案 A: 添加 load_dotenv() 调用（3行代码）
------------------------------------------

在 ai-service/app/core/config.py 顶部添加:

    from dotenv import load_dotenv
    load_dotenv()  # 加载 ai-service/.env

同时创建 ai-service/.env 文件:

    AI_MODEL_NAME=deepseek-v4-flash
    AI_MODEL_PROVIDER=deepseek
    AI_API_KEY=sk-xxxx-your-key
    AI_API_BASE=https://api.deepseek.com/v1

前提: pip install python-dotenv

---

方案 B: 改用 pydantic_settings（与后端一致）
---------------------------------------------

将 AIConfig 改为继承 BaseSettings:

    from pydantic_settings import BaseSettings

    class AIConfig(BaseSettings):
        MODEL_NAME: str = "deepseek-v4-flash"
        API_KEY: str = ""
        ...

        class Config:
            env_file = ".env"

前提: pip install pydantic-settings

---

推荐: 方案 A（改动最小，风险最低）
理由: 仅需添加 2 行代码 + 创建 .env 文件
""")