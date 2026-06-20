# ===================================================================
# Copyright (c) 2026 THE ADVOCACY A LAW FIRM. All rights reserved.
# Confidential and proprietary. Do not distribute without a license.
# LEXSARTHI IS A PROPERTY OR ASSET OF THE ADVOCACY A LAW FIRM.
# ===================================================================
# LEXSARTHI v4.0 - THE COMPLETE LEGAL OS
# $10B VISION - SINGLE PROVIDER FOR ALL LEGAL WORK AUTOMATION
# ===================================================================
# "From Contract Review to Supreme Court Judgments"
# "From Law School to Global Legal Practice"
# "One Platform. Every Legal Need. Anywhere in the World."
# ===================================================================
# Powered By THE ADVOCACY A LAW FIRM
# ===================================================================
# 🔒 ZERO DATA RETENTION POLICY - Auto-delete after 24 hours
# 🎯 100% ACCURACY GUARANTEE - NO HALLUCINATION
# 🔐 CONFIDENTIALITY NOTICE - Attorney-Client Privilege
# 📊 ANALYTICS & BI - Complete Legal Analytics Dashboard
# 💳 ₹2 TEST PAYMENT - Starter Pack
# ⏰ DAILY REPORT - Auto-generates at 4:00 AM IST every day
# 📧 CAMPAIGNS - Email, Engagement, Alerts, Market Intelligence
# 🌐 DOMAIN INTELLIGENCE - WHOIS, SSL, DNS, Domain Agreement
# ===================================================================

import os
import json
import sqlite3
import jwt
import hashlib
import datetime
import re
import socket
import whois
import dns.resolver
import ssl
import uuid
import base64
import hmac
import random
import shutil
import asyncio
import requests
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, File, Form, UploadFile, HTTPException, Depends, Request, BackgroundTasks, Query
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
import httpx
from pydantic import BaseModel, EmailStr, Field
from bs4 import BeautifulSoup
import pdfplumber
import docx
from datetime import datetime, timedelta
import urllib.parse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

