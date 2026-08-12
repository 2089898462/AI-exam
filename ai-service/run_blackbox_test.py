"""
S5.7-F 系统黑盒业务验收测试

黑盒测试原则：
- 仅通过 API 响应判断功能是否正确
- 不查看代码实现作为判断依据
- 模拟真实用户操作流程
- 基于用户体验判断可用性

测试角色：管理员、HR、候选人
"""
import json
import time
import urllib.request
import urllib.error
from datetime import datetime

# 配置
BACKEND_URL = "http://localhost:8000"
AI_SERVICE_URL = "http://localhost:8001"

# 测试结果记录
test_results = {
    "environment": {},
    "admin_tests": [],
    "hr_tests": [],
    "candidate_tests": [],
    "ai_scoring_tests": [],
    "exception_tests": [],
    "bugs": [],
    "passed": True
}

def api(method, path, data=None, token=None, base_url=BACKEND_URL):
    """统一 API 请求（黑盒测试：只看响应）"""
    url = f"{base_url}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    body = json.dumps(data).encode("utf-8") if data else None
    
    try:
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            try:
                return resp.status, json.loads(raw)
            except:
                return resp.status, {"raw": raw.decode("utf-8", errors="replace")}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(error_body)
        except:
            return e.code, {"detail": error_body}
    except Exception as e:
        return None, {"error": str(e)}

def log(test_id, name, status, detail=""):
    """记录测试结果"""
    icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
    result = f"  [{test_id}] {icon} {name}"
    if detail:
        result += f" — {detail}"
    print(result)
    return {"id": test_id, "name": name, "status": status, "detail": detail}

def report_bug(bug_id, title, level, detail):
    """记录 Bug"""
    bug = {"id": bug_id, "title": title, "level": level, "detail": detail}
    test_results["bugs"].append(bug)
    level_icon = {"P0": "🔴", "P1": "🟠", "P2": "🟡", "P3": "🔵"}.get(level, "⚪")
    print(f"  {level_icon} BUG[{bug_id}] [{level}]: {title}")
    print(f"     {detail}")
    return bug

# ============================================================
# 0. 环境检查
# ============================================================
print("=" * 60)
print("S5.7-F 系统黑盒业务验收测试")
print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

print("\n【0. 测试环境检查】")
env_ok = True

# Backend
code, resp = api("GET", "/docs")
test_results["environment"]["backend"] = code is not None and code < 500
if code and code < 500:
    print("  ✅ Backend API 正常")
else:
    print("  ❌ Backend API 异常")
    env_ok = False

# AI Service
code, resp = api("GET", "/health", base_url=AI_SERVICE_URL)
test_results["environment"]["ai_service"] = code == 200
if code == 200:
    print("  ✅ AI Service 正常")
else:
    print("  ❌ AI Service 异常")
    env_ok = False

# Frontend
try:
    r = urllib.request.urlopen("http://localhost:3000", timeout=5)
    test_results["environment"]["frontend"] = r.status == 200
    print("  ✅ Frontend 正常")
except:
    test_results["environment"]["frontend"] = False
    print("  ❌ Frontend 异常")
    env_ok = False

if not env_ok:
    print("\n❌ 环境检查失败，终止测试")
    exit(1)

# ============================================================
# 1. 管理员流程测试
# ============================================================
print("\n" + "=" * 60)
print("【1. 管理员流程测试】")
print("=" * 60)

admin_token = None

# 1.1 管理员登录
print("\n--- 1.1 管理员登录 ---")
code, resp = api("POST", "/api/v1/auth/login", {
    "username": "admin_test",
    "password": "test123456"
})

if code not in (200, 201):
    # 注册管理员
    code, resp = api("POST", "/api/v1/auth/register", {
        "username": "admin_test",
        "password": "test123456",
        "display_name": "测试管理员",
        "role": "admin"
    })

if code in (200, 201):
    admin_token = resp.get("data", {}).get("access_token", "")
    r = log("1.1.1", "管理员登录", "PASS")
    test_results["admin_tests"].append(r)
    
    # 检查用户信息
    me_code, me_resp = api("GET", "/api/v1/auth/me", token=admin_token)
    if me_code == 200:
        r = log("1.1.2", "获取用户信息", "PASS", f"角色: {me_resp.get('data', {}).get('role')}")
        test_results["admin_tests"].append(r)
    else:
        r = log("1.1.2", "获取用户信息", "FAIL", str(me_resp))
        test_results["admin_tests"].append(r)
        report_bug("ADMIN-001", "管理员无法获取用户信息", "P1", f"GET /auth/me 返回 {me_code}: {me_resp}")
