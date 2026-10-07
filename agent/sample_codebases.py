"""
Sample Codebases for Demo & Evaluation
Provides 1-click sample projects for testing the AI Coding Agent.
"""

SAMPLE_PROJECTS = {
    "fastapi-user-api": {
        "id": "fastapi-user-api",
        "name": "FastAPI REST API with Missing Validation & Tests",
        "description": "A Python FastAPI user management API needing input validation, error handling, and unit tests.",
        "language": "Python",
        "suggested_task": "Add Pydantic input validation to user registration, add error handling for duplicate emails, and create a test_main.py with unit tests.",
        "files": {
            "main.py": '''"""FastAPI User Management API."""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="User Service API")

# In-memory database
db = {}

@app.post("/users")
def create_user(user_data: dict):
    # Missing proper schema validation and email uniqueness check!
    user_id = len(db) + 1
    db[user_id] = user_data
    return {"id": user_id, "status": "created", "data": user_data}

@app.get("/users/{user_id}")
def get_user(user_id: int):
    if user_id not in db:
        return {"error": "User not found"} # Should raise proper HTTPException!
    return db[user_id]

@app.get("/users")
def list_users():
    return list(db.values())
''',
            "models.py": '''"""User Models and Schemas."""

# TODO: Define proper Pydantic schemas for UserCreate, UserResponse, UserUpdate
class User:
    def __init__(self, id: int, name: str, email: str, role: str = "user"):
        self.id = id
        self.name = name
        self.email = email
        self.role = role
''',
            "utils.py": '''"""Helper utilities for User Service."""

def validate_email(email: str) -> bool:
    # Basic email validation logic
    return "@" in email and "." in email

def format_user_name(name: str) -> str:
    return name.strip().title()
'''
        }
    },
    "express-auth-service": {
        "id": "express-auth-service",
        "name": "Express.js Auth Service with Security Flaw",
        "description": "A Node.js authentication module missing password hashing validation and proper JWT error handling.",
        "language": "JavaScript",
        "suggested_task": "Add bcrypt password hashing validation, JWT token expiration check, and proper error middleware.",
        "files": {
            "auth.js": '''const express = require('express');
const router = express.Router();

const usersDB = [];

// Login route - SECURITY RISK: Plaintext password comparison!
router.post('/login', (req, res) => {
    const { email, password } = req.body;
    const user = usersDB.find(u => u.email === email);
    
    if (!user || user.password !== password) {
        return res.status(401).json({ message: "Invalid credentials" });
    }
    
    // Insecure token generation without expiration
    const token = "mock-jwt-token-" + user.id;
    res.json({ success: true, token });
});

router.post('/register', (req, res) => {
    const { name, email, password } = req.body;
    const newUser = { id: Date.now(), name, email, password };
    usersDB.push(newUser);
    res.status(201).json({ message: "Registered successfully" });
});

module.exports = router;
''',
            "jwtUtils.js": '''// JWT Helper module

function generateToken(user) {
    return `header.${btoa(JSON.stringify(user))}.signature`;
}

function verifyToken(token) {
    if (!token || !token.startsWith("header.")) {
        return null;
    }
    return true;
}

module.exports = { generateToken, verifyToken };
'''
        }
    },
    "python-data-processor": {
        "id": "python-data-processor",
        "name": "Python Data Pipeline (Needs Refactoring & Tests)",
        "description": "A data processing module with inefficient loops, missing docstrings, and zero error boundary.",
        "language": "Python",
        "suggested_task": "Refactor data processing to use list comprehensions, add type annotations, docstrings, and write a test suite.",
        "files": {
            "processor.py": '''# Data Processor Module

def process_records(records):
    results = []
    for r in records:
        if r.get('active') == True:
            val = r.get('val', 0)
            calc = val * 1.15
            results.append({
                'id': r.get('id'),
                'processed_val': round(calc, 2),
                'status': 'PROCESSED'
            })
    return results

def aggregate_stats(processed_records):
    total = 0
    count = 0
    for r in processed_records:
        total += r['processed_val']
        count += 1
    
    avg = total / count if count > 0 else 0
    return {"total": round(total, 2), "average": round(avg, 2), "count": count}
''',
            "test_processor.py": '''# Unit test stub for processor

import unittest
from processor import process_records, aggregate_stats

class TestDataProcessor(unittest.TestCase):

    def test_process_records_basic(self):
        sample = [{"id": 1, "val": 100, "active": True}]
        result = process_records(sample)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["processed_val"], 115.0)

if __name__ == '__main__':
    unittest.main()
'''
        }
    }
}