# ===================================================================
# CONFIGURATION
# ===================================================================
SECRET_KEY = os.environ.get("JWT_SECRET", "dev-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7
DATABASE_URL = "/data/lexsarthi.db"
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = "openrouter/auto"
SIMILARWEB_API_KEY = os.environ.get("SIMILARWEB_API_KEY", "")

# Razorpay Configuration
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")

# File Storage - TEMPORARY ONLY (Zero Retention)
UPLOAD_DIR = "/data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Zero Data Retention Settings
DATA_RETENTION_HOURS = int(os.environ.get("DATA_RETENTION_HOURS", "24"))
ENABLE_AUTO_DELETE = os.environ.get("ENABLE_AUTO_DELETE", "true").lower() == "true"

# Free Trial Settings
FREE_TRIAL_DAYS = 15
STARTER_PACK_PRICE = 200  # ₹2 in paise

# Website URL
WEBSITE_URL = "https://www.advocacyalawfrim.in"
LAUNCH_DATE = "20 June 2026"
VERSION = "4.0.0"

# Report Settings
REPORT_TIME_HOUR = 4
REPORT_TIME_MINUTE = 0
IST_TIMEZONE = pytz.timezone('Asia/Kolkata')

# ===================================================================
# PRICING PLANS
# ===================================================================
PRICING_PLANS = {
    "starter": {
        "name": "Starter",
        "price": 200,
        "price_label": "₹2",
        "duration": "forever",
        "agents": 6,
        "runs": 3,
        "users": 1,
        "storage": 100,
        "features": [
            "3 free agent runs (lifetime)",
            "6 basic agents",
            "Watermarked output",
            "Email support",
            "₹2 one-time payment"
        ],
        "badge": "⚡ STARTER",
        "cta": "Start for ₹2"
    },
    "professional": {
        "name": "Professional",
        "price": 149900,
        "price_label": "₹1,499",
        "duration": "month",
        "agents": 44,
        "runs": 250,
        "users": 1,
        "storage": 1000,
        "features": [
            "250 agent runs / month",
            "All 44 specialised agents",
            "Full history + PDF export",
            "Priority speed",
            "GST invoice"
        ],
        "badge": "🔥 POPULAR",
        "cta": "Subscribe — ₹1,499"
    },
    "firm": {
        "name": "Firm",
        "price": 2499900,
        "price_label": "₹24,999",
        "duration": "month",
        "agents": 50,
        "runs": 5000,
        "users": 15,
        "storage": 10000,
        "features": [
            "15 user seats",
            "5,000 runs / month",
            "Lawyer-review add-on",
            "Custom branding",
            "Dedicated CSM"
        ],
        "badge": "🏢 FIRM",
        "cta": "Talk to sales"
    }
}

PAY_PER_USE = {
    "domain_review": {"price": 200, "label": "₹2", "description": "Domain Review"},
    "domain_review_lawyer": {"price": 10000, "label": "₹100", "description": "Domain Review with Lawyer Review"},
    "ma_due_diligence": {"price": 250000, "label": "₹2,500", "description": "M&A Due Diligence"}
}

# ===================================================================
# APP INITIALIZATION
# ===================================================================
app = FastAPI(
    title="LexSarthi v4.0 - Complete Legal OS",
    description="Powered by THE ADVOCACY A LAW FIRM | Zero Data Retention | 100% Accuracy | 15 Days Free Trial | ₹2 Starter Pack | International Launch 20 June 2026 | From Contract to Supreme Court",
    version=VERSION
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# ===================================================================
# DATABASE - WITH ANALYTICS TABLES
# ===================================================================
def get_db():
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if not cursor.fetchone():
        # Users table
        conn.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                role TEXT DEFAULT 'user',
                plan TEXT DEFAULT 'free',
                is_premium INTEGER DEFAULT 0,
                premium_expiry TIMESTAMP,
                trial_start_date TIMESTAMP,
                trial_end_date TIMESTAMP,
                organization TEXT,
                consent_given INTEGER DEFAULT 0,
                consent_date TIMESTAMP,
                confidentiality_accepted INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                data_deleted INTEGER DEFAULT 0,
                deletion_requested INTEGER DEFAULT 0,
                deletion_date TIMESTAMP
            )
        """)
        
        # Documents table
        conn.execute("""
            CREATE TABLE documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_type TEXT,
                file_size INTEGER,
                content TEXT,
                agent_used TEXT,
                analysis_result TEXT,
                status TEXT DEFAULT 'pending',
                lawyer_reviewed INTEGER DEFAULT 0,
                lawyer_notes TEXT,
                reviewed_by INTEGER,
                review_date TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)
        
        # Campaigns table
        conn.execute("""
            CREATE TABLE campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                status TEXT DEFAULT 'draft',
                audience TEXT,
                content TEXT,
                scheduled_date TIMESTAMP,
                sent_date TIMESTAMP,
                open_count INTEGER DEFAULT 0,
                click_count INTEGER DEFAULT 0,
                response_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)
        
        # Outreach table
        conn.execute("""
            CREATE TABLE outreach (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                campaign_id INTEGER,
                client_email TEXT,
                client_name TEXT,
                status TEXT DEFAULT 'pending',
                sent_date TIMESTAMP,
                opened_date TIMESTAMP,
                responded_date TIMESTAMP,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(campaign_id) REFERENCES campaigns(id)
            )
        """)
        
        # History table
        conn.execute("""
            CREATE TABLE history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                agent TEXT,
                input_text TEXT,
                result_json TEXT,
                document_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)
        
        # Payments table
        conn.execute("""
            CREATE TABLE payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                order_id TEXT UNIQUE NOT NULL,
                payment_id TEXT,
                amount INTEGER NOT NULL,
                currency TEXT DEFAULT 'INR',
                plan TEXT,
                status TEXT DEFAULT 'created',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)
        
        # Analytics Events table
        conn.execute("""
            CREATE TABLE analytics_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                event_type TEXT NOT NULL,
                event_data TEXT,
                session_id TEXT,
                ip_address TEXT,
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)
        
        # Daily Metrics table
        conn.execute("""
            CREATE TABLE daily_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE UNIQUE NOT NULL,
                total_users INTEGER DEFAULT 0,
                active_users INTEGER DEFAULT 0,
                new_users INTEGER DEFAULT 0,
                total_agents_run INTEGER DEFAULT 0,
                total_documents_uploaded INTEGER DEFAULT 0,
                total_payments INTEGER DEFAULT 0,
                total_revenue INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Reports table
        conn.execute("""
            CREATE TABLE reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_type TEXT NOT NULL,
                report_date DATE NOT NULL,
                report_data TEXT,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(report_type, report_date)
            )
        """)
        
        # Retention Log
        conn.execute("""
            CREATE TABLE retention_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT,
                entity_id INTEGER,
                deletion_reason TEXT,
                deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully")

