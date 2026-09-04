
if __name__ == '__main__':
    """
    商品名识别节点测试

    测试不同场景下的商品名识别逻辑
    """
    import json
    import os

    from knowledge.processor.import_process.base import setup_logging
    from knowledge.processor.import_process.nodes.item_name_recognition import node_item_name_recognition

    # 1. 开启日志
    setup_logging()

    print("=" * 60)
    print("ItemNameRecognitionNode 节点测试")
    print("=" * 60)

    # -------------------- 测试用例 1: 从 chunks.json 加载 -------------------- #
    print("\n--- 测试用例 1: 从 chunks.json 加载并识别 ---")

    # 获取临时目录
    temp_dir = r"D:\develop\develop\workspace\pycharm\usage\shopkeeper_brain_v260213\knowledge\processor\import_process\temp"
    chunk_json_input_path = os.path.join(temp_dir, "chunks.json")

    # 检查文件是否存在
    if os.path.exists(chunk_json_input_path):
        with open(chunk_json_input_path, "r", encoding="utf-8") as f:
            chunk_list = json.load(f)

        # 构建 state 状态
        state = {
            "file_title": "万用表的使用",
            "chunks": chunk_list
        }

        # 调用处理方法
        result = node_item_name_recognition.process(state)

        print(f"\n识别结果:")
        print(f"  item_name: {result.get('item_name', '未识别')}")
        print(f"  chunks 数量: {len(result.get('chunks', []))}")

        # 检查 chunks 是否已回填 item_name
        if result.get("chunks"):
            first_chunk = result["chunks"][0]
            print(f"  首个 chunk 的 item_name: {first_chunk.get('item_name', '未回填')}")

        # 备份结果
        os.makedirs(temp_dir, exist_ok=True)
        output_path = os.path.join(temp_dir, "chunks_item_name.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"  已备份到: {output_path}")

    else:
        print(f"    chunks.json 文件不存在: {chunk_json_input_path}")
        print("  请先运行 document_split 节点生成 chunks.json")

    # -------------------- 测试用例 2: 使用模拟数据 -------------------- #
    print("\n\n--- 测试用例 2: 使用模拟数据 ---")

    mock_chunks = [
        {
            "title": "# 福禄克 15B+ 数字万用表",
            "content": "福禄克 15B+ 是一款专业级数字万用表，适用于电子工程师和技术人员。\n\n主要特点：\n- 自动量程\n- 高精度测量\n- 坚固耐用",
            "file_title": "万用表说明书"
        },
        {
            "title": "## 产品规格",
            "content": "直流电压：0.1mV - 600V\n交流电压：0.1mV - 600V\n电阻：0.1Ω - 40MΩ",
            "file_title": "万用表说明书"
        },
        {
            "title": "## 安全须知",
            "content": "使用前请仔细阅读本手册。不要测量超过额定值的电压。",
            "file_title": "万用表说明书"
        }
    ]

    mock_state = {
        "file_title": "万用表说明书",
        "chunks": mock_chunks
    }

    mock_result = node_item_name_recognition.process(mock_state)

    print(f"识别结果:")
    print(f"  item_name: {mock_result.get('item_name', '未识别')}")

    # -------------------- 测试用例 3: 空 chunks -------------------- #
    print("\n\n--- 测试用例 3: 空 chunks (预期抛出异常) ---")

    try:
        empty_state = {
            "file_title": "测试文件",
            "chunks": []
        }
        node_item_name_recognition.process(empty_state)
    except Exception as e:
        print(f"捕获到预期异常: {e}")

    # -------------------- 测试用例 4: 缺少 file_title -------------------- #
    print("\n\n--- 测试用例 4: 缺少 file_title (预期抛出异常) ---")

    try:
        no_title_state = {
            "file_title": "",
            "chunks": mock_chunks
        }
        node_item_name_recognition.process(no_title_state)
    except Exception as e:
        print(f"捕获到预期异常: {e}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)