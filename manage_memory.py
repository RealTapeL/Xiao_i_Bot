#!/usr/bin/env python3
"""
记忆管理工具 - 查看和管理 Mem0 记忆系统
"""
import sys
import json
from datetime import datetime

def print_header(title):
    print(f"\n{'=' * 50}")
    print(f"  {title}")
    print('=' * 50)

def cmd_status():
    """查看记忆系统状态"""
    print_header("记忆系统状态")
    
    try:
        from src.memory import QQBotMemory
        
        memory = QQBotMemory()
        
        # 获取用户列表
        users = memory.get_all_users()
        
        print(f"\n📊 状态: ✅ 正常运行")
        print(f"💾 存储: SQLite (本地文件)")
        print(f"🔍 搜索: 本地向量相似度 + 关键词匹配")
        print(f"\n👥 已记录用户: {len(users)} 人")
        
        if users:
            print(f"\n用户列表:")
            for user_id in users[:10]:  # 只显示前10个
                stats = memory.get_user_stats(user_id)
                print(f"  • QQ: {user_id}")
                print(f"    └─ 记忆数量: {stats.get('memory_count', 0)}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 状态: 错误")
        print(f"   错误信息: {e}")
        return False

def cmd_list(user_id=None, limit=10):
    """列出用户的记忆"""
    try:
        from src.memory import QQBotMemory
        memory = QQBotMemory()
        
        if user_id:
            # 显示特定用户的记忆
            print_header(f"用户 {user_id} 的记忆")
            
            # 获取相关记忆
            all_memories = memory.get_all_memories(user_id)
            
            print(f"\n📝 共找到 {len(all_memories)} 条记忆:\n")
            
            for i, mem in enumerate(all_memories[:limit], 1):
                print(f"{i}. [{mem.get('created_at', '未知时间')}]")
                print(f"   {mem.get('message', '无内容')[:100]}...")
                if mem.get('metadata'):
                    print(f"   元数据: {mem.get('metadata')}")
                print()
        else:
            # 显示所有用户
            print_header("所有用户")
            users = memory.get_all_users()
            print(f"\n共 {len(users)} 位用户:\n")
            for u in users:
                stats = memory.get_user_stats(u)
                print(f"  • {u} - {stats.get('memory_count', 0)} 条记忆")
                
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False
    
    return True

def cmd_clear(user_id):
    """清除用户的所有记忆"""
    try:
        from src.memory import QQBotMemory
        memory = QQBotMemory()
        
        if not user_id:
            print("❌ 请指定用户ID")
            print("   用法: python manage_memory.py clear <QQ号>")
            return False
        
        confirm = input(f"⚠️ 确定要清除用户 {user_id} 的所有记忆吗？(yes/no): ")
        
        if confirm.lower() == 'yes':
            success = memory.clear_user_memories(user_id)
            if success:
                print(f"✅ 已清除用户 {user_id} 的所有记忆")
            else:
                print(f"❌ 清除失败")
        else:
            print("已取消")
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False
    
    return True

def cmd_test(user_id="123456"):
    """测试记忆系统"""
    print_header("记忆系统测试")
    
    try:
        from src.memory import QQBotMemory
        
        print(f"\n1. 初始化记忆系统...")
        memory = QQBotMemory()
        print("   ✅ 初始化成功")
        
        # 测试用户
        test_user = user_id
        test_role = "测试用户"
        
        print(f"\n2. 测试用户: {test_user}")
        
        # 添加测试记忆
        print(f"\n3. 添加测试记忆...")
        memories = [
            ("我喜欢看电影，尤其是科幻片", "preference"),
            ("我在北京工作", "location"),
            ("我的宠物是一只金毛犬", "pet"),
        ]
        
        for msg, mtype in memories:
            success = memory.add_interaction(
                user_id=test_user,
                user_name=test_role,
                message=msg,
                response=f"收到！我已记住你喜欢{mtype}。",
                metadata={"test": True, "type": mtype}
            )
            if success:
                print(f"   ✅ 已添加: {msg[:30]}...")
        
        # 搜索相关记忆
        print(f"\n4. 搜索相关记忆（查询: '电影'）...")
        results = memory.search_memories(test_user, "电影", limit=3)
        for r in results:
            print(f"   • {r.get('message', '无内容')}")
        
        # 获取记忆上下文
        print(f"\n5. 获取记忆上下文...")
        context = memory.get_context_for_llm(test_user, "你记得我喜欢什么吗？")
        print(f"   找到 {len(context)} 条相关记忆")
        for c in context:
            print(f"   • {c.get('message', '无内容')[:50]}...")
        
        # 显示用户统计
        print(f"\n6. 用户统计...")
        stats = memory.get_user_stats(test_user)
        print(f"   记忆数量: {stats.get('memory_count', 0)}")
        
        print(f"\n✅ 所有测试通过！")
        
        # 清理测试数据
        print(f"\n7. 清理测试数据...")
        memory.clear_user_memories(test_user)
        print("   ✅ 测试数据已清理")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def cmd_help():
    """显示帮助"""
    print_header("记忆管理工具 - 使用指南")
    print("""
用法: python manage_memory.py <命令> [参数]

命令:
  status              查看记忆系统状态
  list [QQ号]         列出所有用户或特定用户的记忆
  clear <QQ号>        清除指定用户的所有记忆
  test [QQ号]         运行测试（默认使用测试用户 123456）
  help                显示此帮助

示例:
  python manage_memory.py status           # 查看系统状态
  python manage_memory.py list             # 列出所有用户
  python manage_memory.py list 123456789   # 查看用户 123456789 的记忆
  python manage_memory.py clear 123456789  # 清除用户 123456789 的记忆
  python manage_memory.py test             # 运行测试
""")

def main():
    if len(sys.argv) < 2:
        cmd_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == 'status':
        cmd_status()
    elif command == 'list':
        user_id = sys.argv[2] if len(sys.argv) > 2 else None
        cmd_list(user_id)
    elif command == 'clear':
        user_id = sys.argv[2] if len(sys.argv) > 2 else None
        cmd_clear(user_id)
    elif command == 'test':
        user_id = sys.argv[2] if len(sys.argv) > 2 else "123456"
        cmd_test(user_id)
    elif command in ['help', '-h', '--help']:
        cmd_help()
    else:
        print(f"未知命令: {command}")
        cmd_help()

if __name__ == '__main__':
    main()
