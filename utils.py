import re
from datetime import datetime

COUNTRY_CODES = {
    '1': ('United States', '🇺🇸'),
    '7': ('Russia', '🇷🇺'),
    '20': ('Egypt', '🇪🇬'),
    '27': ('South Africa', '🇿🇦'),
    '30': ('Greece', '🇬🇷'),
    '31': ('Netherlands', '🇳🇱'),
    '32': ('Belgium', '🇧🇪'),
    '33': ('France', '🇫🇷'),
    '34': ('Spain', '🇪🇸'),
    '36': ('Hungary', '🇭🇺'),
    '39': ('Italy', '🇮🇹'),
    '40': ('Romania', '🇷🇴'),
    '41': ('Switzerland', '🇨🇭'),
    '43': ('Austria', '🇦🇹'),
    '44': ('United Kingdom', '🇬🇧'),
    '45': ('Denmark', '🇩🇰'),
    '46': ('Sweden', '🇸🇪'),
    '47': ('Norway', '🇳🇴'),
    '48': ('Poland', '🇵🇱'),
    '49': ('Germany', '🇩🇪'),
    '51': ('Peru', '🇵🇪'),
    '52': ('Mexico', '🇲🇽'),
    '53': ('Cuba', '🇨🇺'),
    '54': ('Argentina', '🇦🇷'),
    '55': ('Brazil', '🇧🇷'),
    '56': ('Chile', '🇨🇱'),
    '57': ('Colombia', '🇨🇴'),
    '58': ('Venezuela', '🇻🇪'),
    '60': ('Malaysia', '🇲🇾'),
    '61': ('Australia', '🇦🇺'),
    '62': ('Indonesia', '🇮🇩'),
    '63': ('Philippines', '🇵🇭'),
    '64': ('New Zealand', '🇳🇿'),
    '65': ('Singapore', '🇸🇬'),
    '66': ('Thailand', '🇹🇭'),
    '81': ('Japan', '🇯🇵'),
    '82': ('South Korea', '🇰🇷'),
    '84': ('Vietnam', '🇻🇳'),
    '86': ('China', '🇨🇳'),
    '90': ('Turkey', '🇹🇷'),
    '91': ('India', '🇮🇳'),
    '92': ('Pakistan', '🇵🇰'),
    '93': ('Afghanistan', '🇦🇫'),
    '94': ('Sri Lanka', '🇱🇰'),
    '95': ('Myanmar', '🇲🇲'),
    '98': ('Iran', '🇮🇷'),
    '212': ('Morocco', '🇲🇦'),
    '213': ('Algeria', '🇩🇿'),
    '216': ('Tunisia', '🇹🇳'),
    '218': ('Libya', '🇱🇾'),
    '220': ('Gambia', '🇬🇲'),
    '221': ('Senegal', '🇸🇳'),
    '222': ('Mauritania', '🇲🇷'),
    '223': ('Mali', '🇲🇱'),
    '224': ('Guinea', '🇬🇳'),
    '225': ('Ivory Coast', '🇨🇮'),
    '226': ('Burkina Faso', '🇧🇫'),
    '227': ('Niger', '🇳🇪'),
    '228': ('Togo', '🇹🇬'),
    '229': ('Benin', '🇧🇯'),
    '230': ('Mauritius', '🇲🇺'),
    '231': ('Liberia', '🇱🇷'),
    '232': ('Sierra Leone', '🇸🇱'),
    '233': ('Ghana', '🇬🇭'),
    '234': ('Nigeria', '🇳🇬'),
    '235': ('Chad', '🇹🇩'),
    '236': ('Central African Republic', '🇨🇫'),
    '237': ('Cameroon', '🇨🇲'),
    '238': ('Cape Verde', '🇨🇻'),
    '239': ('Sao Tome and Principe', '🇸🇹'),
    '240': ('Equatorial Guinea', '🇬🇶'),
    '241': ('Gabon', '🇬🇦'),
    '242': ('Republic of the Congo', '🇨🇬'),
    '243': ('DR Congo', '🇨🇩'),
    '244': ('Angola', '🇦🇴'),
    '245': ('Guinea-Bissau', '🇬🇼'),
    '246': ('British Indian Ocean Territory', '🇮🇴'),
    '247': ('Ascension Island', '🇸🇭'),
    '248': ('Seychelles', '🇸🇨'),
    '249': ('Sudan', '🇸🇩'),
    '250': ('Rwanda', '🇷🇼'),
    '251': ('Ethiopia', '🇪🇹'),
    '252': ('Somalia', '🇸🇴'),
    '253': ('Djibouti', '🇩🇯'),
    '254': ('Kenya', '🇰🇪'),
    '255': ('Tanzania', '🇹🇿'),
    '256': ('Uganda', '🇺🇬'),
    '257': ('Burundi', '🇧🇮'),
    '258': ('Mozambique', '🇲🇿'),
    '260': ('Zambia', '🇿🇲'),
    '261': ('Madagascar', '🇲🇬'),
    '262': ('Reunion', '🇷🇪'),
    '263': ('Zimbabwe', '🇿🇼'),
    '264': ('Namibia', '🇳🇦'),
    '265': ('Malawi', '🇲🇼'),
    '266': ('Lesotho', '🇱🇸'),
    '267': ('Botswana', '🇧🇼'),
    '268': ('Eswatini', '🇸🇿'),
    '269': ('Comoros', '🇰🇲'),
    '290': ('Saint Helena', '🇸🇭'),
    '291': ('Eritrea', '🇪🇷'),
    '297': ('Aruba', '🇦🇼'),
    '298': ('Faroe Islands', '🇫🇴'),
    '299': ('Greenland', '🇬🇱'),
    '350': ('Gibraltar', '🇬🇮'),
    '351': ('Portugal', '🇵🇹'),
    '352': ('Luxembourg', '🇱🇺'),
    '353': ('Ireland', '🇮🇪'),
    '354': ('Iceland', '🇮🇸'),
    '355': ('Albania', '🇦🇱'),
    '356': ('Malta', '🇲🇹'),
    '357': ('Cyprus', '🇨🇾'),
    '358': ('Finland', '🇫🇮'),
    '359': ('Bulgaria', '🇧🇬'),
    '370': ('Lithuania', '🇱🇹'),
    '371': ('Latvia', '🇱🇻'),
    '372': ('Estonia', '🇪🇪'),
    '373': ('Moldova', '🇲🇩'),
    '374': ('Armenia', '🇦🇲'),
    '375': ('Belarus', '🇧🇾'),
    '376': ('Andorra', '🇦🇩'),
    '377': ('Monaco', '🇲🇨'),
    '378': ('San Marino', '🇸🇲'),
    '380': ('Ukraine', '🇺🇦'),
    '381': ('Serbia', '🇷🇸'),
    '382': ('Montenegro', '🇲🇪'),
    '385': ('Croatia', '🇭🇷'),
    '386': ('Slovenia', '🇸🇮'),
    '387': ('Bosnia and Herzegovina', '🇧🇦'),
    '389': ('North Macedonia', '🇲🇰'),
    '420': ('Czech Republic', '🇨🇿'),
    '421': ('Slovakia', '🇸🇰'),
    '423': ('Liechtenstein', '🇱🇮'),
    '500': ('Falkland Islands', '🇫🇰'),
    '501': ('Belize', '🇧🇿'),
    '502': ('Guatemala', '🇬🇹'),
    '503': ('El Salvador', '🇸🇻'),
    '504': ('Honduras', '🇭🇳'),
    '505': ('Nicaragua', '🇳🇮'),
    '506': ('Costa Rica', '🇨🇷'),
    '507': ('Panama', '🇵🇦'),
    '509': ('Haiti', '🇭🇹'),
    '590': ('Guadeloupe', '🇬🇵'),
    '591': ('Bolivia', '🇧🇴'),
    '592': ('Guyana', '🇬🇾'),
    '593': ('Ecuador', '🇪🇨'),
    '594': ('French Guiana', '🇬🇫'),
    '595': ('Paraguay', '🇵🇾'),
    '596': ('Martinique', '🇲🇶'),
    '597': ('Suriname', '🇸🇷'),
    '598': ('Uruguay', '🇺🇾'),
    '599': ('Netherlands Antilles', '🇧🇶'),
    '670': ('East Timor', '🇹🇱'),
    '672': ('Norfolk Island', '🇳🇫'),
    '673': ('Brunei', '🇧🇳'),
    '674': ('Nauru', '🇳🇷'),
    '675': ('Papua New Guinea', '🇵🇬'),
    '676': ('Tonga', '🇹🇴'),
    '677': ('Solomon Islands', '🇸🇧'),
    '678': ('Vanuatu', '🇻🇺'),
    '679': ('Fiji', '🇫🇯'),
    '680': ('Palau', '🇵🇼'),
    '681': ('Wallis and Futuna', '🇼🇫'),
    '682': ('Cook Islands', '🇨🇰'),
    '683': ('Niue', '🇳🇺'),
    '685': ('Samoa', '🇼🇸'),
    '686': ('Kiribati', '🇰🇮'),
    '687': ('New Caledonia', '🇳🇨'),
    '688': ('Tuvalu', '🇹🇻'),
    '689': ('French Polynesia', '🇵🇫'),
    '690': ('Tokelau', '🇹🇰'),
    '691': ('Micronesia', '🇫🇲'),
    '692': ('Marshall Islands', '🇲🇭'),
    '850': ('North Korea', '🇰🇵'),
    '852': ('Hong Kong', '🇭🇰'),
    '853': ('Macao', '🇲🇴'),
    '855': ('Cambodia', '🇰🇭'),
    '856': ('Laos', '🇱🇦'),
    '880': ('Bangladesh', '🇧🇩'),
    '886': ('Taiwan', '🇹🇼'),
    '960': ('Maldives', '🇲🇻'),
    '961': ('Lebanon', '🇱🇧'),
    '962': ('Jordan', '🇯🇴'),
    '963': ('Syria', '🇸🇾'),
    '964': ('Iraq', '🇮🇶'),
    '965': ('Kuwait', '🇰🇼'),
    '966': ('Saudi Arabia', '🇸🇦'),
    '967': ('Yemen', '🇾🇪'),
    '968': ('Oman', '🇴🇲'),
    '970': ('Palestine', '🇵🇸'),
    '971': ('United Arab Emirates', '🇦🇪'),
    '972': ('Israel', '🇮🇱'),
    '973': ('Bahrain', '🇧🇭'),
    '974': ('Qatar', '🇶🇦'),
    '975': ('Bhutan', '🇧🇹'),
    '976': ('Mongolia', '🇲🇳'),
    '977': ('Nepal', '🇳🇵'),
    '992': ('Tajikistan', '🇹🇯'),
    '993': ('Turkmenistan', '🇹🇲'),
    '994': ('Azerbaijan', '🇦🇿'),
    '995': ('Georgia', '🇬🇪'),
    '996': ('Kyrgyzstan', '🇰🇬'),
    '998': ('Uzbekistan', '🇺🇿'),
}

