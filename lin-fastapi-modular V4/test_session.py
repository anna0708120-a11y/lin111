"""
测试多聊天室功能
运行方式：python3 test_session.py
"""
import sys
sys.path.insert(0, '.')

from app import session

def test_session_creation():
    """测试创建聊天室"""
    print("1. 测试创建新聊天室...")
    new_session = session.create_new_session()
    print(f"   ✓ 创建成功: {new_session['id']}")
    print(f"   标题: {new_session['title']}")
    return new_session['id']

def test_session_list():
    """测试获取聊天室列表"""
    print("\n2. 测试获取聊天室列表...")
    sessions = session.get_session_list()
    print(f"   ✓ 找到 {len(sessions)} 个聊天室")
    for s in sessions:
        print(f"   - {s['title']} ({s['id'][:16]}...)")
    return sessions

def test_update_title(session_id):
    """测试更新标题"""
    print(f"\n3. 测试更新聊天室标题...")
    new_title = "测试聊天室"
    session.update_session_title(session_id, new_title)
    print(f"   ✓ 标题已更新为: {new_title}")

def test_update_activity(session_id):
    """测试更新活跃时间"""
    print(f"\n4. 测试更新活跃时间...")
    session.update_session_activity(session_id)
    print(f"   ✓ 活跃时间已更新")

def test_delete_session(session_id):
    """测试删除聊天室"""
    print(f"\n5. 测试删除聊天室...")
    session.delete_session(session_id)
    print(f"   ✓ 聊天室已删除")

def main():
    print("=" * 50)
    print("多聊天室功能测试")
    print("=" * 50)
    
    try:
        # 1. 创建新聊天室
        session_id = test_session_creation()
        
        # 2. 获取列表
        sessions = test_session_list()
        
        # 3. 更新标题
        test_update_title(session_id)
        
        # 4. 更新活跃时间
        test_update_activity(session_id)
        
        # 5. 删除聊天室
        test_delete_session(session_id)
        
        print("\n" + "=" * 50)
        print("✓ 所有测试通过！")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
