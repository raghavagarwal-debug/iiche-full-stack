<div align="center">

<img src="assests/iiche_bit_mesra_student_chapter_logo-removebg-preview.png" alt="IIChE BIT Mesra Logo" width="100"/>

# IIChE Student Chapter, BIT Mesra

### Official Website & Event Management System

Empowering Future Chemical Engineers Through Innovation, Leadership & Technical Excellence.

![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css3&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-06B6D4?style=for-the-badge&logo=tailwind-css&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![GSAP](https://img.shields.io/badge/GSAP-88CE02?style=for-the-badge&logo=greensock&logoColor=white)

</div>

---

## 📖 About

The **IIChE Student Chapter, BIT Mesra** is a premier student organization dedicated to promoting innovation, technical excellence, and professional growth in Chemical Engineering. This repository contains the full source code for the official digital platform of the chapter, featuring a dynamic frontend integrated with a robust FastAPI backend.

The platform handles chapter initiatives, technical events (such as **Coalescence**), workshops, alumni interactions, executive board profiles, secure user authentication, real-time event registration, and an admin management dashboard.

---

## ✨ Features

- **Modern & Responsive UI**: Designed with Tailwind CSS v4 and smooth GSAP/Lenis scroll animations.
- **Authentication & Security**: Email/password authentication, Google OAuth 2.0, OTP-based password reset, session cookies (HttpOnly, SameSite), and CSRF protection.
- **Dynamic Event Registrations**: Authenticated user event registration flow with instant feedback and registration status tracking.
- **Admin Dashboard**: Comprehensive admin panel (`/pages/admin.html`) to create/edit events, view live registration counts, manage registrations, and export attendee data to CSV.
- **Cloudinary Media Delivery**: High-performance image hosting for chapter galleries and team photos.
- **RESTful API**: OpenAPI (Swagger) compliant FastAPI backend built with SQLAlchemy 2.0 async ORM and Alembic database migrations.

---

## 🛠 Tech Stack

### Frontend
| Component | Technology |
|-----------|------------|
| Markup & Styling | HTML5, CSS3, Tailwind CSS v4 (`@tailwindcss/cli`) |
| Interactivity & Animations | JavaScript (ES6+), GSAP, Lenis Smooth Scroll |
| API Communication | Custom Client SDK (`auth-client.js`, `events-client.js`) |

### Backend & Infrastructure
| Component | Technology |
|-----------|------------|
| Framework | Python 3.12+, FastAPI, Uvicorn (ASGI) |
| Database & ORM | PostgreSQL / SQLite, SQLAlchemy 2.0 (Async), Alembic |
| Caching & Rate Limiting | Redis |
| Containerization | Docker, Docker Compose |
| Image Hosting | Cloudinary CDN |

---

## 📁 Project Structure

```text
iiche/
├── index.html                   # Main landing page
├── auth-client.js               # Frontend Auth & API Client SDK
├── events-client.js             # Dynamic Events & Registration SDK
├── input.css                    # Tailwind CSS source file
├── output.css                   # Compiled Tailwind CSS output
├── package.json                 # Node.js dependencies (Tailwind CLI)
├── assests/                     # Logos, brand assets, images
├── pages/                       # Website pages
│   ├── login.html               # Login & Account Signup
│   ├── forgot-password.html     # Request OTP
│   ├── verify-otp.html          # OTP verification
│   ├── reset-password.html       # Set new password
│   ├── events.html              # Events portal
│   ├── admin.html               # Admin management dashboard
│   ├── departments.html         # Departmental structure
│   ├── committee.html           # Team & Committee details
│   └── more.html                # Additional resources
├── events/                      # Event specific showcase pages
│   ├── coalescnece.26.html
│   ├── coalescnece.25.html
│   ├── workshop.html
│   ├── talks.html
│   └── otherevents.html
├── committee/                   # Executive board & vision
└── backend/                     # FastAPI Backend Application
    ├── app/
    │   ├── main.py              # Application entry point
    │   ├── api/v1/              # API Route Handlers (Auth, Events, Admin, Users)
    │   ├── core/                # Config, Security, DB session, Dependencies
    │   ├── models/              # SQLAlchemy ORM Models
    │   ├── schemas/             # Pydantic Request/Response validation
    │   └── services/            # Business Logic Layer
    ├── alembic/                 # Database Migrations
    ├── docker-compose.yml       # Docker Compose setup (FastAPI + Postgres + Redis)
    ├── Dockerfile               # Production container spec
    ├── make_admin.py            # CLI script to grant admin privileges
    ├── requirements.txt         # Python dependencies
    └── .env.example             # Environment variables template
```

---

## ⚙️ Prerequisites

Before running the website locally, ensure you have the following installed on your machine:

1. **Node.js**: `v18.0.0` or higher (includes `npm`) - [Download Node.js](https://nodejs.org/)
2. **Python**: `v3.12` or higher - [Download Python](https://www.python.org/)
3. **Docker & Docker Compose** *(Recommended for Backend)* - [Download Docker Desktop](https://www.docker.com/)
4. *(Optional)* **Git**: For repository management.

---

## 🚀 Local Setup & Execution Guide

Follow these step-by-step instructions to get both the Frontend and Backend running on your local machine.

### Step 1: Clone the Repository

```bash
git clone https://github.com/raghavagarwal-debug/iiche-final-repo.git
cd iiche-final-repo
```

---

### Step 2: Set Up & Run the Frontend

1. **Install Node Dependencies:**
   Install Tailwind CSS CLI and related dependencies from the root directory:
   ```bash
   npm install
   ```

2. **Compile / Watch Tailwind CSS:**
   Run the Tailwind CLI watcher to automatically compile `input.css` into `output.css` when styles change:
   ```bash
   npx @tailwindcss/cli -i ./input.css -o ./output.css --watch
   ```
   *(Keep this terminal running or run once without `--watch` to generate `output.css`).*

3. **Serve the Static Frontend:**
   Launch a local HTTP server from the repository root directory. You can use any of the following options:
   
   - **Option A: VS Code Live Server extension**
     Right-click `index.html` in VS Code and select **"Open with Live Server"** (default port `5500`).
   
   - **Option B: Node `serve` CLI**
     ```bash
     npx serve -l 5500 .
     ```
   
   - **Option C: Python Built-in HTTP Server**
     ```bash
     python -m http.server 5500
     ```

   The frontend interface will be available at: `http://localhost:5500`

---

### Step 3: Set Up & Run the Backend API

You can start the backend using **Docker Compose (Quickest)** or via a **Local Python Virtual Environment**.

#### **Option A: Quick Start with Docker Compose (Recommended)**

1. **Navigate to the backend directory:**
   ```bash
   cd backend
   ```

2. **Set up Environment Variables:**
   Copy `.env.example` to create your local `.env` file:
   ```bash
   cp .env.example .env
   ```
   *(Note: On Windows PowerShell, use `copy .env.example .env`)*

3. **Start all backend services (FastAPI + PostgreSQL + Redis):**
   ```bash
   docker-compose up -d --build
   ```

4. **Run Database Migrations:**
   Apply Alembic migrations to create the required tables in PostgreSQL:
   ```bash
   docker-compose exec api alembic upgrade head
   ```

---

#### **Option B: Local Python Setup (Without Docker)**

If you prefer to run Python directly without Docker containers:

1. **Navigate to the backend directory:**
   ```bash
   cd backend
   ```

2. **Create and Activate a Python Virtual Environment:**
   - **On Windows (PowerShell):**
     ```powershell
     python -m venv venv
     .\venv\Scripts\activate
     ```
   - **On macOS / Linux:**
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables:**
   Create a `.env` file from `.env.example`:
   ```bash
   cp .env.example .env
   ```
   *If using SQLite locally instead of PostgreSQL, set `DATABASE_URL=sqlite+aiosqlite:///./iiche_dev.db` in `.env`.*

5. **Apply Database Migrations:**
   ```bash
   alembic upgrade head
   ```

6. **Start the FastAPI Uvicorn Server:**
   ```bash
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

   The API server will start at: `http://localhost:8000`

---

### Step 4: Create an Admin Account (Admin Dashboard Access)

To access the **Admin Dashboard** (`/pages/admin.html`) and manage events/registrations:

1. Open `http://localhost:5500/pages/login.html` in your browser and register a new user account (or use an existing account).
2. Open a terminal in the `backend/` directory (with virtual environment active or inside Docker container).
3. Run the `make_admin.py` CLI script with your registered email (and optionally specify a new password):
   ```bash
   python make_admin.py your_email@example.com [new_password]
   ```
   *Example:*
   ```bash
   python make_admin.py satyamkumar29848@gmail.com admin123
   ```
4. Log in on the website with your email and password. You can now access `http://localhost:5500/pages/admin.html` with full administrative privileges!

---

## 🔗 Key URLs & Local Endpoints

| Resource | Service / URL |
|----------|---------------|
| **Frontend Homepage** | `http://localhost:5500` |
| **Login & Register** | `http://localhost:5500/pages/login.html` |
| **Admin Dashboard** | `http://localhost:5500/pages/admin.html` |
| **Events Portal** | `http://localhost:5500/pages/events.html` |
| **Backend API Base** | `http://localhost:8000/api/v1` |
| **Swagger Interactive API Docs** | `http://localhost:8000/docs` |
| **ReDoc API Documentation** | `http://localhost:8000/redoc` |
| **Backend Health Check** | `http://localhost:8000/health` |

---

## 🧪 Testing & API Documentation

- **Interactive API Testing**: Access `http://localhost:8000/docs` to test authentication, user profiles, event management, and registration endpoints directly from your browser.
- **Automated Tests**: Run unit and integration tests for the backend:
  ```bash
  cd backend
  pytest
  ```

---

## 🔒 Security & Best Practices

- **Password Hashing**: Uses **Argon2id** algorithm for secure password hashing.
- **Session Tokens**: HttpOnly, Secure, SameSite cookies prevent XSS and session hijacking.
- **CSRF Protection**: Token-based validation on all state-changing endpoints.
- **Rate Limiting**: Redis-backed sliding window rate limits on Auth endpoints.
- **Environment Isolation**: Sensitive secrets (JWT/Session keys, DB credentials) are stored exclusively in `.env` and never committed to Git.

---

## 👨‍💻 Developed By

<table>
<tr>
<td align="center" width="50%">

### Raghav Agarwal

Full Stack Developer  
*IIChE Student Chapter, BIT Mesra*

</td>

<td align="center" width="50%">

### Satyam Raj

Full Stack Developer  
*IIChE Student Chapter, BIT Mesra*

</td>
</tr>
</table>

---

## 📄 License

This project is licensed under the **MIT License**. See the [LICENSE](file:///c:/Users/BIT/OneDrive%20-%20Amity%20University/Desktop/iiche/LICENSE) file for details.

---

<div align="center">

### IIChE Student Chapter, BIT Mesra

**Catalyzing Innovation • Engineering Excellence • Building the Future**

© 2026 IIChE Student Chapter, BIT Mesra. All Rights Reserved.

</div>