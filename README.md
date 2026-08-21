# AI Based Employee Wellness Management Analytics

A full-stack, enterprise-grade AI-powered web platform for employee health telemetry, risk prediction, personalized wellness recommendations, NLP sentiment analytics, interactive BI dashboards, AI chatbot assistance, and gamified goals & challenges.

Developed by **Bhavyasai0711** for Infosys Internship & B.Tech AI & ML Project.

---

## 🌟 Key Features & Modules

- **Module 1: Authentication & User Management**
  - Secure Signup, Login, Logout, Session persistence, OTP Password Reset, Google OAuth integration, and Profile Picture Upload.
- **Module 2: Employee Health Data Management**
  - Track BMI, sleep cycles, water intake, blood sugar, exercise frequency, attendance, and biometrics. Includes AI Isolation Forest anomaly detection.
- **Module 3: AI Wellness Risk Prediction**
  - Machine Learning risk classification matrix evaluating hypertension, burnout, and stress risk factors.
- **Module 4: Personalized Wellness Recommendations**
  - Content-based and collaborative filtering recommendation engine for diet, cardio, yoga, and mental wellness. Includes real-time Notifications & Reminders center.
- **Module 5: Mental Health & Sentiment Analytics**
  - Anonymous text feedback analysis powered by TextBlob NLP sentiment models.
- **Module 6: Interactive Dashboard & Executive BI**
  - Organization-wide health KPIs, productivity indices, and 30-day predictive forecasting curves using Chart.js.
- **Module 7: AI Wellness Chatbot Assistant**
  - Ollama Qwen / LLM-powered interactive health assistant & automated checkup scheduling.
- **Module 8: Wellness Challenges & Leaderboards**
  - Gamified company challenges, participant tracking, and real-time rank badges (Gold, Silver, Bronze).
- **Module 9: Goals & Achievements**
  - Employee milestone goal setting, progress tracking, and unlocked badge achievements.

---

## 🛠️ Local Setup Instructions

```bash
# 1. Clone the repository
git clone https://github.com/Bhavyasai0711/Employee_Wellness_Management_Analytics.git
cd Employee_Wellness_Management_Analytics

# 2. Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate

# 3. Install requirements
pip install -r requirements.txt

# 4. Run application
python app.py
```

Open `http://127.0.0.1:5000` in your web browser.

---

## 🚀 Deployment (Render / Cloud)

- Includes pre-configured `Procfile` (`web: gunicorn app:app`) and `render.yaml` for 1-click Render web service deployment.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
