# Beginner-Friendly Guide: Using Render for Deploying Backend and Frontend in the AI Complaint System

## Introduction

Render (https://render.com) is a modern cloud platform that allows you to deploy web services, static sites, background workers, databases, and more with minimal configuration. In the **AI Complaint System** project, Render is used to host both the backend services (such as the API, scheduler, and database connection) and the frontend dashboard (the admin UI).

This guide will take you step by step through deploying both backend and frontend for this project.

---

## Prerequisites

- A [GitHub](https://github.com/) account with your project repository (e.g., `shail211/AI-Complaint-System`).
- A [Render](https://dashboard.render.com/) account (you can sign up for free).
- Basic understanding of Git and your project structure (which folders/files are backend, which are frontend).

---

## Step 1: Prepare Your Repository

1. **Structure Your Project:**
   - Your backend should be in its own folder (e.g., `AIComplaintBackend/`).
   - Your frontend (dashboard) should be in a separate folder (e.g., `dashboard/` or `AIComplaintFrontend/`).
   - Ensure both the backend and frontend have their own `requirements.txt` (Python) or `package.json` (if JS) if needed.

2. **Create a `.env.example` file** listing all the required environment variables (without secrets).
   - Example:
     ```
     MONGODB_URI=your-mongo-uri
     FACEBOOK_ACCESS_TOKEN=your-fb-token
     ```

---

## Step 2: Connect Your Repo to Render

1. Go to [Render Dashboard](https://dashboard.render.com/).
2. Click **New** > **Web Service** (for backend), or **Static Site** (for frontend).
3. Click **Connect a repository** and select your GitHub account.
4. Choose your repository (`AI-Complaint-System`).

---

## Step 3: Deploy the Backend (Web Service)

1. **Choose the Backend Directory**  
   When prompted for the root directory, enter the path to your backend code (e.g., `AIComplaintBackend/`).

2. **Configure Build and Start Commands:**  
   - **Build Command**:  
     If using Python, usually:
     ```
     pip install -r requirements.txt
     ```
   - **Start Command**:  
     This is the command that starts your backend service, such as:
     ```
     python AIApp/Facebook_data/scheduler.py
     ```
     or
     ```
     gunicorn app:app
     ```
     (Replace with your actual entry point.)

3. **Set Environment Variables:**  
   - Click **Advanced** > **Environment** and add your secrets (`MONGODB_URI`, `FACEBOOK_ACCESS_TOKEN`, etc.).
   - These variables will be available to your backend securely.

4. **Choose Region and Instance Type:**  
   - For testing, the free tier is fine. For production, you may want to upgrade.

5. **Create the Service:**  
   - Click **Create Web Service**. Render will build and deploy your backend.
   - You’ll get a public URL (e.g., `https://ai-complaint-backend.onrender.com`).

---

## Step 4: Deploy the Frontend (Static Site)

1. **Choose the Frontend Directory**  
   - When setting up, select the folder where your dashboard’s `index.html` (and other files) live.

2. **Set the Build Command:**  
   - If your frontend is pure HTML/CSS/JS, you likely don’t need a build command. If using React/Vue, it might be:
     ```
     npm install && npm run build
     ```
   - Output directory for most JS frameworks is typically `build/` or `dist/`.

3. **Set Environment Variables (If Needed):**  
   - For static sites, you usually don’t need these unless your frontend fetches secrets at build-time.

4. **Create the Static Site:**  
   - Click **Create Static Site**. Render will build and deploy your frontend.
   - Your admin dashboard will be available at a public URL (e.g., `https://ai-complaint-dashboard.onrender.com`).

---

## Step 5: Connecting Frontend and Backend

- **API Calls:**  
  Your frontend dashboard makes HTTP requests (using `fetch` or `axios`) to the backend API endpoints hosted on Render.
  - Example:
    ```js
    fetch('https://ai-complaint-backend.onrender.com/api/complaints')
      .then(response => response.json())
      .then(data => { /* display complaint data */ });
    ```

- **CORS:**  
  Make sure CORS (Cross-Origin Resource Sharing) is configured in your backend code to allow requests from your frontend’s URL. In Python (Flask/FastAPI), you can use packages like `flask-cors` or `fastapi.middleware.cors`.

---

## Step 6: Continuous Deployment

- Whenever you push updates to the GitHub repo, Render automatically rebuilds and redeploys your backend and frontend services.
- You can monitor build logs and service health/status from the Render dashboard.

---

## Step 7: Monitoring, Logs, and Scaling

- Render provides web logs, error logs, and resource usage stats.
- You can scale up your backend (more CPU/memory) or add background workers if needed.
- For production, always set up proper monitoring, error notifications, and consider backups for your MongoDB instance.

---

## How Render Works with This Project

In the AI Complaint System, Render acts as the cloud host for both the backend logic (Python scripts, API endpoints, background jobs) and the frontend dashboard (HTML/JS/CSS). The backend fetches, processes, and stores complaint data, exposing RESTful APIs. The frontend, served as a static site, interacts with these APIs to display live complaint data and analytics to administrators. Both services are deployed independently but remain connected through HTTP requests over the internet. Render handles SSL, environment variable management, scaling, and deployment automation, making it ideal for both prototyping and production use of full-stack applications like this one.

---

## Useful Links

- [Render Docs: Web Services](https://render.com/docs/web-services)
- [Render Docs: Static Sites](https://render.com/docs/static-sites)
- [Render Docs: Environment Variables](https://render.com/docs/environment-variables)
- [Render Docs: Python](https://render.com/docs/deploy-python)
- [Official Render Discord](https://render.com/community)
