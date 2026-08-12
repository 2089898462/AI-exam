"""
S5.7-E AI阅卷完整业务验收测试脚本

测试流程：
1. HR 登录获取 Token
2. 创建考试
3. 添加题目（单选、判断、简答）
4. 发布考试
5. 候选人进入考试
6. 答题并保存
7. 提交试卷（触发 AI 评分）
8. 等待 AI 评分完成
9. 验证评分结果
10. HR 查看成绩

使用方法：python run_acceptance_test.py
"""
import os
import sys
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

# 配置
BACKEND_URL = "http://localhost:8000"
AI_SERVICE_URL = "http://localhost:8001"

results = {
    "test_flow": [],
    "api_results": {},
    "ai_results": {},
    "db_validation": {},
    "issues": [],
    "passed": False
}

def api_request(method, path, data=None, token=None, base_url=BACKEND_URL):
    """统一 API 请求方法"""
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
            except (json.JSONDecodeError, ValueError):
                return resp.status, {"raw": raw.decode("utf-8", errors="replace")}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(error_body)
        except:
            return e.code, {"detail": error_body}
    except Exception as e:
        return None, {"error": str(e)}

def step_log(step, message, status="INFO"):
    prefix = {"INFO": "ℹ️", "SUCCESS": "✅", "FAIL": "❌", "WARN": "⚠️"}.get(status, "ℹ️")
    print(f"  [{step}] {prefix} {message}")

# ============================================================
# 0. 前置检查
# ============================================================
print("=" * 60)
print("S5.7-E AI阅卷完整业务验收测试")
print("=" * 60)

# 检查后端
code, resp = api_request("GET", "/docs")
if code is None or code >= 500:
    print("❌ 后端服务未启动 (http://localhost:8000)")
    sys.exit(1)
print("✅ 后端服务正常")

# 检查 AI 服务
code, resp = api_request("GET", "/health", base_url=AI_SERVICE_URL)
if code is None or code >= 500:
    print("❌ AI 服务未启动 (http://localhost:8001)")
    sys.exit(1)
print("✅ AI 服务正常")

# ============================================================
# 1. HR 登录
# ============================================================
print("\n" + "-" * 40)
print("【步骤 1】HR 登录")
print("-" * 40)

# 先尝试登录，如果失败则注册一个新用户
code, resp = api_request("POST", "/api/v1/auth/login", {
    "username": "hr_test",
    "password": "test123456"
})

if code != 200:
    # 注册
    code, resp = api_request("POST", "/api/v1/auth/register", {
        "username": "hr_test",
        "password": "test123456",
        "display_name": "测试HR",
        "role": "hr"
    })
    if code not in (200, 201):
        step_log("1.1", f"登录/注册失败: {resp}", "FAIL")
        results["issues"].append(f"HR 登录失败: {resp}")
        sys.exit(1)

token = resp.get("data", {}).get("access_token", "")
if not token:
    step_log("1.1", f"Token 获取失败: {resp}", "FAIL")
    results["issues"].append(f"Token 获取失败")
    sys.exit(1)

step_log("1.1", f"HR 登录成功, Token: {token[:20]}...", "SUCCESS")
results["api_results"]["hr_login"] = True

# ============================================================
# 2. 创建考试
# ============================================================
print("\n" + "-" * 40)
print("【步骤 2】创建考试")
print("-" * 40)

code, resp = api_request("POST", "/api/v1/exams", {
    "title": "S5.7-E 验收测试考试",
    "exam_code": "ACCEPT-" + str(int(time.time())),
    "description": "AI阅卷完整业务验收测试用",
    "duration_minutes": 30,
    "pass_score": 60
}, token=token)

if code not in (200, 201):
    step_log("2.1", f"创建考试失败: {resp}", "FAIL")
    results["issues"].append(f"创建考试失败: {resp}")
    sys.exit(1)

exam_data = resp.get("data", {})
exam_id = exam_data.get("id")
exam_code = exam_data.get("exam_code")
exam_status = exam_data.get("status")

step_log("2.1", f"考试创建成功, ID: {exam_id}, Code: {exam_code}", "SUCCESS")
step_log("2.2", f"考试状态: {exam_status}", "INFO")
results["api_results"]["create_exam"] = {"exam_id": exam_id, "exam_code": exam_code}

# 验证 exam_code 自动生成
if exam_code:
    step_log("2.3", f"exam_code 自动生成: {exam_code}", "SUCCESS")
else:
    step_log("2.3", "exam_code 为空", "FAIL")
    results["issues"].append("exam_code 未自动生成")

# ============================================================
# 3. 添加题目
# ============================================================
print("\n" + "-" * 40)
print("【步骤 3】添加题目")
print("-" * 40)

