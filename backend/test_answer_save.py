"""
S3.2.3.1 答案保存接口测试脚本
测试 POST /api/v1/exam-records/{record_id}/answers 和 /answers/batch
"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def test_answer_save():
    print("=" * 60)
    print("S3.2.3.1 答案保存接口测试")
    print("=" * 60)

    # Step 1: 检查服务状态
    print("\n[1] 检查服务状态...")
    resp = requests.get("http://localhost:8000/health")
    print(f"  健康检查: {resp.status_code} - {resp.json()}")
    
    # Step 2: 登录获取 Token
    print("\n[2] 登录获取 Token...")
    login_resp = requests.post(f"{BASE_URL}/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    if login_resp.status_code != 200:
        print(f"  登录失败: {login_resp.json()}")
        # 尝试初始化用户
        print("  尝试注册管理员账号...")
        requests.post(f"{BASE_URL}/auth/register", json={
            "username": "admin",
            "password": "admin123",
            "display_name": "管理员",
            "role": "admin"
        })
        login_resp = requests.post(f"{BASE_URL}/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
    
    token = login_resp.json().get("data", {}).get("access_token", "")
    headers = {"Authorization": f"Bearer {token}"}
    print(f"  Token: {token[:20]}...")

    # Step 3: 获取或创建考试
    print("\n[3] 获取考试列表...")
    exams_resp = requests.get(f"{BASE_URL}/exams", headers=headers)
    exams_data = exams_resp.json().get("data", {})
    # 处理分页或列表格式
    if isinstance(exams_data, dict):
        exams = exams_data.get("items", exams_data.get("list", []))
    else:
        exams = exams_data
    
    if not exams:
        print("  暂无考试，创建考试...")
        exam_resp = requests.post(f"{BASE_URL}/exams", headers=headers, json={
            "title": "测试考试-答案保存测试",
            "description": "用于测试答案保存接口",
            "duration_minutes": 60,
            "pass_score": 60,
            "status": "draft"
        })
        exam_id = exam_resp.json()["data"]["id"]
        
        # 添加题目
        requests.post(f"{BASE_URL}/questions", headers=headers, json={
            "exam_id": exam_id,
            "type": "single_choice",
            "content": "测试单选题：1+1等于几？",
            "options": [
                {"label": "A", "content": "1"},
                {"label": "B", "content": "2"},
                {"label": "C", "content": "3"},
                {"label": "D", "content": "4"}
            ],
            "answer": "B",
            "score": 10,
            "sort_order": 1
        })
        
        requests.post(f"{BASE_URL}/questions", headers=headers, json={
            "exam_id": exam_id,
            "type": "multiple_choice",
            "content": "测试多选题：以下哪些是编程语言？",
            "options": [
                {"label": "A", "content": "Python"},
                {"label": "B", "content": "HTML"},
                {"label": "C", "content": "JavaScript"},
                {"label": "D", "content": "CSS"}
            ],
            "answer": "A,C",
            "score": 20,
            "sort_order": 2
        })
        
        requests.post(f"{BASE_URL}/questions", headers=headers, json={
            "exam_id": exam_id,
            "type": "short_answer",
            "content": "测试简答题：请简述什么是API？",
            "options": None,
            "answer": "API是应用程序编程接口",
            "score": 30,
            "sort_order": 3
        })
    else:
        exam_id = exams[0]["id"]
    
    print(f"  使用考试 ID: {exam_id}")

    # Step 4: 创建候选人考试记录
    print("\n[4] 创建候选人考试记录...")
    record_resp = requests.post(f"{BASE_URL}/exam-records", json={
        "exam_id": exam_id,
        "candidate_name": "测试候选人",
        "candidate_phone": "13800138000",
        "candidate_email": "test@example.com"
    })
    record_id = record_resp.json()["data"]["id"]
    print(f"  考试记录 ID: {record_id}")

    # Step 5: 获取考试试卷
    print("\n[5] 获取考试试卷...")
    paper_resp = requests.get(f"{BASE_URL}/exam-records/{record_id}/paper")
    paper_data = paper_resp.json()["data"]
    questions = paper_data["questions"]
    print(f"  题目数量: {len(questions)}")
    for q in questions:
        print(f"    - [{q['type']}] ID={q['id']}: {q['content'][:30]}...")

    # Step 6: 保存单题答案
    print("\n[6] 保存单题答案 (单选题)...")
    if len(questions) > 0:
        q1_id = questions[0]["id"]
        save_resp = requests.post(f"{BASE_URL}/exam-records/{record_id}/answers", json={
            "question_id": q1_id,
            "answer_content": "B"  # 选择正确答案 B
        })
        print(f"  状态: {save_resp.status_code}")
        print(f"  响应: {json.dumps(save_resp.json(), indent=2, ensure_ascii=False)}")
        assert save_resp.status_code == 200, "保存单题答案失败！"
        print("  ✅ 单题答案保存成功")

    # Step 7: 批量保存答案
    print("\n[7] 批量保存答案...")
    if len(questions) >= 3:
        batch_data = {
            "answers": [
                {"question_id": questions[0]["id"], "answer_content": "B"},
                {"question_id": questions[1]["id"], "answer_content": "A,C"},
                {"question_id": questions[2]["id"], "answer_content": "API是应用程序编程接口，用于不同软件组件之间的通信。"},
            ]
        }
        batch_resp = requests.post(f"{BASE_URL}/exam-records/{record_id}/answers/batch", json=batch_data)
        print(f"  状态: {batch_resp.status_code}")
        print(f"  响应: {json.dumps(batch_resp.json(), indent=2, ensure_ascii=False)}")
        assert batch_resp.status_code == 200, "批量保存答案失败！"
        print("  ✅ 批量答案保存成功")

    # Step 8: 验证答案保存 - 获取考试记录
    print("\n[8] 验证答案保存...")
    detail_resp = requests.get(f"{BASE_URL}/exam-records/{record_id}")
    print(f"  状态: {detail_resp.status_code}")
    print(f"  响应: {json.dumps(detail_resp.json(), indent=2, ensure_ascii=False)}")

    # Step 9: 测试幂等性 - 重复保存同一题
    print("\n[9] 测试幂等性 - 重复保存同一题...")
    if len(questions) > 0:
        q1_id = questions[0]["id"]
        save_resp2 = requests.post(f"{BASE_URL}/exam-records/{record_id}/answers", json={
            "question_id": q1_id,
            "answer_content": "A"  # 修改答案为 A
        })
        print(f"  状态: {save_resp2.status_code}")
        print(f"  响应: {json.dumps(save_resp2.json(), indent=2, ensure_ascii=False)}")
        assert save_resp2.status_code == 200, "幂等更新失败！"
        print("  ✅ 幂等更新成功")

    # Step 10: 测试错误场景 - 无效的题目 ID
    print("\n[10] 测试错误场景 - 无效题目ID...")
    error_resp = requests.post(f"{BASE_URL}/exam-records/{record_id}/answers", json={
        "question_id": 99999,
        "answer_content": "test"
    })
    print(f"  状态: {error_resp.status_code}")
    print(f"  响应: {json.dumps(error_resp.json(), indent=2, ensure_ascii=False)}")
    assert error_resp.status_code == 404, "应该返回404错误！"
    print("  ✅ 错误场景处理正确")

    print("\n" + "=" * 60)
    print("🎉 所有测试通过！")
    print("=" * 60)


if __name__ == "__main__":
    test_answer_save()
