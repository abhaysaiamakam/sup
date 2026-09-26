# NexusHR — Corporate Employee Service Portal (React + FastAPI)

A clean, modern, full-stack HR Employee Service Portal built with **React (Vite)**, **FastAPI**, and **SQLite**.

---

## 🌟 Key Features
- **Dynamic Category Forms**: Leave Clarification, Confidential Payroll Queries, Experience Letters, Hardware Asset Requests, and Onboarding.
- **Role-Based Access Control (RBAC)**: Switch between **Employee**, **HR Specialist**, **Payroll Lead**, **IT Specialist**, and **Admin** in 1 click.
- **Dual-Stream Communication**: Public chat replies + Private Internal Notes for HR staff.
- **Official Certificate Generation**: Auto-generated Experience/Employment Letter preview.
- **Live Analytics**: Real-time KPI cards for open backlog, resolved count, SLA averages, and category distribution.
- **Clean Architecture**: Self-contained SQLite database with zero external database configuration required.

---

## 🚀 How to Run the Application

### 1. Start the FastAPI Backend
```bash
# In the project root directory
python3 -m uvicorn main:app --reload --port 8000
```
API Documentation available at: `http://127.0.0.1:8000/docs`

### 2. Start the React Frontend
```bash
# In a second terminal
cd client
npm run dev
```
Open in browser: `http://localhost:5173`

---

## 📁 Clean Directory Structure
```
hr_service_portal/
├── main.py              # Self-contained, simple FastAPI backend with SQLite & pre-seeded data
├── hr_portal.db         # SQLite database file
├── client/              # React (Vite) Frontend
│   ├── src/
│   │   ├── App.jsx      # Clean single-component React application with all views
│   │   ├── App.css      # Component styles, cards, modals, grid layout
│   │   ├── index.css    # Modern global design system & color variables
│   │   └── main.jsx     # React DOM root entry
│   ├── package.json
│   └── vite.config.js
└── README.md
```

---

## 👥 Demo Credentials
Switch roles directly from the top navigation dropdown:
- **John Doe (Employee)**: Raises requests, views own tickets, confirms resolution.
- **Sarah Smith (Employee)**: Raises asset & marketing requests.
- **Elena Rostova (HR Specialist)**: Reviews tickets, writes internal notes, issues letters.
- **David Miller (Payroll Lead)**: Handles confidential payroll & tax queries.
- **Alex Rivera (IT Specialist)**: Fulfills hardware & asset deliveries.
- **Admin Marcus (Admin)**: Full overview, employee directory, and system analytics.