def get_country_from_phone(phone):
    if not phone:
        return 'Unknown', '🌍'
    digits = re.sub(r'[^\d]', '', phone)
    if digits.startswith('00'):
        digits = digits[2:]
    for length in [3, 2, 1]:
        prefix = digits[:length]
        if prefix in COUNTRY_CODES:
            name, flag = COUNTRY_CODES[prefix]
            return name, flag
    return 'Unknown', '🌍'

def format_otp_message(otp_data):
    otp = otp_data.get('otp', 'N/A')
    phone = otp_data.get('phone', 'N/A')
    service = otp_data.get('service', 'Unknown')

    country_name, country_flag = get_country_from_phone(phone)

    message = (
        f"🎉 <b>NEW OTP RECEIVED</b> 🎉\n\n"
        f"🌍 <b>Country:</b> {country_name} {country_flag}\n"
        f"📱 <b>Number:</b> <code>{phone}</code>\n"
        f"🚨 <b>Service:</b> {service}\n"
        f"🔐 <b>OTP:</b> <code>{otp}</code>"
    )
    return message

def format_multiple_otps(otp_list):
    if not otp_list:
        return "No new OTPs found."
    if len(otp_list) == 1:
        return format_otp_message(otp_list[0])
    messages = []
    for otp_data in otp_list:
        messages.append(format_otp_message(otp_data))
    return "\n\n—————————————\n\n".join(messages)

