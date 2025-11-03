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
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://unpkg.com/lucide@latest"></script>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
                -webkit-font-smoothing: antialiased;
                -moz-osx-font-smoothing: grayscale;
            }

            body {
                background: #18222d;
                color: #ffffff;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }

            /* Animations */
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }

            @keyframes slideIn {
                from { opacity: 0; transform: translateX(-10px); }
                to { opacity: 1; transform: translateX(0); }
            }

            /* Container */
            .container {
                width: 100%;
                max-width: 600px;
                animation: fadeIn 0.5s ease-out;
            }

            /* Header */
            .header {
                margin-bottom: 32px;
                animation: slideIn 0.4s ease-out;
                text-align: center;
            }

            @media (min-width: 640px) {
                .header {
                    text-align: left;
                }
            }

            .header-content {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 12px;
                margin-bottom: 12px;
            }

            @media (min-width: 640px) {
                .header-content {
                    justify-content: flex-start;
                }
            }

            .icon-box {
                width: 52px;
                height: 52px;
                background: linear-gradient(135deg, #3390ec 0%, #2b7cd3 100%);
                border-radius: 16px;
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 8px 16px rgba(51, 144, 236, 0.3);
                transition: all 0.3s ease;
            }

            .icon-box:hover {
                transform: translateY(-2px) scale(1.05);
                box-shadow: 0 12px 24px rgba(51, 144, 236, 0.4);
            }

            .header h1 {
                font-size: 36px;
                font-weight: 700;
                color: #ffffff;
                letter-spacing: -0.5px;
            }

            .header p {
                font-size: 15px;
                color: #8e9297;
                margin-top: 4px;
            }

            /* Card */
            .card {
                background: #212d3b;
                border-radius: 20px;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
                padding: 32px;
                animation: fadeIn 0.5s ease-out 0.1s backwards;
                border: 1px solid rgba(255, 255, 255, 0.08);
            }

            @media (max-width: 639px) {
                .card {
                    padding: 24px;
                }
            }

            /* Form */
            .form-group {
                margin-bottom: 24px;
                animation: slideIn 0.3s ease-out;
            }

            .form-group:nth-child(2) { animation-delay: 0.1s; }
            .form-group:nth-child(4) { animation-delay: 0.15s; }
            .form-group:nth-child(6) { animation-delay: 0.2s; }

            .form-label {
                display: flex;
                align-items: center;
                gap: 8px;
                font-size: 14px;
                font-weight: 600;
                color: #ffffff;
                margin-bottom: 10px;
            }

            .form-label svg {
                color: #3390ec;
            }

            /* Input & Select */
            input, select {
                width: 100%;
                padding: 14px 16px;
                font-size: 15px;
                color: #ffffff;
                background: #18222d;
                border: 1.5px solid #2b3942;
                border-radius: 12px;
                outline: none;
                transition: all 0.2s ease;
                font-family: inherit;
            }

            input:focus, select:focus {
                border-color: #3390ec;
                background: #1a2633;
                box-shadow: 0 0 0 4px rgba(51, 144, 236, 0.15);
                transform: translateY(-1px);
            }

            input:hover, select:hover {
                border-color: #3390ec;
                background: #1a2633;
            }

            input::placeholder {
                color: #6b7280;
            }

            /* Select specific styles */
            select {
                cursor: pointer;
                appearance: none;
                background-image: url("data:image/svg+xml,%3Csvg width='12' height='8' viewBox='0 0 12 8' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M1 1.5L6 6.5L11 1.5' stroke='%238e9297' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
                background-repeat: no-repeat;
                background-position: right 16px center;
                padding-right: 40px;
            }

            select option {
                padding: 12px;
                background: #18222d;
                color: #ffffff;
            }

            /* Help text */
            .help-text {
                display: flex;
                align-items: center;
                gap: 6px;
                font-size: 13px;
                color: #8e9297;
                margin-top: 8px;
            }

            .help-text svg {
                flex-shrink: 0;
            }

            /* Info box */
            .info-box {
                display: flex;
                align-items: flex-start;
                gap: 10px;
                padding: 14px 16px;
                background: rgba(51, 144, 236, 0.1);
                border: 1px solid rgba(51, 144, 236, 0.3);
                border-radius: 12px;
                font-size: 13px;
                color: #c1d7ee;
                margin-top: 10px;
            }

            .info-box svg {
                color: #3390ec;
                flex-shrink: 0;
                margin-top: 2px;
            }

            /* Divider */
            .divider {
                height: 1px;
                background: rgba(255, 255, 255, 0.08);
                margin: 28px 0;
            }

            /* Button */
            .btn-primary {
                width: 100%;
                padding: 16px 24px;
                font-size: 16px;
                font-weight: 600;
                color: #ffffff;
                background: linear-gradient(135deg, #3390ec 0%, #2b7cd3 100%);
                border: none;
                border-radius: 12px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 10px;
                box-shadow: 0 8px 16px rgba(51, 144, 236, 0.3);
                transition: all 0.3s ease;
                margin-top: 12px;
            }

            .btn-primary:hover {
                background: linear-gradient(135deg, #2b7cd3 0%, #1e5fa3 100%);
                box-shadow: 0 12px 24px rgba(51, 144, 236, 0.4);
                transform: translateY(-2px);
            }

            .btn-primary:active {
                transform: translateY(0);
                box-shadow: 0 4px 12px rgba(51, 144, 236, 0.3);
            }

            .btn-primary:disabled {
                background: #4a5568;
                cursor: not-allowed;
                box-shadow: none;
                transform: none;
                opacity: 0.6;
            }

            /* Password toggle */
            .input-wrapper {
                position: relative;
            }

            .toggle-password {
                position: absolute;
                right: 12px;
                top: 50%;
                transform: translateY(-50%);
                background: transparent;
                border: none;
                padding: 8px;
                cursor: pointer;
                color: #6b7280;
                transition: all 0.2s ease;
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .toggle-password:hover {
                background: rgba(51, 144, 236, 0.1);
                color: #3390ec;
            }

            /* Status messages */
            .status-message {
                display: none;
                padding: 16px 18px;
                border-radius: 12px;
                font-size: 14px;
                font-weight: 500;
                margin-top: 20px;
                animation: fadeIn 0.3s ease-out;
            }

            .status-message.show {
                display: flex;
                align-items: center;
                gap: 12px;
            }

            .status-success {
                background: rgba(76, 175, 80, 0.15);
                color: #81c784;
                border: 1px solid rgba(76, 175, 80, 0.3);
            }

            .status-error {
                background: rgba(244, 67, 54, 0.15);
                color: #e57373;
                border: 1px solid rgba(244, 67, 54, 0.3);
            }

            /* Footer */
            .footer {
                text-align: center;
                margin-top: 24px;
                color: #6b7280;
                font-size: 13px;
                animation: fadeIn 0.5s ease-out 0.3s backwards;
            }

            /* Loading animation */
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
            <!-- Header -->
            <div class="header">
                <div class="header-content">
                    <div class="icon-box">
                        <i data-lucide="settings" style="width: 24px; height: 24px; color: white; stroke-width: 2;"></i>
                    </div>
                    <h1>Settings</h1>
                </div>
                <p>Configure your preferences and API settings</p>
            </div>

            <!-- Form Card -->
            <div class="card">
                <form id="settingsForm">
                    <!-- Timezone Field -->
                    <div class="form-group">
                        <label for="timezone" class="form-label">
                            <i data-lucide="globe" style="width: 16px; height: 16px; stroke-width: 2;"></i>
                            <span>Timezone</span>
                        </label>
                        <select id="timezone" name="timezone" required>
                            <option value="">Select timezone...</option>
                        </select>
                        <p class="help-text">
                            <i data-lucide="info" style="width: 14px; height: 14px; stroke-width: 2;"></i>
                            <span>Your current timezone will be auto-selected</span>
                        </p>
                    </div>

                    <div class="divider"></div>

                    <!-- AI Provider Field -->
                    <div class="form-group">
                        <label for="ai_provider" class="form-label">
                            <i data-lucide="sparkles" style="width: 16px; height: 16px; stroke-width: 2;"></i>
                            <span>AI Provider</span>
                        </label>
                        <select id="ai_provider" name="default_ai" required>
                            <option value="gemini">Google Gemini</option>
                            <option value="openai">OpenAI</option>
                        </select>
                    </div>

                    <div class="divider"></div>

                    <!-- API Key Field -->
                    <div class="form-group">
                        <label for="api_key" class="form-label">
                            <i data-lucide="key" style="width: 16px; height: 16px; stroke-width: 2;"></i>
                            <span>API Key</span>
                        </label>
                        <div class="input-wrapper">
                            <input
                                type="password"
                                id="api_key"
                                name="api_key"
                                placeholder="Enter your API key"
                                required
                                style="font-family: monospace; letter-spacing: 1px;"
                            >
                            <button type="button" id="togglePassword" class="toggle-password">
                                <i data-lucide="eye" style="width: 16px; height: 16px; stroke-width: 2;"></i>
                            </button>
                        </div>
                        <div class="info-box">
                            <i data-lucide="shield-check" style="width: 14px; height: 14px; stroke-width: 2;"></i>
                            <span>Your key is encrypted and never stored in chat history</span>
                        </div>
                    </div>

                    <!-- Submit Button -->
                    <button type="submit" id="submitBtn" class="btn-primary">
                        <i data-lucide="save" style="width: 16px; height: 16px; stroke-width: 2.5;"></i>
                        <span>Save Settings</span>
                    </button>

                    <!-- Status Message -->
                    <div id="status" class="status-message"></div>
                </form>
            </div>

            <!-- Footer -->
            <div class="footer">
                <p>Powered by Task Genie</p>
            </div>
        </div>

        <script>
            // Initialize Lucide icons
            lucide.createIcons();

            // Initialize Telegram Web App
            const tg = window.Telegram.WebApp;
            tg.expand();
            tg.ready();

            // Password toggle
            const togglePassword = document.getElementById('togglePassword');
            const apiKeyInput = document.getElementById('api_key');
            togglePassword.addEventListener('click', () => {
                const type = apiKeyInput.type === 'password' ? 'text' : 'password';
                apiKeyInput.type = type;
                const icon = type === 'password' ? 'eye' : 'eye-off';
                togglePassword.innerHTML = `<i data-lucide="${icon}" style="width: 16px; height: 16px; stroke-width: 2;"></i>`;
                lucide.createIcons();
            });

            // Get all available timezones
            const timezones = Intl.supportedValuesOf('timeZone');
            const timezoneSelect = document.getElementById('timezone');
            const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

            // Populate timezone dropdown
            timezones.forEach(tz => {
                const option = document.createElement('option');
                option.value = tz;
                const date = new Date();
                const formatter = new Intl.DateTimeFormat('en', {
                    timeZone: tz,
                    timeZoneName: 'shortOffset'
                });
                const parts = formatter.formatToParts(date);
                const offset = parts.find(part => part.type === 'timeZoneName')?.value || '';
                option.textContent = `${tz} (${offset})`;
                if (tz === userTimezone) {
                    option.selected = true;
                }
                timezoneSelect.appendChild(option);
            });

            // Get the signed authentication data from Telegram
            const initData = tg.initData;

            // Handle form submission
            document.getElementById('settingsForm').addEventListener('submit', async (e) => {
                e.preventDefault();

                const submitBtn = document.getElementById('submitBtn');
                const statusDiv = document.getElementById('status');

                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i data-lucide="loader-2" class="spinner" style="width: 16px; height: 16px; stroke-width: 2;"></i><span>Saving...</span>';
                lucide.createIcons();
                statusDiv.className = 'status-message';

                try {
                    const formData = new FormData(e.target);

                    // CRITICAL: Include the signed initData from Telegram
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
                        statusDiv.className = 'status-message status-success show';
                        statusDiv.innerHTML = '<i data-lucide="check-circle-2" style="width: 16px; height: 16px; stroke-width: 2;"></i><span>Settings saved successfully</span>';
                        lucide.createIcons();

                        // Close the web app after 2 seconds
                        setTimeout(() => tg.close(), 2000);
                    } else {
                        throw new Error(result.detail || 'Failed to save settings');
                    }

                } catch (error) {
                    statusDiv.className = 'status-message status-error show';
                    statusDiv.innerHTML = `<i data-lucide="alert-circle" style="width: 16px; height: 16px; stroke-width: 2;"></i><span>${error.message}</span>`;
                    lucide.createIcons();
                } finally {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = '<i data-lucide="save" style="width: 16px; height: 16px; stroke-width: 2.5;"></i><span>Save Settings</span>';
                    lucide.createIcons();
                }
            });
        </script>
    </body>
    </html>
    """
