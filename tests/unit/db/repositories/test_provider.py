"""商品仓库提供者测试。"""

from app.db.repositories.provider import (
    get_product_repository,
)


def test_get_product_repository_loads_sample_products() -> None:
    """验证提供者能够加载样例商品并创建仓库。"""

    # 清除函数缓存，确保本次测试重新读取商品文件
    get_product_repository.cache_clear()

    # 获取已经装载样例商品数据的仓库
    repository = get_product_repository()

    # 搜索样例数据中的衬衫商品
    products = repository.search(
        query="衬衫",
        category="衬衫",
    )

    # 验证仓库至少返回一件符合条件的商品
    assert len(products) >= 1

    # 验证搜索结果确实属于衬衫品类
    assert all(
        product.category == "衬衫"
        for product in products
    )