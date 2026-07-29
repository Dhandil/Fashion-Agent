"""SQLAlchmy 数据库模型公共基类。"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """项目中所有 SQLAlchemy 数据库模型的公共基类。"""

    # 当前不需要定义公共字段
    # SQLAlchemy 会通过该基类统一收集模型和表的元数据
    pass