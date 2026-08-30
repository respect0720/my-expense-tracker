import os
from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime

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

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

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
    subcategory: str = None,
    merchant: str = None,
    payment_method: str = None,
    note: str = None
):
    

    db = SessionLocal()

    transaction = Transaction(
        amount=amount,
        transaction_type="expense",
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
    # 取得本月第一天 (例如 2026-08-01)
    first_day_of_month = today.replace(day=1)
    
    # 計算今日總花費
    today_total = db.query(func.sum(Transaction.amount)).filter(
        Transaction.transaction_date == today
    ).scalar() or 0
    
    # 計算本月總花費
    month_total = db.query(func.sum(Transaction.amount)).filter(
        Transaction.transaction_date >= first_day_of_month
    ).scalar() or 0
    
    db.close()
    return {
        "today_total": today_total,
        "month_total": month_total
    }

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