questions_added = []

# 3.1 单选题
code, resp = api_request("POST", f"/api/v1/questions?exam_id={exam_id}", {
    "type": "single_choice",
    "content": "以下哪个是 JavaScript 的基本数据类型？",
    "options": [
        {"label": "A", "text": "Array"},
        {"label": "B", "text": "String"},
        {"label": "C", "text": "Object"},
        {"label": "D", "text": "Function"}
    ],
    "answer": "B",
    "score": 10,
    "sort_order": 1
}, token=token)

if code in (200, 201):
    q_id = resp.get("data", {}).get("id")
    questions_added.append({"id": q_id, "type": "single_choice", "score": 10})
    step_log("3.1", f"单选题添加成功, ID: {q_id}", "SUCCESS")
else:
    step_log("3.1", f"单选题添加失败: {resp}", "FAIL")
    results["issues"].append(f"单选题添加失败: {resp}")

# 3.2 判断题
code, resp = api_request("POST", f"/api/v1/questions?exam_id={exam_id}", {
    "type": "true_false",
    "content": "Python 是动态类型语言。",
    "answer": "true",
    "score": 5,
    "sort_order": 2
}, token=token)

if code in (200, 201):
    q_id = resp.get("data", {}).get("id")
    questions_added.append({"id": q_id, "type": "true_false", "score": 5})
    step_log("3.2", f"判断题添加成功, ID: {q_id}", "SUCCESS")
else:
    step_log("3.2", f"判断题添加失败: {resp}", "FAIL")
    results["issues"].append(f"判断题添加失败: {resp}")

# 3.3 简答题（AI 评分重点）
code, resp = api_request("POST", f"/api/v1/questions?exam_id={exam_id}", {
    "type": "short_answer",
    "content": "解释 Vue3 中的响应式原理。",
    "answer": "Vue3 通过 Proxy 实现响应式，通过代理对象拦截数据访问和修改。",
    "score": 15,
    "sort_order": 3
}, token=token)

if code in (200, 201):
    q_id = resp.get("data", {}).get("id")
    questions_added.append({"id": q_id, "type": "short_answer", "score": 15})
    step_log("3.3", f"简答题添加成功, ID: {q_id}", "SUCCESS")
else:
    step_log("3.3", f"简答题添加失败: {resp}", "FAIL")
    results["issues"].append(f"简答题添加失败: {resp}")

results["api_results"]["questions_added"] = len(questions_added)

# ============================================================
# 4. 发布考试
# ============================================================
print("\n" + "-" * 40)
print("【步骤 4】发布考试")
print("-" * 40)

code, resp = api_request("POST", f"/api/v1/exams/{exam_id}/publish", token=token)

if code in (200, 201):
    step_log("4.1", "考试发布成功", "SUCCESS")
    results["api_results"]["publish_exam"] = True
else:
    step_log("4.1", f"考试发布失败: {resp}", "FAIL")
    results["issues"].append(f"考试发布失败: {resp}")
    sys.exit(1)

# ============================================================
# 5. 添加候选人到考试参与人员
# ============================================================
print("\n" + "-" * 40)
print("【步骤 5】添加候选人到参与人员")
print("-" * 40)

candidate_name = "验收测试候选人"
candidate_phone = "13800000001"

code, resp = api_request("POST", f"/api/v1/exams/{exam_id}/participants", {
    "candidate_name": candidate_name,
    "candidate_phone": candidate_phone,
    "candidate_email": "test@example.com"
}, token=token)

if code in (200, 201):
    step_log("5.1", "参与人员添加成功", "SUCCESS")
    results["api_results"]["add_participant"] = True
else:
    step_log("5.1", f"参与人员添加失败: {resp}", "FAIL")
    results["issues"].append(f"参与人员添加失败: {resp}")

# ============================================================
# 6. 候选人进入考试
# ============================================================
print("\n" + "-" * 40)
print("【步骤 6】候选人进入考试")
print("-" * 40)

code, resp = api_request("POST", "/api/v1/exam-records", {
    "exam_id": exam_id,
    "exam_code": exam_code,
    "candidate_name": candidate_name,
    "candidate_phone": candidate_phone
})

if code in (200, 201):
    record_data = resp.get("data", {})
    record_id = record_data.get("id")
    step_log("6.1", f"候选人进入考试成功, Record ID: {record_id}", "SUCCESS")
    results["api_results"]["create_record"] = {"record_id": record_id}
else:
    step_log("6.1", f"候选人进入考试失败: {resp}", "FAIL")
    results["issues"].append(f"候选人进入考试失败: {resp}")
    sys.exit(1)