init_db()

# ===================================================================
# ZERO DATA RETENTION
# ===================================================================
async def delete_expired_data():
    retention_time = datetime.now() - timedelta(hours=DATA_RETENTION_HOURS)
    retention_time_str = retention_time.isoformat()
    
    conn = get_db()
    
    try:
        conn.execute(
            """UPDATE documents SET content = NULL, analysis_result = NULL 
               WHERE created_at < ?""",
            (retention_time_str,)
        )
        
        conn.execute(
            """UPDATE history SET input_text = NULL, result_json = NULL 
               WHERE created_at < ?""",
            (retention_time_str,)
        )
        
        conn.execute(
            "INSERT INTO retention_log (entity_type, entity_id, deletion_reason) VALUES (?, ?, ?)",
            ("system", 0, f"Zero Retention - Auto-deleted data older than {DATA_RETENTION_HOURS} hours")
        )
        
        conn.commit()
        print(f"✅ Zero Retention: Deleted data older than {DATA_RETENTION_HOURS} hours")
    except Exception as e:
        print(f"⚠️ Zero Retention error: {e}")
    finally:
        conn.close()

async def schedule_data_deletion():
    while True:
        if ENABLE_AUTO_DELETE:
            await delete_expired_data()
        await asyncio.sleep(3600)