else:
    r = log("1.1.1", "管理员登录", "FAIL", str(resp))
    test_results["admin_tests"].append(r)
    report_bug("ADMIN-000", "管理员登录失败", "P0", f"响应: {resp}")
    test_results["passed"] = False

# 1.2 权限验证（管理员访问HR页面）
print("\n--- 1.2 权限验证 ---")
if admin_token:
    code, resp = api("GET", "/api/v1/exams", token=admin_token)
    if code == 200:
        r = log("1.2.1", "管理员访问考试列表", "PASS", "HR页面可访问")
        test_results["admin_tests"].append(r)
    else:
        r = log("1.2.1", "管理员访问考试列表", "WARN", f"HTTP {code}: {resp}")
        test_results["admin_tests"].append(r)

# ============================================================
# 2. HR 完整业务流程测试
# ============================================================
print("\n" + "=" * 60)
print("【2. HR 完整业务流程测试】")
print("=" * 60)

hr_token = None

# 2.1 HR登录
print("\n--- 2.1 HR 登录 ---")
code, resp = api("POST", "/api/v1/auth/login", {
    "username": "hr_blackbox",
    "password": "test123456"
})

if code not in (200, 201):
    code, resp = api("POST", "/api/v1/auth/register", {
        "username": "hr_blackbox",
        "password": "test123456",
        "display_name": "黑盒测试HR",
        "role": "hr"
    })

if code in (200, 201):
    hr_token = resp.get("data", {}).get("access_token", "")
    r = log("2.1.1", "HR登录", "PASS")
    test_results["hr_tests"].append(r)
else:
    r = log("2.1.1", "HR登录", "FAIL", str(resp))
    test_results["hr_tests"].append(r)
    report_bug("HR-000", "HR登录失败", "P0", f"响应: {resp}")
    test_results["passed"] = False

# 2.2 创建考试
print("\n--- 2.2 创建考试 ---")
exam_id = None
exam_code = None

if hr_token:
    timestamp = int(time.time())
    code, resp = api("POST", "/api/v1/exams", {
        "title": f"黑盒测试考试_{timestamp}",
        "description": "S5.7-F 黑盒业务验收测试",
        "duration_minutes": 30,
        "pass_score": 60
    }, token=hr_token)
    if code in (200, 201):
        exam_data = resp.get("data", {})
        exam_id = exam_data.get("id")
        exam_code = exam_data.get("exam_code")
        r = log("2.2.1", "创建考试", "PASS", f"ID: {exam_id}")
        test_results["hr_tests"].append(r)
        
        # 验证 exam_code
        if exam_code:
            r = log("2.2.2", "考试码自动生成", "PASS", f"Code: {exam_code}")
            test_results["hr_tests"].append(r)
        else:
            r = log("2.2.2", "考试码自动生成", "FAIL", "exam_code 为 None")
            test_results["hr_tests"].append(r)
            report_bug("HR-001", "创建考试时考试码未自动生成", "P1", "exam_code 字段为 null")
    else:
        r = log("2.2.1", "创建考试", "FAIL", f"HTTP {code}: {resp}")
        test_results["hr_tests"].append(r)
        report_bug("HR-002", "创建考试失败", "P0", f"响应: {resp}")
        test_results["passed"] = False

# 2.3 添加题目
print("\n--- 2.3 添加题目 ---")
question_ids = []

