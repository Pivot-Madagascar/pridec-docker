def get_home_html() -> str:
    return """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Hub Center</title>
  <style>
    :root {
      --amazon-dark: #131921;
      --amazon-orange: #febd69;
      --amazon-light: #f3f3f3;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: ui-sans-serif, system-ui, -apple-system, sans-serif;
      background-color: #f3f4f6;
      color: #111827;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }
    body.dark {
      background-color: #111827;
      color: #f9fafb;
    }
    header {
      background-color: var(--amazon-dark);
      color: #ffffff;
      padding: 1rem 1.5rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      box-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    header h1 { font-size: 1.125rem; font-weight: 700; }
    header .header-right { display: flex; align-items: center; gap: 1rem; }
    .env-badge {
      background-color: var(--amazon-orange);
      color: var(--amazon-dark);
      font-size: 0.75rem;
      font-weight: 700;
      padding: 0.125rem 0.5rem;
      border-radius: 0.25rem;
    }
    .dark-mode-btn {
      padding: 0.25rem 0.75rem;
      border-radius: 0.375rem;
      border: none;
      cursor: pointer;
      font-size: 0.875rem;
      background-color: var(--amazon-light);
      color: #111827;
    }
    body.dark .dark-mode-btn { background-color: #374151; color: #f9fafb; }

    main {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 2rem;
    }
    .card {
      width: 100%;
      max-width: 28rem;
      background: #ffffff;
      border-radius: 1rem;
      box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
      padding: 2rem;
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }
    body.dark .card { background: #1f2937; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.4); }
    .card-title { text-align: center; }
    .card-title h2 { font-size: 1.875rem; font-weight: 700; color: var(--amazon-dark); }
    body.dark .card-title h2 { color: #f9fafb; }
    .card-title p { margin-top: 0.5rem; font-size: 0.875rem; color: #6b7280; }
    body.dark .card-title p { color: #9ca3af; }

    .btn {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 0.5rem;
      width: 100%;
      padding: 0.75rem 1rem;
      border-radius: 0.5rem;
      font-weight: 600;
      font-size: 1rem;
      text-decoration: none;
      cursor: pointer;
      border: none;
      transition: background-color 0.2s;
    }
    .btn-orange {
      background-color: var(--amazon-orange);
      color: var(--amazon-dark);
    }
    .btn-orange:hover { background-color: #f59e0b; }
    .btn-blue { background-color: #2563eb; color: #ffffff; }
    .btn-blue:hover { background-color: #1d4ed8; }
    .btn-gray {
      background-color: #f3f4f6;
      color: #374151;
      font-size: 0.875rem;
    }
    .btn-gray:hover { background-color: #e5e7eb; }
    body.dark .btn-gray { background-color: #374151; color: #e5e7eb; }
    body.dark .btn-gray:hover { background-color: #4b5563; }

    .divider {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      width: 100%;
    }
    .divider::before, .divider::after {
      content: '';
      flex: 1;
      height: 1px;
      background-color: #d1d5db;
    }
    body.dark .divider::before, body.dark .divider::after { background-color: #4b5563; }
    .divider span { font-size: 0.75rem; color: #9ca3af; white-space: nowrap; }

    .secondary-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.75rem;
    }
  </style>
</head>
<body>
  <main>
    <div class="card">
      <div class="card-title">
        <h2>Welcome to <br>Hub Center</h2>
      </div>
      <div style="display:flex;flex-direction:column;gap:0.75rem;">
        <a href="/docs" class="btn btn-orange">
          <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
          Fetch Data
        </a>
        <a href="/docs" class="btn btn-blue">
          <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
          Run Forecast
        </a>
      </div>
        <div class="divider"><span>More options</span></div>
        <div class="secondary-grid">
          <a href="/docs" class="btn btn-gray">API Docs</a>
          <a href="/" class="btn btn-gray" style="color:#2563eb;">Log In</a>
        </div>
    </div>
  </main>
  <script>
    function toggleDarkMode() {
      document.body.classList.toggle('dark');
      const btn = document.getElementById('darkModeBtn');
      btn.textContent = document.body.classList.contains('dark') ? 'Light Mode' : 'Dark Mode';
    }
  </script>
</body>
</html>
"""
