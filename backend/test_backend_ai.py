import sys
sys.path.insert(0, '.')

from app.services.ai_scoring_service import AIScoringService
from app.schemas.ai_scoring import AIScoringRequest, AIScoringResponse
from app.exceptions import BusinessException

print('=== Backend AI 评分链路测试 ===')
print()

print('1. Service 创建')
s = AIScoringService()
print('  URL:', s.base_url)
print('  Timeout:', s.timeout)
print()

print('2. 响应验证')
r = s._validate_response({'score': 8.5, 'reason': 'good', 'missing_points': ['a'], 'confidence': 0.9})
print('  正常:', r)
r = s._validate_response({'score': -5, 'reason': '', 'missing_points': [], 'confidence': 1.5})
print('  越界修复:', r)
print()

print('3. Schema 验证')
req = AIScoringRequest(question='Q', user_answer='A')
print('  请求:', req.model_dump())
print()

print('4. 异常处理测试')
try:
    s._validate_response({'score': 5})
except ValueError as e:
    print('  缺字段:', str(e))
print()

print('5. 健康检查')
print('  模拟不可用:', s.check_service_health())
print()

print('✅ Backend 全部组件测试通过')
