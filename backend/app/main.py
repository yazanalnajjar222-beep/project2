from app.db import engine
from app.models import metadata, users, categories, expenses
from sqlalchemy import Float, extract, insert, select, text, update, delete, func, and_,cast
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
metadata.create_all(engine)


# -------------------------------------------------------------------
# Auth Queries
# -------------------------------------------------------------------
def insert_user(name, password_hash, email):
    with engine.connect() as conn:
        try:
            stmt = insert(users).values(
                name=name,
                password_hash=password_hash,
                email=email,
            ).returning(users.c.id)
            result = conn.execute(stmt)
            inserted_id = result.scalar()
            conn.commit()
            return str(inserted_id)
        except SQLAlchemyError:
            conn.rollback()
            return None

def get_budget_summary(user_id):
    """Calculates total spent per category for the current month."""
    now = datetime.now()

    with engine.connect() as conn:
        try:
            # Condition to match current month and year expenses
            join_condition = and_(
                categories.c.id == expenses.c.category_id,
                extract('year', expenses.c.expense_date) == now.year,
                extract('month', expenses.c.expense_date) == now.month
            )

            # Cast sum to Float to ensure calculations and Jinja formatting work reliably
            total_spent_expr = cast(
                func.coalesce(func.sum(expenses.c.amount), 0.0), 
                Float
            ).label("total_spent")

            query = (
                select(
                    categories.c.id,
                    categories.c.name,
                    categories.c.monthly_budget,
                    total_spent_expr
                )
                .select_from(categories.outerjoin(expenses, join_condition))
                .where(categories.c.user_id == cast(user_id, UUID))
                .group_by(
                    categories.c.id,
                    categories.c.name,
                    categories.c.monthly_budget
                )
                .order_by(categories.c.name.asc())
            )

            results = conn.execute(query).mappings().all()

            # Ensure total_spent and monthly_budget are float values for Jinja math
            summary = []
            for row in results:
                item = dict(row)
                item["total_spent"] = float(item["total_spent"] or 0.0)
                item["monthly_budget"] = float(item["monthly_budget"] or 0.0)
                summary.append(item)

            return summary
        except SQLAlchemyError as e:
            print(f"Error in get_budget_summary: {e}")
            return []

def check_if_exist(email, password_hash):
    """Verifies credentials and returns user dict or None."""
    with engine.connect() as conn:
        try:
            query = select(users).where(
                and_(users.c.email == email, users.c.password_hash == password_hash)
            )
            result = conn.execute(query).mappings().first()
            return dict(result) if result else None
        except SQLAlchemyError:
            return None

def delete_category(category_id, user_id):
    """Deletes a category and all associated expenses in a single transaction."""
    cat_uuid = cast(category_id, UUID)
    user_uuid = cast(user_id, UUID)

    with engine.begin() as conn:  # engine.begin() auto-commits!
        try:
            # 1. Delete associated expenses first so FK constraint doesn't fail
            conn.execute(
                delete(expenses).where(
                    and_(
                        expenses.c.category_id == cat_uuid,
                        expenses.c.user_id == user_uuid
                    )
                )
            )
            # 2. Delete the category itself
            result = conn.execute(
                delete(categories).where(
                    and_(
                        categories.c.id == cat_uuid,
                        categories.c.user_id == user_uuid
                    )
                )
            )
            return result.rowcount > 0
        except SQLAlchemyError as e:
            print(f"Error deleting category: {e}")
            return False
# -------------------------------------------------------------------
# Category Queries
# -------------------------------------------------------------------
def insert_category(user_id, name, monthly_budget=None):
    with engine.connect() as conn:
        try:
            stmt = insert(categories).values(
                user_id=user_id,
                name=name,
                monthly_budget=monthly_budget,
            ).returning(categories.c.id)
            result = conn.execute(stmt)
            inserted_id = result.scalar()
            conn.commit()
            return str(inserted_id)
        except SQLAlchemyError:
            conn.rollback()
            raise


def get_categories_by_user(user_id):
    with engine.connect() as conn:
        try:
            query = select(categories).where(categories.c.user_id == user_id)
            result = conn.execute(query).mappings().all()
            return [dict(row) for row in result]
        except SQLAlchemyError:
            return []


