import os
import pandas as pd
from fastapi.responses import FileResponse
from fastapi import FastAPI
from sqlalchemy import create_engine, Column, Integer, Float, String, Date
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import func
from datetime import date


app = FastAPI()

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./expenses.db")


# ==========================================
# 1. FastAPI
# ==========================================

app = FastAPI(
    title="My Expense Tracker",
    description="我的個人記帳系統",
    version="1.0.0"
)


# ==========================================
# 2. SQLite Database
# ==========================================

if DATABASE_URL.startswith("sqlite"):
    # 如果是本地端開發，保留 SQLite 的專屬設定
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # 如果是雲端 PostgreSQL，自動拿掉會報錯的設定
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


# ==========================================
# 3. 建立交易資料表
# ==========================================

class Transaction(Base):

    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)

    amount = Column(Float, nullable=False)

    transaction_type = Column(
        String,
        default="expense"
    )

    category = Column(
        String,
        nullable=False
    )

    subcategory = Column(
        String,
        nullable=True
    )

    merchant = Column(
        String,
        nullable=True
    )

    payment_method = Column(
        String,
        nullable=True
    )

    note = Column(
        String,
        nullable=True
    )

    transaction_date = Column(
        Date,
        default=date.today
    )


# ==========================================
# 4. 建立資料表
# ==========================================

Base.metadata.create_all(bind=engine)


# ==========================================
# 5. 首頁
# ==========================================
# ==========================================
# 5. 新增一筆交易
# ==========================================

@app.post("/transactions")
def create_transaction(
    amount: float,
    category: str,
    transaction_type: str = "expense",
    subcategory: str = None,
    merchant: str = None,
    payment_method: str = None,
    note: str = None
):
    

    db = SessionLocal()

    transaction = Transaction(
        amount=amount,
        transaction_type=transaction_type,
        category=category,
        subcategory=subcategory,
        merchant=merchant,
        payment_method=payment_method,
        note=note
    )

    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    db.close()

    return {
        "message": "記帳成功",
        "transaction": {
            "id": transaction.id,
            "amount": transaction.amount,
            "type": transaction.transaction_type,
            "category": transaction.category,
            "subcategory": transaction.subcategory,
            "merchant": transaction.merchant,
            "payment_method": transaction.payment_method,
            "note": transaction.note,
            "date": str(transaction.transaction_date)
        }
    }

# ==========================================
# 6. 查看所有交易
# ==========================================

@app.get("/transactions")
def get_transactions():

    db = SessionLocal()

    transactions = (
        db.query(Transaction)
        .order_by(Transaction.id.desc())
        .all()
    )

    result = []

    for transaction in transactions:

        result.append({
            "id": transaction.id,
            "amount": transaction.amount,
            "type": transaction.transaction_type,
            "category": transaction.category,
            "subcategory": transaction.subcategory,
            "merchant": transaction.merchant,
            "payment_method": transaction.payment_method,
            "note": transaction.note,
            "date": str(transaction.transaction_date)
        })

    db.close()

    return result

# 7. 刪除交易
@app.delete("/transactions/{transaction_id}")
def delete_transaction(transaction_id: int):
    db = SessionLocal()
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    
    if transaction:
        db.delete(transaction)
        db.commit()
        
    db.close()
    return {"message": "刪除成功"}

# 5. 首頁 - 改為回傳 HTML 網頁
@app.get("/")
def home():
    return FileResponse("index.html")

# 8. 取得統計資料
@app.get("/statistics")
def get_statistics():
    db = SessionLocal()
    today = date.today()
    first_day_of_month = today.replace(day=1)
    
    # 計算本月總收入
    month_income = db.query(func.sum(Transaction.amount)).filter(
        Transaction.transaction_date >= first_day_of_month,
        Transaction.transaction_type == "income"
    ).scalar() or 0
    
    # 計算本月總支出
    month_expense = db.query(func.sum(Transaction.amount)).filter(
        Transaction.transaction_date >= first_day_of_month,
        Transaction.transaction_type == "expense"
    ).scalar() or 0
    
    db.close()
    
    return {
        "month_income": month_income,
        "month_expense": month_expense,
        "balance": month_income - month_expense  # 本月結餘
    }
# 10. 取得今年 1 到 12 月的各月收支統計
@app.get("/statistics/monthly")
def get_monthly_statistics():
    db = SessionLocal()
    current_year = date.today().year
    
    monthly_data = []
    
    # 用迴圈跑 1 到 12 月
    for month in range(1, 13):
        # 找出該月第一天與最後一天
        if month == 12:
            start_date = date(current_year, 12, 1)
            end_date = date(current_year + 1, 1, 1)
        else:
            start_date = date(current_year, month, 1)
            end_date = date(current_year, month + 1, 1)
            
        # 計算該月總收入
        income = db.query(func.sum(Transaction.amount)).filter(
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date < end_date,
            Transaction.transaction_type == "income"
        ).scalar() or 0
        
        # 計算該月總支出
        expense = db.query(func.sum(Transaction.amount)).filter(
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date < end_date,
            Transaction.transaction_type == "expense"
        ).scalar() or 0
        
        monthly_data.append({
            "month": f"{month}月",
            "income": income,
            "expense": expense,
            "balance": income - expense
        })
        
    db.close()
    return monthly_data

# 9. 匯出 Excel
@app.get("/export/excel")
def export_excel():
    db = SessionLocal()
    transactions = db.query(Transaction).all()
    db.close()
    
    # 準備整理給 Excel 的資料
    data = []
    for t in transactions:
        data.append({
            "日期": t.transaction_date,
            "金額": t.amount,
            "分類": t.category,
            "子分類": t.subcategory,
            "商家": t.merchant,
            "付款方式": t.payment_method,
            "備註": t.note
        })
        
    # 用 pandas 產生 Excel 檔案
    df = pd.DataFrame(data)
    file_name = "expenses_export.xlsx"
    df.to_excel(file_name, index=False)
    
    return FileResponse(file_name, filename="我的記帳紀錄.xlsx")