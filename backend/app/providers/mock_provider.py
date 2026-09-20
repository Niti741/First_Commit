import asyncio
import hashlib
import math
import re
import time
from typing import List, Dict, Any, Optional, AsyncIterator
import numpy as np

from backend.app.providers.base import LLMProvider, ProviderResponse, ProviderUsage, JudgeResult


class MockProvider(LLMProvider):
    """
    Offline deterministic mock provider for testing and local development.
    Requires ZERO external API keys. Simulates:
    - Accurate handbook factual generation
    - Hinglish & English natural answers
    - Streaming SSE token emission
    - 384-dimensional semantic embeddings with cosine similarity
    - Structured judge evaluation
    """

    def __init__(self, handbook_text: str = ""):
        self.handbook_text = handbook_text
        self.embedding_dim = 384

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def supports_prompt_caching(self) -> bool:
        return True

    def _estimate_tokens(self, text: str) -> int:
        return max(1, len(text.split()) * 4 // 3)

    def _generate_synthetic_answer(self, question: str, is_hinglish: bool) -> str:
        q_lower = question.lower()

        # --- 1. Normal Conversation & Greetings ---
        if any(w == q_lower.strip().replace("?", "").replace("!", "").replace(".", "") for w in [
            "hi", "hello", "hey", "namaste", "namaskar", "kese ho", "kaise ho", "kya haal hai", "kya haal", "kem cho"
        ]) or any(q_lower.startswith(g) for g in ["hi ", "hello ", "hey ", "namaste ", "good morning", "good evening", "good afternoon"]):
            if is_hinglish:
                return "Namaste! Main Kifayat AI hoon—aapka intelligent assistant. Main coding (HTML, CSS, JS, Python), general questions, reasoning aur college helpdesk sabhi mein aapki madad kar sakta hoon. Bataiye aaj hum kis par kaam karein?"
            return "Hello! I am Kifayat AI, your versatile intelligent assistant. I can assist you with web development (HTML, CSS, JS), programming, mathematics, technical explanations, or general inquiries. What would you like to build or explore today?"

        if any(w in q_lower for w in ["how are you", "kaise ho", "kaisa hai", "kya chal raha", "all good", "sab theek", "kya haal"]):
            if is_hinglish:
                return "Main bilkul badhiya hoon, shukriya! Aap bataiye, aaj coding, web design ya kisi technical topic par kya explore karna chahte hain?"
            return "I'm doing great, thank you! Ready to help you with coding, architecture, or any questions you have today."

        if any(w in q_lower for w in ["who are you", "what can you do", "tum kaun ho", "introduce yourself", "about yourself", "who made you", "kisne banaya"]):
            if is_hinglish:
                return (
                    "Main **Kifayat AI** hoon—ek high-performance, context-optimized AI assistant!\n\n"
                    "**Main in cheezon mein master hoon:**\n"
                    "- 💻 **Interactive Coding:** HTML, CSS, JavaScript web components aur Python apps jo direct Canvas mein live render hote hain.\n"
                    "- ⚡ **Context Optimization:** Enterprise-grade caching, token reduction aur fast responses.\n"
                    "- 🌐 **Fluent Bilingual:** English aur natural Hinglish dono mein conversation.\n"
                    "- 🧠 **Reasoning & Problem Solving:** Algorithms, mathematics, technical explanations aur debugging."
                )
            return (
                "I am **Kifayat AI**—a state-of-the-art context-optimized AI assistant.\n\n"
                "**Core Capabilities:**\n"
                "- 💻 **Interactive Web Development:** HTML5, CSS3, modern JavaScript with live Canvas rendering.\n"
                "- 🐍 **Full-Stack & Backend:** Python, FastAPI, Pydantic, data structures, and algorithms.\n"
                "- ⚡ **Intelligent Gateway:** Real-time token caching, automated prompt repair, and low-latency SSE streaming.\n"
                "- 🌐 **Natural Bilingual Communication:** Flawless English and natural Hinglish support."
            )

        if any(w in q_lower for w in ["joke", "chutkula", "funny"]):
            if is_hinglish:
                return (
                    "Ek developer joke suniye:\n\n"
                    "**Why do programmers prefer dark mode?**\n"
                    "*Because light attracts bugs!* 🐛😂\n\n"
                    "Aapko kisi programming concept ya web widget par help chahiye?"
                )
            return (
                "Here's a developer joke for you:\n\n"
                "**Why do programmers prefer dark mode?**\n"
                "*Because light attracts bugs!* 🐛💻\n\n"
                "How can I assist your coding journey today?"
            )

        if any(w in q_lower for w in ["thank", "shukriya", "dhanyawad", "thanks"]):
            if is_hinglish:
                return "Aapka swagat hai! Agar koi aur sawal ya coding me help chahiye toh zaroor batayein."
            return "You're very welcome! Feel free to ask if you need anything else—happy to help."

        if any(w in q_lower for w in ["bye", "goodbye", "alvida", "see you"]):
            if is_hinglish:
                return "Alvida! Phir milte hain. Have a productive day ahead!"
            return "Goodbye! Have a fantastic and productive day ahead. Reach out anytime you need assistance."

        # --- 2. HTML / CSS / JS Coding Requests (Interactive Artifacts for Canvas) ---
        is_html_request = any(w in q_lower for w in ["html", "css", "js", "javascript", "web", "frontend", "ui", "component", "canvas"])
        
        # 2.1 3D Glowing Card
        if any(w in q_lower for w in ["card", "gradient card", "3d card"]) or (is_html_request and "glow" in q_lower):
            return (
                "Here is an interactive 3D Gradient Glowing Card crafted with modern HTML and CSS. You can click **✨ Open in Canvas** to preview and interact with it live:\n\n"
                "```html\n"
                "<!DOCTYPE html>\n"
                "<html lang=\"en\">\n"
                "<head>\n"
                "  <meta charset=\"UTF-8\">\n"
                "  <style>\n"
                "    body {\n"
                "      margin: 0;\n"
                "      min-height: 100vh;\n"
                "      display: flex;\n"
                "      justify-content: center;\n"
                "      align-items: center;\n"
                "      background: radial-gradient(circle at 50% 50%, #0f172a 0%, #020617 100%);\n"
                "      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;\n"
                "      color: #f8fafc;\n"
                "    }\n"
                "    .card {\n"
                "      position: relative;\n"
                "      width: 320px;\n"
                "      padding: 2.2rem 1.8rem;\n"
                "      background: rgba(30, 41, 59, 0.7);\n"
                "      border-radius: 20px;\n"
                "      backdrop-filter: blur(16px);\n"
                "      border: 1px solid rgba(255, 255, 255, 0.12);\n"
                "      box-shadow: 0 20px 40px -15px rgba(99, 102, 241, 0.25);\n"
                "      transition: transform 0.35s cubic-bezier(0.175, 0.885, 0.32, 1.275), box-shadow 0.35s ease;\n"
                "      cursor: pointer;\n"
                "    }\n"
                "    .card:hover {\n"
                "      transform: translateY(-8px) scale(1.02);\n"
                "      box-shadow: 0 25px 50px -10px rgba(99, 102, 241, 0.45), 0 0 20px rgba(16, 185, 129, 0.3);\n"
                "      border-color: rgba(99, 102, 241, 0.4);\n"
                "    }\n"
                "    .badge {\n"
                "      display: inline-block;\n"
                "      padding: 0.3rem 0.75rem;\n"
                "      border-radius: 999px;\n"
                "      background: linear-gradient(135deg, #6366f1, #10b981);\n"
                "      font-size: 0.72rem;\n"
                "      font-weight: 700;\n"
                "      text-transform: uppercase;\n"
                "      letter-spacing: 0.05em;\n"
                "      margin-bottom: 1rem;\n"
                "    }\n"
                "    .card h2 {\n"
                "      margin: 0 0 0.5rem 0;\n"
                "      font-size: 1.4rem;\n"
                "      background: linear-gradient(135deg, #ffffff 30%, #cbd5e1 100%);\n"
                "      -webkit-background-clip: text;\n"
                "      -webkit-text-fill-color: transparent;\n"
                "    }\n"
                "    .card p {\n"
                "      color: #94a3b8;\n"
                "      font-size: 0.88rem;\n"
                "      line-height: 1.5;\n"
                "      margin: 0 0 1.5rem 0;\n"
                "    }\n"
                "    .btn-action {\n"
                "      display: block;\n"
                "      width: 100%;\n"
                "      padding: 0.75rem;\n"
                "      border: none;\n"
                "      border-radius: 12px;\n"
                "      background: linear-gradient(135deg, #4f46e5 0%, #3730a3 100%);\n"
                "      color: white;\n"
                "      font-weight: 600;\n"
                "      cursor: pointer;\n"
                "      transition: filter 0.2s;\n"
                "    }\n"
                "    .btn-action:hover { filter: brightness(1.15); }\n"
                "  </style>\n"
                "</head>\n"
                "<body>\n"
                "  <div class=\"card\" onclick=\"alert('Interactive Card Clicked!')\">\n"
                "    <span class=\"badge\">Interactive</span>\n"
                "    <h2>Kifayat Quantum UI</h2>\n"
                "    <p>Modern glassmorphic card with smooth 3D hover physics and ambient blur backdrop.</p>\n"
                "    <button class=\"btn-action\">Click to Test</button>\n"
                "  </div>\n"
                "</body>\n"
                "</html>\n"
                "```\n"
            )

        # 2.2 Interactive Counter App
        if any(w in q_lower for w in ["counter", "increment", "clicker"]) or (is_html_request and "count" in q_lower):
            return (
                "Here is an interactive Counter Web App with increment, decrement, and reset actions. Click **✨ Open in Canvas** to test it directly:\n\n"
                "```html\n"
                "<!DOCTYPE html>\n"
                "<html lang=\"en\">\n"
                "<head>\n"
                "  <meta charset=\"UTF-8\">\n"
                "  <style>\n"
                "    body {\n"
                "      margin: 0;\n"
                "      min-height: 100vh;\n"
                "      display: flex;\n"
                "      flex-direction: column;\n"
                "      justify-content: center;\n"
                "      align-items: center;\n"
                "      background: #0f172a;\n"
                "      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;\n"
                "      color: #f8fafc;\n"
                "    }\n"
                "    .counter-box {\n"
                "      background: #1e293b;\n"
                "      padding: 2.5rem 3rem;\n"
                "      border-radius: 20px;\n"
                "      border: 1px solid #334155;\n"
                "      text-align: center;\n"
                "      box-shadow: 0 10px 30px rgba(0,0,0,0.4);\n"
                "    }\n"
                "    .count-display {\n"
                "      font-size: 4rem;\n"
                "      font-weight: 800;\n"
                "      color: #38bdf8;\n"
                "      margin: 1rem 0;\n"
                "      transition: transform 0.15s ease;\n"
                "    }\n"
                "    .btn-group {\n"
                "      display: flex;\n"
                "      gap: 0.75rem;\n"
                "      justify-content: center;\n"
                "    }\n"
                "    button {\n"
                "      padding: 0.75rem 1.25rem;\n"
                "      font-size: 1.1rem;\n"
                "      font-weight: 700;\n"
                "      border: none;\n"
                "      border-radius: 10px;\n"
                "      cursor: pointer;\n"
                "      transition: all 0.2s;\n"
                "    }\n"
                "    .btn-dec { background: #ef4444; color: white; }\n"
                "    .btn-reset { background: #64748b; color: white; }\n"
                "    .btn-inc { background: #10b981; color: white; }\n"
                "    button:hover { transform: scale(1.08); filter: brightness(1.1); }\n"
                "  </style>\n"
                "</head>\n"
                "<body>\n"
                "  <div class=\"counter-box\">\n"
                "    <h3 style=\"margin:0; color:#94a3b8;\">Interactive Counter</h3>\n"
                "    <div class=\"count-display\" id=\"count\">0</div>\n"
                "    <div class=\"btn-group\">\n"
                "      <button class=\"btn-dec\" onclick=\"update(-1)\">- 1</button>\n"
                "      <button class=\"btn-reset\" onclick=\"reset()\">Reset</button>\n"
                "      <button class=\"btn-inc\" onclick=\"update(1)\">+ 1</button>\n"
                "    </div>\n"
                "  </div>\n"
                "  <script>\n"
                "    let val = 0;\n"
                "    const display = document.getElementById('count');\n"
                "    function update(diff) {\n"
                "      val += diff;\n"
                "      display.textContent = val;\n"
                "      display.style.color = val > 0 ? '#10b981' : val < 0 ? '#ef4444' : '#38bdf8';\n"
                "    }\n"
                "    function reset() {\n"
                "      val = 0;\n"
                "      display.textContent = 0;\n"
                "      display.style.color = '#38bdf8';\n"
                "    }\n"
                "  </script>\n"
                "</body>\n"
                "</html>\n"
                "```\n"
            )

        # 2.3 Working Calculator App
        if any(w in q_lower for w in ["calculator", "calc", "hisab"]):
            return (
                "Here is a modern responsive Calculator app written in clean HTML, CSS, and vanilla JavaScript. Click **✨ Open in Canvas** to test it:\n\n"
                "```html\n"
                "<!DOCTYPE html>\n"
                "<html lang=\"en\">\n"
                "<head>\n"
                "  <meta charset=\"UTF-8\">\n"
                "  <style>\n"
                "    body {\n"
                "      margin: 0; min-height: 100vh; display: flex; justify-content: center; align-items: center;\n"
                "      background: #090d16; font-family: sans-serif; color: #fff;\n"
                "    }\n"
                "    .calculator {\n"
                "      background: #161f30; padding: 1.5rem; border-radius: 16px; width: 280px; box-shadow: 0 15px 35px rgba(0,0,0,0.5);\n"
                "      border: 1px solid #283548;\n"
                "    }\n"
                "    .calc-screen {\n"
                "      width: 100%; height: 50px; background: #0b111e; border: 1px solid #1e293b; border-radius: 8px;\n"
                "      margin-bottom: 1rem; font-size: 1.5rem; text-align: right; padding: 0.5rem; box-sizing: border-box;\n"
                "      color: #38bdf8; font-family: monospace; overflow: hidden;\n"
                "    }\n"
                "    .calc-keys {\n"
                "      display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.5rem;\n"
                "    }\n"
                "    button {\n"
                "      height: 48px; font-size: 1.1rem; border-radius: 8px; border: none; background: #222f46; color: #fff;\n"
                "      cursor: pointer; transition: background 0.15s;\n"
                "    }\n"
                "    button:hover { background: #334360; }\n"
                "    button.op { background: #6366f1; font-weight: bold; }\n"
                "    button.op:hover { background: #4f46e5; }\n"
                "    button.eq { background: #10b981; grid-column: span 2; font-weight: bold; }\n"
                "    button.eq:hover { background: #059669; }\n"
                "    button.clear { background: #ef4444; font-weight: bold; }\n"
                "  </style>\n"
                "</head>\n"
                "<body>\n"
                "  <div class=\"calculator\">\n"
                "    <div class=\"calc-screen\" id=\"screen\">0</div>\n"
                "    <div class=\"calc-keys\">\n"
                "      <button class=\"clear\" onclick=\"clearScreen()\">C</button>\n"
                "      <button class=\"op\" onclick=\"append('(')\">(</button>\n"
                "      <button class=\"op\" onclick=\"append(')')\">)</button>\n"
                "      <button class=\"op\" onclick=\"append('/')\">÷</button>\n"
                "      <button onclick=\"append('7')\">7</button>\n"
                "      <button onclick=\"append('8')\">8</button>\n"
                "      <button onclick=\"append('9')\">9</button>\n"
                "      <button class=\"op\" onclick=\"append('*')\">×</button>\n"
                "      <button onclick=\"append('4')\">4</button>\n"
                "      <button onclick=\"append('5')\">5</button>\n"
                "      <button onclick=\"append('6')\">6</button>\n"
                "      <button class=\"op\" onclick=\"append('-')\">−</button>\n"
                "      <button onclick=\"append('1')\">1</button>\n"
                "      <button onclick=\"append('2')\">2</button>\n"
                "      <button onclick=\"append('3')\">3</button>\n"
                "      <button class=\"op\" onclick=\"append('+')\">+</button>\n"
                "      <button onclick=\"append('0')\">0</button>\n"
                "      <button onclick=\"append('.')\">.</button>\n"
                "      <button class=\"eq\" onclick=\"calculate()\">=</button>\n"
                "    </div>\n"
                "  </div>\n"
                "  <script>\n"
                "    let expr = '';\n"
                "    const screen = document.getElementById('screen');\n"
                "    function append(val) {\n"
                "      if (expr === '0' && !isNaN(val)) expr = '';\n"
                "      expr += val;\n"
                "      screen.textContent = expr;\n"
                "    }\n"
                "    function clearScreen() { expr = ''; screen.textContent = '0'; }\n"
                "    function calculate() {\n"
                "      try {\n"
                "        expr = String(eval(expr) || 0);\n"
                "        screen.textContent = expr;\n"
                "      } catch(e) { screen.textContent = 'Error'; expr = ''; }\n"
                "    }\n"
                "  </script>\n"
                "</body>\n"
                "</html>\n"
                "```\n"
            )

        # 2.4 Todo List / Task Manager
        if any(w in q_lower for w in ["todo", "to-do", "task", "tasks"]):
            return (
                "Here is an interactive To-Do Task Manager in HTML, CSS, and JavaScript. Click **✨ Open in Canvas** to try it:\n\n"
                "```html\n"
                "<!DOCTYPE html>\n"
                "<html lang=\"en\">\n"
                "<head>\n"
                "  <meta charset=\"UTF-8\">\n"
                "  <style>\n"
                "    body {\n"
                "      margin: 0; min-height: 100vh; display: flex; justify-content: center; align-items: center;\n"
                "      background: #0f172a; font-family: -apple-system, sans-serif; color: #f8fafc;\n"
                "    }\n"
                "    .todo-app {\n"
                "      background: #1e293b; padding: 2rem; border-radius: 16px; width: 340px; border: 1px solid #334155;\n"
                "      box-shadow: 0 15px 30px rgba(0,0,0,0.3);\n"
                "    }\n"
                "    .input-row { display: flex; gap: 0.5rem; margin-bottom: 1.25rem; }\n"
                "    input { flex: 1; padding: 0.65rem; border-radius: 8px; border: 1px solid #475569; background: #0f172a; color: #fff; }\n"
                "    button.add-btn { background: #6366f1; color: #fff; border: none; border-radius: 8px; padding: 0.65rem 1rem; cursor: pointer; font-weight: 600; }\n"
                "    ul { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 0.5rem; }\n"
                "    li { display: flex; justify-content: space-between; align-items: center; background: #293548; padding: 0.5rem 0.75rem; border-radius: 8px; }\n"
                "    li.done span { text-decoration: line-through; color: #64748b; }\n"
                "    .del-btn { background: transparent; border: none; color: #ef4444; cursor: pointer; font-size: 1rem; }\n"
                "  </style>\n"
                "</head>\n"
                "<body>\n"
                "  <div class=\"todo-app\">\n"
                "    <h3 style=\"margin-top:0; color:#38bdf8;\">My Tasks</h3>\n"
                "    <div class=\"input-row\">\n"
                "      <input type=\"text\" id=\"taskInput\" placeholder=\"Add a new task...\">\n"
                "      <button class=\"add-btn\" onclick=\"addTask()\">Add</button>\n"
                "    </div>\n"
                "    <ul id=\"taskList\"></ul>\n"
                "  </div>\n"
                "  <script>\n"
                "    function addTask() {\n"
                "      const inp = document.getElementById('taskInput');\n"
                "      if (!inp.value.trim()) return;\n"
                "      const li = document.createElement('li');\n"
                "      li.innerHTML = `<span onclick=\"this.parentElement.classList.toggle('done')\" style=\"cursor:pointer;\">${inp.value.trim()}</span><button class=\"del-btn\" onclick=\"this.parentElement.remove()\">✕</button>`;\n"
                "      document.getElementById('taskList').appendChild(li);\n"
                "      inp.value = '';\n"
                "    }\n"
                "  </script>\n"
                "</body>\n"
                "</html>\n"
                "```\n"
            )

        # 2.5 Button with Glowing Hover Ripple
        if any(w in q_lower for w in ["button", "ripple", "glow button", "3d button"]):
            return (
                "Here is a stylish glowing interactive Button with ripple physics in HTML and CSS. Click **✨ Open in Canvas** to test it:\n\n"
                "```html\n"
                "<!DOCTYPE html>\n"
                "<html lang=\"en\">\n"
                "<head>\n"
                "  <meta charset=\"UTF-8\">\n"
                "  <style>\n"
                "    body {\n"
                "      margin: 0; min-height: 100vh; display: flex; justify-content: center; align-items: center;\n"
                "      background: #020617; font-family: sans-serif;\n"
                "    }\n"
                "    .glow-btn {\n"
                "      position: relative;\n"
                "      padding: 1rem 2.5rem;\n"
                "      font-size: 1.1rem;\n"
                "      font-weight: 700;\n"
                "      color: #fff;\n"
                "      background: linear-gradient(135deg, #6366f1, #10b981);\n"
                "      border: none;\n"
                "      border-radius: 999px;\n"
                "      cursor: pointer;\n"
                "      box-shadow: 0 0 20px rgba(99, 102, 241, 0.4), 0 0 40px rgba(16, 185, 129, 0.2);\n"
                "      transition: all 0.25s ease;\n"
                "    }\n"
                "    .glow-btn:hover {\n"
                "      transform: translateY(-3px) scale(1.05);\n"
                "      box-shadow: 0 0 35px rgba(99, 102, 241, 0.7), 0 0 60px rgba(16, 185, 129, 0.4);\n"
                "    }\n"
                "    .glow-btn:active {\n"
                "      transform: translateY(1px) scale(0.98);\n"
                "    }\n"
                "  </style>\n"
                "</head>\n"
                "<body>\n"
                "  <button class=\"glow-btn\" onclick=\"alert('Action Confirmed!')\">⚡ Launch Quantum Gateway</button>\n"
                "</body>\n"
                "</html>\n"
                "```\n"
            )

        # 2.6 Responsive Navigation Bar (Navbar)
        if any(w in q_lower for w in ["navbar", "nav bar", "navigation"]):
            return (
                "Here is a responsive modern Navigation Bar crafted in clean HTML and CSS. Click **✨ Open in Canvas** to preview and test it:\n\n"
                "```html\n"
                "<!DOCTYPE html>\n"
                "<html lang=\"en\">\n"
                "<head>\n"
                "  <meta charset=\"UTF-8\">\n"
                "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
                "  <title>Responsive Navbar</title>\n"
                "  <style>\n"
                "    body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0b0f19; color: #f8fafc; }\n"
                "    .navbar { display: flex; justify-content: space-between; align-items: center; padding: 1rem 2rem; background: rgba(15, 23, 42, 0.85); backdrop-filter: blur(12px); border-bottom: 1px solid rgba(255,255,255,0.1); position: sticky; top: 0; z-index: 100; }\n"
                "    .logo { font-size: 1.3rem; font-weight: 800; background: linear-gradient(135deg, #6366f1, #38bdf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-decoration: none; }\n"
                "    .nav-links { display: flex; gap: 1.5rem; list-style: none; margin: 0; padding: 0; align-items: center; }\n"
                "    .nav-links a { color: #94a3b8; text-decoration: none; font-size: 0.95rem; font-weight: 500; transition: color 0.2s; }\n"
                "    .nav-links a:hover { color: #38bdf8; }\n"
                "    .nav-btn { background: #6366f1; color: white; border: none; padding: 0.5rem 1.2rem; border-radius: 8px; font-weight: 600; cursor: pointer; transition: background 0.2s; }\n"
                "    .nav-btn:hover { background: #4f46e5; }\n"
                "    .content { padding: 3rem 2rem; text-align: center; }\n"
                "  </style>\n"
                "</head>\n"
                "<body>\n"
                "  <nav class=\"navbar\">\n"
                "    <a href=\"#\" class=\"logo\">⚡ Kifayat</a>\n"
                "    <ul class=\"nav-links\">\n"
                "      <li><a href=\"#\">Home</a></li>\n"
                "      <li><a href=\"#\">Features</a></li>\n"
                "      <li><a href=\"#\">Pricing</a></li>\n"
                "      <li><a href=\"#\">Docs</a></li>\n"
                "    </ul>\n"
                "    <button class=\"nav-btn\" onclick=\"alert('Get Started clicked!')\">Get Started</button>\n"
                "  </nav>\n"
                "  <div class=\"content\">\n"
                "    <h2>Welcome to Kifayat Gateway</h2>\n"
                "    <p style=\"color:#94a3b8;\">A sleek, responsive navbar component with glassmorphism styling.</p>\n"
                "  </div>\n"
                "</body>\n"
                "</html>\n"
                "```\n"
            )

        # 2.7 Interactive Login Form
        if any(w in q_lower for w in ["login", "signup", "sign up", "sign in", "auth form"]) or (is_html_request and "form" in q_lower):
            return (
                "Here is a modern glassmorphic Login Form in HTML, CSS, and JavaScript with input validation. Click **✨ Open in Canvas** to test it:\n\n"
                "```html\n"
                "<!DOCTYPE html>\n"
                "<html lang=\"en\">\n"
                "<head>\n"
                "  <meta charset=\"UTF-8\">\n"
                "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
                "  <title>Login Card</title>\n"
                "  <style>\n"
                "    body { margin: 0; min-height: 100vh; display: flex; justify-content: center; align-items: center; background: radial-gradient(circle at top, #1e1b4b 0%, #090d16 100%); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #f8fafc; }\n"
                "    .login-card { background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(16px); padding: 2.5rem; border-radius: 20px; border: 1px solid rgba(255,255,255,0.12); width: 320px; box-shadow: 0 20px 40px rgba(0,0,0,0.5); }\n"
                "    h2 { margin-top: 0; font-size: 1.5rem; text-align: center; color: #fff; }\n"
                "    .form-group { margin-bottom: 1.25rem; }\n"
                "    label { display: block; margin-bottom: 0.4rem; font-size: 0.85rem; color: #94a3b8; }\n"
                "    input { width: 100%; padding: 0.75rem; border-radius: 10px; border: 1px solid #334155; background: #0f172a; color: #fff; box-sizing: border-box; font-size: 0.95rem; outline: none; transition: border-color 0.2s; }\n"
                "    input:focus { border-color: #6366f1; }\n"
                "    .submit-btn { width: 100%; padding: 0.85rem; border: none; border-radius: 10px; background: linear-gradient(135deg, #6366f1, #4f46e5); color: #fff; font-weight: 700; font-size: 1rem; cursor: pointer; transition: transform 0.15s, filter 0.2s; }\n"
                "    .submit-btn:hover { filter: brightness(1.1); transform: translateY(-1px); }\n"
                "    .msg { margin-top: 1rem; font-size: 0.85rem; text-align: center; }\n"
                "  </style>\n"
                "</head>\n"
                "<body>\n"
                "  <div class=\"login-card\">\n"
                "    <h2>Welcome Back</h2>\n"
                "    <form onsubmit=\"handleLogin(event)\">\n"
                "      <div class=\"form-group\">\n"
                "        <label>Email Address</label>\n"
                "        <input type=\"email\" id=\"email\" placeholder=\"developer@kifayat.ai\" required />\n"
                "      </div>\n"
                "      <div class=\"form-group\">\n"
                "        <label>Password</label>\n"
                "        <input type=\"password\" id=\"password\" placeholder=\"••••••••\" required />\n"
                "      </div>\n"
                "      <button type=\"submit\" class=\"submit-btn\">Sign In</button>\n"
                "      <div id=\"status\" class=\"msg\"></div>\n"
                "    </form>\n"
                "  </div>\n"
                "  <script>\n"
                "    function handleLogin(e) {\n"
                "      e.preventDefault();\n"
                "      const email = document.getElementById('email').value;\n"
                "      const status = document.getElementById('status');\n"
                "      status.style.color = '#10b981';\n"
                "      status.textContent = 'Authenticating ' + email + '... Success!';\n"
                "    }\n"
                "  </script>\n"
                "</body>\n"
                "</html>\n"
                "```\n"
            )

        # 2.8 Digital Neon Clock
        if any(w in q_lower for w in ["clock", "digital clock", "stopwatch", "timer"]):
            return (
                "Here is a real-time Digital Neon Clock built with HTML, CSS, and JavaScript. Click **✨ Open in Canvas** to watch it tick live:\n\n"
                "```html\n"
                "<!DOCTYPE html>\n"
                "<html lang=\"en\">\n"
                "<head>\n"
                "  <meta charset=\"UTF-8\">\n"
                "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
                "  <title>Neon Digital Clock</title>\n"
                "  <style>\n"
                "    body { margin: 0; min-height: 100vh; display: flex; flex-direction: column; justify-content: center; align-items: center; background: #030712; font-family: monospace; color: #38bdf8; }\n"
                "    .clock-container { background: #0f172a; padding: 2.5rem 3.5rem; border-radius: 20px; border: 2px solid #1e293b; box-shadow: 0 0 40px rgba(56, 189, 248, 0.25); text-align: center; }\n"
                "    .time { font-size: 3.8rem; font-weight: 800; letter-spacing: 0.1em; text-shadow: 0 0 20px rgba(56, 189, 248, 0.6); }\n"
                "    .date { margin-top: 0.8rem; font-size: 1.1rem; color: #94a3b8; font-family: sans-serif; }\n"
                "  </style>\n"
                "</head>\n"
                "<body>\n"
                "  <div class=\"clock-container\">\n"
                "    <div class=\"time\" id=\"clock\">00:00:00</div>\n"
                "    <div class=\"date\" id=\"dateStr\">--</div>\n"
                "  </div>\n"
                "  <script>\n"
                "    function tick() {\n"
                "      const now = new Date();\n"
                "      document.getElementById('clock').textContent = now.toLocaleTimeString();\n"
                "      document.getElementById('dateStr').textContent = now.toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });\n"
                "    }\n"
                "    tick();\n"
                "    setInterval(tick, 1000);\n"
                "  </script>\n"
                "</body>\n"
                "</html>\n"
                "```\n"
            )

        # 2.9 Generic HTML / CSS / JS Request Generator
        if is_html_request or any(w in q_lower for w in ["animation", "game", "modal", "page"]):
            return (
                f"Here is a complete, modern frontend web artifact responding to: **'{question}'**. Click **✨ Open in Canvas** to preview and interact with it live:\n\n"
                "```html\n"
                "<!DOCTYPE html>\n"
                "<html lang=\"en\">\n"
                "<head>\n"
                "  <meta charset=\"UTF-8\">\n"
                "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
                "  <title>Interactive Component</title>\n"
                "  <style>\n"
                "    body {\n"
                "      margin: 0;\n"
                "      min-height: 100vh;\n"
                "      display: flex;\n"
                "      flex-direction: column;\n"
                "      align-items: center;\n"
                "      justify-content: center;\n"
                "      background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);\n"
                "      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;\n"
                "      color: #f8fafc;\n"
                "      padding: 1rem;\n"
                "      box-sizing: border-box;\n"
                "    }\n"
                "    .widget-container {\n"
                "      background: rgba(30, 41, 59, 0.85);\n"
                "      padding: 2.2rem;\n"
                "      border-radius: 18px;\n"
                "      border: 1px solid rgba(255, 255, 255, 0.15);\n"
                "      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);\n"
                "      max-width: 420px;\n"
                "      width: 100%;\n"
                "      text-align: center;\n"
                "    }\n"
                "    .live-badge {\n"
                "      display: inline-block;\n"
                "      padding: 0.25rem 0.65rem;\n"
                "      border-radius: 999px;\n"
                "      background: rgba(16, 185, 129, 0.2);\n"
                "      border: 1px solid rgba(16, 185, 129, 0.4);\n"
                "      color: #34d399;\n"
                "      font-size: 0.75rem;\n"
                "      font-weight: 700;\n"
                "      margin-bottom: 0.75rem;\n"
                "    }\n"
                "    .widget-btn {\n"
                "      margin-top: 1.25rem;\n"
                "      padding: 0.75rem 1.5rem;\n"
                "      border: none;\n"
                "      border-radius: 10px;\n"
                "      background: #6366f1;\n"
                "      color: #ffffff;\n"
                "      font-weight: 600;\n"
                "      cursor: pointer;\n"
                "      transition: all 0.2s ease;\n"
                "    }\n"
                "    .widget-btn:hover {\n"
                "      background: #4f46e5;\n"
                "      transform: translateY(-2px);\n"
                "    }\n"
                "  </style>\n"
                "</head>\n"
                "<body>\n"
                "  <div class=\"widget-container\">\n"
                "    <span class=\"live-badge\">● Live Canvas Component</span>\n"
                "    <h2 style=\"margin: 0.2rem 0 0.6rem 0;\">Custom Web Widget</h2>\n"
                f"    <p style=\"color: #94a3b8; font-size: 0.9rem;\">Generated for: <em>{question}</em></p>\n"
                "    <div id=\"output\" style=\"padding: 0.75rem; background: #0b111e; border-radius: 8px; margin: 1rem 0; font-family: monospace; color: #38bdf8;\">Ready for interaction</div>\n"
                "    <button class=\"widget-btn\" onclick=\"document.getElementById('output').textContent = 'Event triggered at ' + new Date().toLocaleTimeString()\">Trigger Action</button>\n"
                "  </div>\n"
                "</body>\n"
                "</html>\n"
                "```\n"
            )

        # --- 3. Python Coding & Algorithmic Requests ---
        if any(w in q_lower for w in ["prime", "prime number", "sieve"]):
            return (
                "Here is an optimized Python solution to check for prime numbers and generate primes up to N using the Sieve of Eratosthenes:\n\n"
                "```python\n"
                "import math\n"
                "from typing import List\n"
                "\n"
                "def is_prime(n: int) -> bool:\n"
                "    \"\"\"Check if a number is prime in O(sqrt(n)) time.\"\"\"\n"
                "    if n <= 1:\n"
                "        return False\n"
                "    if n <= 3:\n"
                "        return True\n"
                "    if n % 2 == 0 or n % 3 == 0:\n"
                "        return False\n"
                "    # Check factors up to sqrt(n) stepping by 6\n"
                "    for i in range(5, int(math.isqrt(n)) + 1, 6):\n"
                "        if n % i == 0 or n % (i + 2) == 0:\n"
                "            return False\n"
                "    return True\n"
                "\n"
                "def sieve_of_eratosthenes(limit: int) -> List[int]:\n"
                "    \"\"\"Generate all prime numbers up to limit in O(n log log n).\"\"\"\n"
                "    if limit < 2:\n"
                "        return []\n"
                "    is_p = [True] * (limit + 1)\n"
                "    is_p[0] = is_p[1] = False\n"
                "    for p in range(2, int(math.isqrt(limit)) + 1):\n"
                "        if is_p[p]:\n"
                "            for i in range(p * p, limit + 1, p):\n"
                "                is_p[i] = False\n"
                "    return [num for num, prime in enumerate(is_p) if prime]\n"
                "\n"
                "# Example Usage:\n"
                "if __name__ == '__main__':\n"
                "    print('Is 29 prime?', is_prime(29))  # Output: True\n"
                "    print('Primes up to 50:', sieve_of_eratosthenes(50))\n"
                "```\n"
            )

        if any(w in q_lower for w in ["fibonacci", "palindrome", "binary search", "factorial"]):
            return (
                "Here is an efficient, clean Python implementation for algorithmic problem solving:\n\n"
                "```python\n"
                "from typing import List, Optional\n"
                "\n"
                "def binary_search(arr: List[int], target: int) -> Optional[int]:\n"
                "    \"\"\"Perform logarithmic O(log n) search on a sorted list.\"\"\"\n"
                "    low, high = 0, len(arr) - 1\n"
                "    while low <= high:\n"
                "        mid = (low + high) // 2\n"
                "        if arr[mid] == target:\n"
                "            return mid\n"
                "        elif arr[mid] < target:\n"
                "            low = mid + 1\n"
                "        else:\n"
                "            high = mid - 1\n"
                "    return None\n"
                "\n"
                "def is_palindrome(text: str) -> bool:\n"
                "    \"\"\"Check if string is a palindrome ignoring case and non-alphanumerics.\"\"\"\n"
                "    clean = [c.lower() for c in text if c.isalnum()]\n"
                "    return clean == clean[::-1]\n"
                "\n"
                "# Verification\n"
                "if __name__ == '__main__':\n"
                "    sorted_nums = [2, 5, 8, 12, 16, 23, 38, 56, 72, 91]\n"
                "    print('Index of 23:', binary_search(sorted_nums, 23))  # 5\n"
                "    print('Is radar a palindrome?', is_palindrome('radar'))  # True\n"
                "```\n"
            )

        if any(w in q_lower for w in ["fastapi", "pydantic", "python"]):
            return (
                "Here is a production-grade FastAPI endpoint implementation featuring Pydantic V2 validation, typing, and dependency injection:\n\n"
                "```python\n"
                "from fastapi import FastAPI, HTTPException, status\n"
                "from pydantic import BaseModel, Field\n"
                "from typing import Optional\n"
                "\n"
                "app = FastAPI(title=\"Kifayat High-Performance API\", version=\"2.0.0\")\n"
                "\n"
                "class ItemRequest(BaseModel):\n"
                "    name: str = Field(..., min_length=2, max_length=50, description=\"Item name\")\n"
                "    price: float = Field(..., gt=0.0, description=\"Positive price in USD\")\n"
                "    tags: list[str] = Field(default_factory=list)\n"
                "\n"
                "class ItemResponse(BaseModel):\n"
                "    id: int\n"
                "    name: str\n"
                "    price: float\n"
                "    tax: float\n"
                "\n"
                "@app.post(\"/items\", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)\n"
                "async def create_item(payload: ItemRequest):\n"
                "    calculated_tax = round(payload.price * 0.18, 2)\n"
                "    return ItemResponse(\n"
                "        id=101,\n"
                "        name=payload.name,\n"
                "        price=payload.price,\n"
                "        tax=calculated_tax\n"
                "    )\n"
                "```\n"
            )

        # --- 4. Technical Explanations ---
        if "quantum" in q_lower:
            return (
                "**Quantum Computing Explained Simply:**\n\n"
                "Classical computers use **bits** as the fundamental unit of information, where each bit is strictly either a `0` or a `1` (like a binary light switch).\n\n"
                "A **Quantum Computer** uses **qubits** (quantum bits). Because of fundamental quantum mechanics:\n"
                "1. **Superposition:** A qubit can exist as a `0`, a `1`, or a probabilistic continuum of *both at the same time* until measured.\n"
                "2. **Entanglement:** Qubits can be deeply linked such that changing the quantum state of one instantly influences another, allowing exponential computational parallelism.\n\n"
                "This enables quantum machines to solve specific ultra-complex problems—such as molecular simulation, RSA cryptographic factorization, and combinatoric supply chain logistics—in minutes rather than millennia."
            )

        if "email" in q_lower or "proposal" in q_lower:
            return (
                "**Subject:** Proposal: Strategic Implementation of Kifayat Context Optimization Gateway\n\n"
                "Dear Executive Stakeholders,\n\n"
                "I am pleased to present our proposal for integrating the **Kifayat Intelligent Gateway** into our enterprise LLM infrastructure.\n\n"
                "**Key Objectives & Impact:**\n"
                "- **85%+ Latency Reduction:** Serving recurring inquiries securely from our 384-dimensional semantic response cache.\n"
                "- **Cost Optimization:** Drastic token compression via immutable frozen memory blocks and KV prefix cache reuse.\n"
                "- **Reliability:** Automated 3-rung prompt repair ladder preventing redundant escalations to expensive 70B+ models.\n\n"
                "We look forward to scheduling a technical walkthrough this Thursday at your convenience.\n\n"
                "Best regards,\n"
                "Engineering Architecture Lead"
            )

        # --- 5. College Helpdesk Questions (Preserved for Tests & Domain Verification) ---
        # Follow-up / Mess questions
        if any(w in q_lower for w in ["mess", "khana", "food", "veg", "egg"]):
            if any(w in q_lower for w in ["included", "include", "shamil"]):
                if is_hinglish:
                    return "Nahi, hostel fee mein mess charges include nahi hain. Standard vegetarian mess ka charge ₹22,500 per semester alag se Central Mess Committee (CMC) ko dena hota hai. Agar egg counter service leni ho toh ₹2,500 extra lagte hain."
                return "No, mess charges are not included in the hostel fee. The standard pure vegetarian mess charge is ₹22,500 per semester paid separately to the Central Mess Committee (CMC). An optional egg counter is available for ₹2,500 extra per semester."
            elif any(w in q_lower for w in ["non-veg", "chicken", "meat", "egg"]):
                if is_hinglish:
                    return "KIT mess mein khana strictly 100% vegetarian hota hai. Chicken ya non-veg meat serve nahi kiya jata, lekin breakfast aur dinner mein optional egg counter (boiled egg/omelet) ₹2,500 per semester extra fee par uplabdh hai."
                return "All dining halls at KIT serve 100% pure vegetarian cuisine. Non-vegetarian meat is not prepared, though an optional egg counter (omelets/boiled eggs) is available during breakfast and dinner for ₹2,500 extra per semester."
            else:
                if is_hinglish:
                    return "KIT standard mess fee ₹22,500 per semester hai. Mess pure vegetarian hai jisme breakfast, lunch, high-tea snacks aur dinner shamil hain."
                return "The standard vegetarian mess fee at KIT is ₹22,500 per semester, which covers breakfast, lunch, evening tea with snacks, and dinner."

        # Hostel fee questions
        if any(w in q_lower for w in ["hostel", "room", "stay", "rehna"]) and any(w in q_lower for w in ["fee", "rent", "cost", "charge", "kitna", "paisa"]):
            if is_hinglish:
                return "KIT mein hostel fee room sharing ke hisaab se hoti hai: Single Occupancy ka ₹42,000 per semester, Double Occupancy ka ₹32,000 per semester, aur Triple Occupancy ka ₹24,000 per semester hai. Iske alawa ₹8,000 utility charges lagte hain aur ek baar ₹15,000 refundable caution deposit dena hota hai."
            return "At Kifayat Institute of Technology, hostel room fees per semester are: Single Occupancy ₹42,000, Double Occupancy ₹32,000, and Triple Occupancy ₹24,000. Additionally, ₹8,000 is charged per semester for utilities/electricity, alongside a one-time refundable hostel caution deposit of ₹15,000."

        # Curfew / Timing questions
        if any(w in q_lower for w in ["curfew", "in-time", "timing", "time", "raat", "gate"]):
            if is_hinglish:
                return "Hostel campus in-time curfew senior students ke liye Sunday se Thursday raat 10:30 PM aur Friday-Saturday ko 11:30 PM hai. First-year freshers ke liye pehle semester mein curfew strictly 9:30 PM hai."
            return "The campus in-time curfew for senior undergraduate students is 10:30 PM (Sunday to Thursday) and 11:30 PM (Friday and Saturday). For first-year freshers during their first semester, the in-time curfew is strictly 9:30 PM."

        # Attendance questions
        if any(w in q_lower for w in ["attendance", "haziri", "attend", "detain", "fa"]):
            if is_hinglish:
                return "Exams mein baithne ke liye har subject mein minimum 75% attendance mandatory hai. Medical emergency hone par Dean of Academic Affairs 65% se 74.9% ke beech condonation de sakte hain. Agar 65% se kam attendance hui toh student detain (FA grade) ho jata hai."
            return "A minimum of 75% attendance is mandatory in each course to appear for End-Semester examinations. A condonation range of 65% to 74.9% is permissible for verified medical illness with approval from the Dean of Academic Affairs. Attendance below 65% results in immediate course detention ('FA' grade)."

        # Placement questions
        if any(w in q_lower for w in ["placement", "job", "package", "salary", "tpc", "company", "recruit"]):
            if any(w in q_lower for w in ["highest", "average", "stats", "salary"]):
                if is_hinglish:
                    return "2024-25 batch mein highest international package $145,000 USD (QuantumWorks Zurich) aur highest domestic package ₹54.50 LPA (TowerApex) tha. CSE/DSAI ka average package ₹16.80 LPA aur ECE ka ₹12.40 LPA raha."
                return "For the 2024–2025 placement season, the highest international package was $145,000 USD/annum and highest domestic package was ₹54.50 LPA. The average package was ₹16.80 LPA for CSE & DSAI, and ₹12.40 LPA for ECE."
            if any(w in q_lower for w in ["eligibility", "eligible", "cgpa", "criteria"]):
                if is_hinglish:
                    return "Campus placements mein baithne ke liye minimum 6.50 CGPA (6th semester ke baad) hona zaroori hai aur koi active backlog nahi honi chahiye. Iske sath 5th semester Placement Training Program mein 85% attendance required hai."
                return "To participate in campus placements, students must maintain a minimum CGPA of 6.50 through the end of the 6th semester with zero active backlogs, alongside 85% attendance in the 5th-semester Placement Training Program."
            if any(w in q_lower for w in ["where", "kahan", "location", "floor", "office"]):
                if is_hinglish:
                    return "Corporate Relations & Training Placement Cell (TPC) Apex Administrative Tower ke 4th Floor par sthit hai. Office hours Monday to Friday 9:00 AM se 6:00 PM tak hain."
                return "The Corporate Relations & Training Placement Cell (TPC) is located on the 4th Floor of the Apex Administrative Tower. Office hours are Monday through Friday, 9:00 AM to 6:00 PM."

        # Library questions
        if any(w in q_lower for w in ["library", "book", "kitab"]):
            if is_hinglish:
                return "Tagore Central Library se B.Tech students ek baar mein 4 books 14 din ke liye borrow kar sakte hain. Late return par pehle 7 din ₹5/day aur uske baad ₹10/day fine lagta hai. Exam time par library 24x7 khuli rehti hai."
            return "At the Tagore Central Library, B.Tech students may borrow up to 4 books for 14 calendar days. Overdue fines are ₹5/day per book for the first 7 days, and ₹10/day thereafter. During exam periods, the library is open 24x7."

        # Fees (Tuition)
        if any(w in q_lower for w in ["tuition", "btech fee", "b.tech fee", "college fee", "cse fee"]):
            if is_hinglish:
                return "B.Tech CSE, ECE aur DSAI branches ke liye tuition fee ₹1,25,000 per semester hai (EE, ME aur CE ke liye ₹1,10,000 per semester). Iske alawa institutional development aur lab fees milakar lagbhag ₹34,000 additional charges hain."
            return "The tuition fee for B.Tech in CSE, ECE, and DSAI is ₹1,25,000 per semester (₹1,10,000 for EE, ME, and CE). Additional semester institutional charges (Development, Labs, Internet, Library, Exam) total ₹34,000."

        # Scholarships
        if any(w in q_lower for w in ["scholarship", "financial aid", "prerna"]):
            if is_hinglish:
                return "Kifayat Prerna Financial Aid un students ke liye hai jinki family annual income ₹4,50,000 se kam ho aur minimum CGPA 7.00 ho. Isme 40% se 75% tak tuition fee waiver milta hai."
            return "The Kifayat Prerna Financial Aid offers 40% to 75% tuition fee waivers for students with annual family income below ₹4,50,000 and a minimum CGPA of 7.00 with clean disciplinary standing."

        # Emergency / Medical
        if any(w in q_lower for w in ["emergency", "hospital", "doctor", "ambulance", "medical", "health"]):
            if is_hinglish:
                return "Campus medical emergency ke liye Charaka Health Center helpline +91-11-2955-0199 ya campus internal phone se Intercom 199 dial karein. Do ambulances 24x7 available rehti hain."
            return "For campus medical emergencies, contact the Charaka Health Center 24x7 at +91-11-2955-0199 or dial Intercom 199. Two dedicated emergency response ambulances are stationed on campus round-the-clock."

        # Natural conversational fallback
        if is_hinglish:
            return f"Aapke sawal '{question}' ke baare mein: Kifayat AI is par puri tarah clear aur accurate analysis provide karta hai. Agar aapko iska code ya deeper explanation chahiye toh bataiye!"
        return f"Regarding your query on '{question}': As Kifayat AI, I provide thorough, accurate assistance across technical problem-solving, coding, and direct answers. Let me know if you would like code examples, step-by-step breakdowns, or deeper context!"

    async def generate(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 500,
        model_id: Optional[str] = None
    ) -> ProviderResponse:
        start_time = time.perf_counter()
        
        # Determine current user question
        user_msgs = [m["content"] for m in messages if m.get("role") == "user"]
        last_question = user_msgs[-1] if user_msgs else "Helpdesk query"
        
        # Detect Hinglish
        hinglish_words = ["ka", "ki", "ke", "hai", "kya", "kitna", "kahan", "nahi", "isme", "mein", "aur", "pehle"]
        is_hinglish = any(w in last_question.lower().split() for w in hinglish_words)

        answer = self._generate_synthetic_answer(last_question, is_hinglish)
        
        # Calculate tokens
        prompt_text = (system or "") + " " + " ".join(m.get("content", "") for m in messages)
        in_tokens = self._estimate_tokens(prompt_text)
        out_tokens = self._estimate_tokens(answer)
        latency = (time.perf_counter() - start_time) * 1000 + 45.0  # slight simulated latency

        is_baseline = (model_id and ("strong" in model_id.lower() or "baseline" in model_id.lower())) or (system and "UNOPTIMIZED" in system)
        if is_baseline or not self.supports_prompt_caching:
            cache_read = 0
            cache_write = in_tokens
        else:
            if system and "CACHE_CHECKPOINT_1" in system:
                prefix_part = system.split("<!-- CACHE_CHECKPOINT_1 -->")[0]
                prefix_tokens = self._estimate_tokens(prefix_part)
                dynamic_tokens = sum(self._estimate_tokens(m.get("content", "")) for m in messages)
                cache_read = min(prefix_tokens, max(0, in_tokens - dynamic_tokens))
                cache_write = in_tokens - cache_read
            else:
                cache_read = 0
                cache_write = in_tokens

        return ProviderResponse(
            text=answer,
            usage=ProviderUsage(
                input_tokens=in_tokens,
                output_tokens=out_tokens,
                cache_read_tokens=cache_read,
                cache_write_tokens=cache_write,
                latency_ms=round(latency, 2),
                model_id=model_id or "mock-kifayat-v1"
            )
        )

    async def stream(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 500,
        model_id: Optional[str] = None
    ) -> AsyncIterator[str]:
        user_msgs = [m["content"] for m in messages if m.get("role") == "user"]
        last_question = user_msgs[-1] if user_msgs else "Helpdesk query"
        hinglish_words = ["ka", "ki", "ke", "hai", "kya", "kitna", "kahan", "nahi", "isme", "mein", "aur", "pehle"]
        is_hinglish = any(w in last_question.lower().split() for w in hinglish_words)

        answer = self._generate_synthetic_answer(last_question, is_hinglish)
        
        # Yield words with small pauses to simulate realistic streaming
        words = answer.split(" ")
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")
            await asyncio.sleep(0.015)

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generates deterministic 384-dimensional dense normalized embeddings
        using token n-gram hashing. Ensures identical/semantically equivalent texts
        produce high cosine similarities (> 0.90).
        """
        embeddings = []
        for text in texts:
            # Clean and normalize text
            normalized = re.sub(r"[^\w\s]", "", text.lower()).strip()
            tokens = normalized.split()
            stop_words = {"what", "is", "the", "how", "much", "does", "for", "a", "an", "in", "at", "to", "of", "per", "semester", "kya", "hai", "ka", "ki", "ke"}
            
            # Map canonical concept stems to common high-weight buckets
            synonyms = {
                "hostel": "residence_hall", "hostels": "residence_hall",
                "room": "residence_hall", "living": "residence_hall",
                "fee": "monetary_cost", "fees": "monetary_cost",
                "cost": "monetary_cost", "charge": "monetary_cost", "rent": "monetary_cost",
                "kitna": "monetary_cost", "kaunsa": "which_entity",
                "mess": "food_dining", "khana": "food_dining", "dining": "food_dining",
                "attendance": "haziri_presence", "haziri": "haziri_presence",
                "curfew": "night_timing", "intime": "night_timing",
                "placement": "career_jobs", "job": "career_jobs", "package": "career_jobs",
                "library": "book_repository", "books": "book_repository", "kitab": "book_repository"
            }
            
            vec = np.zeros(self.embedding_dim, dtype=np.float32)
            
            # Base semantic features
            for token in tokens:
                if token in stop_words:
                    continue
                canonical = synonyms.get(token, token)
                h = int(hashlib.md5(canonical.encode("utf-8")).hexdigest(), 16)
                idx = h % self.embedding_dim
                weight = 4.0 if token in synonyms else 1.5
                vec[idx] += weight
                # Bigram feature
                h2 = (h >> 4) % self.embedding_dim
                vec[h2] += weight * 0.5
                
            # Character trigram features for typo-tolerance on non-stopwords
            for token in tokens:
                if token not in stop_words and len(token) >= 3:
                    for i in range(len(token) - 2):
                        tri = token[i:i+3]
                        h_tri = int(hashlib.sha256(tri.encode("utf-8")).hexdigest(), 16) % self.embedding_dim
                        vec[h_tri] += 0.5


            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            else:
                vec[0] = 1.0
                
            embeddings.append(vec.tolist())
        return embeddings

    async def judge(
        self,
        question: str,
        answer: str,
        context: str,
        model_id: Optional[str] = None
    ) -> JudgeResult:
        """
        Verifies answer against factual handbook constraints.
        Returns structured verification result.
        """
        # Rule check: empty answer or no alphanumeric content
        if not answer or not any(c.isalnum() for c in answer.strip()):
            return JudgeResult(passed=False, score=1, reason="Answer is empty or contains no readable text.")
        
        # Rule check: canned refusal
        if any(r in answer.lower() for r in ["i cannot answer", "i do not know", "as an ai"]):
            return JudgeResult(passed=False, score=2, reason="Answer contained canned refusal phrases.")

        q_lower = question.lower()
        ans_lower = answer.lower()

        # Coding verification check: If user asks for code, ensure answer contains valid code block
        coding_intents = [
            "write a python", "write html", "write css", "write javascript", "write js",
            "create a button", "create a card", "create an app", "create a counter",
            "create a calculator", "create a form", "create a navbar", "write code",
            "fastapi endpoint", "function in python", "code in html", "code in javascript",
            "code for", "implement"
        ]
        if any(intent in q_lower for intent in coding_intents):
            if "```" not in answer:
                return JudgeResult(passed=False, score=2, reason="Coding request was not satisfied with a structured code block.")

        # Factual verification checks
        if "hostel" in q_lower and ("fee" in q_lower or "rent" in q_lower or "kitna" in q_lower):
            if "42,000" in ans_lower or "32,000" in ans_lower or "24,000" in ans_lower:
                return JudgeResult(passed=True, score=5, reason="Hostel fees match handbook figures perfectly.")
            return JudgeResult(passed=False, score=2, reason="Hostel fee amounts are inaccurate or missing.")

        if "attendance" in q_lower:
            if "75%" in ans_lower:
                return JudgeResult(passed=True, score=5, reason="Attendance threshold accurately stated as 75%.")
            return JudgeResult(passed=False, score=2, reason="Mandatory 75% attendance rule not found.")

        if "mess" in q_lower and "included" in q_lower:
            if "not included" in ans_lower or "nahi" in ans_lower:
                return JudgeResult(passed=True, score=5, reason="Accurately clarified that mess is not included in hostel fee.")

        return JudgeResult(passed=True, score=4, reason="Answer is relevant, coherent, and verified by judge.")
