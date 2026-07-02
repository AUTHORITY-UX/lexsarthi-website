<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
  <title>LexSarthi v9.0 — Universal Default OS</title>
  <meta name="description" content="LexSarthi v9.0 — 250 specialists, RAG, live web search, jury verification." />
  <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Ctext y='26' font-size='26'%3E%F0%9F%94%B1%3C/text%3E%3C/svg%3E" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Inter:wght@300;400;500;600;700&family=Noto+Serif+Devanagari:wght@500;600&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" />
  <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
  <style>
    :root{
      --bg:#0a0a0f; --panel:rgba(20,20,32,0.7); --panel-2:#1a1a2a;
      --border:rgba(212,175,55,0.15); --gold:#d4af37; --gold-soft:rgba(212,175,55,0.1);
      --gold-glow:rgba(212,175,55,0.25); --saffron:#ff9933; --text:#f0ede8;
      --muted:#8a8a95; --ok:#34d399; --err:#ff6b6b; --shadow:0 8px 32px rgba(0,0,0,0.4);
    }
    *{box-sizing:border-box;margin:0;padding:0}
    html,body{background:var(--bg);color:var(--text);font-family:'Inter',sans-serif;min-height:100vh;overflow-x:hidden;font-size:15px;line-height:1.55;position:relative}
    body{background:radial-gradient(ellipse at center,#141428 0%,#0a0a0f 80%);}
    .moon{position:fixed;top:5%;left:5%;width:18vmin;height:18vmin;border-radius:50%;background:radial-gradient(circle at 30% 30%, rgba(255,240,200,0.25), rgba(200,180,150,0.05));box-shadow:0 0 60px rgba(255,240,200,0.08), inset 0 0 40px rgba(255,255,255,0.03);pointer-events:none;z-index:0;border:1px solid rgba(255,255,255,0.02);}
    .moon::after{content:'';position:absolute;top:10%;left:20%;width:40%;height:40%;border-radius:50%;background:radial-gradient(circle, rgba(255,255,255,0.05), transparent);}
    .infinite-rings{position:fixed;top:0;left:0;width:100vw;height:100vh;pointer-events:none;z-index:0;overflow:hidden;}
    .ring-bg{position:absolute;top:50%;left:50%;border-radius:50%;border:1px solid rgba(212,175,55,0.10);transform:translate(-50%,-50%) scale(0.5);animation:ringExpand var(--duration) ease-out infinite alternate;opacity:0;}
    @keyframes ringExpand{0%{transform:translate(-50%,-50%) scale(0.2);opacity:0.2}100%{transform:translate(-50%,-50%) scale(5);opacity:0.03}}
    .om-5d-wrapper{position:fixed;top:10%;left:50%;transform:translateX(-50%);z-index:0;pointer-events:none;width:30vmin;height:30vmin;perspective:800px;display:flex;align-items:center;justify-content:center;}
    .om-5d{width:100%;height:100%;transform-style:preserve-3d;animation:spin5d 16s linear infinite;position:relative;}
    @keyframes spin5d{0%{transform:rotateY(0) rotateX(15deg)}100%{transform:rotateY(360deg) rotateX(15deg)}}
    .om-face-5d{position:absolute;width:100%;height:100%;font-family:'Noto Serif Devanagari',serif;font-size:14vmin;color:var(--gold);display:flex;align-items:center;justify-content:center;text-shadow:0 0 40px rgba(212,175,55,0.2);background:rgba(10,10,15,0.05);border-radius:20%;border:1px solid rgba(212,175,55,0.05);backface-visibility:hidden;}
    .om-face-5d.front {transform:translateZ(calc(30vmin / 2))}
    .om-face-5d.back {transform:rotateY(180deg) translateZ(calc(30vmin / 2))}
    .om-face-5d.left {transform:rotateY(-90deg) translateZ(calc(30vmin / 2))}
    .om-face-5d.right {transform:rotateY(90deg) translateZ(calc(30vmin / 2))}
    .om-face-5d.top {transform:rotateX(90deg) translateZ(calc(30vmin / 2))}
    .om-face-5d.bottom {transform:rotateX(-90deg) translateZ(calc(30vmin / 2))}
    .stars{position:fixed;inset:0;pointer-events:none;z-index:0}
    .star{position:absolute;background:#fff;border-radius:50%;opacity:0.4;animation:twinkle var(--duration) infinite ease-in-out}
    @keyframes twinkle{0%,100%{opacity:0.1}50%{opacity:0.7}}
    .wisdom-tagline{position:relative;z-index:1;text-align:center;color:var(--gold);font-family:'Cormorant Garamond',serif;font-size:1.3rem;letter-spacing:4px;margin:20px 0 8px;text-shadow:0 0 30px rgba(212,175,55,0.2);padding-top:calc(30vmin + 20px);}
    .container{position:relative;z-index:2;max-width:900px;margin:0 auto;padding:0 16px 16px;display:flex;flex-direction:column;min-height:100vh;}
    .header{position:relative;z-index:10;background:rgba(20,20,32,0.6);backdrop-filter:blur(18px);border:1px solid var(--border);border-radius:18px;padding:12px 20px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;margin-bottom:16px;box-shadow:var(--shadow);overflow:visible;}
    .brand-name{font-family:'Cormorant Garamond',serif;font-size:1.6rem;font-weight:700;color:var(--gold);letter-spacing:1.5px;}
    .version-badge{background:var(--gold-soft);border:1px solid var(--border);color:var(--gold);padding:2px 10px;border-radius:999px;font-size:0.55rem;font-weight:600;margin-left:8px;letter-spacing:1px;}
    .premium-badge,.enterprise-badge{display:none;background:var(--gold-soft);color:var(--gold);border:1px solid var(--gold);padding:1px 10px;border-radius:999px;font-size:0.55rem;margin-left:6px;}
    .enterprise-badge{background:rgba(124,58,237,0.15);color:#a78bfa;border-color:#7c3aed;}
    .header-actions{display:flex;gap:6px;flex-wrap:wrap}
    .btn{border:none;cursor:pointer;font-family:inherit;font-weight:500;border-radius:10px;transition:transform 0.15s ease, background 0.2s ease, box-shadow 0.2s ease;letter-spacing:0.3px;padding:6px 14px;font-size:0.7rem;}
    .btn:hover{transform:translateY(-1px)}
    .btn-gold{background:linear-gradient(135deg,#d4af37,#b8901e);color:#1a1a1a;box-shadow:0 4px 12px rgba(212,175,55,0.25);}
    .btn-outline{background:transparent;color:var(--gold);border:1px solid var(--gold);}
    .btn-outline:hover{background:var(--gold-soft)}
    .settings-btn{background:transparent;color:var(--gold);border:1px solid var(--border);border-radius:10px;padding:6px 10px;cursor:pointer;}
    .settings-btn:hover{background:var(--gold-soft)}
    .settings-panel{position:absolute;top:calc(100% + 8px);right:16px;background:var(--panel-2);border:1px solid var(--border);border-radius:14px;padding:14px;width:230px;z-index:100;box-shadow:0 12px 40px rgba(0,0,0,0.6);backdrop-filter:blur(12px);display:none;}
    .settings-panel.open{display:block}
    .settings-panel label{display:block;font-size:0.7rem;color:var(--muted);margin:6px 0 3px}
    .settings-panel select{width:100%;background:rgba(255,255,255,0.04);border:1px solid var(--border);color:var(--text);padding:6px 8px;border-radius:8px;font-size:0.75rem;}
    .settings-divider{border:none;border-top:1px solid var(--border);margin:10px 0}
    .chat-container{flex:1;background:rgba(20,20,32,0.45);backdrop-filter:blur(12px);border:1px solid var(--border);border-radius:18px;padding:16px;overflow-y:auto;min-height:220px;max-height:52vh;margin-bottom:14px;box-shadow:var(--shadow);}
    #chatArea{display:flex;flex-direction:column;gap:8px}
    .chat-bubble{max-width:88%;padding:10px 16px;border-radius:14px;font-size:0.9rem;line-height:1.6;animation:slideUp 0.3s ease-out;word-wrap:break-word;}
    @keyframes slideUp{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
    .chat-bubble.user{align-self:flex-end;background:linear-gradient(135deg,rgba(212,175,55,0.18),rgba(212,175,55,0.05));border:1px solid var(--border);color:#f5f2e8;}
    .chat-bubble.agent{align-self:flex-start;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.06);color:var(--text);}
    #defaultWelcome{display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:20px 12px;color:var(--text);}
    .welcome-om{font-size:2.5rem;color:var(--gold);margin-bottom:6px;text-shadow:0 0 40px rgba(212,175,55,0.3);animation:pulseOm 3s ease-in-out infinite;font-family:'Noto Serif Devanagari',serif;}
    @keyframes pulseOm{0%,100%{transform:scale(1);opacity:0.8}50%{transform:scale(1.1);opacity:1}}
    .welcome-title{font-family:'Cormorant Garamond',serif;font-size:1.8rem;font-weight:600;color:var(--gold);margin-bottom:4px;}
    .welcome-sub{font-size:0.9rem;color:var(--muted);max-width:500px;margin:0 auto;line-height:1.6;}
    .welcome-sub strong{color:var(--text)}
    .typing-indicator{display:none;align-items:center;gap:8px;padding:8px 12px;color:var(--muted);font-size:0.8rem;}
    .typing-indicator.active{display:flex}
    .typing-dots span{width:6px;height:6px;background:var(--gold);border-radius:50%;display:inline-block;margin:0 2px;animation:dotBounce 1.4s infinite ease-in-out both;}
    .typing-dots span:nth-child(1){animation-delay:0s}
    .typing-dots span:nth-child(2){animation-delay:0.2s}
    .typing-dots span:nth-child(3){animation-delay:0.4s}
    @keyframes dotBounce{0%,80%,100%{transform:scale(0)}40%{transform:scale(1)}}
    .om-spinner{display:inline-block;font-family:'Noto Serif Devanagari',serif;color:var(--gold);animation:spinOm 1.5s linear infinite;}
    @keyframes spinOm{0%{transform:rotate(0)}100%{transform:rotate(360deg)}}
    .input-card{background:rgba(20,20,32,0.6);backdrop-filter:blur(14px);border:1px solid var(--border);border-radius:18px;padding:14px;margin-bottom:12px;box-shadow:var(--shadow);}
    .query-input{width:100%;background:rgba(255,255,255,0.04);border:1px solid var(--border);color:var(--text);padding:10px 14px;border-radius:12px;font-family:inherit;font-size:0.9rem;resize:vertical;min-height:70px;outline:none;transition:border-color 0.2s, box-shadow 0.2s;}
    .query-input:focus{border-color:var(--gold);box-shadow:0 0 0 3px rgba(212,175,55,0.1);}
    .input-tools{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px;align-items:center;}
    .tool-btn{background:transparent;color:var(--gold);border:1px solid var(--border);padding:5px 12px;border-radius:30px;font-size:0.7rem;cursor:pointer;font-family:inherit;display:inline-flex;align-items:center;gap:5px;transition:background 0.2s, border-color 0.2s;}
    .tool-btn:hover{background:var(--gold-soft);border-color:var(--gold)}
    .web-toggle-label{display:inline-flex;align-items:center;gap:4px;font-size:0.7rem;color:var(--muted);border:1px solid var(--border);padding:5px 12px;border-radius:30px;cursor:pointer;transition:background 0.2s;}
    .web-toggle-label:hover{background:var(--gold-soft)}
    .web-toggle-label input{accent-color:var(--gold)}
    .oracle-toggle{color:var(--saffron)}
    .send-btn{margin-left:auto;background:linear-gradient(135deg,#d4af37,#b8901e);color:#1a1a1a;border:none;padding:6px 20px;border-radius:30px;font-weight:600;cursor:pointer;font-size:0.8rem;transition:transform 0.15s, box-shadow 0.2s;box-shadow:0 4px 12px rgba(212,175,55,0.2);}
    .send-btn:hover{transform:translateY(-1px);box-shadow:0 6px 20px rgba(212,175,55,0.3)}
    .file-preview{display:none;margin-top:6px;padding:6px 12px;background:var(--gold-soft);border:1px solid var(--border);border-radius:30px;font-size:0.7rem;color:var(--gold);align-items:center;justify-content:space-between;}
    .file-preview.show{display:flex}
    .file-preview .remove{cursor:pointer;color:var(--muted)}
    .file-preview .remove:hover{color:var(--err)}
    .quick-actions{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px;padding-top:12px;border-top:1px solid var(--border);}
    .quick-section-title{width:100%;font-size:0.62rem;color:var(--muted);letter-spacing:1.5px;text-transform:uppercase;margin:4px 0 2px;}
    .quick-btn{background:rgba(255,255,255,0.04);border:1px solid var(--border);color:var(--text);padding:4px 12px;border-radius:30px;font-size:0.68rem;cursor:pointer;font-family:inherit;transition:all 0.2s ease;}
    .quick-btn:hover{background:var(--gold-soft);color:var(--gold);border-color:var(--gold);transform:translateY(-1px);}
    .quick-btn-oracle{border-color:rgba(255,153,51,0.2);color:#ffbf80;}
    .quick-btn-oracle:hover{background:rgba(255,153,51,0.1);color:var(--saffron);}
    .output-tools{display:flex;flex-wrap:wrap;gap:5px;justify-content:center;margin:8px 0;}
    .footer{margin-top:auto;padding:10px 0;border-top:1px solid var(--border);text-align:center;font-size:0.6rem;color:var(--muted);}
    .footer-links a{color:var(--muted);cursor:pointer;margin:0 6px;text-decoration:none;font-size:0.62rem;}
    .footer-links a:hover{color:var(--gold)}
    .soc2-badge{display:inline-block;background:rgba(52,211,153,0.06);border:1px solid rgba(52,211,153,0.15);color:var(--ok);padding:2px 12px;border-radius:999px;font-size:0.55rem;margin-top:4px;}
    .copyright-notice{font-size:0.6rem;color:#555;margin-top:4px;}
    .copyright-notice strong{color:var(--muted);font-weight:500}
    .modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,0.8);backdrop-filter:blur(10px);z-index:999;display:none;align-items:center;justify-content:center;padding:16px;}
    .modal-overlay.active{display:flex}
    .modal-content{background:var(--panel-2);border:1px solid var(--border);border-radius:18px;padding:24px;max-width:480px;width:100%;max-height:82vh;overflow-y:auto;position:relative;box-shadow:var(--shadow);}
    .modal-content h3{color:var(--gold);margin-bottom:12px;font-family:'Cormorant Garamond',serif;font-size:1.3rem;}
    .modal-content .close-btn{position:absolute;top:12px;right:16px;background:none;border:none;color:var(--muted);font-size:1.4rem;cursor:pointer;}
    .modal-content .close-btn:hover{color:var(--text)}
    .modal-content input{width:100%;padding:8px 12px;background:rgba(255,255,255,0.04);border:1px solid var(--border);color:var(--text);border-radius:10px;margin-bottom:10px;font-family:inherit;font-size:0.85rem;}
    .modal-actions{display:flex;gap:8px;justify-content:flex-end;margin-top:12px;flex-wrap:wrap;}
    @media(max-width:520px){
      .om-5d-wrapper{width:40vmin;height:40vmin}
      .om-face-5d{font-size:18vmin}
      .brand-name{font-size:1.2rem}
      .container{padding:0 10px 10px}
      .chat-container{max-height:40vh}
      .moon{width:22vmin;height:22vmin}
    }
    .verification-badge {
      margin-top: 8px;
      padding: 6px 12px;
      background: rgba(0,0,0,0.25);
      border-radius: 12px;
      display: inline-block;
      border: 1px solid var(--border);
    }
  </style>
</head>
<body>
  <div class="moon"></div>
  <div class="infinite-rings" id="ringContainer"></div>
  <div class="om-5d-wrapper">
    <div class="om-5d">
      <div class="om-face-5d front">ॐ</div>
      <div class="om-face-5d back">ॐ</div>
      <div class="om-face-5d left">ॐ</div>
      <div class="om-face-5d right">ॐ</div>
      <div class="om-face-5d top">ॐ</div>
      <div class="om-face-5d bottom">ॐ</div>
    </div>
  </div>
  <div class="stars" id="starsContainer"></div>
  <div class="wisdom-tagline">ॐ Wisdom for the Awakening Mind</div>
  <div class="container">
    <div class="header">
      <div class="brand-name">
        LEXSARTHI <span class="version-badge">v9.0</span>
        <span id="premiumBadge" class="premium-badge">⭐ PREMIUM</span>
        <span id="enterpriseBadge" class="enterprise-badge">🏢 ENTERPRISE</span>
      </div>
      <div class="header-actions">
        <button class="settings-btn" onclick="toggleSettings()"><i class="fas fa-cog"></i></button>
        <button class="btn btn-outline btn-sm" onclick="showLogin()">🔐 Login</button>
        <button class="btn btn-gold btn-sm" onclick="showPayment()">💳 Plans</button>
        <button class="btn btn-outline btn-sm" onclick="showMyUsage()">📊 Usage</button>
      </div>
      <div class="settings-panel" id="settingsPanel">
        <label for="langSelect">🌐 Language</label>
        <select id="langSelect">
          <option value="en">English</option><option value="hi">हिन्दी</option>
          <option value="sa">संस्कृतम्</option><option value="bn">বাংলা</option>
          <option value="es">Español</option><option value="fr">Français</option>
          <option value="de">Deutsch</option><option value="pt">Português</option>
          <option value="it">Italiano</option><option value="ru">Русский</option>
          <option value="ar">العربية</option><option value="zh">中文</option>
          <option value="ja">日本語</option><option value="ko">한국어</option>
          <option value="th">ไทย</option><option value="vi">Tiếng Việt</option>
          <option value="id">Bahasa Indonesia</option><option value="he">עברית</option>
          <option value="el">Ελληνικά</option><option value="tr">Türkçe</option>
        </select>
        <label for="modelSelect">🧠 AI Model</label>
        <select id="modelSelect">
          <option value="llama-3.3-70b-versatile">Groq · Llama 3.3 70B</option>
          <option value="gpt-4o-mini">OpenAI · GPT-4o mini</option>
          <option value="gemini-pro">Google · Gemini Pro</option>
        </select>
        <hr class="settings-divider" />
        <div style="display:flex;gap:4px;flex-wrap:wrap;justify-content:center;font-size:0.62rem">
          <a onclick="openModal('termsModal')" style="color:var(--gold);cursor:pointer">Terms</a> ·
          <a onclick="openModal('privacyModal')" style="color:var(--gold);cursor:pointer">Privacy</a> ·
          <a onclick="openModal('aboutModal')" style="color:var(--gold);cursor:pointer">About</a> ·
          <a onclick="openModal('verifiersModal')" style="color:var(--gold);cursor:pointer">Verifiers</a>
        </div>
      </div>
    </div>

    <div class="chat-container" id="chatContainer">
      <div id="chatArea"></div>
      <div id="defaultWelcome">
        <div class="welcome-om">ॐ</div>
        <div class="welcome-title">Universal Default OS</div>
        <div class="welcome-sub">
          <strong>LexSarthi</strong> — 250 specialists, RAG knowledge base, live web search, and a <strong>jury of 3 verifiers</strong> for bullet‑proof answers.
        </div>
      </div>
      <div id="typingIndicator" class="typing-indicator">
        <span class="om-spinner">ॐ</span><span>Consulting specialists & jury…</span>
        <div class="typing-dots"><span></span><span></span><span></span></div>
      </div>
    </div>

    <div class="input-card">
      <textarea class="query-input" id="queryInput" placeholder="Ask the Council — Law · GST · ITR · Audit · Math · Science · Mythology · Oracle Wisdom..."></textarea>
      <div class="input-tools">
        <label class="tool-btn"><i class="fas fa-file-pdf"></i> PDF
          <input type="file" id="pdfUpload" accept=".pdf,.docx,.jpg,.png" hidden multiple onchange="handleFileUpload(this)" /></label>
        <button class="tool-btn" id="voiceBtn" onclick="startVoice()"><i class="fas fa-microphone"></i> Voice</button>
        <label class="web-toggle-label"><input type="checkbox" id="webSearchToggle" checked /> <i class="fas fa-globe"></i> Web</label>
        <label class="web-toggle-label oracle-toggle"><input type="checkbox" id="oracleModeToggle" /> 🕉️ Oracle</label>
        <label class="tool-btn"><i class="fas fa-layer-group"></i> Bulk
          <input type="file" id="bulkUpload" accept=".pdf,.docx,.jpg,.png" hidden multiple onchange="handleBulkUpload(this)" /></label>
        <button class="send-btn" onclick="sendQuery()"><i class="fas fa-paper-plane"></i> Ask</button>
      </div>
      <div id="filePreview" class="file-preview"><span id="filePreviewText"></span><span class="remove" onclick="clearFilePreview()">✕</span></div>

      <div class="quick-actions">
        <span class="quick-section-title">⚖️ Legal & CA</span>
        <button class="quick-btn" onclick="quickAction('Review this contract clause-by-clause and identify risks.')">📄 Contract Review</button>
        <button class="quick-btn" onclick="quickAction('Draft a standard mutual NDA under Indian law.')">📝 NDA</button>
        <button class="quick-btn" onclick="quickAction('Research recent Indian case laws on: ' )">🔍 Case Research</button>
        <button class="quick-btn" onclick="quickAction('How to file GSTR-3B for a small business? Step by step.')">📊 GST</button>
        <button class="quick-btn" onclick="quickAction('How to file ITR-4 under presumptive taxation?')">💰 ITR</button>
        <button class="quick-btn" onclick="quickAction('Steps to incorporate a Private Limited Company in India.')">🏢 Incorporate</button>
        <button class="quick-btn" onclick="quickAction('How to register a Partnership Firm in India?')">🤝 Partnership</button>
        <button class="quick-btn" onclick="quickAction('Explain the process of a statutory audit under Companies Act 2013.')">📋 Audit</button>
        <span class="quick-section-title">🕉️ Oracle — Real-Life Wisdom</span>
        <button class="quick-btn quick-btn-oracle" onclick="oracleAsk('What is the meaning of life?')">🌺 Life</button>
        <button class="quick-btn quick-btn-oracle" onclick="oracleAsk('How to find true love?')">❤️ Love</button>
        <button class="quick-btn quick-btn-oracle" onclick="oracleAsk('What is my life purpose?')">🎯 Purpose</button>
        <button class="quick-btn quick-btn-oracle" onclick="oracleAsk('How to overcome fear and anxiety?')">🔥 Fear</button>
        <button class="quick-btn quick-btn-oracle" onclick="oracleAsk('How to be happy every day?')">😊 Happiness</button>
        <button class="quick-btn quick-btn-oracle" onclick="oracleAsk('How to deal with stress at work?')">💼 Work Stress</button>
        <button class="quick-btn quick-btn-oracle" onclick="oracleAsk('How to heal a broken heart?')">💔 Heartbreak</button>
        <button class="quick-btn quick-btn-oracle" onclick="oracleAsk('What is the secret to success?')">🏆 Success</button>
        <button class="quick-btn quick-btn-oracle" onclick="oracleAsk('How to find inner peace?')">🕊️ Peace</button>
        <button class="quick-btn quick-btn-oracle" onclick="oracleAsk('What is karma?')">🌀 Karma</button>
        <button class="quick-btn quick-btn-oracle" onclick="oracleAsk('How to forgive someone who hurt you?')">💖 Forgiveness</button>
        <button class="quick-btn quick-btn-oracle" onclick="oracleAsk('What is the nature of the soul?')">✨ Soul</button>
        <button class="quick-btn quick-btn-oracle" onclick="oracleAsk('How to live in the present moment?')">🧘 Presence</button>
        <button class="quick-btn quick-btn-oracle" onclick="oracleAsk('What is enlightenment?')">🧘 Enlightenment</button>
        <button class="quick-btn quick-btn-oracle" onclick="oracleAsk('How to attract abundance?')">💰 Abundance</button>
        <button class="quick-btn quick-btn-oracle" onclick="oracleAsk('What happens after death?')">♾️ Afterlife</button>
        <button class="quick-btn quick-btn-oracle" onclick="oracleAsk('How to build self-confidence?')">💪 Confidence</button>
        <button class="quick-btn quick-btn-oracle" onclick="oracleAsk('How to improve relationships?')">👫 Relationships</button>
        <button class="quick-btn quick-btn-oracle" onclick="oracleAsk('How to find your true calling?')">🎯 Calling</button>
        <button class="quick-btn quick-btn-oracle" onclick="oracleAsk('How to let go of anger?')">🔥 Anger</button>
        <button class="quick-btn quick-btn-oracle" onclick="oracleAsk('What is the universe?')">🌌 Universe</button>
        <button class="quick-btn quick-btn-oracle" onclick="oracleAsk('How to be a better person?')">🌟 Better Self</button>
        <button class="quick-btn quick-btn-oracle" onclick="oracleAsk('How to cope with loss?')">🕊️ Loss</button>
        <button class="quick-btn quick-btn-oracle" onclick="oracleAsk('What is true friendship?')">🤝 Friendship</button>
        <button class="quick-btn quick-btn-oracle" onclick="oracleAsk('How to stay motivated?')">⚡ Motivation</button>
        <button class="quick-btn quick-btn-oracle" onclick="oracleAsk('How to make a decision?')">🤔 Decision</button>
        <button class="quick-btn quick-btn-oracle" onclick="oracleAsk('How to find gratitude?')">🙏 Gratitude</button>
        <button class="quick-btn quick-btn-oracle" onclick="oracleAsk('How to trust the universe?')">🌠 Trust</button>
        <button class="quick-btn quick-btn-oracle" onclick="oracleAsk('How to heal past trauma?')">🩹 Healing</button>
        <button class="quick-btn quick-btn-oracle" onclick="oracleAsk('What is the meaning of suffering?')">🌧️ Suffering</button>
        <button class="quick-btn quick-btn-oracle" onclick="oracleAsk('How to live a balanced life?')">⚖️ Balance</button>
      </div>
      <div class="status-text" id="inputStatus"></div>
    </div>

    <div class="output-tools">
      <button class="tool-btn" onclick="copyResponse()"><i class="fas fa-copy"></i> Copy</button>
      <button class="tool-btn" onclick="downloadTXT()"><i class="fas fa-file-alt"></i> TXT</button>
      <button class="tool-btn" onclick="downloadPDF()"><i class="fas fa-file-pdf"></i> PDF</button>
      <button class="tool-btn speak-btn" onclick="speakResponse()"><i class="fas fa-volume-up"></i> Speak</button>
      <button class="tool-btn" onclick="clearResponse()"><i class="fas fa-trash"></i> Clear</button>
    </div>

    <div class="footer">
      <div class="footer-links">
        <a onclick="openModal('termsModal')">Terms</a> ·
        <a onclick="openModal('privacyModal')">Privacy</a> ·
        <a onclick="openModal('aboutModal')">About</a> ·
        <a onclick="openModal('verifiersModal')">Verifiers</a> ·
        <a onclick="showMyUsage()">Usage</a> ·
        <a onclick="showPayment()">Plans</a>
      </div>
      <div class="soc2-badge">🔒 Zero Retention · DPDPA · Encrypted</div>
      <div class="copyright-notice">© 2026 LexSarthi v9.0 · <strong>THE ADVOCACY — A LAW FIRM</strong></div>
    </div>
  </div>

  <!-- Modals -->
  <div class="modal-overlay" id="loginModal">
    <div class="modal-content">
      <button class="close-btn" onclick="closeModal('loginModal')">&times;</button>
      <h3>🔐 Login / Register</h3>
      <input id="login-email" type="email" placeholder="Email" value="counsel@advocacyalawfrim.in" />
      <input id="login-password" type="password" placeholder="Password" value="Password123!" />
      <div style="display:flex;gap:8px">
        <button class="btn btn-gold btn-sm" onclick="handleLogin()" style="flex:1;padding:8px">Login</button>
        <button class="btn btn-outline btn-sm" onclick="handleRegister()" style="flex:1;padding:8px">Register</button>
      </div>
      <div id="login-status" class="status-text"></div>
    </div>
  </div>

  <div class="modal-overlay" id="myUsageModal">
    <div class="modal-content">
      <button class="close-btn" onclick="closeModal('myUsageModal')">&times;</button>
      <h3>📊 My Usage</h3>
      <div id="myUsageContent"><p style="color:var(--muted)">Loading...</p></div>
    </div>
  </div>

  <div class="modal-overlay" id="paymentModal">
    <div class="modal-content">
      <button class="close-btn" onclick="closeModal('paymentModal')">&times;</button>
      <h3>💳 Choose Your Plan</h3>
      <div onclick="selectPlan('lifetime')" style="background:var(--gold-soft);border:2px solid var(--gold);padding:12px;border-radius:12px;margin:8px 0;cursor:pointer">
        <strong>🙏 ₹2 Lifetime</strong> <span style="font-size:0.65rem;color:var(--muted)">(first 1000 seekers)</span>
        <span id="lifetimeCount" style="float:right;font-size:0.7rem;color:var(--gold)"></span>
      </div>
      <div onclick="selectPlan('premium')" style="background:rgba(52,211,153,0.05);border:1px solid rgba(52,211,153,0.2);padding:12px;border-radius:12px;margin:8px 0;cursor:pointer">
        <strong>⭐ ₹102 / month · Premium</strong>
      </div>
      <div onclick="selectPlan('enterprise')" style="background:rgba(124,58,237,0.05);border:1px solid rgba(124,58,237,0.2);padding:12px;border-radius:12px;margin:8px 0;cursor:pointer">
        <strong>🏢 ₹1011 / month · Enterprise</strong>
      </div>
      <input type="hidden" id="paymentPlan" value="lifetime" />
      <button class="btn btn-gold" onclick="processPayment()" style="width:100%;padding:10px;margin-top:8px">Subscribe Securely</button>
      <div id="payment-status" class="status-text"></div>
      <div style="margin-top:10px;font-size:0.6rem;color:var(--muted);text-align:center">🔒 Powered by Razorpay</div>
    </div>
  </div>

  <div class="modal-overlay" id="termsModal">
    <div class="modal-content"><button class="close-btn" onclick="closeModal('termsModal')">&times;</button>
      <h3>📜 Terms of Use</h3>
      <p style="font-size:0.85rem;color:var(--text);line-height:1.6">By using LexSarthi you agree that AI-generated responses are informational only and NOT a substitute for licensed legal, medical, or financial advice. Always verify with a qualified professional before acting.</p>
      <div class="modal-actions"><button class="btn btn-gold btn-sm" onclick="closeModal('termsModal')">Close</button></div>
    </div>
  </div>
  <div class="modal-overlay" id="privacyModal">
    <div class="modal-content"><button class="close-btn" onclick="closeModal('privacyModal')">&times;</button>
      <h3>🔒 Privacy — Zero Retention</h3>
      <p style="font-size:0.85rem;line-height:1.6">All queries are automatically purged within 24 hours. We do not train models on your data. DPDPA-2023 compliant.</p>
      <div class="modal-actions"><button class="btn btn-gold btn-sm" onclick="closeModal('privacyModal')">Close</button></div>
    </div>
  </div>
  <div class="modal-overlay" id="aboutModal">
    <div class="modal-content"><button class="close-btn" onclick="closeModal('aboutModal')">&times;</button>
      <h3>ℹ️ About LexSarthi v9.0</h3>
      <p style="font-size:0.85rem;line-height:1.7">
        <strong style="color:var(--gold)">LexSarthi</strong> is the Universal Default OS, built by <strong>THE ADVOCACY — A LAW FIRM</strong>.
        It features <strong>250 specialist personas</strong>, a <strong>RAG knowledge base</strong>, live web search, and a <strong>jury of 3 verifiers + a final judge</strong> that debate every answer before you see it.
        Zero data retention. Scalable to millions.
      </p>
      <div class="modal-actions"><button class="btn btn-gold btn-sm" onclick="closeModal('aboutModal')">Close</button></div>
    </div>
  </div>
  <div class="modal-overlay" id="verifiersModal">
    <div class="modal-content"><button class="close-btn" onclick="closeModal('verifiersModal')">&times;</button>
      <h3>✅ The 10 Verifiers (Jury + Judge)</h3>
      <p style="font-size:0.75rem;color:var(--muted);margin-bottom:10px;">3 verifiers are selected for each query to critique the answer; Shakti then delivers the final verdict.</p>
      <div style="display:grid;grid-template-columns:1fr;gap:6px;font-size:0.78rem">
        <div><strong style="color:var(--gold)">Ganesha</strong> — Citation & logic integrity</div>
        <div><strong style="color:var(--gold)">Saraswati</strong> — Knowledge cross-reference</div>
        <div><strong style="color:var(--gold)">Hanuman</strong> — Global compliance</div>
        <div><strong style="color:var(--gold)">Kartikeya</strong> — Contradiction detection</div>
        <div><strong style="color:var(--gold)">Indra</strong> — Jurisdiction mapping</div>
        <div><strong style="color:var(--gold)">Yama</strong> — Bias & neutrality</div>
        <div><strong style="color:var(--gold)">Surya</strong> — Timeline & limitation</div>
        <div><strong style="color:var(--gold)">Chandra</strong> — Precedent match</div>
        <div><strong style="color:var(--gold)">Vayu</strong> — PII / privacy filter</div>
        <div><strong style="color:var(--saffron)">Shakti</strong> — Final judge & dharma seal</div>
      </div>
      <div class="modal-actions"><button class="btn btn-gold btn-sm" onclick="closeModal('verifiersModal')">Close</button></div>
    </div>
  </div>

  <script>
    const API_BASE = 'https://upamnyu12-lex.hf.space';
    let uploadedFiles = [];
    let isSpeaking = false;

    (function(){ const container = document.getElementById('ringContainer'); for(let i=0;i<40;i++){ const ring=document.createElement('div'); ring.className='ring-bg'; const size=80+Math.random()*350; const duration=6+Math.random()*10; const delay=(i/40)*14; ring.style.width=size+'px'; ring.style.height=size+'px'; ring.style.setProperty('--duration',duration+'s'); ring.style.animationDelay=delay+'s'; ring.style.borderColor=`rgba(212,175,55,${0.04+Math.random()*0.12})`; container.appendChild(ring); } })();
    (function(){ const c=document.getElementById('starsContainer'); for(let i=0;i<80;i++){ const s=document.createElement('div'); s.className='star'; const sz=Math.random()*2+0.5; s.style.cssText=`width:${sz}px;height:${sz}px;left:${Math.random()*100}%;top:${Math.random()*100}%;--duration:${Math.random()*3+2}s;animation-delay:${Math.random()*5}s;`; c.appendChild(s); } })();

    function getToken(){ return localStorage.getItem('lex_token'); }
    function setTyping(a){ document.getElementById('typingIndicator').classList.toggle('active', a); }
    function openModal(id){ document.getElementById(id).classList.add('active'); }
    function closeModal(id){ document.getElementById(id).classList.remove('active'); }
    function showLogin(){ openModal('loginModal'); }
    function toggleSettings(){ document.getElementById('settingsPanel').classList.toggle('open'); }
    function setStatus(t){ document.getElementById('inputStatus').textContent = t || ''; }
    function quickAction(p){ const i=document.getElementById('queryInput'); i.value=p; i.focus(); sendQuery(); }
    function oracleAsk(q){ document.getElementById('oracleModeToggle').checked=true; quickAction(q); }

    const LANG_VOICE = {en:'en-US',hi:'hi-IN',sa:'hi-IN',bn:'bn-IN',es:'es-ES',fr:'fr-FR',de:'de-DE',pt:'pt-BR',it:'it-IT',ru:'ru-RU',ar:'ar-SA',zh:'zh-CN',ja:'ja-JP',ko:'ko-KR',th:'th-TH',vi:'vi-VN',id:'id-ID',he:'he-IL',el:'el-GR',tr:'tr-TR'};

    function startVoice(){
      try{
        const R=window.SpeechRecognition||window.webkitSpeechRecognition;
        if(!R){ setStatus('❌ Voice not supported'); return; }
        const r=new R(); r.lang=LANG_VOICE[document.getElementById('langSelect').value]||'en-US';
        r.continuous=false; r.interimResults=false;
        const btn=document.getElementById('voiceBtn');
        r.onstart=()=>{ btn.innerHTML='<i class="fas fa-microphone-slash"></i>'; setStatus('🎤 Listening...'); };
        r.onresult=e=>{ document.getElementById('queryInput').value=e.results[0][0].transcript; setStatus('✅ Captured'); };
        r.onerror=()=>{ setStatus('❌ Voice error'); };
        r.onend=()=>{ btn.innerHTML='<i class="fas fa-microphone"></i>'; };
        r.start();
      }catch(e){ setStatus('❌ '+e.message); }
    }

    function speakResponse(){
      const t = document.getElementById('chatArea').innerText || '';
      if(!t.trim()){ alert('Nothing to speak.'); return; }
      if (isSpeaking) {
        window.speechSynthesis.cancel();
        isSpeaking = false;
        document.querySelector('.speak-btn').innerHTML = '<i class="fas fa-volume-up"></i> Speak';
        setStatus('🔇 Stopped');
        return;
      }
      const u = new SpeechSynthesisUtterance(t.slice(0,3000));
      u.lang = LANG_VOICE[document.getElementById('langSelect').value] || 'en-US';
      u.rate = 0.85; u.pitch = 0.9;
      const voices = window.speechSynthesis.getVoices();
      const preferredVoice = voices.find(v => v.name.includes('Google US English') && v.name.includes('Female')) || voices.find(v => v.name.includes('Samantha')) || voices.find(v => v.lang.startsWith('en'));
      if (preferredVoice) u.voice = preferredVoice;
      u.onend = () => { isSpeaking = false; document.querySelector('.speak-btn').innerHTML = '<i class="fas fa-volume-up"></i> Speak'; setStatus('🔊 Finished'); };
      u.onerror = () => { isSpeaking = false; document.querySelector('.speak-btn').innerHTML = '<i class="fas fa-volume-up"></i> Speak'; setStatus('❌ Speech error'); };
      window.speechSynthesis.speak(u);
      isSpeaking = true;
      document.querySelector('.speak-btn').innerHTML = '<i class="fas fa-stop"></i> Stop';
      setStatus('🔊 Speaking...');
    }

    async function handleLogin(){
      const email=document.getElementById('login-email').value;
      const pass=document.getElementById('login-password').value;
      const s=document.getElementById('login-status'); s.textContent='Logging in...';
      try{
        const r=await fetch(`${API_BASE}/auth/login`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:email,password:pass})});
        const d=await r.json();
        if(r.ok){ localStorage.setItem('lex_token',d.access_token); s.textContent='✅ Welcome!'; closeModal('loginModal'); checkPremium(); }
        else s.textContent='❌ '+(d.detail||'Login failed');
      }catch(e){ s.textContent='❌ Network error'; }
    }
    async function handleRegister(){
      const email=document.getElementById('login-email').value;
      const pass=document.getElementById('login-password').value;
      const s=document.getElementById('login-status'); s.textContent='Registering...';
      try{
        const r=await fetch(`${API_BASE}/auth/register`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:email.split('@')[0],email,password:pass,full_name:'User'})});
        const d=await r.json();
        if(r.ok){ s.textContent='✅ Registered! Now login.'; }
        else s.textContent='❌ '+(d.detail||'Registration failed');
      }catch(e){ s.textContent='❌ Network error'; }
    }
    async function checkPremium(){
      const t=getToken(); if(!t) return;
      try{ const r=await fetch(`${API_BASE}/auth/me`,{headers:{'Authorization':`Bearer ${t}`}});
        if(r.ok){ const d=await r.json();
          if(['premium','enterprise','lifetime'].includes(d.tier)) document.getElementById('premiumBadge').style.display='inline-block';
          if(d.tier==='enterprise') document.getElementById('enterpriseBadge').style.display='inline-block';
        }}catch{}
    }
    async function showMyUsage(){
      const t=getToken(); if(!t){ alert('Login first'); showLogin(); return; }
      openModal('myUsageModal');
      try{ const r=await fetch(`${API_BASE}/my-usage`,{headers:{'Authorization':`Bearer ${t}`}});
        const d=await r.json();
        document.getElementById('myUsageContent').innerHTML=`<p>Total Queries: <strong>${d.total_queries}</strong></p><p>Today: <strong>${d.queries_today}</strong></p>`;
      }catch{ document.getElementById('myUsageContent').innerHTML='<p style="color:var(--err)">Error loading</p>'; }
    }

    function handleFileUpload(inp){
      uploadedFiles = Array.from(inp.files);
      if (uploadedFiles.length > 0) {
        document.getElementById('filePreviewText').textContent = `📎 ${uploadedFiles.length} file(s): ${uploadedFiles.map(f=>f.name).join(', ')}`;
        document.getElementById('filePreview').classList.add('show');
        setStatus(`📄 Attached: ${uploadedFiles.map(f=>f.name).join(', ')}`);
      } else { clearFilePreview(); }
    }
    function clearFilePreview(){
      uploadedFiles = [];
      document.getElementById('filePreview').classList.remove('show');
      document.getElementById('pdfUpload').value = '';
    }

    async function handleBulkUpload(inp){
      const t=getToken(); if(!t){ alert('Login first'); showLogin(); return; }
      const files=inp.files; if(!files.length) return;
      const fd=new FormData();
      for(const f of files) fd.append('files',f);
      fd.append('query', document.getElementById('queryInput').value || 'Analyze these documents');
      fd.append('model', document.getElementById('modelSelect').value);
      fd.append('lang',Badge').style.display='inline-block';
        }}catch{}
    }
    async function showMyUsage(){
      const t=getToken(); if(!t){ alert('Login first'); showLogin(); return; }
      openModal('myUsageModal');
      try{ const r=await fetch(`${API_BASE}/my-usage`,{headers:{'Authorization':`Bearer ${t}`}});
        const d=await r.json();
        document.getElementById('myUsageContent').innerHTML=`<p>Total Queries: <strong>${d.total_queries}</strong></p><p>Today: <strong>${d.queries_today}</strong></p>`;
      }catch{ document.getElementById('myUsageContent').innerHTML='<p style="color:var(--err)">Error loading</p>'; }
    }

    function handleFileUpload(inp){
      uploadedFiles = Array.from(inp.files);
      if (uploadedFiles.length > 0) {
        document.getElementById('filePreviewText').textContent = `📎 ${uploadedFiles.length} file(s): ${uploadedFiles.map(f=>f.name).join(', ')}`;
        document.getElementById('filePreview').classList.add('show');
        setStatus(`📄 Attached: ${uploadedFiles.map(f=>f.name).join(', ')}`);
      } else { clearFilePreview(); }
    }
    function clearFilePreview(){
      uploadedFiles = [];
      document.getElementById('filePreview').classList.remove('show');
      document.getElementById('pdfUpload').value = '';
    }

    async function handleBulkUpload(inp){
      const t=getToken(); if(!t){ alert('Login first'); showLogin(); return; }
      const files=inp.files; if(!files.length) return;
      const fd=new FormData();
      for(const document.getElementById('langSelect').value);
      setStatus(`📦 Processing ${files.length} files...`);
      try{
        const r=await fetch(`${API_BASE}/bulk-upload`,{method:'POST',headers:{'Authorization':`Bearer ${t}`},body:fd});
        const d=await r.json();
        if(r.ok) setStatus(`✅ Job ${d.job_id.slice(0,8)}... queued (${d.total_files} files)`);
        else setStatus('❌ '+(d.detail||'Bulk failed'));
      }catch(e){ setStatus('❌ '+e.message); }
      inp.value='';
    }

    async function sendQuery(){
      const q = document.getElementById('queryInput').value.trim();
      if(!q && uploadedFiles.length===0){ setStatus('Type a question or attach files'); return; }
      const t = getToken(); if(!t){ alert('Login first'); showLogin(); return; }

      setTyping(true); setStatus('Consulting specialists & jury…');
      const chat = document.getElementById('chatArea');
      const welcome = document.getElementById('defaultWelcome');
      if(welcome) welcome.style.display = 'none';

      const oracle = document.getElementById('oracleModeToggle').checked;
      let userHtml = (oracle?'🔮 ':'') + (q||'📎 Files attached');
      if(uploadedFiles.length) userHtml += `<br><span style="font-size:0.65rem;color:var(--gold)">📎 ${uploadedFiles.map(f=>f.name).join(', ')}</span>`;
      chat.innerHTML += `<div class="chat-bubble user">${userHtml}</div>`;
      chat.scrollTop f of files) fd.append('files',f);
      fd.append('query', document.getElementById('queryInput').value || 'Analyze these documents');
      fd.append('model', document.getElementById('modelSelect').value);
      fd.append('lang', document.getElementById('langSelect').value);
      setStatus(`📦 Processing ${files.length} files...`);
      try{
        const r=await fetch(`${API_BASE}/bulk-upload`,{method:'POST',headers:{'Authorization':`Bearer ${t}`},body:fd});
        const d=await r.json();
        if(r.ok) setStatus(`✅ Job ${d.job_id.slice(0,8)}... queued (${d.total_files} files)`);
        else setStatus('❌ '+(d.detail||'Bulk failed'));
      }catch(e){ setStatus('❌ '+e.message); }
      inp.value='';
    }

    async function sendQuery(){
      const q = document.getElementById('queryInput').value.trim();
      if(!q && uploadedFiles.length===0){ setStatus('Type a question or attach files'); return; }
      const t = getToken(); if(!t){ alert('Login first'); showLogin(); return; }

      setTyping(true); setStatus('Consulting specialists & jury…');
      const chat = document.getElementById('chatArea');
      const welcome = document.getElementById('defaultWelcome');
      if(welcome) welcome.style.display = 'none';

      const oracle = document.getElementById('oracleModeToggle').checked;
      let userHtml = (oracle?'🔮 ':'') + (q||'📎 Files attached');
      if(uploadedFiles.length) userHtml += `<br><span style="font-size:0.65rem;color:var(--gold)">📎 ${uploadedFiles.map(f=>f.name).join(', ')}</span>`;
      chat.innerHTML += `<div class="chat-bubble user">${userHtml}</div>`;
      chat.scrollTop = chat.scrollHeight;

      const fd = new FormData();
      fd.append('query', q || 'Analyze uploaded documents');
      uploadedFiles.forEach(f => fd.append('files', f));
      fd.append('search_web', document.getElementById('webSearchToggle').checked ? 'on' : 'off');
      fd.append('model', document.getElementById('modelSelect').value);
      fd.append('lang', document.getElementById('langSelect').value);
      fd.append('oracle_mode', oracle ? 'true' : 'false');
      fd.append('agent_id','agent_001');

      try {
 = chat.scrollHeight;

      const fd = new FormData();
      fd.append('query', q || 'Analyze uploaded documents');
      uploadedFiles.forEach(f => fd.append('files', f));
      fd.append('search_web', document.getElementById('webSearchToggle').checked ? 'on' : 'off');
      fd.append('model', document.getElementById('modelSelect').value);
      fd.append('lang', document.getElementById('langSelect').value);
      fd.append('oracle_mode', oracle ? 'true' : 'false');
      fd.append('agent_id','agent_001');

      try {
        const response = await fetch(`${API_BASE}/ask`, {
          method:'POST',
          headers:{'Authorization':`Bearer ${t}`},
          body: fd
        });

        if (!response.ok) {
          const err = await response.json();
          setTyping(false);
          chat.innerHTML += `<div class="chat-bubble agent" style="color:var(--err)">${err.detail||'Server error'}</div>`;
          setStatus('❌ '+(err.detail||'Error'));
          return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let agentBubble = null;
        let finalVerification = null;

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const text = decoder.decode(value, { stream: true });
          const lines = text.split('\n');
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const dataStr = line.slice(6);
              if (dataStr === '[DONE]') break;
              try {
                const data = JSON.parse(dataStr);
                if (data.token && !agentBubble        const response = await fetch(`${API_BASE}/ask`, {
          method:'POST',
          headers:{'Authorization':`Bearer ${t}`},
          body: fd
        });

        if (!response.ok) {
          const err = await response.json();
          setTyping(false);
          chat.innerHTML += `<div class="chat-bubble agent" style="color:var(--err)">${err.detail||'Server error'}</div>`;
          setStatus('❌ '+(err.detail||'Error'));
          return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let agentBubble = null;
        let finalVerification = null;

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const text = decoder.decode(value, { stream: true });
          const lines = text.split('\n');
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const dataStr = line.slice(6);
              if (dataStr === '[DONE]') break;
              try {
                const data = JSON.parse(dataStr);
                if (data.token && !agentBubble) {
                  agentBubble = document.createElement('div');
                  agentBubble.className = 'chat-bubble agent';
                  chat.appendChild(agentBubble);
                }
                if (data.token && agentBubble) {
                  const tokenHtml = data.token.replace(/\n/g, '<br>');
                  agentBubble.innerHTML += tokenHtml;
                  chat.scrollTop = chat.scrollHeight;
                }
                if (data.verification) {
                  finalVerification = data.verification;
                }
              } catch(e) {}
            }
          }
        }

        setTyping(false);
        if (agentBubble && finalVerification) {
          const badge = document.createElement('div) {
                  agentBubble = document.createElement('div');
                  agentBubble.className = 'chat-bubble agent';
                  chat.appendChild(agentBubble);
                }
                if (data.token && agentBubble) {
                  const tokenHtml = data.token.replace(/\n/g, '<br>');
                  agentBubble.innerHTML += tokenHtml;
                  chat.scrollTop = chat.scrollHeight;
                }
                if (data.verification) {
                  finalVerification = data.verification;
                }
              } catch(e) {}
            }
          }
        }

        setTyping(false);
        if (agentBubble && finalVerification) {
          const badge = document.createElement('div');
          badge.className = 'verification-badge';
          const confColor = finalVerification.final_confidence === 'HIGH' ? 'var(--ok)' :
                            finalVerification.final_confidence === 'MEDIUM' ? 'var(--gold)' : 'var(--err)';
          const verifierList = finalVerification.jury_verifiers.join(', ');
          badge.innerHTML = `
            <div style="font-size:0.7rem; color:var(--text);">
              <span style="color:${confColor}; font-weight:bold;">✓ Jury Verified</span> – ${finalVerification.final_confidence} confidence
            </div>
            <div style="font-size:0.6rem; color:var(--muted);">Reviewed by: ${verifierList}</div>
            <div style="font-size:0.6rem; color:var(--muted);">Judge: ${finalVerification.judge}</div>
          `;
          agentBubble.appendChild(badge);
          chat.scrollTop = chat.scrollHeight;
        }
        if (agentBubble) { setStatus('✅ Response ready'); }
        else { setStatus('⚠️ No response'); }
      } catch(e) {
        setTyping(false);
        chat');
          badge.className = 'verification-badge';
          const confColor = finalVerification.final_confidence === 'HIGH' ? 'var(--ok)' :
                            finalVerification.final_confidence === 'MEDIUM' ? 'var(--gold)' : 'var(--err)';
          const verifierList = finalVerification.jury_verifiers.join(', ');
          badge.innerHTML = `
            <div style="font-size:0.7rem; color:var(--text);">
              <span style="color:${confColor}; font-weight:bold;">✓ Jury Verified</span> – ${finalVerification.final_confidence} confidence
            </div>
            <div style="font-size:0.6rem; color:var(--muted);">Reviewed by: ${verifierList}</div>
            <div style="font-size:0.6rem; color:var(--muted);">Judge: ${finalVerification.judge}</div>
          `;
          agentBubble.appendChild(badge);
          chat.scrollTop = chat.scrollHeight;
        }
        if (agentBubble) { setStatus('✅ Response ready'); }
        else { setStatus('⚠️ No response'); }
      } catch(e) {
        setTyping(false);
        chat.innerHTML += `<div class="chat-bubble agent" style="color:var(--err)">Network error: ${e.message}</div>`;
        setStatus('❌ Network error');
      }
      clearFilePreview();
      document.getElementById('queryInput').value = '';
    }

    function copyResponse(){
      navigator.clipboard.writeText(document.getElementById('chatArea').innerText||'').then(()=>setStatus('✅ Copied'));
    }
    function downloadTXT(){
      const txt=document.getElementById('chatArea').innerText||'';
      const b=new Blob([txt],{type:'text/plain'}); const a=document.createElement('a');
      a.href=URL.createObjectURL(b); a.download='lexsarthi.txt'; a.click();
    }
    function downloadPDF(){
      const el=document.getElementById('chatArea.innerHTML += `<div class="chat-bubble agent" style="color:var(--err)">Network error: ${e.message}</div>`;
        setStatus('❌ Network error');
      }
      clearFilePreview();
      document.getElementById('queryInput').value = '';
    }

    function copyResponse(){
      navigator.clipboard.writeText(document.getElementById('chatArea').innerText||'').then(()=>setStatus('✅ Copied'));
    }
    function downloadTXT(){
      const txt=document.getElementById('chatArea').innerText||'';
      const b=new Blob([txt],{type:'text/plain'}); const a=document.createElement('a');
      a.href=URL.createObjectURL(b); a.download='lexsarthi.txt'; a.click();
    }
    function downloadPDF(){
      const el=document.getElementById('chatArea');
      if(!el.innerText.trim()){ alert('Nothing to export'); return; }
      setStatus('Generating PDF...');
      html2pdf().set({margin:0.5,filename:'lexsarthi.pdf',image:{type:'jpeg',quality:0.98},html2canvas:{scale:2},jsPDF:{unit:'in',format:'a4',orientation:'portrait'}}).from(el).save().then(()=>setStatus('✅ PDF ready')).catch(()=>setStatus('❌ PDF failed'));
    }
    function clearResponse(){
      document.getElementById('chatArea').innerHTML='';
      document.getElementById('defaultWelcome').style.display='block';
      setStatus('');
      if (isSpeaking) { window.speechSynthesis.cancel(); isSpeaking = false; document.querySelector('.speak-btn').innerHTML = '<i class="fas fa-volume-up"></i> Speak'; }
    }
    function showPayment(){ openModal('paymentModal'); checkLifetime(); }
    function selectPlan(p){ document.getElementById('paymentPlan').value');
      if(!el.innerText.trim()){ alert('Nothing to export'); return; }
      setStatus('Generating PDF...');
      html2pdf().set({margin:0.5,filename:'lexsarthi.pdf',image:{type:'jpeg',quality:0.98},html2canvas:{scale:2},jsPDF:{unit:'in',format:'a4',orientation:'portrait'}}).from(el).save().then(()=>setStatus('✅ PDF ready')).catch(()=>setStatus('❌ PDF failed'));
    }
    function clearResponse(){
      document.getElementById('chatArea').innerHTML='';
      document.getElementById('defaultWelcome').style.display='block';
      setStatus('');
      if (isSpeaking) { window.speechSynthesis.cancel(); isSpeaking = false; document.querySelector('.speak-btn').innerHTML = '<i class="fas fa-volume-up"></i> Speak'; }
    }
    function showPayment(){ openModal('paymentModal'); checkLifetime(); }
    function selectPlan(p){ document.getElementById('paymentPlan').value=p; }
    async function checkLifetime(){
      try{ const r=await fetch(`${API_BASE}/lifetime-count`); const d=await r.json();
        document.getElementById('lifetimeCount').textContent=`(${d.remaining} left)`;
      }catch{}
    }
    async function processPayment(){
      const t=getToken(); if(!t){ alert('Login first'); return; }
      const tier=document.getElementById('paymentPlan').value;
      const s=document.getElementById('payment-status'); s.textContent='Creating order...';
      try{
        const r=await fetch(`${API_BASE}/create-order`,{method:'POST',headers:{'Content-Type':'application/json','Authorization':`Bearer ${t}`},body:JSON.stringify({tier})});
        const d=await r.json();
        if(!r.ok){ s.textContent='❌ '+d.detail; return; }
        const opts={ key:d.razorpay_key, amount:d.amount, currency:'INR', name:'LexSarthi', order_id:d.order_id,
          handler:async function(resp){
            const=p; }
    async function checkLifetime(){
      try{ const r=await fetch(`${API_BASE}/lifetime-count`); const d=await r.json();
        document.getElementById('lifetimeCount').textContent=`(${d.remaining} left)`;
      }catch{}
    }
    async function processPayment(){
      const t=getToken(); if(!t){ alert('Login first'); return; }
      const tier=document.getElementById('paymentPlan').value;
      const s=document.getElementById('payment-status'); s.textContent='Creating order...';
      try{
        const r=await fetch(`${API_BASE}/create-order`,{method:'POST',headers:{'Content-Type':'application/json','Authorization':`Bearer ${t}`},body:JSON.stringify({tier})});
        const d=await r.json();
        if(!r.ok){ s.textContent='❌ '+d.detail; return; }
        const opts={ key:d.razorpay_key, amount:d.amount, currency:'INR', name:'LexSarthi', order_id:d.order_id,
          handler:async function(resp){
            const v=await fetch(`${API_BASE}/verify-payment`,{method:'POST',headers:{'Authorization':`Bearer ${t}`},body:new URLSearchParams({razorpay_order_id:resp.razorpay_order_id,razorpay_payment_id:resp.razorpay_payment_id,razorpay_signature:resp.razorpay_signature})});
            const vd=await v.json();
            if(v.ok){ s.textContent='✅ Success! Now '+vd.tier; closeModal('paymentModal'); checkPremium(); }
            else s.textContent='❌ '+vd.detail;
          }, theme:{color:'#d4af37'} };
        new Razorpay(opts).open();
      }catch(e){ s.textContent='❌ '+e.message; }
    }

    document.addEventListener('DOMContentLoaded',()=>{
      if(getToken()) checkPremium v=await fetch(`${API_BASE}/verify-payment`,{method:'POST',headers:{'Authorization':`Bearer ${t}`},body:new URLSearchParams({razorpay_order_id:resp.razorpay_order_id,razorpay_payment_id:resp.razorpay_payment_id,razorpay_signature:resp.razorpay_signature})});
            const vd=await v.json();
            if(v.ok){ s.textContent='✅ Success! Now '+vd.tier; closeModal('paymentModal'); checkPremium(); }
            else s.textContent='❌ '+vd.detail;
          }, theme:{color:'#d4af37'} };
        new Razorpay(opts).open();
      }catch(e){ s.textContent='❌ '+e.message; }
    }

    document.addEventListener('DOMContentLoaded',()=>{
      if(getToken()) checkPremium();
      const inp=document.getElementById('queryInput');
      inp.addEventListener('keydown', e=>{ if(e.key==='Enter' && !e.shiftKey){ e.preventDefault(); sendQuery(); }});
    });
  </script>
</body>
</html>