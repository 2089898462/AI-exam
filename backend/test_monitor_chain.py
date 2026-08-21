"""
端到端监考数据链路测试
模拟用户提交考试，验证监考数据是否正确保存和读取
"""
import requests
import json
import sys

BASE_URL = 'http://localhost:8000/api/v1'

def test_monitor_data_chain():
    """测试监考数据链路"""
    print('=' * 80)
    print('监考数据链路测试')
    print('=' * 80)
    
    # 1. 检查后端服务是否运行
    print('\n1. 检查后端服务...')
    try:
        resp = requests.get(f'{BASE_URL}/health')
        if resp.status_code == 200:
            print('   ✅ 后端服务正常运行')
        else:
            print(f'   ❌ 后端服务异常: {resp.status_code}')
            return False
    except requests.exceptions.ConnectionError:
        print('   ❌ 后端服务未启动')
        return False
    
    # 2. 创建一个考试记录（候选人进入考试）
    print('\n2. 创建考试记录...')
    try:
        resp = requests.post(f'{BASE_URL}/exam-records', json={
            'exam_id': 1,
            'candidate_name': '测试考生',
            'candidate_phone': '13800000000',
            'candidate_email': 'test@test.com',
        })
        if resp.status_code == 201:
            record_data = resp.json()['data']
            record_id = record_data['id']
            print(f'   ✅ 考试记录创建成功: ID={record_id}, Status={record_data["status"]}')
        else:
            print(f'   ❌ 创建失败: {resp.status_code} - {resp.text}')
            return False
    except Exception as e:
        print(f'   ❌ 请求异常: {e}')
        return False
    
    # 3. 获取试卷
    print('\n3. 获取试卷...')
    try:
        resp = requests.get(f'{BASE_URL}/exam-records/{record_id}/paper')
        if resp.status_code == 200:
            paper_data = resp.json()['data']
            print(f'   ✅ 试卷获取成功: {len(paper_data.get("questions", []))}道题')
        else:
            print(f'   ❌ 获取失败: {resp.status_code}')
            return False
    except Exception as e:
        print(f'   ❌ 请求异常: {e}')
        return False
    
    # 4. 开始考试
    print('\n4. 开始考试...')
    try:
        resp = requests.post(f'{BASE_URL}/exam-records/{record_id}/start')
        if resp.status_code == 200:
            start_data = resp.json()['data']
            print(f'   ✅ 考试开始成功: Status={start_data["status"]}')
        else:
            print(f'   ❌ 开始失败: {resp.status_code}')
            return False
    except Exception as e:
        print(f'   ❌ 请求异常: {e}')
        return False
    
    # 5. 模拟交卷（包含监考数据）
    print('\n5. 提交考试（包含监考数据）...')
    
    # 模拟 S8.4 格式的监考数据
    monitor_data = {
        'leave_count': 3,
        'total_hidden_duration': 30000,  # 30秒
        'events': [
            {'type': 'exam_leave', 'timestamp': 1713700000000, 'tags': []},
            {'type': 'exam_return', 'timestamp': 1713700005000, 'duration': 5000, 'tags': ['rapid_leave_return']},
            {'type': 'exam_leave', 'timestamp': 1713700010000, 'tags': []},
            {'type': 'exam_return', 'timestamp': 1713700030000, 'duration': 20000, 'tags': []},
            {'type': 'exam_leave', 'timestamp': 1713700040000, 'tags': ['frequent_leave']},
            {'type': 'exam_return', 'timestamp': 1713700055000, 'duration': 15000, 'tags': []},
        ],
        'environment': {
            'device': {
                'userAgent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)',
                'platform': 'ios',
                'isMobile': True,
                'browser': 'safari',
            },
            'screen': {
                'width': 375,
                'height': 812,
                'orientation': 'portrait',
            },
            'browser': {
                'viewportWidth': 375,
                'viewportHeight': 812,
                'pixelRatio': 3,
            },
            'collectedAt': 1713700000000,
        },
    }
    
    try:
        resp = requests.post(
            f'{BASE_URL}/exam-records/{record_id}/submit',
            json={'monitor_data': monitor_data}
        )
        if resp.status_code == 200:
            submit_data = resp.json()['data']
            print(f'   ✅ 提交成功: Status={submit_data["status"]}')
        else:
            print(f'   ❌ 提交失败: {resp.status_code} - {resp.text}')
            return False
    except Exception as e:
        print(f'   ❌ 请求异常: {e}')
        return False
    
    # 6. 检查监考数据是否保存到数据库
    print('\n6. 检查数据库中的监考数据...')
    import sqlite3
    conn = sqlite3.connect('exam_system.db')
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id, exam_record_id, leave_count, total_duration, risk_level, detail_data '
        'FROM exam_monitor_summary WHERE exam_record_id = ?',
        (record_id,)
    )
    row = cursor.fetchone()
    if row:
        print(f'   ✅ 监考记录存在: ID={row[0]}, LeaveCount={row[2]}, Duration={row[3]}s, Risk={row[4]}')
        if row[5]:
            try:
                detail = json.loads(row[5])
                events_count = len(detail.get('events', []))
                has_env = 'environment' in detail
                has_analysis = 'analysis' in detail
                print(f'      Events: {events_count}条, HasEnvironment: {has_env}, HasAnalysis: {has_analysis}')
            except:
                print(f'      JSON解析失败')
    else:
        print(f'   ❌ 监考记录不存在！')
        conn.close()
        return False
    conn.close()
    
    # 7. HR 端登录获取 token
    print('\n7. HR 端登录获取 token...')
    try:
        resp = requests.post(f'{BASE_URL}/auth/login', json={
            'username': 'admin',
            'password': 'admin123',  # 假设默认密码
        })
        if resp.status_code == 200:
            token_data = resp.json()
            token = token_data.get('data', {}).get('access_token', '')
            if token:
                print(f'   ✅ 登录成功，获取 token')
            else:
                print(f'   ❌ Token 获取失败: {token_data}')
                token = None
        else:
            print(f'   ❌ 登录失败: {resp.status_code} - {resp.text}')
            token = None
    except Exception as e:
        print(f'   ❌ 请求异常: {e}')
        token = None
    
    # 8. HR 端查看成绩详情（验证监考数据是否正确返回）
    if token:
        print('\n8. HR 端查看成绩详情...')
        try:
            resp = requests.get(
                f'{BASE_URL}/grading/results/{record_id}',
                headers={'Authorization': f'Bearer {token}'}
            )
            if resp.status_code == 200:
                detail_data = resp.json()['data']
                monitor_data = detail_data.get('monitor_data', {})
                monitor_analysis = detail_data.get('monitor_analysis', {})
                
                print(f'   ✅ 详情获取成功')
                print(f'      monitor_data.has_monitor_data: {monitor_data.get("has_monitor_data")}')
                print(f'      monitor_data.leave_count: {monitor_data.get("leave_count")}')
                print(f'      monitor_data.total_duration: {monitor_data.get("total_duration")}')
                print(f'      monitor_data.events 数量: {len(monitor_data.get("events", []))}')
                print(f'      monitor_analysis.has_analysis: {monitor_analysis.get("has_analysis")}')
                print(f'      monitor_analysis.behavior_tags: {monitor_analysis.get("behavior_tags", [])}')
                
                if monitor_data.get('has_monitor_data'):
                    print(f'\n   ✅ 监考数据完整返回！')
                else:
                    print(f'\n   ❌ 监考数据缺失！')
                    return False
            else:
                print(f'   ❌ 获取失败: {resp.status_code} - {resp.text}')
                return False
        except Exception as e:
            print(f'   ❌ 请求异常: {e}')
            return False
    
    print('\n' + '=' * 80)
    print('✅ 测试完成！监考数据链路正常！')
    print('=' * 80)
    return True

if __name__ == '__main__':
    success = test_monitor_data_chain()
    sys.exit(0 if success else 1)
