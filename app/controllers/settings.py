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
    telegram_id = verified_user['telegram_id']

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
        "user": {
            "telegram_id": telegram_id,
            "name": verified_user['first_name']
        }
    }


@router.get("/settings", response_class=HTMLResponse)
async def settings_page():
    """
    Serves the settings page.
    Notice: NO telegram_id in URL! Same URL for all users.
    """
    return """
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
                -webkit-font-smoothing: antialiased;
                -moz-osx-font-smoothing: grayscale;
            }
            body {
                background: var(--tg-theme-bg-color, #ffffff);
                color: var(--tg-theme-text-color, #000000);
            }
            .tg-accent {
                color: var(--tg-theme-link-color, #2481cc);
            }
            .tg-secondary {
                color: var(--tg-theme-hint-color, #999999);
            }
        </style>
    </head>
    <body class="min-h-screen antialiased bg-gray-50">
        <div class="max-w-xl mx-auto px-4 sm:px-6 py-6 sm:py-10">
            <!-- Header -->
            <div class="mb-8">
                <div class="flex items-center gap-3 mb-2">
                    <div class="w-11 h-11 sm:w-12 sm:h-12 bg-black rounded-2xl flex items-center justify-center shadow-lg">
                        <i data-lucide="settings" class="w-6 h-6 text-white stroke-[2]"></i>
                    </div>
                    <h1 class="text-3xl sm:text-4xl font-semibold tracking-tight">Settings</h1>
                </div>
                <p class="text-sm text-gray-600 ml-0 sm:ml-[56px]">
                    Configure your preferences and API settings
                </p>
            </div>

            <!-- Form Card -->
            <div class="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
                                <form id="settingsForm" class="p-5 sm:p-6 space-y-6">

                    <!-- Timezone Field -->
                    <div class="space-y-2.5">
                        <label for="timezone" class="flex items-center gap-2 text-sm font-semibold text-gray-900">
                            <i data-lucide="globe" class="w-4 h-4 stroke-[2] text-blue-600"></i>
                            <span>Timezone</span>
                        </label>
                        <select
                            id="timezone"
                            name="timezone"
                            required
                            class="w-full px-4 py-3 text-sm bg-white border border-gray-300 rounded-xl focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 focus:outline-none transition-all"
                        >
                            <option value="">Select timezone...</option>
                        </select>
                        <p class="text-xs text-gray-500 flex items-center gap-1.5">
                            <i data-lucide="info" class="w-3.5 h-3.5 stroke-[2]"></i>
                            <span>Your current timezone will be auto-selected</span>
                        </p>
                    </div>

                    <!-- Divider -->
                    <div class="border-t border-gray-100"></div>

                    <!-- AI Provider Field -->
                    <div class="space-y-2.5">
                        <label for="ai_provider" class="flex items-center gap-2 text-sm font-semibold text-gray-900">
                            <i data-lucide="sparkles" class="w-4 h-4 stroke-[2] text-blue-600"></i>
                            <span>AI Provider</span>
                        </label>
                        <div class="relative">
                            <select
                                id="ai_provider"
                                name="default_ai"
                                required
                                class="w-full px-4 py-3 text-sm bg-white border border-gray-300 rounded-xl focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 focus:outline-none transition-all appearance-none cursor-pointer pr-10"
                            >
                                <option value="gemini">Google Gemini</option>
                                <option value="openai">OpenAI</option>
                            </select>
                            <i data-lucide="chevron-down" class="w-4 h-4 absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-gray-400"></i>
                        </div>
                    </div>

                    <!-- Divider -->
                    <div class="border-t border-gray-100"></div>

                    <!-- API Key Field -->
                    <div class="space-y-2.5">
                        <label for="api_key" class="flex items-center gap-2 text-sm font-semibold text-gray-900">
                            <i data-lucide="key" class="w-4 h-4 stroke-[2] text-blue-600"></i>
                            <span>API Key</span>
                        </label>
                        <div class="relative">
                            <input
                                type="password"
                                id="api_key"
                                name="api_key"
                                placeholder="Enter your API key"
                                required
                                class="w-full px-4 py-3 text-sm bg-white border border-gray-300 rounded-xl focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 focus:outline-none transition-all font-mono tracking-wide pr-10"
                            >
                            <button
                                type="button"
                                id="togglePassword"
                                class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-700 transition-colors p-1 hover:bg-gray-100 rounded-lg"
                            >
                                <i data-lucide="eye" class="w-4 h-4 stroke-[2]"></i>
                            </button>
                        </div>
                        <div class="flex items-start gap-2 text-xs text-gray-600 bg-blue-50/50 px-3.5 py-2.5 rounded-lg border border-blue-100">
                            <i data-lucide="shield-check" class="w-3.5 h-3.5 mt-0.5 stroke-[2] text-blue-600 flex-shrink-0"></i>
                            <span>Your key is encrypted and never stored in chat history</span>
                        </div>
                    </div>

                    <!-- Submit Button -->
                    <div class="pt-2">
                        <button
                            type="submit"
                            id="submitBtn"
                            class="w-full py-3.5 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 active:bg-blue-800 disabled:bg-gray-400 disabled:cursor-not-allowed transition-all rounded-xl shadow-lg shadow-blue-600/20 hover:shadow-xl hover:shadow-blue-600/30 flex items-center justify-center gap-2"
                        >
                            <i data-lucide="save" class="w-4 h-4 stroke-[2.5]"></i>
                            <span>Save Settings</span>
                        </button>
                    </div>

                    <!-- Status Message -->
                    <div id="status" class="hidden rounded-xl text-sm font-medium"></div>
                </form>
            </div>

            <!-- Footer -->
            <div class="mt-8 text-center">
                <p class="text-xs text-gray-400">Powered by Task Genie</p>
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
                togglePassword.innerHTML = `<i data-lucide="${icon}" class="w-4 h-4 stroke-[2]"></i>`;
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
                submitBtn.innerHTML = '<i data-lucide="loader-2" class="w-4 h-4 stroke-[2] animate-spin"></i><span>Saving...</span>';
                lucide.createIcons();
                statusDiv.className = 'hidden';

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
                        statusDiv.className = 'block p-4 text-sm font-medium rounded-xl bg-green-50 text-green-900 border border-green-200';
                        statusDiv.innerHTML = '<div class="flex items-center gap-2"><i data-lucide="check-circle-2" class="w-4 h-4 stroke-[2] text-green-600"></i><span>Settings saved successfully</span></div>';
                        lucide.createIcons();

                        // Close the web app after 2 seconds
                        setTimeout(() => tg.close(), 2000);
                    } else {
                        throw new Error(result.detail || 'Failed to save settings');
                    }

                } catch (error) {
                    statusDiv.className = 'block p-4 text-sm font-medium rounded-xl bg-red-50 text-red-900 border border-red-200';
                    statusDiv.innerHTML = `<div class="flex items-center gap-2"><i data-lucide="alert-circle" class="w-4 h-4 stroke-[2] text-red-600"></i><span>${error.message}</span></div>`;
                    lucide.createIcons();
                } finally {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = '<i data-lucide="save" class="w-4 h-4 stroke-[2.5]"></i><span>Save Settings</span>';
                    lucide.createIcons();
                }
            });
        </script>
    </body>
    </html>
    """