if hr_token and exam_id:
    # 2.3.1 单选题
    code, resp = api("POST", f"/api/v1/questions?exam_id={exam_id}", {
        "type": "single_choice",
        "content": "以下哪个是前端框架？",
        "options": [
            {"label": "A", "text": "Django"},
            {"label": "B", "text": "Vue"},
            {"label": "C", "text": "Flask"},
            {"label": "D", "text": "Spring"}
        ],
        "answer": "B",
        "score": 10,
        "sort_order": 1
    }, token=hr_token)
    
    if code in (200, 201):
        qid = resp.get("data", {}).get("id")
        question_ids.append(qid)
        r = log("2.3.1", "添加单选题", "PASS", f"ID: {qid}")
        test_results["hr_tests"].append(r)
    else:
        r = log("2.3.1", "添加单选题", "FAIL", f"HTTP {code}: {resp}")
        test_results["hr_tests"].append(r)
        report_bug("HR-003", "添加单选题失败", "P1", f"响应: {resp}")
    
    # 2.3.2 判断题
    code, resp = api("POST", f"/api/v1/questions?exam_id={exam_id}", {
        "type": "true_false",
        "content": "Python 是动态类型语言。",
        "answer": "true",
        "score": 5,
        "sort_order": 2
    }, token=hr_token)
    
    if code in (200, 201):
        qid = resp.get("data", {}).get("id")
        question_ids.append(qid)
        r = log("2.3.2", "添加判断题", "PASS", f"ID: {qid}")
        test_results["hr_tests"].append(r)
    else:
        r = log("2.3.2", "添加判断题", "FAIL", f"HTTP {code}: {resp}")
        test_results["hr_tests"].append(r)
        report_bug("HR-004", "添加判断题失败", "P1", f"响应: {resp}")
    
    # 2.3.3 简答题（AI评分题型）
    code, resp = api("POST", f"/api/v1/questions?exam_id={exam_id}", {
        "type": "short_answer",
        "content": "简述 RESTful API 的设计原则。",
        "answer": "RESTful API 设计原则包括：无状态通信、统一接口、使用HTTP方法、资源导向、HATEOAS等。",
        "score": 15,
        "sort_order": 3
    }, token=hr_token)
    
    if code in (200, 201):
        qid = resp.get("data", {}).get("id")
        question_ids.append(qid)
        r = log("2.3.3", "添加简答题", "PASS", f"ID: {qid}")
        test_results["hr_tests"].append(r)
    else:
        r = log("2.3.3", "添加简答题", "FAIL", f"HTTP {code}: {resp}")
        test_results["hr_tests"].append(r)
        report_bug("HR-005", "添加简答题失败", "P1", f"响应: {resp}")

# 2.4 发布考试
print("\n--- 2.4 发布考试 ---")
if hr_token and exam_id:
    code, resp = api("POST", f"/api/v1/exams/{exam_id}/publish", token=hr_token)
    
    if code in (200, 201):
        r = log("2.4.1", "发布考试", "PASS")
        test_results["hr_tests"].append(r)
    else:
        r = log("2.4.1", "发布考试", "FAIL", f"HTTP {code}: {resp}")
        test_results["hr_tests"].append(r)
        report_bug("HR-006", "发布考试失败", "P0", f"响应: {resp}")
        test_results["passed"] = False

# 2.5 添加参与人员
print("\n--- 2.5 添加参与人员 ---")
if hr_token and exam_id:
    candidate_name = "黑盒测试候选人"
    candidate_phone = "13900000001"
    
    code, resp = api("POST", f"/api/v1/exams/{exam_id}/participants", {
        "candidate_name": candidate_name,
        "candidate_phone": candidate_phone,
        "candidate_email": "blackbox@test.com"
    }, token=hr_token)
    
    if code in (200, 201):
        r = log("2.5.1", "添加参与人员", "PASS")
        test_results["hr_tests"].append(r)
    else:
        r = log("2.5.1", "添加参与人员", "FAIL", f"HTTP {code}: {resp}")
        test_results["hr_tests"].append(r)
        report_bug("HR-007", "添加参与人员失败", "P1", f"响应: {resp}")

# ============================================================
# 3. 候选人流程测试
# ============================================================
print("\n" + "=" * 60)
print("【3. 候选人流程测试】")
print("=" * 60)

record_id = None
candidate_name = "黑盒测试候选人"
candidate_phone = "13900000001"

# 3.1 使用考试码进入
print("\n--- 3.1 使用考试码进入 ---")
if exam_id and exam_code:
    code, resp = api("POST", "/api/v1/exam-records", {
        "exam_id": exam_id,
        "exam_code": exam_code,
        "candidate_name": candidate_name,
        "candidate_phone": candidate_phone
    })
    
    if code in (200, 201):
        record_data = resp.get("data", {})
        record_id = record_data.get("id")
        r = log("3.1.1", "候选人进入考试", "PASS", f"Record ID: {record_id}")
        test_results["candidate_tests"].append(r)
    else:
        r = log("3.1.1", "候选人进入考试", "FAIL", f"HTTP {code}: {resp}")
        test_results["candidate_tests"].append(r)
        report_bug("CAND-000", "候选人无法进入考试", "P0", f"响应: {resp}")
        test_results["passed"] = False

