"""
Parse tiny11builder PowerShell scripts to extract configurable items.
"""
import re
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class AppxPackage:
    """A provisioned AppX package to remove."""
    prefix: str
    display_name: str
    category: str = "bloatware"
    enabled: bool = True


@dataclass
class RegistryTweak:
    """A registry tweak to apply."""
    path: str
    name: str
    value: str
    description: str
    category: str
    enabled: bool = True


@dataclass
class SystemPackage:
    """A Windows component/package to remove (Core only)."""
    pattern: str
    display_name: str
    enabled: bool = True


def _friendly_name(prefix: str) -> str:
    """Convert package prefix to human-readable name."""
    mapping = {
        "AppUp.IntelManagementandSecurityStatus": "Intel Management",
        "Clipchamp.Clipchamp": "Clipchamp",
        "DolbyLaboratories.DolbyAccess": "Dolby Access",
        "DolbyLaboratories.DolbyDigitalPlusDecoderOEM": "Dolby Digital+",
        "Microsoft.BingNews": "News",
        "Microsoft.BingSearch": "Bing Search",
        "Microsoft.BingWeather": "Weather",
        "Microsoft.Copilot": "Copilot",
        "Microsoft.Windows.CrossDevice": "Cross Device",
        "Microsoft.GamingApp": "Xbox Gaming App",
        "Microsoft.GetHelp": "Get Help",
        "Microsoft.Getstarted": "Get Started",
        "Microsoft.Microsoft3DViewer": "3D Viewer",
        "Microsoft.MicrosoftOfficeHub": "Office Hub",
        "Microsoft.MicrosoftSolitaireCollection": "Solitaire",
        "Microsoft.MicrosoftStickyNotes": "Sticky Notes",
        "Microsoft.MixedReality.Portal": "Mixed Reality Portal",
        "Microsoft.MSPaint": "MS Paint (Legacy)",
        "Microsoft.Office.OneNote": "OneNote",
        "Microsoft.OfficePushNotificationUtility": "Office Push Notifications",
        "Microsoft.OutlookForWindows": "Outlook (New)",
        "Microsoft.Paint": "Paint",
        "Microsoft.People": "People",
        "Microsoft.PowerAutomateDesktop": "Power Automate",
        "Microsoft.SkypeApp": "Skype",
        "Microsoft.StartExperiencesApp": "Start Experiences",
        "Microsoft.Todos": "To Do",
        "Microsoft.Wallet": "Wallet",
        "Microsoft.Windows.DevHome": "Dev Home",
        "Microsoft.Windows.Copilot": "Windows Copilot",
        "Microsoft.Windows.Teams": "Teams",
        "Microsoft.WindowsAlarms": "Alarms & Clock",
        "Microsoft.WindowsCamera": "Camera",
        "microsoft.windowscommunicationsapps": "Mail & Calendar",
        "Microsoft.WindowsFeedbackHub": "Feedback Hub",
        "Microsoft.WindowsMaps": "Maps",
        "Microsoft.WindowsSoundRecorder": "Sound Recorder",
        "Microsoft.WindowsTerminal": "Windows Terminal",
        "Microsoft.Xbox.TCUI": "Xbox TCUI",
        "Microsoft.XboxApp": "Xbox App",
        "Microsoft.XboxGameOverlay": "Xbox Game Overlay",
        "Microsoft.XboxGamingOverlay": "Xbox Gaming Overlay",
        "Microsoft.XboxIdentityProvider": "Xbox Identity",
        "Microsoft.XboxSpeechToTextOverlay": "Xbox Speech-to-Text",
        "Microsoft.YourPhone": "Phone Link",
        "Microsoft.ZuneMusic": "Media Player (Zune)",
        "Microsoft.ZuneVideo": "Movies & TV",
        "MicrosoftCorporationII.MicrosoftFamily": "Microsoft Family",
        "MicrosoftCorporationII.QuickAssist": "Quick Assist",
        "MSTeams": "Teams (MSTeams)",
        "MicrosoftTeams": "Teams (Classic)",
        "Microsoft.549981C3F5F10": "Cortana",
    }
    result = mapping.get(prefix)
    return result if result is not None else prefix.split(".")[-1]


