"""
S8.4.2 异常行为检测增强 - 单元测试
测试场景：
1. 正常考试 → normal
2. 快速返回（3秒）→ low
3. 高频切屏（5分钟内≥3次）→ medium以上
4. 长时间离开（5分钟）→ high
5. 断网场景 → normal（网络豁免）
6. 历史数据兼容
"""

import os
import sys
import json

# 添加后端路径
backend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")
sys.path.insert(0, backend_path)

from app.services.exam_record_service import ExamRecordService


def test_1_normal_exam():
    """测试1: 正常考试 - 无切屏"""
    print("=" * 60)
    print("测试1: 正常考试")
    
    monitor_data = {
        'leave_count': 0,
        'total_hidden_duration': 0,
        'events': [],
        'environment': None,
    }
    
    result = ExamRecordService.analyze_monitor_behavior(monitor_data)
    print(f"  behavior_tags: {result['behavior_tags']}")
    print(f"  risk_reason: {result['risk_reason']}")
    
    # 无离开事件的风险计算
    risk = ExamRecordService._calculate_risk_level_v3(
        leave_count=0,
        total_duration_seconds=0,
        max_single_duration=0,
        leave_ratio=0.0,
        leave_frequency=0,
        behavior_tags=result['behavior_tags'],
    )
    
    assert risk == 'normal', f"预期 normal, 实际 {risk}"
    assert result['behavior_tags'] == [], f"预期空列表, 实际 {result['behavior_tags']}"
    print(f"  风险等级: {risk} ✓")
    print("  ✅ 测试1通过\n")


def test_2_rapid_return():
    """测试2: 快速返回 - 离开3秒返回"""
    print("=" * 60)
    print("测试2: 快速返回（3秒）")
    
    now = 1000000
    monitor_data = {
        'leave_count': 1,
        'total_hidden_duration': 3000,  # 3秒
        'events': [
            {
                'type': 'exam_leave',
                'timestamp': now,
                'duration': 3000,
            },
            {
                'type': 'exam_return',
                'timestamp': now + 3000,
                'duration': 3000,
                'tags': ['rapid_leave_return'],
            },
        ],
    }
    
    result = ExamRecordService.analyze_monitor_behavior(monitor_data)
    print(f"  behavior_tags: {result['behavior_tags']}")
    print(f"  risk_reason: {result['risk_reason']}")
    
    # 验证标签
    assert 'rapid_leave_return' in result['behavior_tags'], \
        f"预期包含 rapid_leave_return, 实际 {result['behavior_tags']}"
    
    risk = ExamRecordService._calculate_risk_level_v3(
        leave_count=1,
        total_duration_seconds=3,
        max_single_duration=3,
        leave_ratio=0.1,
        leave_frequency=0.5,
        behavior_tags=result['behavior_tags'],
        rapid_trips=result['analysis']['rapid_trips'],
    )
    
    # 快速返回1次 → low
    assert risk == 'low', f"预期 low, 实际 {risk}"
    print(f"  风险等级: {risk} ✓")
    print(f"  标签: {result['behavior_tags']} ✓")
    print("  ✅ 测试2通过\n")


def test_3_frequent_leave():
    """测试3: 高频切屏 - 5分钟内切屏4次"""
    print("=" * 60)
    print("测试3: 高频切屏（5分钟内4次）")
    
    now = 1000000
    # 模拟5分钟内4次离开，每次10秒
    events = []
    for i in range(4):
        events.append({
            'type': 'exam_leave',
            'timestamp': now + i * 60000,  # 每1分钟1次
            'duration': 10000,
            'tags': ['frequent_leave'],
        })
        events.append({
            'type': 'exam_return',
            'timestamp': now + i * 60000 + 10000,
            'duration': 10000,
        })
    
    monitor_data = {
        'leave_count': 4,
        'total_hidden_duration': 40000,  # 40秒
        'events': events,
    }
    
    result = ExamRecordService.analyze_monitor_behavior(monitor_data)
    print(f"  behavior_tags: {result['behavior_tags']}")
    print(f"  risk_reason: {result['risk_reason']}")
    
    assert 'frequent_leave' in result['behavior_tags'], \
        f"预期包含 frequent_leave, 实际 {result['behavior_tags']}"
    
    analysis = result['analysis']
    print(f"  max_leave_density: {analysis['max_leave_density']}")
    print(f"  rapid_trips: {analysis['rapid_trips']}")
    
    risk = ExamRecordService._calculate_risk_level_v3(
        leave_count=4,
        total_duration_seconds=40,
        max_single_duration=10,
        leave_ratio=1.0,
        leave_frequency=8.0,
        behavior_tags=result['behavior_tags'],
        rapid_trips=analysis['rapid_trips'],
        max_density=analysis['max_leave_density'],
    )
    
    # 高频离开 → 至少 medium
    assert risk in ('medium', 'high'), f"预期 medium/high, 实际 {risk}"
    print(f"  风险等级: {risk} ✓")
    print(f"  标签: {result['behavior_tags']} ✓")
    print("  ✅ 测试3通过\n")