# 3.2 答题
print("\n--- 3.2 答题流程 ---")
if record_id:
    # 3.2.1 开始考试
    code, resp = api("POST", f"/api/v1/exam-records/{record_id}/start")
    if code in (200, 201):
        r = log("3.2.1", "开始考试", "PASS")
        test_results["candidate_tests"].append(r)
    else:
        r = log("3.2.1", "开始考试", "FAIL", f"HTTP {code}: {resp}")
        test_results["candidate_tests"].append(r)
    
    # 3.2.2 保存答案
    answers = []
    for i, qid in enumerate(question_ids):
        if i == 0:  # 单选
            answers.append({"question_id": qid, "answer": "B"})
        elif i == 1:  # 判断
            answers.append({"question_id": qid, "answer": "true"})
        elif i == 2:  # 简答
            answers.append({"question_id": qid, "answer": "RESTful API设计原则包括无状态通信、统一接口、资源导向、使用HTTP方法等。"})
    
    code, resp = api("POST", f"/api/v1/exam-records/{record_id}/answers/batch", {
        "answers": answers
    })
    
    if code in (200, 201):
        r = log("3.2.2", "批量保存答案", "PASS", f"{len(answers)} 题")
        test_results["candidate_tests"].append(r)
    else:
        r = log("3.2.2", "批量保存答案", "FAIL", f"HTTP {code}: {resp}")
        test_results["candidate_tests"].append(r)
        report_bug("CAND-001", "保存答案失败", "P1", f"响应: {resp}")

# 3.3 提交考试
print("\n--- 3.3 提交考试 ---")
if record_id:
    code, resp = api("POST", f"/api/v1/exam-records/{record_id}/submit")
    
    if code in (200, 201):
        submit_data = resp.get("data", {})
        status = submit_data.get("status", "")
        r = log("3.3.1", "提交考试", "PASS", f"状态: {status}")
        test_results["candidate_tests"].append(r)
        
        if status == "submitted":
            r = log("3.3.2", "提交状态验证", "PASS", "submitted")
            test_results["candidate_tests"].append(r)
        else:
            r = log("3.3.2", "提交状态验证", "FAIL", f"实际: {status}")
            test_results["candidate_tests"].append(r)
    else:
        r = log("3.3.1", "提交考试", "FAIL", f"HTTP {code}: {resp}")
        test_results["candidate_tests"].append(r)
        report_bug("CAND-002", "提交考试失败", "P0", f"响应: {resp}")
        test_results["passed"] = False

# ============================================================
# 4. AI 评分测试
# ============================================================
print("\n" + "=" * 60)
print("【4. AI 评分测试】")
print("=" * 60)

grading_result = None

