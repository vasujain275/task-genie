from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from app.types import SettingsUpdate
from app.utils.security import verify_telegram_webapp_data, encrypt_api_key
from app.models import User

router = APIRouter()


@router.post("/api/save-settings")
async def save_settings(update_settings: SettingsUpdate):
    """
    Saves user settings.

    SECURITY: Notice we don't accept telegram_id as a parameter!
    We extract it from the VERIFIED Telegram authentication data.
    """

    # STEP 1: Verify the authentication data
    # This throws HTTPException if verification fails
    verified_user = verify_telegram_webapp_data(update_settings.init_data)

    # STEP 2: Extract telegram_id from VERIFIED data (not from user input!)
    telegram_id = verified_user["telegram_id"]

    # STEP 3: Now we KNOW this is the real user, so we can update their settings
    user = await User.find_one(User.telegram_id == telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update settings
    user.timezone = update_settings.timezone
    user.default_ai = update_settings.default_ai

    # Encrypt and save API key based on selected AI provider
    if update_settings.api_key:
        encrypted_key = encrypt_api_key(update_settings.api_key)

        if update_settings.default_ai == "gemini":
            user.gemini_key = encrypted_key
        elif update_settings.default_ai == "openai":
            user.openai_key = encrypted_key

    await user.save()

    return {
        "success": True,
        "message": "Settings saved successfully",
        "user": {"telegram_id": telegram_id, "name": verified_user["first_name"]},
    }


@router.get("/settings", response_class=HTMLResponse)
async def settings_page():
    """
    Serves the settings page.
    Notice: NO telegram_id in URL! Same URL for all users.
    """
    return r"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Settings - Task Genie</title>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <script src="https://unpkg.com/lucide@latest"></script>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #17212b;
                color: #ffffff;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }

            .container {
                width: 100%;
                max-width: 460px;
            }

            .header {
                text-align: center;
                margin-bottom: 24px;
            }

            .header h1 {
                font-size: 28px;
                font-weight: 600;
                margin-bottom: 8px;
            }

            .header p {
                font-size: 14px;
                color: #8e9297;
            }

            .card {
                background: #242f3d;
                border-radius: 10px;
                padding: 28px;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
            }

            .form-group {
                margin-bottom: 20px;
            }

            label {
                display: block;
                font-size: 14px;
                font-weight: 500;
                margin-bottom: 8px;
                color: #ffffff;
            }

            input,
            select {
                width: 100%;
                height: 48px;
                padding: 0 16px;
                font-size: 15px;
                color: #ffffff;
                background: #17212b;
                border: 1px solid #3a4d5c;
                border-radius: 6px;
                outline: none;
                font-family: inherit;
            }

            input:focus,
            select:focus {
                border-color: #3390ec;
                background: #1a2633;
            }

            input::placeholder {
                color: #6d7781;
            }

            select {
                cursor: pointer;
                appearance: none;
                background-image: url("data:image/svg+xml,%3Csvg width='16' height='10' viewBox='0 0 16 10' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M2 2L8 8L14 2' stroke='%238e9297' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
                background-repeat: no-repeat;
                background-position: right 16px center;
                padding-right: 44px;
            }

            select option {
                background: #17212b;
                color: #ffffff;
                padding: 12px;
            }

            .help-text {
                font-size: 12px;
                color: #8e9297;
                margin-top: 6px;
            }

            .info-box {
                display: flex;
                gap: 10px;
                padding: 12px;
                background: rgba(51, 144, 236, 0.1);
                border: 1px solid rgba(51, 144, 236, 0.25);
                border-radius: 6px;
                font-size: 12px;
                color: #b5d4ee;
                margin-top: 8px;
            }

            .info-box svg {
                flex-shrink: 0;
                color: #3390ec;
            }

            .divider {
                height: 1px;
                background: rgba(255, 255, 255, 0.08);
                margin: 20px 0;
            }

            .password-wrapper {
                position: relative;
            }

            .password-toggle {
                position: absolute;
                right: 12px;
                top: 50%;
                transform: translateY(-50%);
                background: none;
                border: none;
                padding: 8px;
                cursor: pointer;
                color: #6d7781;
                display: flex;
                align-items: center;
            }

            .password-toggle:hover {
                color: #3390ec;
            }

            .btn {
                width: 100%;
                height: 52px;
                margin-top: 24px;
                font-size: 16px;
                font-weight: 600;
                color: #ffffff;
                background: #3390ec;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 8px;
                transition: background 0.2s;
            }

            .btn:hover {
                background: #2b7cd3;
            }

            .btn:disabled {
                background: #4a5568;
                cursor: not-allowed;
                opacity: 0.6;
            }

            .status {
                display: none;
                padding: 14px;
                border-radius: 6px;
                font-size: 14px;
                margin-top: 16px;
                align-items: center;
                gap: 10px;
            }

            .status.show {
                display: flex;
            }

            .status.success {
                background: rgba(76, 175, 80, 0.15);
                color: #81c784;
                border: 1px solid rgba(76, 175, 80, 0.3);
            }

            .status.error {
                background: rgba(244, 67, 54, 0.15);
                color: #e57373;
                border: 1px solid rgba(244, 67, 54, 0.3);
            }

            .footer {
                text-align: center;
                margin-top: 20px;
                font-size: 12px;
                color: #6d7781;
            }

            @keyframes spin {
                to { transform: rotate(360deg); }
            }

            .spinner {
                animation: spin 1s linear infinite;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>⚙️ Settings</h1>
                <p>Configure your preferences</p>
            </div>

            <div class="card">
                <form id="settingsForm">
                    <!-- Timezone -->
                    <div class="form-group">
                        <label for="timezone">Timezone</label>
                        <select id="timezone" name="timezone" required>
                            <option value="">Select timezone...</option>
                        </select>
                        <p class="help-text">Your current timezone will be auto-selected</p>
                    </div>

                    <div class="divider"></div>

                    <!-- AI Provider -->
                    <div class="form-group">
                        <label for="ai_provider">AI Provider</label>
                        <select id="ai_provider" name="default_ai" required>
                            <option value="gemini">Google Gemini</option>
                            <option value="openai">OpenAI</option>
                        </select>
                    </div>

                    <div class="divider"></div>

                    <!-- API Key -->
                    <div class="form-group">
                        <label for="api_key">API Key</label>
                        <div class="password-wrapper">
                            <input
                                type="password"
                                id="api_key"
                                name="api_key"
                                placeholder="Enter your API key"
                                required
                                style="font-family: monospace; padding-right: 44px;"
                            >
                            <button type="button" id="togglePassword" class="password-toggle">
                                <i data-lucide="eye" style="width: 18px; height: 18px;"></i>
                            </button>
                        </div>
                        <div class="info-box">
                            <i data-lucide="shield-check" style="width: 16px; height: 16px;"></i>
                            <span>Your key is encrypted and stored securely</span>
                        </div>
                    </div>

                    <!-- Submit -->
                    <button type="submit" id="submitBtn" class="btn">
                        <i data-lucide="save" style="width: 18px; height: 18px;"></i>
                        <span>Save Settings</span>
                    </button>

                    <!-- Status -->
                    <div id="status" class="status"></div>
                </form>
            </div>

            <div class="footer">
                <p>Task Genie</p>
            </div>
        </div>

        <script>
            // Initialize icons
            lucide.createIcons();

            // Initialize Telegram Web App
            const tg = window.Telegram.WebApp;
            tg.expand();
            tg.ready();

            // Password toggle
            const toggleBtn = document.getElementById('togglePassword');
            const apiKeyInput = document.getElementById('api_key');

            toggleBtn.addEventListener('click', () => {
                const type = apiKeyInput.type === 'password' ? 'text' : 'password';
                apiKeyInput.type = type;
                const icon = type === 'password' ? 'eye' : 'eye-off';
                toggleBtn.innerHTML = `<i data-lucide="${icon}" style="width: 18px; height: 18px;"></i>`;
                lucide.createIcons();
            });

            // Populate timezone dropdown
            const timezones = Intl.supportedValuesOf('timeZone');
            const timezoneSelect = document.getElementById('timezone');
            const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

            timezones.forEach(tz => {
                const option = document.createElement('option');
                option.value = tz;
                option.textContent = tz.replace(/_/g, ' ');
                if (tz === userTimezone) {
                    option.selected = true;
                }
                timezoneSelect.appendChild(option);
            });

            // Get Telegram auth data
            const initData = tg.initData;

            // Handle form submission
            document.getElementById('settingsForm').addEventListener('submit', async (e) => {
                e.preventDefault();

                const submitBtn = document.getElementById('submitBtn');
                const statusDiv = document.getElementById('status');

                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i data-lucide="loader-2" class="spinner" style="width: 18px; height: 18px;"></i><span>Saving...</span>';
                lucide.createIcons();
                statusDiv.className = 'status';

                try {
                    const formData = new FormData(e.target);

                    const response = await fetch('/api/save-settings', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            init_data: initData,
                            timezone: formData.get('timezone'),
                            default_ai: formData.get('default_ai'),
                            api_key: formData.get('api_key')
                        })
                    });

                    const result = await response.json();

                    if (response.ok) {
                        statusDiv.className = 'status success show';
                        statusDiv.innerHTML = '<i data-lucide="check-circle-2" style="width: 18px; height: 18px;"></i><span>Settings saved successfully!</span>';
                        lucide.createIcons();
                        setTimeout(() => tg.close(), 2000);
                    } else {
                        throw new Error(result.detail || 'Failed to save settings');
                    }
                } catch (error) {
                    statusDiv.className = 'status error show';
                    statusDiv.innerHTML = `<i data-lucide="alert-circle" style="width: 18px; height: 18px;"></i><span>${error.message}</span>`;
                    lucide.createIcons();
                } finally {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = '<i data-lucide="save" style="width: 18px; height: 18px;"></i><span>Save Settings</span>';
                    lucide.createIcons();
                }
            });
        </script>
    </body>
    </html>
    """