def test_4_long_leave():
    """测试4: 长时间离开 - 离开5分钟"""
    print("=" * 60)
    print("测试4: 长时间离开（5分钟）")
    
    now = 1000000
    monitor_data = {
        'leave_count': 1,
        'total_hidden_duration': 300000,  # 5分钟 = 300秒
        'events': [
            {
                'type': 'exam_leave',
                'timestamp': now,
                'duration': 300000,
                'tags': ['long_leave'],
            },
            {
                'type': 'exam_return',
                'timestamp': now + 300000,
                'duration': 300000,
                'tags': ['long_leave'],
            },
        ],
    }
    
    result = ExamRecordService.analyze_monitor_behavior(monitor_data)
    print(f"  behavior_tags: {result['behavior_tags']}")
    print(f"  risk_reason: {result['risk_reason']}")
    
    assert 'long_leave' in result['behavior_tags'], \
        f"预期包含 long_leave, 实际 {result['behavior_tags']}"
    assert result['analysis']['max_single_duration'] >= 60, \
        f"预期 max_single_duration >= 60, 实际 {result['analysis']['max_single_duration']}"
    
    risk = ExamRecordService._calculate_risk_level_v3(
        leave_count=1,
        total_duration_seconds=300,
        max_single_duration=300,
        leave_ratio=10.0,
        leave_frequency=0.5,
        behavior_tags=result['behavior_tags'],
    )
    
    # 单次离开 >= 300秒 → high
    assert risk == 'high', f"预期 high, 实际 {risk}"
    print(f"  风险等级: {risk} ✓")
    print(f"  标签: {result['behavior_tags']} ✓")
    print("  ✅ 测试4通过\n")


def test_5_network_related():
    """测试5: 断网场景 - 断网后页面异常"""
    print("=" * 60)
    print("测试5: 断网场景")
    
    now = 1000000
    monitor_data = {
        'leave_count': 2,
        'total_hidden_duration': 20000,
        'events': [
            # 先断网
            {
                'type': 'network_offline',
                'timestamp': now,
            },
            # 网络断开后10秒离开
            {
                'type': 'exam_leave',
                'timestamp': now + 10000,
                'duration': 10000,
                'tags': ['network_related'],
            },
            {
                'type': 'exam_return',
                'timestamp': now + 20000,
                'duration': 10000,
                'tags': ['network_related'],
            },
            # 又断网后离开
            {
                'type': 'network_offline',
                'timestamp': now + 30000,
            },
            {
                'type': 'exam_leave',
                'timestamp': now + 40000,
                'duration': 10000,
                'tags': ['network_related'],
            },
            {
                'type': 'exam_return',
                'timestamp': now + 50000,
                'duration': 10000,
                'tags': ['network_related'],
            },
        ],
    }
    
    result = ExamRecordService.analyze_monitor_behavior(monitor_data)
    print(f"  behavior_tags: {result['behavior_tags']}")
    print(f"  risk_reason: {result['risk_reason']}")
    
    assert 'network_related' in result['behavior_tags'], \
        f"预期包含 network_related, 实际 {result['behavior_tags']}"
    
    network_related = result['analysis']['network_related_leaves']
    print(f"  network_related_leaves: {network_related}")
    assert network_related == 2, f"预期 network_related_leaves=2, 实际 {network_related}"
    
    # 网络豁免：所有离开都是网络相关
    risk = ExamRecordService._calculate_risk_level_v3(
        leave_count=2,
        total_duration_seconds=20,
        max_single_duration=10,
        leave_ratio=0.5,
        leave_frequency=1.0,
        behavior_tags=result['behavior_tags'],
        network_related_leaves=network_related,
    )
    
    # 所有离开都是网络相关 → normal
    assert risk == 'normal', f"预期 normal（网络豁免）, 实际 {risk}"
    print(f"  风险等级: {risk} ✓")
    print(f"  标签: {result['behavior_tags']} ✓")
    print("  ✅ 测试5通过\n")


def test_6_historical_data():
    """测试6: 历史数据兼容 - 旧数据无analysis字段"""
    print("=" * 60)
    print("测试6: 历史数据兼容")
    
    # 模拟旧格式数据（无 analysis 字段，事件无 tags）
    old_detail_data = json.dumps({
        'events': [
            {'type': 'exam_leave', 'timestamp': 1000000, 'duration': 15000},
            {'type': 'exam_return', 'timestamp': 1015000, 'duration': 15000},
        ],
    })
    
    parsed = json.loads(old_detail_data)
    print(f"  旧数据结构: {list(parsed.keys())}")
    
    # 旧数据没有 analysis 字段
    assert 'analysis' not in parsed, "旧数据不应包含 analysis 字段"
    
    # 验证 analyze_monitor_behavior 处理无标签的事件
    # 注意：duration 15000ms = 15秒，不会触发 rapid_leave_return (<=5s)
    # 也不会触发 long_leave (< 60s)
    monitor_data = {
        'leave_count': 1,
        'total_hidden_duration': 15000,
        'events': parsed['events'],  # 旧事件格式（无 tags）
    }
    
    result = ExamRecordService.analyze_monitor_behavior(monitor_data)
    print(f"  behavior_tags: {result['behavior_tags']}")
    print(f"  risk_reason: {result['risk_reason']}")
    
    # 旧数据中15秒离开不应产生异常标签
    assert result['behavior_tags'] == [], \
        f"旧数据预期空标签, 实际 {result['behavior_tags']}"
    
    # 风险计算正常
    risk = ExamRecordService._calculate_risk_level_v3(
        leave_count=1,
        total_duration_seconds=15,
        max_single_duration=15,
        leave_ratio=0.3,
        leave_frequency=0.5,
        behavior_tags=result['behavior_tags'],
    )
    
    # 15秒离开，单次 < 30秒，次数=1 → low
    assert risk == 'low', f"预期 low, 实际 {risk}"
    print(f"  风险等级: {risk} ✓")
    print(f"  标签: {result['behavior_tags']} ✓")
    print("  ✅ 测试6通过\n")