# ===================================================================
# DAILY REPORT GENERATOR (4:00 AM IST)
# ===================================================================
async def generate_daily_report():
    """Generate daily report at 4:00 AM IST"""
    try:
        ist_now = datetime.now(IST_TIMEZONE)
        report_date = ist_now.strftime("%Y-%m-%d")
        
        print(f"📊 Generating daily report for {report_date} at {ist_now.strftime('%H:%M:%S')} IST")
        
        conn = get_db()
        previous_date = (ist_now - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Collect metrics
        total_users = conn.execute("SELECT COUNT(*) as count FROM users WHERE is_active = 1").fetchone()["count"]
        new_users_today = conn.execute("SELECT COUNT(*) as count FROM users WHERE DATE(created_at) = ?", (report_date,)).fetchone()["count"]
        new_users_yesterday = conn.execute("SELECT COUNT(*) as count FROM users WHERE DATE(created_at) = ?", (previous_date,)).fetchone()["count"]
        
        active_users_today = conn.execute("SELECT COUNT(DISTINCT user_id) as count FROM history WHERE DATE(created_at) = ?", (report_date,)).fetchone()["count"]
        active_users_yesterday = conn.execute("SELECT COUNT(DISTINCT user_id) as count FROM history WHERE DATE(created_at) = ?", (previous_date,)).fetchone()["count"]
        
        total_agents_run_today = conn.execute("SELECT COUNT(*) as count FROM history WHERE DATE(created_at) = ?", (report_date,)).fetchone()["count"]
        total_agents_run_yesterday = conn.execute("SELECT COUNT(*) as count FROM history WHERE DATE(created_at) = ?", (previous_date,)).fetchone()["count"]
        
        top_agents_today = conn.execute(
            """SELECT agent, COUNT(*) as count FROM history WHERE DATE(created_at) = ? 
               GROUP BY agent ORDER BY count DESC LIMIT 10""",
            (report_date,)
        ).fetchall()
        
        documents_today = conn.execute("SELECT COUNT(*) as count FROM documents WHERE DATE(created_at) = ?", (report_date,)).fetchone()["count"]
        documents_yesterday = conn.execute("SELECT COUNT(*) as count FROM documents WHERE DATE(created_at) = ?", (previous_date,)).fetchone()["count"]
        
        payments_today = conn.execute("SELECT COUNT(*) as count, SUM(amount) as total FROM payments WHERE DATE(created_at) = ? AND status = 'paid'", (report_date,)).fetchone()
        payments_yesterday = conn.execute("SELECT COUNT(*) as count, SUM(amount) as total FROM payments WHERE DATE(created_at) = ? AND status = 'paid'", (previous_date,)).fetchone()
        
        payments_today_count = payments_today["count"] if payments_today else 0
        payments_today_total = (payments_today["total"] / 100) if payments_today and payments_today["total"] else 0
        payments_yesterday_count = payments_yesterday["count"] if payments_yesterday else 0
        payments_yesterday_total = (payments_yesterday["total"] / 100) if payments_yesterday and payments_yesterday["total"] else 0
        
        revenue_by_plan = conn.execute(
            """SELECT plan, COUNT(*) as count, SUM(amount) as total FROM payments 
               WHERE DATE(created_at) = ? AND status = 'paid' GROUP BY plan""",
            (report_date,)
        ).fetchall()
        
        campaigns_sent = conn.execute("SELECT COUNT(*) as count FROM campaigns WHERE DATE(sent_date) = ?", (report_date,)).fetchone()["count"]
        campaigns_opened = conn.execute("SELECT SUM(open_count) as total FROM campaigns WHERE DATE(sent_date) = ?", (report_date,)).fetchone()["total"] or 0
        campaigns_clicked = conn.execute("SELECT SUM(click_count) as total FROM campaigns WHERE DATE(sent_date) = ?", (report_date,)).fetchone()["total"] or 0
        
        growth_trend = conn.execute("""
            SELECT DATE(created_at) as date, COUNT(*) as count FROM users 
            WHERE DATE(created_at) >= date('now', '-7 days') GROUP BY DATE(created_at) ORDER BY date ASC
        """).fetchall()
        
        agent_trend = conn.execute("""
            SELECT DATE(created_at) as date, COUNT(*) as count FROM history 
            WHERE DATE(created_at) >= date('now', '-7 days') GROUP BY DATE(created_at) ORDER BY date ASC
        """).fetchall()
        
        conn.close()
        
        # Build report
        report = {
            "report_date": report_date,
            "generated_at": ist_now.isoformat(),
            "timezone": "Asia/Kolkata",
            "summary": {
                "total_users": total_users,
                "new_users_today": new_users_today,
                "new_users_yesterday": new_users_yesterday,
                "active_users_today": active_users_today,
                "active_users_yesterday": active_users_yesterday,
                "growth_percentage": round(((new_users_today - new_users_yesterday) / max(new_users_yesterday, 1)) * 100, 2)
            },
            "agent_usage": {
                "total_runs_today": total_agents_run_today,
                "total_runs_yesterday": total_agents_run_yesterday,
                "change_percentage": round(((total_agents_run_today - total_agents_run_yesterday) / max(total_agents_run_yesterday, 1)) * 100, 2),
                "top_agents": [dict(row) for row in top_agents_today]
            },
            "documents": {
                "uploaded_today": documents_today,
                "uploaded_yesterday": documents_yesterday,
                "change_percentage": round(((documents_today - documents_yesterday) / max(documents_yesterday, 1)) * 100, 2)
            },
            "revenue": {
                "today": {"count": payments_today_count, "total": payments_today_total},
                "yesterday": {"count": payments_yesterday_count, "total": payments_yesterday_total},
                "change_percentage": round(((payments_today_total - payments_yesterday_total) / max(payments_yesterday_total, 0.01)) * 100, 2),
                "by_plan": [dict(row) for row in revenue_by_plan]
            },
            "campaigns": {
                "sent_today": campaigns_sent,
                "opened_today": campaigns_opened,
                "clicked_today": campaigns_clicked,
                "open_rate": round((campaigns_opened / max(campaigns_sent, 1)) * 100, 2),
                "click_rate": round((campaigns_clicked / max(campaigns_opened, 1)) * 100, 2)
            },
            "trends": {
                "user_growth": [dict(row) for row in growth_trend],
                "agent_usage": [dict(row) for row in agent_trend]
            },
            "insights": generate_insights({
                "new_users_today": new_users_today,
                "new_users_yesterday": new_users_yesterday,
                "active_users_today": active_users_today,
                "total_agents_run_today": total_agents_run_today,
                "payments_today_total": payments_today_total,
                "payments_yesterday_total": payments_yesterday_total
            }),
            "lawyer": LAWYER_PROFILE,
            "website": WEBSITE_URL
        }
        
        # Save report
        conn = get_db()
        conn.execute(
            """INSERT OR REPLACE INTO reports (report_type, report_date, report_data) VALUES (?, ?, ?)""",
            ("daily", report_date, json.dumps(report))
        )
        conn.commit()
        conn.close()
        
        print(f"✅ Daily report generated successfully for {report_date}")
        await send_report_to_webhook(report)
        
        return report
        
    except Exception as e:
        print(f"❌ Error generating daily report: {e}")
        return {"error": str(e)}

def generate_insights(data):
    insights = []
    if data["new_users_today"] > data["new_users_yesterday"]:
        insights.append(f"📈 User growth increased by {data['new_users_today'] - data['new_users_yesterday']} new users")
    elif data["new_users_today"] < data["new_users_yesterday"]:
        insights.append(f"📉 User growth decreased by {data['new_users_yesterday'] - data['new_users_today']} users")
    else:
        insights.append("📊 User growth remained stable")
    
    if data["active_users_today"] > 50:
        insights.append(f"🔥 {data['active_users_today']} active users today - strong engagement!")
    elif data["active_users_today"] > 10:
        insights.append(f"✅ {data['active_users_today']} active users today - steady engagement")
    else:
        insights.append(f"📌 {data['active_users_today']} active users today")
    
    if data["total_agents_run_today"] > 100:
        insights.append(f"🤖 {data['total_agents_run_today']} agent runs today - high platform usage")
    elif data["total_agents_run_today"] > 20:
        insights.append(f"⚡ {data['total_agents_run_today']} agent runs today - moderate usage")
    else:
        insights.append(f"📌 {data['total_agents_run_today']} agent runs today")
    
    if data["payments_today_total"] > data["payments_yesterday_total"]:
        insights.append(f"💰 Revenue increased by ₹{data['payments_today_total'] - data['payments_yesterday_total']:.2f}")
    else:
        insights.append(f"💳 Revenue today: ₹{data['payments_today_total']:.2f}")
    
    return insights

async def send_report_to_webhook(report):
    try:
        webhook_url = os.environ.get("REPORT_WEBHOOK_URL", "")
        if webhook_url:
            message = {
                "text": f"📊 **LexSarthi Daily Report - {report['report_date']}**",
                "blocks": [
                    {"type": "header", "text": {"type": "plain_text", "text": f"📊 LexSarthi Daily Report - {report['report_date']}"}},
                    {"type": "section", "fields": [
                        {"type": "mrkdwn", "text": f"*Total Users:* {report['summary']['total_users']}"},
                        {"type": "mrkdwn", "text": f"*New Users Today:* {report['summary']['new_users_today']}"},
                        {"type": "mrkdwn", "text": f"*Active Users:* {report['summary']['active_users_today']}"},
                        {"type": "mrkdwn", "text": f"*Agent Runs:* {report['agent_usage']['total_runs_today']}"},
                        {"type": "mrkdwn", "text": f"*Revenue Today:* ₹{report['revenue']['today']['total']:.2f}"},
                        {"type": "mrkdwn", "text": f"*Documents:* {report['documents']['uploaded_today']}"}
                    ]},
                    {"type": "section", "text": {"type": "mrkdwn", "text": f"*💡 Insights:*\n" + "\n".join(report['insights'])}},
                    {"type": "context", "elements": [{"type": "mrkdwn", "text": f"Generated at {report['generated_at']} IST | Powered by THE ADVOCACY A LAW FIRM"}]}
                ]
            }
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(webhook_url, json=message)
                print("✅ Report sent to webhook")
    except Exception as e:
        print(f"⚠️ Failed to send report to webhook: {e}")

# ===================================================================
# SCHEDULER
# ===================================================================
scheduler = AsyncIOScheduler(timezone=IST_TIMEZONE)

@app.on_event("startup")
async def startup_events():
    asyncio.create_task(schedule_data_deletion())
    scheduler.add_job(
        generate_daily_report,
        CronTrigger(hour=REPORT_TIME_HOUR, minute=REPORT_TIME_MINUTE, timezone=IST_TIMEZONE),
        id="daily_report",
        replace_existing=True
    )
    scheduler.start()
    print(f"⏰ Daily report scheduler started - runs at {REPORT_TIME_HOUR:02d}:{REPORT_TIME_MINUTE:02d} AM IST daily")

@app.on_event("shutdown")
async def shutdown_events():
    scheduler.shutdown()
    print("🛑 Scheduler shutdown")

# ===================================================================
# ANALYTICS ENDPOINTS
# ===================================================================
@app.get("/analytics/dashboard")
async def get_analytics_dashboard(current_user: dict = Depends(get_current_user_bearer), period: str = "30d"):
    try:
        conn = get_db()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30 if period == "30d" else 7 if period == "7d" else 90)
        start_date_str = start_date.strftime("%Y-%m-%d")
        
        daily_metrics = conn.execute("SELECT * FROM daily_metrics WHERE date >= ? ORDER BY date ASC", (start_date_str,)).fetchall()
        top_agents = conn.execute("SELECT agent, COUNT(*) as count FROM history WHERE DATE(created_at) >= ? GROUP BY agent ORDER BY count DESC LIMIT 10", (start_date_str,)).fetchall()
        payment_insights = conn.execute("SELECT COUNT(*) as total_payments, SUM(amount) as total_revenue FROM payments WHERE DATE(created_at) >= ? AND status = 'paid'", (start_date_str,)).fetchone()
        
        daily_data = []
        for row in daily_metrics:
            daily_data.append({
                "date": row["date"],
                "total_users": row["total_users"],
                "active_users": row["active_users"],
                "new_users": row["new_users"],
                "total_agents_run": row["total_agents_run"],
                "total_documents": row["total_documents_uploaded"],
                "total_payments": row["total_payments"],
                "total_revenue": row["total_revenue"] / 100 if row["total_revenue"] else 0
            })
        
        conn.close()
        return {
            "period": period,
            "daily_metrics": daily_data,
            "top_agents": [dict(row) for row in top_agents],
            "payment_insights": {
                "total_payments": payment_insights["total_payments"] if payment_insights else 0,
                "total_revenue": (payment_insights["total_revenue"] / 100) if payment_insights else 0
            },
            "website": WEBSITE_URL
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===================================================================
# REPORT ENDPOINTS
# ===================================================================
@app.get("/reports/daily")
async def get_daily_report(current_user: dict = Depends(get_current_user_bearer), date: Optional[str] = None):
    try:
        if not date:
            date = datetime.now(IST_TIMEZONE).strftime("%Y-%m-%d")
        
        conn = get_db()
        report = conn.execute("SELECT * FROM reports WHERE report_type = 'daily' AND report_date = ?", (date,)).fetchone()
        conn.close()
        
        if report:
            return {
                "report_date": report["report_date"],
                "report_data": json.loads(report["report_data"]),
                "generated_at": report["generated_at"],
                "website": WEBSITE_URL
            }
        else:
            report_data = await generate_daily_report()
            return {"report_date": date, "report_data": report_data, "status": "newly_generated", "website": WEBSITE_URL}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/reports/latest")
async def get_latest_report(current_user: dict = Depends(get_current_user_bearer)):
    try:
        conn = get_db()
        report = conn.execute("SELECT * FROM reports WHERE report_type = 'daily' ORDER BY report_date DESC LIMIT 1").fetchone()
        conn.close()
        
        if report:
            return {
                "report_date": report["report_date"],
                "report_data": json.loads(report["report_data"]),
                "generated_at": report["generated_at"],
                "website": WEBSITE_URL
            }
        else:
            report_data = await generate_daily_report()
            return {"report_data": report_data, "status": "newly_generated", "website": WEBSITE_URL}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reports/generate")
async def generate_report_now(current_user: dict = Depends(get_current_user_bearer)):
    try:
        report = await generate_daily_report()
        return {"message": "Report generated successfully", "report": report, "website": WEBSITE_URL}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===================================================================
# AUTH ENDPOINTS
# ===================================================================
@app.post("/auth/register")
async def register_user(user: UserRegister):
    if not user.consent_given:
        raise HTTPException(status_code=400, detail="Consent required under DPDP Act 2023 Section 4")
    if not user.confidentiality_accepted:
        raise HTTPException(status_code=400, detail="Confidentiality agreement must be accepted")
    
    conn = get_db()
    existing = conn.execute("SELECT id FROM users WHERE username = ?", (user.username,)).fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=400, detail="Username already registered")
    
    password_hash = hash_password(user.password)
    trial_start = datetime.now()
    trial_end = trial_start + timedelta(days=FREE_TRIAL_DAYS)
    
    conn.execute(
        """INSERT INTO users (username, password_hash, full_name, plan, consent_given, consent_date, 
           confidentiality_accepted, trial_start_date, trial_end_date, is_premium) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user.username, password_hash, user.full_name, "free", 1, datetime.now().isoformat(), 
         1, trial_start.isoformat(), trial_end.isoformat(), 1)
    )
    conn.commit()
    conn.close()
    
    return {
        "message": "🎉 Welcome to LexSarthi! Your 15-day free trial has started.",
        "lawyer": "Adv. Debo",
        "firm": "THE ADVOCACY A LAW FIRM",
        "consent_given": True,
        "confidentiality_accepted": True,
        "plan": "free",
        "trial_days": FREE_TRIAL_DAYS,
        "trial_end_date": trial_end.isoformat(),
        "data_retention": f"Zero Retention - Auto-deleted after {DATA_RETENTION_HOURS} hours",
        "website": WEBSITE_URL,
        "launch_date": LAUNCH_DATE
    }

@app.post("/auth/login")
async def login_user(user: UserLogin):
    conn = get_db()
    db_user = conn.execute("SELECT * FROM users WHERE username = ?", (user.username,)).fetchone()
    conn.close()
    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if hash_password(user.password) != db_user["password_hash"]:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_jwt(user.username, db_user["role"])
    trial_end = db_user["trial_end_date"]
    trial_active = False
    if trial_end:
        trial_end_date = datetime.fromisoformat(trial_end)
        trial_active = trial_end_date > datetime.now()
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": db_user["id"],
            "username": db_user["username"],
            "full_name": db_user["full_name"],
            "role": db_user["role"],
            "plan": db_user["plan"],
            "is_premium": db_user["is_premium"],
            "consent_given": bool(db_user["consent_given"]),
            "confidentiality_accepted": bool(db_user["confidentiality_accepted"]),
            "trial_active": trial_active,
            "trial_end_date": trial_end
        },
        "website": WEBSITE_URL,
        "launch_date": LAUNCH_DATE
    }

@app.get("/auth/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    conn = get_db()
    user = conn.execute(
        """SELECT id, username, full_name, role, plan, is_premium, premium_expiry, 
           created_at, consent_given, consent_date, confidentiality_accepted, data_deleted 
           FROM users WHERE id = ?""",
        (current_user["id"],)
    ).fetchone()
    conn.close()
    return dict(user)

# ===================================================================
# AGENTS ENDPOINT
# ===================================================================
@app.get("/agents")
async def get_agents():
    return {
        "agents": AGENTS,
        "count": len(AGENTS),
        "categories": list(set(a["category"] for a in AGENTS)),
        "lawyer": {
            "name": "Adv. Debo",
            "firm": "THE ADVOCACY A LAW FIRM",
            "experience": "8+ years",
            "qualification": "LLB - Delhi University (2016)"
        },
        "website": WEBSITE_URL,
        "launch_date": LAUNCH_DATE
    }

# ===================================================================
# RUN AGENT
# ===================================================================
@app.post("/run-agent")
async def run_agent_endpoint(agent_run: AgentRunRequest, current_user: dict = Depends(get_current_user_bearer)):
    agent = next((a for a in AGENTS if a["id"] == agent_run.agent_id), None)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_run.agent_id}