def _categorize_package(prefix: str) -> str:
    """Categorize a package by its prefix."""
    if "Xbox" in prefix or "Gaming" in prefix:
        return "gaming"
    if "Bing" in prefix or "News" in prefix or "Weather" in prefix:
        return "web_news"
    if "Copilot" in prefix:
        return "ai"
    if "Office" in prefix or "OneNote" in prefix or "Outlook" in prefix or "Teams" in prefix:
        return "productivity"
    if "Edge" in prefix:
        return "browser"
    return "bloatware"


def parse_appx_packages(script_path: Path) -> list[AppxPackage]:
    """Parse $packagePrefixes from a PS1 script."""
    text = script_path.read_text(encoding="utf-8")
    
    # Find the $packagePrefixes array
    match = re.search(
        r'\$packagePrefixes\s*=\s*(.*?)(?:\r?\n\r?\n|\r?\n\$)',
        text, re.DOTALL
    )
    if not match:
        return []
    
    block = match.group(1)
    # Extract quoted strings
    prefixes = re.findall(r"'([^']+)'", block)
    
    packages = []
    seen = set()
    for p in prefixes:
        # Normalize: strip trailing underscore for Core script
        clean = p.rstrip("_")
        if clean in seen:
            continue
        seen.add(clean)
        packages.append(AppxPackage(
            prefix=clean,
            display_name=_friendly_name(clean),
            category=_categorize_package(clean),
        ))
    return packages


def parse_system_packages(script_path: Path) -> list[SystemPackage]:
    """Parse $packagePatterns from Core script."""
    text = script_path.read_text(encoding="utf-8")
    
    match = re.search(
        r'\$packagePatterns\s*=\s*@\((.*?)\)',
        text, re.DOTALL
    )
    if not match:
        return []
    
    block = match.group(1)
    patterns = re.findall(r'"([^"]+)"', block)
    
    friendly = {
        "Microsoft-Windows-InternetExplorer-Optional": "Internet Explorer",
        "Microsoft-Windows-Kernel-LA57-FoD": "Kernel LA57 (5-level paging)",
        "Microsoft-Windows-LanguageFeatures-Handwriting": "Handwriting Support",
        "Microsoft-Windows-LanguageFeatures-OCR": "OCR Support",
        "Microsoft-Windows-LanguageFeatures-Speech": "Speech Recognition",
        "Microsoft-Windows-LanguageFeatures-TextToSpeech": "Text-to-Speech",
        "Microsoft-Windows-MediaPlayer": "Windows Media Player",
        "Microsoft-Windows-Wallpaper-Content-Extended": "Extended Wallpapers",
        "Windows-Defender-Client": "Windows Defender",
        "Microsoft-Windows-WordPad-FoD": "WordPad",
        "Microsoft-Windows-TabletPCMath": "Tablet PC Math",
        "Microsoft-Windows-StepsRecorder": "Steps Recorder",
    }
    
    packages = []
    for pat in patterns:
        # Extract the base name before ~
        base = pat.split("~")[0]
        name = friendly.get(base, base.replace("Microsoft-Windows-", "").replace("-FoD", "").replace("-Package", ""))
        packages.append(SystemPackage(pattern=pat, display_name=name))
    return packages


def parse_registry_tweaks(script_path: Path) -> dict[str, list[RegistryTweak]]:
    """Parse Set-RegistryValue calls, grouped by category."""
    text = script_path.read_text(encoding="utf-8")
    
    # Find all Set-RegistryValue calls
    pattern = r"Set-RegistryValue\s+'([^']+)'\s+'([^']+)'\s+'([^']+)'\s+'([^']+)'"
    matches = re.findall(pattern, text)
    
    # Also find Write-Output lines before each group to determine category
    tweaks: dict[str, list[RegistryTweak]] = {}
    current_category = "general"
    
    for line in text.split("\n"):
        # Detect category from Write-Output
        cat_match = re.search(r'Write-Output\s+"([^"]+)"', line)
        if cat_match:
            label = cat_match.group(1).strip().rstrip(":")
            if "Bypassing" in label or "system requirements" in label:
                current_category = "硬件需求繞過"
            elif "Sponsored" in label or "Sponsored Apps" in label:
                current_category = "廣告與推廣"
            elif "Local Accounts" in label or "OOBE" in label:
                current_category = "OOBE 設定"
            elif "Reserved Storage" in label:
                current_category = "存儲設定"
            elif "BitLocker" in label:
                current_category = "安全設定"
            elif "Chat" in label:
                current_category = "任務欄"
            elif "Edge" in label:
                current_category = "Edge 移除"
            elif "OneDrive" in label:
                current_category = "OneDrive"
            elif "Telemetry" in label:
                current_category = "遙測與隱私"
            elif "DevHome" in label or "Outlook" in label:
                current_category = "應用安裝阻止"
            elif "Copilot" in label:
                current_category = "Copilot"
            elif "Teams" in label:
                current_category = "Teams"
        
        # Parse Set-RegistryValue
        tweak_match = re.search(
            r"Set-RegistryValue\s+'([^']+)'\s+'([^']+)'\s+'([^']+)'\s+'([^']+)'",
            line
        )
        if tweak_match:
            reg_path, reg_name, reg_type, reg_value = tweak_match.groups()
            # Generate a description from the name
            desc = _tweak_description(reg_path, reg_name, reg_value)
            tweak = RegistryTweak(
                path=reg_path, name=reg_name, value=reg_value,
                description=desc, category=current_category,
            )
            tweaks.setdefault(current_category, []).append(tweak)
    
    return tweaks


