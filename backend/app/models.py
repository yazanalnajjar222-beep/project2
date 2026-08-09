from sqlalchemy import  MetaData, Table, Column, String, Text, Numeric, TIMESTAMP, ForeignKey, text

from sqlalchemy.dialects.postgresql import UUID

metadata = MetaData()

users = Table(
    "users",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True,
           server_default=text("gen_random_uuid()")),
    Column("email", String, nullable=False, unique=True),
    Column("password_hash", String, nullable=False),
    Column("name", String, nullable=False),
    Column("created_at", TIMESTAMP, nullable=False,
           server_default=text("CURRENT_TIMESTAMP")),
)

categories = Table(
    "categories",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True,
           server_default=text("gen_random_uuid()")),
    Column("user_id", UUID(as_uuid=True),
           ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("name", String, nullable=False),
    Column("monthly_budget", Numeric(12, 2)),
)

expenses = Table(
    "expenses",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True,
           server_default=text("gen_random_uuid()")),
    Column("user_id", UUID(as_uuid=True),
           ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("category_id", UUID(as_uuid=True),
           ForeignKey("categories.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("amount", Numeric(12, 2), nullable=False),
    Column("description", Text),
    Column("expense_date", TIMESTAMP, nullable=False,
           server_default=text("CURRENT_TIMESTAMP")),
    Column("created_at", TIMESTAMP, nullable=False,
           server_default=text("CURRENT_TIMESTAMP")),
)