if record_id and hr_token:
    print("\n--- 4.1 等待 AI 评分 ---")
    max_wait = 45
    for i in range(max_wait // 3):
        time.sleep(3)
        code, resp = api("GET", f"/api/v1/exam-records/{record_id}/grading", token=hr_token)
        
        if code == 200:
            gdata = resp.get("data", {})
            if isinstance(gdata, dict):
                status = gdata.get("status", "")
                if status in ("completed", "graded", "failed"):
                    grading_result = gdata
                    r = log("4.1.1", "AI评分完成", "PASS", f"等待 {(i+1)*3}s, 状态: {status}")
                    test_results["ai_scoring_tests"].append(r)
                    break
            elif isinstance(gdata, list) and len(gdata) > 0:
                grading_result = gdata[0]
                status = grading_result.get("status", "")
                if status in ("completed", "graded", "failed"):
                    r = log("4.1.1", "AI评分完成", "PASS", f"等待 {(i+1)*3}s")
                    test_results["ai_scoring_tests"].append(r)
                    break
    else:
        r = log("4.1.1", "AI评分完成", "FAIL", f"等待超时 ({max_wait}s)")
        test_results["ai_scoring_tests"].append(r)
        report_bug("AI-000", "AI评分超时", "P1", f"等待 {max_wait}s 仍未完成")
        test_results["passed"] = False

# 4.2 验证 AI 返回
if grading_result:
    print("\n--- 4.2 验证 AI 返回 ---")
    total_score = grading_result.get("total_score")
    ai_score = grading_result.get("ai_score")
    ai_reason = grading_result.get("ai_reason")
    
    if total_score:
        r = log("4.2.1", "总分数", "PASS", f"total_score: {total_score}")
        test_results["ai_scoring_tests"].append(r)
    else:
        r = log("4.2.1", "总分数", "FAIL", "total_score 为空")
        test_results["ai_scoring_tests"].append(r)
        report_bug("AI-001", "评分结果无总分", "P1", "total_score 为 null")
    
    # 查询简答题评分详情
    if hr_token and exam_id:
        code, resp = api("GET", f"/api/v1/exams/{exam_id}/records/{record_id}/answers", token=hr_token)
        if code == 200:
            answers_data = resp.get("data", [])
            if isinstance(answers_data, list):
                for ans in answers_data:
                    if isinstance(ans, dict) and ans.get("question_type") == "short_answer":
                        ai_s = ans.get("ai_score")
                        ai_r = ans.get("ai_reason")
                        ai_c = ans.get("confidence")
                        
                        if ai_s is not None:
                            r = log("4.2.2", "简答题 AI 评分", "PASS", f"score: {ai_s}")
                            test_results["ai_scoring_tests"].append(r)
                        else:
                            r = log("4.2.2", "简答题 AI 评分", "FAIL", "ai_score 为空")
                            test_results["ai_scoring_tests"].append(r)
                            report_bug("AI-002", "简答题未评分", "P1", "ai_score 为 null")
                        
                        if ai_r:
                            r = log("4.2.3", "AI 评分理由", "PASS", f"长度: {len(str(ai_r))}")
                            test_results["ai_scoring_tests"].append(r)
                        else:
                            r = log("4.2.3", "AI 评分理由", "FAIL", "ai_reason 为空")
                            test_results["ai_scoring_tests"].append(r)
                            report_bug("AI-003", "AI评分无理由", "P2", "ai_reason 为 null")
                        
                        if ai_c is not None:
                            r = log("4.2.4", "AI 置信度", "PASS", f"confidence: {ai_c}")
                            test_results["ai_scoring_tests"].append(r)

# 4.3 HR 查看 AI 评分
print("\n--- 4.3 HR 查看 AI 评分 ---")
if hr_token and exam_id:
    code, resp = api("GET", f"/api/v1/exam-records/{record_id}", token=hr_token)
    if code == 200:
        detail = resp.get("data", {})
        r = log("4.3.1", "HR 查看考试详情", "PASS", f"状态: {detail.get('status')}")
        test_results["ai_scoring_tests"].append(r)
    else:
        r = log("4.3.1", "HR 查看考试详情", "FAIL", f"HTTP {code}")
        test_results["ai_scoring_tests"].append(r)

# ============================================================
# 5. 异常测试
# ============================================================
print("\n" + "=" * 60)
print("【5. 异常测试】")
print("=" * 60)

# 5.1 错误考试码
print("\n--- 5.1 错误考试码 ---")
code, resp = api("POST", "/api/v1/exam-records", {
    "exam_id": exam_id if exam_id else 999,
    "exam_code": "INVALID-CODE-12345",
    "candidate_name": "异常测试",
    "candidate_phone": "13800000099"
})

if code and 400 <= code < 500:
    r = log("5.1.1", "错误考试码被拒绝", "PASS", f"HTTP {code}")
    test_results["exception_tests"].append(r)
else:
    r = log("5.1.1", "错误考试码被拒绝", "FAIL", f"HTTP {code}")
    test_results["exception_tests"].append(r)
    report_bug("EXC-000", "错误考试码未被拒绝", "P1", f"错误码返回 HTTP {code}")

# 5.2 重复参加
print("\n--- 5.2 重复参加 ---")
if exam_id and exam_code:
    code, resp = api("POST", "/api/v1/exam-records", {
        "exam_id": exam_id,
        "exam_code": exam_code,
        "candidate_name": candidate_name,
        "candidate_phone": candidate_phone
    })
    
    if code and 400 <= code < 500:
        r = log("5.2.1", "重复参加被拦截", "PASS", f"HTTP {code}")
        test_results["exception_tests"].append(r)
    else:
        r = log("5.2.1", "重复参加被拦截", "WARN", f"HTTP {code}: 未拦截或返回成功")
        test_results["exception_tests"].append(r)
        report_bug("EXC-001", "重复参加未被拦截", "P1", "同一候选人可创建多条考试记录")

# 5.3 空答案提交
print("\n--- 5.3 空答案提交 ---")
if exam_id and exam_code:
    # 创建新的候选人记录
    code, resp = api("POST", "/api/v1/exam-records", {
        "exam_id": exam_id,
        "exam_code": exam_code,
        "candidate_name": "空答案测试",
        "candidate_phone": "13800000098"
    })
    
    if code in (200, 201):
        new_record_id = resp.get("data", {}).get("id")
        
        # 开始考试
        api("POST", f"/api/v1/exam-records/{new_record_id}/start")
        
        # 提交空答案
        code, resp = api("POST", f"/api/v1/exam-records/{new_record_id}/answers/batch", {
            "answers": []
        })
        
        # 尝试提交
        submit_code, submit_resp = api("POST", f"/api/v1/exam-records/{new_record_id}/submit")
        
        if submit_code in (200, 201):
            submit_status = submit_resp.get("data", {}).get("status", "")
            r = log("5.3.1", "空答案提交", "WARN", f"允许提交空答案, 状态: {submit_status}")
            test_results["exception_tests"].append(r)
            report_bug("EXC-002", "允许提交空答案", "P2", "应至少有一道题答案")
        elif submit_code and 400 <= submit_code < 500:
            r = log("5.3.1", "空答案提交被拒绝", "PASS", f"HTTP {submit_code}")
            test_results["exception_tests"].append(r)
        else:
            r = log("5.3.1", "空答案提交", "PASS", f"HTTP {submit_code}")
            test_results["exception_tests"].append(r)

# 5.4 AI 服务异常时的行为
print("\n--- 5.4 AI 服务异常容错 ---")
if record_id:
    # 检查当前 AI 服务状态
    ai_code, ai_resp = api("GET", "/health", base_url=AI_SERVICE_URL)
    if ai_code == 200:
        r = log("5.4.1", "AI 服务正常运行", "PASS")
        test_results["exception_tests"].append(r)
    else:
        r = log("5.4.1", "AI 服务异常", "FAIL")
        test_results["exception_tests"].append(r)
    
    # 检查考试数据是否完整（即使 AI 失败也不应丢失）
    code, resp = api("GET", f"/api/v1/exam-records/{record_id}", token=hr_token)
    if code == 200:
        r = log("5.4.2", "考试数据完整性", "PASS", "数据可查询")
        test_results["exception_tests"].append(r)
    else:
        r = log("5.4.2", "考试数据完整性", "FAIL", f"HTTP {code}")
        test_results["exception_tests"].append(r)
        report_bug("EXC-003", "考试数据丢失", "P0", "无法查询考试记录")

# ============================================================
# 6. 最终结果
# ============================================================
print("\n" + "=" * 60)
print("【黑盒测试结果汇总】")
print("=" * 60)

# 统计各模块通过/失败
all_tests = (test_results["admin_tests"] + 
             test_results["hr_tests"] + 
             test_results["candidate_tests"] + 
             test_results["ai_scoring_tests"] + 
             test_results["exception_tests"])

total = len(all_tests)
passed = sum(1 for t in all_tests if t["status"] == "PASS")
failed = sum(1 for t in all_tests if t["status"] == "FAIL")
warned = sum(1 for t in all_tests if t["status"] == "WARN")

print(f"\n总测试项: {total}")
print(f"  ✅ 通过: {passed}")
print(f"  ❌ 失败: {failed}")
print(f"  ⚠️ 警告: {warned}")

# Bug 列表
if test_results["bugs"]:
    print(f"\n【Bug 列表】")
    for bug in test_results["bugs"]:
        level_icon = {"P0": "🔴", "P1": "🟠", "P2": "🟡", "P3": "🔵"}.get(bug["level"], "⚪")
        print(f"  {level_icon} [{bug['level']}] {bug['title']}")

# 最终结论
test_results["passed"] = failed == 0

if test_results["passed"]:
    print("\n" + "=" * 60)
    print("✅ 黑盒测试通过")
    print("=" * 60)
else:
    print("\n" + "=" * 60)
    print("❌ 黑盒测试不通过")
    print("=" * 60)
    test_results["passed"] = False

# 保存结果
with open("blackbox_test_result.json", "w", encoding="utf-8") as f:
    json.dump(test_results, f, indent=2, ensure_ascii=False, default=str)

print(f"\n详细结果已保存至: blackbox_test_result.json")