def test_edge_cases():
    """边界场景测试"""
    print("=" * 60)
    print("边界场景测试")
    
    # 空事件列表
    result = ExamRecordService.analyze_monitor_behavior({'leave_count': 0, 'total_hidden_duration': 0, 'events': []})
    assert result['behavior_tags'] == []
    print("  空事件列表 → 空标签 ✓")
    
    # rapid_trips >= 3 → high
    risk = ExamRecordService._calculate_risk_level_v3(
        leave_count=3,
        total_duration_seconds=9,
        max_single_duration=3,
        leave_ratio=0.2,
        leave_frequency=1.5,
        behavior_tags=['rapid_leave_return'],
        rapid_trips=3,
    )
    assert risk == 'high', f"3次快速往返 → 预期 high, 实际 {risk}"
    print(f"  rapid_trips>=3 → {risk} ✓")
    
    # leave_count > 8 → high
    risk = ExamRecordService._calculate_risk_level_v3(
        leave_count=10,
        total_duration_seconds=100,
        max_single_duration=10,
        leave_ratio=5.0,
        leave_frequency=20.0,
    )
    assert risk == 'high', f"leave_count>8 → 预期 high, 实际 {risk}"
    print(f"  leave_count>8 → {risk} ✓")
    
    # leave_ratio >= 20% → high
    risk = ExamRecordService._calculate_risk_level_v3(
        leave_count=2,
        total_duration_seconds=600,
        max_single_duration=300,
        leave_ratio=25.0,
        leave_frequency=1.0,
    )
    assert risk == 'high', f"leave_ratio>=20% → 预期 high, 实际 {risk}"
    print(f"  leave_ratio>=20% → {risk} ✓")
    
    # 网络豁免 + 部分非网络相关 → 不豁免
    risk = ExamRecordService._calculate_risk_level_v3(
        leave_count=3,
        total_duration_seconds=30,
        max_single_duration=15,
        leave_ratio=1.0,
        leave_frequency=1.5,
        behavior_tags=['frequent_leave'],
        network_related_leaves=2,  # 3次中只有2次网络相关
    )
    assert risk != 'normal', f"部分网络相关 → 不应为 normal, 实际 {risk}"
    print(f"  部分网络相关 → {risk} ✓")
    
    print("  ✅ 边界场景测试通过\n")


def test_data_structure():
    """数据结构测试 - detail_data 格式验证"""
    print("=" * 60)
    print("数据结构测试")
    
    # 验证新格式包含所有必需字段
    monitor_data = {
        'leave_count': 3,
        'total_hidden_duration': 350000,
        'events': [
            {'type': 'exam_leave', 'timestamp': 1000000, 'duration': 350000, 'tags': ['long_leave']},
        ],
        'environment': {'device': {'browser': 'chrome'}},
    }
    
    result = ExamRecordService.analyze_monitor_behavior(monitor_data)
    
    # 检查 analysis 输出结构
    assert 'behavior_tags' in result
    assert 'risk_reason' in result
    assert 'analysis' in result
    assert 'rapid_trips' in result['analysis']
    assert 'max_single_duration' in result['analysis']
    assert 'max_leave_density' in result['analysis']
    assert 'network_related_leaves' in result['analysis']
    
    print(f"  输出结构字段: {list(result.keys())}")
    print(f"  analysis字段: {list(result['analysis'].keys())}")
    print("  ✅ 数据结构测试通过\n")


if __name__ == '__main__':
    print("╔══════════════════════════════════════════════╗")
    print("║  S8.4.2 异常行为检测增强 - 单元测试        ║")
    print("╚══════════════════════════════════════════════╝")
    print()
    
    test_1_normal_exam()
    test_2_rapid_return()
    test_3_frequent_leave()
    test_4_long_leave()
    test_5_network_related()
    test_6_historical_data()
    test_edge_cases()
    test_data_structure()
    
    print("╔══════════════════════════════════════════════╗")
    print("║  所有测试通过 ✅                             ║")
    print("╚══════════════════════════════════════════════╝")