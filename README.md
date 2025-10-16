# Quantara 🚀  
*AI-Powered Portfolio Forecasting Platform*  

Quantara is a **FinTech platform** that combines **historical stock data** (via [yfinance](https://pypi.org/project/yfinance/)) and **financial news sentiment analysis** (FinBERT + API sources) to deliver **next-day portfolio forecasts** with transparency and explainability.  

⚠️ **Status:** In Progress – actively building out the backend and ML pipeline.  

---

## 📌 Features (Planned & In-Progress)  
- 📊 **Hybrid Predictions** – combine historical OHLCV stock data + news sentiment features.  
- 🧠 **ML Models** – FinBERT for sentiment, XGBoost for time-series forecasting.  
- 💬 **Conversational Insights** – query portfolio performance with LangChain + OpenAI.  
- ⚡ **Real-Time Forecasts** – backend deployed via FastAPI + AWS Lambda.  
- 🖥️ **Interactive Dashboard** – React + PostgreSQL frontend for visualization.  

---

## 🛠️ Tech Stack  
**Languages:** Python, JavaScript (React), SQL  
**ML/DL:** TensorFlow, PyTorch, XGBoost, FinBERT  
**Backend:** FastAPI, Docker, AWS Lambda  
**Database:** PostgreSQL, FAISS (vector search)  
**Other Tools:** GitHub Actions (CI/CD), LangChain, OpenAI API  

---

## 📂 Project Structure (WIP)  
```
Quantara/
├── backend/                            # Core backend logic
│ ├── data/                             # Data loaders and raw/processed storage
│ │ ├── news_raw/                       # Raw scraped/collected news data
│ │ ├── news_processed/                 # Cleaned/feature-engineered news data
│ │ └── stocks/                         # Historical stock data (via yfinance)
│ ├── db/                               # Database connection + schemas
│ │ ├── db_connection.py
│ │ └── schemas.py
│ ├── models/                           # Trained ML models + experiments
│ ├── notebooks/                        # Jupyter notebooks for exploration
│ ├── services/                         # Microservices for modular tasks
│ │ ├── backtesting_service.py          # Portfolio backtesting pipeline
│ │ ├── conversational_service.py       # LLM-powered query interface
│ │ ├── data_pipeline.py                # ETL pipeline (yfinance + APIs)
│ │ ├── prediction_service.py           # ML forecasting endpoints
│ │ └── sentiment_service.py            # FinBERT news sentiment analysis
│ ├── utils/                            # Shared utilities
│ │ ├── config.py
│ │ └── visualization.py
│ ├── app.py                            # FastAPI entry point
│ └── requirements.txt                  # Python dependencies
│
├── frontend/                           # React-based dashboard
│ └── src/
│ ├── components/                       # Reusable UI components
│ ├── pages/                            # Dashboard pages
│ └── App.jsx                           # Main React app entry point
│ └── package.json                      # Frontend dependencies
│
├── .gitignore
└── README.md

```
---

## 📌 Features (Planned & In-Progress)  
- 📊 **Hybrid Predictions** – Combine historical OHLCV stock data + sentiment features.  
- 🧠 **ML Models** – FinBERT for sentiment, XGBoost for forecasting.  
- 💬 **Conversational Insights** – Natural language portfolio queries (LangChain + OpenAI).  
- ⚡ **Scalable Backend** – Modular FastAPI services (prediction, sentiment, backtesting).  
- 🖥️ **Interactive Frontend** – React dashboard with stock visualizations and portfolio simulations.  

---

## 🛠️ Tech Stack  
**Languages:** Python, JavaScript (React), SQL  
**ML/DL:** TensorFlow, PyTorch, XGBoost, FinBERT  
**Backend:** FastAPI, Docker, AWS Lambda  
**Database:** PostgreSQL, FAISS (vector search)  
**Other Tools:** GitHub Actions (CI/CD), LangChain, OpenAI API  

---

## 🚧 Roadmap  
- [X] Complete sentiment pipeline (FinBERT integration + preprocessing).  
- [ ] Build XGBoost forecasting + backtesting services.  
- [ ] Deploy backend with FastAPI + Docker + AWS Lambda.  
- [ ] Expand React dashboard (charts, tables, conversational UI).  
- [ ] Add attribution & explainability visualizations.  

---

## 📜 License  
This project is for **educational and research purposes**.  

---

## 👤 Author  
**Deep Sahu**  
- [LinkedIn](https://linkedin.com/in/deepsahu1)  
- [Portfolio](https://deepsahu.vercel.app)  
- [GitHub](https://github.com/deepsahu21)  

