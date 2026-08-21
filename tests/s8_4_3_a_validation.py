"""
S8.4.3-a 验证脚本
验证：
1. MonitorAnalysisResponse 包含 behavior_tags/behavior_details
2. GradingResultItem 包含 has_monitor_data/monitor_risk_level
3. 序列化兼容性
"""
import os
import sys

backend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")
sys.path.insert(0, backend_path)

from app.schemas.grading import (
    MonitorAnalysisResponse,
    GradingResultItem,
    GradingResultListResponse,
)


def test_1_schema_fields():
    """测试1: MonitorAnalysisResponse 新增字段"""
    print("=" * 60)
    print("测试1: MonitorAnalysisResponse 字段验证")
    
    # 有数据场景
    resp = MonitorAnalysisResponse(
        has_analysis=True,
        exam_duration=2700,
        leave_ratio=11.7,
        max_single_duration=300,
        average_leave_duration=64.0,
        risk_reason="考试期间5次离开页面，存在1次超过5分钟离开",
        behavior_tags=['rapid_leave_return', 'long_leave', 'frequent_leave'],
        behavior_details=[
            {'time': '10:20:01', 'duration': '300秒', 'tags': ['long_leave'], 'tag_texts': ['⏱️ 长时间离开']},
        ],
    )
    
    data = resp.model_dump()
    print(f"  behavior_tags: {data['behavior_tags']}")
    print(f"  behavior_details: {data['behavior_details']}")
    assert 'behavior_tags' in data, "❌ behavior_tags 字段缺失"
    assert 'behavior_details' in data, "❌ behavior_details 字段缺失"
    assert len(data['behavior_tags']) == 3
    assert len(data['behavior_details']) == 1
    print("  ✅ 字段完整\n")
    
    # 无数据场景（历史兼容）
    resp_empty = MonitorAnalysisResponse()
    data_empty = resp_empty.model_dump()
    print(f"  空数据 behavior_tags: {data_empty['behavior_tags']}")
    print(f"  空数据 behavior_details: {data_empty['behavior_details']}")
    assert data_empty['behavior_tags'] == [], "❌ 空数据应为空列表"
    assert data_empty['behavior_details'] == [], "❌ 空数据应为空列表"
    print("  ✅ 默认值正确\n")


def test_2_grading_result_item():
    """测试2: GradingResultItem 新增字段"""
    print("=" * 60)
    print("测试2: GradingResultItem 字段验证")
    
    # 有监考数据
    item = GradingResultItem(
        id=1,
        exam_record_id=100,
        exam_id=1,
        candidate_name="张三",
        candidate_phone="13800138000",
        status="completed",
        grading_type="auto",
        total_score=85.0,
        has_monitor_data=True,
        monitor_risk_level="medium",
    )
    
    data = item.model_dump()
    print(f"  has_monitor_data: {data['has_monitor_data']}")
    print(f"  monitor_risk_level: {data['monitor_risk_level']}")
    assert data['has_monitor_data'] == True
    assert data['monitor_risk_level'] == 'medium'
    print("  ✅ 有监考数据正确\n")
    
    # 无监考数据（历史记录）
    item_old = GradingResultItem(
        id=2,
        exam_record_id=200,
        exam_id=1,
        candidate_name="李四",
        candidate_phone="13900139000",
        status="completed",
        grading_type="auto",
        total_score=90.0,
    )
    
    data_old = item_old.model_dump()
    print(f"  历史数据 has_monitor_data: {data_old['has_monitor_data']}")
    print(f"  历史数据 monitor_risk_level: {data_old['monitor_risk_level']}")
    assert data_old['has_monitor_data'] == False
    assert data_old['monitor_risk_level'] == 'normal'
    print("  ✅ 历史数据默认值正确\n")


