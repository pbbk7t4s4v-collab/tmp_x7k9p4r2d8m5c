try:
    result = 10 / 0
except ZeroDivisionError:
    print("不能除以零！")
    result = None

print(f"结果: {result}")