"""
S4.3-A 考试人员管理能力测试
覆盖：添加、查询、删除、重复校验、权限校验
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.db.session import _get_engine, _get_session_factory
from app.db.base import Base

engine = _get_engine()
Base.metadata.create_all(engine)
SessionLocal = _get_session_factory()
from app.models import Exam, User, ExamRecord, ExamParticipant
from app.models.user import User as UserModel
from app.services.exam_service import ExamService
from app.services.participant_service import ExamParticipantService
from app.exceptions import BusinessException, NotFoundException


def _create_test_exam(db, title="测试考试-人员管理"):
    """创建测试考试"""
    service = ExamService(db)
    hr_user = db.query(User).filter(User.role == "hr").first()
    if not hr_user:
        # 创建 HR 用户
        import bcrypt
        hashed = bcrypt.hashpw("testpass123".encode(), bcrypt.gensalt()).decode()
        hr_user = UserModel(
            username="hr_participant_test",
            password_hash=hashed,
            display_name="测试HR",
            role="hr",
            status="active",
        )
        db.add(hr_user)
        db.commit()
        db.refresh(hr_user)

    return service.create_exam(
        title=title,
        duration_minutes=60,
        pass_score=60,
        created_by=hr_user.id,
    )


def test_add_participant():
    """测试添加考试参与人员"""
    print("=" * 60)
    print("测试1: 添加考试参与人员")
    print("=" * 60)

    db = SessionLocal()
    try:
        exam = _create_test_exam(db)
        service = ExamParticipantService(db)

        # 添加人员
        p = service.add_participant(
            exam_id=exam.id,
            candidate_name="张三",
            candidate_phone="13800138000",
            candidate_email="zhangsan@test.com",
        )
        print(f"✓ 添加成功: id={p.id}, name={p.candidate_name}, status={p.status}")

        # 验证默认状态
        assert p.status == "assigned", f"默认状态应为 assigned，实际为 {p.status}"
        print(f"✓ 默认状态正确: {p.status}")

        # 添加无手机号人员
        p2 = service.add_participant(
            exam_id=exam.id,
            candidate_name="李四",
            candidate_email="lisi@test.com",
        )
        print(f"✓ 添加无手机号人员成功: id={p2.id}")

        # 添加无邮箱人员
        p3 = service.add_participant(
            exam_id=exam.id,
            candidate_name="王五",
            candidate_phone="13900139000",
        )
        print(f"✓ 添加无邮箱人员成功: id={p3.id}")

        # 清理
        service.delete(p.id)
        service.delete(p2.id)
        service.delete(p3.id)
        ExamService(db).delete_exam(exam.id, current_user=db.query(User).filter(User.role == "hr").first())
        print("✓ 清理完成")

        print("\n测试1通过 ✓")
        return True

    except Exception as e:
        print(f"\n测试1失败 ✗: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def test_add_participant_validation():
    """测试添加人员校验"""
    print("\n" + "=" * 60)
    print("测试2: 添加人员校验（重复、必填）")
    print("=" * 60)

    db = SessionLocal()
    try:
        exam = _create_test_exam(db)
        service = ExamParticipantService(db)

        # 先添加一个人员
        p1 = service.add_participant(
            exam_id=exam.id,
            candidate_name="测试用户",
            candidate_phone="13700137000",
        )

        # 测试重复添加（相同手机号）
        try:
            service.add_participant(
                exam_id=exam.id,
                candidate_name="另一个名字",
                candidate_phone="13700137000",  # 相同手机号
            )
            print("✗ 错误：应该抛出重复异常")
            return False
        except BusinessException as e:
            print(f"✓ 重复添加被拦截: {str(e)}")

        # 测试空姓名
        try:
            service.add_participant(
                exam_id=exam.id,
                candidate_name="",
                candidate_phone="13600136000",
            )
            print("✗ 错误：应该抛出必填校验异常")
            return False
        except BusinessException as e:
            print(f"✓ 空姓名被拦截: {str(e)}")

        # 测试不存在的考试
        try:
            service.add_participant(
                exam_id=99999,
                candidate_name="测试",
                candidate_phone="13500135000",
            )
            print("✗ 错误：应该抛出考试不存在异常")
            return False
        except NotFoundException as e:
            print(f"✓ 不存在的考试被拦截: {str(e)}")

        # 清理
        service.delete(p1.id)
        ExamService(db).delete_exam(exam.id, current_user=db.query(User).filter(User.role == "hr").first())

        print("\n测试2通过 ✓")
        return True

    except Exception as e:
        print(f"\n测试2失败 ✗: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def test_list_participants():
    """测试查询考试参与人员"""
    print("\n" + "=" * 60)
    print("测试3: 查询考试参与人员")
    print("=" * 60)

    db = SessionLocal()
    try:
        exam = _create_test_exam(db)
        service = ExamParticipantService(db)

        # 添加多个人员
        participants = []
        for i in range(5):
            p = service.add_participant(
                exam_id=exam.id,
                candidate_name=f"考生{i+1}",
                candidate_phone=f"1380013800{i}",
            )
            participants.append(p)

        # 查询列表
        items, total = service.list_participants(exam.id)
        print(f"✓ 查询列表成功: total={total}")
        assert total == 5, f"应该有5个人员，实际有{total}个"

        # 分页查询
        items_page1, total1 = service.list_participants(exam.id, page=1, page_size=2)
        print(f"✓ 分页查询: page1 count={len(items_page1)}, total={total1}")
        assert len(items_page1) == 2
        assert total1 == 5

        # 按状态筛选
        items_assigned, _ = service.list_participants(exam.id, status="assigned")
        print(f"✓ 按状态筛选: assigned count={len(items_assigned)}")
        assert len(items_assigned) == 5

        # 搜索关键词
        items_search, _ = service.list_participants(exam.id, keyword="考生1")
        print(f"✓ 关键词搜索: '考生1' count={len(items_search)}")

        # 获取统计
        count_data = service.get_participant_count(exam.id)
        print(f"✓ 统计信息: total={count_data['total']}, assigned={count_data['assigned']}")

        # 清理
        for p in participants:
            service.delete(p.id)
        ExamService(db).delete_exam(exam.id, current_user=db.query(User).filter(User.role == "hr").first())

        print("\n测试3通过 ✓")
        return True

    except Exception as e:
        print(f"\n测试3失败 ✗: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def test_remove_participant():
    """测试删除参与人员"""
    print("\n" + "=" * 60)
    print("测试4: 删除参与人员")
    print("=" * 60)

    db = SessionLocal()
    try:
        exam = _create_test_exam(db)
        service = ExamParticipantService(db)

        # 添加人员
        p = service.add_participant(
            exam_id=exam.id,
            candidate_name="待删除用户",
            candidate_phone="13100131000",
        )

        # 验证可以删除（无考试记录）
        result = service.remove_participant(p.id)
        print(f"✓ 删除成功: {result}")

        # 验证已删除
        try:
            service.get_participant(p.id)
            print("✗ 错误：应该已被删除")
            return False
        except NotFoundException:
            print("✓ 验证删除：查询已不存在")

        # 再添加一个人员
        p2 = service.add_participant(
            exam_id=exam.id,
            candidate_name="有记录用户",
            candidate_phone="13200132000",
        )

        # 创建考试记录（模拟已参加考试）
        record = ExamRecord(
            exam_id=exam.id,
            candidate_name="有记录用户",
            candidate_phone="13200132000",
            status="not_started",
        )
        db.add(record)
        db.commit()

        # 尝试删除有记录的人员
        try:
            service.remove_participant(p2.id)
            print("✗ 错误：应该禁止删除有考试记录的人员")
            return False
        except BusinessException as e:
            print(f"✓ 有记录人员禁止删除: {str(e)}")

        # 清理
        db.delete(record)
        db.commit()
        service.delete(p2.id)
        ExamService(db).delete_exam(exam.id, current_user=db.query(User).filter(User.role == "hr").first())

        print("\n测试4通过 ✓")
        return True

    except Exception as e:
        print(f"\n测试4失败 ✗: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def test_batch_add_participants():
    """测试批量添加人员"""
    print("\n" + "=" * 60)
    print("测试5: 批量添加考试人员")
    print("=" * 60)

    db = SessionLocal()
    try:
        exam = _create_test_exam(db)
        service = ExamParticipantService(db)

        # 批量添加
        participants = [
            {"candidate_name": "批量用户1", "candidate_phone": "13300133001"},
            {"candidate_name": "批量用户2", "candidate_phone": "13300133002"},
            {"candidate_name": "批量用户3", "candidate_email": "batch3@test.com"},
        ]

        success_count, errors = service.add_participants_batch(exam.id, participants)
        print(f"✓ 批量添加: success={success_count}, errors={errors}")
        assert success_count == 3

        # 验证已添加
        items, total = service.list_participants(exam.id)
        print(f"✓ 验证总数: total={total}")
        assert total == 3

        # 测试重复冲突
        participants_with_duplicate = [
            {"candidate_name": "重复用户", "candidate_phone": "13300133001"},  # 已存在
            {"candidate_name": "新用户", "candidate_phone": "13300133004"},
        ]
        success_count2, errors2 = service.add_participants_batch(exam.id, participants_with_duplicate)
        print(f"✓ 批量添加含重复: success={success_count2}, errors={errors2}")
        assert success_count2 == 1  # 只有新用户添加成功

        # 清理
        items, _ = service.list_participants(exam.id)
        for item in items:
            p = db.query(ExamParticipant).filter(ExamParticipant.id == item["id"]).first()
            if p:
                db.delete(p)
        db.commit()
        ExamService(db).delete_exam(exam.id, current_user=db.query(User).filter(User.role == "hr").first())

        print("\n测试5通过 ✓")
        return True

    except Exception as e:
        print(f"\n测试5失败 ✗: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def test_sync_status():
    """测试同步人员状态"""
    print("\n" + "=" * 60)
    print("测试6: 同步参与人员状态")
    print("=" * 60)

    db = SessionLocal()
    try:
        exam = _create_test_exam(db)
        service = ExamParticipantService(db)

        # 添加人员
        p = service.add_participant(
            exam_id=exam.id,
            candidate_name="同步测试用户",
            candidate_phone="13400134000",
        )
        print(f"✓ 添加人员: status={p.status}")

        # 创建考试记录
        record = ExamRecord(
            exam_id=exam.id,
            candidate_name="同步测试用户",
            candidate_phone="13400134000",
            status="in_progress",
        )
        db.add(record)
        db.commit()
        print(f"✓ 创建考试记录: status={record.status}")

        # 同步状态
        updated_count = service.sync_status_from_exam_record(exam.id)
        print(f"✓ 同步完成: updated_count={updated_count}")
        assert updated_count == 1

        # 验证状态已更新
        db.refresh(p)
        print(f"✓ 验证状态: participant.status={p.status}")
        assert p.status == "in_progress"

        # 清理
        db.delete(record)
        db.commit()
        service.delete(p.id)
        ExamService(db).delete_exam(exam.id, current_user=db.query(User).filter(User.role == "hr").first())

        print("\n测试6通过 ✓")
        return True

    except Exception as e:
        print(f"\n测试6失败 ✗: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def test_permission_check():
    """测试权限校验"""
    print("\n" + "=" * 60)
    print("测试7: 权限校验")
    print("=" * 60)

    db = SessionLocal()
    try:
        # 验证 HR/Admin 角色才能操作
        # 检查 require_hr_or_admin 逻辑
        from app.core.permissions import _normalize_role
        from app.models.user import User

        # 测试角色标准化
        assert _normalize_role("hr") == "hr"
        assert _normalize_role("admin") == "admin"
        assert _normalize_role("candidate") == "employee"
        assert _normalize_role("employee") == "employee"
        print(f"✓ 角色标准化正确")

        # 验证权限校验函数存在
        from app.core.permissions import require_hr_or_admin, require_admin, require_authenticated
        print(f"✓ 权限校验函数存在")

        # 验证业务逻辑隔离
        service = ExamParticipantService(db)
        exam = _create_test_exam(db)

        # 添加人员
        p = service.add_participant(
            exam_id=exam.id,
            candidate_name="权限测试用户",
            candidate_phone="13000130000",
        )

        # 验证所有参与者通过 Service 层操作
        items, total = service.list_participants(exam.id)
        print(f"✓ 通过Service层查询: total={total}")
        assert total == 1

        # 清理
        service.delete(p.id)
        ExamService(db).delete_exam(exam.id, current_user=db.query(User).filter(User.role == "hr").first())

        print("\n测试7通过 ✓")
        return True

    except Exception as e:
        print(f"\n测试7失败 ✗: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def test_no_impact_on_exam_flow():
    """验证不会影响已有考试流程"""
    print("\n" + "=" * 60)
    print("测试8: 验证不影响已有考试流程")
    print("=" * 60)

    db = SessionLocal()
    try:
        # 创建考试
        exam = _create_test_exam(db)
        exam_service = ExamService(db)
        participant_service = ExamParticipantService(db)

        # 添加参与人员
        p = participant_service.add_participant(
            exam_id=exam.id,
            candidate_name="流程测试用户",
            candidate_phone="13111131111",
        )
        print(f"✓ 添加参与人员: id={p.id}")

        # 验证考试基本功能不受影响
        exam_detail = exam_service.get(exam.id)
        assert exam_detail is not None
        print(f"✓ 考试详情可正常查询")

        # 验证考试列表不受影响
        items, total = exam_service.list_exams(
            current_user=db.query(User).filter(User.role == "hr").first()
        )
        print(f"✓ 考试列表可正常查询: total={total}")
        assert total > 0

        # 验证参与人员独立于考试记录
        items_p, total_p = participant_service.list_participants(exam.id)
        print(f"✓ 参与人员独立查询: total={total_p}")
        assert total_p == 1

        # 清理
        participant_service.delete(p.id)
        exam_service.delete_exam(exam.id, current_user=db.query(User).filter(User.role == "hr").first())

        print("\n测试8通过 ✓")
        return True

    except Exception as e:
        print(f"\n测试8失败 ✗: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def main():
    """运行所有测试"""
    print("\n" + "=" * 70)
    print("S4.3-A 考试人员管理能力 - 测试套件")
    print("=" * 70)

    results = {
        "添加考试人员": test_add_participant(),
        "添加人员校验": test_add_participant_validation(),
        "查询考试人员": test_list_participants(),
        "删除考试人员": test_remove_participant(),
        "批量添加人员": test_batch_add_participants(),
        "同步人员状态": test_sync_status(),
        "权限校验": test_permission_check(),
        "不影响已有流程": test_no_impact_on_exam_flow(),
    }

    print("\n" + "=" * 70)
    print("测试结果汇总")
    print("=" * 70)

    passed = 0
    failed = 0
    for name, result in results.items():
        status = "通过 ✓" if result else "失败 ✗"
        print(f"  {name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1

    print(f"\n总计: {passed} 通过, {failed} 失败")

    if failed == 0:
        print("\n所有测试通过! ✓")
        return 0
    else:
        print(f"\n有 {failed} 个测试失败! ✗")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
