"""
S4.2 固定试卷模板体系测试
测试模板CRUD、基于模板创建考试、数据隔离等核心功能
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.db.session import engine, SessionLocal
from app.models import ExamTemplate, TemplateQuestion, Exam, Question
from app.services.template_service import TemplateService
from app.exceptions import BusinessError


def test_template_crud():
    """测试模板 CRUD 操作"""
    print("=" * 60)
    print("测试1: 模板CRUD操作")
    print("=" * 60)

    db = SessionLocal()
    service = TemplateService(db)

    try:
        # 创建模板
        template_data = {
            "name": "测试模板-CRUD测试",
            "description": "用于CRUD测试的模板",
            "status": "active",
        }
        template = service.create_template(
            template_data=template_data,
            current_user_id=1
        )
        print(f"✓ 创建模板成功: id={template.id}, name={template.name}")

        # 查询模板列表
        templates, total = service.list_templates()
        print(f"✓ 查询模板列表成功: 共{total}个模板")

        # 查询模板详情
        detail = service.get_template(template.id)
        print(f"✓ 查询模板详情成功: {detail.name}")

        # 更新模板
        updated = service.update_template(
            template_id=template.id,
            template_data={"name": "测试模板-CRUD-已更新"},
            current_user_id=1
        )
        print(f"✓ 更新模板成功: name={updated.name}")

        # 停用模板
        deactivated = service.deactivate_template(template.id, current_user_id=1)
        print(f"✓ 停用模板成功: status={deactivated.status}")

        # 重新启用
        activated = service.activate_template(template.id, current_user_id=1)
        print(f"✓ 启用模板成功: status={activated.status}")

        # 删除模板
        service.delete_template(template.id, current_user_id=1)
        print(f"✓ 删除模板成功")

        # 验证删除
        try:
            service.get_template(template.id)
            print("✗ 错误: 模板应该已被删除")
            return False
        except BusinessError as e:
            print(f"✓ 验证删除成功: {str(e)}")

        print("\n测试1通过 ✓")
        return True

    except Exception as e:
        print(f"\n测试1失败 ✗: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def test_template_questions():
    """测试模板题目管理"""
    print("\n" + "=" * 60)
    print("测试2: 模板题目管理")
    print("=" * 60)

    db = SessionLocal()
    service = TemplateService(db)

    try:
        # 创建模板
        template = service.create_template(
            template_data={"name": "测试模板-题目管理", "description": "题目管理测试"},
            current_user_id=1
        )
        print(f"✓ 创建模板: id={template.id}")

        # 添加单选题
        single_q = service.add_question(
            template_id=template.id,
            question_data={
                "question_no": "1",
                "type": "single_choice",
                "content": "以下哪个是Python的解释器？",
                "options": ["CPython", "PyPy", "Jython", "IronPython"],
                "answer": "A",
                "score": 10,
            },
            current_user_id=1
        )
        print(f"✓ 添加单选题: id={single_q.id}, score={single_q.score}")

        # 添加多选题
        multiple_q = service.add_question(
            template_id=template.id,
            question_data={
                "question_no": "2",
                "type": "multiple_choice",
                "content": "以下哪些是前端框架？",
                "options": ["React", "Vue", "Angular", "Django"],
                "answer": "A,B,C",
                "score": 15,
            },
            current_user_id=1
        )
        print(f"✓ 添加多选题: id={multiple_q.id}")

        # 添加判断题
        true_false_q = service.add_question(
            template_id=template.id,
            question_data={
                "question_no": "3",
                "type": "true_false",
                "content": "Python是一种动态类型语言。",
                "options": [],
                "answer": "true",
                "score": 5,
            },
            current_user_id=1
        )
        print(f"✓ 添加判断题: id={true_false_q.id}")

        # 添加简答题
        short_answer_q = service.add_question(
            template_id=template.id,
            question_data={
                "question_no": "4",
                "type": "short_answer",
                "content": "请简述什么是面向对象编程。",
                "options": [],
                "answer": "面向对象编程是一种编程范式...",
                "score": 20,
            },
            current_user_id=1
        )
        print(f"✓ 添加简答题: id={short_answer_q.id}")

        # 查询题目列表
        questions = service.list_questions(template.id)
        print(f"✓ 查询题目列表: 共{len(questions)}道题")

        # 更新题目
        updated_q = service.update_question(
            template_id=template.id,
            question_id=single_q.id,
            question_data={"content": "以下哪个是CPython？", "score": 12},
            current_user_id=1
        )
        print(f"✓ 更新题目: score={updated_q.score}")

        # 按条件查询题目
        filtered = service.list_questions(template.id, question_type="single_choice")
        print(f"✓ 按类型查询: 共{len(filtered)}道单选题")

        # 删除题目
        service.delete_question(template.id, short_answer_q.id, current_user_id=1)
        remaining = service.list_questions(template.id)
        print(f"✓ 删除题目: 剩余{len(remaining)}道题")

        # 获取总分
        total_score = service.get_template_total_score(template.id)
        print(f"✓ 模板总分: {total_score}分")

        # 清理
        service.delete_template(template.id, current_user_id=1)
        print("✓ 清理完成")

        print("\n测试2通过 ✓")
        return True

    except Exception as e:
        print(f"\n测试2失败 ✗: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def test_create_exam_from_template():
    """测试基于模板创建考试"""
    print("\n" + "=" * 60)
    print("测试3: 基于模板创建考试")
    print("=" * 60)

    db = SessionLocal()
    service = TemplateService(db)

    try:
        # 创建模板
        template = service.create_template(
            template_data={
                "name": "测试模板-创建考试",
                "description": "用于测试创建考试的模板",
            },
            current_user_id=1
        )
        print(f"✓ 创建模板: id={template.id}")

        # 添加题目
        for i in range(3):
            service.add_question(
                template_id=template.id,
                question_data={
                    "question_no": str(i + 1),
                    "type": "single_choice",
                    "content": f"测试题目 {i + 1}",
                    "options": ["选项A", "选项B", "选项C", "选项D"],
                    "answer": "A",
                    "score": 10,
                },
                current_user_id=1
            )

        template_questions = service.list_questions(template.id)
        print(f"✓ 模板共{len(template_questions)}道题")

        # 基于模板创建考试
        exam_data = {
            "title": "考试-来自模板测试",
            "exam_code": "T" + str(template.id),
            "position": "测试岗位",
            "duration_minutes": 90,
            "pass_score": 60,
        }
        result = service.create_exam_from_template(
            template_id=template.id,
            exam_data=exam_data,
            current_user_id=1
        )
        print(f"✓ 创建考试: exam_id={result['exam_id']}, total_score={result['total_score']}")

        # 验证考试独立存在
        exam = db.query(Exam).filter(Exam.id == result["exam_id"]).first()
        assert exam is not None, "考试应该存在"
        assert exam.title == "考试-来自模板测试"
        print(f"✓ 验证考试: title={exam.title}")

        # 考试题目数量
        question_count = db.query(Question).filter(Question.exam_id == exam.id).count()
        print(f"✓ 考试题数: {question_count}")

        # 修改模板不影响已创建的考试
        service.update_template(
            template_id=template.id,
            template_data={"name": "模板-已修改"},
            current_user_id=1
        )
        print("✓ 模板已修改")

        # 验证考试不受影响
        exam2 = db.query(Exam).filter(Exam.id == result["exam_id"]).first()
        assert exam2.title == "考试-来自模板测试", "考试标题不应改变"
        print(f"✓ 验证隔离: 考试标题仍为'{exam2.title}'")

        # 清理
        db.delete(exam)
        db.commit()
        service.delete_template(template.id, current_user_id=1)
        print("✓ 清理完成")

        print("\n测试3通过 ✓")
        return True

    except Exception as e:
        print(f"\n测试3失败 ✗: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def test_data_isolation():
    """测试数据隔离 - 修改模板后历史考试数据不变"""
    print("\n" + "=" * 60)
    print("测试4: 数据隔离测试")
    print("=" * 60)

    db = SessionLocal()
    service = TemplateService(db)

    try:
        # 创建模板并添加题目
        template = service.create_template(
            template_data={"name": "隔离测试模板", "description": "数据隔离测试"},
            current_user_id=1
        )
        print(f"✓ 创建模板: id={template.id}")

        # 添加题目
        q = service.add_question(
            template_id=template.id,
            question_data={
                "question_no": "1",
                "type": "single_choice",
                "content": "原始题目内容",
                "options": ["原始选项A", "原始选项B", "原始选项C", "原始选项D"],
                "answer": "A",
                "score": 10,
            },
            current_user_id=1
        )
        original_content = q.content
        original_score = q.score
        print(f"✓ 添加题目: content='{original_content}', score={original_score}")

        # 基于模板创建考试
        result = service.create_exam_from_template(
            template_id=template.id,
            exam_data={"title": "隔离测试考试", "duration_minutes": 60},
            current_user_id=1
        )
        exam_id = result["exam_id"]
        print(f"✓ 创建考试: id={exam_id}")

        # 获取考试题目的快照
        exam_question = db.query(Question).filter(
            Question.exam_id == exam_id,
            Question.question_no == "1"
        ).first()
        assert exam_question is not None
        snapshot_content = exam_question.content
        snapshot_score = exam_question.score
        print(f"✓ 考试快照: content='{snapshot_content}', score={snapshot_score}")

        # 修改模板题目
        service.update_question(
            template_id=template.id,
            question_id=q.id,
            question_data={
                "content": "修改后的题目内容",
                "options": ["修改选项A", "修改选项B", "修改选项C", "修改选项D"],
                "answer": "B",
                "score": 20,
            },
            current_user_id=1
        )
        print("✓ 修改模板题目")

        # 验证模板题目已修改
        updated_q = service.get_question(template.id, q.id)
        assert updated_q.content == "修改后的题目内容"
        assert updated_q.score == 20
        print(f"✓ 验证模板题目已更新: score={updated_q.score}")

        # 验证考试题目的快照未改变
        exam_question_after = db.query(Question).filter(
            Question.exam_id == exam_id,
            Question.question_no == "1"
        ).first()
        assert exam_question_after.content == snapshot_content
        assert exam_question_after.score == snapshot_score
        print(f"✓ 验证数据隔离: 考试题score仍为{exam_question_after.score}")

        # 模板添加新题目不影响考试
        service.add_question(
            template_id=template.id,
            question_data={
                "question_no": "2",
                "type": "single_choice",
                "content": "新增题目",
                "options": ["A", "B", "C", "D"],
                "answer": "A",
                "score": 5,
            },
            current_user_id=1
        )
        exam_question_count = db.query(Question).filter(Question.exam_id == exam_id).count()
        template_question_count = len(service.list_questions(template.id))
        print(f"✓ 模板题目数={template_question_count}, 考试题数={exam_question_count}")
        assert template_question_count == 2, "模板应该有2道题"
        assert exam_question_count == 1, "考试应该只有1道题"

        # 清理
        db.query(Question).filter(Question.exam_id == exam_id).delete()
        db.query(Exam).filter(Exam.id == exam_id).delete()
        db.commit()
        service.delete_template(template.id, current_user_id=1)
        print("✓ 清理完成")

        print("\n测试4通过 ✓")
        return True

    except Exception as e:
        print(f"\n测试4失败 ✗: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def main():
    """运行所有测试"""
    print("\n" + "=" * 70)
    print("S4.2 固定试卷模板体系 - 测试套件")
    print("=" * 70)

    results = {
        "模板CRUD": test_template_crud(),
        "模板题目管理": test_template_questions(),
        "基于模板创建考试": test_create_exam_from_template(),
        "数据隔离": test_data_isolation(),
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
