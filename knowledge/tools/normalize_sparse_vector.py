# knowledge/tools/normalize_sparse_vector.py
"""
稀疏向量 L2 归一化工具

功能：
    将 BGE-M3 生成的稀疏向量（token_id: weight 字典）进行 L2 归一化，
    使得 Milvus 中使用 IP（内积）距离等价于余弦相似度。

背景：
    BGE-M3 输出稀疏向量为 CSR 矩阵格式，转换为 Dict 后权重未归一化。
    若直接使用原始权重，长文档或高频词会获得过高内积值，破坏检索公平性。
    通过 L2 归一化，所有向量模长为 1，内积即余弦相似度。

使用场景：
    - 商品名识别节点（item_name_recognition.py）
    - 切片向量化节点（bge_embedding.py）
    - 知识图谱实体向量化节点（knowledge_graph.py）
    - 查询流程中的向量检索节点（search_embedding.py 等）
"""

import logging
from typing import Dict, Optional
import math

logger = logging.getLogger(__name__)


def normalize_sparse_vector(
    sparse_vector: Optional[Dict[int, float]],
    eps: float = 1e-12
) -> Dict[int, float]:
    """
    对稀疏向量进行 L2 归一化。

    Args:
        sparse_vector: 原始稀疏向量，格式为 {token_id: weight}。
                      允许为 None 或空字典。
        eps: 极小值，防止除零。

    Returns:
        归一化后的稀疏向量（与原字典结构相同，但权重已缩放）。
        若输入为 None 或空，返回空字典。

    Raises:
        TypeError: 如果输入不是字典类型或字典的键/值类型错误。
        ValueError: 如果存在负权重（稀疏向量权重应为非负，但 BGE-M3 输出可能含负值，此处仅警告）。
    """
    # 1. 类型与空值检查
    if sparse_vector is None:
        logger.debug("输入稀疏向量为 None，返回空字典")
        return {}

    if not isinstance(sparse_vector, dict):
        raise TypeError(
            f"sparse_vector 必须为 dict，实际类型为 {type(sparse_vector).__name__}"
        )

    if not sparse_vector:
        return {}

    # 2. 计算 L2 范数的平方和，同时检查键/值有效性
    norm_sq = 0.0
    invalid_keys = []
    for token_id, weight in sparse_vector.items():
        # 检查 token_id 类型（应为 int）
        if not isinstance(token_id, (int,)):
            invalid_keys.append(token_id)
            continue
        # 检查 weight 类型（应为 int 或 float），并转为 float
        if not isinstance(weight, (int, float)):
            invalid_keys.append(token_id)
            continue
        # 若权重为负，记录警告（但继续计算，因为 BGE-M3 有时会输出极小负值）
        if weight < 0:
            logger.warning(
                f"稀疏向量中存在负权重: token_id={token_id}, weight={weight}。"
                "将保留负值，但可能影响归一化稳定性。"
            )
        # 累加平方
        norm_sq += weight * weight

    if invalid_keys:
        logger.warning(f"过滤掉 {len(invalid_keys)} 个无效键/值类型的 token")
        # 移除无效条目（仅当有无效条目时重新构建字典）
        sparse_vector = {
            k: v for k, v in sparse_vector.items()
            if isinstance(k, (int,)) and isinstance(v, (int, float))
        }
        if not sparse_vector:
            return {}

    # 3. 计算范数，处理零向量
    norm = math.sqrt(norm_sq)
    if norm < eps:
        logger.debug("稀疏向量 L2 范数接近零，返回空向量")
        return {}

    # 4. 归一化：每个权重除以范数
    # 使用字典推导式，保留原始键
    normalized = {token_id: weight / norm for token_id, weight in sparse_vector.items()}

    logger.debug(f"归一化完成，原始非零项数: {len(sparse_vector)}，范数: {norm:.6f}")
    return normalized


# 可选：直接对 CSR 矩阵提取的原始稀疏向量进行归一化（兼容已有代码）
def normalize_from_csr(indices, data, indptr, row_index: int = 0) -> Dict[int, float]:
    """
    从 CSR 矩阵中提取第 row_index 行的稀疏向量并 L2 归一化。

    此函数为辅助工具，可直接用于 BGE-M3 输出的 CSR 矩阵提取。
    推荐直接使用 normalize_sparse_vector 处理已转换的字典。

    Args:
        indices: CSR 的 indices 数组（列索引）
        data: CSR 的 data 数组（权重）
        indptr: CSR 的 indptr 数组（行偏移）
        row_index: 要提取的行索引，默认为 0（单向量场景）

    Returns:
        归一化后的稀疏向量字典
    """
    start = indptr[row_index]
    end = indptr[row_index + 1]
    token_ids = indices[start:end]
    weights = data[start:end]
    raw_dict = dict(zip(token_ids, weights))
    return normalize_sparse_vector(raw_dict)


# ============================================================================
# 测试入口
# ============================================================================
if __name__ == "__main__":
    import sys

    # 配置简单日志输出
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    print("=" * 60)
    print("测试稀疏向量 L2 归一化工具")
    print("=" * 60)

    # 测试用例 1: 正常稀疏向量
    print("\n--- 测试 1: 正常稀疏向量 ---")
    raw = {101: 1.0, 205: 2.0, 309: 3.0}
    normed = normalize_sparse_vector(raw)
    print(f"原始: {raw}")
    print(f"归一化后: {normed}")
    # 验证范数是否为 1
    norm_calc = math.sqrt(sum(w*w for w in normed.values()))
    print(f"归一化后向量 L2 范数: {norm_calc:.6f} (应为 1.0)")

    # 测试用例 2: 空字典
    print("\n--- 测试 2: 空字典 ---")
    empty = {}
    result = normalize_sparse_vector(empty)
    print(f"输入: {empty}, 输出: {result} (应为 {{}})")

    # 测试用例 3: None
    print("\n--- 测试 3: None ---")
    result = normalize_sparse_vector(None)
    print(f"输入: None, 输出: {result} (应为 {{}})")

    # 测试用例 4: 含负权重（BGE-M3 可能产生极小负值）
    print("\n--- 测试 4: 含负权重 ---")
    with_neg = {10: 0.5, 20: -0.1, 30: 0.8}
    normed_neg = normalize_sparse_vector(with_neg)
    print(f"原始: {with_neg}")
    print(f"归一化后: {normed_neg}")
    norm_calc_neg = math.sqrt(sum(w*w for w in normed_neg.values()))
    print(f"归一化后向量 L2 范数: {norm_calc_neg:.6f}")

    # 测试用例 5: 全零向量
    print("\n--- 测试 5: 全零向量 ---")
    zero_vec = {1: 0.0, 2: 0.0}
    result_zero = normalize_sparse_vector(zero_vec)
    print(f"输入: {zero_vec}, 输出: {result_zero} (应为 {{}})")

    # 测试用例 6: 模拟从 CSR 提取
    print("\n--- 测试 6: 模拟 CSR 提取并归一化 ---")
    # 假设 indices, data, indptr 来自 BGE-M3 的 CSR 矩阵
    # 单行向量，假设有 3 个非零元
    indices = [101, 205, 309]
    data = [1.0, 2.0, 3.0]
    indptr = [0, 3]  # 只有一行
    result_csr = normalize_from_csr(indices, data, indptr, row_index=0)
    print(f"CSR 提取归一化结果: {result_csr}")

    # 测试用例 7: 非法输入（非字典）
    print("\n--- 测试 7: 非法输入（应抛出 TypeError）---")
    try:
        normalize_sparse_vector([1, 2, 3])
    except TypeError as e:
        print(f"捕获异常: {e}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)