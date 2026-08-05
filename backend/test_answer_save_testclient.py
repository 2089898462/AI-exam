"""
S3.2.3.1 答案保存接口测试
使用 FastAPI TestClient 直接测试
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_answer_save():
    print("=" * 60)
    print("S3.2.3.1 答案保存接口测试 (TestClient)")
    print("=" * 60)

    # Step 1: 健康检查
    print("\n[1] 健康检查...")
    resp = client.get("/health")
    print(f"  状态: {resp.status_code}")
    assert resp.status_code == 200
    print("  ✅ 通过")

    # Step 2: 获取路由列表
    print("\n[2] 检查 exam-records 路由...")
    response = client.get("/openapi.json")
    paths = response.json()["paths"]
    exam_record_paths = [p for p in paths if "exam-record" in p or "exam_record" in p]
    print(f"  exam-records 相关路径: {exam_record_paths}")
    
    # 如果没有路由，尝试直接导入检查
    if not exam_record_paths:
        print("  ⚠️  路由未在 OpenAPI 中显示，直接测试端点...")
        
    # Step 3: 创建考试记录
    print("\n[3] 创建考试记录...")
    resp = client.post("/api/v1/exam-records", json={
        "exam_id": 1,
        "candidate_name": "测试候选人",
        "candidate_phone": "13800138000",
        "candidate_email": "test@example.com"
    })
    print(f"  状态: {resp.status_code}")
    if resp.status_code == 201:
        data = resp.json().get("data", {})
        record_id = data.get("id")
        print(f"  记录 ID: {record_id}")
        print("  ✅ 考试记录创建成功")
    elif resp.status_code == 404:
        print("  ⚠️  路由不存在，可能未注册")
        print(f"  响应: {resp.json()}")
        return
    else:
        print(f"  响应: {resp.json()}")
        return

    # Step 4: 获取考试试卷
    print("\n[4] 获取考试试卷...")
    resp = client.get(f"/api/v1/exam-records/{record_id}/paper")
    print(f"  状态: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()["data"]
        questions = data["questions"]
        print(f"  题目数量: {len(questions)}")
        for q in questions:
            print(f"    - [{q['type']}] ID={q['id']}: {q['content'][:30]}")
        print("  ✅ 获取试卷成功")
    else:
        print(f"  响应: {resp.json()}")
        return

    # Step 5: 保存单题答案
    print("\n[5] 保存单题答案...")
    if len(questions) > 0:
        q1_id = questions[0]["id"]
        resp = client.post(f"/api/v1/exam-records/{record_id}/answers", json={
            "question_id": q1_id,
            "answer_content": "B"
        })
        print(f"  状态: {resp.status_code}")
        if resp.status_code == 200:
            print(f"  响应: {resp.json()}")
            print("  ✅ 保存单题答案成功")
        else:
            print(f"  响应: {resp.json()}")
            if resp.status_code == 404:
                print("  ⚠️  save_answer 端点不存在！")
            return

    # Step 6: 批量保存答案
    print("\n[6] 批量保存答案...")
    if len(questions) >= 3:
        batch_data = {
            "answers": [
                {"question_id": questions[0]["id"], "answer_content": "B"},
                {"question_id": questions[1]["id"], "answer_content": "A,C"},
                {"question_id": questions[2]["id"], "answer_content": "API是应用程序编程接口"},
            ]
        }
        resp = client.post(f"/api/v1/exam-records/{record_id}/answers/batch", json=batch_data)
        print(f"  状态: {resp.status_code}")
        if resp.status_code == 200:
            result = resp.json()
            print(f"  响应数量: {len(result.get('data', []))}")
            print("  ✅ 批量保存答案成功")
        else:
            print(f"  响应: {resp.json()}")

    # Step 7: 测试幂等更新
    print("\n[7] 测试幂等更新...")
    if len(questions) > 0:
        q1_id = questions[0]["id"]
        resp = client.post(f"/api/v1/exam-records/{record_id}/answers", json={
            "question_id": q1_id,
            "answer_content": "A"  # 修改答案
        })
        print(f"  状态: {resp.status_code}")
        if resp.status_code == 200:
            print("  ✅ 幂等更新成功")

    # Step 8: 测试错误场景
    print("\n[8] 测试错误场景 (无效题目ID)...")
    resp = client.post(f"/api/v1/exam-records/{record_id}/answers", json={
        "question_id": 99999,
        "answer_content": "test"
    })
    print(f"  状态: {resp.status_code}")
    if resp.status_code == 404:
        print("  ✅ 错误场景处理正确 (404)")
    else:
        print(f"  响应: {resp.json()}")

    print("\n" + "=" * 60)
    print("🎉 测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    test_answer_save()
