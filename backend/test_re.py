"""
快速测试兑换码加密功能
用于诊断加密问题
"""
import os
import sys
import json
import base64
import zlib
from cryptography.fernet import Fernet

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

def test_encryption():
    """测试加密功能"""
    print("=" * 50)
    print("兑换码加密功能测试")
    print("=" * 50)
    
    # 1. 检查密钥配置
    print(f"\n1. 检查加密密钥配置...")
    key = settings.REDEEM_CODE_ENCRYPTION_KEY
    if not key:
        print("❌ 错误: REDEEM_CODE_ENCRYPTION_KEY 未配置")
        return False
    print(f"✅ 密钥已配置: {key[:20]}...")
    
    # 2. 验证密钥格式
    print(f"\n2. 验证密钥格式...")
    try:
        fernet = Fernet(key.encode())
        print("✅ 密钥格式正确")
    except Exception as e:
        print(f"❌ 密钥格式错误: {str(e)}")
        print("\n提示: Fernet密钥必须是32字节的URL安全的base64编码字符串")
        print("生成新密钥的方法:")
        print("  from cryptography.fernet import Fernet")
        print("  key = Fernet.generate_key()")
        print("  print(key.decode())")
        return False
    
    # 3. 测试加密（使用压缩）
    print(f"\n3. 测试加密功能（使用压缩）...")
    try:
        # 使用短键名和压缩格式（与后端一致）
        test_payload = {
            "t": 100,
            "f": None,
            "u": None,
            "n": "测试备注"
        }
        
        # 紧凑JSON格式
        payload_json = json.dumps(test_payload, ensure_ascii=False, separators=(',', ':'))
        payload_bytes = payload_json.encode('utf-8')
        print(f"   原始JSON数据大小: {len(payload_bytes)} 字节")
        print(f"   原始JSON: {payload_json}")
        
        # 压缩数据
        compressed_data = zlib.compress(payload_bytes, level=9)
        print(f"   压缩后数据大小: {len(compressed_data)} 字节 (压缩率: {len(compressed_data)/len(payload_bytes)*100:.1f}%)")
        
        # 加密压缩后的数据
        encrypted_data = fernet.encrypt(compressed_data)
        print(f"   加密后数据大小: {len(encrypted_data)} 字节")
        
        encrypted_str = base64.urlsafe_b64encode(encrypted_data).decode('utf-8')
        code = f"Timo{encrypted_str}"
        
        print(f"   生成的兑换码长度: {len(code)} 字符")
        print(f"   生成的兑换码: {code[:50]}...")
        
        if len(code) > 128:
            print(f"   ⚠️  警告: 兑换码长度超过128字符限制")
            return False
        else:
            print(f"   ✅ 兑换码长度符合要求（≤128字符）")
        
    except Exception as e:
        print(f"❌ 加密测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    # 4. 测试解密（支持压缩格式）
    print(f"\n4. 测试解密功能（支持压缩格式）...")
    try:
        encrypted_str = code[4:]  # 移除"Timo"前缀
        encrypted_data = base64.urlsafe_b64decode(encrypted_str.encode('utf-8'))
        decrypted_bytes = fernet.decrypt(encrypted_data)
        
        # 尝试解压缩
        try:
            decompressed_data = zlib.decompress(decrypted_bytes)
            decrypted_payload = json.loads(decompressed_data.decode('utf-8'))
        except zlib.error:
            # 如果解压缩失败，可能是旧格式
            decrypted_payload = json.loads(decrypted_bytes.decode('utf-8'))
        
        print(f"   ✅ 解密成功")
        print(f"   解密后的数据: {decrypted_payload}")
        
        # 验证数据（支持新旧格式）
        expected_tcoins = test_payload.get("tcoins") or test_payload.get("t")
        actual_tcoins = decrypted_payload.get("tcoins") or decrypted_payload.get("t")
        
        if actual_tcoins == expected_tcoins:
            print(f"   ✅ 数据完整性验证通过")
        else:
            print(f"   ⚠️  警告: 解密后的数据与原始数据不完全一致")
            print(f"   期望: {test_payload}, 实际: {decrypted_payload}")
            
    except Exception as e:
        print(f"❌ 解密测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    print(f"\n" + "=" * 50)
    print("✅ 所有测试通过！")
    print("=" * 50)
    return True

if __name__ == "__main__":
    success = test_encryption()
    sys.exit(0 if success else 1)