def test_3_list_response_compatibility():
    """测试3: 列表响应兼容性"""
    print("=" * 60)
    print("测试3: GradingResultListResponse 兼容性")
    
    items = [
        GradingResultItem(
            id=1, exam_record_id=100, exam_id=1,
            candidate_name="张三", status="completed", grading_type="auto",
            total_score=85.0, has_monitor_data=True, monitor_risk_level="high",
        ),
        GradingResultItem(
            id=2, exam_record_id=200, exam_id=1,
            candidate_name="李四", status="completed", grading_type="auto",
            total_score=90.0,
        ),
    ]
    
    response = GradingResultListResponse(
        items=items,
        total=2,
        page=1,
        page_size=10,
    )
    
    data = response.model_dump()
    print(f"  items count: {len(data['items'])}")
    print(f"  Item 0: has_monitor={data['items'][0]['has_monitor_data']}, risk={data['items'][0]['monitor_risk_level']}")
    print(f"  Item 1: has_monitor={data['items'][1]['has_monitor_data']}, risk={data['items'][1]['monitor_risk_level']}")
    
    # 验证序列化后字段完整
    for i, item in enumerate(data['items']):
        assert 'has_monitor_data' in item, f"❌ Item {i} 缺少 has_monitor_data"
        assert 'monitor_risk_level' in item, f"❌ Item {i} 缺少 monitor_risk_level"
    
    print("  ✅ 列表响应兼容\n")


def test_4_fastapi_serialization():
    """测试4: FastAPI 序列化模拟"""
    print("=" * 60)
    print("测试4: 完整序列化模拟")
    
    # 模拟后端返回的完整数据
    result = {
        "grading_id": 1,
        "status": "completed",
        "grading_type": "auto",
        "exam_record_id": 100,
        "exam_id": 1,
        "exam_title": "AI 基础考试",
        "candidate_name": "张三",
        "candidate_phone": "13800138000",
        "candidate_email": "zhangsan@test.com",
        "total_score": 85.0,
        "auto_score": 40.0,
        "ai_score": 45.0,
        "review_score": None,
        "review_comment": None,
        "passed": True,
        "start_time": "2026-08-20T10:00:00",
        "complete_time": "2026-08-20T10:45:00",
        "error_message": None,
        "statistics": {"total_questions": 20, "answered_count": 20, "correct_count": 15, "correct_rate": 75.0},
        "answers": [],
        "monitor_data": {
            "has_monitor_data": True,
            "risk_level": "medium",
            "leave_count": 5,
            "total_duration": 320,
            "events": [],
        },
        "monitor_analysis": {
            "has_analysis": True,
            "exam_duration": 2700,
            "leave_ratio": 11.7,
            "max_single_duration": 300,
            "average_leave_duration": 64.0,
            "risk_reason": "考试期间5次离开页面",
            "behavior_tags": ['rapid_leave_return', 'frequent_leave'],
            "behavior_details": [
                {"time": "10:20:01", "duration": "10秒", "tags": ["rapid_leave_return"], "tag_texts": ["⚡ 快速返回"]},
            ],
        },
    }
    
    from app.schemas.grading import GradingResultDetailResponse
    response = GradingResultDetailResponse(**result)
    data = response.model_dump()
    
    ma = data['monitor_analysis']
    print(f"  behavior_tags: {ma['behavior_tags']}")
    print(f"  behavior_details count: {len(ma['behavior_details'])}")
    assert len(ma['behavior_tags']) == 2, "❌ behavior_tags 数量不对"
    assert len(ma['behavior_details']) == 1, "❌ behavior_details 数量不对"
    print("  ✅ 完整序列化通过\n")
    
    # 验证无监考数据的历史记录
    result_old = result.copy()
    result_old['monitor_data'] = None
    result_old['monitor_analysis'] = None
    result_old['monitor_analysis'] = None
    
    response_old = GradingResultDetailResponse(**result_old)
    data_old = response_old.model_dump()
    assert data_old['monitor_analysis'] is None, "❌ 历史记录应为 None"
    print("  ✅ 历史记录兼容")


if __name__ == '__main__':
    print("╔══════════════════════════════════════════════╗")
    print("║  S8.4.3-a Schema & API 验证                 ║")
    print("╚══════════════════════════════════════════════╝")
    print()
    
    test_1_schema_fields()
    test_2_grading_result_item()
    test_3_list_response_compatibility()
    test_4_fastapi_serialization()
    
    print("╔══════════════════════════════════════════════╗")
    print("║  所有验证通过 ✅                             ║")
    print("╚══════════════════════════════════════════════╝")