def get_category_summary(user_id):
    """Calculates total spending per category for current month vs monthly budget."""
    with engine.connect() as conn:
        try:
            # Left join categories to expenses to sum amounts per category
            query = (
                select(
                    categories.c.id,
                    categories.c.name,
                    categories.c.monthly_budget,
                    func.coalesce(func.sum(expenses.c.amount), 0).label("total_spent")
                )
                .select_from(
                    categories.outerjoin(
                        expenses, categories.c.id == expenses.c.category_id
                    )
                )
                .where(categories.c.user_id == user_id)
                .group_by(categories.c.id, categories.c.name, categories.c.monthly_budget)
            )
            result = conn.execute(query).mappings().all()
            return [dict(row) for row in result]
        except SQLAlchemyError:
            return []


# -------------------------------------------------------------------
# Expense Queries
# -------------------------------------------------------------------
def insert_expense(user_id, category_id, amount, description=None, expense_date=None):
    with engine.connect() as conn:
        try:
            values = dict(
                user_id=user_id,
                category_id=category_id,
                amount=amount,
                description=description,
            )
            if expense_date:
                values["expense_date"] = expense_date

            stmt = insert(expenses).values(**values).returning(expenses.c.id)
            result = conn.execute(stmt)
            inserted_id = result.scalar()
            conn.commit()
            return str(inserted_id)
        except SQLAlchemyError:
            conn.rollback()
            raise


def get_expenses_by_user(user_id):
    with engine.connect() as conn:
        try:
            query = (
                select(expenses, categories.c.name.label("category_name"))
                .select_from(
                    expenses.join(categories, expenses.c.category_id == categories.c.id)
                )
                .where(expenses.c.user_id == user_id)
                .order_by(expenses.c.expense_date.desc())
            )
            result = conn.execute(query).mappings().all()
            return [dict(row) for row in result]
        except SQLAlchemyError:
            return []


def get_expense_by_id(expense_id):
    with engine.connect() as conn:
        try:
            query = select(expenses).where(expenses.c.id == expense_id)
            result = conn.execute(query).mappings().first()
            return dict(result) if result else None
        except SQLAlchemyError:
            return None


def update_expense(expense_id, user_id, category_id, amount, description, expense_date=None):
    with engine.connect() as conn:
        try:
            values = dict(
                category_id=category_id,
                amount=amount,
                description=description
            )
            if expense_date:
                values["expense_date"] = expense_date

            stmt = (
                update(expenses)
                .where(and_(expenses.c.id == expense_id, expenses.c.user_id == user_id))
                .values(**values)
            )
            conn.execute(stmt)
            conn.commit()
        except SQLAlchemyError:
            conn.rollback()
            raise


def delete_expense(expense_id, user_id):
    """Deletes an expense item by explicitly casting IDs to UUID."""
    print(f"--> ATTEMPTING DELETE: expense_id='{expense_id}', user_id='{user_id}'")
    
    with engine.begin() as conn:
        try:
            # Cast inputs to UUID explicitly so PostgreSQL matches the column type
            stmt = delete(expenses).where(
                and_(
                    expenses.c.id == cast(expense_id, UUID),
                    expenses.c.user_id == cast(user_id, UUID)
                )
            )
            result = conn.execute(stmt)
            print(f"--> SUCCESS: Deleted {result.rowcount} row(s) from database.")
            return result.rowcount > 0
        except SQLAlchemyError as e:
            print(f"--> ERROR during deletion: {e}")
            return False

def search_expenses(user_id, category_id=None, min_amount=None, max_amount=None, start_date=None, end_date=None):
    with engine.connect() as conn:
        try:
            conditions = [expenses.c.user_id == user_id]

            if category_id:
                conditions.append(expenses.c.category_id == category_id)
            if min_amount:
                conditions.append(expenses.c.amount >= float(min_amount))
            if max_amount:
                conditions.append(expenses.c.amount <= float(max_amount))
            if start_date:
                conditions.append(expenses.c.expense_date >= start_date)
            if end_date:
                conditions.append(expenses.c.expense_date <= end_date)

            query = (
                select(expenses, categories.c.name.label("category_name"))
                .select_from(
                    expenses.join(categories, expenses.c.category_id == categories.c.id)
                )
                .where(and_(*conditions))
                .order_by(expenses.c.expense_date.desc())
            )

            result = conn.execute(query).mappings().all()
            return [dict(row) for row in result]
        except SQLAlchemyError:
            return []