def extract_otp_from_text(text):
    if not text:
        return None
    patterns = [
        r'\b(\d{6})\b',
        r'\b(\d{5})\b',
        r'\b(\d{4})\b',
        r'code[:\s]*(\d+)',
        r'verification[:\s]*(\d+)',
        r'otp[:\s]*(\d+)',
        r'pin[:\s]*(\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None

def clean_phone_number(phone):
    if not phone:
        return "N/A"
    cleaned = re.sub(r'[^\d+]', '', phone)
    if cleaned and not cleaned.startswith('+'):
        if cleaned.startswith('88'):
            cleaned = '+' + cleaned
        elif len(cleaned) >= 10:
            cleaned = '+' + cleaned
    return cleaned or phone

def clean_service_name(service):
    if not service:
        return "Unknown"
    cleaned = service.strip().title()
    service_mappings = {
        'fb': 'Facebook',
        'google': 'Google',
        'whatsapp': 'WhatsApp',
        'telegram': 'Telegram',
        'instagram': 'Instagram',
        'twitter': 'Twitter',
        'linkedin': 'LinkedIn',
        'tiktok': 'TikTok',
        'snapchat': 'Snapchat',
        'discord': 'Discord'
    }
    service_lower = cleaned.lower()
    for key, value in service_mappings.items():
        if key in service_lower:
            return value
    return cleaned

def sanitize_for_telegram(text):
    if not text:
        return ""
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    return text

def truncate_message(message, max_length=4096):
    if len(message) <= max_length:
        return message
    truncated = message[:max_length - 50]
    return truncated + "\n\n<i>... (message truncated)</i>"

def get_status_message(stats):
    uptime = stats.get('uptime', 'Unknown')
    total_otps = stats.get('total_otps_sent', 0)
    last_check = stats.get('last_check', 'Never')
    cache_size = stats.get('cache_size', 0)
    return (
        f"🤖 <b>Bot Status</b>\n\n"
        f"⚡ Status: <b>Online</b>\n"
        f"⏱️ Uptime: {uptime}\n"
        f"📨 Total OTPs Sent: <b>{total_otps}</b>\n"
        f"🔍 Last Check: {last_check}\n"
        f"💾 Cache Size: {cache_size} items\n\n"
        f"<i>Bot is running and monitoring for new OTPs</i>"
    )