# 6.1 验证防重复参加
code2, resp2 = api_request("POST", "/api/v1/exam-records", {
    "exam_id": exam_id,
    "exam_code": exam_code,
    "candidate_name": candidate_name,
    "candidate_phone": candidate_phone
})

if code2 in (200, 201):
    step_log("6.2", "防重复参加：未拦截（返回了新记录）", "WARN")
    results["issues"].append("防重复参加可能未生效")
else:
    step_log("6.2", "防重复参加：已拦截", "SUCCESS")

# ============================================================
# 7. 开始考试 & 答题
# ============================================================
print("\n" + "-" * 40)
print("【步骤 7】答题流程")
print("-" * 40)

# 7.1 开始考试
code, resp = api_request("POST", f"/api/v1/exam-records/{record_id}/start")
if code in (200, 201):
    step_log("7.1", "考试开始", "SUCCESS")
else:
    step_log("7.1", f"考试开始失败: {resp}", "FAIL")
    results["issues"].append(f"考试开始失败: {resp}")

# 7.2 保存答案
answers = []
for q in questions_added:
    if q["type"] == "single_choice":
        answers.append({"question_id": q["id"], "answer": "B"})
    elif q["type"] == "true_false":
        answers.append({"question_id": q["id"], "answer": "true"})
    elif q["type"] == "short_answer":
        answers.append({"question_id": q["id"], "answer": "Vue3使用Proxy监听对象变化，实现数据自动更新。"})

code, resp = api_request("POST", f"/api/v1/exam-records/{record_id}/answers/batch", {
    "answers": answers
})

if code in (200, 201):
    step_log("7.2", f"答案保存成功 ({len(answers)} 题)", "SUCCESS")
else:
    step_log("7.2", f"答案保存失败: {resp}", "FAIL")
    results["issues"].append(f"答案保存失败: {resp}")

# ============================================================
# 8. 提交试卷（触发 AI 评分）
# ============================================================
print("\n" + "-" * 40)
print("【步骤 8】提交试卷（触发 AI 评分）")
print("-" * 40)

code, resp = api_request("POST", f"/api/v1/exam-records/{record_id}/submit")

if code in (200, 201):
    submit_data = resp.get("data", {})
    exam_record_status = submit_data.get("status", "")
    step_log("8.1", f"提交成功, 状态: {exam_record_status}", "SUCCESS")
    results["api_results"]["submit_exam"] = {"status": exam_record_status}
else:
    step_log("8.1", f"提交失败: {resp}", "FAIL")
    results["issues"].append(f"提交失败: {resp}")
    sys.exit(1)

# ============================================================
# 9. 等待 AI 评分完成
# ============================================================
print("\n" + "-" * 40)
print("【步骤 9】等待 AI 评分完成")
print("-" * 40)

max_wait = 60  # 最多等待 60 秒
wait_time = 0
grading_result = None

while wait_time < max_wait:
    time.sleep(3)
    wait_time += 3
    
    # 查询评分状态
    code, resp = api_request("GET", f"/api/v1/exam-records/{record_id}/grading", token=token)
    
    if code == 200:
        grading_data = resp.get("data", {})
        if isinstance(grading_data, dict):
            status = grading_data.get("status", "")
            step_log("9.1", f"[{wait_time}s] 评分状态: {status}", "INFO")
            
            if status in ("completed", "graded", "failed"):
                grading_result = grading_data
                break
        elif isinstance(grading_data, list) and len(grading_data) > 0:
            grading_result = grading_data[0]
            status = grading_result.get("status", "")
            step_log("9.1", f"[{wait_time}s] 评分状态: {status}", "INFO")
            if status in ("completed", "graded", "failed"):
                break
    else:
        step_log("9.1", f"[{wait_time}s] 查询失败: HTTP {code}", "WARN")

if not grading_result:
    step_log("9.1", f"等待超时 ({max_wait}s)", "FAIL")
    results["issues"].append(f"AI 评分等待超时")
else:
    step_log("9.1", f"AI 评分完成 (等待 {wait_time}s)", "SUCCESS")

# ============================================================
# 10. 验证 AI 评分结果
# ============================================================
print("\n" + "-" * 40)
print("【步骤 10】验证 AI 评分结果")
print("-" * 40)