def _tweak_description(path: str, name: str, value: str) -> str:
    """Generate human-readable description for a registry tweak."""
    known = {
        ("BypassCPUCheck", "1"): "繞過 CPU 檢查",
        ("BypassRAMCheck", "1"): "繞過 RAM 檢查",
        ("BypassSecureBootCheck", "1"): "繞過 Secure Boot 檢查",
        ("BypassStorageCheck", "1"): "繞過存儲空間檢查",
        ("BypassTPMCheck", "1"): "繞過 TPM 檢查",
        ("AllowUpgradesWithUnsupportedTPMOrCPU", "1"): "允許在不支援的 TPM/CPU 上升級",
        ("OemPreInstalledAppsEnabled", "0"): "禁用 OEM 預裝應用",
        ("PreInstalledAppsEnabled", "0"): "禁用預裝應用",
        ("SilentInstalledAppsEnabled", "0"): "禁用靜默安裝應用",
        ("DisableWindowsConsumerFeatures", "1"): "禁用消費者功能",
        ("ContentDeliveryAllowed", "0"): "禁用內容推送",
        ("FeatureManagementEnabled", "0"): "禁用功能管理",
        ("SystemPaneSuggestionsEnabled", "0"): "禁用系統面板建議",
        ("BypassNRO", "1"): "繞過網路需求 (OOBE)",
        ("ShippedWithReserves", "0"): "禁用保留存儲",
        ("PreventDeviceEncryption", "1"): "禁用 BitLocker 裝置加密",
        ("ChatIcon", "3"): "隱藏聊天圖示",
        ("TaskbarMn", "0"): "隱藏任務欄聊天按鈕",
        ("AllowTelemetry", "0"): "禁用遙測",
        ("TurnOffWindowsCopilot", "1"): "關閉 Windows Copilot",
        ("DisableInstallation", "1"): "阻止 Teams 安裝",
        ("PreventRun", "1"): "阻止 New Outlook 運行",
        ("DisableFileSyncNGSC", "1"): "禁用 OneDrive 資料夾備份",
        ("Enabled", "0"): "禁用廣告 ID",
        ("TailoredExperiencesWithDiagnosticDataEnabled", "0"): "禁用個人化體驗",
        ("HasAccepted", "0"): "禁用線上語音隱私",
        ("RestrictImplicitInkCollection", "1"): "限制墨跡收集",
        ("RestrictImplicitTextCollection", "1"): "限制文字收集",
        ("HarvestContacts", "0"): "禁用聯繫人採集",
    }
    key = (name, value)
    if key in known:
        return known[key]
    return f"{name} = {value}"


def get_all_packages(script_dir: Path) -> dict[str, list]:
    """Get packages from both scripts."""
    regular = parse_appx_packages(script_dir / "tiny11maker.ps1")
    core = parse_appx_packages(script_dir / "tiny11Coremaker.ps1")
    system = parse_system_packages(script_dir / "tiny11Coremaker.ps1")
    
    # Core-only = packages in core but not in regular
    regular_prefixes = {p.prefix for p in regular}
    core_only = [p for p in core if p.prefix not in regular_prefixes]
    
    return {
        "regular": regular,
        "core_only": core_only,
        "system": system,
    }


def get_all_tweaks(script_dir: Path) -> dict[str, list[RegistryTweak]]:
    """Get registry tweaks from the regular script."""
    return parse_registry_tweaks(script_dir / "tiny11maker.ps1")