if grading_result:
    status = grading_result.get("status", "")
    total_score = grading_result.get("total_score")
    results["ai_results"]["status"] = status
    results["ai_results"]["total_score"] = total_score
    
    step_log("10.1", f"评分状态: {status}", "SUCCESS" if status in ("completed", "graded") else "FAIL")
    step_log("10.2", f"总分数: {total_score}", "SUCCESS" if total_score else "FAIL")
    
    # 检查简答题评分详情
    # 通过查询答题详情来检查
    code, resp = api_request("GET", f"/api/v1/exams/{exam_id}/records/{record_id}/answers", token=token)
    if code == 200:
        answers_data = resp.get("data", [])
        results["ai_results"]["answers_detail"] = len(answers_data)
        
        for ans in answers_data if isinstance(answers_data, list) else answers_data.get("items", []):
            if isinstance(ans, dict):
                q_type = ans.get("question_type", "")
                ai_score = ans.get("ai_score")
                ai_reason = ans.get("ai_reason")
                
                if q_type == "short_answer":
                    if ai_score is not None:
                        step_log("10.3", f"简答题 AI 评分: {ai_score} 分", "SUCCESS")
                    else:
                        step_log("10.3", "简答题 AI 评分: 未评分", "WARN")
                    
                    if ai_reason:
                        step_log("10.4", f"AI 评分理由: {str(ai_reason)[:50]}...", "SUCCESS")
                    else:
                        step_log("10.4", "AI 评分理由: 缺失", "WARN")
    else:
        step_log("10.3", f"答题详情查询失败: HTTP {code}", "WARN")
else:
    step_log("10.1", "无评分结果", "FAIL")

# ============================================================
# 11. HR 查看考试成绩
# ============================================================
print("\n" + "-" * 40)
print("【步骤 11】HR 查看考试成绩")
print("-" * 40)

code, resp = api_request("GET", f"/api/v1/exams/{exam_id}/results", token=token)

if code == 200:
    results_data = resp.get("data", {})
    step_log("11.1", "HR 查看成绩成功", "SUCCESS")
    results["api_results"]["hr_view_results"] = True
    
    # 检查数据
    if isinstance(results_data, dict):
        total_records = results_data.get("total_records", 0)
        passed = results_data.get("passed", 0)
        step_log("11.2", f"考试记录数: {total_records}, 通过: {passed}", "INFO")
    elif isinstance(results_data, list):
        step_log("11.2", f"考试记录数: {len(results_data)}", "INFO")
else:
    step_log("11.1", f"HR 查看成绩失败: {resp}", "FAIL")
    results["issues"].append(f"HR 查看成绩失败: {resp}")

# ============================================================
# 12. 异常检查
# ============================================================
print("\n" + "-" * 40)
print("【步骤 12】异常检查")
print("-" * 40)

# 12.1 检查数据库中 answer_record 的 answer_content 字段
# 通过答题详情 API 间接验证
code, resp = api_request("GET", f"/api/v1/exam-records/{record_id}", token=token)
if code == 200:
    record_detail = resp.get("data", {})
    step_log("12.1", "考试记录详情可查询", "SUCCESS")
    
    # 检查 exam_record 状态
    record_status = record_detail.get("status", "")
    step_log("12.2", f"ExamRecord 状态: {record_status}", "SUCCESS" if record_status == "submitted" else "WARN")
else:
    step_log("12.1", "考试记录详情查询失败", "WARN")

# 12.2 验证 AI 调用日志（检查 AI 服务日志）
code, resp = api_request("GET", "/health", base_url=AI_SERVICE_URL)
if code == 200:
    step_log("12.3", "AI 服务仍在正常运行", "SUCCESS")
else:
    step_log("12.3", "AI 服务异常", "FAIL")
    results["issues"].append("AI 服务异常")

# ============================================================
# 输出最终结果
# ============================================================
print("\n" + "=" * 60)
print("【验收测试结果】")
print("=" * 60)

# 综合判定
all_checks = [
    results["api_results"].get("hr_login", False),
    results["api_results"].get("create_exam", {}).get("exam_id") is not None,
    len(questions_added) == 3,
    results["api_results"].get("publish_exam", False),
    results["api_results"].get("add_participant", False),
    results["api_results"].get("create_record", {}).get("record_id") is not None,
    results["api_results"].get("submit_exam", {}).get("status") == "submitted",
    grading_result is not None,
    results["api_results"].get("hr_view_results", False),
]

results["passed"] = all(all_checks)

check_labels = [
    "HR 登录", "创建考试", "添加 3 道题目", "发布考试",
    "添加参与人员", "候选人进入", "提交试卷", "AI 评分完成", "HR 查看成绩"
]

for label, check in zip(check_labels, all_checks):
    print(f"  {'✅' if check else '❌'} {label}")

print(f"\n最终结论: {'✅ S5.7-E通过' if results['passed'] else '❌ S5.7-E未通过'}")

if results["issues"]:
    print(f"\n问题列表:")
    for issue in results["issues"]:
        print(f"  ⚠️ {issue}")

# 保存结果
with open("acceptance_test_result.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False, default=str)

print(f"\n详细结果已保存至: acceptance_test_result.json")